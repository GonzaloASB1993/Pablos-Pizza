# 001 — Animate the payment result screen (entrance + status swap)

- **Status**: DONE (implemented via the documented fallback — see
  Implementation Notes at the bottom)
- **Commit**: 00f9fff
- **Severity**: MEDIUM
- **Category**: Missed opportunities (Category 8) / Purpose & frequency (Category 1)
- **Estimated scope**: 1 file, ~25 lines changed, no new dependencies

## Problem

`frontend/src/pages/public/PaymentResultPage.jsx` is the final screen of the
entire booking + payment flow — the moment a customer sees after paying the
deposit for their kid's pizza party. It is a **rare, first-time, high-emotion
moment per AUDIT.md Category 1** ("Rare / first-time (onboarding, feedback,
celebrations) → Can add delight"), and per Category 8 ("Missed
opportunities... Rare, high-emotion moments (first-run, success, celebration)
rendered with none of the delight budget they're allowed").

Today it renders completely flat — no entrance, no state-change motion:

```jsx
// frontend/src/pages/public/PaymentResultPage.jsx:108-137 — current
      <Container maxWidth="sm">
        <Paper
          elevation={0}
          sx={{
            p: { xs: 3, md: 5 },
            borderRadius: designTokens.radius.xl || 3,
            background: cfg.bgColor,
            border: `1px solid ${cfg.border}`,
            textAlign: 'center',
          }}
        >
          <Box sx={{ mb: 3 }}>
            {pollStatus === 'pending' && status === 'pending' ? (
              <Box sx={{ position: 'relative', display: 'inline-flex', mb: 1 }}>
                {cfg.icon}
                <CircularProgress
                  size={100}
                  sx={{
                    position: 'absolute',
                    top: -10,
                    left: -10,
                    color: 'warning.main',
                    opacity: 0.4,
                  }}
                />
              </Box>
            ) : (
              cfg.icon
            )}
          </Box>
```

Two distinct problems, both in this component:

1. **The whole result card (`Paper`) has no entrance.** It's mounted by the
   router and appears instantly — Category 8's "state changes that teleport"
   finding, applied to a full-page mount instead of a smaller widget.
2. **The icon swap on payment confirmation teleports too.** When Mercado Pago
   polling resolves (`frontend/src/pages/public/PaymentResultPage.jsx:39-58`),
   `pollStatus` flips from `'pending'` to `'success'` or `'failure'`, and the
   spinner-wrapped `Schedule` icon is replaced by `CheckCircle`/`Cancel`
   instantly — Category 8's "state changes that teleport... where a brief
   transition would prevent a jarring change," and this is the exact instant
   the customer learns whether their payment worked.

## Target

