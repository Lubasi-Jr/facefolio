# FaceFolio — system flows

How data moves through the database, traced end to end with concrete examples.
Companion to `schema.sql` (which defines the structure this document exercises).

Read this to understand *why* the schema is shaped the way it is: each table exists
to serve one of these flows.

---

## Table roles at a glance

| Table | Purpose |
| --- | --- |
| `users` | A person. One row per human, reused across every event they touch. |
| `events` | One occasion. Owns a gallery. `expires_at` drives biometric deletion. |
| `invitations` | Invite token AND membership record. Carries `role` (host/guest) — this is where authorization lives. |
| `face_enrollments` | A guest's biometric baseline: their selfie as a 512-d vector, scoped to ONE event. |
| `photos` | An uploaded image. `status` walks the processing pipeline. |
| `faces` | One *detected face* within a photo. Five people in a group shot = five rows, each with its own vector. |
| `photo_tags` | The payoff: "user U appears in photo P". This is what "Photos of You" reads. |

**How they connect:** `events` is the hub — invitations, photos, enrollments, and
(denormalized) faces all carry an `event_id`, because *every meaningful query is
scoped to one event*. `photos` owns `faces`. `photo_tags` sits at the intersection
of `photos` and `users`.

---

## The cast (sample data used throughout)

| Entity | ID | Notes |
| --- | --- | --- |
| Thabo | `user-thabo` | The host |
| Naledi | `user-naledi` | Guest who enrolls AFTER photos are uploaded |
| Sipho | `user-sipho` | Guest who enrolls BEFORE photos are uploaded |
| Thabo's Wedding | `evt-1` | The event |
| A group photo | `photo-1` | Contains both Naledi and Sipho |

---

## Flow 1 — Host creates an event

Thabo signs in and creates his wedding gallery.

**Writes:**

```sql
INSERT INTO events
  (id, host_id, name, expires_at, status)
VALUES
  ('evt-1', 'user-thabo', 'Thabo''s Wedding', '2026-09-01', 'active');

INSERT INTO invitations
  (id, event_id, invite_token, user_id, role, status)
VALUES
  ('inv-1', 'evt-1', 'tok-abc123', 'user-thabo', 'host', 'joined');
```

**Reads:** none beyond verifying Thabo's identity from his JWT.

**Why two inserts:** the event row, *and* a host invitation row so Thabo is a member
with `role = 'host'`. That second row is what lets the authorization guard later
confirm "yes, Thabo may upload to evt-1". Every membership is an invitation row, so
hosts and guests are modeled uniformly.

---

## Flow 2 — Host invites guests

Thabo generates the shareable guest link behind the QR code.

**Write:**

```sql
INSERT INTO invitations
  (id, event_id, invite_token, user_id, role, status)
VALUES
  ('inv-2', 'evt-1', 'tok-guest-xyz', NULL, 'guest', 'pending');
```

**Key detail:** `user_id` is `NULL` and `status` is `pending`. This invitation isn't
tied to a person yet — it's a token encoded into a QR code that anyone at the wedding
can scan. It becomes tied to a specific guest only when claimed (Flow 4).

---

## Flow 3 — Host uploads photos

Thabo bulk-uploads 200 wedding photos. Tracing one: `photo-1`, containing Naledi and
Sipho. This is the flow with the richest sequence of state changes.

### 3a — Prepare (row created BEFORE the file exists)

```sql
INSERT INTO photos
  (id, event_id, uploader_id, original_key, status)
VALUES
  ('photo-1', 'evt-1', 'user-thabo',
   'events/evt-1/originals/photo-1.jpg', 'awaiting_upload');
```

The API returns a presigned URL. The browser uploads bytes straight to storage — the
database is not involved in the byte transfer. The row is the *plan*; the uploaded
object is the *fulfillment* of the plan.

### 3b — Confirm (browser reports the upload finished)

```sql
UPDATE photos SET status = 'queued' WHERE id = 'photo-1';
```

A Celery message carrying just `photo-1` goes onto the queue.

### 3c — Worker picks it up

```sql
UPDATE photos SET status = 'processing' WHERE id = 'photo-1';
```

### 3d — Worker detects and embeds faces

Two faces found. Delete-then-insert makes this idempotent under retry:

