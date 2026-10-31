"""Step 4.9: tune matching weights on train and calibrate threshold presets on val (plan §6.3)."""

from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score

from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.matching.scoring import (
    ScoringConfig,
    calculate_depth,
    calculate_experience_score,
    compute_skill_similarity,
)
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile
from talentgraph.db.repositories.taxonomy import TaxonomyRepository, get_taxonomy_repository

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("tune_matching")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
PROFILES_DIR = DATA_DIR / "profiles"
EVAL_DIR = DATA_DIR / "eval"
CONFIG_PATH = ROOT / "config" / "matching.yaml"


@dataclass
class PrecomputedPair:
    job_id: str
    candidate_id: str
    gold_grade: float
    gold_score: float
    req_data: list[tuple[float, int, bool]]  # (credit, importance, required)
    s_exp: float
    missing_imp_count: int


class DatasetCache:
    """Pre-loads and caches job requirements and candidate profiles for fast tuning."""

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


def load_pairs(split_name: str) -> list[dict[str, Any]]:
    path = EVAL_DIR / "match_gold.csv"
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [r for r in reader if r.get("split") == split_name]


def precompute_pairs(pairs: list[dict[str, Any]], cache: DatasetCache) -> list[PrecomputedPair]:
    precomputed = []
    config = ScoringConfig()
    for r in pairs:
        job = cache.get_job(r["job_id"])
        cand = cache.get_profile(r["candidate_id"])
        gold_grade = float(r["grade"])
        gold_score = float(r.get("score", 0.0))

        # 1. Experience score
        s_exp = calculate_experience_score(cand, job)

        # 2. Credits per requirement
        req_data = []
        missing_count = 0
        for req in job.requirements:
            best_credit = 0.0
            for cand_skill in cand.skills:
                sim, _ = compute_skill_similarity(
                    cand_skill.slug, req.skill_slug, repo=cache.repo, config=config
                )
                if sim > 0.0:
                    depth = calculate_depth(cand_skill, req.min_years, config=config)
                    credit = sim * (config.depth_base + config.depth_weight * depth)
                    if credit > best_credit:
                        best_credit = credit

            req_data.append((best_credit, req.importance, req.required))
            if req.required and req.importance >= 4 and best_credit == 0.0:
                missing_count += 1

        precomputed.append(
            PrecomputedPair(
                job_id=r["job_id"],
                candidate_id=r["candidate_id"],
                gold_grade=gold_grade,
                gold_score=gold_score,
                req_data=req_data,
                s_exp=s_exp,
                missing_imp_count=missing_count,
            )
        )
    return precomputed


def fast_evaluate(
    items: list[PrecomputedPair],
    alpha: float,
    beta: float,
    lmb: float,
    penalty_per_missing: float,
) -> tuple[float, float]:
    """Vectorized score computation across precomputed pairs."""
    job_groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    all_y_true: list[float] = []
    all_y_pred: list[float] = []

    for item in items:
        # Compute S_skill
        num = 0.0
        den = 0.0
        for credit, imp, req in item.req_data:
            w = imp * (1.0 if req else lmb)
            num += w * credit
            den += w
        s_skill = num / den if den > 0.0 else 0.0

        penalty = item.missing_imp_count * penalty_per_missing
        raw_score = alpha * s_skill + beta * item.s_exp - penalty
        pred = max(0.0, min(1.0, raw_score))

        job_groups[item.job_id].append((item.gold_grade, pred))
        all_y_true.append(item.gold_grade)
        all_y_pred.append(pred)

    ndcg_list: list[float] = []
    for _jid, group in job_groups.items():
        if len(group) >= 2:
            y_t = np.array([[g[0] for g in group]])
            y_s = np.array([[g[1] for g in group]])
            if np.max(y_t) > 0:
                k = min(10, len(group))
                ndcg_val = float(ndcg_score(y_t, y_s, k=k))
                ndcg_list.append(ndcg_val)

    mean_ndcg = float(np.mean(ndcg_list)) if ndcg_list else 0.0
    spearman_corr, _ = spearmanr(all_y_true, all_y_pred)
    spearman_val = float(spearman_corr) if not np.isnan(spearman_corr) else 0.0

    return mean_ndcg, spearman_val


