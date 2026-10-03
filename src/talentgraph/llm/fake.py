"""Offline LLM used by tests (`fake`) and load tests (`stub`, with simulated latency)."""

import asyncio
import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from talentgraph.core.ids import sha256_hex

T = TypeVar("T", bound=BaseModel)


class FakeLLM:
    """Returns recorded fixtures keyed by schema name and input hash.

    Lookup order: `<dir>/<Schema>/<sha256(system+user)[:16]>.json`, then
    `<dir>/<Schema>/default.json`, then an override registered with `register()`, then `schema()`
    built from defaults.
    """

    def __init__(self, fixtures_dir: str | Path, *, latency_ms: int = 0) -> None:
        self._dir = Path(fixtures_dir)
        self._latency_s = latency_ms / 1000
        self._overrides: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, str]] = []

    @staticmethod
    def fixture_key(system: str, user: str) -> str:
        return sha256_hex(system + "\n" + user)[:16]

    def register(self, schema: type[BaseModel], payload: dict[str, Any]) -> None:
        self._overrides[schema.__name__] = payload

    async def extract(self, schema: type[T], system: str, user: str) -> T:
        self.calls.append((schema.__name__, self.fixture_key(system, user)))
        if self._latency_s:
            await asyncio.sleep(self._latency_s)

        folder = self._dir / schema.__name__
        for candidate in (
            folder / f"{self.fixture_key(system, user)}.json",
            folder / "default.json",
        ):
            if candidate.is_file():
                return schema.model_validate(json.loads(candidate.read_text(encoding="utf-8")))
        if schema.__name__ in self._overrides:
            return schema.model_validate(self._overrides[schema.__name__])
        return schema()
