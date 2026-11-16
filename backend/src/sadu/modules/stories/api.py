import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.stories.application.drafting import DraftClaim, draft_claims
from sadu.modules.stories.infrastructure.orm import SourceRow, StoryChunkRow, StoryRow
from sadu.modules.stories.infrastructure.source_import import import_sources
from sadu.shared.errors import NotFound
from sadu.shared.ports.embeddings import EmbeddingPort
from sadu.shared.ports.speech import TextToSpeechPort
from sadu.shared.storage import ObjectStore, new_object_key

__all__ = ["DraftClaim", "draft_claims", "import_sources"]

GENERATOR_VERSION = "guide-v1"
DEFAULT_VOICE = "ar-SA-HamedNeural"
MAX_CHUNKS = 8


@dataclass(frozen=True)
class ChunkView:
    chunk_id: str
    source_id: str
    source_kind: str
    text: str


@dataclass(frozen=True)
class SourceRef:
    title: str
    url: str | None
    narrator_name: str | None


@dataclass(frozen=True)
class StoryClaim:
    claim_id: str
    text: str
    label: str
    source: SourceRef | None


@dataclass(frozen=True)
class StoryView:
    id: UUID
    site_id: UUID
    facade_id: UUID | None
    lang: str
    claims: list[StoryClaim]
    audio_key: str | None
    cached: bool

    @property
    def text(self) -> str:
        return " ".join(claim.text for claim in self.claims)


async def retrieve_chunks(
    session: AsyncSession,
    site_id: UUID,
    facade_id: UUID | None,
    *,
    query_embedding: list[float] | None = None,
    k: int = MAX_CHUNKS,
) -> list[ChunkView]:
    statement = (
        select(StoryChunkRow, SourceRow.kind)
        .join(SourceRow, SourceRow.id == StoryChunkRow.source_id)
        .where(
            StoryChunkRow.site_id == site_id,
            or_(StoryChunkRow.facade_id.is_(None), StoryChunkRow.facade_id == facade_id),
        )
    )
    if query_embedding is not None:
        statement = statement.order_by(StoryChunkRow.embedding.cosine_distance(query_embedding))
    else:
        statement = statement.order_by(StoryChunkRow.facade_id.is_(None), StoryChunkRow.id)
    rows = await session.execute(statement.limit(k))
    return [ChunkView(str(chunk.id), str(chunk.source_id), kind, chunk.text_ar) for chunk, kind in rows.all()]


async def embed_query(embedder: EmbeddingPort | None, text: str) -> list[float] | None:
    if embedder is None:
        return None
    return (await embedder.embed([text]))[0]


async def cached_story(
    session: AsyncSession, site_id: UUID, facade_id: UUID | None, lang: str = "ar"
) -> StoryView | None:
    version = await sources_version(session, site_id)
    row = await session.scalar(
        select(StoryRow)
        .where(
            StoryRow.site_id == site_id,
            StoryRow.facade_id.is_(None) if facade_id is None else StoryRow.facade_id == facade_id,
            StoryRow.lang == lang,
            StoryRow.sources_version == version,
        )
        .order_by(StoryRow.created_at.desc())
        .limit(1)
    )
    return _view(row, cached=True) if row else None


async def get_story(session: AsyncSession, story_id: UUID) -> StoryView:
    row = await session.get(StoryRow, story_id)
    if row is None:
        raise NotFound("not_found")
    return _view(row, cached=True)


async def save_story(
    session: AsyncSession,
    *,
    site_id: UUID,
    facade_id: UUID | None,
    lang: str,
    claims: list[tuple[DraftClaim, str, str | None]],
) -> StoryView:
    source_ids = {UUID(source_id) for _, _, source_id in claims if source_id}
    sources = {
        str(row.id): row
        for row in await session.scalars(select(SourceRow).where(SourceRow.id.in_(source_ids)))
    }
    stored: list[dict[str, Any]] = []
    for claim, label, source_id in claims:
        source = sources.get(source_id or "")
        stored.append(
            {
                "claim_id": claim.claim_id,
                "text": claim.text,
                "label": label,
                "source": {"title": source.title, "url": source.url, "narrator_name": source.narrator_name}
                if source
                else None,
            }
        )
    row = StoryRow(
        site_id=site_id,
        facade_id=facade_id,
        lang=lang,
        claims=stored,
        audio_key=None,
        sources_version=await sources_version(session, site_id),
        generator_version=GENERATOR_VERSION,
    )
    session.add(row)
    await session.flush()
    return _view(row, cached=False)


async def add_audio(
    session: AsyncSession,
    store: ObjectStore,
    tts: TextToSpeechPort,
    story_id: UUID,
    voice: str = DEFAULT_VOICE,
) -> str:
    row = await session.get(StoryRow, story_id)
    if row is None:
        raise NotFound("not_found")
    story = _view(row, cached=True)
    audio = await tts.synthesize(story.text, voice)
    key = new_object_key("audio", "mp3")
    await store.put(key, audio, "audio/mpeg")
    row.audio_key = key
    return key


async def sources_version(session: AsyncSession, site_id: UUID) -> str:
    ids = await session.scalars(
        select(SourceRow.id).where(SourceRow.site_id == site_id).order_by(SourceRow.id)
    )
    digest = hashlib.sha256("".join(str(i) for i in ids).encode())
    return digest.hexdigest()[:16]


def _view(row: StoryRow, *, cached: bool) -> StoryView:
    claims = [
        StoryClaim(
            claim_id=c["claim_id"],
            text=c["text"],
            label=c["label"],
            source=SourceRef(**c["source"]) if c.get("source") else None,
        )
        for c in row.claims
    ]
    return StoryView(row.id, row.site_id, row.facade_id, row.lang, claims, row.audio_key, cached)
