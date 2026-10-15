"""Step 2.14: Gemini rewording of synthetic resume text, ground truth preserved (ADR-0004 A).

    uv run python scripts/reword_resumes.py                 # 50 val + 50 test profiles
    uv run python scripts/reword_resumes.py --render-only   # re-render from the checkpoints
    uv run python -m eval.parsing --dir data/resumes/val_reworded --llm record

The synthetic resumes all share a few template sentences, so a parser could look good just by
fitting them. This script has Gemini rewrite each selected resume's summary and experience
bullets (one call per resume) and renders the result with the original template and format into
`data/resumes/{val,test}_reworded/`, with a `.gt.json` whose summary and bullets are the reworded
text. Everything else (names, companies, titles, dates, skills) is unchanged and is checked:

- the same number of roles and bullets;
- every protected term (skills, companies, titles) and every number in an original sentence
  appears verbatim in its rewrite;
- the rewrite actually differs (rapidfuzz ratio < 90) for most sentences.

Resumes that fail validation are left out and listed. Responses are kept in
`data/.checkpoints/reword_llm/` (gitignored), so re-runs are free and resumable. Pass/fail
decisions are never made on this set; it is reported next to M1 (ADR-0004).
"""

import argparse
import asyncio
import copy
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_resumes as rr  # noqa: E402

from talentgraph.config import get_settings  # noqa: E402
from talentgraph.llm.client import get_llm  # noqa: E402
from talentgraph.llm.fake import FakeLLM  # noqa: E402
from talentgraph.llm.recording import RecordingLLM  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESUMES = ROOT / "data" / "resumes"
CHECKPOINTS = ROOT / "data" / ".checkpoints" / "reword_llm"
PROMPT = ROOT / "src" / "talentgraph" / "llm" / "prompts" / "reword_resume.md"
SEED = 2026
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?%?\+?")


class RewordedRole(BaseModel):
    bullets: list[str] = Field(default_factory=list)


class RewordedResume(BaseModel):
    summary: str | None = None
    experience: list[RewordedRole] = Field(default_factory=list)


def select(split: str, n: int) -> list[Path]:
    gts = sorted((RESUMES / split).glob("candidate_*.gt.json"))
    return sorted(random.Random(f"{SEED}:{split}").sample(gts, min(n, len(gts))))


def protected_terms(gt: dict[str, Any]) -> list[str]:
    terms = {s["raw"] for s in gt.get("skills", [])}
    for exp in gt.get("experience", []):
        terms.update(t for t in (exp.get("company"), exp.get("title")) if t)
    return sorted(terms, key=len, reverse=True)


def user_message(gt: dict[str, Any]) -> str:
    payload = {
        "summary": gt.get("summary"),
        "experience": [
            {"title": e["title"], "company": e["company"], "bullets": e["responsibilities"]}
            for e in gt.get("experience", [])
        ],
        "protected_terms": protected_terms(gt),
    }
    return json.dumps(payload, ensure_ascii=False, indent=1)


def validate(gt: dict[str, Any], out: RewordedResume) -> list[str]:
    problems: list[str] = []
    terms = protected_terms(gt)
    pairs: list[tuple[str, str]] = []
    if gt.get("summary"):
        if not out.summary:
            problems.append("summary missing")
        else:
            pairs.append((gt["summary"], out.summary))
    roles = gt.get("experience", [])
    if len(out.experience) != len(roles):
        return [*problems, f"{len(out.experience)} roles, expected {len(roles)}"]
    for i, (exp, new) in enumerate(zip(roles, out.experience, strict=True)):
        if len(new.bullets) != len(exp["responsibilities"]):
            problems.append(f"role {i}: {len(new.bullets)} bullets, expected original count")
            continue
        pairs.extend(zip(exp["responsibilities"], new.bullets, strict=True))
    unchanged = 0
    for old, new in pairs:
        for term in terms:
            if term in old and term not in new:
                problems.append(f"lost {term!r}")
        for number in NUMBER_RE.findall(old):
            if number not in new:
                problems.append(f"lost number {number!r}")
        if fuzz.ratio(old, new) >= 90:
            unchanged += 1
    if pairs and unchanged > len(pairs) / 2:
        problems.append(f"{unchanged}/{len(pairs)} sentences barely changed")
    return problems


def apply(gt: dict[str, Any], out: RewordedResume) -> dict[str, Any]:
    new = copy.deepcopy(gt)
    if gt.get("summary"):
        new["summary"] = out.summary
    for exp, role in zip(new.get("experience", []), out.experience, strict=True):
        exp["responsibilities"] = [b.strip() for b in role.bullets]
    new["meta"]["reworded"] = True
    return new


