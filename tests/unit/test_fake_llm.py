import json
from pathlib import Path

from pydantic import BaseModel

from talentgraph.config import Settings
from talentgraph.llm import get_llm
from talentgraph.llm.fake import FakeLLM


class Person(BaseModel):
    name: str = "unknown"


def test_get_llm_without_key_returns_fake(settings: Settings) -> None:
    assert isinstance(get_llm(settings), FakeLLM)


async def test_fixture_lookup_by_input_hash(tmp_path: Path) -> None:
    llm = FakeLLM(tmp_path)
    key = FakeLLM.fixture_key("sys", "user")
    (tmp_path / "Person").mkdir()
    (tmp_path / "Person" / f"{key}.json").write_text(json.dumps({"name": "Ada"}))
    assert (await llm.extract(Person, "sys", "user")).name == "Ada"
    assert llm.calls == [("Person", key)]


async def test_falls_back_to_register_then_defaults(tmp_path: Path) -> None:
    llm = FakeLLM(tmp_path)
    assert (await llm.extract(Person, "s", "u")).name == "unknown"
    llm.register(Person, {"name": "Grace"})
    assert (await llm.extract(Person, "s", "u")).name == "Grace"
