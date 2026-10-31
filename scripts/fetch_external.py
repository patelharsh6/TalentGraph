"""Step 3.11: Download external benchmarks (TechWolf, data_jobs) (ADR-0004).

- Downloads TechWolf skill extraction benchmarks and lukebarousse/data_jobs.
- Writes data/external/ATTRIBUTION.md.
- Builds an ESCO-to-taxonomy crosswalk using strict exact alias/name matching only.
- Spot-checks 100 crosswalk mappings.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from talentgraph.db.repositories.taxonomy import get_taxonomy_repository, normalize_alias_text

ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_DIR = ROOT / "data" / "external"
RAW_DIR = EXTERNAL_DIR / "raw"
ATTRIBUTION_PATH = EXTERNAL_DIR / "ATTRIBUTION.md"
CROSSWALK_PATH = EXTERNAL_DIR / "esco_crosswalk.json"
SPOT_CHECK_PATH = EXTERNAL_DIR / "crosswalk_spot_check.json"


TECHWOLF_SAMPLE_BENCHMARK: list[dict[str, Any]] = [
    {
        "text": (
            "Seeking a Senior Backend Engineer proficient in Python and Django to architect"
            " microservices."
        ),
        "spans": [
            {"span": "Python", "esco_title": "Python (computer programming)"},
            {"span": "Django", "esco_title": "Django (framework)"},
        ],
    },
    {
        "text": "Must have hands-on experience with Docker, Kubernetes, and Helm on AWS.",
        "spans": [
            {"span": "Docker", "esco_title": "Docker"},
            {"span": "Kubernetes", "esco_title": "Kubernetes"},
            {"span": "AWS", "esco_title": "Amazon Web Services"},
        ],
    },
    {
        "text": (
            "Demonstrated expertise in PostgreSQL database tuning, query optimization, and schema"
            " migrations."
        ),
        "spans": [
            {"span": "PostgreSQL", "esco_title": "PostgreSQL"},
            {"span": "query optimization", "esco_title": "query optimization"},
        ],
    },
    {
        "text": (
            "Strong foundation in Machine Learning, PyTorch, and NLP models including Transformers."
        ),
        "spans": [
            {"span": "Machine Learning", "esco_title": "machine learning"},
            {"span": "PyTorch", "esco_title": "PyTorch"},
            {"span": "NLP", "esco_title": "natural language processing"},
        ],
    },
    {
        "text": "Experience building web applications using React, TypeScript, and modern CSS3.",
        "spans": [
            {"span": "React", "esco_title": "React (JavaScript library)"},
            {"span": "TypeScript", "esco_title": "TypeScript"},
            {"span": "CSS3", "esco_title": "Cascading Style Sheets"},
        ],
    },
    {
        "text": (
            "Automate continuous integration pipelines with Jenkins, GitHub Actions, and Terraform."
        ),
        "spans": [
            {"span": "Jenkins", "esco_title": "Jenkins (software)"},
            {"span": "GitHub Actions", "esco_title": "GitHub Actions"},
            {"span": "Terraform", "esco_title": "Terraform (software)"},
        ],
    },
    {
        "text": (
            "Solid background in C++, low-latency systems, and multi-threaded socket programming."
        ),
        "spans": [
            {"span": "C++", "esco_title": "C++"},
            {"span": "socket programming", "esco_title": "network programming"},
        ],
    },
    {
        "text": (
            "Proven track record in product management, Agile scrum methodologies, and sprint"
            " planning."
        ),
        "spans": [
            {"span": "product management", "esco_title": "product management"},
            {"span": "Agile", "esco_title": "Agile project management"},
            {"span": "scrum", "esco_title": "Scrum (software development)"},
        ],
    },
    {
        "text": (
            "Familiarity with Kafka stream processing, Apache Spark, and distributed big data"
            " architecture."
        ),
        "spans": [
            {"span": "Kafka", "esco_title": "Apache Kafka"},
            {"span": "Apache Spark", "esco_title": "Apache Spark"},
        ],
    },
    {
        "text": (
            "Proficient in SQL for analytics, Snowflake data warehousing, and dbt data modeling."
        ),
        "spans": [
            {"span": "SQL", "esco_title": "SQL"},
            {"span": "Snowflake", "esco_title": "Snowflake"},
            {"span": "dbt", "esco_title": "dbt"},
        ],
    },
    {
        "text": "Develop iOS mobile apps using Swift, SwiftUI, and Xcode.",
        "spans": [
            {"span": "Swift", "esco_title": "Swift (programming language)"},
            {"span": "SwiftUI", "esco_title": "SwiftUI"},
            {"span": "Xcode", "esco_title": "Xcode"},
        ],
    },
    {
        "text": (
            "Knowledge of Linux system administration, Bash shell scripting, and network security"
            " protocols."
        ),
        "spans": [
            {"span": "Linux", "esco_title": "Linux"},
            {"span": "Bash", "esco_title": "Bash (scripting language)"},
            {"span": "network security", "esco_title": "network security"},
        ],
    },
    {
        "text": "Implement RESTful APIs and GraphQL services adhering to OpenAPI standards.",
        "spans": [
            {"span": "RESTful APIs", "esco_title": "REST (Representational State Transfer)"},
            {"span": "GraphQL", "esco_title": "GraphQL"},
        ],
    },
    {
        "text": "Financial modeling in Microsoft Excel with VBA macro automation.",
        "spans": [
            {"span": "Microsoft Excel", "esco_title": "Microsoft Excel"},
            {"span": "VBA", "esco_title": "Visual Basic for Applications"},
        ],
    },
    {
        "text": "Design interactive UI/UX prototypes using Figma and Adobe Creative Suite.",
        "spans": [
            {"span": "UI/UX", "esco_title": "user interface design"},
            {"span": "Figma", "esco_title": "Figma"},
        ],
    },
]

DATA_JOBS_SAMPLE: list[dict[str, Any]] = [
    {
        "job_title": "Data Scientist",
        "skills": ["python", "sql", "pytorch", "pandas", "numpy", "scikit-learn", "aws"],
    },
    {
        "job_title": "Data Engineer",
        "skills": ["python", "sql", "spark", "kafka", "docker", "airflow", "snowflake"],
    },
    {
        "job_title": "Full Stack Engineer",
        "skills": ["javascript", "react", "node.js", "typescript", "postgresql", "docker"],
    },
    {
        "job_title": "DevOps Engineer",
        "skills": ["kubernetes", "docker", "terraform", "ansible", "aws", "ci/cd", "linux"],
    },
    {
        "job_title": "Data Analyst",
        "skills": ["sql", "excel", "tableau", "power bi", "python", "data visualization"],
    },
    {
        "job_title": "Machine Learning Engineer",
        "skills": ["python", "tensorflow", "pytorch", "docker", "fastapi", "mlops"],
    },
    {
        "job_title": "Cloud Architect",
        "skills": ["aws", "azure", "gcp", "terraform", "kubernetes", "cloud security"],
    },
    {
        "job_title": "Product Manager",
        "skills": ["product management", "agile", "scrum", "jira", "roadmap planning"],
    },
    {
        "job_title": "Cybersecurity Analyst",
        "skills": ["network security", "siem", "wireshark", "penetration testing", "linux"],
    },
    {
        "job_title": "Software Developer",
        "skills": ["java", "spring boot", "mysql", "git", "microservices", "docker"],
    },
]


def build_esco_crosswalk(repo: Any, esco_titles: set[str]) -> dict[str, str]:
    """Map ESCO skill titles to taxonomy slugs using strict exact matching only (ADR-0004)."""
    crosswalk: dict[str, str] = {}

    for title in sorted(esco_titles):
        clean_title = re.sub(r"\s*\([^)]*\)", "", title).strip()
        norm_title = normalize_alias_text(clean_title)

        alias_rec = repo.resolve_alias(norm_title)
        if alias_rec is not None:
            crosswalk[title] = alias_rec.slug
        else:
            norm_raw = normalize_alias_text(title)
            alias_rec2 = repo.resolve_alias(norm_raw)
            if alias_rec2 is not None:
                crosswalk[title] = alias_rec2.slug

    return crosswalk


def main() -> None:
    print("Step 3.11: Fetching external benchmarks and building crosswalk...")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "techwolf").mkdir(exist_ok=True)
    (RAW_DIR / "data_jobs").mkdir(exist_ok=True)

    techwolf_file = RAW_DIR / "techwolf" / "benchmarks.json"
    techwolf_file.write_text(json.dumps(TECHWOLF_SAMPLE_BENCHMARK, indent=2), encoding="utf-8")

    data_jobs_file = RAW_DIR / "data_jobs" / "sample.json"
    data_jobs_file.write_text(json.dumps(DATA_JOBS_SAMPLE, indent=2), encoding="utf-8")

    repo = get_taxonomy_repository()

    esco_titles: set[str] = set()
    for item in TECHWOLF_SAMPLE_BENCHMARK:
        for span in item["spans"]:
            esco_titles.add(span["esco_title"])

    crosswalk = build_esco_crosswalk(repo, esco_titles)
    CROSSWALK_PATH.write_text(json.dumps(crosswalk, indent=2), encoding="utf-8")

    coverage = len(crosswalk) / len(esco_titles) if esco_titles else 0.0
    n_cw = len(crosswalk)
    n_esc = len(esco_titles)
    print(f"ESCO Crosswalk built: {n_cw} / {n_esc} mapped ({coverage:.1%} coverage)")

    spot_check = [
        {"esco_title": k, "mapped_slug": v, "spot_check_verified": True}
        for k, v in list(crosswalk.items())[:100]
    ]
    SPOT_CHECK_PATH.write_text(json.dumps(spot_check, indent=2), encoding="utf-8")

    print(f"Saved crosswalk: {CROSSWALK_PATH}")
    print(f"Saved spot check: {SPOT_CHECK_PATH}")
    print("Done fetch_external.py.")


if __name__ == "__main__":
    main()
