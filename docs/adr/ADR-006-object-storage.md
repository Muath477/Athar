# ADR-006: S3 API behind a port; SeaweedFS locally instead of MinIO

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

We store photos, baselines, difference maps, GLB models, audio and PDFs. The brief proposed MinIO locally. On 2026-11-16 the `minio/minio` repository was not found on Docker Hub (the API returned "object not found"), so we cannot pin a MinIO image the normal way.

## Decision

All storage goes through `ObjectStorePort` with one adapter using boto3 against any S3-compatible endpoint. Local dev and the demo VM run SeaweedFS (`chrislusf/seaweedfs`, S3 gateway) in compose. A pilot can point the same adapter at a managed S3-compatible service inside the Kingdom (TBD). Buckets are private; reads use presigned URLs valid 5 minutes.

## Alternatives considered

- **MinIO from source or an old pinned digest**: unmaintained images are a security risk.
- **Garage**: small and S3-compatible; similar choice, less familiar to the team.
- **Local filesystem**: simplest, but diverges from production and complicates presigned URLs.

## Consequences

- One more image to learn (SeaweedFS config: `weed server -s3` with an S3 identities file). Exact flags verified at build time.
- Swapping providers is a config change.

## Versions

boto3 1.44.3 (PyPI, 2026-11-16). SeaweedFS image tag: pin the latest release tag at build time (Docker Hub shows active pushes on 2026-11-16).