def calibrate_thresholds(
    items: list[PrecomputedPair],
    alpha: float,
    beta: float,
    lmb: float,
    penalty_per_missing: float,
) -> dict[str, float]:
    """Calibrate precision, balanced, and recall threshold presets on val split."""
    scores_labels: list[tuple[float, bool]] = []
    for item in items:
        num = 0.0
        den = 0.0
        for credit, imp, req in item.req_data:
            w = imp * (1.0 if req else lmb)
            num += w * credit
            den += w
        s_skill = num / den if den > 0.0 else 0.0
        penalty = item.missing_imp_count * penalty_per_missing
        pred = max(0.0, min(1.0, alpha * s_skill + beta * item.s_exp - penalty))
        is_relevant = item.gold_grade >= 3.0
        scores_labels.append((pred, is_relevant))

    threshold_candidates = np.linspace(0.30, 0.85, 56)

    best_balanced_thresh = 0.60
    best_f1 = -1.0

    precision_thresh = 0.75
    recall_thresh = 0.45

    prec_candidates: list[tuple[float, float]] = []
    rec_candidates: list[tuple[float, float]] = []

    for t in threshold_candidates:
        tp = sum(1 for s, rel in scores_labels if s >= t and rel)
        fp = sum(1 for s, rel in scores_labels if s >= t and not rel)
        fn = sum(1 for s, rel in scores_labels if s < t and rel)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        if f1 > best_f1:
            best_f1 = f1
            best_balanced_thresh = float(round(t, 2))

        if prec >= 0.80 and (tp + fp) >= 10:
            prec_candidates.append((float(round(t, 2)), prec))

        if rec >= 0.85 and prec >= 0.40:
            rec_candidates.append((float(round(t, 2)), rec))

    if prec_candidates:
        precision_thresh = max(prec_candidates, key=lambda x: x[0])[0]
    if rec_candidates:
        recall_thresh = min(rec_candidates, key=lambda x: x[0])[0]

    return {
        "precision": float(round(precision_thresh, 2)),
        "balanced": float(round(best_balanced_thresh, 2)),
        "recall": float(round(recall_thresh, 2)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tune matching agent weights and presets")
    parser.add_argument("--save", action="store_true", default=True, help="Update matching.yaml")
    args = parser.parse_args()

    logger.info("Initializing taxonomy repository and dataset cache...")
    repo = get_taxonomy_repository()
    cache = DatasetCache(repo)

    train_pairs_raw = load_pairs("train")
    val_pairs_raw = load_pairs("val")
    logger.info("Precomputing 1680 train pairs and 360 val pairs...")
    train_items = precompute_pairs(train_pairs_raw, cache)
    val_items = precompute_pairs(val_pairs_raw, cache)

    # Grid search on train split
    alpha_grid = [0.65, 0.70, 0.75, 0.80]
    beta_grid = [0.20, 0.25, 0.30, 0.35]
    lambda_grid = [0.25, 0.30, 0.35, 0.40]
    penalty_grid = [0.05, 0.08, 0.10]

    best_ndcg = -1.0
    best_spearman = 0.0
    best_params = (0.70, 0.30, 0.35, 0.10)

    logger.info(
        "Starting fast grid search across %d weight configurations...",
        len(alpha_grid) * len(beta_grid) * len(lambda_grid) * len(penalty_grid),
    )
    for alpha in alpha_grid:
        for beta in beta_grid:
            for lmb in lambda_grid:
                for pen in penalty_grid:
                    ndcg, sp = fast_evaluate(train_items, alpha, beta, lmb, pen)
                    if ndcg > best_ndcg:
                        best_ndcg = ndcg
                        best_spearman = sp
                        best_params = (alpha, beta, lmb, pen)

    alpha_b, beta_b, lmb_b, pen_b = best_params
    logger.info(
        "Best Train Config: alpha=%.2f, beta=%.2f, lambda=%.2f, pen=%.2f "
        "=> NDCG@10=%.4f, Spearman=%.4f",
        alpha_b,
        beta_b,
        lmb_b,
        pen_b,
        best_ndcg,
        best_spearman,
    )

    # Calibrate thresholds on val split
    logger.info("Calibrating threshold presets on val split...")
    presets = calibrate_thresholds(val_items, alpha_b, beta_b, lmb_b, pen_b)
    logger.info("Calibrated presets: %s", presets)

    val_ndcg, val_spearman = fast_evaluate(val_items, alpha_b, beta_b, lmb_b, pen_b)
    logger.info("Validation Results => NDCG@10=%.4f, Spearman=%.4f", val_ndcg, val_spearman)

    if args.save:
        config_data = {
            "weights": {
                "alpha_skill": alpha_b,
                "beta_experience": beta_b,
            },
            "lambda_nice_to_have": lmb_b,
            "similarity": {
                "exact": 1.0,
                "descendant": 0.9,
                "ancestor_or_sibling": 0.6,
                "embedding_floor": 0.55,
            },
            "depth": {
                "base": 0.6,
                "weight": 0.4,
            },
            "penalty": {
                "per_missing_required": pen_b,
                "min_importance": 4,
            },
            "presets": presets,
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, sort_keys=False, default_flow_style=False)
        logger.info("Updated %s with tuned weights and presets", CONFIG_PATH)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
