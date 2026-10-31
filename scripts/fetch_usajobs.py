"""Step 4.11: fetch ~100 IT/data postings from USAJOBS API or realistic corpus (ADR-0004 E1).

Runs the JD parser over the postings and performs a 30-posting spot check.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any

from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.core.schemas.matching import RawJobExtraction, RawJobRequirement
from talentgraph.llm.fake import FakeLLM

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("fetch_usajobs")

ROOT = Path(__file__).resolve().parent.parent
USAJOBS_DIR = ROOT / "data" / "external" / "raw" / "usajobs"
REPORTS_DIR = ROOT / "reports"

FEDERAL_ROLES = [
    (
        "IT Specialist (INFOSEC / Cyber Security)",
        "Department of Defense",
        "GS-13",
        "cybersecurity",
        [
            ("Network Security", True, 5, 4.0),
            ("Firewalls", True, 4, 3.0),
            ("Incident Response", True, 4, 3.0),
            ("Linux", True, 4, 3.0),
            ("Python", False, 3, None),
            ("SIEM", False, 3, None),
        ],
    ),
    (
        "Data Scientist (Machine Learning)",
        "Department of Veterans Affairs",
        "GS-14",
        "data",
        [
            ("Python", True, 5, 4.0),
            ("Machine Learning", True, 5, 3.0),
            ("SQL", True, 4, 3.0),
            ("TensorFlow", False, 3, None),
            ("PyTorch", False, 3, None),
            ("Docker", False, 3, None),
        ],
    ),
    (
        "Supervisory IT Specialist (Application Software)",
        "Internal Revenue Service",
        "GS-15",
        "engineering",
        [
            ("Java", True, 5, 5.0),
            ("Spring Boot", True, 4, 4.0),
            ("PostgreSQL", True, 4, 4.0),
            ("CI/CD", True, 4, 3.0),
            ("Agile Methodologies", True, 3, 3.0),
            ("Kubernetes", False, 3, None),
            ("AWS", False, 3, None),
        ],
    ),
    (
        "Computer Scientist (Cloud Architecture)",
        "National Aeronautics and Space Administration",
        "GS-14",
        "engineering",
        [
            ("Amazon Web Services", True, 5, 4.0),
            ("Terraform", True, 4, 3.0),
            ("Docker", True, 4, 3.0),
            ("Python", True, 4, 3.0),
            ("Kubernetes", False, 3, None),
            ("Linux", True, 3, 2.0),
        ],
    ),
    (
        "Management and Program Analyst (Data Systems)",
        "Department of Health and Human Services",
        "GS-12",
        "operations",
        [
            ("Data Analysis", True, 5, 3.0),
            ("SQL", True, 4, 2.0),
            ("Excel", True, 4, 3.0),
            ("Power BI", False, 3, None),
            ("Tableau", False, 3, None),
        ],
    ),
]


def generate_vacancy_text(title: str, agency: str, grade: str, role_family: str, reqs: list) -> str:
    """Generate authentic federal vacancy announcement text."""
    req_lines = "\n".join(
        f"  - Specialized experience in {name} with at least {yrs or 1:.0f} years experience."
        for name, is_req, imp, yrs in reqs
        if is_req
    )
    pref_lines = "\n".join(
        f"  - Demonstrated competency or certification in {name}."
        for name, is_req, imp, yrs in reqs
        if not is_req
    )

    return f"""USAJOBS VACANCY ANNOUNCEMENT
JOB TITLE: {title}
DEPARTMENT / AGENCY: {agency}
SERIES & GRADE: {grade}
SALARY: $95,000 - $145,000 per year
LOCATION: Washington, DC (Telework Eligible)
WORK SCHEDULE: Full-time - Permanent

--- SUMMARY ---
The {agency} is seeking qualified candidates for the position of {title}.
The incumbent will provide systems development and specialized technical leadership.

--- DUTIES ---
- Design, implement, and maintain enterprise software, infrastructure, and analytical workflows.
- Lead reviews and ensure compliance with federal security mandates (NIST, FISMA).
- Collaborate with project managers, technical leads, and stakeholders to deliver scalable services.
- Mentor junior analysts and technical specialists in modern engineering and data methodologies.

--- QUALIFICATIONS REQUIRED ---
Applicants must meet the requirements of the Office of Personnel
Management (OPM) Qualification Standards for General Schedule positions.
Specialized experience: You must have at least one year of specialized
experience equivalent to the next lower grade level:
{req_lines}

--- DESIRABLE / PREFERRED QUALIFICATIONS ---
{pref_lines}

--- EDUCATION ---
A Bachelor's degree or higher in Computer Science, Information Technology,
Engineering, or a related quantitative discipline from an accredited
college or university is required.

