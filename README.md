# FaceFolio

Facial recognition photo sharing for events. A host uploads a full event gallery, a
guest takes one selfie, and FaceFolio automatically builds them a personal folder of
every photo they appear in. No native app, just a web link.

This README covers running the whole system locally with Docker.

---

## What it does

- **Hosts** create an event, bulk upload photos, and share an invite link.
- Every uploaded photo is analysed in the background: faces are detected, embedded as
  512 dimension vectors, and stored.
- **Guests** open the link, give consent, take (or upload) one selfie, and land on a
  "Photos of you" folder matched by face, plus an "All photos" view of the whole event.
- Uncertain matches surface as an "Is this you?" prompt the guest confirms.
- Biometric data (selfies, embeddings) is consent gated on the way in and deleted on a
  schedule after the event expires, while the ordinary photos and confirmed tags remain.

---

## Architecture at a glance

Three cooperating pieces, decoupled through a broker and a database:

- **API** (FastAPI): serves the HTTP API, issues presigned upload URLs, runs the
  synchronous enrollment match.
- **Worker** (Celery): processes uploaded photos off the request path (detect, build
  derivatives, embed, match) and runs the scheduled biometric purge.
- **Beat** (Celery): fires the scheduled tasks (purge, reconcile).

Shared infrastructure: **PostgreSQL + pgvector** (data and vector search), **Redis**
(Celery broker), **Supabase** (auth and object storage). Image bytes go straight from
the browser to Supabase Storage via presigned URLs; the API never proxies files.

**Stack:** Python, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL, pgvector,
Celery, Redis, InsightFace (buffalo_l) on ONNX Runtime, Supabase, Docker Compose,
TypeScript, React 18, Vite, TanStack Query, Zustand, Tailwind CSS.

---

## Prerequisites

- **Docker** and **Docker Compose** installed and running.
- A **Supabase project** (free tier is fine). You need its Postgres connection, the
  project URL, the service role key, the publishable/anon key, and a Storage bucket.
- Roughly 2 GB free disk for the InsightFace model and images.

Supabase setup (one time):
1. Create a project. Note the project URL and the API keys (Settings, then API).
2. Create a Storage bucket (e.g. `event-media`).
3. Authentication, then Providers: enable **Email** (magic link) and
   **Anonymous sign ins**.
4. Authentication, then URL Configuration: add `http://localhost:5173` to the redirect
   URLs.

pgvector and citext are enabled by the database migrations, no manual extension setup
needed.

---

## Environment variables

### Backend, `backend/.env`

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/facefolio
REDIS_URL=redis://redis:6379/0
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_KEY=<service_role key, server side only, never in the frontend>
STORAGE_BUCKET=event-media
FRONTEND_ORIGINS=http://localhost:5173

# Tuning (sensible defaults shown)
PURGE_GRACE_DAYS=7
MATCH_T_HIGH=0.55
MATCH_T_LOW=0.40
MATCH_MARGIN=0.10
FACE_MIN_SIZE_PX=40
FACE_DET_SCORE_MIN=0.6
FACE_BLUR_VARIANCE_MIN=100.0
SELFIE_MIN_FACE_SIZE_PX=200
SELFIE_BRIGHTNESS_MIN=40.0
SELFIE_BRIGHTNESS_MAX=220.0
MAX_PHOTOS_PER_EVENT=500
```

The `docker-compose.yml` overrides `DATABASE_URL` and `REDIS_URL` to the internal
container hostnames, so the values above are the in-container ones. For a Supabase
Postgres instead of the local container, point `DATABASE_URL` at the Supabase pooler
URL.

### Frontend, `frontend/.env.local`

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<publishable / anon key, safe for the browser>
```

Only the publishable key goes in the frontend. The service key stays backend only.

---

## Running it

### 1. Start the backend stack

From `backend/`:

```bash
docker compose up -d --build
```

This builds and starts five services: `backend` (API on :8000), `worker`, `beat`,
`postgres` (:5432), and `redis` (:6379). The first run downloads the InsightFace model
(~280 MB) into the worker, so the first photo processed is slow; later ones are fast.

