"""Step 3.9: Normalization evaluation on the gold set (M2, M9).

Evaluates the Normalization cascade against data/eval/normalization_gold.csv:
- Computes Precision, Recall, F1 overall and per case_type.
- Checks Exit Criterion 3-B (M2 on test: Precision >= 0.90, Recall >= 0.85).
- Generates JSON and Markdown evaluation reports.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

from talentgraph.agents.normalization.cascade import CascadeResult, SkillCascade
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.embeddings.skill_index import get_skill_index

ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = ROOT / "data" / "eval" / "normalization_gold.csv"
REPORTS_DIR = ROOT / "reports"


def evaluate_split(
    cascade: SkillCascade,
    split: str = "val",
    gold_path: Path = GOLD_PATH,
) -> dict[str, Any]:
    """Run normalization evaluation on a split of normalization_gold.csv."""
    with gold_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    rows = all_rows if split == "all" else [r for r in all_rows if r.get("split") == split]

    if not rows:
        raise ValueError(f"No rows found in {gold_path} for split '{split}'")

    start_time = time.perf_counter()

    tp_total = 0
    fp_total = 0
    fn_total = 0

    case_type_counts: dict[str, dict[str, int]] = {}
    method_counts: dict[str, int] = {
        "exact": 0,
        "fuzzy": 0,
        "embedding": 0,
        "llm": 0,
        "fallback": 0,
        "unrecognized": 0,
    }
    errors: list[dict[str, Any]] = []

    for row in rows:
        raw = row["raw"]
        ctx = row.get("context")
        expected_raw = row["expected_slug"]
        case_type = row.get("case_type", "alias")

        if case_type not in case_type_counts:
            case_type_counts[case_type] = {"tp": 0, "fp": 0, "fn": 0, "total": 0}
        case_type_counts[case_type]["total"] += 1

        is_new = expected_raw == "NEW" or not expected_raw
        expected_slugs = (
            set() if is_new else {s.strip() for s in expected_raw.split("|") if s.strip()}
        )

        results: list[CascadeResult] = cascade.normalize_one_sync(raw, context=ctx)

        for res in results:
            method_counts[res.method] = method_counts.get(res.method, 0) + 1

        predicted_slugs = {res.canonical.slug for res in results if res.canonical is not None}

        tp = len(expected_slugs & predicted_slugs)
        fp = len(predicted_slugs - expected_slugs)
        fn = len(expected_slugs - predicted_slugs)

        tp_total += tp
        fp_total += fp
        fn_total += fn

        case_type_counts[case_type]["tp"] += tp
        case_type_counts[case_type]["fp"] += fp
        case_type_counts[case_type]["fn"] += fn

        if fp > 0 or fn > 0:
            errors.append(
                {
                    "raw": raw,
                    "context": ctx,
                    "expected": expected_raw,
                    "predicted": sorted(list(predicted_slugs)),
                    "case_type": case_type,
                    "is_hard_case": row.get("is_hard_case") == "True",
                    "methods": [res.method for res in results],
                }
            )

    elapsed_s = time.perf_counter() - start_time
    total_eval_mentions = len(rows)
    ms_per_mention = (
        round((elapsed_s / total_eval_mentions) * 1000, 2) if total_eval_mentions else 0.0
    )

    precision = round(tp_total / (tp_total + fp_total), 4) if (tp_total + fp_total) > 0 else 0.0
    recall = round(tp_total / (tp_total + fn_total), 4) if (tp_total + fn_total) > 0 else 0.0
    f1 = (
        round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0
    )

    by_case_type: dict[str, dict[str, Any]] = {}
    for ct, counts in sorted(case_type_counts.items()):
        ct_tp = counts["tp"]
        ct_fp = counts["fp"]
        ct_fn = counts["fn"]
        ct_p = round(ct_tp / (ct_tp + ct_fp), 4) if (ct_tp + ct_fp) > 0 else 0.0
        ct_r = round(ct_tp / (ct_tp + ct_fn), 4) if (ct_tp + ct_fn) > 0 else 0.0
        ct_f1 = round(2 * ct_p * ct_r / (ct_p + ct_r), 4) if (ct_p + ct_r) > 0 else 0.0
        by_case_type[ct] = {
            "total": counts["total"],
            "tp": ct_tp,
            "fp": ct_fp,
            "fn": ct_fn,
            "precision": ct_p,
            "recall": ct_r,
            "f1": ct_f1,
        }

    return {
        "split": split,
        "total_mentions": total_eval_mentions,
        "elapsed_seconds": round(elapsed_s, 2),
        "ms_per_mention": ms_per_mention,
        "tp": tp_total,
        "fp": fp_total,
        "fn": fn_total,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "by_case_type": by_case_type,
        "cascade_methods": method_counts,
        "error_count": len(errors),
        "worst_errors": errors[:25],
    }


def format_markdown_report(report: dict[str, Any], model_name: str = "base") -> str:
    """Format evaluation results as a GitHub markdown table."""
    lines: list[str] = [
        f"# Normalization Evaluation Report ({report['split'].upper()} Split)",
        "",
        f"- **Model:** `{model_name}`",
        f"- **Timestamp:** `{datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"- **Mentions evaluated:** {report['total_mentions']}",
        f"- **Latency:** {report['ms_per_mention']} ms/item ({report['elapsed_seconds']}s total)",
        "",
        "## Overall Metrics (M2)",
        "",
        "| Metric | Result | Target (Test) | Status |",
        "|---|---|---|---|",
        (
            f"| **Precision** | **{report['precision']:.4f}** | >= 0.9000 | "
            f"{'[PASS]' if report['precision'] >= 0.90 else '[FAIL]'} |"
        ),
        (
            f"| **Recall** | **{report['recall']:.4f}** | >= 0.8500 | "
            f"{'[PASS]' if report['recall'] >= 0.85 else '[FAIL]'} |"
        ),
        (
            f"| **F1 Score** | **{report['f1']:.4f}** | n/a | "
            f"{'[PASS]' if report['f1'] >= 0.88 else '[WARN]'} |"
        ),
        "",
        "## Breakdown by Case Type",
        "",
        "| Case Type | Mentions | Precision | Recall | F1 | Errors (FP+FN) |",
        "|---|---|---|---|---|---|",
    ]

    for ct, data in report["by_case_type"].items():
        errs = data["fp"] + data["fn"]
        lines.append(
            f"| `{ct}` | {data['total']} | {data['precision']:.4f} | "
            f"{data['recall']:.4f} | {data['f1']:.4f} | {errs} |"
        )

    lines.extend(
        [
            "",
            "## Cascade Step Attribution",
            "",
            "| Step | Method | Accepted Count | Share |",
            "|---|---|---|---|",
        ]
    )

    total_accepted = sum(report["cascade_methods"].values()) or 1
    for method, count in report["cascade_methods"].items():
        share = count / total_accepted * 100
        lines.append(f"| {method} | `{method}` | {count} | {share:.1f}% |")

    if report["worst_errors"]:
        lines.extend(
            [
                "",
                "## Sample Errors (Top 15)",
                "",
                "| Raw | Expected | Predicted | Case Type | Methods |",
                "|---|---|---|---|---|",
            ]
        )
        for err in report["worst_errors"][:15]:
            pred_str = ", ".join(err["predicted"]) if err["predicted"] else "*(unrecognized)*"
            methods_str = ", ".join(err["methods"])
            lines.append(
                f"| `{err['raw']}` | `{err['expected']}` | `{pred_str}` | "
                f"`{err['case_type']}` | `{methods_str}` |"
            )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate skill normalization (M2).")
    parser.add_argument("--split", choices=["val", "test", "all"], default="val")
    parser.add_argument("--model", type=str, default="base", help="Model name or path")
    parser.add_argument("--gold", type=Path, default=GOLD_PATH)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args()

    repo = get_taxonomy_repository()
    index = get_skill_index()
    cascade = SkillCascade(repo=repo, skill_index=index, llm=None)

    report = evaluate_split(cascade, split=args.split, gold_path=args.gold)
    md_content = format_markdown_report(report, model_name=args.model)

    print(md_content)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_json_path = args.report or (REPORTS_DIR / f"normalization_{args.split}_{timestamp}.json")
    report_md_path = args.out_md or (REPORTS_DIR / f"normalization_{args.split}_{timestamp}.md")

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.write_text(md_content, encoding="utf-8")

    print(f"\nSaved JSON report: {report_json_path}")
    print(f"Saved Markdown report: {report_md_path}")

    # Check exit criteria if evaluating test split
    if args.split == "test":
        if report["precision"] < 0.90 or report["recall"] < 0.85:
            print(f"\n❌ Exit Criterion 3-B FAILED: P={report['precision']}, R={report['recall']}")
            sys.exit(1)
        else:
            print(f"\n✅ Exit Criterion 3-B PASSED: P={report['precision']}, R={report['recall']}")


if __name__ == "__main__":
    main()
