"""Phase 1.3: snapshot English Wikidata alt-labels for software skills in the taxonomy.

Usage:  uv run python scripts/fetch_wikidata_aliases.py

Looks up every level-3 technical skill name in data/taxonomy/skills.csv on the Wikidata
SPARQL endpoint, restricted to items that are software (Q7397) or programming languages
(Q9143), and writes their English alt-labels to data/taxonomy/wikidata_aliases.csv
(slug, alias, wikidata_id). Wikidata is CC0. The snapshot is committed so that
scripts/build_taxonomy.py stays reproducible offline; rerun this script to refresh it.

Alt-labels that are descriptions rather than names ("container orchestrator" for
Kubernetes) are dropped: an alias is kept only if it shares a word with the skill name or
looks like a proper noun or acronym (has an uppercase letter or a digit).
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
TAXONOMY_DIR = ROOT_DIR / "data" / "taxonomy"
OUT_PATH = TAXONOMY_DIR / "wikidata_aliases.csv"
ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "TalentGraph-taxonomy-build/0.1 (offline snapshot of skill alt-labels)"
BATCH = 120

QUERY = """
SELECT ?label ?item ?alias WHERE {
  VALUES ?label { %s }
  VALUES ?cls { wd:Q7397 wd:Q9143 }
  ?item rdfs:label ?label .
  ?item wdt:P31/wdt:P279* ?cls .
  ?item skos:altLabel ?alias .
  FILTER(LANG(?alias) = "en")
}
"""


def _tokens(text: str) -> set[str]:
    return set(re.sub(r"[^\w+#]+", " ", text.lower()).split())


def is_surface_form(alias: str, name: str) -> bool:
    if len(alias) > 60 or alias.lower() == name.lower():
        return False
    if _tokens(alias) & _tokens(name):
        return True
    return bool(re.search(r"[A-Z0-9]", alias))


def _query(labels: list[str]) -> list[dict[str, dict[str, str]]]:
    values = " ".join(json.dumps(label) + "@en" for label in labels)
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": QUERY % values, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                bindings: list[dict[str, dict[str, str]]] = json.load(resp)["results"]["bindings"]
                return bindings
        except OSError as exc:
            if attempt == 4:
                raise
            print(f"  retry {attempt} after {exc}")
            time.sleep(10 * attempt)
    return []


def main() -> int:
    with open(TAXONOMY_DIR / "skills.csv", encoding="utf-8") as f:
        skills = [r for r in csv.DictReader(f) if r["level"] == "3" and r["type"] == "technical"]
    by_name: dict[str, str] = {}
    for s in skills:
        by_name.setdefault(s["name"], s["slug"])
    names = sorted(by_name)
    rows: set[tuple[str, str, str]] = set()
    for i in range(0, len(names), BATCH):
        batch = names[i : i + BATCH]
        for b in _query(batch):
            name, alias = b["label"]["value"], b["alias"]["value"].strip()
            qid = b["item"]["value"].rsplit("/", 1)[-1]
            if name in by_name and is_surface_form(alias, name):
                rows.add((by_name[name], alias, qid))
        print(f"{min(i + BATCH, len(names))}/{len(names)} names, {len(rows)} aliases")
        time.sleep(1.0)  # be polite to the public endpoint
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["slug", "alias", "wikidata_id"])
        writer.writerows(sorted(rows))
    print(f"wrote {len(rows)} aliases to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
