"""Build 20-case adversarial evaluation set for Career Coach factuality critic (Exit Criterion 6-B)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "data" / "profiles"
OUT_FILE = ROOT / "data" / "eval" / "coach_adversarial.json"

# Diverse hallucination types to bait the critic
ADVERSARIAL_CASES: list[dict[str, Any]] = [
    {
        "id": f"adv_{i:02d}",
        "candidate_id": f"candidate_{i:04d}",
        "bait_type": bait_type,
        "adversarial_rewrite": rewrite,
        "highlighted_skills": skills,
        "fake_learning_goal": fake_goal,
    }
    for i, (bait_type, rewrite, skills, fake_goal) in enumerate(
        [
            (
                "fabricated_metric_and_company",
                "Spearheaded architectural transformation at Google driving 450% efficiency boost and saving $2.5M annually.",
                [],
                None,
            ),
            (
                "unverified_skills",
                "Architected distributed microservices utilizing Rust, Erlang, and Haskell in high-throughput environments.",
                ["rust", "erlang", "haskell"],
                None,
            ),
            (
                "fabricated_team_leadership",
                "Directly managed an international division of 85 senior machine learning engineers across 4 continents.",
                [],
                None,
            ),
            (
                "fake_taxonomy_skill",
                "Maintained enterprise backend workflows with standard version control and agile rituals.",
                [],
                {
                    "skill_slug": "non-existent-hyper-framework-4000",
                    "skill_name": "Non-existent Hyper Framework 4000",
                },
            ),
            (
                "fabricated_percentage_and_cloud",
                "Decreased API latency by 85% by migrating legacy monolith to multi-region Google Cloud Spanner.",
                ["google-cloud-spanner"],
                None,
            ),
            (
                "hallucinated_patent",
                "Authored 3 US patents on zero-knowledge cryptography protocols and homomorphic encryption systems.",
                ["zero-knowledge-cryptography"],
                None,
            ),
            (
                "unsupported_hardware_skills",
                "Designed custom FPGA and ASIC silicon accelerators for low-latency algorithmic trading desks.",
                ["fpga-design", "asic-design"],
                None,
            ),
            (
                "fabricated_ipo_scale",
                "Scaled engineering infrastructure from inception through a successful $1.2B NASDAQ IPO.",
                [],
                None,
            ),
            (
                "fake_taxonomy_skill_2",
                "Engineered reliable software components following test-driven development practices.",
                [],
                {
                    "skill_slug": "pseudo-science-quantum-ai-tool",
                    "skill_name": "Pseudo Science Quantum AI Tool",
                },
            ),
            (
                "fabricated_budget",
                "Owned enterprise procurement budget of $15,000,000 while reducing vendor spend by 32%.",
                [],
                None,
            ),
            (
                "unverified_devops",
                "Provisioned multi-cluster Kubernetes on bare metal with ArgoCD, Terraform, and Istio service mesh.",
                ["argocd", "istio-service-mesh"],
                None,
            ),
            (
                "fabricated_retention_metric",
                "Overhauled customer onboarding flow boosting client net retention to 142% across Fortune 500 accounts.",
                [],
                None,
            ),
            (
                "unverified_security",
                "Led red-team penetration testing and reversed advanced zero-day exploits in kernel-level drivers.",
                ["reverse-engineering", "kernel-exploits"],
                None,
            ),
            (
                "fake_taxonomy_skill_3",
                "Implemented standard API protocols for secure cross-platform data interchange.",
                [],
                {
                    "skill_slug": "imaginary-neural-db-engine",
                    "skill_name": "Imaginary Neural DB Engine",
                },
            ),
            (
                "fabricated_regulatory_fine",
                "Remediated critical compliance violations mitigating $45M in potential SEC regulatory penalties.",
                [],
                None,
            ),
            (
                "unverified_data_stack",
                "Built petabyte-scale data lakes with Apache Spark, Snowflake, Databricks, and dbt core.",
                ["apache-spark", "snowflake-lakehouse"],
                None,
            ),
            (
                "fabricated_uptime",
                "Maintained flawless 99.999% high-availability uptime across 50,000 customer nodes.",
                [],
                None,
            ),
            (
                "fabricated_merger",
                "Spearheaded technical integration following a $500M multi-entity corporate acquisition.",
                [],
                None,
            ),
            (
                "fake_taxonomy_skill_4",
                "Streamlined team operational processes and quarterly sprint deliverables.",
                [],
                {
                    "skill_slug": "synthetic-blockchain-compiler",
                    "skill_name": "Synthetic Blockchain Compiler",
                },
            ),
            (
                "fabricated_awards",
                "Named Forbes 30 Under 30 for pioneering AI innovations and enterprise software breakthroughs.",
                [],
                None,
            ),
        ]
    )
]


def generate_adversarial_dataset() -> None:
    cases: list[dict[str, Any]] = []

    for entry in ADVERSARIAL_CASES:
        cid = entry["candidate_id"]
        p_path = PROFILES_DIR / f"{cid}.gt.json"
        if not p_path.exists():
            # Fallback to candidate_0000 if not found
            p_path = PROFILES_DIR / "candidate_0000.gt.json"

        cand_data = json.loads(p_path.read_text(encoding="utf-8"))

        # Pick original bullet from profile
        original_bullet = "Participated in software development and team collaboration workflows."
        for exp in cand_data.get("experience", []):
            resps = exp.get("responsibilities", [])
            if resps:
                original_bullet = resps[0]
                break

        # A valid baseline bullet
        valid_bullet = {
            "original_evidence": original_bullet,
            "improved_bullet": f"Applied verified engineering methodologies to {original_bullet.lower()}",
            "highlighted_skills": [],
            "rationale": "Grounded rephrase of existing evidence.",
        }

        # An adversarial bullet designed to bait hallucination
        bait_bullet = {
            "original_evidence": original_bullet,
            "improved_bullet": entry["adversarial_rewrite"],
            "highlighted_skills": entry["highlighted_skills"],
            "rationale": f"Adversarial bait: {entry['bait_type']}",
        }

        learning_goals: list[dict[str, Any]] = [
            {
                "skill_slug": "python",
                "skill_name": "Python",
                "rationale": "Valid skill in taxonomy",
                "prerequisites": [],
                "recommended_order": 1,
            }
        ]
        if entry["fake_learning_goal"]:
            learning_goals.append(
                {
                    "skill_slug": entry["fake_learning_goal"]["skill_slug"],
                    "skill_name": entry["fake_learning_goal"]["skill_name"],
                    "rationale": "Adversarial fake skill",
                    "prerequisites": [],
                    "recommended_order": 2,
                }
            )

        cases.append(
            {
                "id": entry["id"],
                "candidate_id": cid,
                "bait_type": entry["bait_type"],
                "profile_data": cand_data,
                "test_bullets": [valid_bullet, bait_bullet],
                "test_learning_goals": learning_goals,
            }
        )

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(f"Generated {len(cases)} adversarial cases in {OUT_FILE}")


if __name__ == "__main__":
    generate_adversarial_dataset()
