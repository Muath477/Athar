# ADR-011: Local dashboard accounts with server sessions; anonymous passport tokens for visitors

- Status: Accepted (pending team review)
- Date: 2026-11-16

## Context

Inspectors and experts need login; visitors must not need accounts (out of scope) but need a passport and a way to delete their data.

## Decision

Dashboard: users seeded by an admin command; Argon2id hashes (argon2-cffi); server-side session rows; cookie `HttpOnly; Secure; SameSite=Strict`, 8 h idle expiry; lock after 5 failures for 15 min; roles inspector, expert, admin; deny-by-default route dependencies. Visitor: `POST /passports` returns a random 256-bit token stored on the device; the server stores only its SHA-256 hash.

## Alternatives considered

- **Hosted identity provider**: MFA and SSO for free, but setup time and an external dependency for the demo. Recommended for a pilot.
- **JWT in localStorage**: XSS can steal it; no server-side revocation.

## Consequences

- No MFA in Round 1 (accepted risk, demo accounts only).
- Losing the device token loses the passport; acceptable for an anonymous design.

## Versions

argon2-cffi 25.1.0 (PyPI, 2026-11-16).
