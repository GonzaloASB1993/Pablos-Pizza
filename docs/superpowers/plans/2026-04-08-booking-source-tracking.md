# Booking Source Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a required `source` field to every booking to track which channel brought the customer (website, Instagram, TikTok, boca a boca, otro), surface source stats in Dashboard and Reports.

**Architecture:** `source` lives on Firestore booking documents. The public form auto-sends `"website"`. The admin create form requires a dropdown selection. A one-time migration endpoint detects historical web bookings via payment fields. Dashboard and Reports compute source distribution client-side from fetched bookings.

**Tech Stack:** Python Flask + Firebase Firestore (backend), React 18 + Material-UI + Chart.js (frontend)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `backend/routes/bookings_routes.py` | Validate `source` required; add migration endpoint |
| Modify | `frontend/src/pages/public/BookingPage.jsx` | Auto-inject `source: 'website'` in `buildBookingData()` |
| Modify | `frontend/src/pages/admin/BookingsManagement.jsx` | Source dropdown in create form; source chip + edit in view dialog |
| Modify | `frontend/src/pages/admin/AdminDashboard.jsx` | Source ranking card for current month |
| Modify | `frontend/src/pages/admin/ReportsPage.jsx` | Horizontal bar chart in executive summary |

---

## Task 1: Backend — Validate `source` + Migration Endpoint

**Files:**
- Modify: `backend/routes/bookings_routes.py:38-115` (create_booking) and append migration route

### Steps

- [ ] **1.1 Add `source` validation and cleanup to `create_booking`**

  In `backend/routes/bookings_routes.py`, find the `create_booking` function. Locate line 44 where required fields are validated:

  ```python
  for f in ['service_type','participants']:
      if f not in data: return jsonify({"error": f"Missing {f}"}), 400
  ```

  Replace with:

  ```python
  for f in ['service_type','participants','source']:
      if not data.get(f): return jsonify({"error": f"Missing {f}"}), 400

  valid_sources = {'website','instagram','tiktok','word_of_mouth','other'}
  if data['source'] not in valid_sources:
      return jsonify({"error": f"Invalid source. Must be one of: {', '.join(valid_sources)}"}), 400

  # Clear source_other unless source is 'other'
  if data.get('source') != 'other':
      data['source_other'] = ''
  ```

- [ ] **1.2 Verify the field is persisted**

  The booking document is created at line 88 as:
  ```python
  bd = {"id":bid,**data,"customer_id":customer_id,...}
  ```
  Because `**data` spreads all request fields, `source` and `source_other` are already included automatically. No changes needed here.

- [ ] **1.3 Add the migration endpoint at the bottom of `bookings_routes.py`**

  Append after all existing routes:

  ```python
  @bookings_bp.route('/migrate-source', methods=['POST'])
  def migrate_source():
      """One-time migration: auto-detect source for historical bookings.
      Bookings with payment data -> 'website'. Others -> 'unknown'.
      Safe to run multiple times (skips already-migrated bookings)."""
      try:
          db = get_db()
          bookings_ref = db.collection("bookings")
          all_bookings = bookings_ref.get()

          migrated_website = 0
          migrated_unknown = 0
          skipped = 0

          for doc in all_bookings:
              booking = doc.to_dict()

              # Skip bookings that already have a source
              if booking.get('source'):
                  skipped += 1
                  continue

              # Detect web origin via payment-related fields
              has_payment = bool(
                  booking.get('payment_id') or
                  booking.get('preference_id') or
                  booking.get('payment_status') or
                  (isinstance(booking.get('payments'), list) and len(booking['payments']) > 0)
              )

              source = 'website' if has_payment else 'unknown'
              bookings_ref.document(doc.id).update({
                  'source': source,
                  'source_other': ''
              })

              if has_payment:
                  migrated_website += 1
              else:
                  migrated_unknown += 1

          return jsonify({
              "migrated_website": migrated_website,
              "migrated_unknown": migrated_unknown,
              "skipped_already_migrated": skipped,
              "total": migrated_website + migrated_unknown + skipped
          }), 200

      except Exception as e:
          return jsonify({"error": str(e)}), 500
  ```

- [ ] **1.4 Test the migration endpoint manually**

  Start the backend (`cd backend && python main.py`), then run:
  ```bash
  curl -X POST http://localhost:5000/api/bookings/migrate-source
  ```
  Expected response shape:
  ```json
  { "migrated_website": N, "migrated_unknown": N, "skipped_already_migrated": 0, "total": N }
  ```

