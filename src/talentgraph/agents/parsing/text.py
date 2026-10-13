"""Step 2.6: plain-text extraction (encoding detection, paragraphs, header hints).

Header hints (plan §6.1 step 2): "--- SKILLS ---" style banners, lines underlined with "===" or
"---", short ALL-CAPS lines, and short lines ending in a colon.
"""

import re

from talentgraph.agents.parsing.layout import Block, LayoutDocument, clean_line
from talentgraph.core.errors import UnsupportedContent

_BANNER = re.compile(r"^\s*[-=#*_~]{2,}\s*(.+?)\s*[-=#*_~]{2,}\s*$")
_RULE = re.compile(r"^\s*([-=_~*#])\1{2,}\s*$")
MAX_HEADER_WORDS = 5


def decode_text(data: bytes) -> str:
    for bom, encoding in (
        (b"\xef\xbb\xbf", "utf-8-sig"),
        (b"\xff\xfe", "utf-16"),
        (b"\xfe\xff", "utf-16"),
    ):
        if data.startswith(bom):
            return data.decode(encoding)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1252")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def extract_text(data: bytes) -> LayoutDocument:
    raw_lines = decode_text(data).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[Block] = []
    for raw in raw_lines:
        if _RULE.match(raw):
            if blocks:  # "Name\n====" underlines the line above
                blocks[-1].header_hint = True
            continue
        banner = _BANNER.match(raw)
        text = clean_line(banner.group(1) if banner else raw)
        if not text:
            continue
        block = Block(text=text, header_hint=bool(banner) or _looks_like_header(text))
        if block.is_bullet:
            block.kind = "list"
        blocks.append(block)
    if not blocks:
        raise UnsupportedContent("The text file is empty.")
    return LayoutDocument(file_type="txt", blocks=blocks)


def _looks_like_header(text: str) -> bool:
    words = text.rstrip(":").split()
    if not words or len(words) > MAX_HEADER_WORDS or not text[0].isalpha() or "," in text:
        return False  # wrapped list items like "(EHR)" or "SQL, AWS" are not headers
    letters = [c for c in text if c.isalpha()]
    all_caps = len(letters) >= 4 and all(c.isupper() for c in letters)
    return all_caps or (text.endswith(":") and len(words) <= 4)
