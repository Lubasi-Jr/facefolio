# FaceFolio — UI Component Specs

Specs for the shared component foundation. Build in this order (each depends on the
ones above it). Every component uses ONLY the Tailwind tokens from DESIGN.md — no
hardcoded hex, no arbitrary spacing. All icons come from lucide-react. No emoji.

Build each as its own prompt. The spec for each is precise enough to hand to Claude
Code directly.

---

## 1. Button — `src/components/ui/Button.tsx`

The most-used primitive. Sets the interactive visual language.

**Variants:**
- `primary` — sage fill (`bg-primary`), white text (`text-on-primary`), hover
  `bg-primary-hover`. The main call-to-action. One per view, ideally.
- `secondary` — surface fill (`bg-surface`), `border border-border`, text
  `text-text-primary`, hover fills with a subtle sage tint (`hover:bg-background`).
- `ghost` — no fill, no border, `text-text-secondary`, hover `bg-background`. For
  low-emphasis actions (cancel, tertiary links-as-buttons).
- `danger` — `bg-danger`, white text, hover a shade darker. For destructive actions.

**Sizes:**
- `sm` — `px-4 py-2 text-small`
- `md` (default) — `px-6 py-3 text-body`
- `lg` — `px-8 py-4 text-body`

**Structure & behavior:**
- Props extend `React.ButtonHTMLAttributes<HTMLButtonElement>` so it accepts
  `onClick`, `type`, `disabled`, etc. natively.
- Additional props: `variant` (default 'primary'), `size` (default 'md'),
  `isLoading?: boolean`, `leftIcon?: React.ReactNode`, `fullWidth?: boolean`.
- `rounded-interactive`, `font-medium`, `font-body`.
- Transitions fast: `transition-colors duration-100`. No slow fades.
- Disabled: `bg-surface-muted text-text-disabled cursor-not-allowed`, and disabled
  when `isLoading` too.
- When `isLoading`, show a small spinner (lucide `Loader2` with `animate-spin`) in
  place of / alongside the label, and disable the button.
- `leftIcon` renders before the label with `gap-2`; icon size ~18px, inherits color.
- Focus: rely on the global `:focus-visible` ring from index.css (already sage). Do
  not add a custom ring.
- `fullWidth` → `w-full`.

**Implementation notes:**
- Use a small `clsx` or template-literal approach to compose variant/size classes.
  If clsx isn't installed, note it as a dependency (it's tiny and standard); or use a
  plain object lookup for variant→classes and size→classes.
- Export the component and its prop types.

**Do NOT:** add box-shadows, gradients, glows, or scale-on-hover transforms. The hover
is a solid color change, nothing else.

---

## 2. Card — `src/components/ui/Card.tsx`

The surface container for grouped content (an event, a form, a photo tile group).

**Spec:**
- `bg-surface`, `border border-border`, `rounded-container`.
- Default interior padding `p-6` (24px), overridable via a `padding` prop
  (`none | sm | md`) → `p-0 | p-4 | p-6`.
- Optional `as` prop to render as a different element (e.g. `<article>`), default
  `<div>`. Keep this simple — a plain prop, not a polymorphic-generic monster.
- Optional `interactive?: boolean` — when true, adds `hover:border-border-strong`
  (or `hover:border-text-disabled` for a subtle darkening) and `cursor-pointer` and
  `transition-colors duration-100`, for cards that are clickable (an event card that
  navigates). Default false (static card, no hover).
- Accepts and spreads `className` so callers can add layout (width, margin) without
  the component owning layout.
- NO shadow by default. Elevation is the border, not a shadow. (Shadows are reserved
  for overlays/modals only, per DESIGN.md.)

**Do NOT:** add a default shadow, gradient, or hover-lift transform.

---

## 3. Input + Label — `src/components/ui/Input.tsx` and `Label.tsx`

Extract the hand-rolled field from LoginPage into reusable primitives.

**Label (`Label.tsx`):**
- Renders a `<label>` with `text-small font-medium text-text-primary`.
- Props: `htmlFor` (required), children. Spreads the rest.

**Input (`Input.tsx`):**
- Props extend `React.InputHTMLAttributes<HTMLInputElement>`.
- Base: `rounded-interactive border border-border bg-surface px-4 py-3 text-body
  text-text-primary w-full`.
- Placeholder color: `placeholder:text-text-disabled`.
- Disabled: `disabled:bg-background disabled:text-text-disabled
  disabled:cursor-not-allowed`.
- Optional `error?: boolean` prop → `border-danger` when true.
- Focus: global `:focus-visible` ring handles it; don't add a custom one, but do
  ensure the border doesn't fight the ring (fine as-is).
- Forward the ref (`React.forwardRef`) so it works with form libraries later.

Optionally a small `Field` wrapper component that composes Label + Input + an optional
error message line (`text-small text-danger`) with `flex flex-col gap-2`. Nice-to-have;
build if it reads cleanly, skip if it adds complexity.

---

## 4. Spinner — `src/components/ui/Spinner.tsx`

Replaces "Loading..." text strings.

**Spec:**
- lucide `Loader2` with `animate-spin`, `text-text-secondary` (or `text-primary` for
  on-brand emphasis — pick text-secondary for neutral loading).
