"""Step 2.11: merge rule and LLM output into a ParsedResume (plan §6.1 step 7).

Merge rules:

- **Contact fields:** rules win for email, phone and links; the LLM only fills gaps. The LLM wins
  for the name and location, with the rule guesses as fallback.
- **Structured entities** (experience, education, certifications, projects): the LLM wins. Its
  verbatim date text is re-parsed by the date rules, so normalization is deterministic.
- **Skills:** the items under a skills header (rules) are kept as written; LLM skills that match
  one only add a category, and the rest are appended.
- **Long text** (summary, bullets, project descriptions) is copied from the source lines the LLM
  pointed at, so it is grounded by construction (`verified=True`). A pointer to a line that does
  not exist counts as one unverified LLM field.

Without an LLM extraction the result is rules-only: contact fields, the summary paragraph and
skills (the skills section, else alias-index hits).
"""

from dataclasses import dataclass, field
from datetime import date

from rapidfuzz import fuzz

from talentgraph.agents.parsing.llm_extract import NumberedLines
from talentgraph.agents.parsing.rules import (
    EMAIL_RE,
    Match,
    RuleResult,
    months_between,
    normalize_alias,
    normalize_date,
    parse_date_text,
)
from talentgraph.agents.parsing.sections import Section
from talentgraph.core.schemas.resume import (
    Certification,
    Education,
    Experience,
    Extracted,
    FieldSource,
    LLMCertification,
    LLMEducation,
    LLMExperience,
    LLMProject,
    LLMSkill,
    Location,
    ParsedResume,
    Personal,
    Project,
    ResumeExtraction,
    Skill,
)

RULE_CONFIDENCE = {
    "email": 0.98,
    "phone": 0.95,
    "links": 0.95,
    "location": 0.8,
    "name": 0.7,
    "summary": 0.85,
    "skills": 0.9,
    "skill_candidates": 0.6,
}
SKILL_MATCH_MIN = 85


@dataclass
class MergeOutput:
    resume: ParsedResume
    invalid_line_refs: int = 0
    warnings: list[str] = field(default_factory=list)


def from_rule(m: Match, confidence: float) -> Extracted[str]:
    return Extracted[str](value=m.value, evidence=m.evidence, confidence=confidence, verified=True)


