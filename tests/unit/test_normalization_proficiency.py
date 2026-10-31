"""Unit tests for Step 3.6 & Exit Criterion 3-D: Proficiency estimation."""

from datetime import date

from talentgraph.agents.normalization.proficiency import (
    estimate_proficiency,
    merge_date_intervals,
)


def test_merge_date_intervals_and_overlaps() -> None:
    # Two overlapping roles: 2020-01-01 to 2022-01-01 (2y), and 2021-01-01 to 2023-01-01 (2y)
    r1 = (date(2020, 1, 1), date(2022, 1, 1))
    r2 = (date(2021, 1, 1), date(2023, 1, 1))

    merged = merge_date_intervals([r1, r2])
    assert len(merged) == 1
    assert merged[0] == (date(2020, 1, 1), date(2023, 1, 1))


def test_year_bands() -> None:
    # Band 1: 0-2y -> base level 2
    r_1y = [(date(2022, 1, 1), date(2023, 1, 1))]
    res_1y = estimate_proficiency(r_1y, [])
    assert res_1y.level == 2
    assert 0.9 <= res_1y.years <= 1.1

    # Band 2: 2-5y -> base level 3
    r_3y = [(date(2020, 1, 1), date(2023, 1, 1))]
    res_3y = estimate_proficiency(r_3y, [])
    assert res_3y.level == 3
    assert 2.9 <= res_3y.years <= 3.1

    # Band 3: 5-8y -> base level 4
    r_6y = [(date(2017, 1, 1), date(2023, 1, 1))]
    res_6y = estimate_proficiency(r_6y, [])
    assert res_6y.level == 4
    assert 5.9 <= res_6y.years <= 6.1

    # Band 4: 8+y -> base level 5
    r_10y = [(date(2013, 1, 1), date(2023, 1, 1))]
    res_10y = estimate_proficiency(r_10y, [])
    assert res_10y.level == 5
    assert res_10y.years >= 9.9


def test_qualifier_wording_adjustments() -> None:
    # 3 years = base level 3
    r_3y = [(date(2020, 1, 1), date(2023, 1, 1))]

    # +1 qualifier ("architected", "led")
    res_up = estimate_proficiency(r_3y, ["Architected the primary backend service with Python."])
    assert res_up.level == 4  # 3 + 1
    assert "architected" in res_up.explanation

    # -1 qualifier ("familiar with", "basic")
    res_down = estimate_proficiency(r_3y, ["Familiar with basic Python scripts."])
    assert res_down.level == 2  # 3 - 1
    assert "familiar with" in res_down.explanation

    # Upper clamp: 10y (base 5) + 'led' -> clamped at 5
    r_10y = [(date(2013, 1, 1), date(2023, 1, 1))]
    res_clamp_high = estimate_proficiency(r_10y, ["Led the team."])
    assert res_clamp_high.level == 5


def test_skills_section_only_cap() -> None:
    # When listed only in skills section without role evidence, capped at 2
    res_skills_only = estimate_proficiency([], [], is_skills_section_only=True)
    assert res_skills_only.level <= 2
    assert (
        "capped at 2" in res_skills_only.explanation
        or "skills section only" in res_skills_only.explanation
    )

    # Even if someone claims "expert in" in raw text, skills-section-only remains capped at 2
    res_skills_only_expert = estimate_proficiency(
        [], ["expert in C++"], is_skills_section_only=True
    )
    assert res_skills_only_expert.level == 2
