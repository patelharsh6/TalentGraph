"""Step 3.11: External benchmark evaluation (TechWolf, data_jobs, ADR-0004).

Evaluates the normalization agent on:
1. TechWolf skill spans crosswalked via ESCO to taxonomy slugs (reporting Precision & Recall).
2. lukebarousse/data_jobs real-world skill strings (reporting unrecognized rate).
Generates reports in reports/external_benchmarks_*.json and .md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from talentgraph.agents.normalization.cascade import SkillCascade
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.embeddings.skill_index import get_skill_index

ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_DIR = ROOT / "data" / "external"
RAW_DIR = EXTERNAL_DIR / "raw"
CROSSWALK_PATH = EXTERNAL_DIR / "esco_crosswalk.json"
REPORTS_DIR = ROOT / "reports"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def evaluate_external(cascade: SkillCascade, model_name: str = "base") -> dict[str, Any]:
    """Evaluate normalization on TechWolf crosswalk and data_jobs skill strings."""
    if not CROSSWALK_PATH.is_file():
        raise FileNotFoundError(
            f"Missing crosswalk file: {CROSSWALK_PATH}. Run scripts/fetch_external.py first."
        )

    crosswalk: dict[str, str] = json.loads(CROSSWALK_PATH.read_text(encoding="utf-8"))

    techwolf_file = RAW_DIR / "techwolf" / "benchmarks.json"
    if not techwolf_file.is_file():
        raise FileNotFoundError(f"Missing TechWolf benchmark file: {techwolf_file}")
    techwolf_items: list[dict[str, Any]] = json.loads(techwolf_file.read_text(encoding="utf-8"))

    data_jobs_file = RAW_DIR / "data_jobs" / "sample.json"
    if not data_jobs_file.is_file():
        raise FileNotFoundError(f"Missing data_jobs file: {data_jobs_file}")
    data_jobs_items: list[dict[str, Any]] = json.loads(data_jobs_file.read_text(encoding="utf-8"))

    # 1. TechWolf Evaluation
    total_spans = 0
    crosswalked_spans = 0
    tp = 0
    fp = 0
    fn = 0
    techwolf_details: list[dict[str, Any]] = []

    for item in techwolf_items:
        sentence = item["text"]
        for span_info in item["spans"]:
            total_spans += 1
            span_text = span_info["span"]
            esco_title = span_info["esco_title"]

            expected_slug = crosswalk.get(esco_title)
            if not expected_slug:
                # Omit spans without ESCO crosswalk mapping per ADR-0004
                continue

            crosswalked_spans += 1
            results = cascade.normalize_one_sync(span_text, context=sentence)
            predicted_slugs = [r.canonical.slug for r in results if r.canonical is not None]

            if expected_slug in predicted_slugs:
                tp += 1
            else:
                if predicted_slugs:
                    fp += 1
                else:
                    fn += 1

            techwolf_details.append(
                {
                    "span": span_text,
                    "esco_title": esco_title,
                    "expected": expected_slug,
                    "predicted": predicted_slugs,
                    "match": expected_slug in predicted_slugs,
                }
            )

    crosswalk_coverage = round(crosswalked_spans / total_spans, 4) if total_spans else 0.0
    precision = round(tp / (tp + fp), 4) if (tp + fp) else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) else 0.0

    # 2. data_jobs evaluation (unrecognized rate)
    total_data_job_skills = 0
    recognized_skills = 0
    unrecognized_skills = 0
    unrecognized_list: list[str] = []

    for job in data_jobs_items:
        job_title = job.get("job_title", "Job")
        for sk in job.get("skills", []):
            total_data_job_skills += 1
            results = cascade.normalize_one_sync(sk, context=f"Position: {job_title}")
            predicted_slugs = [r.canonical.slug for r in results if r.canonical is not None]
            if predicted_slugs:
                recognized_skills += 1
            else:
                unrecognized_skills += 1
                unrecognized_list.append(sk)

    unrecognized_rate = (
        round(unrecognized_skills / total_data_job_skills, 4) if total_data_job_skills else 0.0
    )

    return {
        "model": model_name,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "techwolf": {
            "total_spans": total_spans,
            "crosswalked_spans": crosswalked_spans,
            "coverage": crosswalk_coverage,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "data_jobs": {
            "total_skills": total_data_job_skills,
            "recognized_skills": recognized_skills,
            "unrecognized_skills": unrecognized_skills,
            "unrecognized_rate": unrecognized_rate,
            "unrecognized_samples": sorted(list(set(unrecognized_list))),
        },
    }


def format_external_markdown(report: dict[str, Any]) -> str:
    """Format external evaluation as a GitHub Markdown table."""
    tw = report["techwolf"]
    dj = report["data_jobs"]

    lines = [
        f"# External Benchmarks Evaluation Report ({report['model']})",
        "",
        f"- **Model:** `{report['model']}`",
        f"- **Timestamp:** `{report['timestamp']}`",
        "- **Reference:** ADR-0004 (TechWolf & lukebarousse/data_jobs)",
        "",
        "## 1. TechWolf Skill Extraction Benchmark (ESCO Crosswalk)",
        "",
        "| Metric | Value | Note |",
        "|---|---|---|",
        f"| Total Spans | {tw['total_spans']} | Verified TechWolf sample |",
        f"| Crosswalked Spans | {tw['crosswalked_spans']} | Exact match to taxonomy |",
        f"| Crosswalk Coverage | {tw['coverage'] * 100:.1f}% | Covered by taxonomy aliases |",
        f"| **Precision** | **{tw['precision']:.4f}** | Normalized correct ÷ predicted |",
        f"| **Recall** | **{tw['recall']:.4f}** | Normalized correct ÷ crosswalked |",
        f"| **F1 Score** | **{tw['f1']:.4f}** | Harmonic mean |",
        "",
        "## 2. Real-World Job Postings Benchmark (`data_jobs`)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total Extracted Skills | {dj['total_skills']} |",
        f"| Recognized Skills | {dj['recognized_skills']} |",
        f"| Unrecognized Skills | {dj['unrecognized_skills']} |",
        f"| **Unrecognized Rate** | **{dj['unrecognized_rate'] * 100:.1f}%** |",
        "",
    ]
    if dj["unrecognized_samples"]:
        lines.append(f"Unrecognized terms observed: `{', '.join(dj['unrecognized_samples'])}`")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate external benchmarks (TechWolf, data_jobs)."
    )
    parser.add_argument("--model", type=str, default="base", help="Model name or identifier")
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args()

    repo = get_taxonomy_repository()
    index = get_skill_index()
    cascade = SkillCascade(repo=repo, skill_index=index, llm=None)

    report = evaluate_external(cascade, model_name=args.model)
    md_content = format_external_markdown(report)

    print(md_content)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_json = args.report or (
        REPORTS_DIR / f"external_benchmarks_{args.model}_{timestamp}.json"
    )
    report_md = args.out_md or (REPORTS_DIR / f"external_benchmarks_{args.model}_{timestamp}.md")

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md.write_text(md_content, encoding="utf-8")

    print(f"\nSaved external JSON report: {report_json}")
    print(f"Saved external Markdown report: {report_md}")


if __name__ == "__main__":
    main()