- [ ] **1.5 Test that creating a booking without `source` returns 400**

  ```bash
  curl -X POST http://localhost:5000/api/bookings/ \
    -H "Content-Type: application/json" \
    -d '{"service_type":"workshop","participants":10}'
  ```
  Expected: `{"error": "Missing source"}`

- [ ] **1.6 Commit**

  ```bash
  git add backend/routes/bookings_routes.py
  git commit -m "feat: add source field validation and migration endpoint to bookings"
  ```

---

## Task 2: Frontend — Public Booking Form Auto-Sets Source

**Files:**
- Modify: `frontend/src/pages/public/BookingPage.jsx:418-429` (`buildBookingData`)

### Steps

- [ ] **2.1 Add `source: 'website'` to `buildBookingData`**

  In `BookingPage.jsx`, find `buildBookingData` at line 418:

  ```js
  const buildBookingData = () => {
    const comunaLejanaExtra = isComunaLejana(selectedComuna) ? CARGO_COMUNA_LEJANA : 0
    return {
      ...formData,
      services,
      participants: getTotalParticipants(),
      participantsByService: getParticipantsByService(),
      eventType: formData.eventType,
      selectedComuna: selectedComuna,
      comunaLejanaExtra: comunaLejanaExtra
    }
  }
  ```

  Add `source: 'website'` to the returned object:

  ```js
  const buildBookingData = () => {
    const comunaLejanaExtra = isComunaLejana(selectedComuna) ? CARGO_COMUNA_LEJANA : 0
    return {
      ...formData,
      services,
      participants: getTotalParticipants(),
      participantsByService: getParticipantsByService(),
      eventType: formData.eventType,
      selectedComuna: selectedComuna,
      comunaLejanaExtra: comunaLejanaExtra,
      source: 'website'
    }
  }
  ```

- [ ] **2.2 Verify manually**

  Start the frontend (`cd frontend && npm run dev`). Go to `/agendar`, complete the booking form and submit. In the Firebase console (or backend logs), verify the new booking document has `source: "website"`.

- [ ] **2.3 Commit**

  ```bash
  git add frontend/src/pages/public/BookingPage.jsx
  git commit -m "feat: auto-set source=website on public booking form submissions"
  ```

---

## Task 3: Frontend — Admin Create Booking Form (Source Dropdown)

**Files:**
- Modify: `frontend/src/pages/admin/BookingsManagement.jsx`

### Steps

- [ ] **3.1 Add `source` and `source_other` to `newBookingData` initial state**

  Find the `newBookingData` state at line 177:

  ```js
  const [newBookingData, setNewBookingData] = useState({
      client_name: '',
      client_email: '',
      client_phone: '',
      service_type: '',
      event_type: '',
      event_date: '',
      event_time: '',
      duration_hours: 4,
      participants: '',
      pizzeros_participants: 0,
      party_participants: 0,
      party_guests: 0,
      pizza_quantity: 10,
      location: '',
      special_requests: '',
      initial_payment: '',
      payment_method: 'transferencia'
  })
  ```

  Add the two new fields at the end of the object:

  ```js
  const [newBookingData, setNewBookingData] = useState({
      client_name: '',
      client_email: '',
      client_phone: '',
      service_type: '',
      event_type: '',
      event_date: '',
      event_time: '',
      duration_hours: 4,
      participants: '',
      pizzeros_participants: 0,
      party_participants: 0,
      party_guests: 0,
      pizza_quantity: 10,
      location: '',
      special_requests: '',
      initial_payment: '',
      payment_method: 'transferencia',
      source: '',
      source_other: ''
  })
  ```

- [ ] **3.2 Add `source` and `source_other` to `handleCreateBooking`**

  Find `handleCreateBooking` at line 1367. Inside it, the `bookingData` object is built at line 1369. Add the source fields:

  ```js
  const bookingData = {
      client_name: newBookingData.client_name,
      client_email: newBookingData.client_email,
      client_phone: newBookingData.client_phone,
      service_type: newBookingData.service_type || 'workshop',
      event_type: newBookingData.event_type || 'private',
      event_date: newBookingData.event_date,
      event_time: newBookingData.event_time,
      duration_hours: parseInt(newBookingData.duration_hours || 4),
      participants: parseInt(newBookingData.participants || 0),
      pizzeros_participants: parseInt(newBookingData.pizzeros_participants || 0, 10),
      party_guests: parseInt(newBookingData.party_guests || 0, 10),
      pizza_quantity: parseInt(newBookingData.pizza_quantity || 10, 10),
      estimated_price: newEstimatedPrice,
      location: newBookingData.location,
      special_requests: newBookingData.special_requests || '',
      source: newBookingData.source,
      source_other: newBookingData.source === 'other' ? newBookingData.source_other : ''
  }
  ```

