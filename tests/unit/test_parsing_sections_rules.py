"""Steps 2.7–2.8: section detection and the rule extractors (exit criterion 2-A)."""

import re
from pathlib import Path

import pytest
import yaml
from parsing_samples import LEXICON, SAMPLES, Sample
from rapidfuzz import fuzz

from talentgraph.agents.parsing.layout import Block, LayoutDocument
from talentgraph.agents.parsing.rules import (
    find_date_ranges,
    find_email,
    find_links,
    find_location,
    find_phone,
    find_skill_candidates,
    guess_name,
    load_alias_index,
    months_between,
    normalize_date,
    parse_date_text,
    run_rules,
    split_skill_items,
)
from talentgraph.agents.parsing.sections import (
    Section,
    detect_sections,
    load_lexicon,
    normalize_header,
)

OPTIONAL = ("summary", "experience", "education", "skills", "certifications", "projects")


# -------------------------------------------------------------------------------------------------
# Sections
# -------------------------------------------------------------------------------------------------


def test_lexicon_has_150_unique_variants() -> None:
    raw = yaml.safe_load(Path(LEXICON).read_text(encoding="utf-8"))
    variants = [normalize_header(v) for vs in raw.values() for v in vs]
    assert len(variants) >= 150
    assert len(variants) == len(set(variants)), "a variant is listed twice"


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s.id)
def test_detects_the_rendered_sections(sample: Sample) -> None:
    sections = detect_sections(sample.layout(), load_lexicon(LEXICON))
    labels = [s.label for s in sections]
    assert labels[0] == "contact"
    # Sidebar layouts repeat the contact block under a "Contact" header.
    assert set(labels[1:]) - {"contact"} == {k for k in OPTIONAL if sample.gold.get(k)}
    assert labels.count("experience") == 1


def _doc(*blocks: Block) -> LayoutDocument:
    return LayoutDocument(file_type="pdf", blocks=list(blocks))


def test_header_signals() -> None:
    lex = load_lexicon(LEXICON)
    body = 9.0
    doc = _doc(
        Block("Jane Roe", font_size=18, bold=True),
        Block("jane@x.com", font_size=body),
        Block("▸ Relevant Work Experience", font_size=12, bold=True),  # keyword + icon
        Block("Customer Experience Manager | Acme", font_size=body, bold=True),  # entry heading
        Block("Education Optimization System", font_size=body, bold=True),  # bold, not a header
        Block("Led things across the experience platform.", font_size=body),
        Block("Volunteering", font_size=12, bold=True),
        Block("Food bank, 2019", font_size=body),
        Block("Hobbies & Things", font_size=12, bold=True),  # larger, unknown: other
        *(Block(f"filler line {i} for body size", font_size=body) for i in range(6)),
    )
    sections = detect_sections(doc, lex)
    assert [(s.label, s.header) for s in sections] == [
        ("contact", None),
        ("experience", "▸ Relevant Work Experience"),
        ("other", "Volunteering"),
        ("other", "Hobbies & Things"),
    ]
    assert len(sections[1].blocks) == 3


def test_header_wrapped_over_two_lines() -> None:
    doc = _doc(
        Block("Jane Roe", font_size=18, bold=True),
        Block("Skills", font_size=11.5, bold=True),
        Block("Python, SQL", font_size=8),
        Block("Certifications &", font_size=11.5, bold=True),
        Block("Licenses", font_size=11.5, bold=True),
        Block("AWS Certified", font_size=8),
    )
    sections = detect_sections(doc, load_lexicon(LEXICON))
    assert [s.label for s in sections] == ["contact", "skills", "certifications"]
    assert sections[1].text == "Python, SQL"
    assert sections[2].header == "Certifications & Licenses"


# -------------------------------------------------------------------------------------------------
# Contact rules
# -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "phone"),
    [
        ("call (833)215-8692x322 now", "(833)215-8692x322"),
        ("a@b.co | 001-626-728-4987x769 | City, ST", "001-626-728-4987x769"),
        ("+1-677-219-0659", "+1-677-219-0659"),
        ("669.373.5779x071", "669.373.5779x071"),
        ("4155551234", "4155551234"),
        ("+44 20 7946 0958", "+44 20 7946 0958"),
        ("555-123-4567 ext. 89", "555-123-4567 ext. 89"),
    ],
)
def test_phone_formats(text: str, phone: str) -> None:
    found = find_phone(text)
    assert found is not None and found.value == phone


def test_phone_ignores_dates_and_ids() -> None:
    assert find_phone("Jun 2018 – 2022-10 · ID CERT-865990 · 3.85 GPA") is None


