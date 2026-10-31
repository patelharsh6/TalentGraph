"""Step 3.6: Proficiency estimation (plan §6.2, Exit Criterion 3-D).

Calculates skill proficiency (level 1-5) and years from:
1. `years_used`: summed durations of roles mentioning skill, overlapping intervals merged.
   - 0-2y -> level 2
   - 2-5y -> level 3
   - 5-8y -> level 4
   - 8+y  -> level 5
2. Qualifier wording in evidence ("expert in", "led", "architected" vs. "basic"): ±1
3. Skills-section-only cap: skills with no role/project evidence capped at level 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = ROOT / "config" / "proficiency.yaml"


@dataclass
class ProficiencyConfig:
    years_to_base_level: list[tuple[float, int]]
    qualifiers_raise: list[str]
    qualifiers_lower: list[str]
    qualifiers_delta: int = 1
    skills_section_only_cap: int = 2

    @classmethod
    def load(cls, path: Path | str | None = None) -> ProficiencyConfig:
        file_path = Path(path or CONFIG_PATH)
        if not file_path.is_file():
            return cls(
                years_to_base_level=[(2.0, 2), (5.0, 3), (8.0, 4), (float("inf"), 5)],
                qualifiers_raise=["expert in", "led", "architected", "deep expertise", "mentored"],
                qualifiers_lower=["familiar with", "exposure to", "basic", "beginner", "learning"],
                qualifiers_delta=1,
                skills_section_only_cap=2,
            )
        data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        raw_bands = data.get("years_to_base_level", [])
        bands = []
        for bound, lvl in raw_bands:
            b_val = float(bound) if bound not in (".inf", "inf", None) else float("inf")
            bands.append((b_val, int(lvl)))

        quals = data.get("qualifiers", {})
        return cls(
            years_to_base_level=bands or [(2.0, 2), (5.0, 3), (8.0, 4), (float("inf"), 5)],
            qualifiers_raise=quals.get(
                "raise", ["expert in", "led", "architected", "deep expertise", "mentored"]
            ),
            qualifiers_lower=quals.get(
                "lower", ["familiar with", "exposure to", "basic", "beginner", "learning"]
            ),
            qualifiers_delta=int(quals.get("delta", 1)),
            skills_section_only_cap=int(data.get("skills_section_only_cap", 2)),
        )


@dataclass
class ProficiencyResult:
    level: int  # 1-5
    years: float
    explanation: str


def merge_date_intervals(intervals: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """Merge overlapping or contiguous date ranges."""
    if not intervals:
        return []

    # Filter invalid intervals where start > end
    valid = [(s, e) for s, e in intervals if s <= e]
    if not valid:
        return []

    # Sort by start date, then end date
    sorted_ivs = sorted(valid, key=lambda x: (x[0], x[1]))
    merged: list[tuple[date, date]] = [sorted_ivs[0]]

    for current in sorted_ivs[1:]:
        prev_start, prev_end = merged[-1]
        cur_start, cur_end = current

        if cur_start <= prev_end:
            # Overlap or contiguous: merge
            merged[-1] = (prev_start, max(prev_end, cur_end))
        else:
            merged.append(current)

    return merged


def calculate_years_from_intervals(intervals: list[tuple[date, date]]) -> float:
    """Calculate total years from merged intervals."""
    merged = merge_date_intervals(intervals)
    total_days = sum((end - start).days + 1 for start, end in merged)
    years = round(total_days / 365.25, 1)
    return max(0.0, years)


def estimate_proficiency(
    role_intervals: list[tuple[date, date]],
    evidence_texts: list[str],
    is_skills_section_only: bool = False,
    config: ProficiencyConfig | None = None,
) -> ProficiencyResult:
    """Estimate skill proficiency level (1-5) and provide a concise explanation."""
    cfg = config or ProficiencyConfig.load()

    years = calculate_years_from_intervals(role_intervals)

    # 1. Base level from years
    base_level = 2
    for upper_bound, lvl in cfg.years_to_base_level:
        if years < upper_bound:
            base_level = lvl
            break

    # 2. Qualifier wording check
    combined_evidence = " ".join(evidence_texts).casefold()
    found_raise = [q for q in cfg.qualifiers_raise if q in combined_evidence]
    found_lower = [q for q in cfg.qualifiers_lower if q in combined_evidence]

    delta = 0
    qual_reason = ""
    if found_raise and not found_lower:
        delta = cfg.qualifiers_delta
        qual_reason = f" + '{found_raise[0]}' qualifier"
    elif found_lower and not found_raise:
        delta = -cfg.qualifiers_delta
        qual_reason = f" - '{found_lower[0]}' qualifier"

    level = base_level + delta

    # 3. Skills-section-only cap
    capped_reason = ""
    if is_skills_section_only:
        if level > cfg.skills_section_only_cap:
            level = cfg.skills_section_only_cap
            capped_reason = (
                f" (capped at {cfg.skills_section_only_cap}: listed in skills section only)"
            )
        else:
            capped_reason = " (listed in skills section only)"

    # Clamp to [1, 5]
    final_level = max(1, min(5, level))

    # Explanation construction
    if is_skills_section_only:
        explanation = f"Level {final_level}{capped_reason}"
    else:
        role_count = len(role_intervals)
        plural = "role" if role_count == 1 else "roles"
        explanation = (
            f"{years}y across {role_count} {plural} (base level {base_level}){qual_reason}"
        )

    return ProficiencyResult(level=final_level, years=years, explanation=explanation)
