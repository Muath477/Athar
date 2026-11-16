from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.stories.infrastructure.orm import SourceRow, StoryChunkRow, StoryRow
from sadu.shared.ports.embeddings import EmbeddingPort


class SourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["official", "oral_reviewed"]
    title: str
    url: str | None = None
    narrator_name: str | None = None
    license: str
    reviewed_by: str
    reviewed_at: datetime
    facade_code: str | None = None
    chunks: list[str] = Field(min_length=1)


class SourcesFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sources: list[SourceSpec]


async def import_sources(
    session: AsyncSession,
    *,
    site_id: UUID,
    facade_ids: dict[str, UUID],
    sources_path: Path,
    embedder: EmbeddingPort | None = None,
) -> int:
    raw = sources_path.read_text(encoding="utf-8")
    spec = SourcesFile.model_validate_json(raw)
    await session.execute(delete(SourceRow).where(SourceRow.site_id == site_id))
    await session.execute(delete(StoryRow).where(StoryRow.site_id == site_id))

    chunk_count = 0
    for source in spec.sources:
        row = SourceRow(
            site_id=site_id,
            kind=source.kind,
            title=source.title,
            url=source.url,
            narrator_name=source.narrator_name,
            license=source.license,
            reviewed_by=source.reviewed_by,
            reviewed_at=source.reviewed_at,
        )
        session.add(row)
        await session.flush()
        facade_id = facade_ids[source.facade_code] if source.facade_code else None
        embeddings = await embedder.embed(source.chunks) if embedder else [None] * len(source.chunks)
        for text, embedding in zip(source.chunks, embeddings, strict=True):
            session.add(
                StoryChunkRow(
                    source_id=row.id, site_id=site_id, facade_id=facade_id, text_ar=text, embedding=embedding
                )
            )
        chunk_count += len(source.chunks)
    await session.flush()
    return chunk_count
