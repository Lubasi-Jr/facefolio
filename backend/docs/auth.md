# FaceFolio — Authentication & Authorization

How auth works in this project, why it is built this way, and how to test it.
Companion to `schema.sql` (structure) and `FLOWS.md` (data movement).

---

## The one-paragraph summary

Supabase is the **identity provider**: it authenticates people and issues JWTs. This
backend is a **resource server**: it verifies those JWTs and serves data accordingly. It
never issues tokens, never sees passwords, and holds no session state. Authentication
answers *"who are you?"* (verify the JWT, get a user id). Authorization answers *"what may
you do?"* (look up the `invitations` table for this user + this event). The two are
separate layers and both are required on every protected route.

---

## Architecture

```
  Browser ──1. signInWithOtp ──────────────▶ Supabase Auth
          ◀──2. JWT (ES256) ────────────────

  Browser ──3. request + Bearer JWT ───────▶ FastAPI backend
                                              │ 4. verify signature via JWKS
                                              │ 5. sub → local users row
                                              │ 6. invitations lookup (authz)
          ◀──7. response / 401 / 403 ────────
```

Key properties:

- **The backend is not in the login path.** Steps 1–2 happen directly between the client
  and Supabase. The backend never sees credentials.
- **Verification is local and offline.** The backend does not call Supabase to ask "is this
  token real?" It checks the cryptographic signature itself. No network hop per request.
- **The backend is stateless.** No sessions stored, so any API instance can serve any
  request. This is what allows horizontal scaling with no sticky sessions or shared session
  store.
- **Token lifecycle is entirely client-side.** supabase-js refreshes access tokens
  proactively in the background before they expire (they last 1 hour). The backend's only
  job on an expired token is to return 401. It has no refresh logic.

---

## Authentication

### Why ES256 / JWKS, not HS256

Supabase migrated this project to **asymmetric signing keys**. Tokens are signed with
**ES256** using a private key Supabase holds; the matching **public** keys are published at:

```
{SUPABASE_URL}/auth/v1/.well-known/jwks.json
```

The backend fetches that key set, matches the token's `kid` header to the right public key,
and verifies the signature. `PyJWKClient` handles fetching and caching; it is instantiated
**once at module level** so the key set is not re-fetched per request.

This is better than the legacy HS256 shared-secret approach: with a symmetric secret, the
same value that *verifies* tokens can also *forge* them, so every service holding it is a
liability. With asymmetric keys the backend holds only a public key — even if compromised,
it could not mint a valid token.

Requires `pyjwt[crypto]`. Plain PyJWT cannot do elliptic-curve crypto and fails with
`MissingCryptographyError: ES256 requires 'cryptography' to be installed`.

### Why HTTPBearer, not OAuth2PasswordBearer

`OAuth2PasswordBearer(tokenUrl="token")` tells OpenAPI "this API has a login endpoint that
accepts a username and password." This API has no such endpoint — users authenticate with
Supabase and arrive already holding a token. `HTTPBearer` simply says "expect an
`Authorization: Bearer` header," which is exactly the situation.

Both extract the same string from the same header; they differ only in what they claim about
where the token came from.

### The layers

```
app/auth/supabase.py     verify_token(token) -> (UUID, email)
                         Pure logic. No FastAPI coupling. Unit-testable with a
                         hand-made token and no HTTP involved.

app/dependencies.py      bearer_scheme = HTTPBearer()        (extracts the header)
                         current_user(credentials, session)  (verifies + bridges identity)
                         SessionDep   = Annotated[AsyncSession, Depends(get_session)]
                         CurrentUser  = Annotated[UUID, Depends(current_user)]
```

Endpoints use the aliases and never touch `Depends(...)` directly:

```python
async def create_event(payload: EventCreate, session: SessionDep, user: CurrentUser): ...
```

### Boundary rules

- The `sub` claim is parsed into a `UUID` **at the auth boundary**, not in each endpoint. A
  malformed `sub` therefore fails as a 401 rather than surfacing as a type error deep inside
  a SQLAlchemy query. Validate and normalize at the edge; the interior only handles
  well-formed data.
- `audience="authenticated"` is validated. Supabase puts `"aud": "authenticated"` in its
  tokens, and PyJWT rejects tokens whose `aud` is present but unchecked — this parameter is
  load-bearing, not decoration.
- The client-facing error is deliberately vague (`"Invalid or expired token"`) so crypto
  details are never leaked to callers. The **real** exception is logged at warning level.
  Both `PyJWTError` and `PyJWKClientError` are caught — JWKS fetch/parse failures are not
  `PyJWTError` subclasses and would otherwise escape as unhandled 500s.

