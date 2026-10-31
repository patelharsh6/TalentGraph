"""Step 4.9: NDCG@k, Spearman/Kendall and threshold P/R curves (M3 evaluation).

Exit criterion 4-A: NDCG@10 >= 0.80 and Spearman rho >= 0.60 on test split,
stating which gold re-validation was used.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from scipy.stats import kendalltau, spearmanr
from sklearn.metrics import ndcg_score

from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.matching.scoring import ScoringConfig, calculate_match_score
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile
from talentgraph.db.repositories.taxonomy import TaxonomyRepository, get_taxonomy_repository
from talentgraph.embeddings.skill_index import SkillIndex

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval_matching")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
PROFILES_DIR = DATA_DIR / "profiles"
EVAL_DIR = DATA_DIR / "eval"
REPORTS_DIR = ROOT / "reports"
CONFIG_PATH = ROOT / "config" / "matching.yaml"


class DatasetCache:
    def __init__(self, repo: TaxonomyRepository) -> None:
        self.repo = repo
        self.jobs: dict[str, Any] = {}
        self.profiles: dict[str, SkillProfile] = {}

    def get_job(self, job_id: str) -> Any:
        if job_id not in self.jobs:
            self.jobs[job_id] = JobParser.load_from_ground_truth(job_id)
        return self.jobs[job_id]

    def get_profile(self, candidate_id: str) -> SkillProfile:
        if candidate_id not in self.profiles:
            p_file = PROFILES_DIR / f"{candidate_id}.gt.json"
            data = json.loads(p_file.read_text(encoding="utf-8"))
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
            self.profiles[candidate_id] = SkillProfile(
                skills=skills,
                meta=data.get("meta", {}),
            )
        return self.profiles[candidate_id]


def load_config() -> tuple[ScoringConfig, dict[str, float]]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    weights = cfg.get("weights", {})
    sim = cfg.get("similarity", {})
    depth = cfg.get("depth", {})
    pen = cfg.get("penalty", {})

    scoring_cfg = ScoringConfig(
        alpha_skill=float(weights.get("alpha_skill", 0.70)),
        beta_experience=float(weights.get("beta_experience", 0.30)),
        lambda_nice=float(cfg.get("lambda_nice_to_have", 0.35)),
        sim_exact=float(sim.get("exact", 1.0)),
        sim_descendant=float(sim.get("descendant", 0.9)),
        sim_ancestor_or_sibling=float(sim.get("ancestor_or_sibling", 0.6)),
        sim_embedding_floor=float(sim.get("embedding_floor", 0.55)),
        depth_base=float(depth.get("base", 0.6)),
        depth_weight=float(depth.get("weight", 0.4)),
        penalty_per_missing=float(pen.get("per_missing_required", 0.10)),
        penalty_min_importance=int(pen.get("min_importance", 4)),
    )
    presets = cfg.get("presets", {"precision": 0.75, "balanced": 0.60, "recall": 0.45})
    return scoring_cfg, presets


def evaluate_split(
    split_name: str,
    cache: DatasetCache,
    config: ScoringConfig,
    presets: dict[str, float],
    skill_index: SkillIndex | None = None,
) -> dict[str, Any]:
    gold_path = EVAL_DIR / "match_gold.csv"
    with open(gold_path, encoding="utf-8") as f:
        pairs = [r for r in csv.DictReader(f) if r.get("split") == split_name]

    job_groups: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
    all_grades: list[float] = []
    all_scores: list[float] = []
    pair_results: list[dict[str, Any]] = []

    for r in pairs:
        job = cache.get_job(r["job_id"])
        cand = cache.get_profile(r["candidate_id"])
        gold_grade = float(r["grade"])

        res = calculate_match_score(
            cand, job, repo=cache.repo, skill_index=skill_index, config=config
        )

        job_groups[r["job_id"]].append((gold_grade, res.score, r["candidate_id"]))
        all_grades.append(gold_grade)
        all_scores.append(res.score)

        pair_results.append(
            {
                "job_id": r["job_id"],
                "candidate_id": r["candidate_id"],
                "gold_grade": gold_grade,
                "score": res.score,
                "skill_score": res.components["skill_score"],
                "exp_score": res.components["experience_score"],
                "penalty": res.components["penalty"],
            }
        )

    # NDCG@5 and NDCG@10 per job
    ndcg5_list: list[float] = []
    ndcg10_list: list[float] = []
    for _jid, group in job_groups.items():
        if len(group) >= 2:
            y_t = np.array([[g[0] for g in group]])
            y_s = np.array([[g[1] for g in group]])
            if np.max(y_t) > 0:
                k5 = min(5, len(group))
                k10 = min(10, len(group))
                ndcg5_list.append(float(ndcg_score(y_t, y_s, k=k5)))
                ndcg10_list.append(float(ndcg_score(y_t, y_s, k=k10)))

    mean_ndcg5 = float(np.mean(ndcg5_list)) if ndcg5_list else 0.0
    mean_ndcg10 = float(np.mean(ndcg10_list)) if ndcg10_list else 0.0

    spearman_corr, _ = spearmanr(all_grades, all_scores)
    spearman_val = float(spearman_corr) if not np.isnan(spearman_corr) else 0.0

    kendall_corr, _ = kendalltau(all_grades, all_scores)
    kendall_val = float(kendall_corr) if not np.isnan(kendall_corr) else 0.0

    # Evaluate presets (relevance = gold_grade >= 2)
    preset_metrics: dict[str, dict[str, float]] = {}
    for name, thresh in presets.items():
        tp = sum(1 for p in pair_results if p["score"] >= thresh and p["gold_grade"] >= 2.0)
        fp = sum(1 for p in pair_results if p["score"] >= thresh and p["gold_grade"] < 2.0)
        fn = sum(1 for p in pair_results if p["score"] < thresh and p["gold_grade"] >= 2.0)
        tn = sum(1 for p in pair_results if p["score"] < thresh and p["gold_grade"] < 2.0)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        preset_metrics[name] = {
            "threshold": thresh,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        }

    return {
        "split": split_name,
        "pair_count": len(pairs),
        "job_count": len(job_groups),
        "ndcg_at_5": round(mean_ndcg5, 4),
        "ndcg_at_10": round(mean_ndcg10, 4),
        "spearman_rho": round(spearman_val, 4),
        "kendall_tau": round(kendall_val, 4),
        "presets": preset_metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate semantic matching quality (M3)")
    parser.add_argument("--split", default="test", help="Dataset split (test, val, train)")
    args = parser.parse_args()

    repo = get_taxonomy_repository()
    cache = DatasetCache(repo)
    config, presets = load_config()

    metrics = evaluate_split(args.split, cache, config, presets)

    # Gold revalidation note
    gold_revalidation = (
        "Quadratic-weighted Cohen's kappa = 0.955 across 240 double-labeled candidate-job pairs "
        "in data/eval/human_labeling.csv (ADR-0002)"
    )

    passes_ndcg = metrics["ndcg_at_10"] >= 0.80
    passes_spearman = metrics["spearman_rho"] >= 0.60
    exit_4a_pass = passes_ndcg and passes_spearman

    prec_p = metrics["presets"]["precision"]
    bal_p = metrics["presets"]["balanced"]
    rec_p = metrics["presets"]["recall"]
    pass_ndcg_str = "PASS" if passes_ndcg else "FAIL"
    pass_sp_str = "PASS" if passes_spearman else "FAIL"
    pass_str = "PASS" if exit_4a_pass else "FAIL"

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    prec_row = (
        f"| `precision` | {presets['precision']:.2f} | "
        f"{prec_p['precision']:.4f} | {prec_p['recall']:.4f} | {prec_p['f1']:.4f} |"
    )
    bal_row = (
        f"| `balanced` | {presets['balanced']:.2f} | "
        f"{bal_p['precision']:.4f} | {bal_p['recall']:.4f} | {bal_p['f1']:.4f} |"
    )
    rec_row = (
        f"| `recall` | {presets['recall']:.2f} | "
        f"{rec_p['precision']:.4f} | {rec_p['recall']:.4f} | {rec_p['f1']:.4f} |"
    )
    report_md = f"""# Milestone 4 Evaluation: Semantic Matching (Metric M3)

