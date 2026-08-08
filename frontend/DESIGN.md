# FaceFolio — Design System

The design contract for the frontend. Every color, font, spacing value, radius, and
component style comes from here. If a value isn't in this system, it doesn't go in the
UI. Consistency is the whole point — a small set of tokens applied rigorously is what
separates intentional design from generated-looking design.

## Aesthetic direction

Calm, warm, editorial. FaceFolio is a place people go to find photos of themselves
from an event — a wedding, a conference, a party. The mood is unhurried and human,
not corporate-SaaS and not flashy-consumer. The palette is deliberately muted and
earthy (sage greens, warm greys) so the interface recedes and the PHOTOS carry the
visual richness. The UI is the frame; the pictures are the art.

Three principles:
1. **The photos are the color.** The chrome is desaturated on purpose. Never add
   decorative color that competes with photo thumbnails.
2. **Space over ornament.** Hierarchy comes from generous whitespace and type scale,
   not from borders-everywhere, cards-on-cards, or decorative graphics.
3. **Quiet confidence.** Interactions are crisp and immediate. Nothing floats, glows,
   or drifts.

## Color tokens

All colors are defined as CSS variables and consumed through Tailwind. Never write a
raw hex in a component.

### Brand
```
--color-primary        #777C6D   sage — primary actions, key accents, active states
--color-primary-hover  #656A5C   darker sage — hover on primary
--color-secondary      #B7B89F   light sage — secondary fills, subtle highlights
```

### Surfaces & neutrals
```
--color-background     #EEEEEE   the canvas / page background
--color-surface        #FFFFFF   cards, modals, dropdowns, inputs — elevated content
--color-surface-muted  #CBCBCB   table headers, subtle section separation, disabled fills
--color-border         #D4D4D4   dividers and hairlines between sections
```

### Text ("on" colors)
```
--color-text-primary    #2A2C26   headings and body — near-black with a warm green undertone, never pure #000
--color-text-secondary  #5A5D52   subtitles, timestamps, supporting copy — readable, never faint
--color-text-disabled   #9A9C90   inactive inputs, unclickable controls
--color-on-primary      #FFFFFF   text/icons on a sage (primary) background
```

### Status & feedback (muted to sit with the desaturated base)
```
--color-success     #5F7D52   earthy green — completed processing, confirmed match
--color-success-bg  #E8EFE3
--color-info        #5B7A8C   muted slate-blue — neutral tips, active filters
--color-info-bg     #E5ECEF
--color-warning     #B08947   muted ochre — non-blocking alerts (e.g. some uploads failed)
--color-warning-bg  #F5EDDE
--color-danger      #A6534A   muted brick — errors, destructive actions
--color-danger-bg   #F2E3E1
```

### Interactive
```
--color-focus-ring   #777C6D           keyboard focus outline (:focus-visible), full opacity
--color-scrim        rgba(42,44,38,.5)  modal/dialog backdrop, tinted to match the palette
hover tint: primary at ~8% opacity for subtle hover fills
```

Status colors are intentionally desaturated. A pure #22C55E green or #0EA5E9 blue would
look imported from a different design — the muted versions above read as
success/info/warning while belonging to this palette.

## Typography

Two fonts, each with a job.

- **Capriola** (`--font-heading`) — headings, the wordmark, section titles, numbers
  that matter (photo counts, match counts). Rounded and characterful; it carries the
  brand. Do NOT use it for body copy or small UI text — it tires at small sizes.
- **Plus Jakarta Sans** (`--font-body`) — everything else: body, labels, buttons,
  inputs, captions. Clean, humanist, legible at every size. Its slight warmth
  harmonizes with Capriola's roundness.

```
--font-heading  "Capriola", sans-serif
--font-body     "Plus Jakarta Sans", system-ui, sans-serif
```

Weights (Plus Jakarta Sans): 400 regular, 500 medium, 600 semibold, 700 bold.
Capriola ships a single regular weight — that's fine, headings use size and the font's
inherent character for presence, not extra weight.

