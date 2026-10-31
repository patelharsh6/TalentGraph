"""Step 5.7: Python client demo covering all Milestone 5 API endpoints (plan §8).

Run against a live TalentGraph server:
    python examples/api_demo.py
"""

import os
import sys
import time
from pathlib import Path

import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")
ROOT = Path(__file__).resolve().parent.parent
SAMPLE_RESUME = ROOT / "tests" / "fixtures" / "resumes" / "candidate_0009.txt"


def main() -> int:
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    client = httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0)

    print("==========================================================")
    print(f"TalentGraph API Python Client Demo ({BASE_URL})")
    print("==========================================================")

    # 1. Health & readiness probes
    print("\n1. Checking liveness and readiness probes...")
    res = client.get("/health")
    print(f"   GET /health -> {res.status_code}: {res.json()}")

    res = client.get("/ready")
    print(f"   GET /ready  -> {res.status_code}: {res.json()}")

    # 2. Browse Taxonomy
    print("\n2. Browsing taxonomy root domains...")
    res = client.get("/api/v1/skills/taxonomy", params={"limit": 3})
    print(f"   GET /skills/taxonomy -> {res.status_code}")
    for domain in res.json():
        print(f"   - Domain: {domain['name']} (slug: {domain['slug']}, level: {domain['level']})")

    # 3. Search Skills
    print("\n3. Searching skills for 'machine learning'...")
    res = client.get("/api/v1/skills/search", params={"q": "machine learning", "limit": 3})
    for hit in res.json():
        print(f"   - Match: {hit['name']} ({hit['slug']}) via {hit['match_type']}")

    # 4. Parse Resume
    if not SAMPLE_RESUME.exists():
        print(f"\n[!] Sample resume not found at {SAMPLE_RESUME}")
        return 1

    print(f"\n4. Uploading and parsing {SAMPLE_RESUME.name}...")
    with open(SAMPLE_RESUME, "rb") as f:
        files = {"file": (SAMPLE_RESUME.name, f, "text/plain")}
        res = client.post("/api/v1/parse?include=trace", files=files)

    if res.status_code != 200:
        print(f"   [x] Parse failed: {res.status_code} {res.text}")
        return 1

    payload = res.json()
    candidate_id = payload["data"]["candidate_id"]
    candidate_name = payload["data"]["parsed"]["name"]["value"]
    print(f"   [+] Parsed Candidate: {candidate_name} (ID: {candidate_id})")
    print(
        f"   [+] Status: {payload['meta']['status']}, Latency: {payload['meta']['latency_ms']} ms"
    )

    # 5. Retrieve Candidate Profile & Skills
    print(f"\n5. Retrieving candidate details for {candidate_id}...")
    res = client.get(f"/api/v1/candidates/{candidate_id}")
    cand_quality = res.json().get("quality")
    print(f"   GET /candidates/{candidate_id} -> {res.status_code}, Quality: {cand_quality}")

    print("\n6. Retrieving normalized skills (min_proficiency=2)...")
    res = client.get(f"/api/v1/candidates/{candidate_id}/skills", params={"min_proficiency": 2})
    skills = res.json().get("skills", [])
    print(f"   Found {len(skills)} skills meeting threshold:")
    for sk in skills[:5]:
        print(f"   - {sk['name']} (Proficiency: {sk['proficiency']}, Inferred: {sk['inferred']})")

    # 6. Semantic Matching
    print("\n7. Scoring candidate against a job description...")
    job_spec = {
        "candidate_id": candidate_id,
        "job": {
            "title": "Senior Backend Developer",
            "description": "Expert Python developer proficient in SQL, Docker, and API design.",
        },
        "preset": "balanced",
    }
    res = client.post("/api/v1/match", json=job_spec)
    match_data = res.json()["data"]
    print(f"   Score:     {match_data['score']:.2%} (Threshold: {match_data['threshold']:.2%})")
    print(f"   Is Match:  {'YES' if match_data['is_match'] else 'NO'}")
    print("   Requirement Breakdown:")
    for b in match_data["breakdown"][:4]:
        b_name, b_matched = b["requirement_name"], b["matched_name"]
        print(f"   - {b_name}: Credit {b['credit']:.1%} via {b_matched} ({b['match_type']})")

    # 7. Blind Screening
    print("\n8. Scoring candidate in blind screening mode (Feature F4)...")
    res = client.post("/api/v1/match", params={"blind": "true"}, json=job_spec)
    blind_data = res.json()["data"]
    print(f"   Blind Mode Score: {blind_data['score']:.2%} (Identical explainable score)")

    # 8. Candidate Ranking
    print("\n9. Ranking candidates...")
    rank_spec = {
        "candidate_ids": [candidate_id],
        "job": job_spec["job"],
        "preset": "balanced",
    }
    res = client.post("/api/v1/match/rank", json=rank_spec)
    top_score = res.json()[0]["match"]["score"]
    print(f"   Ranked {len(res.json())} candidate(s). Top score: {top_score:.2%}")

    # 9. Batch Upload
    print("\n10. Submitting batch resume processing...")
    with open(SAMPLE_RESUME, "rb") as f:
        data = f.read()
    files_batch = [
        ("files", ("batch_01.txt", data, "text/plain")),
        ("files", ("batch_02.txt", data, "text/plain")),
    ]
    res = client.post("/api/v1/parse/batch", files=files_batch)
    batch_info = res.json()
    batch_job_id = batch_info["batch_job_id"]
    b_total, b_st = batch_info["total"], batch_info["status"]
    print(f"   Submitted batch {batch_job_id} with {b_total} items (Status: {b_st})")

    print(f"\n11. Polling batch status for {batch_job_id}...")
    time.sleep(1.0)
    res = client.get(f"/api/v1/jobs/{batch_job_id}")
    j_res = res.json()
    st, succ, tot = j_res["status"], j_res["succeeded"], j_res["total"]
    print(f"   Batch Status: {st} (Succeeded: {succ}, Total: {tot})")

    print("\n==========================================================")
    print("Demo completed successfully!")
    print("==========================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
