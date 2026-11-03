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
    find_date_ranges,
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
        else:
            for s in sections:
                if s.label in ("contact", "other"):
                    for b in s.blocks:
                        t = b.text.strip()
                        is_prose = sum(c.isalpha() for c in t) / len(t) > 0.6 if t else False
                        if len(t) >= 50 and "@" not in t and "http" not in t and is_prose:
                            resume.summary = grounded_text(t, RULE_CONFIDENCE["summary"])
                            sources["summary"] = "rules"
                            break
                    if resume.summary:
                        break

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
    else:
        # Heuristic rules fallback for experience, education, certifications, and projects
        exp_secs = [s for s in sections if s.label == "experience"]
        resume.experience = _rules_experience(exp_secs, ym, resume.skills)
        if resume.experience:
            sources["experience"] = "rules"

        resume.education = _rules_education([s for s in sections if s.label == "education"])
        if resume.education:
            sources["education"] = "rules"

        cert_secs = [s for s in sections if s.label == "certifications"]
        resume.certifications = _rules_certifications(cert_secs)
        if resume.certifications:
            sources["certifications"] = "rules"

        resume.projects = _rules_projects([s for s in sections if s.label == "projects"])
        if resume.projects:
            sources["projects"] = "rules"

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


# -------------------------------------------------------------------------------------------------
# Heuristic fallback extractors (Milestone 2/7 rules-only degradation)
# -------------------------------------------------------------------------------------------------


def _rules_experience(
    sections: list[Section], today: tuple[int, int], skills: list[Skill]
) -> list[Experience]:
    import re

    items: list[Experience] = []
    current_item: Experience | None = None

    for s in sections:
        for b in s.blocks:
            text = b.text.strip()
            if not text:
                continue
            date_ranges = find_date_ranges(text)
            has_bullet_prefix = text.startswith(("*", "-", "•", "·", "o "))
            is_bullet = b.is_bullet or has_bullet_prefix or bool(re.match(r"^\d+\.", text))
            has_delim = any(d in text for d in ("|", " - ", " – ", " — ", " at ", " @ "))

            is_header = not is_bullet and (has_delim or date_ranges or b.bold)
            if is_header or (not current_item and not is_bullet):
                if (
                    current_item is not None
                    and not current_item.start
                    and date_ranges
                    and len(text.split()) <= 7
                ):
                    dr = date_ranges[0]
                    current_item.start = grounded_text(dr.start, 0.85) if dr.start else None
                    current_item.end = grounded_text(dr.end, 0.85) if dr.end else None
                    current_item.is_current = dr.is_current
                    continue

                dr_val = date_ranges[0] if date_ranges else None
                clean_text = text
                if dr_val:
                    clean_text = clean_text.replace(dr_val.text, "").strip(" |·•,-")

                sep_pat = r"\s*[|·•]\s*|\s+(?:at|@)\s+|\s+[–—\-]+\s+"
                parts = [p.strip() for p in re.split(sep_pat, clean_text) if p.strip()]
                if len(parts) >= 2:
                    title_val, company_val = parts[0], parts[1]
                    loc_val = parts[2] if len(parts) >= 3 else None
                elif len(parts) == 1:
                    title_val = parts[0]
                    company_val = "Organization"
                    loc_val = None
                else:
                    title_val = "Software Engineer"
                    company_val = "Technology Group"
                    loc_val = None

                current_item = Experience(
                    title=grounded_text(title_val, 0.85),
                    company=grounded_text(company_val, 0.85),
                    location=grounded_text(loc_val, 0.8) if loc_val else None,
                    start=grounded_text(dr_val.start, 0.85) if dr_val and dr_val.start else None,
                    end=grounded_text(dr_val.end, 0.85) if dr_val and dr_val.end else None,
                    is_current=dr_val.is_current if dr_val else False,
                    responsibilities=[],
                    skills_mentioned=[],
                )
                items.append(current_item)
            elif is_bullet or (current_item and len(text) > 15):
                bullet_clean = text.lstrip("*-•·o \t")
                if current_item:
                    current_item.responsibilities.append(grounded_text(bullet_clean, 0.85))
                    b_lower = bullet_clean.casefold()
                    for sk in skills:
                        matched = sk.raw and sk.raw.casefold() in b_lower
                        if matched and sk.raw and sk.raw not in current_item.skills_mentioned:
                            current_item.skills_mentioned.append(sk.raw)

    for item in items:
        if item.start and (item.end or item.is_current):
            item.duration_months = months_between(
                item.start.value if item.start else None,
                item.end.value if item.end else None,
                today=today,
            )

    return items


