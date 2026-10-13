"""Phase 1.8: Generate synthetic job descriptions and ground truth requirements.

Generates >= 110 realistic job descriptions across engineering, data science,
product management, design, DevOps, marketing, finance, and operations.
Outputs both job_xxx.txt and job_xxx.gt.json conforming to JobRequirements.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path
from typing import Any

from faker import Faker

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("gen_jobs")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
JOBS_DIR = DATA_DIR / "jobs"

fake = Faker()
Faker.seed(1337)
random.seed(1337)

JOB_TEMPLATES = [
    {
        "role_family": "engineering",
        "title_template": "{seniority_prefix}Backend Software Engineer ({specialty})",
        "specialties": [
            "Python/FastAPI",
            "Go/Distributed Systems",
            "Java/Spring Boot",
            "Rust/High Performance",
            "Node.js/TypeScript",
        ],
        "core_skills": [
            ("python", "Python", True, 5, 3.0),
            ("fastapi", "FastAPI", True, 4, 2.0),
            ("postgresql", "PostgreSQL", True, 4, 3.0),
            ("docker", "Docker", True, 4, 2.0),
            ("kubernetes", "Kubernetes", False, 3, 1.0),
            ("redis", "Redis", False, 3, 1.0),
            ("amazon-web-services", "AWS", False, 3, 2.0),
        ],
    },
    {
        "role_family": "engineering",
        "title_template": "{seniority_prefix}Frontend Web Engineer ({specialty})",
        "specialties": ["React/Next.js", "TypeScript/Tailwind", "Vue.js/Nuxt", "Design Systems"],
        "core_skills": [
            ("javascript", "JavaScript", True, 5, 3.0),
            ("typescript", "TypeScript", True, 5, 3.0),
            ("react", "React", True, 5, 3.0),
            ("next-js", "Next.js", True, 4, 2.0),
            ("tailwindcss", "Tailwind CSS", False, 3, 1.0),
            ("html5", "HTML5", True, 4, 3.0),
            ("css3", "CSS3", True, 4, 3.0),
            ("figma", "Figma", False, 2, 1.0),
        ],
    },
    {
        "role_family": "data",
        "title_template": "{seniority_prefix}Machine Learning Engineer ({specialty})",
        "specialties": [
            "LLMs & Generative AI",
            "Computer Vision",
            "NLP & Information Retrieval",
            "Recommendation Systems",
        ],
        "core_skills": [
            ("python", "Python", True, 5, 4.0),
            ("pytorch", "PyTorch", True, 5, 3.0),
            ("machine-learning", "Machine Learning", True, 5, 4.0),
            ("deep-learning", "Deep Learning", True, 5, 3.0),
            ("large-language-models", "Large Language Models", True, 4, 2.0),
            ("retrieval-augmented-generation", "RAG", False, 4, 1.0),
            ("vector-databases", "Vector Databases", False, 3, 1.0),
            ("docker", "Docker", False, 3, 2.0),
            ("machine-learning-operations", "MLOps", False, 3, 2.0),
        ],
    },
    {
        "role_family": "data",
        "title_template": "{seniority_prefix}Data Engineer ({specialty})",
        "specialties": [
            "Lakehouse Architecture",
            "Real-Time Streaming",
            "Data Warehousing",
            "dbt & Snowflake",
        ],
        "core_skills": [
            ("python", "Python", True, 5, 3.0),
            ("sql", "SQL", True, 5, 4.0),
            ("apache-spark", "Apache Spark", True, 4, 3.0),
            ("apache-airflow", "Apache Airflow", True, 4, 2.0),
            ("snowflake", "Snowflake", False, 4, 2.0),
            ("dbt", "dbt", False, 3, 1.0),
            ("apache-kafka", "Apache Kafka", False, 3, 2.0),
            ("data-engineering", "Data Engineering", True, 4, 3.0),
        ],
    },
    {
        "role_family": "cloud",
        "title_template": "{seniority_prefix}DevOps / Site Reliability Engineer ({specialty})",
        "specialties": [
            "Kubernetes & Cloud Infrastructure",
            "CI/CD Automation",
            "Security & SRE",
            "Multi-Cloud",
        ],
        "core_skills": [
            ("linux", "Linux", True, 5, 4.0),
            ("kubernetes", "Kubernetes", True, 5, 3.0),
            ("docker", "Docker", True, 5, 3.0),
            ("terraform", "Terraform", True, 4, 3.0),
            ("continuous-integration-and-continuous-delivery", "CI/CD", True, 4, 3.0),
            ("amazon-web-services", "AWS", True, 4, 3.0),
            ("prometheus", "Prometheus", False, 3, 2.0),
            ("grafana", "Grafana", False, 3, 2.0),
        ],
    },
    {
        "role_family": "product",
        "title_template": "{seniority_prefix}Product Manager ({specialty})",
        "specialties": [
            "B2B Enterprise SaaS",
            "AI/ML Products",
            "Growth & Monetization",
            "Platform & APIs",
        ],
        "core_skills": [
            ("product-management", "Product Management", True, 5, 4.0),
            ("product-roadmapping", "Product Roadmapping", True, 4, 3.0),
            ("user-stories", "User Stories", True, 4, 3.0),
            ("agile-methodology", "Agile Methodology", True, 4, 3.0),
            ("competitive-analysis", "Competitive Analysis", False, 3, 2.0),
            ("product-discovery", "Product Discovery", False, 3, 2.0),
            ("jira", "Jira", True, 3, 2.0),
        ],
    },
    {
        "role_family": "design",
        "title_template": "{seniority_prefix}Product Designer ({specialty})",
        "specialties": [
            "Design Systems",
            "User Research & Prototyping",
            "Mobile & Web UI",
            "Enterprise UX",
        ],
        "core_skills": [
            ("figma", "Figma", True, 5, 3.0),
            ("user-experience-design", "UX Design", True, 5, 4.0),
            ("user-interface-design", "UI Design", True, 5, 4.0),
            ("wireframing", "Wireframing", True, 4, 3.0),
            ("prototyping", "Prototyping", True, 4, 3.0),
            ("design-systems", "Design Systems", False, 4, 2.0),
            ("user-research", "User Research", False, 3, 2.0),
        ],
    },
    {
        "role_family": "finance",
        "title_template": "{seniority_prefix}Financial Analyst ({specialty})",
        "specialties": [
            "Corporate Finance & Valuation",
            "M&A Strategic Finance",
            "FP&A and Forecasting",
        ],
        "core_skills": [
            ("financial-modeling", "Financial Modeling", True, 5, 3.0),
            ("dcf-valuation", "DCF Valuation", True, 4, 2.0),
            ("financial-analysis", "Financial Analysis", True, 5, 3.0),
            ("gaap", "GAAP", True, 4, 2.0),
            ("corporate-finance", "Corporate Finance", True, 4, 3.0),
            ("bloomberg-terminal", "Bloomberg Terminal", False, 3, 1.0),
        ],
    },
    {
        "role_family": "marketing",
        "title_template": "{seniority_prefix}Growth Marketing Specialist ({specialty})",
        "specialties": [
            "SEO & Organic Search",
            "Paid Performance & SEM",
            "Lifecycle & Funnel Optimization",
        ],
        "core_skills": [
            ("search-engine-optimization", "SEO", True, 5, 3.0),
            ("search-engine-marketing", "SEM", True, 4, 2.0),
            ("google-analytics", "Google Analytics", True, 4, 3.0),
            ("growth-marketing", "Growth Marketing", True, 4, 3.0),
            ("conversion-rate-optimization", "CRO", False, 3, 2.0),
            ("hubspot", "HubSpot", False, 3, 1.0),
        ],
    },
    {
        "role_family": "healthcare",
        "title_template": "{seniority_prefix}Health Informatics Specialist ({specialty})",
        "specialties": [
            "Clinical Systems Integration",
            "EHR Interoperability & FHIR",
            "Digital Health",
        ],
        "core_skills": [
            ("electronic-health-records", "EHR", True, 5, 3.0),
            ("epic-systems", "Epic Systems", True, 4, 2.0),
            ("hl7-fhir", "HL7 / FHIR", True, 4, 2.0),
            ("hipaa-compliance", "HIPAA Compliance", True, 5, 3.0),
            ("clinical-trials", "Clinical Trials", False, 3, 1.0),
            ("python", "Python", False, 3, 1.0),
        ],
    },
    {
        "role_family": "manufacturing",
        "title_template": "{seniority_prefix}Industrial Automation & SCADA Engineer ({specialty})",
        "specialties": ["PLC Programming & Robotics", "IoT & Edge Systems", "Supply Chain Quality"],
        "core_skills": [
            ("scada", "SCADA", True, 5, 3.0),
            ("plc-programming", "PLC Programming", True, 5, 3.0),
            ("internet-of-things", "IoT", True, 4, 2.0),
            ("embedded-c", "Embedded C", True, 4, 2.0),
            ("six-sigma", "Six Sigma", False, 3, 2.0),
            ("supply-chain-management", "Supply Chain Management", False, 3, 2.0),
        ],
    },
]


def generate_single_job(idx: int) -> tuple[str, dict[str, Any]]:
    """Generate text description and ground truth requirements for a job."""
    tpl = JOB_TEMPLATES[idx % len(JOB_TEMPLATES)]
    seniority = random.choice(["junior", "mid", "senior", "lead", "principal"])
    seniority_prefix = (
        f"{seniority.capitalize()} " if seniority in ("senior", "lead", "principal") else ""
    )
    specialty = random.choice(tpl["specialties"])
    title = tpl["title_template"].format(seniority_prefix=seniority_prefix, specialty=specialty)

    company = fake.company()
    city = fake.city()
    state = fake.state_abbr()

    min_exp_years = {
        "junior": 1.0,
        "mid": 3.0,
        "senior": 5.0,
        "lead": 8.0,
        "principal": 12.0,
    }[seniority]

    requirements: list[dict[str, Any]] = []
    for sk_slug, sk_name, req, imp, base_years in tpl["core_skills"]:
        sk_years = (
            base_years
            if seniority in ("senior", "lead", "principal")
            else max(1.0, base_years - 1.0)
        )
        requirements.append(
            {
                "skill_slug": sk_slug,
                "skill_name": sk_name,
                "required": req,
                "importance": imp,
                "min_years": sk_years if req else None,
            }
        )

    required_reqs = [r for r in requirements if r["required"]]
    preferred_reqs = [r for r in requirements if not r["required"]]

    # Construct Job Description Text
    lines = [
        f"JOB TITLE: {title}",
        f"COMPANY: {company}",
        f"LOCATION: {city}, {state} (Hybrid / Remote Available)",
        f"SENIORITY LEVEL: {seniority.capitalize()}",
        f"MINIMUM RELEVANT EXPERIENCE: {min_exp_years:.0f}+ Years",
        "",
        "--- ROLE OVERVIEW ---",
        (
            f"{company} is seeking an exceptional {title} to lead key initiatives within our "
            f"{tpl['role_family'].capitalize()} organization."
        ),
        (
            "In this role, you will architect, build, and deploy mission-critical solutions "
            "that directly impact our customers and platform scale."
        ),
        "",
        "--- KEY RESPONSIBILITIES ---",
        "• Design and maintain scalable, secure, and resilient systems.",
        "• Drive technical strategy and mentor team members in technical execution.",
        "• Collaborate cross-functionally with product managers and designers.",
        "• Deliver measurable impact on product performance and reliability.",
        "",
        "--- REQUIRED QUALIFICATIONS ---",
    ]
    for r in required_reqs:
        years_txt = f" ({r['min_years']:.0f}+ years experience)" if r.get("min_years") else ""
        lines.append(f"• Proven expertise in {r['skill_name']}{years_txt}")
    lines.append(f"• Minimum of {min_exp_years:.0f}+ years of experience in {tpl['role_family']}.")
    lines.append(
        "• Bachelor's or Master's degree in relevant field, or equivalent practical experience."
    )

    lines.extend(
        [
            "",
            "--- PREFERRED / NICE-TO-HAVE QUALIFICATIONS ---",
        ]
    )
    for r in preferred_reqs:
        lines.append(f"• Familiarity or hands-on experience with {r['skill_name']}.")

    lines.extend(
        [
            "",
            "--- WHAT WE OFFER ---",
            "• Competitive compensation package with equity options and performance bonuses.",
            "• Comprehensive health, dental, and vision insurance with 401(k) matching.",
            "• Flexible work environment and generous paid time off (PTO).",
        ]
    )

    job_text = "\n".join(lines)

    gt_data = {
        "title": title,
        "company": company,
        "role_family": tpl["role_family"],
        "seniority": seniority,
        "min_total_experience_years": min_exp_years,
        "education": ["Bachelor's Degree", "Master's Degree"],
        "requirements": requirements,
        "raw_text_length": len(job_text),
    }

    return job_text, gt_data


def generate_all_jobs(count: int = 120) -> None:
    """Generate >= 110 job descriptions and ground truth JSON requirements."""
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Generating %d job descriptions and ground truth specifications...", count)

    for i in range(count):
        job_text, gt_data = generate_single_job(i)

        txt_file = JOBS_DIR / f"job_{i:03d}.txt"
        gt_file = JOBS_DIR / f"job_{i:03d}.gt.json"

        txt_file.write_text(job_text + "\n", encoding="utf-8", newline="\n")
        gt_file.write_text(json.dumps(gt_data, indent=2) + "\n", encoding="utf-8", newline="\n")

    logger.info("Successfully generated %d jobs in %s", count, JOBS_DIR)


def print_job_stats() -> None:
    """Print job dataset statistics."""
    txt_files = list(JOBS_DIR.glob("job_*.txt"))
    gt_files = list(JOBS_DIR.glob("job_*.gt.json"))

    print("\n==================== TALENTGRAPH JOB CORPUS STATS ====================")
    print(f"Total Job Text Files:         {len(txt_files)}")
    print(f"Total Ground Truth GT Files:  {len(gt_files)}")

    role_families: dict[str, int] = {}
    seniorities: dict[str, int] = {}

    for gf in gt_files:
        try:
            data = json.loads(gf.read_text(encoding="utf-8"))
            rf = data.get("role_family", "unknown")
            sen = data.get("seniority", "unknown")
            role_families[rf] = role_families.get(rf, 0) + 1
            seniorities[sen] = seniorities.get(sen, 0) + 1
        except Exception:
            pass

    print("\nRole Families Breakdown:")
    for rf, c in sorted(role_families.items()):
        print(f"  - {rf:15s}: {c:3d} jobs")

    print("\nSeniority Breakdown:")
    for sen, c in sorted(seniorities.items()):
        print(f"  - {sen:15s}: {c:3d} jobs")
    print("======================================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic job descriptions")
    parser.add_argument(
        "--count", type=int, default=120, help="Number of jobs to generate (default: 120)"
    )
    parser.add_argument("--stats", action="store_true", help="Print job corpus statistics")
    args = parser.parse_args()

    if not args.stats:
        generate_all_jobs(count=args.count)

    print_job_stats()


if __name__ == "__main__":
    main()
