"""Step 2.9: one structured Gemini call per resume, into ResumeExtraction (evidence per field).

The prompt (`llm/prompts/parse_resume.md`) is static; the per-resume input goes in the user
message: the rule hints, then the section-labelled text with every content line numbered. Long
text comes back as line numbers, which `NumberedLines` resolves.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from talentgraph.agents.parsing.layout import BULLET_CHARS, Block
from talentgraph.agents.parsing.rules import RuleResult
from talentgraph.agents.parsing.sections import Section
from talentgraph.core.schemas.resume import ResumeExtraction
from talentgraph.llm.client import LLMClient

PROMPT_PATH = Path(__file__).resolve().parents[2] / "llm" / "prompts" / "parse_resume.md"


@lru_cache(maxsize=1)
def system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@dataclass
class NumberedLines:
    """Content lines by the number shown to the LLM (1-based)."""

    blocks: dict[int, Block]

    def valid(self, numbers: list[int]) -> tuple[list[int], int]:
        """The known line numbers (sorted, de-duplicated) and how many were unknown."""
        known = sorted({n for n in numbers if n in self.blocks})
        return known, len({n for n in numbers if n not in self.blocks})

    def paragraph(self, numbers: list[int]) -> str:
        return " ".join(_strip_bullet(self.blocks[n].text) for n in numbers)

    def bullets(self, numbers: list[int]) -> list[str]:
        """Group lines into bullets: a bullet marker or a gap in numbering starts a new one."""
        out: list[list[str]] = []
        previous: int | None = None
        for n in numbers:
            block = self.blocks[n]
            if not out or block.is_bullet or previous is None or n != previous + 1:
                out.append([])
            out[-1].append(_strip_bullet(block.text))
            previous = n
        return [" ".join(parts) for parts in out if any(parts)]


def _strip_bullet(text: str) -> str:
    stripped = text.lstrip()
    if len(stripped) > 1 and stripped[0] in BULLET_CHARS and stripped[1] in " \t":
        return stripped[2:].strip()
    return stripped


def build_user_message(sections: list[Section], rules: RuleResult) -> tuple[str, NumberedLines]:
    hints = ["<rule_hints>"]
    hints.append(f"email: {rules.email.value if rules.email else 'not found'}")
    hints.append(f"phone: {rules.phone.value if rules.phone else 'not found'}")
    links = ", ".join(m.value for m in rules.links) or "not found"
    hints.append(f"links: {links}")
    hints.append(f"location: {rules.location_text or 'not found'}")
    hints.append("</rule_hints>")

    lines = ["<resume>"]
    numbered: dict[int, Block] = {}
    for section in sections:
        header = f' (header: "{section.header}")' if section.header else ""
        lines.append(f"## section: {section.label}{header}")
        for block in section.blocks:
            n = len(numbered) + 1
            numbered[n] = block
            lines.append(f"{n}| {block.text}")
    lines.append("</resume>")
    return "\n".join(hints + [""] + lines), NumberedLines(numbered)


async def llm_extract(
    llm: LLMClient, sections: list[Section], rules: RuleResult
) -> tuple[ResumeExtraction, NumberedLines]:
    user, numbered = build_user_message(sections, rules)
    extraction = await llm.extract(ResumeExtraction, system_prompt(), user)
    return extraction, numbered