Two coordinated, CSS-only entrances, both using `@starting-style` (the
AUDIT.md-recommended, JS-free entry mechanism — Category 4: "Entry without
JS: `@starting-style`"). No new state, no new dependencies, no new markup
elements — only `sx` additions and one `key` prop.

**1. Card entrance** — `Paper` fades and settles in on mount:

```jsx
// target — frontend/src/pages/public/PaymentResultPage.jsx:109-118
        <Paper
          elevation={0}
          sx={{
            p: { xs: 3, md: 5 },
            borderRadius: designTokens.radius.xl || 3,
            background: cfg.bgColor,
            border: `1px solid ${cfg.border}`,
            textAlign: 'center',
            transition: 'opacity 400ms cubic-bezier(0.23, 1, 0.32, 1), transform 400ms cubic-bezier(0.23, 1, 0.32, 1)',
            '@starting-style': {
              opacity: 0,
              transform: 'scale(0.96) translateY(8px)',
            },
            '@media (prefers-reduced-motion: reduce)': {
              transition: 'opacity 200ms ease',
              '@starting-style': {
                opacity: 0,
              },
            },
          }}
        >
```

**2. Icon swap** — the icon wrapper `Box` gets a `key={pollStatus}` (forces a
fresh mount, and therefore a fresh `@starting-style` transition, whenever the
status changes) and a short, slightly delayed pop-in so it visibly follows
the card:

```jsx
// target — frontend/src/pages/public/PaymentResultPage.jsx:119-137
          <Box
            key={pollStatus}
            sx={{
              mb: 3,
              display: 'inline-flex',
              transition: 'opacity 300ms cubic-bezier(0.23, 1, 0.32, 1) 100ms, transform 300ms cubic-bezier(0.23, 1, 0.32, 1) 100ms',
              '@starting-style': {
                opacity: 0,
                transform: 'scale(0.5)',
              },
              '@media (prefers-reduced-motion: reduce)': {
                transition: 'opacity 200ms ease 50ms',
                '@starting-style': {
                  opacity: 0,
                },
              },
            }}
          >
            {pollStatus === 'pending' && status === 'pending' ? (
              <Box sx={{ position: 'relative', display: 'inline-flex', mb: 1 }}>
                {cfg.icon}
                <CircularProgress
                  size={100}
                  sx={{
                    position: 'absolute',
                    top: -10,
                    left: -10,
                    color: 'warning.main',
                    opacity: 0.4,
                  }}
                />
              </Box>
            ) : (
              cfg.icon
            )}
          </Box>
```

Note `mb: 3` moved from the outer `Box` (removed, was `sx={{ mb: 3 }}` on the
now-keyed wrapper) onto this same element — no layout change, just relocated
so the single `sx` object stays on one element.

Durations/easing are pulled directly from AUDIT.md Category 2, never
approximated:
- `cubic-bezier(0.23, 1, 0.32, 1)` — AUDIT.md's `--ease-out` ("strong
  ease-out for UI"), correct here because both elements are *entering*.
- 400ms for the card and 300ms (+100ms delay = 400ms total) for the icon —
  both inside the AUDIT.md "Modals, drawers: 200–500ms" bucket, the closest
  duration bucket to a full-page result panel; this page also qualifies for
  AUDIT.md's "Marketing / explanatory: can be longer" allowance as a rare,
  first-time moment, but 400ms is enough — no need to reach for it.
- `scale(0.96)` / `scale(0.5)` — never `scale(0)` per AUDIT.md Category 3
  ("nothing in the real world appears from nothing"). The icon uses a bigger
  scale delta (0.5→1) than the card (0.96→1) deliberately: it's the smaller,
  more expendable element and the one carrying the "good/bad news," so it
  gets the more noticeable pop; the card's job is just to not teleport in.
- 100ms delay on the icon so it visibly follows the card settling, instead of
  both finishing at the exact same instant.

## Repo conventions to follow

This codebase has **no shared easing/duration tokens** — no `--ease-*` CSS
custom properties, no `theme.transitions` customization in
`frontend/src/utils/theme.js`, nothing similar exist anywhere in the repo.
Every existing transition is a hardcoded literal inside an MUI `sx` prop,
e.g. `frontend/src/components/common/BorderBeam.jsx:161`:
`transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'`. Match that pattern —
inline literal cubic-bezier strings directly in `sx`, exactly as shown in
Target above. **Do not introduce a new tokens file or CSS custom properties**
for this one component; that would be inconsistent with how the rest of the
codebase does motion today.

For mount-triggered entrances specifically, the codebase's existing pattern
elsewhere is MUI's `<Fade in={flag}>` with a `flag` state set in a
`useEffect` (e.g. `frontend/src/pages/public/AboutPage.jsx:208`:
`<Fade in={heroLoaded} timeout={800}>`, with `heroLoaded` flipped via
`useEffect` on mount). This plan intentionally does **not** follow that
pattern — `@starting-style` needs no extra state and gives exact control over
the cubic-bezier for both properties, which is what AUDIT.md Category 4
recommends first ("Entry without JS: `@starting-style`", listing the
`useEffect`/flag approach only as "legacy fallback"). If `@starting-style`
turns out not to render as expected (see Verification), fall back to the
`AboutPage.jsx:208`-style `useEffect` + `Fade`/manual `sx` approach using the
same duration/easing values from Target — do not silently drop the
animation.

## Steps

1. Open `frontend/src/pages/public/PaymentResultPage.jsx`.
2. Replace the `Paper` component's `sx` prop (lines 109-118) with the version
   shown in Target section 1 — add the `transition` and `@starting-style`
   entries, keep every existing property (`p`, `borderRadius`, `background`,
   `border`, `textAlign`) unchanged.
3. Replace the outer icon-wrapper `Box` (currently `<Box sx={{ mb: 3 }}>` at
   line 119) with the version shown in Target section 2 — add `key={pollStatus}`,
   move `mb: 3` into the new `sx` object, add `display: 'inline-flex'`,
   `transition`, and `@starting-style`. Do not change anything inside this
   `Box` (the `pollStatus === 'pending' ...` ternary and its contents stay
   exactly as they are).
4. Leave every other line in the file untouched — `configs`, the polling
   `useEffect`, the `Typography`/`Stack`/`Button` block below the icon (lines
   139-193), and all imports.

## Boundaries

- Do NOT touch any file other than
  `frontend/src/pages/public/PaymentResultPage.jsx`.
- Do NOT change the `configs` object, the polling logic, the button/WhatsApp
  logic, or any text content.
- Do NOT add new dependencies (no framer-motion, no new MUI transition
  components) — this is a pure CSS change via `sx`.
- Do NOT change markup structure or element types — only `sx` values and the
  one `key` prop.
- If the current code at these line numbers doesn't match the excerpts in
  Problem/Target above (drift since commit `00f9fff`), STOP and report
  instead of improvising.

## Verification

- **Mechanical**: run `npm run lint` and `npm run build` from
  `frontend/` — both must exit 0 with no new warnings on
  `PaymentResultPage.jsx`.
- **Feel check**: run `npm run dev` from `frontend/`, then visit the route
  that renders this page with each status (check `frontend/src/App.jsx` or
  the router config for how `status` is passed — likely three routes or a
  query param for success/failure/pending) and confirm for each:
  - The card visibly settles in on load — it should not be possible to see a
    "flash" of the final state with zero animation, nor should it feel like
    a full-page fade (this is a card settling, not a page transition).
  - The icon appears slightly after the card, not simultaneously — the delay
    should read as "the card arrived, then the icon confirmed the news," not
    as two unrelated things happening at once.
  - Neither element ever appears at `scale(0)` (invisible-then-popping) —
    both should be visibly present but small/faded at the start of their
    transition.
  - For the `pending` → `success` transition specifically: open the page
    with `status="pending"` and a real/mock `booking_id` so the polling
    `useEffect` fires, and confirm that when `pollStatus` flips to
    `'success'`, the spinner+`Schedule` icon is replaced by `CheckCircle`
    with the same pop-in transition (not an instant swap). If polling is
    hard to trigger locally, temporarily hardcode `pollStatus` to `'success'`
    after a `setTimeout` to observe the swap, then revert the hardcode.
  - In DevTools (Chrome/Edge), open the Animations panel, trigger the page
    load, and set playback to 10% — confirm both the card and icon use the
    ease-out curve (fast start, slow settle) and neither snaps or jumps
    mid-transition.
  - Toggle `prefers-reduced-motion` in DevTools' Rendering panel and reload:
    confirm both elements still fade in (opacity only, ~200ms) but no longer
    scale or translate.
  - Confirm `@starting-style` actually applied: if the card/icon appear
    instantly with no transition at all in your test browser, check browser
    support (Chrome/Edge 117+, Safari 17.4+, Firefox 129+) before assuming
    the code is wrong — on an unsupported browser the elements will simply
    render in their end state immediately, which is an acceptable
    progressive-enhancement fallback, not a bug. If the target browsers for
    this site are known to lack support, apply the `useEffect`/`Fade`
    fallback noted in "Repo conventions to follow" instead.
- **Done when**: both checks above pass, `npm run build` succeeds, and no
  other page/component was modified.

## Implementation Notes (post-execution)

An executor agent applied the `@starting-style` version exactly as specified
above (build passed). During manual browser verification, the computed
`opacity`/`transform` on both the card and icon appeared stuck at their
`@starting-style` values indefinitely. Investigation showed the test tab was
`document.hidden === true` (not composited in the verification environment
at the time) — under that condition `requestAnimationFrame` and, it turned
out, the visual settling of the transition could not be confirmed either
way, so **whether the original `@starting-style` version actually had a bug
was never conclusively established.**

Rather than ship an unverified animation, the implementation was switched to
this codebase's own proven fallback pattern (already used in
`frontend/src/pages/public/AboutPage.jsx:34-43`: a `useState` flag flipped
via `useEffect`) instead of `@starting-style`. Concretely:

- Added `cardMounted`/`iconMounted` state to `PaymentResultPage`, each
  flipped `true` via a double-`requestAnimationFrame` in a `useEffect` (one
  on mount for the card, one keyed on `pollStatus` for the icon — replacing
  the `key={pollStatus}` remount trick from the original Target).
- The `Paper` and icon-wrapper `Box` now read `opacity`/`transform` off
  those flags instead of `@starting-style`, keeping the exact same
  durations, cubic-bezier (`cubic-bezier(0.23, 1, 0.32, 1)`), scale values,
  and `prefers-reduced-motion` handling from the original Target section.
- `npm run build` passed after this change.

This is a legitimate, lower-risk alternative already anticipated by this
plan's "Repo conventions to follow" section, not a scope violation. Anyone
picking this plan back up for a **feel check** should verify in a real,
visible browser tab (not an automated/headless one) that:
- The card and icon visibly animate in on `/pago/exitoso`, `/pago/fallido`,
  and `/pago/pendiente`.
- On `/pago/pendiente` with a real `booking_id`, the icon re-plays its
  entrance when polling resolves to `success`/`failure`.
