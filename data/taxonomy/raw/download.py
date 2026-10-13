"""Download the pinned O*NET source tables used by scripts/build_taxonomy.py (ordered.md 1.1).

Usage:  uv run python data/taxonomy/raw/download.py

Files land in data/taxonomy/raw/onet/ (gitignored). Each file is checked against a pinned
SHA-256 so the taxonomy build is reproducible; bump ONET_VERSION and the hashes together.
O*NET is published by USDOL/ETA under CC BY 4.0 (see data/taxonomy/ATTRIBUTION.md).
"""

from __future__ import annotations

import hashlib
import sys
import time
import urllib.request
from pathlib import Path

ONET_VERSION = "31_0"
BASE_URL = f"https://www.onetcenter.org/dl_files/database/db_{ONET_VERSION}_csv"

# file name -> pinned sha256
FILES = {
    "software_skills.csv": "6aabb96b464288db849580e6510530efff3f80e25dde2bb23f1fc36bb526b016",
    "content_model_reference.csv": (
        "370033744006dbd5df048431d42a402f6741a00a229b6d0f4e4f4249b6399c04"
    ),
}

OUT_DIR = Path(__file__).resolve().parent / "onet"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fetch(url: str, dest: Path, attempts: int = 4) -> None:
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=300) as resp:
                dest.write_bytes(resp.read())
            return
        except OSError as exc:  # the O*NET server is slow and sometimes drops connections
            if attempt == attempts:
                raise
            print(f"  retry {attempt}/{attempts - 1} after error: {exc}")
            time.sleep(5 * attempt)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failed = False
    for name, expected in FILES.items():
        dest = OUT_DIR / name
        if dest.exists() and _sha256(dest) == expected:
            print(f"ok (cached)  {name}")
            continue
        print(f"downloading  {BASE_URL}/{name}")
        _fetch(f"{BASE_URL}/{name}", dest)
        actual = _sha256(dest)
        if actual != expected:
            print(f"SHA-256 MISMATCH for {name}: expected {expected}, got {actual}")
            failed = True
        else:
            print(f"ok           {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