---

## Identity bridging: `get_or_create_user`

### The problem it solves

Supabase Auth maintains its own `auth.users` table. This project has its **own** `users`
table. They are separate. A JWT's `sub` is a Supabase user id — and on a user's first
request, there is no corresponding row in the local `users` table.

Every write then fails, because `events.host_id`, `invitations.user_id`, `photos.uploader_id`
and others are all foreign keys to `users.id`:

```
asyncpg.exceptions.ForeignKeyViolationError:
  insert or update on table "events" violates foreign key constraint "events_host_id_fkey"
  DETAIL: Key (host_id)=(cc308900-...) is not present in table "users".
```

This is **not** a bug in the foreign key. The constraint is doing exactly its job — refusing
to create an event owned by a user who does not exist. The gap is the missing bridge.

### The fix

`app/db/queries/users.py::get_or_create_user(session, user_id, email, display_name)` inserts
a `users` row if one does not exist for that id, and returns it. It is called from the
`current_user` dependency, so **every authenticated request guarantees the local user row
exists** before any endpoint body runs. No endpoint has to remember.

`verify_token` returns the `email` claim alongside the `sub` so the bridge has something to
populate the row with. `current_user` still returns just the `UUID`, so endpoint signatures
are unchanged.

### Why a local users table at all

This is the deliberate seam. Every foreign key in the database points at an identity concept
**we own**, not one the auth provider controls. Swap Supabase for Auth0 or a hand-rolled auth
service tomorrow and `get_or_create_user` is the one function that changes — every foreign
key, query, and model is untouched. Without it, every FK in the schema would point at a
vendor's identity concept.

### Why not populate `users` manually

It does not survive contact with a real user. A guest scans a QR code at a wedding, Supabase
authenticates them, and their first request 500s because no human was standing by to insert
their row. `get_or_create_user` **is** the sign-up path for guests (see `FLOWS.md` Flow 4a) —
there is no separate registration step in this product.

### Why not a Supabase webhook

Arguably cleaner in production (sync on signup rather than checking every request), but it is
a whole extra integration to build, deploy, and debug. Get-or-create is a primary-key lookup
on a session the endpoint already borrowed — effectively free. Noted as possible future work.

---

## Authorization

### The model

Permissions here are **relational**, not scope-based. Naledi is a *guest* of evt-1 and a
*host* of evt-99 — there is no single token scope that captures that. Her permission is not a
property of *her*; it is a property of the `(user, event)` pair, and it lives in the
`invitations` table.

This is why authorization uses plain `Depends` with a database-checking guard, and **not**
FastAPI's `Security(..., scopes=[...])`. Scopes answer *"what kind of user is this?"* (a
global fact in the token). These guards answer *"what is this user's relationship to this
specific thing?"* (a live fact in the database).

A live lookup also stays current: revoke a guest's invitation and the next request is denied
immediately, whereas a scope baked into a token would remain valid until it expired.

### The guards

`app/auth/guards.py`:

| Guard | Requires | Used for |
| --- | --- | --- |
| `require_event_member(event_id)` | a `joined` invitation for this user + event | viewing the gallery, enrolling a selfie, reading "Photos of You" |
| `require_host(event_id)` | the same, **and** `role = 'host'` | creating upload URLs, deleting photos, generating invitation links |

Both require `status = 'joined'`. A **pending** invitation (invited but never claimed) and a
**revoked** one do not grant access.

`require_host` deliberately does **not** consult `events.host_id`. `invitations` is the single
source of truth for membership and role, so adding co-hosts later would be a new row rather
than a schema change plus a guard rewrite. `events.host_id` remains useful as "who created
this event," but authorization reads one table.

### Layering

The SQL lives in `app/db/queries/invitations.py::get_membership(session, event_id, user_id)`,
not in the guards. The guards call it and decide whether to raise. This keeps the lookup
reusable (a Celery task may need it) and keeps FastAPI coupling out of the query layer.

### How `event_id` reaches the guard

The guard declares `event_id: uuid.UUID` as a plain parameter. FastAPI resolves it from the
**path** of whatever route uses the guard. So `POST /events/{event_id}/photos` hands that
value to the guard automatically. Guards therefore only work on routes that actually have
`{event_id}` in the path.

### Attaching a guard

Guards return `None` — they exist to raise or not raise — so attach them via the decorator
rather than an unused parameter:

```python
@router.post("/events/{event_id}/photos", dependencies=[Depends(require_host)])
```

