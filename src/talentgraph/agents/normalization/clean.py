"""Step 3.2: Raw skill cleaning (plan §6.2).

Handles:
- case and whitespace normalization
- version stripping (e.g. 'Python 3.11' -> 'Python', 'ReactJS 18' -> 'ReactJS', 'C++20' -> 'C++')
- multi-skill compound splitting (e.g. 'Python/Django' -> ['Python', 'Django']) while preserving
  known composite aliases (e.g. 'HL7 / FHIR', 'CI/CD', 'UI/UX')
- punctuation unification and bullet stripping
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from talentgraph.db.repositories.taxonomy import TaxonomyRepository

_LEADING_BULLETS_RE = re.compile(r"^[•●◦▪▫■□‣⁃∙·*\-–—➢➤►▸o\s]+")
_TRAILING_PUNCT_RE = re.compile(r"[\s,;:.–—\-]+$")


def strip_version(text: str) -> str:
    """Strip version numbers, release tags, and parenthetical metadata from a skill string."""
    # Remove parenthesized content like '(CUDA 12)', '(Apollo 4)', '(2024)'
    s = re.sub(r"\s*\([^)]*\)", "", text)
    # Remove version prefixes like 'v3', 'v3.2', 'v2.0'
    s = re.sub(r"\bv\d+(?:\.\d+)*\b", "", s, flags=re.IGNORECASE)
    # Remove year patterns like '2019', '2023.3'
    s = re.sub(r"\b(?:19|20)\d{2}(?:\.\d+)?\b", "", s)
    # Remove standalone edition keywords and versions
    s = re.sub(
        r"\b\d+(?:\.\d+)*(?:\.[xX])?(?:\s+(?:LTS|App Router|Desktop|Cloud|Lightning|Enterprise))?\b",
        "",
        s,
        flags=re.IGNORECASE,
    )
    # Handle C++20, Python3 (digits attached directly to letters, except html5/css3/sha256/mp3)
    s = re.sub(r"(?<=[a-zA-Z\+])(?<!html)(?<!css)(?<!sha)(?<!mp)\d+\b", "", s, flags=re.IGNORECASE)
    # Remove standalone 'SE', 'v', 'version'
    s = re.sub(r"\b(?:SE|v|version)\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else text


def split_multi_skills(text: str, repo: TaxonomyRepository | None = None) -> list[str]:
    """Split compound skill strings (e.g. 'Python/Django', 'Docker & K8s') into parts."""
    # If the whole text resolves as a known alias (e.g. 'HL7 / FHIR', 'CI/CD'), keep it whole
    if repo is not None and repo.resolve_alias(text) is not None:
        return [text]

    # Delimiters: &, +, comma, or slash
    # Be careful not to split C++ / G++ on '+'
    s = re.sub(r"(?<=[a-zA-Z0-9])\s*\+\s*(?=[a-zA-Z0-9])", " § ", text)
    s = re.sub(r"\s*&\s*", " § ", s)
    s = re.sub(r"\s*,\s*", " § ", s)
    s = re.sub(r"(?<!\+)\s*/\s*(?!\+)", " § ", s)

    parts = [p.strip() for p in s.split(" § ") if p.strip()]
    return parts if parts else [text]


def clean_raw_skill(raw: str, repo: TaxonomyRepository | None = None) -> list[str]:
    """Clean a raw skill string and split it into individual skill candidates."""
    text = raw.strip()
    text = _LEADING_BULLETS_RE.sub("", text)
    text = _TRAILING_PUNCT_RE.sub("", text)
    if not text:
        return []

    # If the string resolves as a single known alias right away, return it directly
    if repo is not None and repo.resolve_alias(text) is not None:
        return [text]

    # Split multi-skill strings
    parts = split_multi_skills(text, repo=repo)

    cleaned_candidates: list[str] = []
    for part in parts:
        part_clean = part.strip()
        part_clean = _LEADING_BULLETS_RE.sub("", part_clean)
        part_clean = _TRAILING_PUNCT_RE.sub("", part_clean)
        if not part_clean:
            continue

        # Strip version details if the part doesn't already resolve as a known alias
        candidate = strip_version(part_clean)
        if candidate:
            cleaned_candidates.append(candidate)

    return cleaned_candidates if cleaned_candidates else [text]
