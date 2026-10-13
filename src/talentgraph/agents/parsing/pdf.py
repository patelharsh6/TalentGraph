"""Step 2.4: PDF extraction (PyMuPDF lines, column ordering, tables, scanned-page check).

Reading order is a recursive XY-cut over text lines (plan §6.1 step 2):

1. If a vertical gutter (an x-range no line crosses) splits the region, read each column left to
   right, recursing into each.
2. Otherwise peel off the top band (the lines above the first horizontal gap) and repeat on the
   rest. A full-width line therefore separates the bands above and below it.

Tables from `find_tables()` are atomic units in that cut and are read row by row, cell by cell,
so a two-column "title | body" table is not mistaken for two text columns.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field

import pymupdf

from talentgraph.agents.parsing.layout import Block, LayoutDocument, clean_line
from talentgraph.core.errors import FileTooLarge, UnsupportedContent
from talentgraph.core.schemas.resume import LayoutKind

SYMBOL_FONTS = ("zapfdingbats", "symbol", "wingdings", "webdings", "fontawesome", "dingbat")
MIN_GUTTER_PT = 8.0  # narrowest whitespace gap treated as a column gutter
MIN_COLUMN_LINES = 3  # both sides of a cut need this many lines for the page to count as multi
LOW_TEXT_RATIO = 0.004  # text-line area / page area below this: the page is (probably) scanned
BOLD_FLAG = 1 << 4

Rect = tuple[float, float, float, float]


@dataclass
class _Line:
    bbox: Rect
    text: str
    size: float
    bold: bool
    kind: str = "paragraph"


@dataclass
class _Unit:
    """A line, or a whole table (its lines already in row order)."""

    bbox: Rect
    lines: list[_Line] = field(default_factory=list)


def extract_pdf(data: bytes, *, max_pages: int = 20) -> LayoutDocument:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises several unrelated types for corrupt files
        raise UnsupportedContent("The PDF could not be opened; it may be corrupt.") from exc
    with doc:
        if doc.needs_pass:
            raise UnsupportedContent("The PDF is password-protected.")
        if doc.page_count > max_pages:
            raise FileTooLarge(f"The PDF has {doc.page_count} pages; the limit is {max_pages}.")

        blocks: list[Block] = []
        warnings: list[str] = []
        kinds: set[LayoutKind] = set()
        low_text_pages: list[int] = []
        for page in doc:
            lines = _page_lines(page)
            if _text_ratio(lines, page.rect) < LOW_TEXT_RATIO:
                low_text_pages.append(page.number or 0)
            units, has_table = _table_units(page, lines)
            ordered, multi = _xy_cut(units)
            if has_table:
                kinds.add("table")
            if multi:
                kinds.add("multi")
            if page.number == 0 and _has_banner(page):
                kinds.add("creative")
            blocks.extend(_to_block(line, page.number or 0) for u in ordered for line in u.lines)

        if len(low_text_pages) == doc.page_count:
            raise UnsupportedContent(
                "The PDF has no usable text layer (it looks scanned). OCR is not supported; "
                "upload a text-based PDF or a DOCX."
            )
        if low_text_pages:
            pages = ", ".join(str(p + 1) for p in low_text_pages)
            warnings.append(f"Pages {pages} have almost no text and may be scanned images.")
        return LayoutDocument(
            file_type="pdf",
            blocks=blocks,
            pages=doc.page_count,
            layout=_pick_layout(kinds),
            warnings=warnings,
        )


def _pick_layout(kinds: set[LayoutKind]) -> LayoutKind:
    for kind in ("table", "multi", "creative"):
        if kind in kinds:
            return kind
    return "single"


def _page_lines(page: pymupdf.Page) -> list[_Line]:
    out: list[_Line] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            # Icon glyphs (e.g. "▸" rendered in ZapfDingbats) come out as stray letters.
            spans = [s for s in spans if not _is_symbol_span(s)]
            if not spans:
                continue
            text = clean_line("".join(s["text"] for s in spans))
            if not text:
                continue
            out.append(
                _Line(
                    bbox=tuple(line["bbox"]),
                    text=text,
                    size=max(float(s["size"]) for s in spans),
                    bold=all(_is_bold(s) for s in spans),
                )
            )
    return out


def _is_symbol_span(span: dict[str, object]) -> bool:
    font = str(span.get("font", "")).lower()
    return any(f in font for f in SYMBOL_FONTS) and len(str(span["text"]).strip()) <= 2


def _is_bold(span: dict[str, object]) -> bool:
    font = str(span.get("font", "")).lower()
    flags = int(span.get("flags", 0))  # type: ignore[call-overload]
    return bool(flags & BOLD_FLAG) or any(w in font for w in ("bold", "black", "heavy"))


def _text_ratio(lines: list[_Line], rect: pymupdf.Rect) -> float:
    area = sum((b[2] - b[0]) * (b[3] - b[1]) for b in (ln.bbox for ln in lines))
    page_area = rect.width * rect.height
    return area / page_area if page_area else 0.0


def _has_banner(page: pymupdf.Page) -> bool:
    """A filled rectangle across most of the page width near the top (a "creative" header)."""
    width, height = page.rect.width, page.rect.height
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if drawing.get("fill") is None or rect is None:
            continue
        if rect.width > 0.6 * width and rect.y0 < 0.25 * height and rect.height > 20:
            return True
    return False


# -------------------------------------------------------------------------------------------------
# Tables
# -------------------------------------------------------------------------------------------------


def _center(b: Rect) -> tuple[float, float]:
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def _inside(point: tuple[float, float], rect: Iterable[float]) -> bool:
    x0, y0, x1, y1 = rect
    return x0 <= point[0] <= x1 and y0 <= point[1] <= y1


def _table_units(page: pymupdf.Page, lines: list[_Line]) -> tuple[list[_Unit], bool]:
    """Turn real tables (≥ 2 rows and ≥ 2 columns) into atomic units read row by row."""
    try:
        tables = [t for t in page.find_tables().tables if len(t.rows) >= 2 and t.col_count >= 2]
    except Exception:  # find_tables is heuristic; a failure must not fail the parse
        tables = []
    remaining = list(lines)
    units: list[_Unit] = []
    for table in tables:
        inside = [ln for ln in remaining if _inside(_center(ln.bbox), table.bbox)]
        if not inside:
            continue
        remaining = [ln for ln in remaining if ln not in inside]
        ordered: list[_Line] = []
        for row in table.rows:
            for cell in row.cells:
                if cell is None:
                    continue
                in_cell = [ln for ln in inside if _inside(_center(ln.bbox), cell)]
                ordered.extend(sorted(in_cell, key=lambda ln: (ln.bbox[1], ln.bbox[0])))
                inside = [ln for ln in inside if ln not in in_cell]
        ordered.extend(sorted(inside, key=lambda ln: (ln.bbox[1], ln.bbox[0])))
        for ln in ordered:
            ln.kind = "table"
        units.append(_Unit(bbox=tuple(table.bbox), lines=ordered))
    units.extend(_Unit(bbox=ln.bbox, lines=[ln]) for ln in remaining)
    return units, bool(tables)


# -------------------------------------------------------------------------------------------------
# Reading order (recursive XY-cut)
# -------------------------------------------------------------------------------------------------


def _xy_cut(units: list[_Unit]) -> tuple[list[_Unit], bool]:
    """Return units in reading order and whether a real multi-column split was found."""
    out: list[_Unit] = []
    multi = False
    remaining = units
    while remaining:
        columns = _split_columns(remaining)
        if len(columns) > 1:
            if sum(1 for c in columns if _line_count(c) >= MIN_COLUMN_LINES) >= 2:
                multi = True
            for column in columns:
                ordered, column_multi = _xy_cut(column)
                out.extend(ordered)
                multi = multi or column_multi
            return out, multi
        top, rest = _split_top_band(remaining)
        if len(top) > 1 and len(_split_columns(top)) > 1:
            ordered, band_multi = _xy_cut(top)
            multi = multi or band_multi
        else:
            ordered = sorted(top, key=lambda u: (u.bbox[1], u.bbox[0]))
        out.extend(ordered)
        remaining = rest
    return out, multi


def _line_count(units: list[_Unit]) -> int:
    return sum(len(u.lines) for u in units)


def _split_columns(units: list[_Unit]) -> list[list[_Unit]]:
    """Split on vertical gutters: x-ranges of at least MIN_GUTTER_PT that no unit crosses."""
    ordered = sorted(units, key=lambda u: u.bbox[0])
    columns: list[list[_Unit]] = [[ordered[0]]]
    right_edge = ordered[0].bbox[2]
    for unit in ordered[1:]:
        if unit.bbox[0] - right_edge >= MIN_GUTTER_PT:
            columns.append([unit])
        else:
            columns[-1].append(unit)
        right_edge = max(right_edge, unit.bbox[2])
    return columns


def _split_top_band(units: list[_Unit]) -> tuple[list[_Unit], list[_Unit]]:
    """Units above the first horizontal gap, and the rest (empty when there is no gap)."""
    ordered = sorted(units, key=lambda u: u.bbox[1])
    bottom = ordered[0].bbox[3]
    for i, unit in enumerate(ordered[1:], start=1):
        if unit.bbox[1] >= bottom - 1.0:  # 1 pt tolerance for touching line boxes
            return ordered[:i], ordered[i:]
        bottom = max(bottom, unit.bbox[3])
    return ordered, []


def _to_block(line: _Line, page: int) -> Block:
    block = Block(
        text=line.text,
        page=page,
        bbox=line.bbox,
        font_size=round(line.size, 1),
        bold=line.bold,
        kind="table" if line.kind == "table" else "paragraph",
    )
    if block.kind == "paragraph" and block.is_bullet:
        block.kind = "list"
    return block