- [ ] **3.3 Add client-side validation for `source` in `handleCreateBooking`**

  At the very top of `handleCreateBooking` (before the `try` block), add:

  ```js
  const handleCreateBooking = async () => {
      if (!newBookingData.source) {
          toast.error('Debes indicar cómo nos encontró el cliente')
          return
      }
      if (newBookingData.source === 'other' && !newBookingData.source_other.trim()) {
          toast.error('Debes especificar el origen cuando seleccionas "Otro"')
          return
      }
      try {
          // ... rest of existing code
  ```

- [ ] **3.4 Define the SOURCE_OPTIONS constant near the top of the component (after imports)**

  Add this constant right after the imports section, before the `BookingsManagement` component definition:

  ```js
  const SOURCE_OPTIONS = [
      { value: 'website', label: 'Página Web', icon: '🌐' },
      { value: 'instagram', label: 'Instagram', icon: '📸' },
      { value: 'tiktok', label: 'TikTok', icon: '🎵' },
      { value: 'word_of_mouth', label: 'Boca a Boca', icon: '🗣️' },
      { value: 'other', label: 'Otro', icon: '❓' },
  ]
  ```

- [ ] **3.5 Add source dropdown to the create booking dialog**

  Find the create booking Dialog at line 2803. Inside the `<Grid container spacing={2}>`, find the last `<Grid item>` before the `</Grid>` that closes the container and add after it:

  ```jsx
  {/* Source field */}
  <Grid item xs={12} sm={6}>
      <FormControl fullWidth required>
          <InputLabel>¿Cómo nos encontró el cliente?</InputLabel>
          <Select
              name="source"
              value={newBookingData.source}
              onChange={handleNewBookingChange}
              label="¿Cómo nos encontró el cliente?"
          >
              {SOURCE_OPTIONS.map(opt => (
                  <MenuItem key={opt.value} value={opt.value}>
                      {opt.icon} {opt.label}
                  </MenuItem>
              ))}
          </Select>
      </FormControl>
  </Grid>
  {newBookingData.source === 'other' && (
      <Grid item xs={12} sm={6}>
          <TextField
              fullWidth
              required
              label="Especificar origen"
              name="source_other"
              value={newBookingData.source_other}
              onChange={handleNewBookingChange}
          />
      </Grid>
  )}
  ```

- [ ] **3.6 Reset source fields when create dialog closes**

  Find where `setCreateDialog(false)` is called (line 1414). After the `setManualCustomerEntry(false)` call that follows it, add:

  ```js
  setNewBookingData(prev => ({ ...prev, source: '', source_other: '' }))
  ```

- [ ] **3.7 Verify in browser**

  Open the admin panel → Agendamientos → "Crear Agendamiento". Verify:
  - The "¿Cómo nos encontró el cliente?" dropdown appears
  - Selecting "Otro" reveals the text field
  - Submitting without a source shows the toast error

- [ ] **3.8 Commit**

  ```bash
  git add frontend/src/pages/admin/BookingsManagement.jsx
  git commit -m "feat: add required source dropdown to admin create booking form"
  ```

---

## Task 4: Frontend — Booking Detail View + Edit Source

**Files:**
- Modify: `frontend/src/pages/admin/BookingsManagement.jsx`

### Steps

- [ ] **4.1 Add state for inline source editing**

  Near the other dialog states (around line 108), add:

  ```js
  const [editingSource, setEditingSource] = useState(false)
  const [editSourceValue, setEditSourceValue] = useState('')
  const [editSourceOther, setEditSourceOther] = useState('')
  ```

- [ ] **4.2 Add `SOURCE_OPTIONS` helper to get label and icon**

  After the `SOURCE_OPTIONS` constant defined in Task 3.4, add this helper:

  ```js
  const getSourceDisplay = (source, sourceOther) => {
      const opt = SOURCE_OPTIONS.find(o => o.value === source)
      if (!opt) return { label: 'Sin datos', icon: '❓' }
      if (source === 'other' && sourceOther) return { label: sourceOther, icon: '❓' }
      return opt
  }
  ```

