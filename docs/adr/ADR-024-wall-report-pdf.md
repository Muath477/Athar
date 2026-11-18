# ADR-024: Wall reports are PDFs rendered on the server

- Status: Accepted
- Date: 2026-11-18

## Context

The Diriyah challenge asks for damage to be mapped, and the people who act on a map (site managers, contractors, the authority's archive) work from documents, not from our dashboard. The dashboard could already print with the browser, but each browser printed differently, the result depended on screen state, and nothing could produce a report without a person at a browser.

## Decision

- `GET /maps/{id}/report.pdf` renders an A4 Arabic report with WeasyPrint 70 from a Jinja2 template in `reports/infrastructure/templates`.
- Contents: the rectified wall with damage painted per cell in the dashboard's colors and labelled cells, totals by type, changes since the last approved map, the treatment plan with materials and tools, material totals, how much of the model's proposal the expert kept, the cited sources, and the map id. Drafts and a draft treatment catalog are stated on the page.
- Numbers use Arabic-Indic digits and dates are Gregorian in Riyadh time.
- The PDF image needs Pango, HarfBuzz-Subset and Noto Naskh Arabic; the image keeps only the four Noto families the report uses.
- The palette lives in `mapping/domain/palette.py`; a test fails if it drifts from the dashboard's `damage-palette.ts`.

## Alternatives

- Browser print from the dashboard: no server dependency, but inconsistent output and no way to generate reports from a job.
- Headless Chromium on the server: matches the dashboard exactly, but adds a browser and its update cycle to the API image.
- ReportLab: no HTML layout, and Arabic shaping needs extra libraries.

## Consequences

- The API image grows by the PDF libraries and fonts.
- The report and the dashboard share colors but not layout code.
- A site-wide report (Round 2) can reuse the template pieces and run as a job.