def test_email_links_location_name() -> None:
    line = (
        "Steven.Flynn@Gmail.com | (833)215-8692 | Lake Sandra, WY | "
        "https://linkedin.com/in/steven-flynn | github.com/stevenflynn."
    )
    email = find_email(line)
    assert email is not None and email.value == "steven.flynn@gmail.com"
    assert [m.value for m in find_links(line)] == [
        "https://linkedin.com/in/steven-flynn",
        "https://github.com/stevenflynn",
    ]
    loc = find_location([line])
    assert loc is not None and loc[0] == ("Lake Sandra", "WY")
    name = guess_name(["STEVEN FLYNN", line])
    assert name is not None and name.value == "Steven Flynn"
    assert guess_name(["steven.flynn@gmail.com"]) is None


# -------------------------------------------------------------------------------------------------
# Dates
# -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "start", "end", "current"),
    [
        ("10/2022 – Present · West Erik, UT", "2022-10", None, True),
        ("Jun 2018 – Oct. 2022", "2018-06", "2022-10", False),
        ("Apr. 2014 – 06/2018", "2014-04", "2018-06", False),
        ("02/2010 – 2014-04", "2010-02", "2014-04", False),
        ("2020 – 07/2023", "2020", "2023-07", False),
        ("Sept. 2018 to May 2020", "2018-09", "2020-05", False),
        ("2018-2022", "2018", "2022", False),
        ("January 2021 - current", "2021-01", None, True),
    ],
)
def test_date_ranges(text: str, start: str, end: str | None, current: bool) -> None:
    ranges = find_date_ranges(text)
    assert len(ranges) == 1
    assert (ranges[0].start, ranges[0].end, ranges[0].is_current) == (start, end, current)


def test_single_dates_and_months() -> None:
    single = parse_date_text("Industry Board · Jun 2023 · ID CERT-1")
    assert single is not None and single.start == "2023-06"
    assert normalize_date("2023") == "2023"
    assert normalize_date("not a date") is None
    assert months_between("2022-10", None, today=(2026, 10)) == 48
    assert months_between("2018", "2020-06", today=(2026, 10)) == 29
    assert months_between(None, None, today=(2026, 10)) is None


# -------------------------------------------------------------------------------------------------
# Skills
# -------------------------------------------------------------------------------------------------


def test_skill_items_rejoin_wrapped_lines() -> None:
    section = Section(
        label="skills",
        header="Skills",
        blocks=[
            Block("Learning Management Systems (LMS), Active Mentoring, Instructional"),
            Block("Design, HTML5 / CSS3, OKRs / KPIs Tracking"),
            Block("• Python"),
            Block("Languages: Go; Rust"),
        ],
    )
    assert split_skill_items(section) == [
        "Learning Management Systems (LMS)",
        "Active Mentoring",
        "Instructional Design",
        "HTML5 / CSS3",
        "OKRs / KPIs Tracking",
        "Python",
        "Go",
        "Rust",
    ]


def test_skill_candidates_longest_match() -> None:
    index = frozenset({"python", "machine learning", "react", "react native"})
    text = "Built React Native apps and Python machine learning models"
    assert find_skill_candidates(text, index) == ["React Native", "Python", "machine learning"]
    assert find_skill_candidates(text, frozenset()) == []


def test_alias_index_loads_taxonomy_without_ambiguous_aliases() -> None:
    index = load_alias_index(str(Path(LEXICON).parents[1] / "data" / "taxonomy"))
    assert {"javascript", "kubernetes", "react js"} <= index
    assert "go" not in index and "r" not in index


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s.id)
def test_rules_on_fixture_resumes(sample: Sample) -> None:
    doc = sample.layout()
    rules = run_rules(detect_sections(doc, load_lexicon(LEXICON)), doc.text, frozenset())
    gold = sample.gold
    p = gold["personal"]
    assert rules.email is not None and rules.email.value == p["email"]
    assert rules.phone is not None
    assert re.sub(r"\D", "", rules.phone.value) == re.sub(r"\D", "", p["phone"])
    assert rules.location == (p["location"]["city"], p["location"]["region"])
    assert [m.value for m in rules.links] == p["links"]
    assert rules.name is not None and fuzz.ratio(rules.name.value, p["name"]) >= 85
    assert len(rules.date_ranges) == len(gold["experience"]) + len(gold["education"])
    gold_skills = [s["raw"] for s in gold["skills"]]
    matched = sum(any(fuzz.ratio(g, r) >= 80 for r in rules.skills_section) for g in gold_skills)
    assert matched == len(gold_skills) == len(rules.skills_section)
