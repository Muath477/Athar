# Sadu web

Visitor PWA (capture, story, passport) and the authority dashboard (3D pins, evidence, review queue).
Arabic first, right to left. All data comes from the API under `/api/v1`.

```bash
npm ci
SADU_API_ORIGIN=http://localhost:8000 npm run dev   # http://localhost:3000
npm run lint && npm run typecheck && npm run build
```

In development, `next.config.ts` proxies `/api` to `SADU_API_ORIGIN`. In production Caddy routes `/api`
to the API container, so the browser always talks to one origin and the session cookie stays `SameSite=Strict`.
