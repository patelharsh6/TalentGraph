"""Step 2.3: Block and LayoutDocument models shared by every extractor (plan §6.1 step 2).

A `Block` is one line of text in reading order. Lines (rather than paragraphs) are the unit
because section headers, entry headings and bullets are all single lines, and wrapped PDF
paragraphs are rejoined downstream when needed.
"""

from dataclasses import dataclass, field
from typing import Literal

from talentgraph.core.schemas.resume import FileKind, LayoutKind, SectionLabel

BlockKind = Literal["paragraph", "table", "list"]
BULLET_CHARS = "•●◦▪▫■□‣⁃∙·*-–—➢➤►▸o"


@dataclass
class Block:
    text: str
    page: int = 0
    bbox: tuple[float, float, float, float] | None = None  # x0, y0, x1, y1 (PDF points)
    font_size: float | None = None
    bold: bool = False
    kind: BlockKind = "paragraph"
    header_hint: bool = False  # extractor-level hint: heading style, "--- X ---", underline, ...
    section: SectionLabel | None = None  # set by the section detector

    @property
    def is_bullet(self) -> bool:
        stripped = self.text.lstrip()
        return len(stripped) > 1 and stripped[0] in BULLET_CHARS and stripped[1] in " \t"


@dataclass
class LayoutDocument:
    file_type: FileKind
    blocks: list[Block]
    pages: int = 1
    layout: LayoutKind = "single"
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        """The whole document in reading order, one block per line (the verifier's source)."""
        return "\n".join(b.text for b in self.blocks)

    @property
    def body_font_size(self) -> float | None:
        """Most common font size, weighted by characters; None when the format has no sizes."""
        weights: dict[float, int] = {}
        for b in self.blocks:
            if b.font_size:
                weights[round(b.font_size, 1)] = weights.get(round(b.font_size, 1), 0) + len(b.text)
        return max(weights, key=lambda k: weights[k]) if weights else None


def clean_line(text: str) -> str:
    """Collapse internal whitespace and drop control characters."""
    text = "".join(ch if ch.isprintable() or ch == "\t" else " " for ch in text)
    return " ".join(text.split())
