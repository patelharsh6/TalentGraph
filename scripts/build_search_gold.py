"""Generate 30-query ground truth evaluation set for Talent Search (Metric M10, Exit Criterion 6-A)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "data" / "profiles"
OUT_PATH = ROOT / "data" / "eval" / "search_gold.json"

# 30 realistic recruiter queries spanning diverse domains, skills, and seniorities
QUERY_SPECS: list[dict[str, Any]] = [
    {
        "id": "query_01",
        "query": "Senior Python developer with Redis and CI/CD",
        "must_skills": ["python"],
        "should_skills": ["redis", "continuous-integration-and-continuous-delivery"],
        "min_years": 4.0,
        "seniorities": ["senior", "lead", "principal"],
        "industry": "software",
    },
    {
        "id": "query_02",
        "query": "Junior software developer with Python and JavaScript",
        "must_skills": ["python"],
        "should_skills": ["javascript"],
        "max_years": 3.0,
        "seniorities": ["junior", "mid"],
        "industry": "software",
    },
    {
        "id": "query_03",
        "query": "Financial analyst with financial modeling and Excel skills",
        "must_skills": ["financial-modeling"],
        "should_skills": ["microsoft-excel", "financial-risk-management"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "finance",
    },
    {
        "id": "query_04",
        "query": "Salesforce CRM specialist with HubSpot expertise",
        "must_skills": ["salesforce", "hubspot"],
        "should_skills": ["customer-success"],
        "min_years": None,
        "seniorities": None,
        "industry": "sales",
    },
    {
        "id": "query_05",
        "query": "Data engineer with PyTorch and Pandas experience",
        "must_skills": ["pandas", "pytorch"],
        "should_skills": ["apache-airflow"],
        "min_years": 3.0,
        "seniorities": None,
        "industry": "data",
    },
    {
        "id": "query_06",
        "query": "Healthcare professional with HIPAA compliance and Epic Systems",
        "must_skills": ["hipaa-compliance"],
        "should_skills": ["epic-systems", "hl7-fhir"],
        "min_years": None,
        "seniorities": None,
        "industry": "healthcare",
    },
    {
        "id": "query_07",
        "query": "Customer success specialist with Salesforce background",
        "must_skills": ["customer-success", "salesforce"],
        "should_skills": ["effective-communication"],
        "min_years": 1.0,
        "seniorities": None,
        "industry": "sales",
    },
    {
        "id": "query_08",
        "query": "Financial risk management specialist in finance",
        "must_skills": ["financial-risk-management"],
        "should_skills": ["financial-modeling", "microsoft-excel"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "finance",
    },
    {
        "id": "query_09",
        "query": "Legal counsel with contract drafting and intellectual property",
        "must_skills": ["contract-drafting", "intellectual-property"],
        "should_skills": ["regulatory-compliance"],
        "min_years": None,
        "seniorities": None,
        "industry": "legal",
    },
    {
        "id": "query_10",
        "query": "Sales professional skilled in B2B sales and HubSpot",
        "must_skills": ["hubspot", "b2b-sales"],
        "should_skills": ["salesforce"],
        "min_years": None,
        "seniorities": None,
        "industry": "sales",
    },
    {
        "id": "query_11",
        "query": "Machine learning engineer with TensorFlow and LLMs",
        "must_skills": ["tensorflow", "large-language-models"],
        "should_skills": ["pytorch"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "data",
    },
    {
        "id": "query_12",
        "query": "Instructional design professional with public speaking",
        "must_skills": ["instructional-design"],
        "should_skills": ["public-speaking", "mentoring"],
        "min_years": None,
        "seniorities": None,
        "industry": "education",
    },
    {
        "id": "query_13",
        "query": "Mid-level Python programmer with Redis experience",
        "must_skills": ["python"],
        "should_skills": ["redis"],
        "min_years": 2.0,
        "seniorities": ["mid", "senior"],
        "industry": "software",
    },
    {
        "id": "query_14",
        "query": "Compliance analyst with regulatory compliance and contract drafting",
        "must_skills": ["regulatory-compliance", "contract-drafting"],
        "should_skills": ["risk-management"],
        "min_years": None,
        "seniorities": None,
        "industry": "legal",
    },
    {
        "id": "query_15",
        "query": "Data scientist with Airflow and Pandas expertise",
        "must_skills": ["apache-airflow", "pandas"],
        "should_skills": ["pytorch"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "data",
    },
    {
        "id": "query_16",
        "query": "Senior customer success manager with HubSpot and Salesforce",
        "must_skills": ["customer-success", "salesforce"],
        "should_skills": ["hubspot"],
        "min_years": 4.0,
        "seniorities": ["senior", "lead", "principal"],
        "industry": "sales",
    },
    {
        "id": "query_17",
        "query": "Health informatics specialist with HL7 FHIR and Cerner",
        "must_skills": ["hl7-fhir"],
        "should_skills": ["cerner", "epic-systems"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "healthcare",
    },
    {
        "id": "query_18",
        "query": "Finance specialist with LBO modeling and Excel",
        "must_skills": ["lbo-modeling", "microsoft-excel"],
        "should_skills": ["financial-modeling"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "finance",
    },
    {
        "id": "query_19",
        "query": "Education mentor with curriculum development background",
        "must_skills": ["curriculum-development", "mentoring"],
        "should_skills": ["instructional-design"],
        "min_years": None,
        "seniorities": None,
        "industry": "education",
    },
    {
        "id": "query_20",
        "query": "Intellectual property lawyer with legal research experience",
        "must_skills": ["intellectual-property", "legal-research"],
        "should_skills": ["contract-drafting"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "legal",
    },
    {
        "id": "query_21",
        "query": "Senior software engineer with Python and team leadership",
        "must_skills": ["python", "team-leadership"],
        "should_skills": ["redis"],
        "min_years": 4.0,
        "seniorities": ["senior", "lead", "principal"],
        "industry": "software",
    },
    {
        "id": "query_22",
        "query": "CRM administrator with B2B sales and HubSpot",
        "must_skills": ["b2b-sales", "hubspot"],
        "should_skills": ["salesforce"],
        "min_years": None,
        "seniorities": None,
        "industry": "sales",
    },
    {
        "id": "query_23",
        "query": "Healthcare clinical trials manager with bioinformatics",
        "must_skills": ["clinical-trials"],
        "should_skills": ["bioinformatics", "hipaa-compliance"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "healthcare",
    },
    {
        "id": "query_24",
        "query": "Lead software architect with CI/CD and Redis",
        "must_skills": ["continuous-integration-and-continuous-delivery", "redis"],
        "should_skills": ["team-leadership"],
        "min_years": 5.0,
        "seniorities": ["lead", "principal", "senior"],
        "industry": "software",
    },
    {
        "id": "query_25",
        "query": "Deep learning engineer with PyTorch and TensorFlow",
        "must_skills": ["pytorch", "tensorflow"],
        "should_skills": ["large-language-models"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "data",
    },
    {
        "id": "query_26",
        "query": "EdTech professional with EdTech solutions and mentoring",
        "must_skills": ["edtech-solutions"],
        "should_skills": ["mentoring", "instructional-design"],
        "min_years": 1.0,
        "seniorities": None,
        "industry": "education",
    },
    {
        "id": "query_27",
        "query": "Corporate legal counsel with risk management and compliance",
        "must_skills": ["risk-management", "regulatory-compliance"],
        "should_skills": ["contract-drafting"],
        "min_years": 2.0,
        "seniorities": None,
        "industry": "legal",
    },
    {
        "id": "query_28",
        "query": "Senior financial analyst with IFRS and financial modeling",
        "must_skills": ["ifrs", "financial-modeling"],
        "should_skills": ["financial-risk-management"],
        "min_years": 4.0,
        "seniorities": ["senior", "lead", "principal"],
        "industry": "finance",
    },
    {
        "id": "query_29",
        "query": "Customer success director with effective communication and Salesforce",
        "must_skills": ["customer-success", "effective-communication"],
        "should_skills": ["salesforce"],
        "min_years": 4.0,
        "seniorities": ["senior", "lead", "principal"],
        "industry": "sales",
    },
    {
        "id": "query_30",
        "query": "Education specialist with instructional design and public speaking",
        "must_skills": ["instructional-design", "public-speaking"],
        "should_skills": ["mentoring"],
        "min_years": 1.0,
        "seniorities": None,
        "industry": "education",
    },
]


def load_all_profiles() -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for p in sorted(PROFILES_DIR.glob("candidate_*.gt.json")):
        cid = p.stem.replace(".gt", "")
        data = json.loads(p.read_text(encoding="utf-8"))
        profiles[cid] = data
    return profiles


def is_candidate_relevant(cand_data: dict[str, Any], spec: dict[str, Any]) -> bool:
    meta = cand_data.get("meta", {})
    cand_skills = {
        s.get("canonical_slug") for s in cand_data.get("skills", []) if s.get("canonical_slug")
    }

    # Must-have skills check: must have all must_skills (or at least 1 if multiple and lenient)
    musts = set(spec.get("must_skills", []))
    if musts and not musts.issubset(cand_skills):
        return False

    # Industry check if strictly specified
    target_ind = spec.get("industry")
    cand_ind = meta.get("industry", "")
    if target_ind and cand_ind and target_ind.lower() != cand_ind.lower():
        # Allow if candidate summary/experience explicitly matches domain
        summary = cand_data.get("summary", "").lower()
        if target_ind.lower() not in summary:
            return False

    # Seniority check if specified
    allowed_sen = spec.get("seniorities")
    cand_sen = meta.get("seniority", "")
    if allowed_sen and cand_sen and cand_sen.lower() not in [s.lower() for s in allowed_sen]:
        return False

    # Min years check
    min_years = spec.get("min_years")
    cand_years = float(meta.get("total_experience_years", 0))
    if min_years is not None and cand_years < (min_years - 1.0):
        return False

    # Max years check
    max_years = spec.get("max_years")
    if max_years is not None and cand_years > (max_years + 1.0):
        return False

    return True


def build_gold_set() -> None:
    profiles = load_all_profiles()
    print(f"Loaded {len(profiles)} candidate profiles.")

    gold_entries: list[dict[str, Any]] = []

    for spec in QUERY_SPECS:
        qid = spec["id"]
        query = spec["query"]
        relevant_ids: list[str] = []

        for cid, cand in profiles.items():
            if is_candidate_relevant(cand, spec):
                relevant_ids.append(cid)

        print(f"Query {qid}: '{query}' -> {len(relevant_ids)} relevant candidates")

        gold_entries.append(
            {
                "id": qid,
                "query": query,
                "must_skills": spec.get("must_skills", []),
                "should_skills": spec.get("should_skills", []),
                "min_years": spec.get("min_years"),
                "seniority": spec.get("seniorities", [None])[0]
                if spec.get("seniorities")
                else None,
                "domain": spec.get("industry"),
                "relevant_candidates": relevant_ids,
                "relevant_count": len(relevant_ids),
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(gold_entries, indent=2), encoding="utf-8")
    print(f"Saved {len(gold_entries)} gold queries to {OUT_PATH}")


if __name__ == "__main__":
    build_gold_set()
