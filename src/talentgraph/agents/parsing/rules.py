"""Step 2.8: deterministic extractors (email, phone, URLs, date ranges, skill candidates).

These run before the LLM and never fail. Their output is used three ways: as hints in the LLM
prompt, as the winning value for contact fields in the merge, and as the whole result when the
LLM is unavailable (rules-only degradation, `status="partial"`).
"""

import csv
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from phonenumbers import Leniency, PhoneNumberMatcher

from talentgraph.agents.parsing.layout import BULLET_CHARS
from talentgraph.agents.parsing.sections import Section

EMAIL_RE = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"
)
URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s|,;<>\"'()]+"
    r"|\b(?:[a-z0-9-]+\.)*(?:linkedin\.com|github\.com|gitlab\.com|bitbucket\.org|behance\.net"
    r"|dribbble\.com|medium\.com|kaggle\.com|stackoverflow\.com)/[^\s|,;<>\"'()]+",
    re.IGNORECASE,
)
# North American shapes phonenumbers misses, e.g. "001-626-728-4987x769".
PHONE_RE = re.compile(
    r"(?<![\w/])(?:\+?\d{1,3}[\s.-]?|00\d[\s.-])?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
    r"(?:\s*(?:x|ext\.?|extension)\s*\d{1,6})?(?![\w/])",
    re.IGNORECASE,
)
CITY_REGION_RE = re.compile(r"^([A-Z][A-Za-z.' -]+),\s*([A-Z]{2}|[A-Z][a-z]+(?: [A-Z][a-z]+)*)$")

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}  # fmt: skip
_MONTH = (
    r"(?P<{g}>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
    r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
)
_YEAR = r"(?:19|20)\d{2}"


def _date_pattern(g: str) -> str:
    return (
        rf"(?:{_MONTH.format(g=g + 'n')}\s*,?\s*(?P<{g}y1>{_YEAR})"  # Jun 2018, Sept. 2018
        rf"|(?P<{g}m2>0?[1-9]|1[0-2])\s*[/.]\s*(?P<{g}y2>{_YEAR})"  # 06/2018
        rf"|(?P<{g}y3>{_YEAR})\s*[-/.]\s*(?P<{g}m3>0[1-9]|1[0-2])(?!\d)"  # 2018-06
        rf"|(?P<{g}y4>{_YEAR}))"  # 2018
    )


_PRESENT = r"(?P<present>present|current|currently|now|today|ongoing|to date)"
DATE_RANGE_RE = re.compile(
    rf"(?<!\d){_date_pattern('s')}\s*(?:[-–—~]|to|until|through|till)\s*"
    rf"(?:{_date_pattern('e')}|{_PRESENT})(?!\d)",
    re.IGNORECASE,
)
SINGLE_DATE_RE = re.compile(rf"(?<!\d){_date_pattern('s')}(?!\d)", re.IGNORECASE)
SKILL_SPLIT_RE = re.compile(r"\s*[,;|•·●▪]\s*")
SKILL_LABEL_RE = re.compile(r"^[A-Z][\w &/-]{1,30}:\s+")  # "Languages: Python, Go"


@dataclass(frozen=True)
class Match:
    value: str
    evidence: str  # the exact span in the source


@dataclass(frozen=True)
class DateRange:
    start: str | None  # "YYYY-MM" or "YYYY"
    end: str | None
    is_current: bool
    text: str  # verbatim span


@dataclass
class RuleResult:
    name: Match | None = None
    email: Match | None = None
    phone: Match | None = None
    location: tuple[str, str] | None = None  # (city, region)
    location_text: str | None = None
    links: list[Match] = field(default_factory=list)
    date_ranges: list[DateRange] = field(default_factory=list)
    skills_section: list[str] = field(default_factory=list)  # items listed under a skills header
    skill_candidates: list[str] = field(default_factory=list)  # alias-index hits elsewhere


# -------------------------------------------------------------------------------------------------
# Contact fields
# -------------------------------------------------------------------------------------------------


def find_email(text: str) -> Match | None:
    m = EMAIL_RE.search(text)
    return Match(m.group(0).lower(), m.group(0)) if m else None


