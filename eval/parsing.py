"""Step 2.13: field-level P/R/F1 and hallucination rate for the Parsing Agent (M1, M7).

    uv run python -m eval.parsing --split val                    # FakeLLM fixtures (offline)
    uv run python -m eval.parsing --split val --llm record       # replay fixtures, record misses
    uv run python -m eval.parsing --dir data/private/real_resumes --private   # ADR-0004 B

**Scoring (micro F1).** Every ground-truth value is one field. A predicted value that matches is a
TP; a wrong value is an FP and an FN; a missing value is an FN; a value with no ground truth is
an FP. List entities (experience, education, certifications, projects) are aligned in order by
their key fields before their fields are compared; unmatched entities count all their fields.

**What "matches" means.** The rendered resumes contain ~1% injected typos and sometimes print
only the year of a date, while the ground truth is clean. So text matches at rapidfuzz ratio
≥ 85 after case/space normalization; e-mails exactly (case-insensitive); phones by digits; URLs
ignoring scheme and "www."; dates by year, and by month when both sides have one.

**Not scored**, because the resume does not contain them: `location.country`,
`experience.skills_mentioned` (ground truth lists skills the bullets don't name),
`duration_months` (derived), certification `expires`, skill canonical slugs.

**Hallucination rate (M7)** = LLM fields whose evidence was not found ÷ LLM fields checked. Text
copied by line reference is grounded by construction and not counted; references to lines that
do not exist count as unverified.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.parsing.verify import iter_grounded
from talentgraph.config import get_settings
from talentgraph.core.schemas.resume import Extracted, ParsedResume
from talentgraph.llm.client import LLMClient, get_llm
from talentgraph.llm.fake import FakeLLM
from talentgraph.llm.recording import RecordingLLM
from talentgraph.observability.logging import configure_logging

ROOT = Path(__file__).resolve().parent.parent
RESUME_EXTS = (".pdf", ".docx", ".txt")
TEXT_MIN = 85
ALIGN_MIN = 60
CONTACT_FIELDS = ("personal.name", "personal.email", "personal.phone")

# -------------------------------------------------------------------------------------------------
# Value comparison
# -------------------------------------------------------------------------------------------------


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w@.+#&/%-]", " ", text.casefold()).split())


def same_text(a: str, b: str) -> bool:
    return fuzz.ratio(_norm(a), _norm(b)) >= TEXT_MIN


def same_email(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def same_phone(a: str, b: str) -> bool:
    return re.sub(r"\D", "", a) == re.sub(r"\D", "", b)


def _url_key(url: str) -> str:
    return re.sub(r"^(https?://)?(www\.)?", "", url.strip().lower()).rstrip("/")


def same_url(a: str, b: str) -> bool:
    return _url_key(a) == _url_key(b)


def same_date(a: str, b: str) -> bool:
    ya, _, ma = a.strip().partition("-")
    yb, _, mb = b.strip().partition("-")
    return ya == yb and (not ma or not mb or int(ma) == int(mb))


def _val(x: Any) -> Any:
    """Unwrap `Extracted` (and gold dicts) to the raw value."""
    if isinstance(x, Extracted):
        return x.value
    return x


# -------------------------------------------------------------------------------------------------
# Counting
# -------------------------------------------------------------------------------------------------


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def add(self, other: Counts) -> None:
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
        }


@dataclass
class DocScore:
    fields: dict[str, Counts] = field(default_factory=lambda: defaultdict(Counts))
    errors: list[str] = field(default_factory=list)

    def scalar(self, name: str, gold: Any, pred: Any, same: Callable[[str, str], bool]) -> None:
        g, p = _val(gold), _val(pred)
        g = g if g not in ("", None) else None
        p = p if p not in ("", None) else None
        c = self.fields[name]
        if g is None and p is None:
            return
        if g is None:
            c.fp += 1
        elif p is None:
            c.fn += 1
            self.errors.append(f"{name}: missed {g!r}")
        elif same(str(g), str(p)):
            c.tp += 1
        else:
            c.fp += 1
            c.fn += 1
            self.errors.append(f"{name}: {p!r} != {g!r}")

    def boolean(self, name: str, gold: bool, pred: bool) -> None:
        c = self.fields[name]
        if gold == pred:
            c.tp += 1
        else:
            c.fp += 1
            c.fn += 1
            self.errors.append(f"{name}: {pred} != {gold}")

    def bag(self, name: str, gold: Sequence[str], pred: Sequence[str], same: Any) -> None:
        """Unordered set comparison with greedy one-to-one matching."""
        c = self.fields[name]
        unmatched = list(pred)
        for g in gold:
            hit = next((p for p in unmatched if same(g, p)), None)
            if hit is None:
                c.fn += 1
                self.errors.append(f"{name}: missed {g!r}")
            else:
                c.tp += 1
                unmatched.remove(hit)
        c.fp += len(unmatched)
        self.errors.extend(f"{name}: extra {p!r}" for p in unmatched)

    def sequence(self, name: str, gold: Sequence[str], pred: Sequence[str]) -> None:
        """Ordered text lists (bullets), aligned in order."""
        pairs = align(gold, pred, lambda g, p: float(fuzz.ratio(_norm(g), _norm(p))))
        c = self.fields[name]
        for gi, pi in pairs:
            if gi is not None and pi is not None and same_text(gold[gi], pred[pi]):
                c.tp += 1
            else:
                if gi is not None:
                    c.fn += 1
                if pi is not None:
                    c.fp += 1


def align[G, P](
    gold: Sequence[G], pred: Sequence[P], sim: Callable[[G, P], float]
) -> list[tuple[int | None, int | None]]:
    """Order-preserving alignment maximizing total similarity (pairs need sim ≥ ALIGN_MIN)."""
    n, m = len(gold), len(pred)
    scores = [[sim(g, p) for p in pred] for g in gold]
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            pair = scores[i][j] + best[i + 1][j + 1] if scores[i][j] >= ALIGN_MIN else -1.0
            best[i][j] = max(pair, best[i + 1][j], best[i][j + 1])
    out: list[tuple[int | None, int | None]] = []
    i = j = 0
    while i < n and j < m:
        if scores[i][j] >= ALIGN_MIN and best[i][j] == scores[i][j] + best[i + 1][j + 1]:
            out.append((i, j))
            i, j = i + 1, j + 1
        elif best[i][j] == best[i + 1][j]:
            out.append((i, None))
            i += 1
        else:
            out.append((None, j))
            j += 1
    out.extend((k, None) for k in range(i, n))
    out.extend((None, k) for k in range(j, m))
    return out


# -------------------------------------------------------------------------------------------------
# Scoring one resume
# -------------------------------------------------------------------------------------------------


def _key_sim(*names: str) -> Callable[[Any, Any], float]:
    def sim(g: Any, p: Any) -> float:
        gk = " ".join(str(_val(getattr(g, n)) or "") for n in names)
        pk = " ".join(str(_val(getattr(p, n)) or "") for n in names)
        return float(fuzz.ratio(_norm(gk), _norm(pk)))

    return sim


def score_resume(gold: ParsedResume, pred: ParsedResume) -> DocScore:
    s = DocScore()
    gp, pp = gold.personal, pred.personal
    s.scalar("personal.name", gp.name, pp.name, same_text)
    s.scalar("personal.email", gp.email, pp.email, same_email)
    s.scalar("personal.phone", gp.phone, pp.phone, same_phone)
    gl = gp.location.value if gp.location else None
    pl = pp.location.value if pp.location else None
    s.scalar("personal.city", gl.city if gl else None, pl.city if pl else None, same_text)
    s.scalar("personal.region", gl.region if gl else None, pl.region if pl else None, same_text)
    s.bag("personal.links", [x.value for x in gp.links], [x.value for x in pp.links], same_url)
    s.scalar("summary", gold.summary, pred.summary, same_text)

    for gi, pi in align(gold.experience, pred.experience, _key_sim("title", "company")):
        g = gold.experience[gi] if gi is not None else None
        p = pred.experience[pi] if pi is not None else None
        for f, same in (
            ("title", same_text),
            ("company", same_text),
            ("location", same_text),
            ("start", same_date),
            ("end", same_date),
        ):
            s.scalar(f"experience.{f}", getattr(g, f, None), getattr(p, f, None), same)
        if g is not None and p is not None:
            s.boolean("experience.is_current", g.is_current, p.is_current)
        elif g is not None:
            s.fields["experience.is_current"].fn += 1
        else:
            s.fields["experience.is_current"].fp += 1
        s.sequence(
            "experience.responsibilities",
            [b.value for b in g.responsibilities] if g else [],
            [b.value for b in p.responsibilities] if p else [],
        )

    for gi, pi in align(gold.education, pred.education, _key_sim("institution", "degree")):
        g = gold.education[gi] if gi is not None else None
        p = pred.education[pi] if pi is not None else None
        for f, same in (
            ("institution", same_text),
            ("degree", same_text),
            ("field", same_text),
            ("start", same_date),
            ("end", same_date),
            ("grade", same_text),
        ):
            s.scalar(f"education.{f}", getattr(g, f, None), getattr(p, f, None), same)

    s.bag("skills", [x.raw for x in gold.skills], [x.raw for x in pred.skills], same_text)

    for gi, pi in align(gold.certifications, pred.certifications, _key_sim("name")):
        g = gold.certifications[gi] if gi is not None else None
        p = pred.certifications[pi] if pi is not None else None
        for f, same in (
            ("name", same_text),
            ("issuer", same_text),
            ("date", same_date),
            ("credential_id", same_text),
        ):
            s.scalar(f"certifications.{f}", getattr(g, f, None), getattr(p, f, None), same)

    for gi, pi in align(gold.projects, pred.projects, _key_sim("name")):
        g = gold.projects[gi] if gi is not None else None
        p = pred.projects[pi] if pi is not None else None
        for f, same in (("name", same_text), ("description", same_text), ("url", same_url)):
            s.scalar(f"projects.{f}", getattr(g, f, None), getattr(p, f, None), same)
        s.bag(
            "projects.technologies",
            g.technologies if g else [],
            p.technologies if p else [],
            same_text,
        )
    return s


# -------------------------------------------------------------------------------------------------
# Running over a directory
# -------------------------------------------------------------------------------------------------


@dataclass
class EvalResult:
    overall: Counts = field(default_factory=Counts)
    by_field: dict[str, Counts] = field(default_factory=lambda: defaultdict(Counts))
    by_group: dict[str, Counts] = field(default_factory=lambda: defaultdict(Counts))
    llm_checked: int = 0
    llm_unverified: int = 0
    unverified_examples: list[str] = field(default_factory=list)
    statuses: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latencies_ms: list[int] = field(default_factory=list)
    worst: list[tuple[float, str, list[str]]] = field(default_factory=list)
    docs: int = 0

    @property
    def hallucination_rate(self) -> float:
        return self.llm_unverified / self.llm_checked if self.llm_checked else 0.0

    def contact_f1(self) -> Counts:
        c = Counts()
        for f in CONTACT_FIELDS:
            c.add(self.by_field[f])
        return c


def find_resumes(folder: Path, ids: set[str] | None, limit: int | None) -> list[Path]:
    files = sorted(
        p
        for p in folder.iterdir()
        if p.suffix.lower() in RESUME_EXTS and p.with_name(p.stem + ".gt.json").is_file()
    )
    if ids:
        files = [p for p in files if p.stem in ids]
    return files[:limit] if limit else files


async def evaluate(files: list[Path], agent: ParsingAgent, *, progress: bool = True) -> EvalResult:
    result = EvalResult()
    for i, path in enumerate(files, 1):
        gold_raw = json.loads(path.with_name(path.stem + ".gt.json").read_text(encoding="utf-8"))
        gold = ParsedResume.model_validate(gold_raw)
        parsed = await agent.parse(path.read_bytes(), path.name)
        doc = score_resume(gold, parsed.resume)
        meta = gold_raw.get("meta", {})
        groups = [f"format:{path.suffix.lstrip('.')}"]
        if meta.get("template"):
            groups.append(f"template:{meta['template']}")
        doc_counts = Counts()
        for name, c in doc.fields.items():
            result.by_field[name].add(c)
            doc_counts.add(c)
        result.overall.add(doc_counts)
        for g in groups:
            result.by_group[g].add(doc_counts)
        result.docs += 1
        result.statuses[parsed.status] += 1
        result.latencies_ms.append(parsed.latency_ms)
        result.llm_checked += parsed.resume.meta.llm_field_count
        result.llm_unverified += parsed.resume.meta.unverified_count
        for item in iter_grounded(parsed.resume):
            if item.verified is False and len(result.unverified_examples) < 25:
                result.unverified_examples.append(f"{path.name}: {item.evidence!r}")
        result.worst.append((doc_counts.f1, path.name, doc.errors[:12]))
        if progress:
            print(
                f"[{i}/{len(files)}] {path.name}: F1 {doc_counts.f1:.3f} "
                f"status={parsed.status} {parsed.latency_ms} ms",
                file=sys.stderr,
            )
    result.worst.sort()
    return result


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        )
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        return out.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def to_report(result: EvalResult, label: str, *, private: bool) -> dict[str, Any]:
    lat = sorted(result.latencies_ms)

    def pct(q: float) -> int:
        return lat[min(len(lat) - 1, int(q * len(lat)))] if lat else 0

    report: dict[str, Any] = {
        "label": label,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "docs": result.docs,
        "statuses": dict(result.statuses),
        "m1": {
            "overall": result.overall.as_dict(),
            "contact": {f: result.by_field[f].as_dict() for f in CONTACT_FIELDS},
        },
        "m7": {
            "hallucination_rate": round(result.hallucination_rate, 4),
            "llm_fields_checked": result.llm_checked,
            "llm_fields_unverified": result.llm_unverified,
        },
        "by_field": {k: v.as_dict() for k, v in sorted(result.by_field.items())},
        "by_group": {k: v.as_dict() for k, v in sorted(result.by_group.items())},
        "latency_ms": {"p50": pct(0.5), "p95": pct(0.95), "max": lat[-1] if lat else 0},
    }
    if not private:  # never write resume content from the private set (ADR-0004 B)
        report["unverified_examples"] = result.unverified_examples
        report["worst_docs"] = [
            {"file": name, "f1": round(f1, 4), "errors": errors}
            for f1, name, errors in result.worst[:10]
        ]
    return report


def to_markdown(report: dict[str, Any]) -> str:
    m1, m7 = report["m1"], report["m7"]
    lines = [
        f"# Parsing evaluation: {report['label']}",
        "",
        f"- Generated {report['generated_at']} at git `{report['git_sha']}`; "
        f"{report['docs']} resumes; statuses {report['statuses']}",
        f"- **M1 overall F1 {m1['overall']['f1']:.4f}** "
        f"(P {m1['overall']['precision']:.4f}, R {m1['overall']['recall']:.4f})",
        "- M1 contact F1: "
        + ", ".join(f"{k.split('.')[-1]} {v['f1']:.4f}" for k, v in m1["contact"].items()),
        f"- **M7 hallucination rate {m7['hallucination_rate']:.2%}** "
        f"({m7['llm_fields_unverified']} of {m7['llm_fields_checked']} LLM fields unverified)",
        f"- Latency p50 {report['latency_ms']['p50']} ms, p95 {report['latency_ms']['p95']} ms",
        "",
        "| Field | TP | FP | FN | P | R | F1 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, c in report["by_field"].items():
        lines.append(
            f"| {name} | {c['tp']} | {c['fp']} | {c['fn']} | {c['precision']:.3f} "
            f"| {c['recall']:.3f} | {c['f1']:.3f} |"
        )
    lines += ["", "| Group | F1 |", "|---|---|"]
    lines += [f"| {k} | {v['f1']:.4f} |" for k, v in report["by_group"].items()]
    if report.get("worst_docs"):
        lines += ["", "## Lowest-scoring resumes", ""]
        for d in report["worst_docs"][:5]:
            lines.append(f"- `{d['file']}` F1 {d['f1']:.3f}: " + "; ".join(d["errors"][:6]))
    return "\n".join(lines) + "\n"


def build_llm(mode: str, fixtures_dir: str, min_interval_s: float) -> LLMClient:
    settings = get_settings()
    if mode == "fake":
        return FakeLLM(fixtures_dir)
    real = get_llm(settings.model_copy(update={"llm_mode": "real"}))
    if mode == "record":
        return RecordingLLM(real, fixtures_dir, min_interval_s=min_interval_s)
    return real  # "real": always call the API, record nothing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--split", default="val", help="data/resumes/<split> (default: val)")
    src.add_argument("--dir", type=Path, help="any folder of resumes with .gt.json files")
    ap.add_argument("--llm", choices=("fake", "record", "real"), default="fake")
    ap.add_argument("--fixtures-dir", default=str(ROOT / "tests" / "fixtures" / "llm"))
    ap.add_argument("--min-interval", type=float, default=0.0, help="seconds between API calls")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", help="comma-separated file stems, e.g. candidate_0009,candidate_0016")
    ap.add_argument("--private", action="store_true", help="aggregate-only report (ADR-0004 B)")
    ap.add_argument("--out", type=Path, default=ROOT / "reports")
    ap.add_argument("--label", help="report name (default: the split or folder name)")
    args = ap.parse_args(argv)
    configure_logging("WARNING")  # per-resume parse logs would drown the progress lines

    folder = args.dir or ROOT / "data" / "resumes" / args.split
    label = args.label or (args.dir.name if args.dir else args.split)
    files = find_resumes(folder, set(args.ids.split(",")) if args.ids else None, args.limit)
    if not files:
        print(f"No resumes with ground truth in {folder}", file=sys.stderr)
        return 1
    agent = ParsingAgent(llm=build_llm(args.llm, args.fixtures_dir, args.min_interval))
    started = time.perf_counter()
    result = asyncio.run(evaluate(files, agent))
    report = to_report(result, label, private=args.private)
    report["llm_mode"] = args.llm
    report["wall_s"] = round(time.perf_counter() - started, 1)

    out_dir = args.out / "private" if args.private else args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = out_dir / f"parsing_{label}_{stamp}"
    base.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    base.with_suffix(".md").write_text(to_markdown(report), encoding="utf-8")
    print(to_markdown(report).split("\n| Field")[0])
    print(f"Wrote {base}.json/.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