### Important: there is no database-level safety net

This project **bypasses Supabase's PostgREST + RLS entirely**. The frontend never talks to
the database; it talks to this API, which queries Postgres directly via SQLAlchemy with its
own credentials. That means these guards are the **only** thing standing between a user and
someone else's data. There is no RLS backstop. Treat any change to `guards.py` as
security-sensitive and always test the negative case.

---

## The invitation model

A **shared invite token** is what a QR code encodes. Many guests scan the same code.

Therefore claiming an invitation **INSERTs a new invitation row** for the claiming user
rather than mutating the shared row. The shared row stays `pending` and reusable. See
`FLOWS.md` Flow 4a: `inv-2` is the shared pending invitation; Naledi's claim creates `inv-3`,
her own `joined` row.

If claiming mutated the shared row, only the first guest to scan would ever get in.

Consequences:

- The `email` field on an invitation is **advisory only** — a note of where the link was
  sent. The claim endpoint identifies the guest from their **JWT**, not from the email. This
  is required for a shared QR code to work at all.
- `role` is never client-supplied. `InvitationCreate` accepts only an optional email; the
  role is server-set to `guest`. (If a client could set `role`, anyone able to invite could
  mint a host invitation and escalate.)
- The claim endpoint checks `get_membership` first and returns a deliberate **409** if the
  user is already a member, rather than letting `UNIQUE(event_id, user_id)` surface as an
  unhandled `IntegrityError` → 500. The constraint remains the correctness backstop; the
  check provides the decent API response.
- Tokens are `secrets.token_urlsafe(24)` — ~192 bits of entropy, URL-safe for links and QR
  codes. Not `uuid4`, not `random`.
- The host's own invitation row is created as `joined` directly when the event is created, so
  it is never claimable (the `status != 'pending'` check blocks it). This invariant matters:
  a claim copies `role` from the shared invitation, so a `pending` host row would be an
  escalation path.

---

## Environment configuration

| Variable | Purpose |
| --- | --- |
| `SUPABASE_URL` | Project URL; the JWKS URL is derived from it |
| `SUPABASE_JWKS_URL` | `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` (derived, not a separate secret) |
| `FRONTEND_ORIGIN` | Used to build `invite_link` and for CORS |

**No JWT secret is needed.** Verification uses public keys fetched from JWKS. The legacy
`SUPABASE_JWT_SECRET` has been removed from `Settings`.

Note: Supabase's dashboard shows four keys (`anon` / `sb_publishable` are the public pair;
`service_role` / `sb_secret` are the privileged pair). **None of them are used for JWT
verification.** The publishable key is used by clients to talk to *Supabase*; the secret key
is used server-side for Storage (Phase 3). The database password is separate again and only
appears in `DATABASE_URL`.

---

## Testing: worked examples

### 1. Get tokens

Magic link is the production flow, but for testing, create users in the Supabase dashboard
(Authentication → Users → Add user, with a password) and exchange credentials for a JWT:

```bash
curl -X POST 'https://<PROJECT-REF>.supabase.co/auth/v1/token?grant_type=password' \
  -H "apikey: <anon-or-publishable-key>" \
  -H "Content-Type: application/json" \
  -d '{"email":"usera@test.com","password":"<password>"}'
```

The response contains `access_token` — that is the JWT. Do it twice, for two users.

The backend does not care *how* a token was obtained; it only verifies the signature. So a
password-grant token tests the magic-link flow perfectly well.

```bash
TOKEN_A="<host token>"
TOKEN_B="<guest token>"
BASE="localhost:8000/api/v1"
```

> Tokens expire after 1 hour (`expires_in: 3600`). If requests that worked start returning
> 401, the token aged out — fetch a fresh one. That is not a bug in the guards.

### 2. The full sequence

**Create an event as the host** → 200
```bash
curl -X POST $BASE/events \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Wedding","event_date":"2026-08-01","expires_at":"2026-09-01T00:00:00Z"}'
```
```json
{"id":"8d2ec22d-...","host_id":"cc308900-...","name":"Test Wedding","status":"active",...}
```
This single request exercises the whole stack: JWKS verification → `sub` parsed to UUID →
`get_or_create_user` bridges the identity → event inserted → host invitation row created.
Note `host_id` matches the token's `sub`.

```bash
EVENT_ID="8d2ec22d-..."
```

**Reject a bad token** → 401
```bash
curl -X POST $BASE/events \
  -H "Authorization: Bearer not-a-real-token" \
  -H "Content-Type: application/json" \
  -d '{"name":"Nope","expires_at":"2026-09-01T00:00:00Z"}'
```