- **Date:** {datetime.now(UTC).isoformat()}
- **Split:** `{args.split}` ({metrics["pair_count"]} pairs across {metrics["job_count"]} jobs)
- **Gold Re-validation (ADR-0002):** {gold_revalidation}
- **Exit Criterion 4-A:** {pass_str}

## Ranking Metrics (M3)

| Metric | Target | Measured | Pass? |
|---|---|---|---|
| **NDCG@10** | >= 0.8000 | **{metrics["ndcg_at_10"]:.4f}** | {pass_ndcg_str} |
| **Spearman rho** | >= 0.6000 | **{metrics["spearman_rho"]:.4f}** | {pass_sp_str} |
| NDCG@5 | - | {metrics["ndcg_at_5"]:.4f} | - |
| Kendall tau | - | {metrics["kendall_tau"]:.4f} | - |

## Threshold Presets Performance (Relevance >= Grade 2)

| Preset | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|
{prec_row}
{bal_row}
{rec_row}

## Weights Configuration
```yaml
alpha_skill: {config.alpha_skill}
beta_experience: {config.beta_experience}
lambda_nice: {config.lambda_nice}
penalty_per_missing: {config.penalty_per_missing}
```
"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / f"matching_{args.split}_{timestamp}.md"
    report_file.write_text(report_md, encoding="utf-8")

    json_file = REPORTS_DIR / f"matching_{args.split}_{timestamp}.json"
    full_output = {
        **metrics,
        "gold_revalidation": gold_revalidation,
        "exit_criterion_4_a": exit_4a_pass,
        "weights": {
            "alpha_skill": config.alpha_skill,
            "beta_experience": config.beta_experience,
            "lambda_nice": config.lambda_nice,
            "penalty_per_missing": config.penalty_per_missing,
        },
    }
    json_file.write_text(json.dumps(full_output, indent=2), encoding="utf-8")

    print("\n" + report_md)
    print(f"Saved evaluation report to {report_file}")

    return 0 if exit_4a_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
