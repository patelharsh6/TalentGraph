"""Resume contracts (plan §6.1, Step 2.1).

`ParsedResume` is what the Parsing Agent returns and the API serves. Every extracted value is an
`Extracted[T]` carrying `{value, confidence, evidence, verified}` (feature F2). Plain values are
accepted on input and wrapped, so the Phase 1 ground-truth files (`*.gt.json`) validate as-is.

`ResumeExtraction` is the schema the LLM fills in. It is deliberately compact: long free-text
fields (summary, bullets, project descriptions) come back as references to numbered source lines
instead of copied text, so they cost few output tokens and are grounded by construction. Short
fields come back as text and are checked against the source by the evidence verifier.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from talentgraph.core.schemas.messages import AgentResult, QualityScore

SCHEMA_VERSION = "2.0"

FieldSource = Literal["rules", "llm", "merged"]
SectionLabel = Literal[
    "contact",
    "summary",
    "experience",
    "education",
    "skills",
    "certifications",
    "projects",
    "publications",
    "other",
]
LayoutKind = Literal["single", "multi", "table", "creative"]
FileKind = Literal["pdf", "docx", "txt"]


# -------------------------------------------------------------------------------------------------
# ParsedResume (API output)
# -------------------------------------------------------------------------------------------------


class Grounded(BaseModel):
    """Provenance shared by every extracted value: how sure we are and where it came from."""

    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: str | None = None  # verbatim span of the source text
    verified: bool | None = None  # None: not checked (gold data, or the verifier did not run)


class Extracted[T](Grounded):
    value: T

    @model_validator(mode="before")
    @classmethod
    def _wrap_plain_value(cls, data: Any) -> Any:
        """Accept `"Jane"` as shorthand for `{"value": "Jane"}` (ground truth, fixtures)."""
        if isinstance(data, dict) and "value" in data:
            return data
        if isinstance(data, BaseModel) and hasattr(data, "value"):
            return data
        return {"value": data}


class Location(BaseModel):
    city: str | None = None
    region: str | None = None
    country: str | None = None


class Personal(BaseModel):
    name: Extracted[str] | None = None
    email: Extracted[str] | None = None
    phone: Extracted[str] | None = None
    location: Extracted[Location] | None = None
    links: list[Extracted[str]] = Field(default_factory=list)


class Experience(BaseModel):
    company: Extracted[str] | None = None
    title: Extracted[str] | None = None
    location: Extracted[str] | None = None
    start: Extracted[str] | None = None  # "YYYY-MM", or "YYYY" when the month is not given
    end: Extracted[str] | None = None  # None while is_current
    is_current: bool = False
    duration_months: int | None = None
    responsibilities: list[Extracted[str]] = Field(default_factory=list)
    skills_mentioned: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: Extracted[str] | None = None
    degree: Extracted[str] | None = None
    field: Extracted[str] | None = None
    start: Extracted[str] | None = None
    end: Extracted[str] | None = None
    grade: Extracted[str] | None = None


class Skill(Grounded):
    raw: str
    category_hint: str = "unknown"  # technical | soft | domain | business | unknown


class Certification(BaseModel):
    name: Extracted[str]
    issuer: Extracted[str] | None = None
    date: Extracted[str] | None = None
    credential_id: Extracted[str] | None = None


class Project(BaseModel):
    name: Extracted[str]
    description: Extracted[str] | None = None
    technologies: list[str] = Field(default_factory=list)
    url: Extracted[str] | None = None
    dates: Extracted[str] | None = None


class ResumeMeta(BaseModel):
    # Ground-truth files carry generator metadata here (industry, template, ...); keep it.
    model_config = ConfigDict(extra="allow")

    file_type: FileKind | None = None
    layout: LayoutKind | None = None
    pages: int | None = None
    sections_found: list[SectionLabel] = Field(default_factory=list)
    confidence: float | None = None  # parser quality score, 0..1
    field_sources: dict[str, FieldSource] = Field(default_factory=dict)
    llm_field_count: int = 0  # LLM-extracted values checked by the verifier
    unverified_count: int = 0  # ... of which the evidence could not be found (M7 numerator)


class ParsedResume(BaseModel):
    schema_version: str = SCHEMA_VERSION
    personal: Personal = Field(default_factory=Personal)
    summary: Extracted[str] | None = None
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    publications: list[Extracted[str]] = Field(default_factory=list)
    meta: ResumeMeta = Field(default_factory=ResumeMeta)


# -------------------------------------------------------------------------------------------------
# ResumeExtraction (LLM output; see llm/prompts/parse_resume.md for the field guidance)
# -------------------------------------------------------------------------------------------------


class LLMLocation(BaseModel):
    city: str | None = None
    region: str | None = None
    country: str | None = None
    evidence: str = ""


class LLMExperience(BaseModel):
    title: str = ""
    company: str = ""
    location: str | None = None
    dates_text: str | None = None  # verbatim date range, e.g. "Jun 2018 – Oct. 2022"
    start: str | None = None
    end: str | None = None
    is_current: bool = False
    bullet_lines: list[int] = Field(default_factory=list)
    skills_mentioned: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class LLMEducation(BaseModel):
    institution: str = ""
    degree: str | None = None
    field: str | None = None
    dates_text: str | None = None
    start: str | None = None
    end: str | None = None
    grade: str | None = None
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class LLMSkill(BaseModel):
    name: str
    category: Literal["technical", "soft", "domain", "business", "unknown"] = "unknown"
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class LLMCertification(BaseModel):
    name: str
    issuer: str | None = None
    date_text: str | None = None
    date: str | None = None
    credential_id: str | None = None
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class LLMProject(BaseModel):
    name: str
    description_lines: list[int] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None
    dates: str | None = None
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class ResumeExtraction(BaseModel):
    name: str | None = None
    email: str | None = None  # only when the rule hints lack it
    phone: str | None = None
    links: list[str] = Field(default_factory=list)
    location: LLMLocation | None = None
    summary_lines: list[int] = Field(default_factory=list)
    experience: list[LLMExperience] = Field(default_factory=list)
    education: list[LLMEducation] = Field(default_factory=list)
    skills: list[LLMSkill] = Field(default_factory=list)
    certifications: list[LLMCertification] = Field(default_factory=list)
    projects: list[LLMProject] = Field(default_factory=list)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)  # overall, for name/location

    def is_empty(self) -> bool:
        """True for a default instance, e.g. FakeLLM with no fixture for this input."""
        return not (self.name or self.experience or self.education or self.skills)


# -------------------------------------------------------------------------------------------------
# ParseResult (Parsing Agent output: the resume plus run metadata)
# -------------------------------------------------------------------------------------------------


class ParseResult(BaseModel):
    status: Literal["ok", "partial", "failed"]
    resume: ParsedResume
    quality: QualityScore
    latency_ms: int
    warnings: list[str] = Field(default_factory=list)
    timings_ms: dict[str, int] = Field(default_factory=dict)  # per stage: extract, llm, ...
    sha256: str = ""
    pipeline_version: str = ""
    cached: bool = False

    def to_agent_result(self) -> AgentResult:
        return AgentResult(
            status=self.status,
            data=self.resume.model_dump(mode="json"),
            quality=self.quality,
            latency_ms=self.latency_ms,
            warnings=self.warnings,
        )