def find_phone(text: str) -> Match | None:
    """Earliest phone number; at the same position, the longest (keeps "x123" extensions)."""
    found: list[tuple[int, int]] = []
    for pm in PhoneNumberMatcher(text, "US", leniency=Leniency.POSSIBLE):
        found.append((pm.start, pm.end))
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) >= 10:
            found.append((m.start(), m.end()))
    # POSSIBLE leniency also accepts things like "2018 – 2022-10".
    found = [(s, e) for s, e in found if not DATE_RANGE_RE.search(text[s:e])]
    if not found:
        return None
    start, end = min(found, key=lambda span: (span[0], -(span[1] - span[0])))
    raw = text[start:end].strip()
    return Match(raw, raw)


def find_links(text: str) -> list[Match]:
    out: list[Match] = []
    seen: set[str] = set()
    for m in URL_RE.finditer(text):
        raw = m.group(0).rstrip(".,;:)")
        if "@" in raw:
            continue
        key = re.sub(r"^(https?://)?(www\.)?", "", raw.lower()).rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        url = raw if raw.lower().startswith("http") else "https://" + raw
        out.append(Match(url, raw))
    return out


def find_location(lines: Iterable[str]) -> tuple[tuple[str, str], str] | None:
    """A "City, ST" fragment in the contact block (separated by | or on its own line)."""
    for line in lines:
        for part in re.split(r"\s*[|•·]\s*", line):
            part = part.strip()
            if "@" in part or "://" in part or any(ch.isdigit() for ch in part):
                continue
            m = CITY_REGION_RE.match(part)
            if m and len(part) <= 40:
                return (m.group(1).strip(), m.group(2).strip()), part
    return None


def guess_name(lines: list[str]) -> Match | None:
    """The first short line of letters at the top of the document."""
    for line in lines[:5]:
        text = line.strip()
        words = text.split()
        if (
            2 <= len(words) <= 5
            and not any(ch.isdigit() for ch in text)
            and "@" not in text
            and "|" not in text
            and all(w[0].isalpha() for w in words)
        ):
            value = " ".join(w.capitalize() if w.isupper() else w for w in words)
            return Match(value, text)
    return None


# -------------------------------------------------------------------------------------------------
# Dates
# -------------------------------------------------------------------------------------------------


def _date_value(m: re.Match[str], g: str) -> str | None:
    gd = m.groupdict()
    if gd.get(g + "n") and gd.get(g + "y1"):
        return f"{gd[g + 'y1']}-{_MONTHS[gd[g + 'n'][:3].lower()]:02d}"
    if gd.get(g + "m2") and gd.get(g + "y2"):
        return f"{gd[g + 'y2']}-{int(gd[g + 'm2']):02d}"
    if gd.get(g + "y3") and gd.get(g + "m3"):
        return f"{gd[g + 'y3']}-{gd[g + 'm3']}"
    if gd.get(g + "y4"):
        return str(gd[g + "y4"])
    return None


def find_date_ranges(text: str) -> list[DateRange]:
    out: list[DateRange] = []
    for m in DATE_RANGE_RE.finditer(text):
        present = bool(m.group("present"))
        out.append(
            DateRange(
                start=_date_value(m, "s"),
                end=None if present else _date_value(m, "e"),
                is_current=present,
                text=m.group(0),
            )
        )
    return out


def parse_date_text(text: str | None) -> DateRange | None:
    """Parse a date or date range written any way the corpus (and most resumes) write them."""
    if not text:
        return None
    ranges = find_date_ranges(text)
    if ranges:
        return ranges[0]
    m = SINGLE_DATE_RE.search(text)
    if m:
        return DateRange(start=_date_value(m, "s"), end=None, is_current=False, text=m.group(0))
    return None


def normalize_date(value: str | None) -> str | None:
    """Coerce an LLM-supplied date to "YYYY-MM" / "YYYY"; None if it is not a date."""
    if not value:
        return None
    parsed = parse_date_text(value.strip())
    return parsed.start if parsed else None


