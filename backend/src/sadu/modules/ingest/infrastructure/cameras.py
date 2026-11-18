import asyncio
import os
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from sadu.modules.ingest.application.ports import CameraTarget, CameraUnreachable
from sadu.modules.ingest.domain.url_safety import (
    RTSP_SCHEMES,
    SNAPSHOT_SCHEMES,
    AllowList,
    CameraUrl,
    IpAddress,
    UnsafeCameraUrl,
    check_addresses,
    parse_camera_url,
)

type Resolver = Callable[[str, int], Awaitable[list[str]]]

CAMERA_TIMEOUT_S = 10.0
ACCEPTED_CONTENT_TYPES = ("image/jpeg", "image/jpg", "image/png")


async def system_resolver(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def camera_password(secret_env: str | None) -> str | None:
    if not secret_env:
        return None
    return os.environ.get(secret_env) or None


@dataclass(frozen=True)
class _Response:
    status: int
    challenge: str
    body: bytes


class SafeAddresses:
    def __init__(self, allowed: AllowList, resolve: Resolver = system_resolver) -> None:
        self._allowed = allowed
        self._resolve = resolve

    async def pin(self, url_text: str, schemes: frozenset[str]) -> tuple[CameraUrl, IpAddress]:
        try:
            url = parse_camera_url(url_text, schemes)
        except UnsafeCameraUrl as error:
            raise CameraUnreachable("invalid_url") from error
        try:
            addresses = await self._resolve(url.host, url.port)
        except OSError as error:
            raise CameraUnreachable("unresolvable") from error
        try:
            return url, check_addresses(url.host, addresses, self._allowed)[0]
        except UnsafeCameraUrl as error:
            raise CameraUnreachable(error.reason) from error


class HttpSnapshots:
    def __init__(
        self,
        addresses: SafeAddresses,
        max_bytes: int,
        *,
        timeout_s: float = CAMERA_TIMEOUT_S,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._addresses = addresses
        self._max_bytes = max_bytes
        self._timeout_s = timeout_s
        self._transport = transport

    async def fetch(self, url_text: str, username: str | None, password: str | None) -> bytes:
        url, address = await self._addresses.pin(url_text, SNAPSHOT_SCHEMES)
        async with httpx.AsyncClient(
            transport=self._transport, timeout=self._timeout_s, follow_redirects=False
        ) as client:
            try:
                response = await self._get(client, url, address, _digest(username, password))
                if response.status == 401 and username and response.challenge.startswith("basic"):
                    response = await self._get(
                        client, url, address, httpx.BasicAuth(username, password or "")
                    )
            except httpx.TimeoutException as error:
                raise CameraUnreachable("timeout") from error
            except httpx.HTTPError as error:
                raise CameraUnreachable("connection") from error
        if response.status != 200:
            raise CameraUnreachable("http_status", status=response.status)
        return response.body

    async def _get(
        self, client: httpx.AsyncClient, url: CameraUrl, address: IpAddress, auth: httpx.Auth | None
    ) -> _Response:
        extensions = {"sni_hostname": url.host} if url.scheme == "https" else {}
        async with client.stream(
            "GET",
            url.pinned_to(address),
            headers={"Host": url.host_header, "Accept": "image/jpeg, image/png"},
            extensions=extensions,
            auth=auth,
        ) as response:
            if response.status_code != 200:
                return _Response(
                    response.status_code, response.headers.get("www-authenticate", "").lower(), b""
                )
            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type not in ACCEPTED_CONTENT_TYPES:
                raise CameraUnreachable("not_image")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > self._max_bytes:
                    raise CameraUnreachable("too_large")
            return _Response(200, "", bytes(body))


class RtspSnapshots:
    def __init__(
        self,
        addresses: SafeAddresses,
        max_bytes: int,
        ffmpeg: str | None,
        *,
        timeout_s: float = CAMERA_TIMEOUT_S,
    ) -> None:
        self._addresses = addresses
        self._max_bytes = max_bytes
        self._ffmpeg = ffmpeg
        self._timeout_s = timeout_s

    async def fetch(self, url_text: str, username: str | None, password: str | None) -> bytes:
        if self._ffmpeg is None:
            raise CameraUnreachable("rtsp_unavailable")
        url, address = await self._addresses.pin(url_text, RTSP_SCHEMES)
        process = await asyncio.create_subprocess_exec(
            self._ffmpeg,
            "-nostdin",
            "-loglevel",
            "error",
            "-protocol_whitelist",
            "rtsp,rtp,tcp,udp",
            "-rtsp_transport",
            "tcp",
            "-i",
            url.pinned_to(address, _userinfo(username, password)),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "pipe:1",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            frame, _ = await asyncio.wait_for(process.communicate(), timeout=self._timeout_s)
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise CameraUnreachable("timeout") from error
        if process.returncode != 0 or not frame:
            raise CameraUnreachable("connection")
        if len(frame) > self._max_bytes:
            raise CameraUnreachable("too_large")
        return frame


class NetworkCameras:
    def __init__(self, http: HttpSnapshots, rtsp: RtspSnapshots) -> None:
        self._http = http
        self._rtsp = rtsp

    async def snapshot(self, target: CameraTarget) -> bytes:
        if target.snapshot_url:
            return await self._http.fetch(target.snapshot_url, target.username, target.password)
        if target.rtsp_url:
            return await self._rtsp.fetch(target.rtsp_url, target.username, target.password)
        raise CameraUnreachable("no_source")


def _digest(username: str | None, password: str | None) -> httpx.Auth | None:
    if not username:
        return None
    return httpx.DigestAuth(username, password or "")


def _userinfo(username: str | None, password: str | None) -> str:
    if not username:
        return ""
    if not password:
        return f"{quote(username, safe='')}@"
    return f"{quote(username, safe='')}:{quote(password, safe='')}@"