- [ ] **4.3 Add source handler to save the edit**

  After `handleDeleteBooking` (around line 1434), add:

  ```js
  const handleSaveSource = async () => {
      if (!editSourceValue) {
          toast.error('Selecciona un origen')
          return
      }
      if (editSourceValue === 'other' && !editSourceOther.trim()) {
          toast.error('Especifica el origen')
          return
      }
      try {
          await bookingsAPI.update(selectedBooking.id, {
              source: editSourceValue,
              source_other: editSourceValue === 'other' ? editSourceOther : ''
          })
          toast.success('Origen actualizado')
          setEditingSource(false)
          loadBookings()
          setSelectedBooking(prev => ({
              ...prev,
              source: editSourceValue,
              source_other: editSourceValue === 'other' ? editSourceOther : ''
          }))
      } catch (error) {
          console.error('Error saving source:', error)
          toast.error('Error al guardar el origen')
      }
  }
  ```

- [ ] **4.4 Add source row inside the viewDialog "Información" accordion**

  Find the viewDialog at line 4114. Inside the "Información" `<AccordionDetails>`, after the `<Grid container spacing={1}>` that contains client name, phone, email, and location, add a new `<Grid item xs={12}>`:

  ```jsx
  <Grid item xs={12}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="body2"><strong>Origen:</strong></Typography>
          {!editingSource ? (
              <>
                  <Chip
                      size="small"
                      label={`${getSourceDisplay(selectedBooking.source, selectedBooking.source_other).icon} ${getSourceDisplay(selectedBooking.source, selectedBooking.source_other).label}`}
                      color={selectedBooking.source === 'unknown' || !selectedBooking.source ? 'default' : 'primary'}
                      variant="outlined"
                  />
                  <IconButton
                      size="small"
                      onClick={() => {
                          setEditSourceValue(selectedBooking.source || '')
                          setEditSourceOther(selectedBooking.source_other || '')
                          setEditingSource(true)
                      }}
                  >
                      <Edit fontSize="small" />
                  </IconButton>
              </>
          ) : (
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                  <FormControl size="small" sx={{ minWidth: 180 }}>
                      <Select
                          value={editSourceValue}
                          onChange={(e) => setEditSourceValue(e.target.value)}
                          displayEmpty
                      >
                          {SOURCE_OPTIONS.map(opt => (
                              <MenuItem key={opt.value} value={opt.value}>
                                  {opt.icon} {opt.label}
                              </MenuItem>
                          ))}
                      </Select>
                  </FormControl>
                  {editSourceValue === 'other' && (
                      <TextField
                          size="small"
                          label="Especificar"
                          value={editSourceOther}
                          onChange={(e) => setEditSourceOther(e.target.value)}
                          sx={{ width: 160 }}
                      />
                  )}
                  <Button size="small" variant="contained" onClick={handleSaveSource}>Guardar</Button>
                  <Button size="small" onClick={() => setEditingSource(false)}>Cancelar</Button>
              </Box>
          )}
      </Box>
  </Grid>
  ```

- [ ] **4.5 Reset editing state when viewDialog closes**

  Find `setViewDialog(false)` calls and ensure the editing state resets. Add to the `onClose` prop of the viewDialog:

  ```jsx
  <Dialog
      open={viewDialog}
      onClose={() => { setViewDialog(false); setEditingSource(false) }}
      ...
  >
  ```

- [ ] **4.6 Verify in browser**

  Open a booking's detail view. Verify the "Origen" row appears in the Información accordion with a Chip and edit pencil. Click the pencil, change the source, save. Verify the chip updates.

- [ ] **4.7 Commit**

  ```bash
  git add frontend/src/pages/admin/BookingsManagement.jsx
  git commit -m "feat: add source chip and inline edit to booking detail view"
  ```

---

## Task 5: Frontend — Dashboard Source Ranking Card

**Files:**
- Modify: `frontend/src/pages/admin/AdminDashboard.jsx`

### Steps

- [ ] **5.1 Define SOURCE_LABELS near the top of the file**

  After the `monthNames` constant at line 83, add:

  ```js
  const SOURCE_LABELS = {
      website: 'Página Web',
      instagram: 'Instagram',
      tiktok: 'TikTok',
      word_of_mouth: 'Boca a Boca',
      other: 'Otro',
      unknown: 'Sin datos'
  }
  ```

