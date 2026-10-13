"""Phase 1.9: build the normalization gold set (data/eval/normalization_gold.csv).

    uv run python scripts/build_normalization_gold.py           # build, then print stats
    uv run python scripts/build_normalization_gold.py --stats   # stats + 1-G check (exit 1 on fail)

Columns: raw, context, expected_slug, case_type, is_hard_case, split.
`expected_slug` is a taxonomy slug, `NEW` for a skill that is not in the taxonomy, or several
slugs joined by `|` for a multi-skill string (all of them should be produced).

Easy rows (~70%) are real surface forms: every distinct skill string used in the synthetic
profiles and job descriptions, plus a seeded sample of non-ambiguous taxonomy aliases.
Hard rows (>= 25%) are hand-written ambiguous terms with context, version strings,
multi-skill strings, abbreviations and unknown skills, plus deterministic typos of real
skill names. Split 50/50 into val and test, stratified by case_type.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
EVAL_DIR = DATA_DIR / "eval"
TAXONOMY_DIR = DATA_DIR / "taxonomy"
GOLD_PATH = EVAL_DIR / "normalization_gold.csv"
SEED = 42
TARGET_ROWS = 1200
FIELDS = ["raw", "context", "expected_slug", "case_type", "is_hard_case", "split"]

# (raw, context, expected_slug): ambiguous surface forms resolved only by context.
AMBIGUOUS_CASES = [
    ("Go", "Engineered high-throughput concurrent microservices in Go using goroutines.", "golang"),
    (
        "Go",
        "Led the go-to-market launch for our enterprise analytics product.",
        "go-to-market-strategy",
    ),
    ("R", "Performed regression and time-series analysis in R with ggplot2.", "r-language"),
    (
        "R&D",
        "Managed a 12-person R&D group building next-generation sensors.",
        "research-and-development",
    ),
    ("C", "Wrote kernel device drivers and memory allocators in C.", "c-language"),
    ("C-level", "Presented quarterly results to C-level stakeholders.", "executive-communication"),
    (
        "Spring",
        "Built Java microservices with Spring Boot and Spring Data JPA.",
        "spring-framework",
    ),
    ("Swift", "Built a native iOS app in Swift using SwiftUI.", "swift-language"),
    ("SWIFT", "Processed SWIFT MT103 international wire transfers.", "swift-network"),
    ("Rust", "Implemented memory-safe WebAssembly modules in Rust.", "rust-language"),
    ("Excel", "Built three-statement forecasting models in Excel.", "microsoft-excel"),
    ("Word", "Drafted and formatted contracts in Word with tracked changes.", "microsoft-word"),
    ("Git", "Managed branching, rebasing and pull requests in Git.", "git-version-control"),
    ("Ruby", "Maintained a Ruby on Rails monolith.", "ruby-language"),
    ("PM", "Served as PM owning the product requirements and roadmap.", "product-management"),
    (
        "PM",
        "Performed scheduled PM on CNC machines to prevent breakdowns.",
        "preventive-maintenance",
    ),
    ("CV", "Trained object-detection models for CV using PyTorch.", "computer-vision"),
    ("CV", "Screened candidate CVs and ran first-round interviews.", "talent-acquisition"),
    ("REST", "Designed REST endpoints documented with OpenAPI 3.", "rest-api"),
    ("rest periods", "Audited shift schedules for statutory rest periods.", "workplace-compliance"),
    ("Spark", "Ran distributed ETL jobs on Spark clusters.", "apache-spark"),
    ("Chef", "Automated server configuration with Chef cookbooks.", "chef"),
    ("Puppet", "Provisioned data-centre servers with Puppet manifests.", "puppet"),
    ("Flask", "Built lightweight Python APIs with Flask and Gunicorn.", "flask"),
    ("Unity", "Developed a 3D mobile game in Unity with C# scripts.", "unity-3d"),
    ("Access", "Maintained departmental databases and reports in Access.", "microsoft-access"),
    ("Teams", "Ran remote stand-ups and channels in Teams.", "microsoft-teams"),
    ("Project", "Scheduled the plant rollout with Gantt charts in Project.", "microsoft-project"),
    ("Kafka", "Streamed clickstream events through Kafka topics.", "apache-kafka"),
    ("Airflow", "Orchestrated nightly batch pipelines as Airflow DAGs.", "apache-airflow"),
]

# Version strings and decorated forms.
VERSION_CASES = [
    ("Python 3.11", "python"),
    ("Python3", "python"),
    ("Java 17", "java"),
    ("Java SE 21", "java"),
    ("C++20", "c-plus-plus"),
    ("PostgreSQL 15.2", "postgresql"),
    ("Postgres 16", "postgresql"),
    ("ReactJS 18", "react"),
    ("React 18.2", "react"),
    ("Angular 16", "angular"),
    ("Vue.js v3.2", "vue-js"),
    ("Node.js 20 LTS", "node-js"),
    ("TypeScript 5.x", "typescript"),
    ("TensorFlow 2.14", "tensorflow"),
    ("PyTorch 2.1 (CUDA 12)", "pytorch"),
    ("Django 5.0", "django"),
    ("Spring Boot 3", "spring-boot"),
    ("Kubernetes 1.29", "kubernetes"),
    ("Docker 24", "docker"),
    ("Terraform 1.6", "terraform"),
    ("Next.js 14 App Router", "next-js"),
    ("Tailwind CSS v3", "tailwindcss"),
    ("MongoDB 6.0", "mongodb"),
    ("Redis 7", "redis"),
    ("Elasticsearch 8", "elasticsearch"),
    ("HTML5", "html5"),
    ("CSS3", "css3"),
    ("Microsoft Excel 365", "microsoft-excel"),
    ("Excel 2019", "microsoft-excel"),
    ("Scikit-learn 1.3", "scikit-learn"),
    ("Pandas 2.x", "pandas"),
    ("Apache Spark 3.5", "apache-spark"),
    ("Kafka 3.6", "apache-kafka"),
    ("GraphQL (Apollo 4)", "graphql"),
    ("Figma (2024)", "figma"),
    ("Tableau 2023.3", "tableau"),
    ("Power BI Desktop", "power-bi"),
    ("Salesforce Lightning", "salesforce"),
    ("Jira Cloud", "jira"),
    ("SAP S/4HANA", "sap-erp"),
]

# Multi-skill strings: every listed slug should be produced.
MULTI_CASES = [
    ("Python/Django", "python|django"),
    ("Python & FastAPI", "python|fastapi"),
    ("React + TypeScript", "react|typescript"),
    ("HTML/CSS/JavaScript", "html5|css3|javascript"),
    ("Docker & Kubernetes", "docker|kubernetes"),
    ("Terraform/Ansible", "terraform|ansible"),
    ("Pandas, NumPy", "pandas|numpy"),
    ("PyTorch/TensorFlow", "pytorch|tensorflow"),
    ("SQL & Tableau", "sql|tableau"),
    ("Kafka/Spark Streaming", "apache-kafka|apache-spark"),
    ("Jira & Confluence", "jira|confluence"),
    ("SEO/SEM", "search-engine-optimization|search-engine-marketing"),
    ("GAAP & IFRS", "gaap|ifrs"),
    ("HL7 / FHIR", "hl7-fhir"),
    ("Node.js/Express", "node-js|express-js"),
    ("Git/GitHub", "git-version-control|github"),
    ("Excel/VBA", "microsoft-excel|excel-vba"),
    ("Figma & Sketch", "figma|sketch"),
    ("Grafana + Prometheus", "grafana|prometheus"),
    ("Snowflake/dbt", "snowflake|dbt"),
]

# Abbreviations whose expansion is not visible in the string.
ABBREVIATION_CASES = [
    ("JS", "javascript"),
    ("TS", "typescript"),
    ("K8s", "kubernetes"),
    ("TF", "tensorflow"),
    ("GCP", "google-cloud-platform"),
    ("AWS", "amazon-web-services"),
    ("ML", "machine-learning"),
    ("DL", "deep-learning"),
    ("NLP", "natural-language-processing"),
    ("CI/CD", "continuous-integration-and-continuous-delivery"),
    ("UX", "user-experience-design"),
    ("LLMs", "large-language-models"),
    ("RAG", "retrieval-augmented-generation"),
    ("MLOps", "machine-learning-operations"),
    ("EHR", "electronic-health-records"),
    ("SEO", "search-engine-optimization"),
    ("CRO", "conversion-rate-optimization"),
    ("IoT", "internet-of-things"),
    ("KPIs", "key-performance-indicators"),
    ("OKRs", "objectives-and-key-results"),
    ("GTM", "go-to-market-strategy"),
    ("IaC", "infrastructure-as-code"),
    ("Postgres", "postgresql"),
    ("ML Engineering", "machine-learning-engineering"),
    ("MS Excel", "microsoft-excel"),
]

# Plausible skills that are not in the taxonomy (expected NEW).
UNKNOWN_CASES = [
    ("Mamba state-space models", "Researched sub-quadratic sequence models with Mamba SSMs."),
    ("Mojo", "Wrote GPU kernels in Mojo for the Modular inference stack."),
    ("Direct Preference Optimization", "Aligned chat models with DPO instead of RLHF."),
    ("DNA data storage", "Encoded digital archives into synthetic DNA strands."),
    ("Quantum error mitigation", "Applied zero-noise extrapolation on noisy quantum circuits."),
    ("Neuromorphic computing", "Designed spiking neural networks for low-power edge chips."),
    ("DePIN", "Deployed token-incentivised wireless hardware networks."),
    ("zk-STARK circuits", "Built zk-STARK verification circuits for a Layer-2 rollup."),
    ("Scope 3 carbon accounting", "Modelled supplier Scope 3 emissions for CSRD reporting."),
    ("Agentic tool-use protocols", "Designed MCP tool schemas for autonomous agents."),
    ("Gaussian splatting", "Reconstructed 3D scenes from video using Gaussian splatting."),
    ("Speculative decoding", "Cut LLM latency 2x with speculative decoding."),
    ("Vector-symbolic architectures", "Prototyped hyperdimensional computing for edge inference."),
    ("Kolmogorov-Arnold networks", "Benchmarked KANs against MLPs on tabular data."),
    ("Prompt caching strategy", "Reduced inference cost with layered prompt caching."),
    ("Digital product passports", "Implemented EU digital product passports for batteries."),
    ("Biochar carbon removal", "Verified biochar carbon-removal credits for buyers."),
    ("Precision fermentation", "Scaled precision-fermentation dairy proteins to pilot plant."),
    ("Solid-state battery cell design", "Characterised solid-state electrolyte interfaces."),
    ("Embodied AI simulation", "Trained household robots in embodied-AI simulators."),
    ("Federated analytics", "Ran federated analytics across hospital sites without moving data."),
    ("Synthetic biology CAD", "Designed genetic circuits in a synthetic-biology CAD tool."),
    ("Agent evaluation harnesses", "Built evaluation harnesses for multi-step LLM agents."),
    ("Ambient clinical documentation", "Rolled out ambient AI scribes in outpatient clinics."),
    ("Carbon-aware scheduling", "Shifted batch jobs to low-carbon grid hours."),
    ("Retrieval-interleaved generation", "Prototyped retrieval-interleaved generation for QA."),
    ("Post-quantum TLS migration", "Migrated services to hybrid post-quantum TLS key exchange."),
    ("Sovereign cloud compliance", "Mapped workloads to EU sovereign-cloud requirements."),
    ("Humanoid robot teleoperation", "Collected teleoperation data for humanoid manipulation."),
    ("Space-based solar power", "Modelled microwave power beaming from orbital arrays."),
]

EASY_CONTEXTS = [
    "Used {x} daily to deliver features for internal and external customers.",
    "Hands-on experience with {x} in production environments.",
    "Led a project built on {x}, improving delivery speed by 30%.",
    "Skills: {x}, stakeholder communication, documentation.",
    "Trained two junior colleagues in {x} best practices.",
    "Applied {x} to automate reporting and cut manual effort.",
]
HARD_CONTEXTS = [
    "Proficient in {x} across several client engagements.",
    "Core skills include {x} and cross-team collaboration.",
    "Delivered three releases using {x}.",
]


def make_typo(word: str, rng: random.Random) -> str:
    """Deterministic single edit: swap, drop or double one interior letter."""
    letters = [i for i, ch in enumerate(word) if ch.isalpha() and 0 < i < len(word) - 1]
    if not letters:
        return word
    i = rng.choice(letters)
    op = rng.choice(["swap", "drop", "double"])
    if op == "swap" and i + 1 < len(word) and word[i + 1].isalpha() and word[i] != word[i + 1]:
        return word[:i] + word[i + 1] + word[i] + word[i + 2 :]
    if op == "drop":
        return word[:i] + word[i + 1 :]
    return word[:i] + word[i] + word[i:]


def load_skill_strings() -> list[tuple[str, str]]:
    """Distinct (raw, slug) pairs used by the synthetic profiles and job descriptions."""
    pairs: set[tuple[str, str]] = set()
    for f in sorted((DATA_DIR / "profiles").glob("*.gt.json")):
        for s in json.loads(f.read_text(encoding="utf-8"))["skills"]:
            if s.get("canonical_slug"):
                pairs.add((s["raw"], s["canonical_slug"]))
    for f in sorted((DATA_DIR / "jobs").glob("*.gt.json")):
        for r in json.loads(f.read_text(encoding="utf-8"))["requirements"]:
            pairs.add((r["skill_name"], r["skill_slug"]))
    return sorted(pairs)


def build_rows() -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(raw: str, context: str, slug: str, case_type: str) -> None:
        key = raw.lower()
        if key in seen:
            return
        seen.add(key)
        rows.append(
            {
                "raw": raw,
                "context": context,
                "expected_slug": slug,
                "case_type": case_type,
                "is_hard_case": case_type != "alias",
            }
        )

    # Hard cases first so they win any surface-form collision. Ambiguous rows reuse the
    # surface form on purpose, so they bypass the dedupe.
    for raw, context, slug in AMBIGUOUS_CASES:
        rows.append(
            {
                "raw": raw,
                "context": context,
                "expected_slug": slug,
                "case_type": "ambiguous",
                "is_hard_case": True,
            }
        )
        seen.add(raw.lower())
    for raw, slug in VERSION_CASES:
        add(raw, rng.choice(HARD_CONTEXTS).format(x=raw), slug, "version")
    for raw, slug in MULTI_CASES:
        add(raw, rng.choice(HARD_CONTEXTS).format(x=raw), slug, "multi_skill")
    for raw, slug in ABBREVIATION_CASES:
        add(raw, rng.choice(HARD_CONTEXTS).format(x=raw), slug, "abbreviation")
    for raw, context in UNKNOWN_CASES:
        add(raw, context, "NEW", "unknown")

    skill_strings = load_skill_strings()
    typo_sources = [
        (raw, slug) for raw, slug in skill_strings if sum(c.isalpha() for c in raw) >= 5
    ]
    with open(TAXONOMY_DIR / "aliases.csv", encoding="utf-8") as f:
        aliases = [a for a in csv.DictReader(f) if a["ambiguous"] == "false"]
    common = [
        (a["alias"], a["slug"])
        for a in aliases
        if a["source"] in ("curated", "wikidata") and len(a["alias"]) >= 6 and " " not in a["alias"]
    ]
    rng.shuffle(common)
    for raw, slug in [*typo_sources, *common]:
        if sum(r["case_type"] == "typo" for r in rows) >= 160:
            break
        typo = make_typo(raw, rng)
        if typo != raw:
            add(typo, rng.choice(HARD_CONTEXTS).format(x=typo), slug, "typo")

    # Easy rows: real skill strings from the corpora, then a taxonomy alias sample.
    for raw, slug in skill_strings:
        add(raw, rng.choice(EASY_CONTEXTS).format(x=raw), slug, "alias")
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for a in aliases:
        by_source[a["source"]].append(a)
    for pool in by_source.values():
        rng.shuffle(pool)
    order = ["curated", "wikidata", "variant", "onet"]
    while len(rows) < TARGET_ROWS and any(by_source[s] for s in order):
        for src in order:
            if by_source[src] and len(rows) < TARGET_ROWS:
                a = by_source[src].pop()
                add(a["alias"], rng.choice(EASY_CONTEXTS).format(x=a["alias"]), a["slug"], "alias")

    # 50/50 val/test, stratified by case type.
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_type[r["case_type"]].append(r)
    for case_type in sorted(by_type):
        group = by_type[case_type]
        rng.shuffle(group)
        for i, r in enumerate(group):
            r["split"] = "val" if i % 2 == 0 else "test"
    return rows


def validate(rows: list[dict[str, Any]]) -> list[str]:
    with open(TAXONOMY_DIR / "skills.csv", encoding="utf-8") as f:
        slugs = {r["slug"] for r in csv.DictReader(f)}
    errors = []
    for r in rows:
        for slug in str(r["expected_slug"]).split("|"):
            if slug != "NEW" and slug not in slugs:
                errors.append(f"{r['raw']!r}: unknown slug {slug!r}")
    return errors


def write_rows(rows: list[dict[str, Any]]) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(GOLD_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def print_stats() -> bool:
    with open(GOLD_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    hard = sum(r["is_hard_case"] == "True" for r in rows)
    errors = validate(rows)
    print("\n================ TALENTGRAPH NORMALIZATION GOLD STATS ================")
    print(f"Rows: {len(rows)}   hard cases: {hard} ({hard / len(rows) * 100:.1f}%)")
    print(
        "Case types: "
        + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r["case_type"] for r in rows).items()))
    )
    print(
        "Splits:     "
        + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r["split"] for r in rows).items()))
    )
    print(f"Unknown expected slugs: {len(errors)}")
    for e in errors[:10]:
        print(f"  {e}")
    passes = len(rows) >= 1000 and hard / len(rows) >= 0.25 and not errors
    print(f"\nExit criterion 1-G (normalization gold): {'PASS' if passes else 'FAIL'}")
    print("======================================================================\n")
    return passes


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the normalization gold set")
    parser.add_argument("--stats", action="store_true", help="Only print statistics")
    args = parser.parse_args()
    if not args.stats:
        rows = build_rows()
        errors = validate(rows)
        if errors:
            print("\n".join(errors))
            return 1
        write_rows(rows)
    return 0 if print_stats() else 1


if __name__ == "__main__":
    sys.exit(main())
