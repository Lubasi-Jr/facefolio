# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

FaceFolio: an event photo-sharing backend. Event hosts bulk-upload photos; guests take a
selfie and receive a personalized "Photos of You" folder built by facial recognition. The
core is an async computer-vision pipeline: detect faces, embed them as 512-d vectors, and
match guest selfies against event photos using vector similarity in PostgreSQL (pgvector).

This is a solo learning project. The developer is building it to learn Celery, InsightFace,
FastAPI, and vector search, so prefer clear, conventional, well-explained code over clever
abstractions. When a decision has a tradeoff, briefly note it in a comment or in your reply.

## Tech stack (do not substitute without asking)

- Python 3.12, managed with uv (use `uv add`, `uv run`; never pip or poetry)
- FastAPI (async), Pydantic v2, pydantic-settings for config
- SQLAlchemy 2.0 async (Mapped / mapped_column typing style), asyncpg driver
- Alembic for migrations
- PostgreSQL + pgvector (pgvector.sqlalchemy Vector type)
- Celery with Redis as broker ONLY (result backend disabled; task status is tracked via the
  photo.status column in Postgres, not Celery's result backend)
- InsightFace (buffalo_l bundle) on onnxruntime CPU, for detection + embedding
- Supabase for Postgres host, Auth (JWT verification), and Storage

## Architecture principles (respect these)

- The API tier is stateless and never holds large files. Uploads go directly from client to
  Supabase Storage via presigned URLs. The API only issues URLs and reads/writes the database.
- Heavy work (CV processing) runs in Celery tasks, never inline in a request. One queue
  message per photo, carrying only the photo_id; the task looks up everything else.
- Celery tasks must be idempotent (they may run more than once under at-least-once delivery):
  deterministic storage keys, delete-then-insert for face rows in a transaction, and
  ON CONFLICT DO NOTHING for tag upserts.
- Vector search is always scoped to a single event via a WHERE clause. Do NOT add HNSW or
  IVFFlat indexes; the per-event candidate set is small enough for exact search, and that is
  a deliberate decision. Cosine similarity is `1 - (embedding <=> :vec)`.
- Embeddings are L2-normalized before storage.
- Biometric data (embeddings, selfies, face crops) is per-event and lifecycle-managed. Never
  design a global/cross-event face profile.

## Layering rules (important)

- `app/cv/` is pure computer vision. It takes numpy arrays / file paths and returns plain data
  (boxes, vectors, booleans). It must NOT import from `app/db/`, `app/storage/`, or FastAPI.
  This keeps it unit-testable without infrastructure. Do not break this boundary.
- `app/db/queries/` holds query functions callable from both the API and Celery tasks. No
  FastAPI coupling in there.
- Celery task bodies and API endpoints are thin orchestrators that call into `cv/` and
  `db/queries/`. Business logic lives in those layers, not in the endpoint or task function.
- Pydantic schemas (`app/schemas/`) are separate from SQLAlchemy models (`app/models/`). The
  API contract does not leak ORM internals.

## Conventions

- Async all the way: async endpoints, async SQLAlchemy sessions, async db query functions.
- Type-hint everything. Use `Mapped[...]` on models.
- Config comes from `app/config.py` (pydantic-settings). Never hardcode secrets, URLs, or
  thresholds; add a setting. Secrets load from `.env` (which is gitignored).
- Prefer explicit over magic. Small, named functions over long ones.
- When creating a file, put it in the right layer per the structure below. Ask if unsure.
- Use `Annotated[Type, Depends(...)]` for all FastAPI dependencies, never the
  legacy `param: Type = Depends(...)` default-value style. Define reusable aliases
  (e.g. `SessionDep = Annotated[AsyncSession, Depends(get_session)]`,
  `CurrentUser = Annotated[str, Depends(current_user)]`) in app/dependencies.py
  and use those in endpoint signatures.

## Logging

- All logging uses structlog. Never use `print()` or bare stdlib `logging` calls.
- Every log call's first argument is a dotted event name (`photo.processing.faces_detected`),
  never a prose sentence. Context goes in keyword arguments, never f-strings.
  Good:  log.info("photo.processing.completed", photo_id=pid, faces=3, duration_ms=412)
  Bad:   log.info(f"Processed photo {pid} with 3 faces")
- Bind `event_id` / `photo_id` / `user_id` via contextvars at the start of a request or
  Celery task so downstream lines inherit them automatically.
- When building or modifying any core feature, add logging at: entry (what was requested),
  each significant state transition, external calls (storage, queue) and their outcome, all
  failure paths (with the underlying exception), and completion (with a duration and a
  count where meaningful).
- Log ids, never payloads. Never log JWTs, signed URLs, secrets, emails, or embeddings.
- Failures log the real exception internally while the client-facing message stays vague.
- NEVER log face embeddings or any vector data. Embeddings are biometric data under
  POPIA/GDPR — logging them creates copies outside the database that the purge job cannot
  reach. Log shape and derived metrics instead: face_count, dims, norms, det_scores,
  similarity scores, quality pass/reject counts with reasons.

## Working style with me

- I run prompts one small unit at a time, on purpose, to learn as I go. Do NOT scaffold ahead
  or create files I did not ask for. Build only what the current prompt requests.
- When you generate non-trivial code (Celery config, CV pipeline, vector queries), add a short
  explanation of what it does and why, so I can check it against my understanding.
- If a prompt would require a design decision I have not specified, ask a brief question rather
  than guessing, especially around the architecture principles above.
- After making changes, tell me how to verify them (a command, a curl, a psql check).
- Do not add dependencies without saying so and why.

## Project structure (target — grows phase by phase, do not pre-create empty files)

```
app/
  main.py              # FastAPI app factory + lifespan
  config.py            # pydantic-settings
  dependencies.py      # shared Depends (db session, current user)
  api/                 # routers: events, photos, enrollments, tags, invitations
  schemas/             # Pydantic request/response models
  models/              # SQLAlchemy 2.0 models
  db/
    session.py         # async engine + sessionmaker
    queries/           # query functions (shared by api + worker)
  auth/                # Supabase JWT verify + authz guards
  storage/             # Supabase storage client + key builders
  cv/                  # pure CV: loader, detector, embedder, quality, imaging
  worker/              # celery_app, tasks, scheduler
  utils/
tests/
migrations/            # Alembic
```

## Commands

- Run API locally: `uv run uvicorn app.main:app --reload`
- Run worker: `uv run celery -A app.worker.celery_app worker --loglevel=info`
- Run beat: `uv run celery -A app.worker.celery_app beat --loglevel=info`
- Migrations: `uv run alembic revision --autogenerate -m "msg"` then `uv run alembic upgrade head`
- Everything up locally: `docker compose up --build`

## Things NOT to do

- Do not use pip/poetry, or add a result backend to Celery.
- Do not run CV work inside a request handler.
- Do not add ANN vector indexes (HNSW/IVFFlat).
- Do not couple `app/cv/` to the database or storage.
- Do not commit secrets; anything sensitive is a setting loaded from `.env`.
- Do not create files or folders beyond what the current task needs.