def months_between(start: str | None, end: str | None, *, today: tuple[int, int]) -> int | None:
    """Whole months from start to end (or `today`), inclusive of neither bound's day."""
    if not start:
        return None

    def ym(value: str) -> tuple[int, int]:
        year, _, month = value.partition("-")
        return int(year), int(month) if month else 1

    y0, m0 = ym(start)
    y1, m1 = ym(end) if end else today
    months = (y1 - y0) * 12 + (m1 - m0)
    return months if months >= 0 else None


# -------------------------------------------------------------------------------------------------
# Skills
# -------------------------------------------------------------------------------------------------


def split_skill_items(section: Section) -> list[str]:
    """Items of a skills section: comma/pipe/bullet separated, wrapped lines rejoined."""
    pieces: list[str] = []
    for block in section.blocks:
        text = block.text.strip()
        if block.is_bullet:
            text = text.lstrip(BULLET_CHARS + " \t")
            pieces.append(",")
        text = SKILL_LABEL_RE.sub("", text)
        pieces.append(text)
        if block.is_bullet:
            pieces.append(",")  # a bullet is one item; don't run it into the next line
    joined = " ".join(pieces)
    items = []
    seen: set[str] = set()
    for item in SKILL_SPLIT_RE.split(joined):
        item = item.strip(" .-–")
        words = item.split()
        if not item or len(words) > 6 or len(item) > 60:
            continue
        if item.lower() not in seen:
            seen.add(item.lower())
            items.append(item)
    return items


def normalize_alias(text: str) -> str:
    """Same normalization as `aliases.csv:alias_normalized` (scripts/build_taxonomy.py)."""
    return re.sub(r"[\s\-_/.]+", " ", text.lower().strip()).strip()


@lru_cache(maxsize=2)
def load_alias_index(taxonomy_dir: str) -> frozenset[str]:
    """Unambiguous normalized aliases and skill names; empty if the taxonomy is not present."""
    root = Path(taxonomy_dir)
    names: set[str] = set()
    ambiguous: set[str] = set()
    aliases = root / "aliases.csv"
    skills = root / "skills.csv"
    if aliases.is_file():
        with aliases.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                key = row["alias_normalized"]
                (ambiguous if row["ambiguous"] == "true" else names).add(key)
    if skills.is_file():
        with skills.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row["level"] == "3":
                    names.add(normalize_alias(row["name"]))
    # Two-letter names ("go", "r") and context-dependent aliases need the normalizer's context.
    return frozenset(n for n in names - ambiguous if len(n) > 2)


def find_skill_candidates(text: str, index: frozenset[str], *, max_n: int = 5) -> list[str]:
    """Longest-match n-gram lookup of the text against the alias index."""
    if not index:
        return []
    tokens = re.findall(r"[A-Za-z0-9+#][A-Za-z0-9+#.\-/]*", text)
    found: list[str] = []
    seen: set[str] = set()
    i = 0
    while i < len(tokens):
        for n in range(min(max_n, len(tokens) - i), 0, -1):
            phrase = " ".join(tokens[i : i + n])
            key = normalize_alias(phrase)
            if key in index:
                if key not in seen:
                    seen.add(key)
                    found.append(phrase.rstrip("."))
                i += n
                break
        else:
            i += 1
    return found


# -------------------------------------------------------------------------------------------------
# All rules over a sectioned document
# -------------------------------------------------------------------------------------------------


def run_rules(sections: list[Section], full_text: str, alias_index: frozenset[str]) -> RuleResult:
    contact_lines = [b.text for s in sections if s.label == "contact" for b in s.blocks]
    contact_text = "\n".join(contact_lines)
    result = RuleResult()
    result.name = guess_name(contact_lines)
    result.email = find_email(contact_text) or find_email(full_text)
    result.phone = find_phone(contact_text) or find_phone(full_text)
    result.links = find_links(contact_text)
    loc = find_location(contact_lines)
    if loc:
        result.location, result.location_text = loc
    result.date_ranges = find_date_ranges(full_text)

    for section in sections:
        if section.label == "skills":
            result.skills_section.extend(split_skill_items(section))
    listed = {normalize_alias(s) for s in result.skills_section}
    other_text = "\n".join(s.text for s in sections if s.label not in ("skills", "contact"))
    candidates = find_skill_candidates(other_text, alias_index)
    result.skill_candidates = [c for c in candidates if normalize_alias(c) not in listed]
    return result
