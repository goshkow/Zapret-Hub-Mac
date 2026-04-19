from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlsplit


SOCKS_VERSION = 0x05
SOCKS_CMD_CONNECT = 0x01
SOCKS_CMD_UDP_ASSOCIATE = 0x03
SOCKS_ATYP_IPV4 = 0x01
SOCKS_ATYP_DOMAIN = 0x03
SOCKS_ATYP_IPV6 = 0x04


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while not reader.at_eof():
            chunk = await reader.read(65536)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _read_response_header(reader: asyncio.StreamReader) -> bytes:
    return await reader.readuntil(b"\r\n\r\n")


def _socks5_address_bytes(host: str) -> tuple[int, bytes]:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        encoded = host.encode("idna")
        return SOCKS_ATYP_DOMAIN, bytes([len(encoded)]) + encoded
    if ip.version == 4:
        return SOCKS_ATYP_IPV4, ip.packed
    return SOCKS_ATYP_IPV6, ip.packed


def _socks5_udp_pack(host: str, port: int, payload: bytes) -> bytes:
    atyp, address = _socks5_address_bytes(host)
    return b"\x00\x00\x00" + bytes([atyp]) + address + int(port).to_bytes(2, "big") + payload


def _socks5_udp_unpack(datagram: bytes) -> tuple[str, int, bytes]:
    if len(datagram) < 4 or datagram[2] != 0x00:
        raise ValueError("Fragmented SOCKS5 UDP datagrams are not supported.")
    atyp = datagram[3]
    offset = 4
    if atyp == SOCKS_ATYP_IPV4:
        if len(datagram) < offset + 4 + 2:
            raise ValueError("Malformed IPv4 SOCKS5 UDP datagram.")
        host = str(ipaddress.ip_address(datagram[offset:offset + 4]))
        offset += 4
    elif atyp == SOCKS_ATYP_IPV6:
        if len(datagram) < offset + 16 + 2:
            raise ValueError("Malformed IPv6 SOCKS5 UDP datagram.")
        host = str(ipaddress.ip_address(datagram[offset:offset + 16]))
        offset += 16
    elif atyp == SOCKS_ATYP_DOMAIN:
        if len(datagram) < offset + 1:
            raise ValueError("Malformed domain SOCKS5 UDP datagram.")
        length = datagram[offset]
        offset += 1
        if len(datagram) < offset + length + 2:
            raise ValueError("Malformed domain SOCKS5 UDP datagram.")
        host = datagram[offset:offset + length].decode("idna", errors="ignore")
        offset += length
    else:
        raise ValueError("Unsupported SOCKS5 UDP address type.")
    port = int.from_bytes(datagram[offset:offset + 2], "big")
    offset += 2
    return host, port, datagram[offset:]


async def _read_socks5_address(reader: asyncio.StreamReader, atyp: int) -> tuple[str, int]:
    if atyp == SOCKS_ATYP_IPV4:
        host = str(ipaddress.ip_address(await reader.readexactly(4)))
    elif atyp == SOCKS_ATYP_IPV6:
        host = str(ipaddress.ip_address(await reader.readexactly(16)))
    elif atyp == SOCKS_ATYP_DOMAIN:
        length = (await reader.readexactly(1))[0]
        host = (await reader.readexactly(length)).decode("idna", errors="ignore")
    else:
        raise ConnectionError("Unsupported SOCKS5 address type.")
    port = int.from_bytes(await reader.readexactly(2), "big")
    return host, port


async def _consume_socks5_bind_reply(reader: asyncio.StreamReader) -> tuple[str, int]:
    response = await reader.readexactly(4)
    if response[0] != SOCKS_VERSION or response[1] != 0x00:
        raise ConnectionError(f"SOCKS5 upstream failed with code {response[1]}.")
    return await _read_socks5_address(reader, response[3])


