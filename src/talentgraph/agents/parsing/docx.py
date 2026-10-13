"""Step 2.5: DOCX extraction (paragraphs, tables, text boxes, heading styles).

The document XML is walked directly, in body order, so that tables, content controls (`w:sdt`)
and text boxes (`w:txbxContent`) all land where they appear. Line breaks inside a paragraph
(`w:br`) start a new block, which keeps "Title | Company" and its date line apart.
"""

import io
from typing import Any

import docx
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from talentgraph.agents.parsing.layout import Block, LayoutDocument, clean_line
from talentgraph.core.errors import UnsupportedContent
from talentgraph.core.schemas.resume import LayoutKind

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def extract_docx(data: bytes) -> LayoutDocument:
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:  # python-docx raises KeyError/ValueError/lxml errors for bad files
        raise UnsupportedContent("The DOCX file could not be read; it may be corrupt.") from exc

    walker = _Walker(document)
    for section in document.sections[:1]:  # contact details sometimes live in the page header
        if not section.header.is_linked_to_previous:
            walker.walk(section.header._element, in_table=False)
    walker.walk(document.element.body, in_table=False)
    if not any(b.text for b in walker.blocks):
        raise UnsupportedContent("The DOCX file contains no text.")
    return LayoutDocument(file_type="docx", blocks=walker.blocks, layout=walker.layout())


class _Walker:
    def __init__(self, document: Any) -> None:
        self._document = document
        self.blocks: list[Block] = []
        self._grid_tables = 0  # ≥ 2 rows and ≥ 2 columns
        self._column_tables = 0  # 1 row, ≥ 2 columns: a page-layout table

    def layout(self) -> LayoutKind:
        if self._grid_tables:
            return "table"
        if self._column_tables:
            return "multi"
        return "single"

    def walk(self, container: Any, *, in_table: bool) -> None:
        for el in container.iterchildren():
            if el.tag == W + "p":
                self._paragraph(el, in_table=in_table)
            elif el.tag == W + "tbl":
                self._table(el)
            elif el.tag == W + "sdt":
                content = el.find(W + "sdtContent")
                if content is not None:
                    self.walk(content, in_table=in_table)

    def _table(self, tbl: Any) -> None:
        rows = tbl.findall(W + "tr")
        max_cols = max((len(r.findall(W + "tc")) for r in rows), default=0)
        if max_cols >= 2:
            if len(rows) >= 2:
                self._grid_tables += 1
            else:
                self._column_tables += 1
        for row in rows:
            for cell in row.findall(W + "tc"):
                self.walk(cell, in_table=True)

    def _paragraph(self, p_el: Any, *, in_table: bool) -> None:
        para = Paragraph(p_el, self._document)
        style = para.style
        style_name = (style.name or "").lower() if style is not None else ""
        heading = style_name.startswith("heading") or style_name == "title"
        style_bold = bool(style.font.bold) if style is not None else False
        style_size = style.font.size.pt if style is not None and style.font.size else None

        lines: list[list[tuple[str, bool, float | None]]] = [[]]
        for r_el in p_el.iter(W + "r"):
            if _inside_textbox(r_el, p_el):
                continue
            run = Run(r_el, para)
            bold = run.bold if run.bold is not None else style_bold
            size = run.font.size.pt if run.font.size else style_size
            for child in r_el.iterchildren():
                if child.tag == W + "t":
                    lines[-1].append((child.text or "", bold, size))
                elif child.tag == W + "tab":
                    lines[-1].append((" ", bold, size))
                elif child.tag in (W + "br", W + "cr"):
                    lines.append([])

        for segments in lines:
            text = clean_line("".join(t for t, _, _ in segments))
            if not text:
                continue
            visible = [(b, s) for t, b, s in segments if t.strip()]
            sizes = [s for _, s in visible if s]
            block = Block(
                text=text,
                font_size=max(sizes) if sizes else None,
                bold=all(b for b, _ in visible),
                kind="table" if in_table else "paragraph",
                header_hint=heading,
            )
            if block.kind == "paragraph" and block.is_bullet:
                block.kind = "list"
            self.blocks.append(block)

        for txbx in p_el.iter(W + "txbxContent"):
            if any(a.tag == MC_FALLBACK for a in txbx.iterancestors()):
                continue  # the same box is repeated in the VML fallback
            self.walk(txbx, in_table=in_table)


def _inside_textbox(r_el: Any, p_el: Any) -> bool:
    for ancestor in r_el.iterancestors():
        if ancestor is p_el:
            return False
        if ancestor.tag == W + "txbxContent":
            return True
    return False