def render(gt: dict[str, Any], out_dir: Path, stem: str) -> None:
    meta = gt["meta"]
    noise = rr.Noise(random.Random(f"{SEED}:reword:{stem}"))
    doc = rr.build_document(gt, noise, list(rr.BODY_ORDER))
    out_doc = out_dir / f"{stem}.{meta['format']}"
    if meta["format"] == "pdf":
        rr.render_pdf(doc, meta["template"], out_doc)
    elif meta["format"] == "docx":
        rr.render_docx(doc, meta["template"], out_doc)
    else:
        rr.render_txt(doc, out_doc)
    (out_dir / f"{stem}.gt.json").write_text(
        json.dumps(gt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


async def reword_all(
    paths: list[Path],
    llm: RecordingLLM | None,
    *,
    max_calls: int | None = None,
    max_consecutive_failures: int = 3,
    failure_backoff_s: float = 90.0,
) -> dict[str, list[str]]:
    """Reword and render each resume; `rejected` maps left-out stems to the reasons.

    `max_calls` caps real API calls (checkpointed responses replay for free); a resume skipped
    for budget or an API error is reported as "pending" and picked up by the next run.
    """
    system = PROMPT.read_text(encoding="utf-8")
    rejected: dict[str, list[str]] = {}
    consecutive = 0
    for i, gt_path in enumerate(paths, 1):
        stem = gt_path.name.removesuffix(".gt.json")
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        user = user_message(gt)
        cached = CHECKPOINTS / "RewordedResume" / f"{FakeLLM.fixture_key(system, user)}.json"
        if llm is None or cached.is_file():  # replay the checkpoint (no API call)
            if not cached.is_file():
                rejected[stem] = ["pending: no checkpoint"]
                continue
            out = RewordedResume.model_validate_json(cached.read_text(encoding="utf-8"))
        else:
            calls = llm.recorded + llm.failed
            if max_calls is not None and calls >= max_calls:
                rejected[stem] = ["pending: call budget reached"]
                continue
            if consecutive >= max_consecutive_failures:
                rejected[stem] = ["pending: stopped after repeated API errors"]
                continue
            if consecutive:
                await asyncio.sleep(failure_backoff_s)
            try:
                out = await llm.extract(RewordedResume, system, user)
                consecutive = 0
            except Exception as exc:  # quota or API error: report it and keep going
                consecutive += 1
                rejected[stem] = [f"pending: LLM error: {exc}"[:200]]
                print(f"[{i}/{len(paths)}] {stem}: LLM error", flush=True)
                continue
        problems = validate(gt, out)
        if problems:
            rejected[stem] = problems
            print(f"[{i}/{len(paths)}] {stem}: rejected ({problems[0]})", flush=True)
            continue
        split = gt_path.parent.name
        out_dir = RESUMES / f"{split}_reworded"
        out_dir.mkdir(parents=True, exist_ok=True)
        render(apply(gt, out), out_dir, stem)
        print(f"[{i}/{len(paths)}] {stem}: ok", flush=True)
    return rejected


def make_llm(min_interval_s: float) -> RecordingLLM | None:
    """Gemini behind a checkpointing recorder: one attempt per call (each attempt is quota)."""
    settings = get_settings()
    if settings.gemini_api_key is None:
        return None
    real = get_llm(
        settings.model_copy(
            update={"llm_mode": "real", "llm_max_attempts": 1, "llm_timeout_s": 60.0}
        )
    )
    return RecordingLLM(real, CHECKPOINTS, min_interval_s=min_interval_s)


def main() -> int:
    ap = argparse.ArgumentParser(description="Reword val/test resumes with Gemini (ADR-0004 A).")
    ap.add_argument("--per-split", type=int, default=50)
    ap.add_argument("--splits", default="val,test")
    ap.add_argument("--render-only", action="store_true")
    ap.add_argument("--min-interval", type=float, default=15.0)
    ap.add_argument("--max-calls", type=int, default=18, help="API calls this run (20/day)")
    args = ap.parse_args()

    paths = [p for split in args.splits.split(",") for p in select(split, args.per_split)]
    llm: RecordingLLM | None = None
    if not args.render_only:
        llm = make_llm(args.min_interval)
        if llm is None:
            print("GEMINI_API_KEY is not set.", file=sys.stderr)
            return 2
    rejected = asyncio.run(reword_all(paths, llm, max_calls=args.max_calls))
    print(f"{len(paths) - len(rejected)} rendered, {len(rejected)} left out")
    for stem, problems in sorted(rejected.items()):
        print(f"  {stem}: {'; '.join(problems[:3])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
