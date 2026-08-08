-- =============================================================================
-- FaceFolio — Database Schema
-- =============================================================================
-- Event photo-sharing app. Hosts upload bulk photo galleries; guests take one
-- selfie and receive a personalized "Photos of You" folder built by facial
-- recognition and vector similarity search.
--
-- This file is a readable, runnable snapshot of the schema. It can be pasted
-- into the Supabase SQL Editor to stand up a fresh database. In the application
-- itself, schema is owned by Alembic migrations (this file mirrors migration 001).
--
-- Engine: PostgreSQL 16 + pgvector.
-- Face embeddings are 512-dimensional, L2-normalized, so cosine distance (<=>)
-- and inner product agree. Cosine SIMILARITY = 1 - (a <=> b).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Extensions
-- -----------------------------------------------------------------------------
-- vector : enables the vector(N) column type and distance operators (<->, <=>, <#>).
-- citext : case-insensitive text, used for emails so "A@x.com" == "a@x.com".
-- pgcrypto: provides gen_random_uuid() for primary keys. (On Supabase this is
--           usually available already; included here for portability.)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- -----------------------------------------------------------------------------
-- users
-- -----------------------------------------------------------------------------
-- A person. May host events and/or attend them as a guest. The same user row is
-- reused across every event they touch. Identity/auth is handled by Supabase Auth;
-- this table holds the application-level user record.
CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email         citext UNIQUE NOT NULL,      -- case-insensitive, one account per email
    display_name  text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);


-- -----------------------------------------------------------------------------
-- events
-- -----------------------------------------------------------------------------
-- A single occasion (wedding, conference, party) that owns a gallery of photos.
-- Relationship: users 1---* events, via host_id. A host owns their events.
--
-- expires_at is load-bearing: it drives the scheduled biometric purge. When an
-- event expires, all biometric data (face vectors, selfies, crops) is deleted
-- while the ordinary photos and tags are kept. status tracks that lifecycle.
CREATE TABLE events (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id       uuid NOT NULL REFERENCES users(id),
    name          text NOT NULL,
    event_date    date,
    expires_at    timestamptz NOT NULL,        -- when biometric data must be purged
    status        text NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'expired', 'purged')),
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- Partial index: the purge job only ever scans for still-active events that are
-- past their expiry, so we index just those rows, not the whole table.
CREATE INDEX idx_events_expiry
    ON events (expires_at)
    WHERE status = 'active';


-- -----------------------------------------------------------------------------
-- invitations
-- -----------------------------------------------------------------------------
-- The join between a user and an event, and also the membership record itself.
-- Relationship: events 1---* invitations.
--
-- The invitation IS the membership. It starts as 'pending' (an invite_token that
-- a QR code / link encodes, optionally an email), and flips to 'joined' with a
-- user_id once claimed. Modeling invite + membership in one table avoids keeping
-- two tables in sync.
--
-- role answers authorization ("can this user upload / delete, or only view?").
-- The role lives here on the server side; it is never taken from the request.
--
-- UNIQUE(event_id, user_id) stops a person being a member of one event twice.
CREATE TABLE invitations (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id      uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    invite_token  text UNIQUE NOT NULL,        -- encoded in the QR code / share link
    email         citext,                      -- optional; for known-email invites
    user_id       uuid REFERENCES users(id),   -- NULL until the invite is claimed
    role          text NOT NULL DEFAULT 'guest'
                  CHECK (role IN ('host', 'guest')),
    status        text NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'joined', 'revoked')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (event_id, user_id)
);

CREATE INDEX idx_invitations_event ON invitations (event_id);


-- -----------------------------------------------------------------------------
-- face_enrollments
-- -----------------------------------------------------------------------------
-- The biometric baseline for matching: a guest's selfie, embedded as a vector.
-- Relationship: keyed UNIQUE(event_id, user_id).
--
-- KEY DESIGN DECISION: enrollment is PER EVENT, not global. A user attending
-- three events has three enrollment rows and takes three selfies. This gives a
-- clean deletion boundary ("delete all biometric data for event X") and means the
-- system never builds a permanent, cross-event face profile of anyone — the
-- privacy/compliance-friendly posture (POPIA special personal information; GDPR
-- Article 9 biometric data).
--
-- The embedding here is biometric data, just like the selfie, and is destroyed
-- on event expiry by the purge job.
CREATE TABLE face_enrollments (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    selfie_key      text NOT NULL,             -- object-storage key of the selfie
    embedding       vector(512) NOT NULL,      -- L2-normalized face vector
    quality_score   real NOT NULL,             -- reject poor selfies at onboarding
    consented_at    timestamptz NOT NULL,      -- when explicit biometric consent was given
    UNIQUE (event_id, user_id)                 -- one baseline per guest per event
);

-- Scopes every match query to a single event's enrollments (a small candidate
-- set), so matching is an exact search over hundreds of vectors, never a global scan.
CREATE INDEX idx_enrollments_event ON face_enrollments (event_id);