```sql
DELETE FROM faces WHERE photo_id = 'photo-1';

INSERT INTO faces
  (id, photo_id, event_id, bbox, det_score, embedding, crop_key)
VALUES
  ('face-1', 'photo-1', 'evt-1', '{120,80,60,60}', 0.98,
   '[0.021, -0.043, ...]', 'events/evt-1/faces/face-1.webp'),
  ('face-2', 'photo-1', 'evt-1', '{400,90,58,58}', 0.97,
   '[-0.011, 0.052, ...]', 'events/evt-1/faces/face-2.webp');
```

Two rows, each with its own 512-d `embedding`. `event_id` is denormalized onto each
face (see "Design notes" below for why). At this point these faces are **unknown** —
nobody is linked to them yet.

### 3e — Match against anyone already enrolled

```sql
SELECT user_id, embedding
FROM face_enrollments
WHERE event_id = 'evt-1';
```

Say nobody has enrolled yet (the wedding just ended, guests haven't scanned). Zero
rows, so no tags are written. The faces sit and wait. (Flow 5 shows what happens when
this returns rows.)

### 3f — Mark done, record derivatives

```sql
UPDATE photos
SET status = 'processed',
    web_key = 'events/evt-1/web/photo-1.webp',
    thumb_key = 'events/evt-1/thumbs/photo-1.webp',
    taken_at = '2026-08-15 16:32:00'
WHERE id = 'photo-1';
```

Multiply 3a–3f across 200 photos, running in parallel across workers. Result: 200
processed photos, a pile of `faces` rows with embeddings, all still unmatched.

### Progress polling (read, while all this runs)

```sql
SELECT status, count(*)
FROM photos
WHERE event_id = 'evt-1'
GROUP BY status;
```

Renders "412 of 500 processed, 2 failed" on the host's screen.

---

## Flow 4 — Guest onboards and gets their folder

The payoff flow. Naledi scans the QR code.

### 4a — Claim the invitation

The QR encodes `tok-guest-xyz`. Naledi authenticates, and claiming creates *her own*
membership row:

```sql
INSERT INTO invitations
  (id, event_id, invite_token, user_id, role, status)
VALUES
  ('inv-3', 'evt-1', 'tok-naledi-unique', 'user-naledi', 'guest', 'joined');
```

Now the authorization guard permits her to view and to enroll. `UNIQUE(event_id,
user_id)` guarantees she can't end up with two memberships for one event.

### 4b — Consent, then selfie upload

Naledi agrees to the explicit facial-recognition consent, and her selfie uploads to
storage via a presigned URL. No database write for the bytes. Key:
`events/evt-1/enrollments/user-naledi.webp`.

**Consent is not skippable and not buried.** No consent → no enrollment → no selfie
stored. `consented_at` is recorded at this moment (next step) and is what the purge
and any erasure request operate against.

### 4c — Embed the selfie, store the enrollment

```sql
INSERT INTO face_enrollments
  (id, event_id, user_id, selfie_key, embedding, quality_score, consented_at)
VALUES
  ('enr-1', 'evt-1', 'user-naledi',
   'events/evt-1/enrollments/user-naledi.webp',
   '[0.019, -0.041, ...]', 0.95, now());
```

This is Naledi's biometric baseline, scoped to this one event — the "known face" that
photos get matched against.

### 4d — The match query (the heart of the system)

Take her selfie vector, find which faces in this event it matches:

```sql
SELECT DISTINCT ON (f.photo_id)
       f.photo_id,
       1 - (f.embedding <=> :naledi_vec) AS similarity
FROM faces f
WHERE f.event_id = 'evt-1'
  AND f.embedding IS NOT NULL
  AND 1 - (f.embedding <=> :naledi_vec) >= 0.55
ORDER BY f.photo_id, f.embedding <=> :naledi_vec;
```

Returns, say, 15 photo_ids with similarities (photo-1 at 0.82, etc.).

- `<=>` is cosine *distance*, so similarity is `1 - distance`.
- `DISTINCT ON (photo_id)` + that `ORDER BY` keeps the **best-matching face per
  photo**, so a guest appearing twice in one frame still yields one result.
- `WHERE f.event_id` is the entire scoping mechanism: exact cosine search over a
  small, event-scoped set. No ANN index needed, guaranteed correct.

### 4e — Write the tags

```sql
INSERT INTO photo_tags
  (photo_id, user_id, face_id, similarity, status, source)
VALUES
  ('photo-1', 'user-naledi', 'face-1',  0.82, 'confirmed', 'auto'),
  ('photo-7', 'user-naledi', 'face-19', 0.79, 'confirmed', 'auto')
  -- ... 13 more rows ...
ON CONFLICT (photo_id, user_id) DO NOTHING;
```

The composite PK `(photo_id, user_id)` plus `ON CONFLICT DO NOTHING` guarantee exactly
one tag per photo per user, no matter how many faces matched her.

### 4f — Serve the two folders (reads)

Full gallery (everyone's photos):

```sql
SELECT id, web_key, thumb_key, taken_at
FROM photos
WHERE event_id = 'evt-1' AND status = 'processed'
ORDER BY taken_at DESC;
```

Her personal "Photos of You" folder:

```sql
SELECT p.id, p.web_key, p.thumb_key, p.taken_at
FROM photo_tags t
JOIN photos p ON p.id = t.photo_id
WHERE t.user_id = 'user-naledi'
  AND p.event_id = 'evt-1'
  AND t.status = 'confirmed'
ORDER BY p.taken_at DESC;
```

That second query — a plain indexed join — is the entire "magic feature" at the
database level. All the heavy lifting already happened; retrieval is trivial.

**Timing:** enrollment runs synchronously inside the HTTP request. Embedding one
selfie takes ~1–2s; the scoped query is milliseconds. So the guest sees a populated
folder in the same response. This is only possible because face embedding was already
done at upload time (Flow 3d).

---

## Flow 5 — The reverse ordering (guest enrolls BEFORE photos are processed)

Shows why matching must happen from both directions.

Sipho scans the QR during the reception, before Thabo uploads. He enrolls (Flow 4a–4c
writes his `face_enrollments` row), but the Flow 4d match query finds no faces yet:
zero tags, empty folder for now.

Later, Thabo uploads photo-1. This time the worker's step 3e check returns Sipho:

```sql
SELECT user_id, embedding FROM face_enrollments WHERE event_id = 'evt-1';
-- returns Sipho's row
```

So the worker matches photo-1's faces against Sipho's baseline. For each detected
face, it runs the scoped top-2 query against enrollments:

```sql
SELECT user_id, 1 - (embedding <=> :face_vec) AS similarity
FROM face_enrollments
WHERE event_id = 'evt-1'
ORDER BY embedding <=> :face_vec
LIMIT 2;   -- top-2 enables the margin test (Phase 11)
```

`face-2` matches Sipho at 0.80, so:

```sql
INSERT INTO photo_tags (photo_id, user_id, face_id, similarity, status, source)
VALUES ('photo-1', 'user-sipho', 'face-2', 0.80, 'confirmed', 'auto')
ON CONFLICT (photo_id, user_id) DO NOTHING;
```

Sipho's folder populates in near real-time as photos process.

### The two matching moments

| When | Direction | Covers |
| --- | --- | --- |
| **Photo-time** (Flow 3e) | New faces → existing enrollments | Guests who enrolled early |
| **Enrollment-time** (Flow 4d) | New enrollment → existing faces | Photos uploaded before the guest arrived |

Whichever of (photo processed, guest enrolled) happens **second** triggers the match.
So every guest–photo pair is evaluated exactly once, regardless of ordering. Same
`photo_tags` table, written from either side.

---

## Flow 6 — Event expires (biometric purge)

The wedding hits `expires_at`. The daily purge job runs.

**Read** the expired events:

```sql
SELECT id FROM events
WHERE expires_at < now() AND status = 'active';
-- returns evt-1
```

**Phase A — database (one transaction per event):**

```sql
BEGIN;
  UPDATE events SET status = 'expired' WHERE id = 'evt-1';

  DELETE FROM face_enrollments WHERE event_id = 'evt-1';

  UPDATE faces
  SET embedding = NULL, crop_key = NULL
  WHERE event_id = 'evt-1';
COMMIT;
```

Naledi's and Sipho's enrollment rows (selfies + baselines) are deleted outright. Every
face's `embedding` is nulled and `crop_key` cleared — *this is why those columns are
nullable*. The `faces` rows survive; a bounding box is not biometric data.

**Phase B — storage, then finalize:**

Delete every object under `events/evt-1/faces/` and `events/evt-1/enrollments/`, then:

```sql
UPDATE events SET status = 'purged' WHERE id = 'evt-1';

INSERT INTO deletion_log (event_id, categories, db_purged_at, storage_purged_at)
VALUES ('evt-1', '{enrollments,embeddings,crops}', ..., ...);
```

**Database first, storage second** — so even if storage deletion lags, no query in the
system can *use* the biometric data anymore.

### What survives, and why that's the elegant part

`photos`, `web_key`/`thumb_key` derivatives, and every `photo_tags` row are untouched.
So this still works perfectly after the purge:

```sql
SELECT p.id, p.web_key
FROM photo_tags t
JOIN photos p ON p.id = t.photo_id
WHERE t.user_id = 'user-naledi'
  AND p.event_id = 'evt-1'
  AND t.status = 'confirmed';
```

Naledi still opens her folder and sees her 15 wedding photos. The biometric data that
*created* those tags is gone, but a tag ("Naledi appears in photo-1") is ordinary
personal data, not biometric data.

**You destroy the ability to match new faces, not the results of past matches.**

### Individual erasure (POPIA s24 / GDPR Art. 17)

Same machinery, scoped to `(event_id, user_id)`: delete that user's enrollment and
selfie, null the embeddings on faces linked to their tags, delete their tags. The
untagged photos remain in the gallery.

---

## Design notes (the questions this schema answers)

### Why doesn't `photo_tags` have an `event_id`?

It doesn't need one. A tag belongs to one photo; that photo belongs to one event. The
event is already fully determined by `photo_id`. The folder query reaches it by
joining: `photo_tags.photo_id → photos.id → photos.event_id`. Note the `p.` prefix in
`WHERE p.event_id = 'evt-1'` — that column lives on the *joined* table.

Adding `event_id` to `photo_tags` would store the same fact twice and create the
possibility of disagreement (a tag claiming evt-15 while its photo says evt-1).

**It costs nothing** because the folder query joins to `photos` anyway — it needs
`web_key`, `thumb_key`, and `taken_at` from that table regardless. The event filter is
a free rider on a join that had to happen.

### Then why DOES `faces` have a denormalized `event_id`?

Two hot operations demand it:

1. The match query filters *thousands* of face rows: `WHERE f.event_id = :event_id`.
   Without the column it would join to `photos` every time just to filter — on the
   hottest query in the system.
2. The purge job runs `UPDATE faces SET embedding = NULL WHERE event_id = :event_id`.
   A direct filter beats a join-then-update, and deletion should be as unambiguous as
   possible.

**Rule of thumb:** normalize by default (derive through joins); denormalize only where
a specific hot query demands it. `faces` earned it; `photo_tags` didn't.

### Can a returning guest see photos from an old event?

No — and there are **two independent safeguards**, either of which alone would prevent
it. Say Naledi attends `evt-15` a month later:

1. **The read is event-scoped.** Her folder query has `AND p.event_id = 'evt-15'`. Her
   evt-1 tags still exist but join to photos with `event_id = 'evt-1'`, so they're
   excluded.
2. **The write path was event-scoped too.** Her evt-15 enrollment is a *separate row*
   (`UNIQUE(event_id, user_id)`), and matching only ever compares against
   `faces WHERE event_id = 'evt-15'`. Cross-event tags physically cannot be created.

She takes a fresh selfie for evt-15, so she has two enrollment rows — one per event —
each deleted independently when its own event expires. The `users` table gives her a
stable identity across events; `face_enrollments` keeps her biometrics siloed per event.

**Worth a test in Phase 7:** enroll one user in two events, confirm each folder shows
only its own photos.

### Why is enrollment per-event rather than global?

It's the load-bearing privacy decision. A guest attending three events takes three
selfies and has three enrollment rows. This gives:

- A clean deletion boundary: "delete all biometric data for event X" is well-defined.
- No permanent, cross-event face profile of anyone.
- Structural impossibility of cross-event contamination (see above).

Slightly worse UX; dramatically better compliance posture (POPIA s26/s27 special
personal information; GDPR Art. 9 biometric data).

---

## The through-line

**Writes concentrate the work early** — the expensive embedding happens at upload
time, and matching happens at enrollment time — so that **reads stay trivial**: the
personalized folder is one indexed join.

**Every query is scoped by `event_id`**, which is why that column appears on almost
every table (including denormalized onto `faces`). That scoping is what keeps the
system fast *and* what makes the per-event deletion boundary clean.

If you internalize one thing: **`photo_tags` is the product.** Everything else exists
to populate it correctly, then safely dismantle the biometric machinery that did so.