def from_llm[V](value: V | None, evidence: str | None, confidence: float) -> Extracted[V] | None:
    """An LLM value, unverified until the evidence verifier runs; None stays None."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return Extracted[V](value=value, evidence=evidence, confidence=confidence)


def grounded_text(value: str, confidence: float) -> Extracted[str]:
    """Text copied from source lines: verified by construction."""
    return Extracted[str](value=value, evidence=value, confidence=confidence, verified=True)


def build_resume(
    rules: RuleResult,
    sections: list[Section],
    extraction: ResumeExtraction | None,
    lines: NumberedLines | None,
    *,
    today: date,
) -> MergeOutput:
    out = MergeOutput(resume=ParsedResume())
    resume = out.resume
    sources = resume.meta.field_sources
    use_llm = extraction is not None and lines is not None
    x = extraction if extraction is not None else ResumeExtraction()
    nl = lines if lines is not None else NumberedLines({})
    ym = (today.year, today.month)

    resume.personal = _personal(rules, x if use_llm else None, sources)

    # Summary: LLM-selected lines, else the whole summary section.
    if use_llm and x.summary_lines:
        known, unknown = nl.valid(x.summary_lines)
        out.invalid_line_refs += unknown
        if known:
            resume.summary = grounded_text(nl.paragraph(known), x.confidence)
            sources["summary"] = "llm"
    elif not use_llm:
        summary_blocks = [b.text for s in sections if s.label == "summary" for b in s.blocks]
        if summary_blocks:
            resume.summary = grounded_text(" ".join(summary_blocks), RULE_CONFIDENCE["summary"])
            sources["summary"] = "rules"

    if use_llm:
        for item in x.experience:
            exp, unknown = _experience(item, nl, ym)
            out.invalid_line_refs += unknown
            resume.experience.append(exp)
        resume.education = [_education(e) for e in x.education]
        resume.certifications = [_certification(c) for c in x.certifications if c.name.strip()]
        for p in x.projects:
            if p.name.strip():
                project, unknown = _project(p, nl)
                out.invalid_line_refs += unknown
                resume.projects.append(project)
        for key in ("experience", "education", "certifications", "projects"):
            if getattr(resume, key):
                sources[key] = "llm"

    resume.skills, skill_source = _skills(rules, x.skills if use_llm else [])
    if skill_source:
        sources["skills"] = skill_source
    if out.invalid_line_refs:
        out.warnings.append(f"LLM referenced {out.invalid_line_refs} line(s) that do not exist.")
    return out


# -------------------------------------------------------------------------------------------------
# Sections of the merge
# -------------------------------------------------------------------------------------------------


def _personal(
    rules: RuleResult, x: ResumeExtraction | None, sources: dict[str, FieldSource]
) -> Personal:
    personal = Personal()
    confidence = x.confidence if x else 0.0

    if x and x.name:
        personal.name = from_llm(x.name.strip(), x.name.strip(), confidence)
        sources["name"] = "llm"
    elif rules.name:
        personal.name = from_rule(rules.name, RULE_CONFIDENCE["name"])
        sources["name"] = "rules"

    if rules.email:
        personal.email = from_rule(rules.email, RULE_CONFIDENCE["email"])
        sources["email"] = "rules"
    elif x and x.email and EMAIL_RE.fullmatch(x.email.strip()):
        personal.email = from_llm(x.email.strip().lower(), x.email.strip(), confidence)
        sources["email"] = "llm"

    if rules.phone:
        personal.phone = from_rule(rules.phone, RULE_CONFIDENCE["phone"])
        sources["phone"] = "rules"
    elif x and x.phone and sum(ch.isdigit() for ch in x.phone) >= 7:
        personal.phone = from_llm(x.phone.strip(), x.phone.strip(), confidence)
        sources["phone"] = "llm"

    if rules.links:
        personal.links = [from_rule(m, RULE_CONFIDENCE["links"]) for m in rules.links]
        sources["links"] = "rules"
    elif x and x.links:
        personal.links = [e for u in x.links if (e := from_llm(u.strip(), u.strip(), confidence))]
        sources["links"] = "llm"

    loc = x.location if x else None
    if loc and (loc.city or loc.region or loc.country):
        value = Location(city=loc.city, region=loc.region, country=loc.country)
        evidence = loc.evidence or ", ".join(p for p in (loc.city, loc.region) if p)
        personal.location = from_llm(value, evidence, confidence)
        sources["location"] = "llm"
    elif rules.location:
        city, region = rules.location
        personal.location = Extracted[Location](
            value=Location(city=city, region=region),
            evidence=rules.location_text,
            confidence=RULE_CONFIDENCE["location"],
            verified=True,
        )
        sources["location"] = "rules"
    return personal


def _dates(
    dates_text: str | None, start: str | None, end: str | None, is_current: bool, confidence: float
) -> tuple[Extracted[str] | None, Extracted[str] | None, bool]:
    """Normalize a date range: rules parse the verbatim text, else the LLM's own values."""
    parsed = parse_date_text(dates_text)
    if parsed:
        s, e, current = parsed.start, parsed.end, parsed.is_current or is_current
    else:
        s, e, current = normalize_date(start), normalize_date(end), is_current
    if current:
        e = None
    if s and e and _ym_tuple(e) < _ym_tuple(s):
        s, e = e, s  # written backwards ("2022 – 2018"); keep both, in order
    evidence = dates_text or None
    return from_llm(s, evidence, confidence), from_llm(e, evidence, confidence), current


