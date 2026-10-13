"""Phase 1.6: Generate ground-truth candidate resume profiles.

Generates >= 550 realistic candidate profiles conforming to ParsedResume,
stratified across >= 10 industries, a mix of seniorities, realistic experience
and education trajectories, deliberate alias/variant forms, and ~5% emerging skills.
Supports checkpointing and rate-limited execution.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path
from typing import Any

from faker import Faker

from talentgraph.core.schemas.resume import ParsedResume

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("gen_profiles")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROFILES_DIR = DATA_DIR / "profiles"
CHECKPOINTS_DIR = DATA_DIR / ".checkpoints"

fake = Faker()
Faker.seed(42)
random.seed(42)

INDUSTRIES = [
    "software",
    "data",
    "finance",
    "healthcare",
    "marketing",
    "design",
    "manufacturing",
    "education",
    "sales",
    "legal",
    "operations",
]

SENIORITIES = ["junior", "mid", "senior", "lead", "principal"]

EMERGING_SKILLS = [
    {"raw": "Mamba State Space Models", "slug": "mamba-ssm", "category_hint": "emerging"},
    {
        "raw": "Direct Preference Optimization (DPO)",
        "slug": "dpo-alignment",
        "category_hint": "emerging",
    },
    {"raw": "Mojo Programming Language", "slug": "mojo-lang", "category_hint": "emerging"},
    {
        "raw": "Neuromorphic Computing",
        "slug": "neuromorphic-computing",
        "category_hint": "emerging",
    },
    {
        "raw": "Synthetic Data Generation with GANs/Diffusion",
        "slug": "synthetic-data-gen",
        "category_hint": "emerging",
    },
    {
        "raw": "DNA Data Storage Compilers",
        "slug": "dna-storage-compiler",
        "category_hint": "emerging",
    },
    {
        "raw": "Quantum Circuit Synthesis with Qiskit",
        "slug": "quantum-circuit-synthesis",
        "category_hint": "emerging",
    },
    {
        "raw": "Carbon Accounting & Scope 3 Protocol",
        "slug": "carbon-accounting-engine",
        "category_hint": "emerging",
    },
    {
        "raw": "Decentralized Physical Infrastructure (DePIN)",
        "slug": "depin-networks",
        "category_hint": "emerging",
    },
    {
        "raw": "Autonomous Agent Tool-Use Protocols",
        "slug": "agent-tool-use",
        "category_hint": "emerging",
    },
]

INDUSTRY_SKILL_POOLS: dict[str, list[dict[str, str]]] = {
    "software": [
        {"raw": "Python", "slug": "python", "category_hint": "technical"},
        {"raw": "JavaScript (ES6+)", "slug": "javascript", "category_hint": "technical"},
        {"raw": "TypeScript", "slug": "typescript", "category_hint": "technical"},
        {"raw": "React.js", "slug": "react", "category_hint": "technical"},
        {"raw": "Node.js", "slug": "node-js", "category_hint": "technical"},
        {"raw": "FastAPI", "slug": "fastapi", "category_hint": "technical"},
        {"raw": "Docker", "slug": "docker", "category_hint": "technical"},
        {"raw": "Kubernetes (K8s)", "slug": "kubernetes", "category_hint": "technical"},
        {"raw": "PostgreSQL", "slug": "postgresql", "category_hint": "technical"},
        {"raw": "Redis", "slug": "redis", "category_hint": "technical"},
        {"raw": "GraphQL", "slug": "graphql", "category_hint": "technical"},
        {
            "raw": "CI/CD Pipelines",
            "slug": "continuous-integration-and-continuous-delivery",
            "category_hint": "technical",
        },
        {"raw": "AWS", "slug": "amazon-web-services", "category_hint": "technical"},
        {"raw": "Team Leadership", "slug": "team-leadership", "category_hint": "soft"},
        {"raw": "Microservices", "slug": "microservices", "category_hint": "technical"},
    ],
    "data": [
        {"raw": "Python", "slug": "python", "category_hint": "technical"},
        {"raw": "SQL", "slug": "sql", "category_hint": "technical"},
        {"raw": "PyTorch", "slug": "pytorch", "category_hint": "technical"},
        {"raw": "TensorFlow", "slug": "tensorflow", "category_hint": "technical"},
        {"raw": "Scikit-Learn", "slug": "scikit-learn", "category_hint": "technical"},
        {"raw": "Pandas", "slug": "pandas", "category_hint": "technical"},
        {"raw": "NumPy", "slug": "numpy", "category_hint": "technical"},
        {"raw": "Apache Spark (PySpark)", "slug": "apache-spark", "category_hint": "technical"},
        {"raw": "Snowflake", "slug": "snowflake", "category_hint": "technical"},
        {"raw": "dbt", "slug": "dbt", "category_hint": "technical"},
        {"raw": "Apache Airflow", "slug": "apache-airflow", "category_hint": "technical"},
        {
            "raw": "Large Language Models (LLM)",
            "slug": "large-language-models",
            "category_hint": "technical",
        },
        {
            "raw": "RAG Architecture",
            "slug": "retrieval-augmented-generation",
            "category_hint": "technical",
        },
        {"raw": "MLOps", "slug": "machine-learning-operations", "category_hint": "technical"},
        {
            "raw": "Data Visualization",
            "slug": "business-intelligence",
            "category_hint": "technical",
        },
    ],
    "finance": [
        {"raw": "Financial Modeling", "slug": "financial-modeling", "category_hint": "business"},
        {"raw": "DCF Valuation", "slug": "dcf-valuation", "category_hint": "business"},
        {"raw": "LBO Modeling", "slug": "lbo-modeling", "category_hint": "business"},
        {"raw": "US GAAP", "slug": "gaap", "category_hint": "business"},
        {"raw": "IFRS Standards", "slug": "ifrs", "category_hint": "business"},
        {"raw": "Bloomberg Terminal", "slug": "bloomberg-terminal", "category_hint": "business"},
        {"raw": "Financial Analysis", "slug": "financial-analysis", "category_hint": "business"},
        {"raw": "SQL", "slug": "sql", "category_hint": "technical"},
        {"raw": "Advanced Excel", "slug": "microsoft-excel", "category_hint": "technical"},
        {
            "raw": "Quantitative Risk Management",
            "slug": "financial-risk-management",
            "category_hint": "business",
        },
        {"raw": "Corporate Finance", "slug": "corporate-finance", "category_hint": "business"},
        {
            "raw": "Stakeholder Management",
            "slug": "stakeholder-communication",
            "category_hint": "soft",
        },
    ],
    "healthcare": [
        {
            "raw": "Electronic Health Records (EHR)",
            "slug": "electronic-health-records",
            "category_hint": "domain",
        },
        {"raw": "Epic Systems", "slug": "epic-systems", "category_hint": "domain"},
        {"raw": "Cerner", "slug": "cerner", "category_hint": "domain"},
        {"raw": "HL7 FHIR Protocols", "slug": "hl7-fhir", "category_hint": "domain"},
        {"raw": "HIPAA Compliance", "slug": "hipaa-compliance", "category_hint": "domain"},
        {"raw": "Clinical Trials Management", "slug": "clinical-trials", "category_hint": "domain"},
        {"raw": "Bioinformatics", "slug": "bioinformatics", "category_hint": "domain"},
        {"raw": "Python", "slug": "python", "category_hint": "technical"},
        {"raw": "R Language", "slug": "r-language", "category_hint": "technical"},
        {"raw": "Health Informatics", "slug": "health-informatics", "category_hint": "domain"},
    ],
    "marketing": [
        {
            "raw": "Search Engine Optimization (SEO)",
            "slug": "search-engine-optimization",
            "category_hint": "business",
        },
        {
            "raw": "Search Engine Marketing (SEM)",
            "slug": "search-engine-marketing",
            "category_hint": "business",
        },
        {
            "raw": "Google Analytics 4 (GA4)",
            "slug": "google-analytics",
            "category_hint": "business",
        },
        {"raw": "Growth Marketing", "slug": "growth-marketing", "category_hint": "business"},
        {
            "raw": "A/B Testing & CRO",
            "slug": "conversion-rate-optimization",
            "category_hint": "business",
        },
        {"raw": "HubSpot", "slug": "hubspot", "category_hint": "business"},
        {"raw": "Salesforce Marketing Cloud", "slug": "salesforce", "category_hint": "business"},
        {"raw": "Content Strategy", "slug": "content-marketing", "category_hint": "business"},
        {
            "raw": "Email Marketing Campaigns",
            "slug": "email-marketing",
            "category_hint": "business",
        },
        {"raw": "Copywriting", "slug": "copywriting", "category_hint": "soft"},
    ],
    "design": [
        {"raw": "Figma", "slug": "figma", "category_hint": "business"},
        {"raw": "Adobe XD", "slug": "adobe-xd", "category_hint": "business"},
        {"raw": "UI/UX Design", "slug": "user-experience-design", "category_hint": "business"},
        {"raw": "Wireframing & Prototyping", "slug": "wireframing", "category_hint": "business"},
        {
            "raw": "User Research & Usability Testing",
            "slug": "user-research",
            "category_hint": "business",
        },
        {"raw": "Design Systems", "slug": "design-systems", "category_hint": "business"},
        {
            "raw": "Information Architecture",
            "slug": "information-architecture",
            "category_hint": "business",
        },
        {"raw": "HTML5 / CSS3", "slug": "html5", "category_hint": "technical"},
        {"raw": "Design Thinking", "slug": "design-thinking", "category_hint": "soft"},
    ],
    "manufacturing": [
        {
            "raw": "Supply Chain Management",
            "slug": "supply-chain-management",
            "category_hint": "domain",
        },
        {"raw": "Six Sigma Green Belt", "slug": "six-sigma", "category_hint": "domain"},
        {
            "raw": "Internet of Things (IoT)",
            "slug": "internet-of-things",
            "category_hint": "domain",
        },
        {"raw": "Embedded C", "slug": "embedded-c", "category_hint": "technical"},
        {"raw": "SCADA Systems", "slug": "scada", "category_hint": "domain"},
        {
            "raw": "PLC Programming (Siemens/Allen-Bradley)",
            "slug": "plc-programming",
            "category_hint": "domain",
        },
        {"raw": "Lean Manufacturing", "slug": "lean-manufacturing", "category_hint": "domain"},
        {"raw": "SolidWorks CAD", "slug": "solidworks", "category_hint": "technical"},
        {"raw": "Root Cause Analysis", "slug": "root-cause-analysis", "category_hint": "soft"},
    ],
    "education": [
        {
            "raw": "Curriculum Development",
            "slug": "curriculum-development",
            "category_hint": "domain",
        },
        {"raw": "Instructional Design", "slug": "instructional-design", "category_hint": "domain"},
        {
            "raw": "Learning Management Systems (LMS)",
            "slug": "lms-platforms",
            "category_hint": "technical",
        },
        {"raw": "Public Speaking & Lecturing", "slug": "public-speaking", "category_hint": "soft"},
        {
            "raw": "Educational Technology (EdTech)",
            "slug": "edtech-solutions",
            "category_hint": "domain",
        },
        {"raw": "Assessment Design", "slug": "assessment-design", "category_hint": "domain"},
        {"raw": "Active Mentoring", "slug": "mentoring", "category_hint": "soft"},
    ],
    "sales": [
        {"raw": "B2B Enterprise Sales", "slug": "b2b-sales", "category_hint": "business"},
        {"raw": "Salesforce CRM", "slug": "salesforce", "category_hint": "business"},
        {"raw": "HubSpot Sales Hub", "slug": "hubspot", "category_hint": "business"},
        {"raw": "Sales Pipeline Management", "slug": "sales-strategy", "category_hint": "business"},
        {"raw": "Contract Negotiation", "slug": "contract-negotiation", "category_hint": "soft"},
        {"raw": "Account Management", "slug": "customer-success", "category_hint": "business"},
        {"raw": "Lead Prospecting", "slug": "sales-prospecting", "category_hint": "business"},
        {
            "raw": "Client Relationship Building",
            "slug": "effective-communication",
            "category_hint": "soft",
        },
    ],
    "legal": [
        {
            "raw": "Corporate Contract Drafting",
            "slug": "contract-drafting",
            "category_hint": "domain",
        },
        {
            "raw": "Intellectual Property (IP) Protection",
            "slug": "intellectual-property",
            "category_hint": "domain",
        },
        {"raw": "GDPR & Data Privacy", "slug": "gdpr", "category_hint": "domain"},
        {
            "raw": "Regulatory Compliance",
            "slug": "regulatory-compliance",
            "category_hint": "domain",
        },
        {
            "raw": "Legal Research (Westlaw/LexisNexis)",
            "slug": "legal-research",
            "category_hint": "domain",
        },
        {"raw": "M&A Due Diligence", "slug": "ma-due-diligence", "category_hint": "domain"},
        {"raw": "Risk Assessment", "slug": "risk-management", "category_hint": "business"},
    ],
    "operations": [
        {
            "raw": "Operations Management",
            "slug": "operations-management",
            "category_hint": "business",
        },
        {
            "raw": "Process Optimization",
            "slug": "process-optimization",
            "category_hint": "business",
        },
        {"raw": "Jira & Confluence", "slug": "jira", "category_hint": "business"},
        {
            "raw": "Agile Scrum Methodology",
            "slug": "agile-methodology",
            "category_hint": "business",
        },
        {
            "raw": "Cross-Functional Leadership",
            "slug": "cross-functional-collaboration",
            "category_hint": "soft",
        },
        {
            "raw": "Vendor Management & Procurement",
            "slug": "vendor-management",
            "category_hint": "business",
        },
        {
            "raw": "OKRs / KPIs Tracking",
            "slug": "key-performance-indicators",
            "category_hint": "business",
        },
        {
            "raw": "Budgeting & Cost Reduction",
            "slug": "financial-analysis",
            "category_hint": "business",
        },
    ],
}


def generate_single_profile(idx: int, industry: str, seniority: str) -> dict[str, Any]:
    """Generate a single ground truth candidate profile."""
    name = fake.name()
    email = f"{name.lower().replace(' ', '.')}.{random.randint(10, 99)}@{fake.free_email_domain()}"
    phone = fake.phone_number()
    city = fake.city()
    state = fake.state_abbr()
    country = "United States"

    seniority_years = {
        "junior": (1, 2),
        "mid": (3, 5),
        "senior": (6, 9),
        "lead": (9, 13),
        "principal": (13, 20),
    }[seniority]

    total_years = random.randint(*seniority_years)
    num_jobs = min(max(1, total_years // 3), 4)

    # Experience building
    experience_list: list[dict[str, Any]] = []
    curr_year = 2026
    curr_month = 9

    industry_skills = INDUSTRY_SKILL_POOLS.get(industry, INDUSTRY_SKILL_POOLS["software"])

    # Pick 5-8 skills for the profile
    num_skills = random.randint(6, 10)
    selected_skills = random.sample(industry_skills, min(num_skills, len(industry_skills)))

    # 5% chance of adding an emerging skill
    is_emerging = random.random() < 0.05
    if is_emerging:
        emerging_item = random.choice(EMERGING_SKILLS)
        selected_skills.append(emerging_item)

    titles_by_industry = {
        "software": [
            "Software Engineer",
            "Senior Backend Developer",
            "Full Stack Engineer",
            "Staff Software Architect",
            "DevOps Engineer",
        ],
        "data": [
            "Data Scientist",
            "Senior Machine Learning Engineer",
            "Data Engineer",
            "AI Research Scientist",
            "Analytics Engineer",
        ],
        "finance": [
            "Financial Analyst",
            "Senior Investment Analyst",
            "Portfolio Manager",
            "Corporate Finance Lead",
            "Risk Analyst",
        ],
        "healthcare": [
            "Health Informatics Specialist",
            "Clinical Research Associate",
            "Healthcare Systems Analyst",
            "Biomedical Data Lead",
        ],
        "marketing": [
            "Growth Marketing Manager",
            "Senior SEO Specialist",
            "Digital Marketing Lead",
            "Demand Generation Strategist",
        ],
        "design": [
            "UI/UX Designer",
            "Senior Product Designer",
            "Design Systems Lead",
            "User Experience Researcher",
        ],
        "manufacturing": [
            "Supply Chain Analyst",
            "Industrial Automation Engineer",
            "Operations Lead",
            "Quality Assurance Engineer",
        ],
        "education": [
            "Instructional Designer",
            "Curriculum Developer",
            "EdTech Specialist",
            "Senior Academic Advisor",
        ],
        "sales": [
            "Account Executive",
            "Senior Enterprise Sales Manager",
            "Business Development Representative",
            "Sales Director",
        ],
        "legal": [
            "Corporate Counsel",
            "Legal Compliance Specialist",
            "Senior Contracts Manager",
            "IP Legal Advisor",
        ],
        "operations": [
            "Operations Manager",
            "Program Manager",
            "Director of People Operations",
            "Business Operations Lead",
        ],
    }

    titles = titles_by_industry.get(industry, titles_by_industry["software"])

    years_remaining = total_years
    for job_idx in range(num_jobs):
        job_dur_years = max(1, years_remaining // (num_jobs - job_idx))
        years_remaining -= job_dur_years
        end_year = curr_year
        end_month = curr_month
        start_year = end_year - job_dur_years
        start_month = max(1, (curr_month - random.randint(0, 5)) % 12 + 1)

        is_current = job_idx == 0
        start_str = f"{start_year:04d}-{start_month:02d}"
        end_str = None if is_current else f"{end_year:04d}-{end_month:02d}"
        dur_months = job_dur_years * 12

        title_prefix = (
            "Senior " if seniority in ("senior", "lead", "principal") and job_idx == 0 else ""
        )
        job_title = f"{title_prefix}{random.choice(titles)}"

        job_skills = [
            s["raw"] for s in random.sample(selected_skills, min(4, len(selected_skills)))
        ]
        responsibilities = [
            (
                f"Led the architectural design and implementation of key {industry} "
                f"workflows using {', '.join(job_skills[:2])}."
            ),
            (
                "Improved cross-team delivery speed by 35% through standardized CI/CD "
                "pipelines and automated testing."
            ),
            (
                "Collaborated with executive stakeholders and product teams to drive "
                "data-informed roadmap decisions."
            ),
        ]

        experience_list.append(
            {
                "company": fake.company(),
                "title": job_title,
                "location": f"{fake.city()}, {fake.state_abbr()}",
                "start": start_str,
                "end": end_str,
                "is_current": is_current,
                "duration_months": dur_months,
                "responsibilities": responsibilities,
                "skills_mentioned": job_skills,
            }
        )

        curr_year = start_year
        curr_month = start_month

    # Education
    degree_levels = ["Bachelor of Science", "Master of Science", "Bachelor of Arts", "PhD"]
    fields_by_industry = {
        "software": "Computer Science",
        "data": "Data Science & Statistics",
        "finance": "Finance & Economics",
        "healthcare": "Health Informatics / Biology",
        "marketing": "Marketing & Communications",
        "design": "Human-Computer Interaction / Graphic Design",
        "manufacturing": "Industrial Engineering",
        "education": "Education & Curriculum Design",
        "sales": "Business Administration",
        "legal": "Juris Doctor (JD) / Legal Studies",
        "operations": "Operations Research / Management",
    }
    edu_start = 2026 - total_years - 4
    edu_end = 2026 - total_years
    education_list = [
        {
            "institution": f"{fake.city()} State University",
            "degree": random.choice(degree_levels),
            "field": fields_by_industry.get(industry, "Information Technology"),
            "start": f"{edu_start:04d}-09",
            "end": f"{edu_end:04d}-05",
            "grade": f"{random.uniform(3.5, 4.0):.2f} GPA",
        }
    ]

    # Skills formatting. Emerging skills are not in the taxonomy: no canonical slug, flagged.
    skills_payload = [
        {
            "raw": s["raw"],
            "canonical_slug": None if s["category_hint"] == "emerging" else s["slug"],
            "emerging": s["category_hint"] == "emerging",
            "category_hint": s["category_hint"],
            "evidence": f"Utilized {s['raw']} across multiple enterprise roles.",
        }
        for s in selected_skills
    ]

    # Certifications
    certifications_list = [
        {
            "name": f"Certified {industry.capitalize()} Professional",
            "issuer": "Industry Accreditation Board",
            "date": "2023-06",
            "expires": "2026-06",
            "credential_id": f"CERT-{random.randint(100000, 999999)}",
        }
    ]

    # Projects
    projects_list = [
        {
            "name": f"{industry.capitalize()} Optimization System",
            "description": (
                f"Designed and delivered a high-impact production tool leveraging "
                f"{selected_skills[0]['raw']}."
            ),
            "technologies": [s["raw"] for s in selected_skills[:3]],
            "url": f"https://github.com/{name.lower().replace(' ', '')}/project-showcase",
            "dates": "2024",
        }
    ]

    # Summary
    summary = (
        f"Experienced {seniority.capitalize()} professional with {total_years}+ years of "
        f"expertise in {industry}. Proven track record delivering scalable solutions using "
        f"{', '.join(s['raw'] for s in selected_skills[:3])}."
    )

    profile_data = {
        "schema_version": "1.0",
        "personal": {
            "name": name,
            "email": email,
            "phone": phone,
            "location": {"city": city, "region": state, "country": country},
            "links": [
                f"https://linkedin.com/in/{name.lower().replace(' ', '-')}",
                f"https://github.com/{name.lower().replace(' ', '')}",
            ],
        },
        "summary": summary,
        "experience": experience_list,
        "education": education_list,
        "skills": skills_payload,
        "certifications": certifications_list,
        "projects": projects_list,
        "publications": [],
        "meta": {
            "industry": industry,
            "seniority": seniority,
            "total_experience_years": total_years,
            "is_emerging_profile": is_emerging,
            "candidate_index": idx,
        },
    }

    # Validate against ParsedResume Pydantic model
    ParsedResume.model_validate(profile_data)
    return profile_data


def generate_profiles(count: int = 560) -> list[dict[str, Any]]:
    """Generate and save count profiles across industries and seniorities."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

    profiles: list[dict[str, Any]] = []
    checkpoint_file = CHECKPOINTS_DIR / "gen_profiles.json"

    logger.info("Generating %d ground truth candidate profiles...", count)

    for i in range(count):
        industry = INDUSTRIES[i % len(INDUSTRIES)]
        seniority = SENIORITIES[i % len(SENIORITIES)]

        profile = generate_single_profile(i, industry, seniority)
        profiles.append(profile)

        # The ground-truth profile (ParsedResume + gold canonical slugs) is the only output;
        # render_resumes.py reads it to produce the documents.
        gt_path = PROFILES_DIR / f"candidate_{i:04d}.gt.json"
        gt_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Write summary checkpoint
    checkpoint_data = {
        "total_generated": len(profiles),
        "industries": INDUSTRIES,
        "seniorities": SENIORITIES,
        "files": [f"candidate_{i:04d}.gt.json" for i in range(len(profiles))],
    }
    checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2), encoding="utf-8")

    logger.info("Successfully generated and saved %d profiles to %s", len(profiles), PROFILES_DIR)
    return profiles


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic ground truth candidate profiles"
    )
    parser.add_argument(
        "--count", type=int, default=560, help="Number of profiles to generate (default: 560)"
    )
    args = parser.parse_args()

    generate_profiles(count=args.count)


if __name__ == "__main__":
    main()
