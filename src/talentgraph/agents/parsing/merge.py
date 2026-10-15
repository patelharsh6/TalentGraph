"""Step 2.11: merge rule and LLM output into a ParsedResume (plan §6.1 step 7).

Merge rules:

- **Contact fields:** rules win for email, phone and links; the LLM only fills gaps. The LLM wins
  for the name and location, with the rule guesses as fallback.
- **Structured entities** (experience, education, certifications, projects): the LLM wins. It
  returns dates only as verbatim text, which the date rules normalize (start, end, current).
- **Skills:** the items under a skills header (rules) are kept as written; the LLM adds only
  skills that are not in that list (a near-duplicate just adds its category). Each role's
  `skills_mentioned` is every resume skill named in that role's bullets.
- **Long text** (summary, bullets, project descriptions) is copied from the source lines the LLM
  pointed at, so it is grounded by construction (`verified=True`). A reference to a line that
  does not exist counts as one unverified LLM field.
- **Confidence:** the model's own confidence was uninformative (always 0.95), so LLM values start
  at `LLM_CONFIDENCE`; the verifier halves it when the evidence is not found (ADR-0005).

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

LLM_CONFIDENCE = 0.9
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


def from_llm[V](
    value: V | None, evidence: str | None, confidence: float = LLM_CONFIDENCE
) -> Extracted[V] | None:
    """An LLM value, unverified until the evidence verifier runs; None stays None."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, str):
        value = value.strip()  # type: ignore[assignment]
    return Extracted[V](value=value, evidence=evidence, confidence=confidence)


def grounded_text(value: str, confidence: float = LLM_CONFIDENCE) -> Extracted[str]:
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
        known, invalid = nl.valid(x.summary_lines)
        out.invalid_line_refs += invalid
        if known:
            resume.summary = grounded_text(nl.paragraph(known))
            sources["summary"] = "llm"
    elif not use_llm:
        summary_blocks = [b.text for s in sections if s.label == "summary" for b in s.blocks]
        if summary_blocks:
            resume.summary = grounded_text(" ".join(summary_blocks), RULE_CONFIDENCE["summary"])
            sources["summary"] = "rules"

    resume.skills, skill_source = _skills(rules, x.skills if use_llm else [])
    if skill_source:
        sources["skills"] = skill_source

    if use_llm:
        for item in x.experience:
            exp, invalid = _experience(item, nl, ym, resume.skills)
            out.invalid_line_refs += invalid
            resume.experience.append(exp)
        resume.education = [_education(e) for e in x.education]
        resume.certifications = [_certification(c) for c in x.certifications if c.name.strip()]
        for p in x.projects:
            if p.name.strip():
                project, invalid = _project(p, nl)
                out.invalid_line_refs += invalid
                resume.projects.append(project)
        for key in ("experience", "education", "certifications", "projects"):
            if getattr(resume, key):
                sources[key] = "llm"

    if out.invalid_line_refs:
        out.warnings.append(
            f"LLM referenced {out.invalid_line_refs} line range(s) that do not exist."
        )
    return out


# -------------------------------------------------------------------------------------------------
# Sections of the merge
# -------------------------------------------------------------------------------------------------