-- -----------------------------------------------------------------------------
-- photos
-- -----------------------------------------------------------------------------
-- One uploaded event photo. Relationship: events 1---* photos.
--
-- status drives the async pipeline:
--   awaiting_upload -> queued -> processing -> processed | failed
-- The client polls counts of this column to show upload/processing progress.
--
-- original_key / web_key / thumb_key are object-storage keys for the raw upload
-- and its derivatives. taken_at comes from EXIF and orders galleries chronologically.
CREATE TABLE photos (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id      uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    uploader_id   uuid NOT NULL REFERENCES users(id),
    original_key  text NOT NULL,               -- storage key of the uploaded image
    web_key       text,                        -- ~1600px web derivative (set during processing)
    thumb_key     text,                        -- ~400px thumbnail (set during processing)
    width         int,
    height        int,
    taken_at      timestamptz,                 -- from EXIF; used for gallery ordering
    status        text NOT NULL DEFAULT 'awaiting_upload'
                  CHECK (status IN ('awaiting_upload', 'queued', 'processing',
                                    'processed', 'failed')),
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- Progress polling: "count photos in this event grouped by status".
CREATE INDEX idx_photos_event_status ON photos (event_id, status);
-- Gallery listing: newest-first within an event.
CREATE INDEX idx_photos_event_taken  ON photos (event_id, taken_at DESC);


-- -----------------------------------------------------------------------------
-- faces
-- -----------------------------------------------------------------------------
-- One detected face within a photo. Relationship: photos 1---* faces.
-- A group photo of five people yields five rows here. The FACE is embedded, not
-- the photo, so each row carries its own vector.
--
-- event_id is DENORMALIZED here (it is already reachable via photo_id -> photos).
-- This is deliberate: it lets the scoped match query and the purge job filter
-- faces by event directly, without joining through photos.
--
-- embedding and crop_key are NULLABLE on purpose. The purge job nulls the
-- embedding and clears crop_key on event expiry while KEEPING the row — the
-- bounding box (bbox) is not biometric and is harmless metadata. Nullable columns
-- are what make in-place biometric erasure possible without deleting the row.
CREATE TABLE faces (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_id      uuid NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    event_id      uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,  -- denormalized for scoping/purge
    bbox          int[] NOT NULL,              -- [x, y, w, h] face location (non-biometric)
    det_score     real NOT NULL,               -- detector confidence for this face
    embedding     vector(512),                 -- NULLABLE: set to NULL on biometric purge
    crop_key      text                         -- NULLABLE: face-crop storage key, cleared on purge
);

CREATE INDEX idx_faces_photo ON faces (photo_id);
-- Enrollment-time matching scans an event's faces for a newly enrolled selfie,
-- and the purge job filters faces by event — both use this index.
CREATE INDEX idx_faces_event ON faces (event_id);


-- -----------------------------------------------------------------------------
-- photo_tags
-- -----------------------------------------------------------------------------
-- The payoff table: "user U appears in photo P". This is what powers the
-- "Photos of You" folder. Relationship: links photos and users many-to-many.
--
-- COMPOSITE PRIMARY KEY (photo_id, user_id) enforces "a user appears at most once
-- per photo" at the database level — no matter how many faces in the photo matched
-- them (mirrors, duplicates), there is exactly one tag. Correctness by constraint,
-- not by application logic.
--
-- IMPORTANT: a tag is an ordinary personal-data assertion, NOT biometric data.
-- Tags SURVIVE the biometric purge, so the personalized-folder feature keeps
-- working after the face vectors that created it are deleted.
--
-- status: 'confirmed' (shown in the folder), 'pending_guest' (needs an
--         "Is this you?" confirmation from the guest), 'rejected' (guest said no).
-- source: how the tag arose — 'auto' (high-confidence match), 'guest_confirmed'
--         (guest accepted an uncertain match), 'host_action' (manual).
CREATE TABLE photo_tags (
    photo_id      uuid NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    face_id       uuid REFERENCES faces(id) ON DELETE SET NULL,  -- which face matched; kept loosely
    similarity    real NOT NULL,               -- cosine similarity of the match
    status        text NOT NULL DEFAULT 'confirmed'
                  CHECK (status IN ('confirmed', 'pending_guest', 'rejected')),
    source        text NOT NULL DEFAULT 'auto'
                  CHECK (source IN ('auto', 'guest_confirmed', 'host_action')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (photo_id, user_id)            -- at most one tag per (photo, user)
);

-- Powers the "Photos of You" query: a user's confirmed tags, one lookup.
CREATE INDEX idx_tags_user ON photo_tags (user_id, status);


-- =============================================================================
-- Relationship summary (for quick reading)
-- =============================================================================
--   users        1---*  events            (host_id)
--   events       1---*  invitations       (membership + invite token + role)
--   events       1---*  photos
--   photos       1---*  faces             (one row per detected face)
--   events/users *---1  face_enrollments  (one selfie baseline per guest PER EVENT)
--   photos/users *---*  photo_tags        ("photo P contains user U")
--
-- Data flow:
--   1. Host uploads a photo            -> photos row (awaiting_upload -> processed)
--   2. Worker detects + embeds faces   -> faces rows (vector per face)
--   3. Guest consents + submits selfie -> face_enrollments row (vector baseline)
--   4. Scoped cosine match, per event  -> photo_tags rows (the personal folder)
--   5. Event expires                   -> purge nulls face embeddings, deletes
--                                          enrollments + selfies + crops; KEEPS
--                                          photos and tags.
-- =============================================================================
