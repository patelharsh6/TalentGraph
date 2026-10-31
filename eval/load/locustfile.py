"""Step 5.8: Locust load test simulating ~10 concurrent users (Metric M5, plan §8).

Run with:
    LLM_MODE=stub uv run locust -f eval/load/locustfile.py --headless -u 10 -r 2 \
        --run-time 30s --host http://localhost:8000
"""

import os
import random
from pathlib import Path

from locust import HttpUser, between, task

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "resumes"

SEARCH_QUERIES = [
    "python",
    "docker",
    "kubernetes",
    "machine learning",
    "react",
    "postgresql",
    "fastapi",
    "aws",
    "cybersecurity",
    "data science",
]


class TalentGraphUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        self.api_key = os.getenv("API_KEY", "")
        self.headers = {"X-API-Key": self.api_key} if self.api_key else {}
        self.candidate_ids: list[str] = []

        # Load sample resume bytes for testing
        self.sample_files = list(FIXTURES_DIR.glob("*.txt"))
        if not self.sample_files:
            self.sample_files = list(FIXTURES_DIR.glob("*.*"))

    @task(2)
    def check_health_probes(self) -> None:
        self.client.get("/health", headers=self.headers)
        with self.client.get("/ready", headers=self.headers, catch_response=True) as res:
            if res.status_code in (200, 503):
                res.success()
            else:
                res.failure(f"Unexpected ready status: {res.status_code}")

    @task(4)
    def browse_and_search_skills(self) -> None:
        # Taxonomy browsing
        self.client.get("/api/v1/skills/taxonomy?limit=10", headers=self.headers)

        # Keyword / semantic skill search
        q = random.choice(SEARCH_QUERIES)
        self.client.get(f"/api/v1/skills/search?q={q}", headers=self.headers)

        # Skill detail
        slug = q.replace(" ", "-")
        with self.client.get(
            f"/api/v1/skills/{slug}", headers=self.headers, catch_response=True
        ) as res:
            if res.status_code in (200, 404):
                res.success()
            else:
                res.failure(f"Unexpected status for skill {slug}: {res.status_code}")

    @task(3)
    def parse_resume(self) -> None:
        if not self.sample_files:
            return
        sample = random.choice(self.sample_files)
        with open(sample, "rb") as f:
            files = {"file": (sample.name, f.read(), "text/plain")}
            with self.client.post(
                "/api/v1/parse",
                files=files,
                headers=self.headers,
                catch_response=True,
            ) as res:
                if res.status_code == 200:
                    payload = res.json()
                    cid = payload.get("data", {}).get("candidate_id")
                    if cid and len(self.candidate_ids) < 50:
                        self.candidate_ids.append(cid)
                    res.success()
                elif res.status_code == 429:
                    res.success()  # Rate limiting is an expected safeguard
                else:
                    res.failure(f"Unexpected status: {res.status_code}")

    @task(2)
    def match_candidate(self) -> None:
        if not self.candidate_ids:
            return
        cid = random.choice(self.candidate_ids)
        body = {
            "candidate_id": cid,
            "job": {
                "title": "Software Engineer",
                "description": "Looking for a software engineer with Python and Docker background.",
            },
            "preset": "balanced",
        }
        with self.client.post(
            "/api/v1/match",
            json=body,
            headers=self.headers,
            catch_response=True,
        ) as res:
            if res.status_code in (200, 429):
                res.success()
            else:
                res.failure(f"Match failed with {res.status_code}")
