from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.sites import api as sites
from sadu.modules.stories import api as stories
from sadu.modules.verification import api as verification
from sadu.shared.ports.embeddings import EmbeddingPort
from sadu.shared.ports.llm import LLMPort, LLMRefused, LLMUnavailable
from sadu.shared.ports.speech import SpeechUnavailable, TextToSpeechPort
from sadu.shared.storage import ObjectStore
from sadu.shared.web import UnitOfWork

log = structlog.get_logger()


@dataclass(frozen=True)
class Dependencies:
    unit_of_work: UnitOfWork
    store: ObjectStore
    llm: LLMPort
    tts: TextToSpeechPort
    embedder: EmbeddingPort | None = None
    voice: str = stories.DEFAULT_VOICE


async def verified_story(
    deps: Dependencies, site_id: UUID, facade_id: UUID | None
) -> stories.StoryView | None:
    async with deps.unit_of_work() as session:
        story = await stories.cached_story(session, site_id, facade_id)
        if story is None:
            story = await _new_story(deps, session, site_id, facade_id)
        if story is not None and story.audio_key is None:
            try:
                await stories.add_audio(session, deps.store, deps.tts, story.id, deps.voice)
                story = await stories.cached_story(session, site_id, facade_id)
            except SpeechUnavailable as error:
                log.info("story_audio_skipped", reason=str(error))
    return story


async def _new_story(
    deps: Dependencies, session: AsyncSession, site_id: UUID, facade_id: UUID | None
) -> stories.StoryView | None:
    site = await sites.get_site(session, site_id)
    place = site.name_ar
    if facade_id:
        place = f"{place}، {(await sites.get_facade(session, facade_id)).name_ar}"
    query = await stories.embed_query(deps.embedder, place)
    chunks = await stories.retrieve_chunks(session, site_id, facade_id, query_embedding=query)
    if not chunks:
        return None
    try:
        drafts = await stories.draft_claims(
            deps.llm, place_name=place, passages=[(c.chunk_id, c.text) for c in chunks]
        )
    except (LLMUnavailable, LLMRefused) as error:
        log.warning("story_draft_failed", error=str(error))
        return None
    verdicts = await verification.check_claims(
        deps.llm,
        [verification.Claim(d.claim_id, d.text, d.chunk_id) for d in drafts],
        [
            verification.Chunk(c.chunk_id, c.source_id, verification.SourceKind(c.source_kind), c.text)
            for c in chunks
        ],
    )
    kept = [(d, v.label.value, v.source_id) for d, v in zip(drafts, verdicts, strict=True) if v.publishable]
    if not kept:
        return None
    return await stories.save_story(session, site_id=site_id, facade_id=facade_id, lang="ar", claims=kept)
