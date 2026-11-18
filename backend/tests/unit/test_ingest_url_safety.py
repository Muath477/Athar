import ipaddress

import httpx
import pytest

from sadu.modules.ingest.application.ports import CameraTarget, CameraUnreachable
from sadu.modules.ingest.domain.url_safety import (
    RTSP_SCHEMES,
    SNAPSHOT_SCHEMES,
    AllowList,
    UnsafeCameraUrl,
    check_addresses,
    parse_camera_url,
)
from sadu.modules.ingest.infrastructure.cameras import (
    HttpSnapshots,
    NetworkCameras,
    RtspSnapshots,
    SafeAddresses,
)

pytestmark = pytest.mark.anyio

JPEG = b"\xff\xd8\xff\xe0fake-jpeg"
MAX_BYTES = 1024


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("ftp://camera.example/snap.jpg", "scheme"),
        ("file:///etc/passwd", "scheme"),
        ("http:///snap.jpg", "host"),
        ("http://admin:hunter2@camera.example/snap.jpg", "credentials_in_url"),
        ("http://camera.example/cgi?user=admin&pwd=hunter2", "credentials_in_url"),
        ("http://camera.example:99999/snap.jpg", "port"),
        ("http://camera.example/" + "a" * 500, "too_long"),
    ],
)
def test_unsafe_snapshot_urls_are_rejected(url: str, reason: str) -> None:
    with pytest.raises(UnsafeCameraUrl) as raised:
        parse_camera_url(url, SNAPSHOT_SCHEMES)
    assert raised.value.reason == reason


def test_snapshot_url_keeps_path_query_and_default_port() -> None:
    url = parse_camera_url(
        "https://Camera.Example/ISAPI/Streaming/channels/101/picture?size=2", SNAPSHOT_SCHEMES
    )

    assert (url.scheme, url.host, url.port) == ("https", "camera.example", 443)
    assert url.target == "/ISAPI/Streaming/channels/101/picture?size=2"
    assert url.host_header == "camera.example"
    assert url.pinned_to(ipaddress.ip_address("93.184.216.34")) == (
        "https://93.184.216.34:443/ISAPI/Streaming/channels/101/picture?size=2"
    )


def test_rtsp_urls_are_only_accepted_for_streams() -> None:
    assert parse_camera_url("rtsp://10.0.0.5/stream1", RTSP_SCHEMES).port == 554
    with pytest.raises(UnsafeCameraUrl):
        parse_camera_url("rtsp://10.0.0.5/stream1", SNAPSHOT_SCHEMES)


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "192.168.1.20",
        "172.16.0.9",
        "169.254.169.254",
        "100.64.0.1",
        "::1",
        "fe80::1",
        "::ffff:127.0.0.1",
        "0.0.0.1",
        "224.0.0.1",
    ],
)
def test_internal_addresses_are_blocked_by_default(address: str) -> None:
    with pytest.raises(UnsafeCameraUrl) as raised:
        check_addresses("camera.example", [address], AllowList())
    assert raised.value.reason == "blocked_address"


def test_public_addresses_pass() -> None:
    assert [str(a) for a in check_addresses("camera.example", ["93.184.216.34"], AllowList())] == [
        "93.184.216.34"
    ]


def test_every_resolved_address_must_be_safe() -> None:
    with pytest.raises(UnsafeCameraUrl):
        check_addresses("camera.example", ["93.184.216.34", "10.0.0.1"], AllowList())


def test_allowlist_opens_named_hosts_and_networks_but_never_metadata() -> None:
    allowed = AllowList.parse(" NVR.Site.Local , 10.20.0.0/16,")

    assert check_addresses("nvr.site.local", ["192.168.1.20"], allowed)
    assert check_addresses("cam-7", ["10.20.4.7"], allowed)
    with pytest.raises(UnsafeCameraUrl):
        check_addresses("cam-8", ["10.21.0.1"], allowed)
    with pytest.raises(UnsafeCameraUrl):
        check_addresses("metadata", ["169.254.169.254"], AllowList.parse("metadata,169.254.0.0/16"))


