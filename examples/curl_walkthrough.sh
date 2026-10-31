#!/usr/bin/env bash
# Step 5.7: TalentGraph REST API cURL Walkthrough
# Demonstrates every Milestone 5 API endpoint in order.

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-}"
AUTH_HEADER=()

if [[ -n "$API_KEY" ]]; then
  AUTH_HEADER=(-H "X-API-Key: $API_KEY")
fi

echo "=========================================================="
echo "TalentGraph API Walkthrough ($BASE_URL)"
echo "=========================================================="

echo -e "\n1. Liveness & Readiness Probes:"
curl -s "$BASE_URL/health" | jq .
curl -s "$BASE_URL/ready" | jq .

echo -e "\n2. Browse Root Skills Taxonomy:"
curl -s "$BASE_URL/api/v1/skills/taxonomy?limit=5" | jq .

echo -e "\n3. Search Skills (Semantic + Fuzzy):"
curl -s "$BASE_URL/api/v1/skills/search?q=python&limit=3" | jq .

echo -e "\n4. Retrieve Skill Detail:"
curl -s "$BASE_URL/api/v1/skills/python" | jq .

echo -e "\n5. Parse a Resume (POST /api/v1/parse):"
PARSE_RES=$(curl -s -X POST "$BASE_URL/api/v1/parse?include=trace" \
  "${AUTH_HEADER[@]}" \
  -F "file=@tests/fixtures/resumes/candidate_0009.txt;type=text/plain")

echo "$PARSE_RES" | jq '{candidate_id: .data.candidate_id, name: .data.parsed.name.value, status: .meta.status, latency_ms: .meta.latency_ms}'

CANDIDATE_ID=$(echo "$PARSE_RES" | jq -r '.data.candidate_id')

echo -e "\n6. Retrieve Candidate by ID:"
curl -s "$BASE_URL/api/v1/candidates/$CANDIDATE_ID" | jq '{id: .id, quality: .quality}'

echo -e "\n7. Retrieve Candidate Skill Profile (with filter):"
curl -s "$BASE_URL/api/v1/candidates/$CANDIDATE_ID/skills?min_proficiency=2" | jq '.skills[:5]'

echo -e "\n8. Semantic Match Against Job Description:"
MATCH_PAYLOAD=$(cat <<EOF
{
  "candidate_id": "$CANDIDATE_ID",
  "job": {
    "title": "Senior Backend Software Engineer",
    "description": "Seeking an experienced engineer proficient in Python, PostgreSQL, and Docker containerization."
  },
  "preset": "balanced"
}
EOF
)

curl -s -X POST "$BASE_URL/api/v1/match" \
  "${AUTH_HEADER[@]}" \
  -H "Content-Type: application/json" \
  -d "$MATCH_PAYLOAD" | jq '{score: .data.score, threshold: .data.threshold, is_match: .data.is_match, top_gaps: .data.gaps[:2]}'

echo -e "\n9. Blind Match Screening (Feature F4):"
curl -s -X POST "$BASE_URL/api/v1/match?blind=true" \
  "${AUTH_HEADER[@]}" \
  -H "Content-Type: application/json" \
  -d "$MATCH_PAYLOAD" | jq '{score: .data.score, blind: .data.blind}'

echo -e "\n10. Rank Candidates for Job:"
RANK_PAYLOAD=$(cat <<EOF
{
  "candidate_ids": ["$CANDIDATE_ID"],
  "job": {
    "title": "Senior Backend Software Engineer",
    "description": "Seeking an experienced engineer proficient in Python, PostgreSQL, and Docker containerization."
  },
  "preset": "balanced"
}
EOF
)

curl -s -X POST "$BASE_URL/api/v1/match/rank" \
  "${AUTH_HEADER[@]}" \
  -H "Content-Type: application/json" \
  -d "$RANK_PAYLOAD" | jq .

echo -e "\n11. Submit a Batch of Resumes (POST /api/v1/parse/batch):"
BATCH_RES=$(curl -s -X POST "$BASE_URL/api/v1/parse/batch" \
  "${AUTH_HEADER[@]}" \
  -F "files=@tests/fixtures/resumes/candidate_0009.txt" \
  -F "files=@tests/fixtures/resumes/candidate_0028.txt")

echo "$BATCH_RES" | jq .
BATCH_ID=$(echo "$BATCH_RES" | jq -r '.batch_job_id')

echo -e "\n12. Check Batch Progress (GET /api/v1/jobs/{id}):"
sleep 1
curl -s "$BASE_URL/api/v1/jobs/$BATCH_ID" | jq .

echo -e "\n=========================================================="
echo "Walkthrough completed successfully!"
echo "=========================================================="