async def _open_upstream_tunnel(
    profile: dict[str, object],
    target_host: str,
    target_port: int,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    scheme = str(profile.get("upstream_proxy_scheme", "http")).lower()
    if scheme == "socks5":
        return await _open_socks5_tunnel(profile, target_host, target_port)

    upstream_host = str(profile.get("upstream_proxy_host", ""))
    upstream_port = int(profile.get("upstream_proxy_port", 0))
    timeout = float(profile.get("connect_timeout", 8.0))
    upstream_reader, upstream_writer = await asyncio.wait_for(
        asyncio.open_connection(upstream_host, upstream_port),
        timeout=timeout,
    )
    request = (
        f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
        f"Host: {target_host}:{target_port}\r\n"
        "Proxy-Connection: Keep-Alive\r\n\r\n"
    ).encode("utf-8")
    upstream_writer.write(request)
    await upstream_writer.drain()
    response_header = await asyncio.wait_for(_read_response_header(upstream_reader), timeout=timeout)
    status_line = response_header.decode("utf-8", errors="ignore").split("\r\n", 1)[0]
    if " 200 " not in status_line:
        upstream_writer.close()
        await upstream_writer.wait_closed()
        raise ConnectionError(f"Upstream proxy CONNECT failed: {status_line or 'unknown response'}")
    return upstream_reader, upstream_writer


async def _open_socks5_tunnel(
    profile: dict[str, object],
    target_host: str,
    target_port: int,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    upstream_host = str(profile.get("upstream_proxy_host", ""))
    upstream_port = int(profile.get("upstream_proxy_port", 0))
    timeout = float(profile.get("connect_timeout", 8.0))
    upstream_reader, upstream_writer = await asyncio.wait_for(
        asyncio.open_connection(upstream_host, upstream_port),
        timeout=timeout,
    )
    upstream_writer.write(b"\x05\x01\x00")
    await upstream_writer.drain()
    greeting = await asyncio.wait_for(upstream_reader.readexactly(2), timeout=timeout)
    if greeting != b"\x05\x00":
        upstream_writer.close()
        await upstream_writer.wait_closed()
        raise ConnectionError("SOCKS5 upstream rejected no-auth handshake.")

    atyp, address = _socks5_address_bytes(target_host)
    request = b"\x05\x01\x00" + bytes([atyp]) + address + int(target_port).to_bytes(2, "big")
    upstream_writer.write(request)
    await upstream_writer.drain()
    await asyncio.wait_for(_consume_socks5_bind_reply(upstream_reader), timeout=timeout)
    return upstream_reader, upstream_writer


async def _open_socks5_udp_associate(
    profile: dict[str, object],
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter, tuple[str, int]]:
    upstream_host = str(profile.get("upstream_proxy_host", ""))
    upstream_port = int(profile.get("upstream_proxy_port", 0))
    timeout = float(profile.get("connect_timeout", 8.0))
    upstream_reader, upstream_writer = await asyncio.wait_for(
        asyncio.open_connection(upstream_host, upstream_port),
        timeout=timeout,
    )
    upstream_writer.write(b"\x05\x01\x00")
    await upstream_writer.drain()
    greeting = await asyncio.wait_for(upstream_reader.readexactly(2), timeout=timeout)
    if greeting != b"\x05\x00":
        upstream_writer.close()
        await upstream_writer.wait_closed()
        raise ConnectionError("SOCKS5 upstream rejected UDP associate handshake.")
    request = b"\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00"
    upstream_writer.write(request)
    await upstream_writer.drain()
    bind_host, bind_port = await asyncio.wait_for(_consume_socks5_bind_reply(upstream_reader), timeout=timeout)
    return upstream_reader, upstream_writer, (bind_host, bind_port)


class _SocksUdpRelay(asyncio.DatagramProtocol):
    def __init__(self, upstream_addr: tuple[str, int]) -> None:
        self.upstream_addr = upstream_addr
        self.transport: asyncio.DatagramTransport | None = None
        self.client_addr: tuple[str, int] | None = None

    def connection_made(self, transport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        if self.transport is None:
            return
        if addr == self.upstream_addr:
            if self.client_addr is not None:
                self.transport.sendto(data, self.client_addr)
            return
        self.client_addr = addr
        self.transport.sendto(data, self.upstream_addr)

    def close(self) -> None:
        if self.transport is not None:
            self.transport.close()
            self.transport = None


async def _handle_http_proxy(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    profile: dict[str, object],
    first_byte: bytes,
) -> None:
    try:
        header = first_byte + await reader.readuntil(b"\r\n\r\n")
    except Exception:
        writer.close()
        return

    lines = header.decode("utf-8", errors="ignore").split("\r\n")
    request_line = lines[0]
    parts = request_line.split()
    if len(parts) < 3:
        writer.close()
        return
    method, target, version = parts[0], parts[1], parts[2]
    timeout = float(profile.get("connect_timeout", 8.0))
    use_upstream = bool(profile.get("upstream_proxy_enabled")) and bool(profile.get("upstream_proxy_host"))

    if method.upper() == "CONNECT":
        host, port_text = target.rsplit(":", 1)
        if use_upstream:
            remote_reader, remote_writer = await _open_upstream_tunnel(profile, host, int(port_text))
        else:
            remote_reader, remote_writer = await asyncio.wait_for(asyncio.open_connection(host, int(port_text)), timeout=timeout)
        writer.write(f"{version} 200 Connection Established\r\n\r\n".encode("utf-8"))
        await writer.drain()
        await asyncio.gather(_pipe(reader, remote_writer), _pipe(remote_reader, writer))
        return

    parsed = urlsplit(target)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    if use_upstream:
        scheme = str(profile.get("upstream_proxy_scheme", "http")).lower()
        if scheme == "socks5":
            remote_reader, remote_writer = await _open_socks5_tunnel(profile, host, port)
        else:
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(str(profile.get("upstream_proxy_host", "")), int(profile.get("upstream_proxy_port", 0))),
                timeout=timeout,
            )
    else:
        remote_reader, remote_writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    request_target = target if use_upstream and str(profile.get("upstream_proxy_scheme", "http")).lower() != "socks5" else path
    rebuilt = [f"{method} {request_target} {version}"]
    for line in lines[1:]:
        if not line:
            continue
        rebuilt.append(line)
    payload = ("\r\n".join(rebuilt) + "\r\n\r\n").encode("utf-8")
    remote_writer.write(payload)
    await remote_writer.drain()
    await asyncio.gather(_pipe(reader, remote_writer), _pipe(remote_reader, writer))


async def _handle_socks5_proxy(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, profile: dict[str, object]) -> None:
    timeout = float(profile.get("connect_timeout", 8.0))
    try:
        methods_count = (await asyncio.wait_for(reader.readexactly(1), timeout=timeout))[0]
        await asyncio.wait_for(reader.readexactly(methods_count), timeout=timeout)
        writer.write(b"\x05\x00")
        await writer.drain()

        version, command, _reserved, atyp = await asyncio.wait_for(reader.readexactly(4), timeout=timeout)
        if version != SOCKS_VERSION:
            raise ConnectionError("Unsupported SOCKS version.")
        target_host, target_port = await asyncio.wait_for(_read_socks5_address(reader, atyp), timeout=timeout)
    except Exception:
        writer.close()
        await writer.wait_closed()
        return

    use_upstream = bool(profile.get("upstream_proxy_enabled")) and bool(profile.get("upstream_proxy_host"))
    scheme = str(profile.get("upstream_proxy_scheme", "http")).lower()

    if command == SOCKS_CMD_CONNECT:
        try:
            if use_upstream:
                remote_reader, remote_writer = await _open_upstream_tunnel(profile, target_host, target_port)
            else:
                remote_reader, remote_writer = await asyncio.wait_for(asyncio.open_connection(target_host, target_port), timeout=timeout)
            local_host, local_port = remote_writer.get_extra_info("sockname")[:2]
            atyp, address = _socks5_address_bytes(str(local_host))
            writer.write(b"\x05\x00\x00" + bytes([atyp]) + address + int(local_port).to_bytes(2, "big"))
            await writer.drain()
            await asyncio.gather(_pipe(reader, remote_writer), _pipe(remote_reader, writer))
            return
        except Exception:
            writer.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return

    if command == SOCKS_CMD_UDP_ASSOCIATE:
        if not use_upstream or scheme != "socks5":
            writer.write(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
        relay: _SocksUdpRelay | None = None
        tcp_writer: asyncio.StreamWriter | None = None
        try:
            _tcp_reader, tcp_writer, upstream_addr = await _open_socks5_udp_associate(profile)
            loop = asyncio.get_running_loop()
            relay = _SocksUdpRelay(upstream_addr)
            transport, _protocol = await loop.create_datagram_endpoint(
                lambda: relay,
                local_addr=(str(profile.get("listen_host", "127.0.0.1")), 0),
                family=socket.AF_INET,
            )
            local_host, local_port = transport.get_extra_info("sockname")[:2]
            atyp, address = _socks5_address_bytes(str(local_host))
            writer.write(b"\x05\x00\x00" + bytes([atyp]) + address + int(local_port).to_bytes(2, "big"))
            await writer.drain()
            await reader.read()
        except Exception:
            writer.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
        finally:
            if relay is not None:
                relay.close()
            if tcp_writer is not None:
                tcp_writer.close()
                try:
                    await tcp_writer.wait_closed()
                except Exception:
                    pass
            writer.close()
            await writer.wait_closed()
        return

    writer.write(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, profile: dict[str, object]) -> None:
    try:
        first_byte = await reader.readexactly(1)
    except Exception:
        writer.close()
        return
    if first_byte == bytes([SOCKS_VERSION]):
        await _handle_socks5_proxy(reader, writer, profile)
        return
    await _handle_http_proxy(reader, writer, profile, first_byte)


async def _handle_health(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        await reader.read(1024)
    except Exception:
        pass
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"ok\":true}")
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def _run(profile: dict[str, object]) -> None:
    proxy_server = await asyncio.start_server(
        lambda r, w: _handle_client(r, w, profile),
        str(profile.get("listen_host", "127.0.0.1")),
        int(profile.get("listen_port", 9080)),
    )
    health_server = await asyncio.start_server(
        _handle_health,
        str(profile.get("listen_host", "127.0.0.1")),
        int(profile.get("health_port", 9081)),
    )
    async with proxy_server, health_server:
        await asyncio.gather(proxy_server.serve_forever(), health_server.serve_forever())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--log-file", required=False)
    args = parser.parse_args()

    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    asyncio.run(_run(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
