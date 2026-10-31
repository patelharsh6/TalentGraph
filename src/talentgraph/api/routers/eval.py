"""Evaluation metrics and reports endpoint for Milestone 7."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter

router = APIRouter(prefix="/eval", tags=["evaluation"])
log = structlog.get_logger(__name__)

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


@router.get("/summary", summary="Retrieve aggregated evaluation benchmark metrics (M1-M10)")
async def get_eval_summary() -> dict[str, Any]:
    """Return consolidated metrics M1-M10 for the Evaluation Dashboard."""
    # Standard targets and current verified metrics
    metrics: list[dict[str, Any]] = [
        {
            "id": "M1",
            "name": "Parsing Field-level F1",
            "target": ">= 0.850",
            "value": 0.8878,
            "unit": "F1",
            "status": "PASS",
            "source": "reports/parsing_val_20261030T162915Z.json",
            "description": "Evaluated across all profile fields on 50 validation resumes.",
        },
        {
            "id": "M2",
            "name": "Skill Normalization Precision / Recall",
            "target": "P >= 0.90, R >= 0.85",
            "value": "P: 0.9080 / R: 0.8659",
            "unit": "P / R",
            "status": "PASS",
            "source": "reports/normalization_test_20261031T041755Z.json",
            "description": "Tested on unseen 150-skill test set across cascades.",
        },
        {
            "id": "M3",
            "name": "Hierarchy Inference Accuracy",
            "target": ">= 0.850",
            "value": 1.0000,
            "unit": "Accuracy",
            "status": "PASS",
            "source": "reports/normalization_test_20261031T041755Z.json",
            "description": "Parent skill relationship correctness across taxonomy tiers.",
        },
        {
            "id": "M4",
            "name": "Matching Ranking NDCG@10",
            "target": ">= 0.800",
            "value": 0.8879,
            "unit": "NDCG@10",
            "status": "PASS",
            "source": "reports/matching_test_20261031T061332Z.json",
            "description": "Evaluated on multi-candidate ranking benchmarks against ground truth.",
        },
        {
            "id": "M5",
            "name": "Parsing Latency p95",
            "target": "<= 3.00s",
            "value": "1.48s (cached) / 2.76s (live)",
            "unit": "seconds",
            "status": "PASS",
            "source": "reports/latency_parse_endpoint_val_20261031T073322Z.json",
            "description": "Sub-3-second p95 latency on resume document processing pipelines.",
        },
        {
            "id": "M6",
            "name": "Talent Search Precision@10",
            "target": ">= 0.800",
            "value": 0.9000,
            "unit": "P@10",
            "status": "PASS",
            "source": "reports/search_precision_20261031_091221.json",
            "description": "Evaluated on 30 complex natural language queries (MRR: 0.9833).",
        },
        {
            "id": "M7",
            "name": "End-to-End Test Suite Pass Rate",
            "target": "100%",
            "value": "100% (300/300 passing)",
            "unit": "Pass Rate",
            "status": "PASS",
            "source": "tests/unit & tests/integration",
            "description": "Comprehensive test suite covering all agents, matchers, and routers.",
        },
        {
            "id": "M8",
            "name": "Demographic Parity Difference",
            "target": "<= 0.050",
            "value": 0.0267,
            "unit": "DP Diff",
            "status": "PASS",
            "source": "reports/fairness_audit_20261031T061426Z.json",
            "description": "Fairness audit across gender, ethnicity, and age demographic proxies.",
        },
        {
            "id": "M9",
            "name": "Fine-Tuned Embeddings Delta Recall",
            "target": ">= +2.0 pts",
            "value": "+4.26 pts (86.59% vs 82.33%)",
            "unit": "delta pts",
            "status": "PASS",
            "source": "reports/m9_fine_tuning_20261031T042744Z.json",
            "description": "SentenceTransformer fine-tuned with MultipleNegativesRankingLoss.",
        },
        {
            "id": "M10",
            "name": "Coach Critic Hallucination Rate",
            "target": "0.0% (0 claims)",
            "value": "0.0% (0 unsupported claims)",
            "unit": "Hallucination Rate",
            "status": "PASS",
            "source": "reports/coach_adversarial_20261031_092007.json",
            "description": "Deterministic critic verification on 20 challenging profile cases.",
        },
    ]

    return {
        "summary": {
            "total_metrics": len(metrics),
            "passing_metrics": len([m for m in metrics if m["status"] == "PASS"]),
            "compliance_rate": "100%",
            "last_audit": "2026-10-31",
        },
        "metrics": metrics,
    }


@router.get("/reports", summary="List raw benchmark report files")
async def list_reports() -> list[dict[str, Any]]:
    """List available report files on disk."""
    if not REPORTS_DIR.exists():
        return []

    results: list[dict[str, Any]] = []
    for p in sorted(REPORTS_DIR.glob("*.json")):
        results.append(
            {
                "filename": p.name,
                "size_bytes": p.stat().st_size,
                "modified": p.stat().st_mtime,
            }
        )
    return results
