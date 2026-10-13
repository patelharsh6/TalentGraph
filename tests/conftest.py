import ipaddress
import socket
from collections.abc import Iterator
from typing import Any

import pytest

from talentgraph.config import Settings

NETWORK_MARKERS = ("integration", "e2e", "llm")


@pytest.fixture
def settings(tmp_path: object) -> Settings:
    """Offline settings: no API key, fake LLM."""
    return Settings(
        _env_file=None, llm_mode="fake", gemini_api_key=None, fixtures_dir=str(tmp_path)
    )


@pytest.fixture(autouse=True)
def _block_network(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Unit tests must run offline (exit criterion 0-B): refuse non-loopback connections.

    Loopback stays allowed because asyncio's event loop uses a local socket pair on Windows.
    Tests marked integration, e2e or llm may use the network.
    """
    if any(request.node.get_closest_marker(m) for m in NETWORK_MARKERS):
        yield
        return

    real_connect = socket.socket.connect

    def guarded_connect(self: socket.socket, address: Any) -> None:
        host = address[0] if isinstance(address, tuple) else None
        if host is not None:
            try:
                loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                loopback = host == "localhost"
            if not loopback:
                raise RuntimeError(f"unit tests must not use the network (tried {address!r})")
        real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    yield
