"""Step 6.3: precision@10 of natural-language search on the query gold set (Metric M10, Exit Criterion 6-A)."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from talentgraph.agents.search.agent import SearchAgent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval_search")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
EVAL_DIR = DATA_DIR / "eval"
REPORTS_DIR = ROOT / "reports"
GOLD_FILE = EVAL_DIR / "search_gold.json"


async def evaluate_search(
    gold_file: Path = GOLD_FILE,
    k: int = 10,
    use_llm: bool = False,
    reports_dir: Path = REPORTS_DIR,
) -> dict[str, Any]:
    """Run search precision evaluation across gold queries."""
    if not gold_file.exists():
        raise FileNotFoundError(f"Gold evaluation file not found at {gold_file}")

    gold_data: list[dict[str, Any]] = json.loads(gold_file.read_text(encoding="utf-8"))
    logger.info("Loaded %d queries from %s", len(gold_data), gold_file)

    agent = SearchAgent(enable_llm=use_llm)

    results: list[dict[str, Any]] = []
    precisions: list[float] = []
    reciprocal_ranks: list[float] = []

    for item in gold_data:
        qid = item["id"]
        query = item["query"]
        relevant_ids = set(item.get("relevant_candidates", []))

        # Execute search
        plan, hits, plan_used_llm = await agent.search(query, limit=k)

        retrieved_ids = [h.candidate_id for h in hits[:k]]
        relevant_retrieved = [cid for cid in retrieved_ids if cid in relevant_ids]

        p_at_k = len(relevant_retrieved) / k if k > 0 else 0.0
        precisions.append(p_at_k)

        # Reciprocal rank (1 / position of first relevant hit)
        rr = 0.0
        for rank, cid in enumerate(retrieved_ids, 1):
            if cid in relevant_ids:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        results.append(
            {
                "id": qid,
                "query": query,
                "relevant_count": len(relevant_ids),
                "retrieved_count": len(retrieved_ids),
                "relevant_retrieved": len(relevant_retrieved),
                "precision_at_10": round(p_at_k, 4),
                "reciprocal_rank": round(rr, 4),
                "top_candidate": retrieved_ids[0] if retrieved_ids else None,
                "top_score": hits[0].score if hits else 0.0,
                "plan_used_llm": plan_used_llm,
            }
        )
        logger.info(
            "Query %s: P@10 = %.2f | Found %d/%d relevant in top %d",
            qid,
            p_at_k,
            len(relevant_retrieved),
            len(relevant_ids),
            k,
        )

    mean_precision = sum(precisions) / len(precisions) if precisions else 0.0
    mean_rr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    summary = {
        "timestamp": timestamp,
        "metric": "M10",
        "name": "search_precision_at_10",
        "num_queries": len(gold_data),
        "mean_precision_at_10": round(mean_precision, 4),
        "mean_reciprocal_rank": round(mean_rr, 4),
        "pass_condition": "Precision@10 >= 0.70",
        "passed": mean_precision >= 0.70,
        "use_llm": use_llm,
        "queries": results,
    }

    # Save JSON report
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"search_precision_{timestamp}.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Saved JSON report to %s", json_path)

    # Save Markdown report
    md_path = reports_dir / f"search_precision_{timestamp}.md"
    md_content = _build_markdown_report(summary)
    md_path.write_text(md_content, encoding="utf-8")
    logger.info("Saved Markdown report to %s", md_path)

    return summary


def _build_markdown_report(summary: dict[str, Any]) -> str:
    status_emoji = "✅ PASS" if summary["passed"] else "❌ FAIL"
    lines = [
        "# Milestone 6 Search Precision Evaluation (Metric M10)",
        "",
        f"- **Date:** {summary['timestamp']}",
        "- **Metric:** M10 (Precision@10 on Search Gold Set)",
        "- **Exit Criterion 6-A:** Precision@10 >= 0.70",
        f"- **Mean Precision@10:** **{summary['mean_precision_at_10']:.4f}**",
        f"- **Mean Reciprocal Rank (MRR):** **{summary['mean_reciprocal_rank']:.4f}**",
        f"- **Status:** {status_emoji}",
        "",
        "## Query Results Breakdown",
        "",
        "| Query ID | Query Text | Relevant Count | Top Hit | P@10 | Reciprocal Rank |",
        "|---|---|---|---|---|---|",
    ]
    for q in summary["queries"]:
        top = q["top_candidate"] or "N/A"
        lines.append(
            f"| {q['id']} | {q['query']} | {q['relevant_count']} | {top} | {q['precision_at_10']:.2f} | {q['reciprocal_rank']:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate search Precision@10")
    parser.add_argument("--gold", type=Path, default=GOLD_FILE, help="Path to gold dataset")
    parser.add_argument("--use-llm", action="store_true", help="Use real LLM planner if available")
    parser.add_argument("--k", type=int, default=10, help="Cutoff k for Precision@k")
    args = parser.parse_args()

    summary = asyncio.run(evaluate_search(gold_file=args.gold, k=args.k, use_llm=args.use_llm))
    print("\n==========================================")
    print(f"Mean Precision@10: {summary['mean_precision_at_10']:.4f}")
    print(f"Mean Reciprocal Rank: {summary['mean_reciprocal_rank']:.4f}")
    print(f"Pass Condition (>= 0.70): {'PASSED' if summary['passed'] else 'FAILED'}")
    print("==========================================\n")

    if not summary["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
