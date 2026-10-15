"""Steps 2.13 and 5.8: sequential latency measurement, per agent or endpoint (M6).

    uv run python -m eval.latency --target parser --split val --n 20          # real Gemini
    uv run python -m eval.latency --target parser --n 20 --redis-url redis://localhost:6379/0

`--target parser` (exit criterion 2-F) parses N resumes one after another with the real API (no
fixture replay) and reports p50/p95/p99 of the total and of each stage. Each resume is then
parsed a second time through the parse cache to measure a cache hit. The cache is Redis when
`--redis-url` (or REDIS_URL) is reachable, otherwise in-memory, and the report says which.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from redis.asyncio import Redis

from eval.parsing import RESUME_EXTS, git_sha
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.parsing.cache import InMemoryParseCache, ParseCache, RedisParseCache
from talentgraph.config import get_settings
from talentgraph.llm.client import get_llm
from talentgraph.llm.fake import FakeLLM
from talentgraph.observability.logging import configure_logging

ROOT = Path(__file__).resolve().parent.parent


def percentiles(values: list[int]) -> dict[str, int]:
    if not values:
        return {}
    v = sorted(values)

    def pct(q: float) -> int:
        return v[min(len(v) - 1, round(q * (len(v) - 1)))]

    return {"p50": pct(0.5), "p95": pct(0.95), "p99": pct(0.99), "max": v[-1], "n": len(v)}


async def _cache(redis_url: str) -> tuple[ParseCache, str]:
    redis = Redis.from_url(redis_url, socket_connect_timeout=2)
    try:
        await redis.ping()
    except Exception:
        await redis.aclose()
        return InMemoryParseCache(), "in-memory (Redis unreachable)"
    await redis.flushdb()  # a fresh DB so the first parse of each resume is a miss
    return RedisParseCache(redis, ttl_s=3600), f"redis ({redis_url})"


async def run_parser(files: list[Path], *, fake: bool, redis_url: str) -> dict[str, Any]:
    settings = get_settings()
    llm = (
        FakeLLM(settings.fixtures_dir)
        if fake
        else get_llm(settings.model_copy(update={"llm_mode": "real"}))
    )
    cache, cache_kind = await _cache(redis_url)
    agent = ParsingAgent(settings, llm=llm, cache=cache)
    totals: list[int] = []
    stages: dict[str, list[int]] = {}
    hits: list[int] = []
    statuses: dict[str, int] = {}
    for i, path in enumerate(files, 1):
        data = path.read_bytes()
        result = await agent.parse(data, path.name)
        statuses[result.status] = statuses.get(result.status, 0) + 1
        totals.append(result.latency_ms)
        for stage, ms in result.timings_ms.items():
            stages.setdefault(stage, []).append(ms)
        start = time.perf_counter()
        again = await agent.parse(data, path.name)
        hit_ms = int((time.perf_counter() - start) * 1000)
        if again.cached:
            hits.append(hit_ms)
        print(
            f"[{i}/{len(files)}] {path.name}: {result.latency_ms} ms {result.status} "
            f"(cache {'hit' if again.cached else 'miss'} {hit_ms} ms)",
            file=sys.stderr,
            flush=True,
        )
    return {
        "target": "parser",
        "llm": "fake" if fake else f"real ({settings.llm_model})",
        "cache": cache_kind,
        "statuses": statuses,
        "total_ms": percentiles(totals),
        "stages_ms": {k: percentiles(v) for k, v in stages.items()},
        "cache_hit_ms": percentiles(hits),
    }


def from_records(n: int) -> dict[str, Any]:
    """Sequential real-API parse latencies collected by the daily recording runs.

    On the free tier (20 requests/day) a dedicated 20-call latency run would cost a day of
    quota, so 2-F uses the first `n` successful real calls the daily runs already made: each is
    a sequential parse of a val resume, timed without the pacing waits between calls.
    """
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "reports").glob("record_daily_val_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows += [
            {**r, "run": path.name} for r in data["rows"] if r["called_api"] and r["status"] == "ok"
        ]
    rows = rows[:n]
    return {
        "source": "reports/record_daily_val_*.json",
        "resumes": [r["file"] for r in rows],
        "total_ms": percentiles([r["latency_ms"] for r in rows]),
        "llm_ms": percentiles([r["timings_ms"].get("llm", 0) for r in rows]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sequential latency measurement (M6, 2-F).")
    ap.add_argument("--target", choices=("parser",), default="parser")
    ap.add_argument("--split", default="val")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--fake", action="store_true", help="FakeLLM fixtures instead of Gemini")
    ap.add_argument("--redis-url", default=None)
    ap.add_argument(
        "--from-records",
        action="store_true",
        help="real-call latencies from reports/record_daily_val_*.json (free-tier runs)",
    )
    ap.add_argument("--out", type=Path, default=ROOT / "reports")
    args = ap.parse_args()
    configure_logging("WARNING")

    folder = ROOT / "data" / "resumes" / args.split
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in RESUME_EXTS)[: args.n]
    redis_url = args.redis_url or get_settings().redis_url
    report = asyncio.run(run_parser(files, fake=args.fake, redis_url=redis_url))
    if args.from_records:
        report["real_api"] = from_records(args.n)
    report.update(
        split=args.split,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        git_sha=git_sha(),
    )
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"latency_{args.target}_{args.split}_{stamp}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
