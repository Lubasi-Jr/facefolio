# FaceFolio Frontend

The React + TypeScript web client for FaceFolio. A pure client of the backend HTTP
API (see ../backend/app/schemas/ and ../backend/docs/ for contracts). Solo learning
project — prefer clear, conventional, well-explained code over clever abstractions.

Design is governed by DESIGN.md in this folder. Read it before building any UI. Every
color, font, spacing value, and component style comes from the tokens defined there —
never hardcode a hex value or a pixel spacing that isn't in the system.

## Stack (do not substitute without asking)

- React 18 + TypeScript (strict mode), built with Vite (client-rendered SPA)
- React Router for routing (not file-system routing)
- TanStack Query for all server state (fetching, caching, polling)
- Tailwind CSS for styling, configured with the DESIGN.md tokens
- lucide-react for icons (never hand-managed SVG icon files — consistent stroke
  weight is part of the design system)
- Supabase JS client for AUTH ONLY (signInWithOtp, session/token). NEVER for database
  queries — all data goes through the backend API.
- Tailwind CSS v3 (NOT v4 — v4 ignores tailwind.config.ts and the @tailwind directives). Styling depends on a non-empty postcss.config.js with `tailwindcss: {}` and `autoprefixer: {}`. If utilities silently don't apply, check `npm list tailwindcss` shows 3.x and that postcss.config.js is populated.
- Zustand for transient client state that isn't server state (e.g. the upload queue
  of files in flight). TanStack Query owns server state; Zustand owns local UI state
  that's too complex for useState. Do not use it for data that lives on the backend.

## Architecture principles

- The frontend never talks to the database, and never to Supabase Storage's data
  plane except to PUT bytes to a presigned URL the backend issued. All reads and all
  authorization go through the backend API.
- Supabase is the identity provider. The Supabase client owns the session and
  refreshes the JWT proactively in the background. Our API client reads the current
  token from the Supabase session on EVERY request (never caches a token) and sends it
  as `Authorization: Bearer <token>`.
- Uploads are direct-to-storage: call the backend prepare endpoint for presigned URLs,
  PUT files straight to Supabase Storage, then call confirm. No server code of ours
  ever touches file bytes.
- Server state (events, photos, processing status) lives in TanStack Query, not in
  local component state. Poll processing-status while a batch is processing; stop when
  every photo is processed or failed.
- Bulk uploads use a BOUNDED concurrency pool (~5 in flight), never an unbounded
  Promise.all. This is built in Phase 9.

## Folder structure (feature-based)

```
src/
  app/            # app-wide setup: providers.tsx (Query + Router + Auth), router.tsx
  features/       # product logic by domain: auth/, events/, upload/, enrollment/, gallery/
    <feature>/
      api/        # network calls for this feature
      components/ # UI specific to this feature
      hooks/      # TanStack Query hooks + logic for this feature
      types.ts    # types for this feature
      index.ts    # public surface of the feature
  components/
    ui/           # truly global primitives (Button, Input, Modal, Spinner)
    layouts/      # structural wrappers (AppLayout, GuestLayout)
  hooks/          # global hooks (useDebounce, etc.)
  lib/            # initialized clients: api.ts, supabase.ts
  utils/          # pure helpers (formatDate, etc.)
  assets/         # fonts, the rare image
  main.tsx
```

Structure conventions (pragmatic, not dogmatic — this is a solo project):
- Prefer importing a feature's things from its `index.ts`, not deep internal paths.
  This is a soft convention for tidiness, not a hard-enforced wall.
- Before putting something in the global `components/ui/` or `utils/`, check it's
  genuinely used by more than one feature. One-feature things stay in that feature.
- Use the `@/` path alias (configured in tsconfig + vite) — never `../../../` chains.

## Layering

- `lib/api.ts` — the single API client. Attaches the Bearer token, sets the base URL,
  centralizes error handling. Components and hooks never call fetch directly; they go
  through this.
- `lib/supabase.ts` — the Supabase client, auth only.
- `features/*/hooks/` — TanStack Query hooks wrapping API calls (useEvent,
  useUploadPhotos, useProcessingStatus, useEnroll). Components consume hooks.
- Components are presentational; logic lives in hooks.

## Conventions

- TypeScript strict. Type every API response explicitly against the feature's types,
  mirroring the backend Pydantic schema.
- Config via Vite env vars (import.meta.env.VITE_*): API base URL, Supabase URL,
  Supabase publishable key. Never hardcode. Never the service key.
- Handle the three states of every async view: loading, error, empty. A gallery
  mid-processing is a normal state, not an error.
- Keep components focused; extract logic into hooks.

## Cross-cutting contracts (from the backend)

- Invitation route is `/join/:token` — the backend builds links with this exact path.
- API base URL in dev: http://localhost:8000/api/v1.
- Enrollment consent: collect explicit facial-recognition consent before calling
  enroll; send the consent flag true. No consent, no enroll.
- Enroll selfie key: Supabase's upload response prepends the bucket name to the key,
  but the backend expects it WITHOUT the bucket prefix
  (events/{event_id}/enrollments/{user_id}.webp, not event-media/events/...). Strip
  the bucket prefix, or construct the key from event_id + user_id, before sending it
  to enroll.

## Working style with me

- I run prompts one small unit at a time, to learn as I go. Do NOT scaffold ahead or
  create files I did not ask for.
- When you generate non-trivial logic (the upload concurrency pool, the token flow,
  polling), add a short explanation of what it does and why.
- If a prompt needs a design decision I haven't specified, ask rather than guess.
- After changes, tell me how to verify (what to run, what to click).
- Do not add dependencies without saying so and why.

## Things NOT to do

- Do not use the Supabase client for database queries (supabase.from(...)). Auth only.
- Do not put the Supabase service key anywhere in the frontend.
- Do not cache the JWT; read it fresh from the Supabase session per request.
- Do not call fetch directly in components; go through lib/api.ts.
- Do not fire unbounded concurrent uploads; use the bounded pool (Phase 9).
- Do not hardcode colors, spacing, or fonts; use the DESIGN.md tokens via Tailwind.
- Do not add decorative gradients, glows, drop-shadow "floating" effects, or generic
  filler illustrations. See DESIGN.md.
- No emoji in UI or in generated copy. Use lucide-react icons and plain text.
- Do not route direct-to-storage uploads (PUT to a Supabase signed URL) through
  lib/api.ts. Those are raw fetch calls — they carry no JWT and go to a different
  origin. lib/api.ts is ONLY for calls to our own backend.