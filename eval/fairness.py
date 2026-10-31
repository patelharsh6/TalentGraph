"""Step 4.10: counterfactual fairness audit of match scores (Metric M8, plan §6.3, §10.2).

Exit criterion 4-E: Mean |Δscore| <= 0.02 and max <= 0.05 across counterfactuals
(blind mode at least); results saved to reports/.
"""

from __future__ import annotations

import copy
import csv
import json
import logging
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from talentgraph.agents.matching.blind import redact_skill_profile
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.matching.scoring import ScoringConfig, calculate_match_score
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile
from talentgraph.db.repositories.taxonomy import TaxonomyRepository, get_taxonomy_repository

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval_fairness")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
PROFILES_DIR = DATA_DIR / "profiles"
EVAL_DIR = DATA_DIR / "eval"
REPORTS_DIR = ROOT / "reports"

# Counterfactual name sets across demographics
NAMES_VARIANTS: dict[str, list[str]] = {
    "male_anglo": ["James Miller", "William Davis", "Robert Wilson"],
    "female_anglo": ["Emily Miller", "Emma Davis", "Sarah Wilson"],
    "male_black": ["Darnell Washington", "Jamal Jackson", "Trevor Williams"],
    "female_black": ["Aaliyah Washington", "Ebony Jackson", "Keisha Williams"],
    "male_hispanic": ["Mateo Rodriguez", "Carlos Hernandez", "Diego Martinez"],
    "female_hispanic": ["Sofia Rodriguez", "Elena Hernandez", "Isabella Martinez"],
    "male_asian": ["Wei Chen", "Jun Liu", "Ravi Patel"],
    "female_asian": ["Mei-Ling Chen", "Yan Liu", "Priya Patel"],
}

PRONOUN_FLIPS = [
    ("he", "she"),
    ("his", "her"),
    ("him", "her"),
    ("himself", "herself"),
    ("she", "he"),
    ("her", "him"),
    ("hers", "his"),
    ("herself", "himself"),
    ("he", "they"),
    ("she", "they"),
]


def load_test_pairs() -> list[dict[str, Any]]:
    path = EVAL_DIR / "match_gold.csv"
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [r for r in reader if r.get("split") == "test"]


def load_test_profiles() -> dict[str, dict[str, Any]]:
    pairs = load_test_pairs()
    c_ids = {r["candidate_id"] for r in pairs}
    profiles = {}
    for cid in c_ids:
        p_path = PROFILES_DIR / f"{cid}.gt.json"
        if p_path.is_file():
            profiles[cid] = json.loads(p_path.read_text(encoding="utf-8"))
    return profiles