def _ym_tuple(value: str) -> tuple[int, int]:
    year, _, month = value.partition("-")
    return int(year), int(month) if month else 0


def _experience(
    item: LLMExperience, nl: NumberedLines, today: tuple[int, int]
) -> tuple[Experience, int]:
    c = item.confidence
    start, end, current = _dates(item.dates_text, item.start, item.end, item.is_current, c)
    known, unknown = nl.valid(item.bullet_lines)
    exp = Experience(
        company=from_llm(item.company.strip(), item.company.strip(), c),
        title=from_llm(item.title.strip(), item.title.strip(), c),
        location=from_llm(item.location, item.location, c),
        start=start,
        end=end,
        is_current=current,
        duration_months=months_between(
            start.value if start else None, end.value if end else None, today=today
        )
        if start and (end or current)
        else None,
        responsibilities=[grounded_text(b, c) for b in nl.bullets(known)],
        skills_mentioned=[s.strip() for s in item.skills_mentioned if s.strip()],
    )
    return exp, unknown


def _education(item: LLMEducation) -> Education:
    c = item.confidence
    start, end, _ = _dates(item.dates_text, item.start, item.end, False, c)
    return Education(
        institution=from_llm(item.institution.strip(), item.institution.strip(), c),
        degree=from_llm(item.degree, item.degree, c),
        field=from_llm(item.field, item.field, c),
        start=start,
        end=end,
        grade=from_llm(item.grade, item.grade, c),
    )


def _certification(item: LLMCertification) -> Certification:
    c = item.confidence
    parsed = parse_date_text(item.date_text)
    when = parsed.start if parsed else normalize_date(item.date)
    name = from_llm(item.name.strip(), item.name.strip(), c)
    assert name is not None  # callers skip blank names
    return Certification(
        name=name,
        issuer=from_llm(item.issuer, item.issuer, c),
        date=from_llm(when, item.date_text, c),
        credential_id=from_llm(item.credential_id, item.credential_id, c),
    )


def _project(item: LLMProject, nl: NumberedLines) -> tuple[Project, int]:
    c = item.confidence
    known, unknown = nl.valid(item.description_lines)
    name = from_llm(item.name.strip(), item.name.strip(), c)
    assert name is not None  # callers skip blank names
    project = Project(
        name=name,
        description=grounded_text(nl.paragraph(known), c) if known else None,
        technologies=[t.strip() for t in item.technologies if t.strip()],
        url=from_llm(item.url, item.url, c),
        dates=from_llm(item.dates, item.dates, c),
    )
    return project, unknown


def _skills(
    rules: RuleResult, llm_skills: list[LLMSkill]
) -> tuple[list[Skill], FieldSource | None]:
    skills = [
        Skill(raw=item, evidence=item, confidence=RULE_CONFIDENCE["skills"], verified=True)
        for item in rules.skills_section
    ]
    source: FieldSource | None = "rules" if skills else None
    keys = [normalize_alias(s.raw) for s in skills]
    for llm_skill in llm_skills:
        name = llm_skill.name.strip()
        if not name:
            continue
        key = normalize_alias(name)
        best = max(range(len(keys)), key=lambda i: fuzz.ratio(key, keys[i]), default=None)
        if best is not None and fuzz.ratio(key, keys[best]) >= SKILL_MATCH_MIN:
            if llm_skill.category != "unknown":
                skills[best].category_hint = llm_skill.category
            source = "merged"
            continue
        skills.append(
            Skill(
                raw=name,
                category_hint=llm_skill.category,
                evidence=name,
                confidence=llm_skill.confidence,
            )
        )
        keys.append(key)
        source = "merged" if source in ("rules", "merged") else "llm"
    if not skills and rules.skill_candidates:
        skills = [
            Skill(raw=s, evidence=s, confidence=RULE_CONFIDENCE["skill_candidates"], verified=True)
            for s in rules.skill_candidates
        ]
        source = "rules"
    return skills, source
