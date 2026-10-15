"""Step 2.9: record real Gemini responses as FakeLLM fixtures.

    uv run python scripts/record_llm_fixtures.py                  # tests/fixtures/resumes (18)
    uv run python scripts/record_llm_fixtures.py --split val      # all of data/resumes/val
    uv run python scripts/record_llm_fixtures.py --split val --ids candidate_0009,candidate_0016
    uv run python scripts/record_llm_fixtures.py --force          # re-record existing fixtures

Each resume is parsed by the ParsingAgent with a `RecordingLLM`: inputs that already have a
fixture are replayed, the rest call Gemini once and are saved under
`tests/fixtures/llm/ResumeExtraction/`. A fixture is keyed by the exact prompt, so changing the
prompt, the extractors or the section detector means re-recording.

The free tier allows 20 requests a day and failed attempts count, so by default each call gets
one attempt (`--attempts`) and a generous timeout. The run stops at `--max-calls` or after
`--max-consecutive-failures`, and waits `--failure-backoff` after a failure (503s come in bursts);
failed resumes stay unrecorded for the next run. Calls are paced *between* parses, so each
parse's latency is a clean sequential real-API measurement; they are written to
`reports/record_<label>_<time>.json` and serve as the 2-F latency sample.

Free-tier data policy (plan §3.1): only synthetic resumes go through this script. Resumes under
`data/private/` are refused, because their fixtures would land in a committed folder.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.config import get_settings
from talentgraph.llm.client import get_llm
from talentgraph.llm.recording import RecordingLLM
from talentgraph.observability.logging import configure_logging

ROOT = Path(__file__).resolve().parent.parent
EXTS = (".pdf", ".docx", ".txt")


def percentiles(values: list[int]) -> dict[str, int]:
    if not values:
        return {}
    v = sorted(values)

    def pct(q: float) -> int:
        return v[min(len(v) - 1, round(q * (len(v) - 1)))]

    return {"n": len(v), "p50": pct(0.5), "p95": pct(0.95), "max": v[-1]}


async def record(
    files: list[Path],
    llm: RecordingLLM,
    *,
    interval_s: float,
    max_calls: int,
    max_consecutive_failures: int,
    failure_backoff_s: float,
) -> list[dict[str, Any]]:
    """Parse each file once; stop at the call budget or after a run of failures.

    The free-tier model fails intermittently with 503 "high demand"; a failed resume is left
    unrecorded (the next run picks it up) and the next call waits `failure_backoff_s`.
    """
    agent = ParsingAgent(llm=llm)
    rows: list[dict[str, Any]] = []
    consecutive = 0
    last_call = 0.0
    for i, path in enumerate(files, 1):
        if llm.recorded + llm.failed >= max_calls:
            print(f"Call budget of {max_calls} reached.", file=sys.stderr)
            break
        gap = interval_s if consecutive == 0 else failure_backoff_s
        wait = last_call + gap - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        before = llm.recorded + llm.failed
        result = await agent.parse(path.read_bytes(), path.name)
        called = llm.recorded + llm.failed > before
        if called:
            last_call = time.monotonic()
        action = "recorded" if called else "replayed"
        if result.status != "ok":
            consecutive += 1
            action = f"FAILED ({'; '.join(result.warnings)})"
        else:
            consecutive = 0
        rows.append(
            {
                "file": path.name,
                "action": "failed" if result.status != "ok" else action,
                "called_api": called,
                "status": result.status,
                "latency_ms": result.latency_ms,
                "timings_ms": result.timings_ms,
                "unverified": result.resume.meta.unverified_count,
                "checked": result.resume.meta.llm_field_count,
            }
        )
        print(f"[{i}/{len(files)}] {path.name}: {action} ({result.latency_ms} ms)", flush=True)
        if consecutive >= max_consecutive_failures:
            print(f"Stopping after {consecutive} failures in a row.", file=sys.stderr)
            break
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Record FakeLLM fixtures with the real Gemini API.")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--split", help="data/resumes/<split> instead of tests/fixtures/resumes")
    src.add_argument("--dir", type=Path)
    ap.add_argument("--ids", help="comma-separated file stems to record (default: all)")
    ap.add_argument("--fixtures-dir", type=Path, default=ROOT / "tests" / "fixtures" / "llm")
    ap.add_argument("--force", action="store_true", help="call the API even if a fixture exists")
    ap.add_argument("--interval", type=float, default=6.0, help="seconds between API calls")
    ap.add_argument("--attempts", type=int, default=1, help="attempts per call (quota!)")
    ap.add_argument("--timeout", type=float, default=30.0, help="seconds per attempt")
    ap.add_argument("--max-calls", type=int, default=18, help="API calls this run (20/day)")
    ap.add_argument("--max-consecutive-failures", type=int, default=3)
    ap.add_argument("--failure-backoff", type=float, default=90.0, help="seconds after a failure")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--label", default=None)
    ap.add_argument("--log-level", default="WARNING", help="INFO shows tokens per call")
    args = ap.parse_args()
    configure_logging(args.log_level)

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

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTS)
    if args.ids:
        wanted = set(args.ids.split(","))
        files = [p for p in files if p.stem in wanted]
    files = files[: args.limit]
    real_settings = settings.model_copy(
        update={
            "llm_mode": "real",
            "llm_max_attempts": args.attempts,
            "llm_timeout_s": args.timeout,
        }
    )
    llm = RecordingLLM(get_llm(real_settings), args.fixtures_dir, replay=not args.force)
    rows = asyncio.run(
        record(
            files,
            llm,
            interval_s=args.interval,
            max_calls=args.max_calls,
            max_consecutive_failures=args.max_consecutive_failures,
            failure_backoff_s=args.failure_backoff,
        )
    )

    write_report(rows, llm, label=args.label or folder.name)
    return 1 if llm.failed or any(r["status"] != "ok" for r in rows) else 0


def write_report(rows: list[dict[str, Any]], llm: RecordingLLM, *, label: str) -> Path:
    """`reports/record_<label>_<time>.json`: per-resume results and real-call latency."""
    settings = get_settings()
    real = [r for r in rows if r["called_api"] and r["status"] == "ok"]
    report = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": settings.llm_model,
        "thinking_level": settings.llm_thinking_level,
        "recorded": llm.recorded,
        "failed_calls": llm.failed,
        "replayed": llm.replayed,
        "latency_ms_real_calls": percentiles([r["latency_ms"] for r in real]),
        "llm_ms_real_calls": percentiles([r["timings_ms"].get("llm", 0) for r in real]),
        "rows": rows,
    }
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"record_{label}_{stamp}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"{llm.recorded} recorded, {llm.replayed} replayed, {llm.failed} failed calls; "
        f"real-call latency {report['latency_ms_real_calls']}; wrote {path.name}"
    )
    return path


if __name__ == "__main__":
    raise SystemExit(main())
