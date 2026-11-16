# ADR-015: Process before store: EXIF strip and face blur before storage or any LLM call

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

Visitor photos can contain faces and EXIF GPS. Saudi PDPL requires minimization and purpose limitation.

## Decision

The upload handler decodes the image in memory, applies orientation, drops all metadata, resizes, blurs faces (YuNet), and only then writes to storage. Raw GPS lives on the observation until identification, then is nulled. No visitor names or accounts. Retention table in 03-architecture §6.

## Alternatives considered

- **Store original, blur on read**: keeps more data than needed and risks leaks.
- **Blur on device**: saves bandwidth, but older phones are slow and we cannot trust the client.

## Consequences

- Face detection can miss faces (side profiles, small faces); we accept this risk in Round 1 and log detection counts; a pilot needs a review.
- Cross-border LLM processing remains an open legal question (TBD).

## Versions

opencv-python-headless 5.0.0.93, pillow 13.0.0 (PyPI, 2026-11-16).