def resolver(*addresses: str):
    async def resolve(host: str, port: int) -> list[str]:
        return list(addresses)

    return resolve


def snapshots(handler, *addresses: str, allowed: AllowList | None = None) -> HttpSnapshots:
    safe = SafeAddresses(allowed or AllowList(), resolver(*addresses))
    return HttpSnapshots(safe, MAX_BYTES, transport=httpx.MockTransport(handler))


async def test_snapshot_is_fetched_from_the_checked_address() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=JPEG)

    body = await snapshots(handler, "93.184.216.34").fetch("http://camera.example:8080/snap.jpg", None, None)

    assert body == JPEG
    [request] = seen
    assert request.url.host == "93.184.216.34"
    assert request.url.port == 8080
    assert request.headers["host"] == "camera.example:8080"


async def test_private_camera_is_never_contacted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("request must not be sent")

    with pytest.raises(CameraUnreachable) as raised:
        await snapshots(handler, "169.254.169.254").fetch("http://camera.example/snap.jpg", None, None)
    assert raised.value.reason == "blocked_address"


async def test_allowlisted_site_network_camera_is_fetched() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=JPEG)

    fetcher = snapshots(handler, "192.168.1.64", allowed=AllowList.parse("192.168.1.0/24"))
    assert await fetcher.fetch("http://cam-north/snap.jpg", None, None) == JPEG


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (httpx.Response(302, headers={"location": "http://169.254.169.254/"}), "http_status"),
        (httpx.Response(404), "http_status"),
        (httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>"), "not_image"),
        (
            httpx.Response(200, headers={"content-type": "image/jpeg"}, content=b"x" * (MAX_BYTES + 1)),
            "too_large",
        ),
    ],
)
async def test_bad_camera_answers_are_rejected(response: httpx.Response, reason: str) -> None:
    with pytest.raises(CameraUnreachable) as raised:
        await snapshots(lambda _: response, "93.184.216.34").fetch(
            "http://camera.example/snap.jpg", None, None
        )
    assert raised.value.reason == reason


async def test_basic_auth_cameras_get_credentials_after_the_challenge() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("authorization", "").startswith("Basic "):
            return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=JPEG)
        return httpx.Response(401, headers={"www-authenticate": 'Basic realm="cam"'})

    assert (
        await snapshots(handler, "93.184.216.34").fetch("http://camera.example/snap.jpg", "viewer", "s3cret")
        == JPEG
    )


async def test_timeouts_surface_as_camera_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow", request=request)

    with pytest.raises(CameraUnreachable) as raised:
        await snapshots(handler, "93.184.216.34").fetch("http://camera.example/snap.jpg", None, None)
    assert raised.value.reason == "timeout"


async def test_rtsp_without_ffmpeg_is_reported() -> None:
    rtsp = RtspSnapshots(SafeAddresses(AllowList(), resolver("93.184.216.34")), MAX_BYTES, ffmpeg=None)
    cameras = NetworkCameras(snapshots(lambda _: httpx.Response(500), "93.184.216.34"), rtsp)

    with pytest.raises(CameraUnreachable) as raised:
        await cameras.snapshot(CameraTarget(snapshot_url=None, rtsp_url="rtsp://camera.example/stream1"))
    assert raised.value.reason == "rtsp_unavailable"


async def test_device_without_urls_has_nothing_to_capture() -> None:
    rtsp = RtspSnapshots(SafeAddresses(AllowList(), resolver()), MAX_BYTES, ffmpeg=None)
    cameras = NetworkCameras(snapshots(lambda _: httpx.Response(500)), rtsp)

    with pytest.raises(CameraUnreachable) as raised:
        await cameras.snapshot(CameraTarget(snapshot_url=None, rtsp_url=None))
    assert raised.value.reason == "no_source"
