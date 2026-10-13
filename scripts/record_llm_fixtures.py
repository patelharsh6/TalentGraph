"""Step 2.9: record real Gemini responses as FakeLLM fixtures.

    uv run python scripts/record_llm_fixtures.py                  # tests/fixtures/resumes (18)
    uv run python scripts/record_llm_fixtures.py --split val      # all of data/resumes/val
    uv run python scripts/record_llm_fixtures.py --force          # re-record existing fixtures

Each resume is parsed by the ParsingAgent with a `RecordingLLM`: inputs that already have a
fixture are replayed, the rest call Gemini once and are saved under
`tests/fixtures/llm/ResumeExtraction/`. A fixture is keyed by the exact prompt, so changing the
prompt, the extractors or the section detector means re-recording.

Free-tier data policy (plan §3.1): only synthetic resumes go through this script. Resumes under
`data/private/` are refused, because their fixtures would land in a committed folder.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.config import get_settings
from talentgraph.llm.client import get_llm
from talentgraph.llm.recording import RecordingLLM
from talentgraph.observability.logging import configure_logging

ROOT = Path(__file__).resolve().parent.parent
EXTS = (".pdf", ".docx", ".txt")


async def record(files: list[Path], llm: RecordingLLM) -> tuple[int, int]:
    agent = ParsingAgent(llm=llm)
    failures = 0
    for i, path in enumerate(files, 1):
        before = llm.recorded
        result = await agent.parse(path.read_bytes(), path.name)
        action = "recorded" if llm.recorded > before else "replayed"
        if result.status != "ok":
            failures += 1
            action = f"FAILED ({'; '.join(result.warnings)})"
        print(f"[{i}/{len(files)}] {path.name}: {action}", flush=True)
    return llm.recorded, failures


def main() -> int:
    ap = argparse.ArgumentParser(description="Record FakeLLM fixtures with the real Gemini API.")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--split", help="data/resumes/<split> instead of tests/fixtures/resumes")
    src.add_argument("--dir", type=Path)
    ap.add_argument("--fixtures-dir", type=Path, default=ROOT / "tests" / "fixtures" / "llm")
    ap.add_argument("--force", action="store_true", help="call the API even if a fixture exists")
    ap.add_argument("--min-interval", type=float, default=4.0, help="seconds between API calls")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    configure_logging("WARNING")

    folder = args.dir or (
        ROOT / "data" / "resumes" / args.split if args.split else ROOT / "tests/fixtures/resumes"
    )
    if (ROOT / "data" / "private") in folder.resolve().parents:
        print("Refusing to record fixtures for private resumes (ADR-0004 B).", file=sys.stderr)
        return 2
    settings = get_settings()
    if settings.gemini_api_key is None:
        print("GEMINI_API_KEY is not set; nothing to record with.", file=sys.stderr)
        return 2

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTS)[: args.limit]
    real = get_llm(settings.model_copy(update={"llm_mode": "real"}))
    llm = RecordingLLM(
        real, args.fixtures_dir, replay=not args.force, min_interval_s=args.min_interval
    )
    recorded, failures = asyncio.run(record(files, llm))
    print(f"{recorded} recorded, {len(files) - recorded - failures} replayed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
