"""End-to-end parsing of the fixture resumes with recorded Gemini responses (Step 2.9, 2-A/2-C).

FakeLLM replays the real extraction recorded by `scripts/record_llm_fixtures.py`, so this runs
offline. A resume whose fixture hasn't been recorded yet is skipped (the free tier allows only
20 recordings a day); once recorded, it must parse cleanly.
"""

from datetime import date
from pathlib import Path

import pytest
from eval.parsing import score_resume
from parsing_samples import SAMPLES, Sample

from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.parsing.llm_extract import build_user_message, system_prompt
from talentgraph.config import Settings
from talentgraph.core.schemas.resume import ParsedResume, ResumeExtraction
from talentgraph.llm.fake import FakeLLM

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "llm"
MIN_F1 = 0.80  # per resume; the milestone target (0.85) is on the whole val split
MAX_UNVERIFIED_SHARE = 0.10  # per resume; M7 (≤ 5%) is measured on the whole val split


def _fixture_exists(agent: ParsingAgent, sample: Sample) -> bool:
    _, sections, rules = agent._prepare(sample.path.read_bytes())
    user, _ = build_user_message(sections, rules)
    key = FakeLLM.fixture_key(system_prompt(), user)
    return (FIXTURES / ResumeExtraction.__name__ / f"{key}.json").is_file()


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s.id)
async def test_recorded_extraction(settings: Settings, sample: Sample) -> None:
    llm = FakeLLM(FIXTURES)
    agent = ParsingAgent(settings, llm=llm, today=date(2026, 10, 13))
    if not _fixture_exists(agent, sample):
        pytest.skip("Gemini response not recorded yet (scripts/record_llm_fixtures.py)")

    result = await agent.parse(sample.path.read_bytes(), sample.path.name)
    assert result.status == "ok", result.warnings
    meta = result.resume.meta
    assert meta.unverified_count <= MAX_UNVERIFIED_SHARE * meta.llm_field_count

    gold = ParsedResume.model_validate(sample.gold)
    counts = score_resume(gold, result.resume).fields
    tp = sum(c.tp for c in counts.values())
    fp = sum(c.fp for c in counts.values())
    fn = sum(c.fn for c in counts.values())
    f1 = 2 * tp / (2 * tp + fp + fn)
    assert f1 >= MIN_F1, f"F1 {f1:.3f}"
