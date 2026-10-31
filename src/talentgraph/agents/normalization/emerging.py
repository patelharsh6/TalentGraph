"""Step 3.7: Unrecognized-skill store (plan §6.2).

Upserts unrecognized skill mentions into `emerging_skills` with:
- `normalized_text`: unique cleaned string
- `occurrences`: incremented count of how many candidates/jobs mentioned this term
- `example_contexts`: up to 5 example sentences/contexts where the term appeared
- Review-ready flagging when occurrences >= review_ready_occurrences (default 3)

Operates with SQLAlchemy AsyncSession when DB is available, or an in-memory store for
offline tests and standalone processing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from talentgraph.agents.normalization.cascade import NormalizationConfig
from talentgraph.core.schemas.skills import EmergingSkillMention


@dataclass
class EmergingSkillRecord:
    normalized_text: str
    occurrences: int = 1
    example_contexts: list[str] = field(default_factory=list)

    @property
    def is_review_ready(self) -> bool:
        return self.occurrences >= 3


class EmergingSkillStore:
    """Store for tracking and accumulating unrecognized skills."""

    def __init__(self, config: NormalizationConfig | None = None) -> None:
        self.config = config or NormalizationConfig.load()
        self._in_memory: dict[str, EmergingSkillRecord] = {}

    def record_mention_sync(self, mention: EmergingSkillMention) -> EmergingSkillRecord:
        """In-memory recording of an unrecognized skill mention."""
        norm = mention.normalized.strip().lower()
        if not norm:
            return EmergingSkillRecord(normalized_text=norm, occurrences=0)

        record = self._in_memory.get(norm)
        if record is None:
            ctxs = [mention.context] if mention.context else []
            record = EmergingSkillRecord(
                normalized_text=norm,
                occurrences=1,
                example_contexts=ctxs,
            )
            self._in_memory[norm] = record
        else:
            record.occurrences += 1
            if (
                mention.context
                and mention.context not in record.example_contexts
                and len(record.example_contexts) < self.config.emerging_max_contexts
            ):
                record.example_contexts.append(mention.context)

        return record

    def record_batch_sync(self, mentions: list[EmergingSkillMention]) -> list[EmergingSkillRecord]:
        """Record multiple unrecognized skill mentions in-memory."""
        return [self.record_mention_sync(m) for m in mentions]

    async def record_mention_db(
        self, mention: EmergingSkillMention, session: AsyncSession
    ) -> EmergingSkillRecord:
        """Record an unrecognized skill into the PostgreSQL database."""
        from talentgraph.db.models import EmergingSkill

        norm = mention.normalized.strip().lower()
        if not norm:
            return EmergingSkillRecord(normalized_text=norm, occurrences=0)

        stmt = select(EmergingSkill).where(EmergingSkill.normalized_text == norm)
        res = await session.execute(stmt)
        row = res.scalar_one_or_none()

        if row is None:
            ctxs = [mention.context] if mention.context else []
            row = EmergingSkill(
                normalized_text=norm,
                occurrences=1,
                example_contexts=ctxs,
            )
            session.add(row)
            await session.flush()
        else:
            row.occurrences += 1
            ctxs = list(row.example_contexts or [])
            if (
                mention.context
                and mention.context not in ctxs
                and len(ctxs) < self.config.emerging_max_contexts
            ):
                ctxs.append(mention.context)
                row.example_contexts = ctxs
            await session.flush()

        return EmergingSkillRecord(
            normalized_text=row.normalized_text,
            occurrences=row.occurrences,
            example_contexts=list(row.example_contexts or []),
        )

    def get(self, normalized_text: str) -> EmergingSkillRecord | None:
        """Get an emerging skill record by normalized text."""
        return self._in_memory.get(normalized_text.strip().lower())

    def list_review_ready(self) -> list[EmergingSkillRecord]:
        """List emerging skills with >= review_ready_occurrences."""
        threshold = self.config.emerging_review_ready
        return [r for r in self._in_memory.values() if r.occurrences >= threshold]

    def all_records(self) -> list[EmergingSkillRecord]:
        return list(self._in_memory.values())
