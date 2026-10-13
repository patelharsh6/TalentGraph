"""Regenerate every Phase 1 dataset in order, optionally checking reproducibility (1-I).

    uv run python scripts/regenerate_data.py            # delete generated data, rebuild all
    uv run python scripts/regenerate_data.py --check    # rebuild twice, compare SHA-256 of outputs

Needs the O*NET files (data/taxonomy/raw/download.py) and the committed Wikidata snapshot
(data/taxonomy/wikidata_aliases.csv); no network or LLM calls.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

STEPS = [
    ["scripts/build_taxonomy.py"],
    ["scripts/gen_profiles.py", "--count", "560"],
    ["scripts/render_resumes.py"],
    ["scripts/gen_jobs.py", "--count", "120"],
    ["scripts/build_normalization_gold.py"],
    ["scripts/label_matches.py"],
]
GENERATED = [
    DATA_DIR / "profiles",
    DATA_DIR / "jobs",
    DATA_DIR / "resumes",
    DATA_DIR / ".checkpoints",
    ROOT_DIR / "tests" / "fixtures" / "resumes",
    DATA_DIR / "taxonomy" / "skills.csv",
    DATA_DIR / "taxonomy" / "aliases.csv",
    DATA_DIR / "eval" / "normalization_gold.csv",
    DATA_DIR / "eval" / "match_gold.csv",
    DATA_DIR / "eval" / "human_labeling.csv",
]


def clean() -> None:
    for path in GENERATED:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def run_all() -> None:
    for step in STEPS:
        print(f"$ python {' '.join(step)}", flush=True)
        subprocess.run([sys.executable, *step], cwd=ROOT_DIR, check=True, stdout=subprocess.DEVNULL)


def snapshot() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in GENERATED:
        files = sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
        for f in files:
            if f.exists():
                hashes[f.relative_to(ROOT_DIR).as_posix()] = hashlib.sha256(
                    f.read_bytes()
                ).hexdigest()
    return hashes


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate all Phase 1 data")
    parser.add_argument("--check", action="store_true", help="Run twice and compare hashes")
    args = parser.parse_args()

    clean()
    run_all()
    if not args.check:
        return 0
    first = snapshot()
    clean()
    run_all()
    second = snapshot()

    differing = sorted(k for k in first.keys() | second.keys() if first.get(k) != second.get(k))
    print(f"\nFiles hashed: {len(first)}   differing between runs: {len(differing)}")
    for k in differing[:20]:
        print(f"  DIFF {k}")
    print(f"Exit criterion 1-I: {'PASS' if not differing and first else 'FAIL'}")
    return 0 if not differing and first else 1


if __name__ == "__main__":
    sys.exit(main())
