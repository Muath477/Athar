from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from sadu.shared.db import Base, Timestamped, UuidPk

EMBEDDING_DIMENSIONS = 1024


class SourceRow(UuidPk, Timestamped, Base):
    __tablename__ = "sources"

    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(String(500))
    narrator_name: Mapped[str | None] = mapped_column(String(200))
    license: Mapped[str] = mapped_column(String(100))
    reviewed_by: Mapped[str] = mapped_column(String(200))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StoryChunkRow(UuidPk, Base):
    __tablename__ = "story_chunks"
    __table_args__ = (
        Index(
            "ix_story_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_story_chunks_tsv", "tsv", postgresql_using="gin"),
    )

    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    facade_id: Mapped[UUID | None] = mapped_column(ForeignKey("facades.id", ondelete="SET NULL"))
    text_ar: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    # 'simple' config: Postgres has no Arabic stemmer, so match on whole words.
    tsv: Mapped[Any] = mapped_column(TSVECTOR, Computed("to_tsvector('simple', text_ar)", persisted=True))


class StoryRow(UuidPk, Timestamped, Base):
    __tablename__ = "stories"

    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    facade_id: Mapped[UUID | None] = mapped_column(ForeignKey("facades.id", ondelete="SET NULL"))
    lang: Mapped[str] = mapped_column(String(4))
    claims: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    audio_key: Mapped[str | None] = mapped_column(String(300))
    sources_version: Mapped[str] = mapped_column(String(64))
    generator_version: Mapped[str] = mapped_column(String(32))
