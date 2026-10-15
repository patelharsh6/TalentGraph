"""Spend one day's Gemini free-tier quota on the remaining Milestone 2 LLM work, in order.

    docker compose run --rm tools uv run python scripts/daily_llm_batch.py      # once a day
    docker compose run --rm tools uv run python scripts/daily_llm_batch.py --status

The free tier gives `gemini-3.8-flash` 20 requests a day, and failed attempts count (owner chose
to stay on it, 2026-10-15). Each stage records into a cache that replays for free, so running
this every day simply continues where the last run stopped:

1. **val fixtures** (Step 2.9 → 2-B, 2-C, 2-F): every `data/resumes/val` resume, recorded into
   `tests/fixtures/llm/` (committed; the CI eval gate replays them).
2. **rewording** (Step 2.14): 50 val + 50 test profiles, checkpointed in
   `data/.checkpoints/reword_llm/`, rendered into `data/resumes/{val,test}_reworded/`.
3. **reworded val fixtures** (2-G): recorded into `data/.checkpoints/reworded_llm/` (gitignored).

When everything is recorded it prints the evaluation commands to run (all offline).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import record_llm_fixtures as rec  # noqa: E402
import reword_resumes as rw  # noqa: E402

from talentgraph.agents.parsing.agent import ParsingAgent  # noqa: E402
from talentgraph.agents.parsing.llm_extract import build_user_message, system_prompt  # noqa: E402
from talentgraph.config import get_settings  # noqa: E402
from talentgraph.llm.client import get_llm  # noqa: E402
from talentgraph.llm.fake import FakeLLM  # noqa: E402
from talentgraph.llm.recording import RecordingLLM  # noqa: E402
from talentgraph.observability.logging import configure_logging  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VAL = ROOT / "data" / "resumes" / "val"
VAL_REWORDED = ROOT / "data" / "resumes" / "val_reworded"
FIXTURES = ROOT / "tests" / "fixtures" / "llm"
REWORDED_FIXTURES = ROOT / "data" / ".checkpoints" / "reworded_llm"
EXTS = (".pdf", ".docx", ".txt")


def resumes(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTS)


def missing(files: list[Path], fixtures_dir: Path) -> list[Path]:
    """Resumes with no recorded ResumeExtraction for their current prompt."""
    agent = ParsingAgent(llm=FakeLLM(fixtures_dir))
    out = []
    for path in files:
        _, sections, rules = agent._prepare(path.read_bytes())
        user, _ = build_user_message(sections, rules)
        key = FakeLLM.fixture_key(system_prompt(), user)
        if not (fixtures_dir / "ResumeExtraction" / f"{key}.json").is_file():
            out.append(path)
    return out


def reword_pending() -> list[Path]:
    system = rw.PROMPT.read_text(encoding="utf-8")
    paths = [p for split in ("val", "test") for p in rw.select(split, 50)]
    out = []
    for p in paths:
        user = rw.user_message(json.loads(p.read_text(encoding="utf-8")))
        key = FakeLLM.fixture_key(system, user)
        if not (rw.CHECKPOINTS / "RewordedResume" / f"{key}.json").is_file():
            out.append(p)
    return out


def status() -> tuple[list[Path], list[Path], list[Path]]:
    val_missing = missing(resumes(VAL), FIXTURES)
    reword_missing = reword_pending()
    reworded_missing = missing(resumes(VAL_REWORDED), REWORDED_FIXTURES)
    print(f"1. val fixtures:          {88 - len(val_missing)}/88 recorded")
    print(f"2. rewording:             {100 - len(reword_missing)}/100 responses")
    n = len(resumes(VAL_REWORDED))
    print(f"3. reworded val fixtures: {n - len(reworded_missing)}/{n} recorded (rendered: {n})")
    return val_missing, reword_missing, reworded_missing


def recorder(fixtures_dir: Path) -> RecordingLLM:
    settings = get_settings().model_copy(
        update={"llm_mode": "real", "llm_max_attempts": 1, "llm_timeout_s": 60.0}
    )
    return RecordingLLM(get_llm(settings), fixtures_dir)


async def _record(todo: list[Path], fixtures_dir: Path, budget: int, label: str) -> int:
    llm = recorder(fixtures_dir)
    rows = await rec.record(
        todo,
        llm,
        interval_s=15.0,  # the per-minute limit tripped at ~4 calls in 40 s
        max_calls=budget,
        max_consecutive_failures=3,
        failure_backoff_s=90.0,
    )
    rec.write_report(rows, llm, label=label)
    return llm.recorded + llm.failed


async def run(budget: int) -> int:
    """Stages run strictly in order; a stage that isn't finished ends the day's run."""
    used = 0
    todo = missing(resumes(VAL), FIXTURES)
    if todo:
        print(f"\n== Stage 1: {len(todo)} val resumes to record")
        used += await _record(todo, FIXTURES, budget, "daily_val")
        if missing(resumes(VAL), FIXTURES):
            return used
    if reword_pending():
        if used >= budget:
            return used
        print(f"\n== Stage 2: {len(reword_pending())} profiles to reword")
        llm = rw.make_llm(15.0)
        assert llm is not None
        paths = [p for split in ("val", "test") for p in rw.select(split, 50)]
        await rw.reword_all(paths, llm, max_calls=budget - used)
        used += llm.recorded + llm.failed
        if reword_pending():
            return used
    todo = missing(resumes(VAL_REWORDED), REWORDED_FIXTURES)
    if todo and used < budget:
        print(f"\n== Stage 3: {len(todo)} reworded val resumes to record")
        used += await _record(todo, REWORDED_FIXTURES, budget - used, "daily_reworded")
    return used


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--budget", type=int, default=19, help="API calls to spend (20/day)")
    ap.add_argument("--status", action="store_true", help="show progress; spend nothing")
    args = ap.parse_args()
    configure_logging("WARNING")
    if args.status:
        status()
        return 0
    if get_settings().gemini_api_key is None:
        print("GEMINI_API_KEY is not set.", file=sys.stderr)
        return 2
    used = asyncio.run(run(args.budget))
    print(f"\nUsed {used} of {args.budget} calls. Progress now:")
    val_missing, reword_missing, reworded_missing = status()
    if not (val_missing or reword_missing or reworded_missing) and resumes(VAL_REWORDED):
        print(
            "\nAll LLM work is recorded. Evaluate (offline):\n"
            "  uv run python -m eval.parsing --split val\n"
            "  uv run python -m eval.parsing --dir data/resumes/val_reworded "
            f"--fixtures-dir {REWORDED_FIXTURES.relative_to(ROOT)} --label val_reworded"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