- [ ] **5.2 Add `sourceRanking` state**

  Near the other data states (around line 190), add:

  ```js
  const [sourceRanking, setSourceRanking] = useState([])
  ```

- [ ] **5.3 Compute source ranking from bookings already fetched**

  In `loadDashboardData`, the results at index 5 contain all bookings (line 249):

  ```js
  if (results[5].status === 'fulfilled') {
      const bookingsData = results[5].value.data
      const bookings = bookingsData.items || bookingsData || []
      // ... existing code ...
  }
  ```

  After the existing booking processing inside this block, add:

  ```js
  // Source ranking for selected month
  const monthBookings = bookings.filter(b => {
      if (!b.event_date) return false
      const [y, m] = b.event_date.split('-').map(Number)
      return y === selectedYear && m === selectedMonth
  })
  const sourceCounts = monthBookings.reduce((acc, b) => {
      const src = b.source || 'unknown'
      acc[src] = (acc[src] || 0) + 1
      return acc
  }, {})
  const sourceRanking = Object.entries(sourceCounts)
      .sort(([, a], [, b]) => b - a)
      .map(([source, count]) => ({ source, count }))
  setSourceRanking(sourceRanking)
  ```

- [ ] **5.4 Add the source ranking card to the Dashboard JSX**

  Find where `SectionCard` components are rendered in the Dashboard JSX. Add a new `<Grid item xs={12} md={6}>` with the source ranking:

  ```jsx
  <Grid item xs={12} md={6}>
      <SectionCard
          title="Origen de Bookings"
          icon={<ShowChart sx={{ color: '#FFD700' }} />}
      >
          {sourceRanking.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                  No hay bookings con origen registrado este mes.
              </Typography>
          ) : (
              <Box>
                  {(() => {
                      const known = sourceRanking.filter(r => r.source !== 'unknown')
                      const total = known.reduce((s, r) => s + r.count, 0)
                      const unknown = sourceRanking.find(r => r.source === 'unknown')
                      return (
                          <>
                              {known.map(({ source, count }) => (
                                  <Box key={source} sx={{ mb: 1.5 }}>
                                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                                          <Typography variant="body2">{SOURCE_LABELS[source] || source}</Typography>
                                          <Typography variant="body2" fontWeight={600}>
                                              {count} ({total > 0 ? Math.round((count / total) * 100) : 0}%)
                                          </Typography>
                                      </Box>
                                      <LinearProgress
                                          variant="determinate"
                                          value={total > 0 ? (count / total) * 100 : 0}
                                          sx={{ height: 6, borderRadius: 3 }}
                                      />
                                  </Box>
                              ))}
                              {unknown && (
                                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                                      Sin datos de origen: {unknown.count} booking(s)
                                  </Typography>
                              )}
                          </>
                      )
                  })()}
              </Box>
          )}
      </SectionCard>
  </Grid>
  ```

- [ ] **5.5 Verify in browser**

  Open the Dashboard, select a month that has bookings. Verify the "Origen de Bookings" card appears with progress bars per channel.

- [ ] **5.6 Commit**

  ```bash
  git add frontend/src/pages/admin/AdminDashboard.jsx
  git commit -m "feat: add source acquisition ranking card to dashboard"
  ```

---

## Task 6: Frontend — Reports Source Chart

**Files:**
- Modify: `frontend/src/pages/admin/ReportsPage.jsx`

### Steps

- [ ] **6.1 Define SOURCE_LABELS and SOURCE_COLORS in ReportsPage.jsx**

  After the ChartJS register block (around line 94), add:

  ```js
  const SOURCE_LABELS = {
      website: 'Página Web',
      instagram: 'Instagram',
      tiktok: 'TikTok',
      word_of_mouth: 'Boca a Boca',
      other: 'Otro',
      unknown: 'Sin datos'
  }

  const SOURCE_COLORS = {
      website: '#1976d2',
      instagram: '#e91e8c',
      tiktok: '#000000',
      word_of_mouth: '#ff9800',
      other: '#9e9e9e',
      unknown: '#bdbdbd'
  }
  ```

- [ ] **6.2 Add `sourceData` state and `bookingsForSource` state**

  Near the other state declarations in `ReportsPage`, add:

  ```js
  const [sourceChartData, setSourceChartData] = useState(null)
  ```