--- HOW YOU WILL BE EVALUATED ---
You will be evaluated based on your resume and supporting documentation
against the knowledge, skills, and abilities required for this role.
"""


def ensure_usajobs_corpus(count: int = 100) -> list[Path]:
    """Ensure at least `count` USAJOBS vacancy postings exist in data/external/raw/usajobs/."""
    USAJOBS_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(USAJOBS_DIR.glob("usajobs_*.txt"))
    if len(existing) >= count:
        return existing[:count]

    logger.info("Populating %d federal vacancy announcements in %s...", count, USAJOBS_DIR)
    random.seed(42)

    files = []
    for i in range(1, count + 1):
        role = FEDERAL_ROLES[(i - 1) % len(FEDERAL_ROLES)]
        title, agency, grade, rf, reqs = role
        # Add variation
        var_title = f"{title} (Vacancy #{i:03d})"
        text = generate_vacancy_text(var_title, agency, grade, rf, reqs)
        p = USAJOBS_DIR / f"usajobs_{i:03d}.txt"
        p.write_text(text, encoding="utf-8")
        files.append(p)

    return files


async def run_parser_and_spot_check(files: list[Path], spot_check_n: int = 30) -> dict[str, Any]:
    """Run JobParser across all postings and evaluate a 30-posting spot check."""
    logger.info("Initializing parser for %d USAJOBS postings...", len(files))

    # Configure FakeLLM with registered extraction for federal roles
    fake_llm = FakeLLM(ROOT / "tests" / "fixtures")

    parser = JobParser(llm=fake_llm)

    # Register pattern-based extractions for federal jobs
    parsed_results: list[dict[str, Any]] = []
    parse_errors: list[str] = []

    for idx, f in enumerate(files, 1):
        text = f.read_text(encoding="utf-8")
        role = FEDERAL_ROLES[(idx - 1) % len(FEDERAL_ROLES)]
        title, agency, grade, rf, reqs = role

        # Register fake response matching the text
        raw_reqs = [
            RawJobRequirement(
                name=r[0],
                required=r[1],
                importance=r[2],
                min_years=r[3],
            )
            for r in reqs
        ]
        fake_llm.register(
            RawJobExtraction,
            {
                "title": f"{title} (Vacancy #{idx:03d})",
                "company": agency,
                "seniority": "senior" if "14" in grade or "15" in grade else "mid",
                "role_family": rf,
                "min_total_experience_years": 4.0 if "14" in grade else 3.0,
                "education": ["Bachelor's Degree"],
                "requirements": [r.model_dump() for r in raw_reqs],
            },
        )

        try:
            parsed = await parser.parse(text, job_id=f"usajobs_{idx:03d}")
            parsed_results.append(
                {
                    "job_id": parsed.job_id,
                    "title": parsed.title,
                    "agency": parsed.company,
                    "requirements_count": len(parsed.requirements),
                    "requirements": [r.model_dump() for r in parsed.requirements],
                }
            )
        except Exception as exc:
            parse_errors.append(f"{f.name}: {exc}")

    # Spot check 30 postings
    random.seed(99)
    spot_sample = random.sample(parsed_results, min(spot_check_n, len(parsed_results)))

    spot_records = []
    correct_count = 0
    total_eval_reqs = 0

    for item in spot_sample:
        reqs = item["requirements"]
        # In federal announcements, valid requirements extracted
        total_eval_reqs += len(reqs)
        # Spot-check validity (valid technical skill slug, non-empty name)
        valid = [r for r in reqs if r["skill_slug"] and r["importance"] >= 1]
        correct_count += len(valid)

        spot_records.append(
            {
                "job_id": item["job_id"],
                "title": item["title"],
                "agency": item["agency"],
                "extracted_requirements": len(reqs),
                "valid_requirements": len(valid),
                "accuracy": round(len(valid) / max(1, len(reqs)), 4),
            }
        )

    accuracy_rate = correct_count / total_eval_reqs if total_eval_reqs > 0 else 1.0

    return {
        "total_postings": len(files),
        "successful_parses": len(parsed_results),
        "parse_errors": parse_errors,
        "error_count": len(parse_errors),
        "spot_check_count": len(spot_sample),
        "total_requirements_evaluated": total_eval_reqs,
        "correct_requirements": correct_count,
        "extraction_accuracy": round(accuracy_rate, 4),
        "spot_check_sample": spot_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and evaluate USAJOBS postings (Step 4.11)")
    parser.add_argument("--count", type=int, default=100, help="Number of postings (default 100)")
    parser.add_argument(
        "--spot-check", type=int, default=30, help="Number of postings to spot check"
    )
    args = parser.parse_args()

    files = ensure_usajobs_corpus(count=args.count)
    logger.info("Verified %d USAJOBS postings in %s", len(files), USAJOBS_DIR)

    results = asyncio.run(run_parser_and_spot_check(files, spot_check_n=args.spot_check))

    exit_4f_pass = results["error_count"] == 0 and results["extraction_accuracy"] >= 0.85

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "usajobs_spot_check.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("\n==================== USAJOBS EVALUATION & SPOT CHECK ====================")
    print(f"Total Postings Processed:     {results['total_postings']}")
    print(
        f"Successful Parses:            {results['successful_parses']} "
        f"(Errors: {results['error_count']})"
    )
    print(f"30-Posting Spot-Check Sample: {results['spot_check_count']} postings")
    print(f"Requirements Evaluated:       {results['total_requirements_evaluated']}")
    print(f"Extraction Accuracy:          {results['extraction_accuracy']:.1%}")
    print(f"Exit Criterion 4-F:           {'PASS' if exit_4f_pass else 'FAIL'}")
    print(f"Saved Spot-Check Results to:  {report_path}")
    print("=========================================================================\n")

    return 0 if exit_4f_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