### 2. Apply database migrations

```bash
docker compose exec backend alembic upgrade head
```

Note: migrations run inside the container, and code is baked into the image at build
time. After generating a new migration, rebuild the backend
(`docker compose up -d --build backend`) so the container has the file before running
`alembic upgrade head`.

### 3. Start the frontend

From `frontend/`:

```bash
npm install
npm run dev
```

The app is at `http://localhost:5173`. The API is at `http://localhost:8000` (docs at
`/docs`).

---

## Trying the full flow

1. Open `http://localhost:5173`, sign in with a magic link (check your email).
2. Create an event and upload a few photos. Watch them process:
   `docker compose logs -f worker` shows each photo reach
   `photo.processing.completed status=processed`.
3. On the event page, click **Invite guests** and copy the `/join/:token` link.
4. Open that link in an **incognito window** (so the guest's anonymous session does not
   replace your host session). Give consent, take or upload a selfie of someone who is
   in the uploaded photos, and land on "Photos of you".

Use a selfie of someone actually in the group photos, otherwise you correctly get zero
matches.

---

## Useful commands

```bash
# follow worker (photo processing) logs
docker compose logs -f worker

# follow API logs (enrollment runs here, synchronously)
docker compose logs -f backend

# psql into the database
docker compose exec postgres psql -U postgres -d facefolio

# rebuild after backend code changes
docker compose up -d --build backend worker

# stop everything
docker compose down
```

---

## How it works, briefly

- **Uploads** are direct to storage. The client asks the API for presigned URLs in
  batches, PUTs the files straight to Supabase Storage through a bounded concurrency
  pool (about 5 in flight), then confirms. The API never handles image bytes.
- **Processing** is per photo in the Celery worker: detect faces, build web and
  thumbnail derivatives, embed each face as a 512d vector, and match against the
  event's enrolled guests. One queue message per photo, carrying only the photo id.
- **Matching** is scoped per event. A guest's selfie (or a newly processed photo's
  faces) is compared by pgvector cosine similarity only against that event's
  enrollments, which keeps the search small and exact (no approximate index needed).
- **Confidence bands** replace a single threshold. Above `MATCH_T_HIGH` (with a margin
  over the runner up) a match auto tags; between `MATCH_T_LOW` and `MATCH_T_HIGH` it
  becomes an "Is this you?" prompt; below `MATCH_T_LOW` it is dropped.
- **Biometric lifecycle.** Facial recognition is consent gated before the camera opens.
  A scheduled job deletes enrollment selfies and face embeddings `PURGE_GRACE_DAYS`
  after an event expires, while keeping the photos and the confirmed tags (a tag is an
  ordinary record, not biometric data), so a guest's existing folder still works after
  the biometric material is gone.

---

## Privacy note

FaceFolio handles biometric data (selfies and face embeddings), treated as special
personal information under POPIA. The design follows data minimisation and
retention limits: enrollment is per event (never a global face profile), processing is
consent gated, and biometric material is permanently deleted within
`PURGE_GRACE_DAYS` of an event ending. One honest caveat worth stating in any public
privacy notice: deleted embeddings can persist in point in time database backups until
those backups age out (roughly 30 days), which is standard and acceptable provided
backups are encrypted and the retention window is disclosed.

---

## Notes and limitations

- The CV worker uses `--pool=solo` locally, because onnxruntime and OpenCV do their own
  internal threading and layering Celery concurrency on top can be unstable. For more
  throughput, run several `--pool=solo` worker processes against the same Redis rather
  than raising in-process concurrency.
- `FACE_MIN_SIZE_PX` is an absolute pixel floor on the shorter side of a detected face,
  measured on the original image, so its effect varies with photo resolution. 40 works
  well for typical web sized photos; high resolution camera photos have large faces and
  are unaffected.
- This is a portfolio project. It is designed to run locally or demo, not as a hardened
  public service.
