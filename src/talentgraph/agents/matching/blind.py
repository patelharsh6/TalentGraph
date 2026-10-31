"""Step 4.8: blind-screening redaction (Feature F4, plan §6.3).

Redacts:
- Name and contact details, and photo references
- Gendered words and pronouns
- Age signals: graduation years, birth years, and 'N years old'
- Institutions (employers, colleges, universities)
"""

from __future__ import annotations

import copy
import re

from talentgraph.core.schemas.resume import (
    Extracted,
    ParsedResume,
)
from talentgraph.core.schemas.skills import SkillProfile

# --- Redaction Regexes ----------------------------------------------------------------------------

GENDER_PRONOUNS_RE = re.compile(r"\b(he|she|him|her|his|hers|himself|herself)\b", re.IGNORECASE)

GENDER_NOUNS_RE = re.compile(
    r"\b(mr|mrs|ms|miss|sir|madam|businesswoman|businessman|"
    r"woman|women|man|men|female|male|lady|ladies|"
    r"gentleman|gentlemen|boy|girl|mother|father|sister|brother|son|daughter|"
    r"alumna|alumnae|alumnus|alumni)\b",
    re.IGNORECASE,
)

PHOTO_RE = re.compile(r"\b(photo(?:graph)?|picture|headshot|portrait|avatar)\b", re.IGNORECASE)

AGE_SIGNALS_RE = re.compile(
    r"\b(\d{1,2}\s*(?:years?\s*old|y/?o)|born\s+in\s+\d{4}|dob\s*[:\s]\s*[\d/.-]+|date\s+of\s+birth\s*[:\s]\s*[\d/.-]+)\b",
    re.IGNORECASE,
)

YEAR_RE = re.compile(r"\b(19\d{2}|20[0-2]\d)\b")


def redact_text(text: str) -> str:
    """Scrub gender, photo, age, and graduation signals from a text string."""
    if not text:
        return text

    s = GENDER_PRONOUNS_RE.sub("[REDACTED_PRONOUN]", text)
    s = GENDER_NOUNS_RE.sub("[REDACTED_GENDER]", s)
    s = PHOTO_RE.sub("[REDACTED_PHOTO]", s)
    s = AGE_SIGNALS_RE.sub("[REDACTED_AGE]", s)
    return s


def redact_resume(resume: ParsedResume) -> ParsedResume:
    """Return a sanitized copy of ParsedResume with all PII and bias signals redacted."""
    data = copy.deepcopy(resume.model_dump())

    # 1. Redact Personal Contact
    data["personal"] = {
        "name": Extracted(value="[REDACTED_NAME]", confidence=1.0, evidence=None).model_dump(),
        "email": Extracted(
            value="redacted@candidate.local", confidence=1.0, evidence=None
        ).model_dump(),
        "phone": Extracted(value="[REDACTED_PHONE]", confidence=1.0, evidence=None).model_dump(),
        "location": None,
        "links": [],
    }

    # 2. Redact Summary
    if data.get("summary") and data["summary"].get("value"):
        data["summary"]["value"] = redact_text(data["summary"]["value"])
        data["summary"]["evidence"] = None

    # 3. Redact Experience (scrub employer institutions and gender/age in responsibilities)
    for exp in data.get("experience", []):
        if exp.get("company") and exp["company"].get("value"):
            exp["company"]["value"] = "[REDACTED_EMPLOYER]"
            exp["company"]["evidence"] = None
        if exp.get("location"):
            exp["location"] = None
        cleaned_resps = []
        for r in exp.get("responsibilities", []):
            if r.get("value"):
                r["value"] = redact_text(r["value"])
                r["evidence"] = None
            cleaned_resps.append(r)
        exp["responsibilities"] = cleaned_resps

    # 4. Redact Education (scrub institution names and graduation years)
    for edu in data.get("education", []):
        if edu.get("institution") and edu["institution"].get("value"):
            edu["institution"]["value"] = "[REDACTED_INSTITUTION]"
            edu["institution"]["evidence"] = None
        if edu.get("start") and edu["start"].get("value"):
            edu["start"]["value"] = YEAR_RE.sub("[REDACTED_YEAR]", edu["start"]["value"])
            edu["start"]["evidence"] = None
        if edu.get("end") and edu["end"].get("value"):
            edu["end"]["value"] = YEAR_RE.sub("[REDACTED_YEAR]", edu["end"]["value"])
            edu["end"]["evidence"] = None

    # 5. Redact Projects and Certifications
    for proj in data.get("projects", []):
        if proj.get("description") and proj["description"].get("value"):
            proj["description"]["value"] = redact_text(proj["description"]["value"])
            proj["description"]["evidence"] = None
        if proj.get("url"):
            proj["url"] = None

    for cert in data.get("certifications", []):
        if cert.get("issuer") and cert["issuer"].get("value"):
            cert["issuer"]["value"] = "[REDACTED_ISSUER]"

    return ParsedResume.model_validate(data)


def redact_skill_profile(profile: SkillProfile) -> SkillProfile:
    """Return a sanitized copy of SkillProfile removing any bias signals from evidence and meta."""
    data = copy.deepcopy(profile.model_dump())

    # Scrub candidate identification from meta
    if "meta" in data:
        data["meta"].pop("name", None)
        data["meta"].pop("email", None)
        data["meta"].pop("phone", None)
        data["meta"].pop("gender", None)
        data["meta"].pop("ethnicity", None)

    # Scrub evidence snippets in skills
    for skill in data.get("skills", []):
        cleaned_ev = [redact_text(ev) for ev in skill.get("evidence", [])]
        skill["evidence"] = cleaned_ev

    return SkillProfile.model_validate(data)
