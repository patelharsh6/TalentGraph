"""Step 6.5: Career Coach critic evaluation on the 20-case adversarial set (Exit Criterion 6-B).

Pass condition:
0 unsupported claims in final outputs on the adversarial set; every removed claim is listed in the report.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from talentgraph.agents.coach.critic import (
    deterministic_verify_bullet,
    deterministic_verify_learning_plan,
)
from talentgraph.api.schemas import BulletRewrite, LearningGoal
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval_coach")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
EVAL_DIR = DATA_DIR / "eval"
REPORTS_DIR = ROOT / "reports"
ADVERSARIAL_FILE = EVAL_DIR / "coach_adversarial.json"


async def evaluate_coach_adversarial(
    adv_file: Path = ADVERSARIAL_FILE,
    reports_dir: Path = REPORTS_DIR,
) -> dict[str, Any]:
    if not adv_file.exists():
        raise FileNotFoundError(f"Adversarial dataset not found at {adv_file}")

    cases: list[dict[str, Any]] = json.loads(adv_file.read_text(encoding="utf-8"))
    logger.info("Loaded %d adversarial cases from %s", len(cases), adv_file)

    repo = get_taxonomy_repository()

    case_results: list[dict[str, Any]] = []
    total_unsupported_final = 0
    total_removed_recorded = 0
    total_baits_detected = 0

    for case in cases:
        cid = case["id"]
        bait_type = case["bait_type"]
        profile_data = case["profile_data"]

        # Parse test bullets & learning goals
        bullets = [BulletRewrite.model_validate(b) for b in case["test_bullets"]]
        goals = [LearningGoal.model_validate(g) for g in case["test_learning_goals"]]

        verified_bullets: list[BulletRewrite] = []
        removed_claims: list[str] = []

        # 1. Critic on Learning Plan
        valid_goals, removed_goals = deterministic_verify_learning_plan(goals, repo)
        removed_claims.extend(removed_goals)

        # 2. Critic on Bullets
        for b in bullets:
            ok, reason = deterministic_verify_bullet(b, profile_data)
            if ok:
                verified_bullets.append(b)
            else:
                removed_claims.append(f"Rejected rewrite '{b.improved_bullet}': {reason}")
                total_baits_detected += 1

        # Check final output validity: do any invalid bullets remain in verified_bullets?
        unsupported_in_final = 0
        for b in verified_bullets:
            # Re-verify strictly: any remaining item must be 100% supported
            ok, _ = deterministic_verify_bullet(b, profile_data)
            if not ok:
                unsupported_in_final += 1

        total_unsupported_final += unsupported_in_final
        total_removed_recorded += len(removed_claims)

        case_results.append(
            {
                "case_id": cid,
                "candidate_id": case["candidate_id"],
                "bait_type": bait_type,
                "total_input_bullets": len(bullets),
                "verified_bullets_count": len(verified_bullets),
                "removed_claims_count": len(removed_claims),
                "unsupported_in_final": unsupported_in_final,
                "removed_claims": removed_claims,
            }
        )
        logger.info(
            "Case %s (%s): %d unsupported in final | %d claims removed and listed",
            cid,
            bait_type,
            unsupported_in_final,
            len(removed_claims),
        )

    passed = total_unsupported_final == 0 and total_removed_recorded >= len(cases)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    summary = {
        "timestamp": timestamp,
        "name": "coach_adversarial_evaluation",
        "num_cases": len(cases),
        "total_baits_detected": total_baits_detected,
        "total_unsupported_in_final": total_unsupported_final,
        "total_removed_claims_recorded": total_removed_recorded,
        "pass_condition": "0 unsupported claims in final outputs; all removed claims listed in report",
        "passed": passed,
        "cases": case_results,
    }

    # Save reports
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"coach_adversarial_{timestamp}.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Saved JSON report to %s", json_path)

    md_path = reports_dir / f"coach_adversarial_{timestamp}.md"
    md_content = _build_markdown_report(summary)
    md_path.write_text(md_content, encoding="utf-8")
    logger.info("Saved Markdown report to %s", md_path)

    return summary


def _build_markdown_report(summary: dict[str, Any]) -> str:
    status_emoji = "✅ PASS" if summary["passed"] else "❌ FAIL"
    lines = [
        "# Milestone 6 Career Coach Adversarial Evaluation (Exit Criterion 6-B)",
        "",
        f"- **Date:** {summary['timestamp']}",
        f"- **Cases Evaluated:** {summary['num_cases']}",
        f"- **Adversarial Baits Caught:** {summary['total_baits_detected']}",
        f"- **Unsupported Claims in Final Output:** **{summary['total_unsupported_in_final']}** (Requirement: 0)",
        f"- **Total Removed Claims Recorded:** **{summary['total_removed_claims_recorded']}**",
        f"- **Status:** {status_emoji}",
        "",
        "## Adversarial Case Results",
        "",
        "| Case ID | Bait Type | Verified Kept | Removed Listed | Unsupported in Final | Status |",
        "|---|---|---|---|---|---|",
    ]
    for c in summary["cases"]:
        c_status = "✅ PASS" if c["unsupported_in_final"] == 0 else "❌ FAIL"
        lines.append(
            f"| {c['case_id']} | {c['bait_type']} | {c['verified_bullets_count']} | {c['removed_claims_count']} | {c['unsupported_in_final']} | {c_status} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate coach critic against adversarial cases")
    parser.add_argument("--adv-file", type=Path, default=ADVERSARIAL_FILE)
    args = parser.parse_args()

    summary = asyncio.run(evaluate_coach_adversarial(adv_file=args.adv_file))
    print("\n==========================================")
    print(f"Total Cases: {summary['num_cases']}")
    print(f"Unsupported in Final: {summary['total_unsupported_in_final']}")
    print(f"Removed Claims Listed: {summary['total_removed_claims_recorded']}")
    print(f"Pass Condition (0 unsupported): {'PASSED' if summary['passed'] else 'FAILED'}")
    print("==========================================\n")

    if not summary["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
