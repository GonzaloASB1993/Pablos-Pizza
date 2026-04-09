# Booking Source Tracking — Design Spec
**Date:** 2026-04-08  
**Status:** Approved  

---

## Overview

Add a required `source` field to bookings to track which channel brought each customer. The public booking form sets it automatically to `"website"`. Admins select it manually when creating a booking. Historical bookings are migrated once via a backend endpoint. Source data surfaces in the Dashboard and Reports page.

---

## 1. Data Model

### Firestore — `bookings` collection

Two new fields added to every booking document:

| Field | Type | Required | Description |
|---|---|---|---|
| `source` | string | yes | Acquisition channel |
| `source_other` | string | no | Free text, only when `source == "other"` |

### Valid `source` values

| Value | Display label |
|---|---|
| `website` | Página Web |
| `instagram` | Instagram |
| `tiktok` | TikTok |
| `word_of_mouth` | Boca a Boca |
| `other` | Otro |
| `unknown` | Desconocido *(migration fallback only)* |

`unknown` is never selectable by users — it is assigned only to historical bookings that cannot be auto-detected.

---

## 2. Backend

### `POST /api/bookings/`
- `source` is now a **required** field. Missing or empty → `400 Bad Request` with `{"error": "Missing source"}`.
- `source_other` is optional. Saved only when `source == "other"`. Ignored otherwise.
- Public website always sends `source: "website"` (set client-side, transparent to user).

### `PUT /api/bookings/<id>`
- No structural changes. `source` and `source_other` are accepted and updated like any other field.
- No re-validation of `source` on update (allows admins to correct it freely).

### `POST /api/bookings/migrate-source` *(one-time)*
- No auth required on the endpoint itself (consistent with existing backend pattern). Callable once via Postman or curl by the developer.
- Iterates all booking documents without a `source` field.
- Logic:
  - Has `payment_id` → assign `source: "website"`
  - No `payment_id` → assign `source: "unknown"`
- Returns: `{ "migrated_website": N, "migrated_unknown": N, "total": N }`
- Safe to run multiple times (skips bookings that already have `source`).

---

## 3. Frontend — Public Booking Form (`BookingPage.jsx`)

- No UI changes visible to the customer.
- Before submitting the booking payload, append `source: "website"` programmatically.
- No `source_other` needed for this path.

---

## 4. Frontend — Admin Create Booking (`BookingsManagement.jsx`)

### Form dialog changes
- Add a required **Select** field labeled **"¿Cómo nos encontró el cliente?"**
- Options: Página Web, Instagram, TikTok, Boca a Boca, Otro
- If **"Otro"** is selected → show a `TextField` labeled **"Especificar"** (required when `source == "other"`)
- Submit button remains disabled until `source` is selected (and `source_other` filled if applicable)

### Initial form state
```js
formData = {
  ...existingFields,
  source: '',
  source_other: ''
}
```

---

## 5. Frontend — Booking Detail Modal (`BookingsManagement.jsx`)

### Display
- Show current source as a labeled `Chip` with a channel-specific icon:
  - `website` → Language icon
  - `instagram` → CameraAlt icon
  - `tiktok` → MusicNote icon
  - `word_of_mouth` → People icon
  - `other` → HelpOutline icon
  - `unknown` → QuestionMark icon (gray, muted)

### Edit
- Edit icon button next to the chip opens an inline Select (same options as creation form)
- If changed to "Otro", shows `source_other` text field
- Saves via `PUT /api/bookings/<id>` on confirm
- Shows toast on success/error

---

## 6. Dashboard

In the existing summary section, add a new **"Origen de Bookings"** card for the current month:

- Ordered list of channels by volume (highest first)
- Each row: channel name + booking count + percentage of total
- Example:
  ```
  1. Página Web     12  (60%)
  2. Instagram       5  (25%)
  3. Boca a Boca     2  (10%)
  4. TikTok          1   (5%)
  ```
- Excludes `unknown` from percentage calculation (shown separately as "Sin datos: N")

---

## 7. Reports Page (`ReportsPage.jsx`)

In the existing executive summary section, add a **"Canales de Adquisición"** subsection:

- Bar chart (horizontal preferred for label readability) showing booking count per source
- Respects the existing date range filter already present in the Reports page
- Color-coded bars matching the channel (Instagram → purple, TikTok → black/pink, etc.)
- Shows raw count and percentage on each bar
- `unknown` shown as a separate muted bar at the bottom

---

## 8. Migration Plan

1. Deploy backend with new `migrate-source` endpoint
2. Call `POST /api/bookings/migrate-source` once from backend console or Postman
3. Verify response counts are reasonable
4. Deploy frontend with new `source` field required
5. No rollback needed — `source` field on old documents is additive

---

## Out of Scope

- UTM parameter tracking from browser referrer
- Per-source revenue analytics (future milestone)
- Tracking source on Events directly (source lives on Booking only)
