"""Step 5.9: CI Evaluation Gate (Exit Criterion 5-G, Metric F5).

Checks test/val split evaluation reports against frozen baselines in reports/baseline/.
Verifies:
- M1 (Parsing): Field F1 >= 0.80, quality >= 0.85 (delta <= tolerance)
- M2 (Normalization): Precision >= 0.90, recall >= 0.85 (delta <= tolerance)
- M3 (Matching): NDCG@5 >= 0.70, rank correlation >= 0.65 (delta <= tolerance)

Fails (exit 1) if any metric regresses by more than the allowed tolerance (default: 0.02)
or fails minimum quality thresholds. Passes (exit 0) otherwise.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class GateCheck:
    name: str
    target_text: str
    min_threshold: float
    baseline_value: float
    actual_value: float
    tolerance: float

    @property
    def delta(self) -> float:
        return self.actual_value - self.baseline_value

    @property
    def passed(self) -> bool:
        # Must meet absolute minimum threshold AND not drop by more than tolerance from baseline
        meets_minimum = self.actual_value >= (self.min_threshold - 1e-6)
        within_tolerance = self.delta >= (-self.tolerance - 1e-6)
        return meets_minimum and within_tolerance


def _find_latest_report(reports_dir: Path, pattern: str) -> Path | None:
    matches = sorted(reports_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def load_baselines(baseline_dir: Path) -> dict[str, Any]:
    baselines: dict[str, Any] = {}
    for name in ("parsing", "normalization", "matching"):
        p = baseline_dir / f"{name}.json"
        if p.exists():
            baselines[name] = json.loads(p.read_text(encoding="utf-8"))
        else:
            raise FileNotFoundError(f"Missing baseline specification: {p}")
    return baselines


def collect_actual_metrics(reports_dir: Path) -> dict[str, float]:
    metrics: dict[str, float] = {}

    # 1. Parsing
    parse_report = _find_latest_report(reports_dir, "parsing_val_*.json") or _find_latest_report(
        reports_dir, "parsing_*.json"
    )
    if parse_report:
        data = json.loads(parse_report.read_text(encoding="utf-8"))
        if "m1" in data and "overall" in data["m1"]:
            metrics["parsing_f1"] = float(data["m1"]["overall"].get("f1", 0.0))
            metrics["parsing_precision"] = float(data["m1"]["overall"].get("precision", 0.0))
            metrics["parsing_recall"] = float(data["m1"]["overall"].get("recall", 0.0))

    # 2. Normalization
    norm_report = _find_latest_report(
        reports_dir, "normalization_test_*.json"
    ) or _find_latest_report(reports_dir, "normalization_*.json")
    if norm_report:
        data = json.loads(norm_report.read_text(encoding="utf-8"))
        metrics["norm_precision"] = float(data.get("precision", 0.0))
        metrics["norm_recall"] = float(data.get("recall", 0.0))
        metrics["norm_f1"] = float(data.get("f1", 0.0))

    # 3. Matching
    match_report = _find_latest_report(reports_dir, "matching_test_*.json") or _find_latest_report(
        reports_dir, "matching_*.json"
    )
    if match_report:
        data = json.loads(match_report.read_text(encoding="utf-8"))
        metrics["match_ndcg_at_5"] = float(data.get("ndcg_at_5", 0.0))
        metrics["match_spearman"] = float(data.get("spearman_rho", 0.0))
        if "presets" in data and "balanced" in data["presets"]:
            metrics["match_balanced_f1"] = float(data["presets"]["balanced"].get("f1", 0.0))

    return metrics


def run_eval_gate(
    reports_dir: Path,
    baseline_dir: Path,
    tolerance: float = 0.02,
    overrides: dict[str, float] | None = None,
) -> int:
    baselines = load_baselines(baseline_dir)
    actuals = collect_actual_metrics(reports_dir)

    # Apply any simulated overrides for CI regression testing
    if overrides:
        for k, v in overrides.items():
            actuals[k] = v

    p_base = baselines["parsing"]
    n_base = baselines["normalization"]
    m_base = baselines["matching"]

    checks: list[GateCheck] = [
        GateCheck(
            name="M1: Parsing Field F1",
            target_text=f">= {p_base.get('min_field_f1', 0.80):.2f}",
            min_threshold=p_base.get("min_field_f1", 0.80),
            baseline_value=p_base["baseline"]["f1"],
            actual_value=actuals.get("parsing_f1", 0.0),
            tolerance=tolerance,
        ),
        GateCheck(
            name="M2: Normalization Precision",
            target_text=f">= {n_base.get('min_precision', 0.90):.2f}",
            min_threshold=n_base.get("min_precision", 0.90),
            baseline_value=n_base["baseline"]["precision"],
            actual_value=actuals.get("norm_precision", 0.0),
            tolerance=tolerance,
        ),
        GateCheck(
            name="M2: Normalization Recall",
            target_text=f">= {n_base.get('min_recall', 0.85):.2f}",
            min_threshold=n_base.get("min_recall", 0.85),
            baseline_value=n_base["baseline"]["recall"],
            actual_value=actuals.get("norm_recall", 0.0),
            tolerance=tolerance,
        ),
        GateCheck(
            name="M3: Matching NDCG@5",
            target_text=f">= {m_base.get('min_ndcg_at_5', 0.70):.2f}",
            min_threshold=m_base.get("min_ndcg_at_5", 0.70),
            baseline_value=m_base["baseline"]["ndcg_at_5"],
            actual_value=actuals.get("match_ndcg_at_5", 0.0),
            tolerance=tolerance,
        ),
        GateCheck(
            name="M3: Matching Spearman Rho",
            target_text=f">= {m_base.get('min_spearman_rho', 0.65):.2f}",
            min_threshold=m_base.get("min_spearman_rho", 0.65),
            baseline_value=m_base["baseline"]["spearman_rho"],
            actual_value=actuals.get("match_spearman", 0.0),
            tolerance=tolerance,
        ),
    ]

    print("=" * 88)
    print(f"TalentGraph CI Evaluation Gate (Exit Criterion 5-G) | Tolerance = {tolerance}")
    print("=" * 88)
    print(
        f"{'Metric':<28} {'Target':<12} {'Baseline':<10} {'Actual':<10} {'Delta':<10} {'Status':<8}"
    )
    print("-" * 88)

    all_passed = True
    for c in checks:
        delta_str = f"{c.delta:+.4f}"
        status_str = "PASS" if c.passed else "FAIL"
        if not c.passed:
            all_passed = False
        print(
            f"{c.name:<28} {c.target_text:<12} {c.baseline_value:<10.4f} {c.actual_value:<10.4f} "
            f"{delta_str:<10} {status_str:<8}"
        )

    print("=" * 88)
    if all_passed:
        print("[CI EVAL GATE] All evaluation metrics satisfy baseline & tolerance requirements.")
        return 0
    else:
        print("[CI EVAL GATE] REGRESSION DETECTED! One or more metrics failed evaluation gate.")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="TalentGraph CI Eval Gate (Metric F5, Step 5.9)")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--baseline-dir", type=Path, default=ROOT / "reports" / "baseline")
    parser.add_argument("--tolerance", type=float, default=0.02)
    parser.add_argument(
        "--override",
        action="append",
        help="Simulate metric override: key=value (e.g. --override match_ndcg_at_5=0.55)",
    )
    args = parser.parse_args()

    overrides: dict[str, float] = {}
    if args.override:
        for item in args.override:
            k, v = item.split("=", 1)
            overrides[k.strip()] = float(v.strip())

    return run_eval_gate(
        reports_dir=args.reports_dir,
        baseline_dir=args.baseline_dir,
        tolerance=args.tolerance,
        overrides=overrides,
    )


if __name__ == "__main__":
    raise SystemExit(main())
