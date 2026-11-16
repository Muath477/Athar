# ADR-009: BGE-M3 embeddings locally behind a port, with full-text fallback

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

Story retrieval needs Arabic-capable embeddings. The knowledge base is small (tens to hundreds of chunks).

## Decision

`EmbeddingPort.embed(texts) -> list[list[float]]` with a BGE-M3 adapter (1024-dim dense vectors) running on CPU in the API container; source chunks are embedded offline by a script at pack import, so only short queries are embedded at runtime. Fallback: Postgres full-text search on `tsv`.

## Alternatives considered

- **Hosted embeddings API**: no model in the image, but another key, network dependency and Arabic quality to validate.
- **No embeddings, keyword only**: works for a tiny corpus but weak on paraphrased questions.

## Consequences

- Larger API image (PyTorch CPU + model weights about 2 GB); weights downloaded at build time and cached.
- If the image size becomes a problem, move the embedder to a separate container or a hosted API; only the adapter changes.

## Versions

FlagEmbedding 1.4.2 (PyPI, 2026-11-16). Model id `BAAI/bge-m3`: verify on Hugging Face at build time. pgvector 0.8.7 for HNSW.
