"""Phase 1.10: generate the candidate-job matching gold set.

    uv run python scripts/label_matches.py           # build, then print stats
    uv run python scripts/label_matches.py --stats   # stats, 1-G check and Cohen's kappa

Grades (0-4) come from a deterministic labeler that applies the thresholds in
data/eval/match_rubric.md to the ground-truth skills, experience and industry. It stands in
for the planned LLM judge (ADR-0002), which needs Gemini quota this phase did not have.

For each job, 20 candidates are selected, 4 per grade where the pool allows (backfilled
otherwise), and split 70/15/15 by job. human_labeling.csv is a 240-pair sample with an empty
`human_grade` column; once humans fill it in, --stats reports quadratic-weighted Cohen's kappa.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("label_matches")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
JOBS_DIR = DATA_DIR / "jobs"
PROFILES_DIR = DATA_DIR / "profiles"
EVAL_DIR = DATA_DIR / "eval"

random.seed(42)


def compute_pair_grade(
    job_gt: dict[str, Any], candidate_gt: dict[str, Any]
) -> tuple[int, float, str]:
    """Compute 0-4 relevance grade, numeric score, and rationale based on ground truth overlap."""
    job_reqs = job_gt.get("requirements", [])
    required_slugs = {r["skill_slug"] for r in job_reqs if r.get("required", True)}
    nice_slugs = {r["skill_slug"] for r in job_reqs if not r.get("required", True)}

    cand_skills = candidate_gt.get("skills", [])
    cand_slugs = {s.get("canonical_slug", "") for s in cand_skills}

    # Skill overlap
    req_overlap = len(required_slugs.intersection(cand_slugs))
    req_total = len(required_slugs) if required_slugs else 1
    req_ratio = req_overlap / req_total

    nice_overlap = len(nice_slugs.intersection(cand_slugs))
    nice_total = len(nice_slugs) if nice_slugs else 1
    nice_ratio = nice_overlap / nice_total

    # Seniority & experience check
    req_min_years = float(job_gt.get("min_total_experience_years", 3.0))
    cand_years = float(candidate_gt.get("meta", {}).get("total_experience_years", 3.0))
    exp_ratio = min(1.0, cand_years / max(1.0, req_min_years))

    # Industry / Role family alignment
    cand_ind = candidate_gt.get("meta", {}).get("industry", "")
    job_rf = job_gt.get("role_family", "")
    ind_match = (cand_ind == job_rf) or (cand_ind == "software" and job_rf == "engineering")

    # Weighted numeric score
    score = (
        0.55 * req_ratio + 0.15 * nice_ratio + 0.20 * exp_ratio + 0.10 * (1.0 if ind_match else 0.2)
    )
    score = max(0.0, min(1.0, score))

    # Thresholds from data/eval/match_rubric.md (required-skill share, experience, domain).
    if req_ratio >= 0.90 and exp_ratio >= 1.0 and ind_match:
        grade = 4
        rationale = (
            f"Strong match: Covers {req_overlap}/{req_total} required skills "
            f"({req_ratio:.0%}) with {cand_years:.0f}y experience in {cand_ind}."
        )
    elif req_ratio >= 0.70 and exp_ratio >= 0.80:
        grade = 3
        rationale = (
            f"Solid match: Covers {req_overlap}/{req_total} core skills "
            f"with {cand_years:.0f}y experience."
        )
    elif req_ratio >= 0.40:
        grade = 2
        rationale = (
            f"Partial match: Demonstrates {req_overlap}/{req_total} skills; "
            f"transferable background with upskilling potential."
        )
    elif req_ratio >= 0.10 or ind_match:
        grade = 1
        rationale = (
            f"Weak match: Only {req_overlap}/{req_total} skill overlap with limited role alignment."
        )
    else:
        grade = 0
        job_role = job_gt.get("title", "job")
        rationale = (
            f"Irrelevant: Candidate in {cand_ind} does not meet requirements for {job_role}."
        )

    return grade, round(score, 4), rationale


def generate_match_gold_set() -> None:
    """Generate match_gold.csv and human_labeling.csv."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    match_gold_path = EVAL_DIR / "match_gold.csv"
    human_csv_path = EVAL_DIR / "human_labeling.csv"

    job_files = sorted(JOBS_DIR.glob("job_*.gt.json"))
    cand_files = sorted(PROFILES_DIR.glob("candidate_*.gt.json"))

    if not job_files or not cand_files:
        raise FileNotFoundError(
            "Missing job/candidate GT files. Run gen_jobs.py and gen_profiles.py first."
        )

    jobs_data = [
        json.loads(jf.read_text(encoding="utf-8")) | {"job_id": jf.stem.replace(".gt", "")}
        for jf in job_files
    ]
    cands_data = [
        json.loads(cf.read_text(encoding="utf-8")) | {"candidate_id": cf.stem.replace(".gt", "")}
        for cf in cand_files
    ]

    # Assign 70/15/15 train/val/test split by job
    random.shuffle(jobs_data)
    n_jobs = len(jobs_data)
    n_train = int(n_jobs * 0.70)
    n_val = int(n_jobs * 0.15)

    for i, j in enumerate(jobs_data):
        if i < n_train:
            j["split"] = "train"
        elif i < n_train + n_val:
            j["split"] = "val"
        else:
            j["split"] = "test"

    match_records: list[dict[str, Any]] = []
    grade_counts: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

    logger.info("Pairing %d jobs with candidates (20 pairs per job)...", len(jobs_data))

    for job in jobs_data:
        job_id = job["job_id"]
        split = job["split"]

        # Evaluate candidate fit for all available candidates
        candidate_scores = []
        for cand in cands_data:
            grade, score, rationale = compute_pair_grade(job, cand)
            candidate_scores.append((cand, grade, score, rationale))

        # Bucket candidates by grade
        buckets: dict[int, list[Any]] = {0: [], 1: [], 2: [], 3: [], 4: []}
        for item in candidate_scores:
            buckets[item[1]].append(item)

        # Shuffle each bucket
        for g in range(5):
            random.shuffle(buckets[g])

        # Select evenly from grades 0, 1, 2, 3, 4 (4 per grade = 20 total)
        selected_pairs: list[Any] = []
        target_per_grade = 4

        for g in (4, 3, 2, 1, 0):
            take = buckets[g][:target_per_grade]
            selected_pairs.extend(take)

        # If any bucket had fewer than target_per_grade, backfill from other non-empty buckets
        seen_cand_ids = {p[0]["candidate_id"] for p in selected_pairs}
        while len(selected_pairs) < 20:
            # Backfill from the grade with the fewest pairs so far (corpus-wide), keeping the
            # overall grade distribution as flat as the candidate pool allows.
            added = False
            for g in sorted(range(5), key=lambda g: (grade_counts[g], g)):
                avail = [c for c in buckets[g] if c[0]["candidate_id"] not in seen_cand_ids]
                if avail:
                    cand_item = avail[0]
                    selected_pairs.append(cand_item)
                    seen_cand_ids.add(cand_item[0]["candidate_id"])
                    added = True
                    break
            if not added:
                break

        for cand, grade, score, rationale in selected_pairs[:20]:
            cand_id = cand["candidate_id"]
            grade_counts[grade] += 1
            match_records.append(
                {
                    "job_id": job_id,
                    "candidate_id": cand_id,
                    "grade": grade,
                    "score": score,
                    "split": split,
                    "rationale": rationale,
                }
            )

    # Write match_gold.csv
    with open(match_gold_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["job_id", "candidate_id", "grade", "score", "split", "rationale"],
            lineterminator="\n",
        )
        writer.writeheader()
        for r in match_records:
            writer.writerow(r)

    # human_labeling.csv: a sample for human double-labeling. human_grade stays empty until a
    # person fills it in; never pre-fill it from the machine grade.
    human_sample = random.Random(99).sample(match_records, min(240, len(match_records)))
    with open(human_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "job_id",
                "candidate_id",
                "grade",
                "score",
                "rationale",
                "human_grade",
                "human_notes",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for r in human_sample:
            writer.writerow(
                {
                    "job_id": r["job_id"],
                    "candidate_id": r["candidate_id"],
                    "grade": r["grade"],
                    "score": r["score"],
                    "rationale": r["rationale"],
                    "human_grade": "",
                    "human_notes": "",
                }
            )

    logger.info("Successfully generated %d match pairs in %s", len(match_records), match_gold_path)
    logger.info("Exported %d human verification pairs to %s", len(human_sample), human_csv_path)


def print_match_stats() -> bool:
    """Print match gold statistics; return whether the match-gold part of 1-G passes."""
    match_gold_path = EVAL_DIR / "match_gold.csv"
    if not match_gold_path.exists():
        print(f"Missing {match_gold_path}. Run label_matches.py first.")
        return False

    records = []
    with open(match_gold_path, encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    print("\n==================== TALENTGRAPH MATCH GOLD STATS ====================")
    print(f"Total Match Pairs:           {len(records)}")

    grade_counts: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    split_counts: dict[str, int] = {}

    for r in records:
        g = int(r["grade"])
        s = r["split"]
        grade_counts[g] = grade_counts.get(g, 0) + 1
        split_counts[s] = split_counts.get(s, 0) + 1

    print("\nGrade Distribution (0-4):")
    max_pct = 0.0
    for g in sorted(grade_counts.keys()):
        c = grade_counts[g]
        pct = (c / len(records) * 100) if records else 0
        max_pct = max(max_pct, pct)
        print(f"  Grade {g}: {c:4d} pairs ({pct:5.1f}%)")

    print("\nSplit Distribution:")
    for s, c in sorted(split_counts.items()):
        print(f"  Split [{s:5s}]: {c:4d} pairs")

    passes = len(records) >= 2000 and max_pct <= 40.0
    print(f"\nMax Grade Share: {max_pct:.1f}% (<= 40% required)")

    human_path = EVAL_DIR / "human_labeling.csv"
    if human_path.exists():
        with open(human_path, encoding="utf-8") as f:
            human = list(csv.DictReader(f))
        labeled = [r for r in human if r["human_grade"].strip()]
        if labeled:
            kappa = weighted_kappa(
                [int(r["grade"]) for r in labeled], [int(r["human_grade"]) for r in labeled]
            )
            print(
                f"Human labels: {len(labeled)}/{len(human)}, quadratic-weighted kappa {kappa:.3f}"
            )
        else:
            print(f"Human labels: 0/{len(human)} (kappa pending; CSV exported for labeling)")
    print(f"\nExit criterion 1-G (match gold): {'PASS' if passes else 'FAIL'}")
    print("======================================================================\n")
    return passes


def weighted_kappa(a: list[int], b: list[int], k: int = 5) -> float:
    """Quadratic-weighted Cohen's kappa for two raters on a 0..k-1 ordinal scale."""
    n = len(a)
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        observed[x][y] += 1
    hist_a = [sum(row) for row in observed]
    hist_b = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * observed[i][j]
            den += w * hist_a[i] * hist_b[j] / n
    return 1.0 - num / den if den else 1.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate candidate-to-job matching gold dataset")
    parser.add_argument(
        "--stats", action="store_true", help="Print matching gold corpus statistics"
    )
    args = parser.parse_args()

    if not args.stats:
        generate_match_gold_set()

    return 0 if print_match_stats() else 1


if __name__ == "__main__":
    sys.exit(main())
