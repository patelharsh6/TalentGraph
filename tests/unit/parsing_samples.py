"""The 18 fixture resumes (3 per template, all 3 formats) with their ground truth."""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from talentgraph.agents.parsing.docx import extract_docx
from talentgraph.agents.parsing.layout import LayoutDocument
from talentgraph.agents.parsing.pdf import extract_pdf
from talentgraph.agents.parsing.text import extract_text

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "resumes"
LEXICON = str(Path(__file__).resolve().parents[2] / "config" / "section_lexicon.yaml")


@dataclass(frozen=True)
class Sample:
    path: Path

    @property
    def id(self) -> str:
        return f"{self.path.stem}-{self.template}"

    @property
    def gold(self) -> dict[str, Any]:
        return _gold(self.path)

    @property
    def template(self) -> str:
        return str(self.gold["meta"]["template"])

    def layout(self) -> LayoutDocument:
        data = self.path.read_bytes()
        if self.path.suffix == ".pdf":
            return extract_pdf(data)
        if self.path.suffix == ".docx":
            return extract_docx(data)
        return extract_text(data)


@cache
def _gold(path: Path) -> dict[str, Any]:
    gt = path.with_name(path.stem + ".gt.json")
    return json.loads(gt.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


SAMPLES = [
    Sample(p)
    for p in sorted(FIXTURE_DIR.iterdir())
    if p.suffix in (".pdf", ".docx", ".txt")
]
