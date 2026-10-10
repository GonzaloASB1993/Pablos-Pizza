# Animation Plans

Plans produced by `improve-animations`, derived from the
`find-animation-opportunities` sweep of the frontend (public site + admin
panel). Each plan is fully self-contained — see the plan file itself for
exact values, not this index.

| # | Title | Severity | Status |
| --- | --- | --- | --- |
| [001](001-payment-result-entrance.md) | Animate the payment result screen (entrance + status swap) | MEDIUM | DONE — needs a real-browser feel check (see plan's Implementation Notes) |

## Recommended execution order

Only one plan exists so far — no ordering/dependency concerns yet.

## Other opportunities not yet planned

From the `find-animation-opportunities` sweep, these were identified but
don't have a plan written yet. Run `improve-animations plan <description>`
for any of them to generate a self-contained plan:

- `frontend/src/pages/admin/BookingsManagement.jsx:3633` — "Marcar como
  completado" uses a bare `window.confirm()` for a consequential, hard-to-
  reverse financial action. Candidate for a hold-to-confirm press-and-fill
  pattern. Bigger lift than 001 — replaces a native dialog with a custom
  component.
- `frontend/src/pages/admin/AdminDashboard.jsx:597-601` — skeleton-to-
  `StatCard` swap on dashboard load/refresh teleports; needs a subtle,
  fast (~150-200ms) cross-fade given the dashboard is checked many times a
  day.
- `frontend/src/pages/admin/GalleryManagement.jsx:99-107` (same pattern in
  `EventsManagement.jsx`, `InventoryManagement.jsx`) — content grids appear
  in one frame after loading; candidate for a ~40ms per-card stagger.
- `frontend/src/pages/public/BookingPage.jsx:523,615,1046` (`FormStepper`,
  defined at lines 205-271) — step transitions are opacity-only with no
  directional cue between forward/back navigation; candidate for a
  `translateX` direction cue.