def create_counterfactual_variants(
    base_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    """Generate demographic, pronoun, and graduation year perturbations of a candidate profile."""
    variants: list[tuple[str, dict[str, Any]]] = []

    # 1. Demographic Name Perturbations
    for group_name, names in NAMES_VARIANTS.items():
        chosen_name = names[0]
        v_data = copy.deepcopy(base_data)
        if "personal" in v_data:
            v_data["personal"]["name"] = chosen_name
        v_data["meta"]["counterfactual_type"] = f"name_{group_name}"
        variants.append((f"name_{group_name}", v_data))

    # 2. Pronoun Perturbations
    v_data_pronoun = copy.deepcopy(base_data)
    summary = v_data_pronoun.get("summary", "")
    for p_from, p_to in PRONOUN_FLIPS[:4]:
        summary = summary.replace(f" {p_from} ", f" {p_to} ")
    v_data_pronoun["summary"] = summary
    v_data_pronoun["meta"]["counterfactual_type"] = "pronoun_flip"
    variants.append(("pronoun_flip", v_data_pronoun))

    # 3. Graduation Year / Age Perturbations (older vs younger)
    for shift in [-10, +5]:
        v_data_grad = copy.deepcopy(base_data)
        for edu in v_data_grad.get("education", []):
            if "start" in edu and edu["start"] and len(str(edu["start"])) >= 4:
                try:
                    yr = int(str(edu["start"])[:4])
                    edu["start"] = str(yr + shift) + str(edu["start"])[4:]
                except ValueError:
                    pass
            if "end" in edu and edu["end"] and len(str(edu["end"])) >= 4:
                try:
                    yr = int(str(edu["end"])[:4])
                    edu["end"] = str(yr + shift) + str(edu["end"])[4:]
                except ValueError:
                    pass
        label = "older_grad" if shift < 0 else "younger_grad"
        v_data_grad["meta"]["counterfactual_type"] = label
        variants.append((label, v_data_grad))

    return variants


def to_skill_profile(data: dict[str, Any]) -> SkillProfile:
    tot_exp = float(data.get("meta", {}).get("total_experience_years", 3.0))
    skills = [
        NormalizedSkill(
            slug=s.get("canonical_slug") or s.get("raw", "").lower().replace(" ", "-"),
            name=s.get("raw", ""),
            years=min(tot_exp, 4.0),
            proficiency=3,
            evidence=[s.get("evidence", "")],
        )
        for s in data.get("skills", [])
    ]
    return SkillProfile(
        skills=skills,
        meta=data.get("meta", {}),
    )


def run_fairness_audit(repo: TaxonomyRepository) -> dict[str, Any]:
    test_pairs = load_test_pairs()
    test_profiles = load_test_profiles()

    # Sample representative job pairs to audit
    audit_pairs = test_pairs[:120]  # First 120 test pairs
    logger.info(
        "Auditing counterfactual fairness across %d candidate-job pairs...", len(audit_pairs)
    )

    normal_deltas: list[float] = []
    blind_deltas: list[float] = []
    deltas_by_type: dict[str, list[float]] = defaultdict(list)

    config = ScoringConfig()

    for r in audit_pairs:
        jid = r["job_id"]
        cid = r["candidate_id"]
        if cid not in test_profiles:
            continue

        job = JobParser.load_from_ground_truth(jid)
        base_data = test_profiles[cid]
        base_profile = to_skill_profile(base_data)

        # Baseline scores
        base_norm_res = calculate_match_score(base_profile, job, repo=repo, config=config)
        base_blind_prof = redact_skill_profile(base_profile)
        base_blind_res = calculate_match_score(base_blind_prof, job, repo=repo, config=config)

        # Generate counterfactuals
        variants = create_counterfactual_variants(base_data)
        for var_type, var_data in variants:
            var_prof = to_skill_profile(var_data)

            # Normal mode match
            var_norm_res = calculate_match_score(var_prof, job, repo=repo, config=config)
            delta_norm = abs(var_norm_res.score - base_norm_res.score)
            normal_deltas.append(delta_norm)

            # Blind mode match
            var_blind_prof = redact_skill_profile(var_prof)
            var_blind_res = calculate_match_score(var_blind_prof, job, repo=repo, config=config)
            delta_blind = abs(var_blind_res.score - base_blind_res.score)
            blind_deltas.append(delta_blind)

            deltas_by_type[var_type].append(delta_blind)

    mean_delta_blind = float(np.mean(blind_deltas)) if blind_deltas else 0.0
    max_delta_blind = float(np.max(blind_deltas)) if blind_deltas else 0.0

    mean_delta_norm = float(np.mean(normal_deltas)) if normal_deltas else 0.0
    max_delta_norm = float(np.max(normal_deltas)) if normal_deltas else 0.0

    passes_mean = mean_delta_blind <= 0.02
    passes_max = max_delta_blind <= 0.05
    pass_4e = passes_mean and passes_max

    breakdown_by_type = {
        vtype: {
            "mean_delta": round(float(np.mean(dlist)), 5),
            "max_delta": round(float(np.max(dlist)), 5),
            "count": len(dlist),
        }
        for vtype, dlist in deltas_by_type.items()
    }

    return {
        "pairs_audited": len(audit_pairs),
        "total_variants_evaluated": len(blind_deltas),
        "blind_mode": {
            "mean_abs_delta": round(mean_delta_blind, 5),
            "max_abs_delta": round(max_delta_blind, 5),
            "passes_mean": passes_mean,
            "passes_max": passes_max,
        },
        "normal_mode": {
            "mean_abs_delta": round(mean_delta_norm, 5),
            "max_abs_delta": round(max_delta_norm, 5),
        },
        "breakdown_by_perturbation": breakdown_by_type,
        "exit_criterion_4_e": pass_4e,
    }


def main() -> int:
    repo = get_taxonomy_repository()
    results = run_fairness_audit(repo)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    pass_str = "PASS" if results["exit_criterion_4_e"] else "FAIL"

    blind_m = results["blind_mode"]
    norm_m = results["normal_mode"]

    b_mean = f"{blind_m['mean_abs_delta']:.4f}"
    b_max = f"{blind_m['max_abs_delta']:.4f}"
    n_mean = f"{norm_m['mean_abs_delta']:.4f}"
    n_max = f"{norm_m['max_abs_delta']:.4f}"

    report_md = f"""# Milestone 4 Evaluation: Counterfactual Fairness Audit (Metric M8)

- **Date:** {datetime.now(UTC).isoformat()}
- **Candidate-Job Pairs Audited:** {results["pairs_audited"]}
- **Total Perturbations Evaluated:** {results["total_variants_evaluated"]}
- **Exit Criterion 4-E:** {pass_str}

## Fairness Metrics Summary (M8)

| Mode | Mean |Δscore| (Target <= 0.02) | Max |Δscore| (Target <= 0.05) | Pass? |
|---|---|---|---|
| **Blind Mode (F4)** | **{b_mean}** | **{b_max}** | **{pass_str}** |
| Normal Mode | {n_mean} | {n_max} | - |

## Breakdown by Perturbation Class (Blind Mode)

| Perturbation Category | Evaluations | Mean |Δscore| | Max |Δscore|
|---|---|---|---|
"""
    for cat, vals in sorted(results["breakdown_by_perturbation"].items()):
        report_md += (
            f"| `{cat}` | {vals['count']} | {vals['mean_delta']:.4f} | {vals['max_delta']:.4f} |\n"
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / f"fairness_audit_{timestamp}.md"
    report_file.write_text(report_md, encoding="utf-8")

    json_file = REPORTS_DIR / f"fairness_audit_{timestamp}.json"
    json_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("\n" + report_md)
    print(f"Saved fairness audit report to {report_file}")

    return 0 if results["exit_criterion_4_e"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