Type scale (use these, don't improvise sizes):
```
display   36px / 1.1   Capriola          hero / page title
h1        28px / 1.2   Capriola          primary section heading
h2        22px / 1.25  Capriola          sub-section
h3        18px / 1.3   Plus Jakarta 600  card title, group label
body      16px / 1.6   Plus Jakarta 400  default paragraph and UI text
small     14px / 1.5   Plus Jakarta 400  captions, secondary
tiny      12px / 1.4   Plus Jakarta 500  labels, metadata, badges
```

- Headings track slightly tight: letter-spacing -0.01em on Capriola display/h1.
- Body copy uses --color-text-secondary for supporting text, --color-text-primary for
  primary reading — never a fainter grey than text-secondary.

## Spacing

Strict 8px-based rhythm. Every margin, padding, and gap is one of these:
```
4, 8, 12, 16, 24, 32, 48, 64, 96   (px)
```
No arbitrary values (no 13px, no 27px). Section-to-section vertical gap on desktop is
64–96px. Card interior padding is 24px. Related items sit 8–16px apart; distinct groups
32–48px. Whitespace is the primary tool for hierarchy — use it generously before
reaching for a border.

## Radius

```
--radius-interactive  6px    buttons, inputs, small controls — crisp, not bubbly
--radius-container    12px   cards, modals, image tiles
```
No fully-rounded (pill) shapes except intentionally for tags/badges. No inconsistent
corner rounding within a view.

## Borders & elevation

- Separate sections with a 1px `--color-border` line rather than stacking alternating
  background blocks.
- Elevation is expressed with a subtle, single, soft shadow ONLY where genuinely
  needed (an open modal, a dropdown) — never on static cards to make them "pop," and
  never as a glow. Prefer a border to a shadow for resting states.
- Modals sit above a `--color-scrim` backdrop.

## Interaction

- Hover: an immediate, solid change (background swaps to primary-hover, or a subtle
  hover-tint fill). No slow fades — transitions are fast (100–150ms) or instant.
- Focus: a visible `--color-focus-ring` outline on :focus-visible for every
  interactive element. Keyboard users must always see where they are.
- Buttons: tight padding — 12px vertical, 20–24px horizontal. Primary = sage fill,
  white text. Secondary = surface fill, border, text-primary. Never more than one
  primary button competing in a single view.
- Loading: a simple spinner or skeleton in the palette. No bouncing, no shimmer
  rainbows.

## Anti-slop directives (what makes UI look generated — avoid)

- **No decorative gradients.** Especially no purple/indigo/pink gradients on
  backgrounds or buttons. Flat fills only. (A single subtle same-hue gradient is
  acceptable only if it ever encodes real meaning, which it won't here.)
- **No glows or fake lighting.** No box-shadow used as a glow, no radial-gradient
  "orbs" floating in backgrounds, no glowing text.
- **No filler illustrations or abstract geometric SVG shapes** to occupy empty space.
  Empty states use a single lucide icon + a clear line of text. The photos and the
  typography are the visual interest.
- **No spacing guesswork.** Every value comes from the 8px scale.
- **No font-weight soup.** Two weights of body text in a view is plenty; more reads as
  indecision.
- **No icon-style mixing.** All icons come from lucide-react (consistent stroke).
  Never mix icon sets.
- **No pure black (#000) or pure faint grey text.** Use the defined text tokens.
- **No emoji anywhere in the UI** — not in headings, buttons, empty states, toasts, or
  copy. Emoji render inconsistently across platforms and read as generated/casual.
  Use lucide-react icons for visual cues and plain text for everything else.

## Responsive

- Mobile-first is natural for this product — guests use phones at events.
- Below 768px: stack layouts vertically; the gallery goes to a tighter grid (2 columns)
  but keeps comfortable edge padding (min 16px) — don't crowd the screen edges.
- Touch targets are at least 44px.

## Accessibility

- Every text/background pair meets WCAG AA contrast. The text tokens above are chosen
  to pass on their intended surfaces; verify any new pairing.
- Every interactive element is keyboard-reachable with a visible focus ring.
- Images have alt text; icon-only buttons have aria-labels.
- Consent language for facial recognition is explicit and plain — never buried or
  pre-checked.
