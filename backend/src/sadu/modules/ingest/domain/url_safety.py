import ipaddress
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit

type IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
type IpNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

SNAPSHOT_SCHEMES = frozenset({"http", "https"})
RTSP_SCHEMES = frozenset({"rtsp"})
DEFAULT_PORTS = {"http": 80, "https": 443, "rtsp": 554}
MAX_URL_LENGTH = 500
SECRET_QUERY_KEYS = frozenset({"pass", "passwd", "password", "pwd", "token", "key", "secret", "auth"})
METADATA_ADDRESSES = frozenset(
    {ipaddress.ip_address("169.254.169.254"), ipaddress.ip_address("fd00:ec2::254")}
)


class UnsafeCameraUrl(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class AllowList:
    hosts: frozenset[str] = frozenset()
    networks: tuple[IpNetwork, ...] = ()

    @classmethod
    def parse(cls, entries: str) -> "AllowList":
        hosts: set[str] = set()
        networks: list[IpNetwork] = []
        for entry in (e.strip().lower() for e in entries.split(",")):
            if not entry:
                continue
            try:
                networks.append(ipaddress.ip_network(entry, strict=False))
            except ValueError:
                hosts.add(entry)
        return cls(frozenset(hosts), tuple(networks))

    def with_host(self, host: str) -> "AllowList":
        return AllowList(self.hosts | {host.lower()}, self.networks)

    def allows(self, host: str, address: IpAddress) -> bool:
        return host.lower() in self.hosts or any(address in network for network in self.networks)


@dataclass(frozen=True)
class CameraUrl:
    scheme: str
    host: str
    port: int
    target: str

    @property
    def host_header(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        if self.port == DEFAULT_PORTS[self.scheme]:
            return host
        return f"{host}:{self.port}"

    def pinned_to(self, address: IpAddress, userinfo: str = "") -> str:
        host = f"[{address}]" if address.version == 6 else str(address)
        return f"{self.scheme}://{userinfo}{host}:{self.port}{self.target}"


def parse_camera_url(url: str, schemes: frozenset[str]) -> CameraUrl:
    if len(url) > MAX_URL_LENGTH:
        raise UnsafeCameraUrl("too_long")
    parts = urlsplit(url)
    if parts.scheme not in schemes:
        raise UnsafeCameraUrl("scheme")
    if not parts.hostname:
        raise UnsafeCameraUrl("host")
    if parts.username is not None or parts.password is not None or _has_secret_query(parts.query):
        raise UnsafeCameraUrl("credentials_in_url")
    try:
        port = parts.port or DEFAULT_PORTS[parts.scheme]
    except ValueError as error:
        raise UnsafeCameraUrl("port") from error
    target = parts.path or "/"
    if parts.query:
        target = f"{target}?{parts.query}"
    return CameraUrl(parts.scheme, parts.hostname, port, target)


def check_addresses(host: str, addresses: list[str], allowed: AllowList) -> list[IpAddress]:
    if not addresses:
        raise UnsafeCameraUrl("unresolvable")
    checked = []
    for text in addresses:
        address = _unmapped(ipaddress.ip_address(text.split("%", 1)[0]))
        if address in METADATA_ADDRESSES:
            raise UnsafeCameraUrl("blocked_address")
        if not allowed.allows(host, address) and not _is_public(address):
            raise UnsafeCameraUrl("blocked_address")
        checked.append(address)
    return checked


def _has_secret_query(query: str) -> bool:
    return any(name.lower() in SECRET_QUERY_KEYS for name, _ in parse_qsl(query, keep_blank_values=True))


def _is_public(address: IpAddress) -> bool:
    return address.is_global and not address.is_multicast


def _unmapped(address: IpAddress) -> IpAddress:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address
