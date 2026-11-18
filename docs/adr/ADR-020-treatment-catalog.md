# ADR-020: Treatments come from a reviewed catalog, not from the model

- Status: Accepted (pending team review)
- Date: 2026-11-18

## Context

The challenge asks for a specific treatment per damage type and the materials and tools it needs. A model writing treatments freely would produce confident text with no source and no review, which conflicts with Athar's rule that nothing reaches the authority without evidence.

## Decision

- Treatments live in `region-packs/treatments/earthen-najdi.json` (path overridable with `SADU_TREATMENT_CATALOG`). Each entry names one damage type and the severities it covers, steps in Arabic, materials with a quantity per m² of wall, tools, whether a specialist must supervise, and source ids.
- Loading validates the file: every source id must exist, and no two entries may cover the same type and severity. A unit test checks that every map damage type has a treatment at every severity.
- The plan groups damaged cells by type and severity, multiplies area by the per-m² quantities (rounded up to 0.1), and lists urgent work first. Anything without a matching treatment is listed as unmatched for the specialist.
- The catalog carries `review_status` and `reviewed_by`. Version 0.1 is a draft written from the Getty Conservation Institute earthen architecture teaching material; the UI shows a warning on every plan until a conservator sets it to `approved`.

## Alternatives

- Ask the model for treatments: flexible, unreviewable.
- Hard-code treatments in Python: reviewers could not edit them without a developer.

## Consequences

- The quantities are estimates (the catalog note says so); the specialist sets the real figures.
- Diriyah can replace the file with its own approved methods and materials without a code change.
