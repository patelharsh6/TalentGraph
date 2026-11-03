"""Network utility helpers for fast non-blocking service reachability checks."""

from __future__ import annotations

import asyncio
import concurrent.futures
import socket
from urllib.parse import urlsplit

_probe_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="net_probe"
)


def parse_host_port(target: str, default_port: int) -> tuple[str, int]:
    """Parse host and port from a URL (e.g. postgresql://..., redis://...) or host[:port] string."""
    if not target:
        return "localhost", default_port
    if "://" in target:
        parsed = urlsplit(target)
        host = parsed.hostname or "localhost"
        port = parsed.port or default_port
        return host, port
    if ":" in target:
        parts = target.split(":", 1)
        try:
            return parts[0], int(parts[1])
        except ValueError:
            return parts[0], default_port
    return target, default_port


def _raw_socket_check(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def check_tcp_reachability(host: str | None, port: int | None, timeout: float = 0.25) -> bool:
    """Test if a TCP host:port is reachable, strictly bounded by timeout."""
    if not host or not port:
        return False
    future = _probe_executor.submit(_raw_socket_check, host, port, timeout)
    try:
        return future.result(timeout=timeout + 0.05)
    except Exception:
        return False


async def is_service_reachable_async(
    host: str | None, port: int | None, timeout_s: float = 0.25
) -> bool:
    """Asynchronously probe TCP reachability off the main loop, bounded by timeout."""
    if not host or not port:
        return False
    loop = asyncio.get_running_loop()
    try:
        async with asyncio.timeout(timeout_s + 0.1):
            return await loop.run_in_executor(
                None, lambda: check_tcp_reachability(host, port, timeout_s)
            )
    except Exception:
        return False