def _personal(
    rules: RuleResult, x: ResumeExtraction | None, sources: dict[str, FieldSource]
) -> Personal:
    personal = Personal()

    if x and x.name:
        personal.name = from_llm(x.name, x.name)
        sources["name"] = "llm"
    elif rules.name:
        personal.name = from_rule(rules.name, RULE_CONFIDENCE["name"])
        sources["name"] = "rules"

    if rules.email:
        personal.email = from_rule(rules.email, RULE_CONFIDENCE["email"])
        sources["email"] = "rules"
    elif x and x.email and EMAIL_RE.fullmatch(x.email.strip()):
        personal.email = from_llm(x.email.strip().lower(), x.email)
        sources["email"] = "llm"

    if rules.phone:
        personal.phone = from_rule(rules.phone, RULE_CONFIDENCE["phone"])
        sources["phone"] = "rules"
    elif x and x.phone and sum(ch.isdigit() for ch in x.phone) >= 7:
        personal.phone = from_llm(x.phone, x.phone)
        sources["phone"] = "llm"

    if rules.links:
        personal.links = [from_rule(m, RULE_CONFIDENCE["links"]) for m in rules.links]
        sources["links"] = "rules"
    elif x and x.links:
        personal.links = [e for u in x.links if (e := from_llm(u, u))]
        sources["links"] = "llm"

    loc = x.location if x else None
    if loc and (loc.city or loc.region or loc.country):
        value = Location(city=loc.city, region=loc.region, country=loc.country)
        # Evidence: the city and region as written; the country is often implied, not written.
        evidence = ", ".join(p for p in (loc.city, loc.region) if p) or loc.country
        personal.location = from_llm(value, evidence)
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


def _dates(dates_text: str | None) -> tuple[Extracted[str] | None, Extracted[str] | None, bool]:
    """Normalize the verbatim date text with the date rules; the text is the evidence."""
    parsed = parse_date_text(dates_text)
    if parsed is None:
        return None, None, False
    start, end = parsed.start, None if parsed.is_current else parsed.end
    if start and end and _ym_tuple(end) < _ym_tuple(start):
        start, end = end, start  # written backwards ("2022 – 2018"); keep both, in order
    return from_llm(start, dates_text), from_llm(end, dates_text), parsed.is_current


def _ym_tuple(value: str) -> tuple[int, int]:
    year, _, month = value.partition("-")
    return int(year), int(month) if month else 0


def _experience(
    item: LLMExperience, nl: NumberedLines, today: tuple[int, int], skills: list[Skill]
) -> tuple[Experience, int]:
    start, end, current = _dates(item.dates_text)
    known, invalid = nl.valid(item.bullet_lines)
    bullets = nl.bullets(known)
    text = " ".join(bullets).casefold()
    exp = Experience(
        company=from_llm(item.company, item.company),
        title=from_llm(item.title, item.title),
        location=from_llm(item.location, item.location),
        start=start,
        end=end,
        is_current=current,
        duration_months=months_between(
            start.value if start else None, end.value if end else None, today=today
        )
        if start and (end or current)
        else None,
        responsibilities=[grounded_text(b) for b in bullets],
        skills_mentioned=[s.raw for s in skills if s.raw.casefold() in text],
    )
    return exp, invalid


def _education(item: LLMEducation) -> Education:
    start, end, _ = _dates(item.dates_text)
    return Education(
        institution=from_llm(item.institution, item.institution),
        degree=from_llm(item.degree, item.degree),
        field=from_llm(item.field, item.field),
        start=start,
        end=end,
        grade=from_llm(item.grade, item.grade),
    )


def _certification(item: LLMCertification) -> Certification:
    parsed = parse_date_text(item.date_text)
    name = from_llm(item.name, item.name)
    assert name is not None  # callers skip blank names
    return Certification(
        name=name,
        issuer=from_llm(item.issuer, item.issuer),
        date=from_llm(parsed.start if parsed else None, item.date_text),
        credential_id=from_llm(item.credential_id, item.credential_id),
    )


def _project(item: LLMProject, nl: NumberedLines) -> tuple[Project, int]:
    known, invalid = nl.valid(item.description_lines)
    name = from_llm(item.name, item.name)
    assert name is not None  # callers skip blank names
    project = Project(
        name=name,
        description=grounded_text(nl.paragraph(known)) if known else None,
        technologies=[t.strip() for t in item.technologies if t.strip()],
        url=from_llm(item.url, item.url),
        dates=from_llm(item.dates, item.dates),
    )
    return project, invalid


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
                confidence=LLM_CONFIDENCE,
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
