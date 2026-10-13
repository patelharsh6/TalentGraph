"""Step 2.7: section detection (header lexicon plus typography and position signals).

A line starts a section when:

- its normalized text is a lexicon variant (`config/section_lexicon.yaml`), whatever its style;
- or it *looks* like a header (bold, larger than body text, a style or banner hint, ALL CAPS) and
  fuzzily matches a variant or contains a section keyword ("Relevant Work Experience");
- or it looks strongly like a header (larger font, or an extractor hint) after the first real
  section, in which case it opens an `other` section.

Everything before the first header is the `contact` block (name and contact line at the top).
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from rapidfuzz import fuzz, process

from talentgraph.agents.parsing.layout import BULLET_CHARS, Block, LayoutDocument
from talentgraph.core.schemas.resume import SectionLabel

FUZZY_MIN = 88
MAX_HEADER_WORDS = 6
LARGER_FONT_PT = 1.5  # header if at least this much larger than body text
# A header-like line containing one of these words names that section.
KEYWORDS: dict[str, SectionLabel] = {
    "experience": "experience",
    "employment": "experience",
    "education": "education",
    "skills": "skills",
    "competencies": "skills",
    "certifications": "certifications",
    "certificates": "certifications",
    "projects": "projects",
    "publications": "publications",
    "summary": "summary",
    "objective": "summary",
}


@dataclass
class Section:
    label: SectionLabel
    header: str | None  # the header line as written; None for the implicit top block
    blocks: list[Block] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks)


@lru_cache(maxsize=4)
def load_lexicon(path: str) -> dict[str, SectionLabel]:
    """Map each normalized header variant to its label."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {normalize_header(v): label for label, variants in raw.items() for v in variants}


def normalize_header(text: str) -> str:
    text = text.strip().lstrip(BULLET_CHARS + " \t#>|").strip()
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def detect_sections(doc: LayoutDocument, lexicon: dict[str, SectionLabel]) -> list[Section]:
    body_size = doc.body_font_size
    sections: list[Section] = [Section(label="contact", header=None)]
    seen_lexicon_header = False
    blocks = doc.blocks
    i = 0
    while i < len(blocks):
        block = blocks[i]
        header_lines = 1
        label = _wrapped_header_label(blocks, i, lexicon)
        if label is not None:
            header_lines = 2
        else:
            label = _header_label(block, lexicon, body_size, allow_other=seen_lexicon_header)
        if label is not None:
            seen_lexicon_header = seen_lexicon_header or label != "other"
            header = " ".join(b.text for b in blocks[i : i + header_lines])
            for b in blocks[i : i + header_lines]:
                b.section = label
            sections.append(Section(label=label, header=header))
            i += header_lines
            continue
        block.section = sections[-1].label
        sections[-1].blocks.append(block)
        i += 1
    if not sections[0].blocks:
        sections.pop(0)
    return sections


def _wrapped_header_label(
    blocks: list[Block], i: int, lexicon: dict[str, SectionLabel]
) -> SectionLabel | None:
    """A header wrapped over two lines in a narrow column ("Certifications &" / "Licenses")."""
    if i + 1 >= len(blocks):
        return None
    first, second = blocks[i], blocks[i + 1]
    styled = first.bold or first.header_hint
    same_style = first.font_size == second.font_size and first.bold == second.bold
    if not (styled and same_style) or normalize_header(first.text) in lexicon:
        return None
    joined = normalize_header(f"{first.text} {second.text}")
    if len(joined.split()) <= MAX_HEADER_WORDS and joined in lexicon:
        return lexicon[joined]
    return None


def _header_label(
    block: Block,
    lexicon: dict[str, SectionLabel],
    body_size: float | None,
    *,
    allow_other: bool,
) -> SectionLabel | None:
    norm = normalize_header(block.text)
    words = norm.split()
    if not words or len(words) > MAX_HEADER_WORDS or block.text.rstrip().endswith((".", ",")):
        return None
    if norm in lexicon:
        return lexicon[norm]

    if any(sep in block.text for sep in ("|", " — ", "@", "://", ",")):
        return None  # entry headings ("Title | Company") and contact lines, not headers
    larger = bool(body_size and block.font_size and block.font_size >= body_size + LARGER_FONT_PT)
    letters = [c for c in block.text if c.isalpha()]
    all_caps = len(letters) >= 4 and all(c.isupper() for c in letters)
    # Bold alone is weak: entry headings and project names are bold too.
    strong = block.header_hint or larger or all_caps
    if not (strong or block.bold):
        return None

    match = process.extractOne(norm, lexicon.keys(), scorer=fuzz.ratio)
    if match is not None and match[1] >= FUZZY_MIN:
        return lexicon[match[0]]
    if strong and len(words) <= 4:
        for word in words:
            if word in KEYWORDS:
                return KEYWORDS[word]
    if allow_other and (block.header_hint or larger):
        return "other"
    return None