- [ ] **6.3 Fetch bookings for source chart and compute distribution**

  Find the main data loading function in `ReportsPage` (it calls `reportsAPI.getMonthly`, etc.). Add a `bookingsAPI` import if not present — check the imports at line 78:

  ```js
  import { reportsAPI, inventoryAPI, expensesAPI, vacuumSalesAPI } from '../../services/api'
  ```

  Add `bookingsAPI` to the import:

  ```js
  import { reportsAPI, inventoryAPI, expensesAPI, vacuumSalesAPI, bookingsAPI } from '../../services/api'
  ```

  Then, inside the data loading function (wherever it fetches reports data), add a parallel call to get bookings:

  ```js
  const bookingsRes = await bookingsAPI.getAll({ limit: 500 })
  const allBookings = bookingsRes.data?.items || bookingsRes.data || []

  // Filter by selected year (and month if applicable)
  const filtered = allBookings.filter(b => {
      if (!b.event_date) return false
      const [y, m] = b.event_date.split('-').map(Number)
      if (selectedYear && y !== selectedYear) return false
      if (selectedMonth && selectedMonth !== 0 && m !== selectedMonth) return false
      return true
  })

  const counts = filtered.reduce((acc, b) => {
      const src = b.source || 'unknown'
      acc[src] = (acc[src] || 0) + 1
      return acc
  }, {})

  const labels = Object.keys(counts).map(k => SOURCE_LABELS[k] || k)
  const values = Object.values(counts)
  const colors = Object.keys(counts).map(k => SOURCE_COLORS[k] || '#9e9e9e')

  setSourceChartData({
      labels,
      datasets: [{
          label: 'Bookings por canal',
          data: values,
          backgroundColor: colors,
          borderRadius: 4
      }]
  })
  ```

- [ ] **6.4 Add the source chart to the Reports JSX executive summary**

  Find the executive summary section in the Reports JSX. Add a new card with the horizontal bar chart:

  ```jsx
  {sourceChartData && (
      <Grid item xs={12} md={6}>
          <Card>
              <CardContent>
                  <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
                      Canales de Adquisición
                  </Typography>
                  <Bar
                      data={sourceChartData}
                      options={{
                          indexAxis: 'y',
                          responsive: true,
                          plugins: {
                              legend: { display: false },
                              tooltip: {
                                  callbacks: {
                                      label: (ctx) => {
                                          const total = ctx.dataset.data.reduce((a, b) => a + b, 0)
                                          const pct = total > 0 ? Math.round((ctx.raw / total) * 100) : 0
                                          return ` ${ctx.raw} bookings (${pct}%)`
                                      }
                                  }
                              }
                          },
                          scales: {
                              x: {
                                  beginAtZero: true,
                                  ticks: { precision: 0 },
                                  grid: { color: 'rgba(0,0,0,0.05)' }
                              },
                              y: { grid: { display: false } }
                          }
                      }}
                  />
              </CardContent>
          </Card>
      </Grid>
  )}
  ```

- [ ] **6.5 Verify in browser**

  Open Reports, select a period with bookings. Verify the "Canales de Adquisición" horizontal bar chart appears with correct data.

- [ ] **6.6 Commit**

  ```bash
  git add frontend/src/pages/admin/ReportsPage.jsx
  git commit -m "feat: add source acquisition bar chart to reports executive summary"
  ```

---

## Task 7: Run Migration

- [ ] **7.1 Deploy backend with migration endpoint**

  Ensure the backend with Task 1 changes is running in production (or locally connected to production Firestore).

- [ ] **7.2 Execute migration once**

  ```bash
  curl -X POST https://main-4kqeqojbsq-uc.a.run.app/api/bookings/migrate-source
  ```

  Or locally if connected to production Firestore:
  ```bash
  curl -X POST http://localhost:5000/api/bookings/migrate-source
  ```

- [ ] **7.3 Verify migration output**

  Confirm response shows reasonable numbers:
  ```json
  { "migrated_website": N, "migrated_unknown": N, "skipped_already_migrated": 0, "total": N }
  ```

  Cross-check in Firebase console: open a few bookings that had payments, verify they now have `source: "website"`.

- [ ] **7.4 Final commit (if any cleanup needed)**

  ```bash
  git add .
  git commit -m "chore: post-migration cleanup and verification"
  ```