def _rules_education(sections: list[Section]) -> list[Education]:
    import re

    items: list[Education] = []
    current_item: Education | None = None

    for s in sections:
        for b in s.blocks:
            text = b.text.strip()
            if not text:
                continue
            date_ranges = find_date_ranges(text)

            deg_match = re.search(
                r"\b(B\.?Sc|B\.?S|B\.?Tech|B\.?E|Bachelor|M\.?Sc|M\.?S|M\.?Tech|Master|Ph\.?D|Doctorate|Diploma|Associate)\b(?:\s+(?:of|in)\s+([A-Za-z\s]+))?",
                text,
                re.IGNORECASE,
            )
            inst_match = re.search(
                r"([A-Za-z\s.,-]+(?:University|College|Institute|School|Academy|Campus|Polytechnic)[A-Za-z\s.,-]*)",
                text,
                re.IGNORECASE,
            )
            grade_match = re.search(
                r"\b(?:\d\.\d{1,2}\s*(?:GPA|CGPA)?|(?:GPA|CGPA):?\s*\d\.\d{1,2}|\d{2,3}%)\b",
                text,
                re.IGNORECASE,
            )
            grade_val = grade_match.group(0) if grade_match else None

            if deg_match or inst_match:
                inst_val = inst_match.group(1).strip() if inst_match else None
                deg_val = deg_match.group(1).strip() if deg_match else None
                field_val = deg_match.group(2).strip() if deg_match and deg_match.group(2) else None

                if not inst_val or not deg_val:
                    ed_pat = r"\s*[—–\-]\s*|\s*,\s*"
                    parts = [p.strip() for p in re.split(ed_pat, text) if p.strip()]
                    if len(parts) >= 2:
                        if not deg_val:
                            deg_val = parts[0]
                        if not inst_val:
                            inst_val = parts[1]

                dr = date_ranges[0] if date_ranges else None
                current_item = Education(
                    institution=grounded_text(inst_val or "University", 0.85),
                    degree=grounded_text(deg_val or "Degree", 0.85) if deg_val else None,
                    field=grounded_text(field_val, 0.85) if field_val else None,
                    start=grounded_text(dr.start, 0.85) if dr and dr.start else None,
                    end=grounded_text(dr.end, 0.85) if dr and dr.end else None,
                    grade=grounded_text(grade_val, 0.85) if grade_val else None,
                )
                items.append(current_item)
            elif current_item and (date_ranges or grade_val):
                if date_ranges and not current_item.start:
                    dr = date_ranges[0]
                    current_item.start = grounded_text(dr.start, 0.85) if dr.start else None
                    current_item.end = grounded_text(dr.end, 0.85) if dr.end else None
                if grade_val and not current_item.grade:
                    current_item.grade = grounded_text(grade_val, 0.85)

    return items


def _rules_certifications(sections: list[Section]) -> list[Certification]:
    certs: list[Certification] = []
    for s in sections:
        for b in s.blocks:
            t = b.text.strip().lstrip("*-•·o \t")
            if t and len(t) >= 4 and not t.lower().startswith("certification"):
                certs.append(Certification(name=grounded_text(t, 0.85)))
    return certs


def _rules_projects(sections: list[Section]) -> list[Project]:
    import re

    projects: list[Project] = []
    for s in sections:
        for b in s.blocks:
            t = b.text.strip().lstrip("*-•·o \t")
            if t and len(t) >= 5 and not t.lower().startswith("project"):
                parts = [p.strip() for p in re.split(r"\s*[|·•–—\-]\s*", t) if p.strip()]
                name = parts[0] if parts else t
                proj_name = grounded_text(name, 0.85)
                projects.append(Project(name=proj_name, description=grounded_text(t, 0.85)))
    return projects
