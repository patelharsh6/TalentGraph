"""Unit tests for blind-screening redaction and Exit Criterion 4-D (Step 4.8)."""

import pytest

from talentgraph.agents.matching.blind import (
    redact_resume,
    redact_skill_profile,
    redact_text,
)
from talentgraph.core.schemas.resume import (
    Education,
    Experience,
    Extracted,
    ParsedResume,
    Personal,
)
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile


def test_redact_contact_and_personal() -> None:
    resume = ParsedResume(
        personal=Personal(
            name=Extracted(value="Jane Doe"),
            email=Extracted(value="jane.doe@stanford.edu"),
            phone=Extracted(value="+1 555-123-4567"),
            links=[Extracted(value="https://linkedin.com/in/janedoe")],
        )
    )
    redacted = redact_resume(resume)
    assert redacted.personal.name.value == "[REDACTED_NAME]"
    assert "jane" not in redacted.personal.email.value.lower()
    assert redacted.personal.phone.value == "[REDACTED_PHONE]"
    assert len(redacted.personal.links) == 0


def test_redact_gendered_words_and_pronouns() -> None:
    import re

    text = "She is a skilled software engineer. Her team delivered the project and he commended her."
    scrubbed = redact_text(text)
    assert not re.search(r"\bshe\b", scrubbed, re.IGNORECASE)
    assert not re.search(r"\bher\b", scrubbed, re.IGNORECASE)
    assert not re.search(r"\bhe\b", scrubbed, re.IGNORECASE)
    assert "[REDACTED_PRONOUN]" in scrubbed

    gender_noun_text = "Experienced businesswoman and alumna of the university; Mr. Smith recommended her."
    scrubbed_noun = redact_text(gender_noun_text)
    assert not re.search(r"\bbusinesswoman\b", scrubbed_noun, re.IGNORECASE)
    assert not re.search(r"\balumna\b", scrubbed_noun, re.IGNORECASE)
    assert not re.search(r"\bmr\b", scrubbed_noun, re.IGNORECASE)
    assert "[REDACTED_GENDER]" in scrubbed_noun


def test_redact_age_signals() -> None:
    text = "Candidate is 35 years old, born in 1989, with 12 y/o experience notes."
    scrubbed = redact_text(text)
    assert "35 years old" not in scrubbed
    assert "born in 1989" not in scrubbed
    assert "[REDACTED_AGE]" in scrubbed


def test_redact_institutions() -> None:
    resume = ParsedResume(
        experience=[
            Experience(
                company=Extracted(value="Google LLC"),
                title=Extracted(value="Staff Engineer"),
                responsibilities=[
                    Extracted(value="Led migration at Google for her team."),
                ],
            )
        ],
        education=[
            Education(
                institution=Extracted(value="Stanford University"),
                degree=Extracted(value="B.S. in Computer Science"),
                start=Extracted(value="2012"),
                end=Extracted(value="2016"),
            )
        ],
    )
    redacted = redact_resume(resume)

    # Employer scrubbed
    assert redacted.experience[0].company.value == "[REDACTED_EMPLOYER]"

    # University and graduation years scrubbed
    assert redacted.education[0].institution.value == "[REDACTED_INSTITUTION]"
    assert "2012" not in redacted.education[0].start.value
    assert "2016" not in redacted.education[0].end.value
    assert "[REDACTED_YEAR]" in redacted.education[0].end.value

    # Responsibilities scrubbed of pronouns
    resp = redacted.experience[0].responsibilities[0].value
    assert "her" not in resp.lower()


def test_redact_photo_references() -> None:
    text = "See attached headshot photograph portrait on page 1."
    scrubbed = redact_text(text)
    assert "headshot" not in scrubbed.lower()
    assert "photograph" not in scrubbed.lower()
    assert "portrait" not in scrubbed.lower()
    assert "[REDACTED_PHOTO]" in scrubbed


def test_redact_skill_profile_evidence() -> None:
    profile = SkillProfile(
        skills=[
            NormalizedSkill(
                slug="python",
                name="Python",
                evidence=["She wrote Python pipelines at Stanford."],
            )
        ],
        meta={"gender": "female", "name": "Jane"},
    )
    redacted = redact_skill_profile(profile)
    assert "gender" not in redacted.meta
    assert "name" not in redacted.meta
    assert "She" not in redacted.skills[0].evidence[0]
    assert "[REDACTED_PRONOUN]" in redacted.skills[0].evidence[0]
