# FaceFolio — Logging

How structured logging works in this project, what to expect in the output, and how to dig
through it when debugging. Companion to `auth.md` (which documents the token-verification
logging in detail) and `CLAUDE.md` (the rules this doc explains the reasoning for).

---

## The one-paragraph summary

Every log line is a `structlog` event: a dotted, lowercase **event name** as the first
argument, plus structured **keyword arguments** for context — never an f-string sentence.
`app/logging_config.py::configure_logging()` renders that as colored, human-readable text in
development and as one JSON object per line in production, and routes stdlib loggers
(uvicorn, SQLAlchemy) through the same pipeline so everything ends up in one consistent
format. A handful of identifying fields (`request_id`, `user_id`, `event_id`, `photo_id`) are
bound once via `structlog.contextvars` and then ride along on every subsequent line for that
request automatically — no endpoint has to pass them explicitly.

---

## Output format

| `ENVIRONMENT` | Renderer | Looks like |
| --- | --- | --- |
| `development` (default) | `structlog.dev.ConsoleRenderer` | Colored, aligned, human-readable |
| `production` | `structlog.processors.JSONRenderer` | One JSON object per line |

Both go through the same processor chain first (`app/logging_config.py`): contextvars are
merged in, a log level and logger name are added, an ISO-8601 UTC timestamp is added, and
`exc_info` (set by `log.exception(...)` or `log.warning(..., exc_info=True)`) is rendered into
a plain `exception` string field via `structlog.processors.format_exc_info`. That last step
matters specifically for JSON mode — without it, an exception would serialize as a bare `true`
and the traceback would be lost, which defeats the entire point of logging the failure.

The jq recipes below assume `ENVIRONMENT=production` (JSON lines). The dev console renderer
is for reading at a terminal, not for piping through `jq`.

---

## Event-name namespaces

| Namespace | Covers | Where |
| --- | --- | --- |
| `http.*` | One line per request (`http.request.completed` / `http.request.failed`), with `status_code` and `duration_ms` | `app/middleware.py` |
| `auth.*` | Token verification failures; new local user rows bridged from a Supabase identity | `app/auth/supabase.py`, `app/db/queries/users.py` |
| `event.*` | Event lifecycle (currently: creation) | `app/api/events.py` |
| `invitation.*` | Invitation creation, claims, and claim rejections (with a `reason`) | `app/api/invitations.py` |
| `photo.upload.*` | The prepare → confirm upload flow, including the future Celery enqueue point | `app/api/photos.py` |
| `photo.processing.*` | Progress polling (status counts) | `app/api/photos.py` |
| `photo.gallery.*` | Gallery listing and its signed-URL generation | `app/api/photos.py` |
| `storage.*` | Every Supabase Storage call (signed URLs, download, delete, exists) | `app/storage/client.py` |
| `purge.*` | Reserved for the scheduled biometric-purge job — **not implemented yet** | (future) |

Within a namespace, event names describe what happened, not the code path: `invitation.claimed`,
not `invitation.claim_success`. Failure/rejection variants say why in a `reason` (or `status`)
keyword argument rather than baking the reason into the event name itself — this keeps the set
of event names small and `jq`-filterable while still being specific in the payload.

---

## Standard context-bound fields

These are bound via `structlog.contextvars.bind_contextvars(...)` rather than passed to every
individual `log.info(...)` call, so once they're known, *every* line for the rest of that
request carries them — including lines from library code (SQLAlchemy, uvicorn) and lines on a
failure path that never reaches the "normal" logging at the end of the handler.

| Field | Bound where | Bound when |
| --- | --- | --- |
| `request_id` | `app/middleware.py::RequestLoggingMiddleware` | First line of every request, alongside `method` and `path` |
| `user_id` | `app/dependencies.py::current_user` | As soon as the JWT is verified and the local user row is confirmed/created — i.e. before any authenticated endpoint body runs |
| `event_id` | Each event-scoped endpoint handler (`app/api/events.py`, `app/api/invitations.py`, `app/api/photos.py`) | As soon as it's known — from the path directly, or from a loaded row (e.g. `invitation.event_id`) if the path doesn't carry it |
| `photo_id` | `app/api/photos.py::confirm_photo_endpoint` | As soon as it's known from the path |

**Contextvars are cleared at the end of every request**, in `RequestLoggingMiddleware`'s
`finally` block (`structlog.contextvars.clear_contextvars()`), and once defensively at the
start too. This is what stops `event_id` from a photo-confirm request leaking into the next,
unrelated request handled by the same worker process.

---

## Never-log rules

Log **ids and derived metrics**, never the underlying sensitive value:

| Never log | Log instead | Why |
| --- | --- | --- |
| JWTs / bearer tokens | `reason` for the failure (`invalid_or_expired`, `missing_claims`, `malformed_subject`) | A logged token is a valid credential sitting in a log aggregator |
| Signed storage URLs | the storage `key`, `count`, `expires_in` | A signed URL **is** a bearer credential — anyone with it can read/write that object until it expires |
| Emails | `user_id` | PII; the id is sufficient to correlate |
| Face embeddings / any vector data | `face_count`, `dims`, `det_scores`, similarity scores, quality pass/reject counts with reasons | **Embeddings are biometric data under POPIA/GDPR.** The scheduled purge job (`purge.*`, Phase 4+) deletes them from the `embedding` column on event expiry — but it can only reach Postgres. A copy sitting in a log line, and from there in whatever log aggregator ingests it, outlives that deletion entirely and defeats the purpose of having a purge job at all. |

Failure paths follow the same split: the exception is logged internally (`log.exception(...)`
or `log.warning(..., exc_info=True)`), but the client-facing `HTTPException` detail stays
generic (`"Invalid or expired token"`, `"Could not prepare uploads, try again"`). This is
already how `verify_token` works — see `docs/auth.md`'s "Debugging notes" section for the
reasoning.

---

## jq recipes

Assumes JSON-lines output (`ENVIRONMENT=production`), piped from wherever the process's stdout
ends up — e.g. `docker compose logs backend --no-log-prefix -f | jq ...` or a log file.

**All activity for one event:**
```bash
jq 'select(.event_id == "8d2ec22d-...")'
```

**Everything that went wrong (warnings and errors):**
```bash
jq 'select(.level == "warning" or .level == "error")'
```

**Trace a single request end-to-end:**
```bash
jq 'select(.request_id == "d3e80c85-...")'
```

**Everything in one namespace** (e.g. the upload flow):
```bash
jq 'select(.event | startswith("photo.upload"))'
```

**A rejected/failed outcome with its reason, across namespaces:**
```bash
jq 'select(.event | endswith("_rejected") or endswith("_failed")) | {event, reason, event_id, request_id}'
```

**Just the request-completion summary line for slow requests:**
```bash
jq 'select(.event == "http.request.completed" and .duration_ms > 500)'
```
