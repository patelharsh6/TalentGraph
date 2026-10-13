"""Record real LLM responses as FakeLLM fixtures (Step 2.9).

`RecordingLLM` wraps a real client. When a fixture for the exact input already exists it is
replayed (no quota used); otherwise the real call is made and its validated response is written
to `<fixtures_dir>/<Schema>/<sha256(system+user)[:16]>.json`, where `FakeLLM` will find it.
Only synthetic or consented resumes may go through it (free-tier data policy, plan §3.1).
"""

import asyncio
import time
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from talentgraph.llm.client import LLMClient
from talentgraph.llm.fake import FakeLLM

T = TypeVar("T", bound=BaseModel)


class RecordingLLM:
    def __init__(
        self,
        inner: LLMClient,
        fixtures_dir: str | Path,
        *,
        replay: bool = True,
        min_interval_s: float = 0.0,
    ) -> None:
        self._inner = inner
        self._dir = Path(fixtures_dir)
        self._replay = replay
        self._min_interval_s = min_interval_s  # pace real calls to stay under the free-tier RPM
        self._last_call = 0.0
        self.recorded = 0
        self.replayed = 0

    def fixture_path(self, schema: type[BaseModel], system: str, user: str) -> Path:
        return self._dir / schema.__name__ / f"{FakeLLM.fixture_key(system, user)}.json"

    async def extract(self, schema: type[T], system: str, user: str) -> T:
        path = self.fixture_path(schema, system, user)
        if self._replay and path.is_file():
            self.replayed += 1
            return schema.model_validate_json(path.read_text(encoding="utf-8"))
        wait = self._last_call + self._min_interval_s - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call = time.monotonic()
        result = await self._inner.extract(schema, system, user)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(indent=1) + "\n", encoding="utf-8")
        self.recorded += 1
        return result
