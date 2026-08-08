# FaceFolio — Monorepo

Event photo-sharing with facial recognition. Hosts bulk-upload event photos; guests
take one selfie and receive a personalized "Photos of You" folder built by matching
their face against every photo in the event.

## Layout

This is a monorepo with two independently deployable halves:

- `backend/` — FastAPI + Celery + PostgreSQL/pgvector + InsightFace. The API, the
  async CV pipeline, and all data. Deploys to Render. Has its own CLAUDE.md.
- `frontend/` — React + TypeScript + Vite. The web client. Deploys to Vercel. Has
  its own CLAUDE.md and DESIGN.md.

When working in one half, read that half's CLAUDE.md — it is authoritative for its
conventions. This root file is shared context only.

## How the halves relate

The frontend is a pure client of the backend's HTTP API. It never touches the
database directly. Authentication is via Supabase: the frontend obtains a JWT from
Supabase and sends it as a Bearer token; the backend verifies it. File uploads go
directly from the browser to Supabase Storage via presigned URLs the backend issues —
the backend never proxies file bytes.

The backend API is the contract between the two halves. Its shapes are defined in:
- `backend/app/schemas/` — the Pydantic request/response models (source of truth)
- `backend/docs/` — auth flows, system flows, the SQL schema
- `docs/API.md` — consolidated, frontend-facing endpoint reference (if present)

When writing frontend code that calls the API, read the backend schema for the exact
shape rather than guessing. The TypeScript types and the Pydantic models must agree.

## Cross-cutting contracts to respect

- Invitation links use the path `/join/:token`. The backend builds links with this
  exact path; the frontend router must match it.
- The frontend dev server runs on http://localhost:5173; the backend on
  http://localhost:8000. Backend CORS is configured from its `frontend_origin` setting.
- Biometric data (selfies, embeddings) is per-event and consent-gated. The frontend
  must collect explicit facial-recognition consent before the enroll call, and must
  never treat a guest's selfie or matches as shareable data.
- Only the Supabase PUBLISHABLE (anon) key belongs in the frontend. The service key
  is backend-only and must never appear in frontend code or env.

## Deploy targets

Backend → Render (Docker). Frontend → Vercel (static). Postgres/Auth/Storage →
Supabase. Redis broker → Upstash (production). Each half deploys from its own
subdirectory.