- `size` prop (`sm | md | lg`) → 16px / 24px / 32px.
- Optional `label?: string` — when provided, render the spinner and the label
  side by side (`flex items-center gap-2 text-body text-text-secondary`), e.g.
  "Loading events". No ellipsis animation, just the spinner conveys motion.
- A `center?: boolean` convenience → wraps in a `flex items-center justify-center`
  container with some vertical padding, for full-section loading states.

---

## 5. EmptyState — `src/components/ui/EmptyState.tsx`

For "no events yet" / "no photos yet" — the anti-slop empty state (icon + text, no
illustration).

**Spec:**
- Centered column: `flex flex-col items-center justify-center text-center gap-3 py-16`.
- Props: `icon: React.ReactNode` (a lucide icon, ~32px, `text-text-disabled`),
  `title: string` (`font-heading text-h3 text-text-primary`),
  `description?: string` (`text-body text-text-secondary max-w-sm`),
  `action?: React.ReactNode` (an optional Button, rendered below with `mt-2`).
- The icon sits in a subtle circle: a `rounded-full bg-background p-4` wrapper around
  the icon, for a bit of intentional structure. Keep it flat — no shadow.

**Do NOT:** use an illustration or decorative SVG. A single lucide icon plus text is
the whole visual.

---

## 6. AppLayout — `src/components/layouts/AppLayout.tsx`

The shell every authenticated page renders inside. THE single biggest visual change.

**Structure:**
```
<div min-h-screen bg-background flex flex-col>
  <header>                          ← sticky top, surface bg, bottom border
    <div max-w container, flex justify-between items-center, py-4>
      <wordmark: "FaceFolio" font-heading text-h2 text-primary>   (links to /events)
      <right side: user email (text-small text-text-secondary, hide on mobile)
                   + sign-out Button variant="ghost" size="sm">
    </div>
  </header>
  <main flex-1>
    <div max-w container, px + py>
      <Outlet />                    ← nested route content renders here
    </div>
  </main>
</div>
```

**Details:**
- Header: `bg-surface border-b border-border`. Optionally `sticky top-0 z-10` so it
  stays on scroll (nice for long galleries). Keep it thin — `py-4`.
- The content container and the header's inner container share the SAME max-width and
  horizontal padding so the wordmark aligns with the page content below. Use
  `max-w-5xl mx-auto px-4 sm:px-6` (or a shared constant/wrapper). This alignment is
  what makes it feel designed rather than thrown together.
- Main content gets generous vertical padding: `py-8` (or `py-12` on larger screens).
- Sign-out calls `signOut` from `useAuth`, then routing sends the user to /login
  (the auth state change + route guard handles the redirect).
- The wordmark is text, not an image — Capriola in sage IS the logo.
- Uses `<Outlet />` from react-router so nested routes render inside it.

**Do NOT:** add a sidebar (overkill for this app), a shadow under the header (the
border is the separator), or any decorative header background.

---

## 7. Wire the layout into routing — `src/app/router.tsx`

Nest the authenticated routes inside `AppLayout` so they all inherit the shell.

**Spec:**
- The protected routes (events list, event detail, upload, etc.) become children of a
  route whose `element` is `<AppLayout />` (which renders `<Outlet />`).
- Wrap that in whatever auth guard you already have (a `<RequireAuth>` or a check that
  redirects to /login if no session).
- `/login` and the guest `/join/:token` route stay OUTSIDE AppLayout — login is
  pre-auth, and the guest flow likely wants its own lighter layout (a GuestLayout can
  come later; for now /join can render bare or reuse AppLayout without the sign-out).
- Structure roughly:
  ```
  /login                    → LoginPage (no layout)
  /join/:token              → JoinPage (no AppLayout, or a minimal one)
  / (RequireAuth + AppLayout)
    /events                 → EventsPage
    /events/:id             → EventDetailPage (later)
    ...
  ```

---

## 8. Refit the existing pages

Now update LoginPage and EventsPage to use the primitives.

**LoginPage:**
- Replace the hand-rolled input with `<Input>` + `<Label>` (or `<Field>`).
- Replace the button with `<Button variant="primary" fullWidth isLoading={status ===
  'submitting'}>Send magic link</Button>`.
- Wrap the form panel in `<Card className="w-full max-w-sm">`.
- Keep it centered on the page (it's outside AppLayout).
- The success and error messages keep their `bg-success-bg`/`bg-danger-bg` styling.

**EventsPage:**
- Wrap each event in a `<Card interactive>` (clickable → navigates to the event).
- Replace "Loading events..." with `<Spinner center label="Loading events" />`.
- When there are no events, render `<EmptyState icon={<Calendar />} title="No events
  yet" description="Create your first event to start collecting photos." action={
  <Button>New event</Button>} />`.
- The "New event" button becomes `<Button leftIcon={<Plus size={18} />}>New event
  </Button>` — this fixes the cramped plus-icon you saw.
- Lay events out in a responsive grid or a clean vertical stack with `gap-4`.

---

## Dependency note

These specs assume `clsx` for conditional class composition (tiny, standard). If it
isn't installed, add it: `npm i clsx`. Alternatively use plain object lookups for
variant→class maps and avoid clsx entirely — either is fine, just be consistent.

lucide-react is already a dependency. Icons used above: Loader2, Plus, Calendar,
and (for empty states elsewhere) ImageOff, Camera, Upload.