**Host lists own events** → 200
```bash
curl $BASE/events -H "Authorization: Bearer $TOKEN_A"
```

**Host reads the event** → 200
```bash
curl $BASE/events/$EVENT_ID -H "Authorization: Bearer $TOKEN_A"
```

**Non-member reads the event** → **403** ← the test that matters
```bash
curl $BASE/events/$EVENT_ID -H "Authorization: Bearer $TOKEN_B"
```
```json
{"detail":"Not a member of this event"}
```
A 200 here would mean anyone can read anyone's event. With no RLS backstop, this guard is the
only defense.

**Non-host tries to invite** → 403
```bash
curl -X POST $BASE/events/$EVENT_ID/invitations \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" -d '{"email":"guest@test.com"}'
```
```json
{"detail":"Not the host of this event"}
```

**Host creates an invitation** → 200
```bash
curl -X POST $BASE/events/$EVENT_ID/invitations \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" -d '{"email":"guest@test.com"}'
```
```json
{"id":"6b95d414-...","status":"pending","invite_link":"http://localhost:5173/join/MfjfKuv7..."}
```
```bash
INVITE_TOKEN="MfjfKuv7..."
```

**Guest claims it** → 200
```bash
curl -X POST $BASE/invitations/$INVITE_TOKEN/claim -H "Authorization: Bearer $TOKEN_B"
```
```json
{"id":"09b6b699-...","invite_token":"INotn9yp...","user_id":"f9de8e60-...","role":"guest","status":"joined"}
```
Note: a **new** row with its own `id` and a **fresh** `invite_token` — not the shared token
that was claimed with. The shared invitation stays `pending` for the next guest. Also note
`user_id` is user B's — `get_or_create_user` silently bridged their identity on their first
authenticated request; nobody inserted that row by hand.

**Guest reads the event now** → **200** ← the payoff
```bash
curl $BASE/events/$EVENT_ID -H "Authorization: Bearer $TOKEN_B"
```
Identical request to the 403 above. Same user, same token, same URL. Only a database row
changed. This is the proof that authorization reads live state rather than faking it.

**Double claim** → 409
```bash
curl -X POST $BASE/invitations/$INVITE_TOKEN/claim -H "Authorization: Bearer $TOKEN_B"
```
```json
{"detail":"Already a member of this event"}
```

### 3. Shell gotchas (Git Bash)

- JSON bodies need **single quotes outside, double quotes inside**:
  `-d '{"name":"Test Wedding"}'`. Without the single quotes, bash splits on the space and
  curl receives fragments (you will see a JSON decode error plus "URL rejected" errors).
- No spaces around `=` in variable assignment.
- Paste with right-click or Shift+Insert; Ctrl+V often does not work in MinTTY.

`http://localhost:8000/docs` (Swagger UI) is often easier: click Authorize, paste a token
once, then click through the endpoints. Swap the token to act as the other user.

---

## Debugging notes

**A generic error message costs debugging time.** "Invalid or expired token" was true from
the client's perspective but useless internally — a `MissingCryptographyError` (a missing
dependency) looked identical to an expired token. This is why the real exception is now
logged. Vague to the caller, specific in the logs.

**When an HTTP layer swallows an exception, drop below it.** Calling the function directly
with the same input surfaces the full traceback, including the chained cause:

```bash
docker compose exec backend python -c "
from app.auth.supabase import verify_token
verify_token('<token>')
"
```

**Common failure modes:**

| Symptom | Likely cause |
| --- | --- |
| 401 on every request | Container running stale code — rebuild: `docker compose up -d --build backend` |
| 401 after previously working | Token expired (1 hour) — fetch a fresh one |
| `ModuleNotFoundError` in container | New files not in the image — rebuild |
| 500 with `ForeignKeyViolationError` on `users` | Identity bridge not running — see `get_or_create_user` |
| `MissingCryptographyError` | `pyjwt[crypto]` not installed |

---

## Known simplifications / future work

- **Get-or-create on every request** rather than a Supabase signup webhook. Cheap (a PK
  lookup on an already-borrowed session), but a webhook would be cleaner at scale.
- **No row locking on claim.** Made moot by the insert-a-new-row model — concurrent claims
  are independent inserts, with `UNIQUE(event_id, user_id)` as the backstop.
- **`display_name`** currently falls back to the email (the JWT carries no name claim). Would
  come from `user_metadata` if the signup flow collected one.
- **No RLS.** Deliberate — this backend owns authorization. Noted here because it raises the
  stakes on `guards.py`.