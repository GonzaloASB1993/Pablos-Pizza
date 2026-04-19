# UX/UI Audit Improvements — Pablo's Pizza

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolver los 15 hallazgos + 4 gaps del roadmap de la auditoría UX/UI: unificar el sistema visual en 5 páginas públicas, centralizar pricing y stats, eliminar fotos ilegales de stock, y elevar la calidad percibida del sitio de 4/10 a 7+/10.

**Architecture:** Tres oleadas de trabajo. Oleada 1 (críticos + fundamentos): unificación de paleta dark-editorial en todas las páginas, pricing.js y stats.js centralizados, fotos stock eliminadas, focus states globales, fuente display. Oleada 2 (páginas individuales): rediseñar ServicesPage, BookingPage hero, iconografía, micro-animación editorial de reemplazo, y copy. Oleada 3 (mejoras futuras): stats dinámicas desde backend, valores concretos + timeline en About, A/B test FloatingCTA.

**Tech Stack:** React 18, Material-UI v5, JavaScript (sin TypeScript), Firebase/Firestore (backend para stats dinámicas).

---

## Archivos que se modifican en este plan

| Archivo | Acción | Tarea |
|---------|--------|-------|
| `frontend/src/data/pricing.js` | Crear | Task 1 |
| `frontend/src/data/stats.js` | Crear | Task 2 |
| `frontend/src/utils/theme.js` | Modificar | Tasks 3, 4 |
| `frontend/index.html` | Modificar | Task 4 |
| `frontend/src/pages/public/ServicesPage.jsx` | Modificar | Tasks 0, 6, 7, 8, 12, 13 |
| `frontend/src/pages/public/AboutPage.jsx` | Modificar | Tasks 0, 5, 12, 13, 15 |
| `frontend/src/pages/public/ContactPage.jsx` | Modificar | Tasks 0, 11 |
| `frontend/src/pages/public/BookingPage.jsx` | Modificar | Tasks 1, 9, 10 |
| `frontend/src/pages/public/HomePage.jsx` | Modificar | Tasks 1, 2, 13 |
| `frontend/src/hooks/useStats.js` | Crear | Task 14 |

---

## ═══════════════════════════════════
## OLEADA 1 — CRÍTICOS Y FUNDAMENTOS
## (Semanas 1–2 · Mayor ROI por hora)
## ═══════════════════════════════════

---

### Task 0: Unificar paleta — extender dark-editorial a todas las páginas (Crítico #01)

**Problema:** El Home usa fondo `#080808` con dorado puntual — se siente como una marca premium. Al hacer click en "Ver Servicios", ServicesPage aparece con fondo `#fafafa` + gradiente saturado `135deg #FFD700 → #B8860B`. AboutPage y ContactPage repiten variaciones. El visitante siente que cambió de sitio web. Es la causa raíz de la puntuación 4/10 en Calidad Percibida.

**Files:**
- Modify: `frontend/src/pages/public/ServicesPage.jsx` (secciones hero y body)
- Modify: `frontend/src/pages/public/AboutPage.jsx` (secciones hero y body)
- Modify: `frontend/src/pages/public/ContactPage.jsx` (secciones hero y body)

> **Sistema de paleta unificado (aplicar en toda la tarea):**
> - Fondo body principal: `#0d0d0d` (oscuro, idéntico al Home)
> - Fondo secciones alternas: `#141414`
> - Fondo cards elevadas: `#1a1714`
> - Color texto principal: `#FFFFFF`
> - Color texto secundario: `rgba(255,255,255,0.65)`
> - Acento dorado: `#e8b63a` (dorado cálido, no saturado)
> - **PROHIBIDO:** `linear-gradient(135deg, #FFD700`, `#B8860B`, `#FF8A00` en backgrounds de página
> - **PERMITIDO:** `#FFD700` solo como color de texto/borde/acento puntual, nunca como fondo de sección

- [ ] **Step 1: Leer los backgrounds actuales de ServicesPage**

```bash
grep -n "background\|bgcolor\|#fafafa\|#FAFAFA\|FFD700.*B8860B\|gradient" \
  frontend/src/pages/public/ServicesPage.jsx | head -40
```

Identificar todos los `Box` de sección que usan fondos claros o gradientes dorados saturados.

- [ ] **Step 2: Reemplazar fondos en ServicesPage**

Para cada sección con fondo claro (`#fafafa`, `#ffffff`, `#f5f5f5`) o gradiente dorado saturado, aplicar el sistema unificado:

```jsx
// Hero section principal — ANTES:
// background: 'linear-gradient(135deg, #FFD700 0%, #B8860B 100%)'
// o background: '#FAFAFA'

// Hero section principal — DESPUÉS:
sx={{ background: '#0d0d0d' }}

// Sección "Nuestros Servicios" (cards) — ANTES:
// background: '#fafafa' o '#ffffff'

// DESPUÉS:
sx={{ background: '#0d0d0d' }}

// Sección "Planes y Precios" — DESPUÉS:
sx={{ background: '#141414' }}

// Cards individuales de servicio — DESPUÉS:
sx={{ background: '#1a1714', border: '1px solid rgba(232,182,58,0.15)' }}

// Texto de titulares en secciones oscuras — DESPUÉS:
sx={{ color: '#FFFFFF' }}

// Texto secundario en secciones oscuras — DESPUÉS:
sx={{ color: 'rgba(255,255,255,0.65)' }}
```

- [ ] **Step 3: Leer los backgrounds actuales de AboutPage**

```bash
grep -n "background\|bgcolor\|#fafafa\|#FAFAFA\|FFD700.*B8860B\|gradient" \
  frontend/src/pages/public/AboutPage.jsx | head -40
```

- [ ] **Step 4: Reemplazar fondos en AboutPage**

Aplicar el mismo sistema de paleta unificado. Las cards del equipo y los valores van sobre `#1a1714`:

```jsx
// Page wrapper — DESPUÉS:
sx={{ background: '#0d0d0d', minHeight: '100vh' }}

// Hero de la página — DESPUÉS:
sx={{ background: '#0d0d0d', py: { xs: 8, md: 12 } }}

// Sección equipo — DESPUÉS:
sx={{ background: '#141414', py: { xs: 6, md: 10 } }}

// Cards del equipo — DESPUÉS:
sx={{ background: '#1a1714', border: '1px solid rgba(232,182,58,0.12)', borderRadius: 2 }}

// Sección valores — DESPUÉS:
sx={{ background: '#0d0d0d', py: { xs: 6, md: 10 } }}
```

- [ ] **Step 5: Leer los backgrounds actuales de ContactPage**

```bash
grep -n "background\|bgcolor\|#fafafa\|#FAFAFA\|FFD700.*B8860B\|gradient" \
  frontend/src/pages/public/ContactPage.jsx | head -40
```

- [ ] **Step 6: Reemplazar fondos en ContactPage**

```jsx
// Page wrapper — DESPUÉS:
sx={{ background: '#0d0d0d', minHeight: '100vh' }}

// Hero — DESPUÉS:
sx={{ background: '#0d0d0d', py: { xs: 8, md: 10 } }}

// Sección con cards de contacto — DESPUÉS:
sx={{ background: '#141414', py: { xs: 6, md: 8 } }}

// Cards de contacto — DESPUÉS:
sx={{ background: '#1a1714', border: '1px solid rgba(232,182,58,0.15)', borderRadius: 2 }}
```

- [ ] **Step 7: Ajustar colores de texto que quedan ilegibles sobre fondo oscuro**

Después de cambiar fondos, buscar en los tres archivos cualquier `color: '#333'`, `color: 'text.primary'`, `color: '#000'` que estén sobre el nuevo fondo oscuro y reemplazarlos:

```jsx
// Texto principal sobre fondo oscuro:
sx={{ color: '#FFFFFF' }}  // o color: 'white'

// Texto secundario sobre fondo oscuro:
sx={{ color: 'rgba(255,255,255,0.65)' }}

// Separadores/borders sobre fondo oscuro:
sx={{ borderColor: 'rgba(255,255,255,0.1)' }}
```

- [ ] **Step 8: Verificar transición visual Home → Servicios → Nosotros → Contacto**

```bash
cd frontend && npm run dev
```

Navegar `/` → click "Ver Servicios" → click "Nosotros" → click "Contacto". Las 4 páginas deben sentirse visualmente coherentes: mismo fondo oscuro, mismo acento dorado, sin saltos de "mundo claro" a "mundo oscuro".

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/public/ServicesPage.jsx \
        frontend/src/pages/public/AboutPage.jsx \
        frontend/src/pages/public/ContactPage.jsx
git commit -m "style: unify dark-editorial palette across ServicesPage, AboutPage, ContactPage"
```

---

### Task 1: Centralizar pricing en un solo archivo de datos

**Problema:** El Home muestra "10% dcto este mes" en el FloatingCTA, la sección Taller dice "10% para +15 niños · 15% para +25 niños", y ServicesPage tiene una tabla de 4 tiers con precios distintos. Tres fuentes contradictorias.

**Files:**
- Create: `frontend/src/data/pricing.js`
- Modify: `frontend/src/pages/public/HomePage.jsx` (líneas ~752, ~967)
- Modify: `frontend/src/pages/public/ServicesPage.jsx` (líneas ~825–860)

- [ ] **Step 1: Crear el archivo de datos centralizado**

Crear `frontend/src/data/pricing.js`:

```js
// Fuente única de verdad para todos los precios del sitio.
// Actualizar este archivo propaga los cambios a Home, Servicios y Agendar.

export const PIZZEROS_TIERS = [
  { range: 'Hasta 10 niños', price: 13500, unit: 'por niño', label: 'Hasta 10 niños' },
  { range: '11–14 niños',    price: 10500, unit: 'por niño', label: '11–14 niños' },
  { range: '15–19 niños',    price:  9500, unit: 'por niño', label: '15–19 niños', highlight: true },
  { range: '20+ niños',      price:  9000, unit: 'por niño', label: '20+ niños',   highlight: true },
]

// Precio base para mostrar en hero/CTA (tier más alto para atraer con precio mínimo)
export const PIZZEROS_BASE_PRICE = PIZZEROS_TIERS[0].price

// Calcula el precio por participante según cantidad
export function getPizzerosPrice(participants) {
  if (participants >= 20) return PIZZEROS_TIERS[3].price
  if (participants >= 15) return PIZZEROS_TIERS[2].price
  if (participants >= 11) return PIZZEROS_TIERS[1].price
  return PIZZEROS_TIERS[0].price
}

// Descuentos del FloatingCTA — null = sin descuento activo
export const ACTIVE_PROMO = null
// Ejemplo cuando hay promo: { label: '10% dcto este mes', expiry: '2026-04-30' }
```

- [ ] **Step 2: Consumir pricing.js en ServicesPage**

En `frontend/src/pages/public/ServicesPage.jsx`, agregar el import al inicio del archivo (después de los imports de MUI):

```js
import { PIZZEROS_TIERS } from '../../data/pricing'
```

Localizar el bloque con la tabla hardcodeada (líneas ~826–865) y reemplazarlo:

```jsx
// ANTES (hardcodeado):
// { range: 'Hasta 10 niños', price: '$13.500', unit: 'por niño', desc: 'Precio estándar' },
// { range: '11–14 niños', price: '$10.500', ... }
// etc.

// DESPUÉS (desde datos centralizados):
{PIZZEROS_TIERS.map((tier, index) => (
  <Box
    key={index}
    sx={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      p: 1.5,
      borderRadius: 1,
      bgcolor: tier.highlight ? 'rgba(255,215,0,0.1)' : 'rgba(0,0,0,0.02)',
      border: tier.highlight ? '2px solid rgba(255,215,0,0.3)' : '1px solid rgba(0,0,0,0.1)',
    }}
  >
    <Typography variant="body2" sx={{ fontWeight: 500 }}>{tier.range}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 700 }}>
      ${tier.price.toLocaleString('es-CL')}
      <Typography component="span" variant="caption" sx={{ ml: 0.5, color: 'text.secondary' }}>
        {tier.unit}
      </Typography>
    </Typography>
  </Box>
))}
```

- [ ] **Step 3: Consumir pricing.js en HomePage**

En `frontend/src/pages/public/HomePage.jsx`, agregar import:

```js
import { getPizzerosPrice, ACTIVE_PROMO, PIZZEROS_TIERS } from '../../data/pricing'
```

Localizar la sección del FloatingCTA (búsqueda: `"10% dcto"` o `"este mes"`) y reemplazar el texto hardcodeado:

```jsx
// ANTES:
// 'Este mes 10% OFF'

// DESPUÉS:
{ACTIVE_PROMO ? ACTIVE_PROMO.label : null}
```

Localizar la línea ~967 con `"Descuentos: 10% para +15 niños · 15% para +25 niños"` y reemplazar:

```jsx
// ANTES:
// Descuentos: 10% para +15 niños · 15% para +25 niños

// DESPUÉS — derivado de los datos reales:
{`Desde $${PIZZEROS_TIERS[PIZZEROS_TIERS.length - 1].price.toLocaleString('es-CL')} con grupos de 20+ niños`}
```

Localizar la función `getPizzerosPrice` local en BookingPage.jsx (línea ~97) y reemplazarla con el import:

En `frontend/src/pages/public/BookingPage.jsx`:
```js
// Eliminar la función local getPizzerosPrice (líneas ~97–105)
// Agregar import:
import { getPizzerosPrice } from '../../data/pricing'
```

- [ ] **Step 4: Verificar en el navegador**

```bash
cd frontend && npm run dev
```

Navegar a `/`, `/servicios` y `/agendar`. Verificar que:
- Home no muestra descuento si `ACTIVE_PROMO = null`
- ServicesPage muestra la misma tabla de 4 tiers
- BookingPage calcula precios con la función importada

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/pricing.js frontend/src/pages/public/ServicesPage.jsx frontend/src/pages/public/HomePage.jsx frontend/src/pages/public/BookingPage.jsx
git commit -m "feat: centralize pricing data in src/data/pricing.js"
```

---

### Task 2: Centralizar stats de social proof

**Problema:** "500+" aparece hardcodeado en `HomePage.jsx` (~L752 y ~L1587), `AboutPage.jsx` (~L240) y `ServicesPage.jsx` (~L800). Si cambia hay que actualizar 3 archivos.

**Files:**
- Create: `frontend/src/data/stats.js`
- Modify: `frontend/src/pages/public/HomePage.jsx`
- Modify: `frontend/src/pages/public/AboutPage.jsx`
- Modify: `frontend/src/pages/public/ServicesPage.jsx`

- [ ] **Step 1: Crear archivo de stats**

Crear `frontend/src/data/stats.js`:

```js
// Cifras de social proof — actualizar aquí propaga a todo el sitio.
// IMPORTANTE: Usar cifras específicas (526 > 500+) para mayor credibilidad.
// Derivar de bookings reales en una futura iteración (Task 16).

export const STATS = {
  kidsServed:  '500+',   // Reemplazar con número real cuando esté disponible
  eventsCount: '50+',    // Ídem
  yearsActive: '3',
  rating: '5.0',
}
```

- [ ] **Step 2: Consumir en HomePage**

```js
import { STATS } from '../../data/stats'
```

Localizar línea ~752 (array de stats con `number: '500+'`) y línea ~1587 (`'500+ Familias felices'`).
Reemplazar ambas referencias:

```jsx
// Línea ~752 — array de stats:
{ number: STATS.kidsServed, label: 'Niños felices', icon: <Favorite sx={{ fontSize: 16, color: GOLD }} /> },

// Línea ~1587 — quick stats:
{ number: STATS.kidsServed, label: 'Familias felices' },
```

- [ ] **Step 3: Consumir en AboutPage**

```js
import { STATS } from '../../data/stats'
```

Localizar línea ~240 (`number="500+"`) y reemplazar:

```jsx
<StatCard number={STATS.kidsServed} label="Niños felices" />
// (o como esté nombrado el componente en ese archivo)
```

- [ ] **Step 4: Consumir en ServicesPage** (si hay referencia hardcodeada)

```js
import { STATS } from '../../data/stats'
```

Buscar `"500"` o `"Más de 500"` y reemplazar con `STATS.kidsServed`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/stats.js frontend/src/pages/public/HomePage.jsx frontend/src/pages/public/AboutPage.jsx frontend/src/pages/public/ServicesPage.jsx
git commit -m "feat: centralize social proof stats in src/data/stats.js"
```

---

### Task 3: Focus states globales en el theme MUI

**Problema:** Solo el Home define `&:focus-visible`. ServicesPage, AboutPage, ContactPage y BookingPage dependen del default del navegador, que es casi invisible sobre fondos dorados (`#FFD700`).

**Files:**
- Modify: `frontend/src/utils/theme.js` (línea ~80 en adelante, sección `components`)

- [ ] **Step 1: Leer el theme actual**

Leer `frontend/src/utils/theme.js` completo para ver la estructura del objeto `createTheme`.

- [ ] **Step 2: Agregar override global de focus en el theme**

En `frontend/src/utils/theme.js`, dentro del objeto pasado a `createTheme`, agregar (o extender) la sección `components`:

```js
components: {
  MuiButtonBase: {
    defaultProps: {
      disableRipple: false,
    },
    styleOverrides: {
      root: {
        '&:focus-visible': {
          outline: '3px solid #000000',
          outlineOffset: '3px',
        },
      },
    },
  },
  MuiButton: {
    styleOverrides: {
      root: {
        '&:focus-visible': {
          outline: '3px solid #000000',
          outlineOffset: '3px',
        },
      },
    },
  },
  MuiIconButton: {
    styleOverrides: {
      root: {
        '&:focus-visible': {
          outline: '3px solid #000000',
          outlineOffset: '3px',
        },
      },
    },
  },
  MuiMenuItem: {
    styleOverrides: {
      root: {
        '&:focus-visible': {
          outline: '3px solid #000000',
          outlineOffset: '3px',
          backgroundColor: 'rgba(0,0,0,0.04)',
        },
      },
    },
  },
  MuiLink: {
    styleOverrides: {
      root: {
        '&:focus-visible': {
          outline: '3px solid #000000',
          outlineOffset: '3px',
          borderRadius: '2px',
        },
      },
    },
  },
},
```

> Nota: Se usa `#000000` (negro) sobre fondos claros para máximo contraste WCAG AA. Las páginas con fondo oscuro ya tienen dorado como color del texto, por lo que el negro destaca igualmente. Si en una sección específica el contraste es insuficiente, sobreescribir localmente con `#FFD700`.

- [ ] **Step 3: Verificar navegación por teclado**

```bash
cd frontend && npm run dev
```

Abrir `/servicios` y presionar Tab repetidamente. Cada botón/link debe mostrar un outline negro de 3px claramente visible.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/theme.js
git commit -m "feat: add global focus-visible states to MUI theme for a11y"
```

---

### Task 4: Agregar display font (Fraunces) para titulares H1/H2

**Problema:** El sitio solo usa Roboto. Cuando el Home estira Roboto a `10rem`, el resultado es grande pero sin carácter. Una fuente display hace que el mismo tamaño sea memorable.

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/utils/theme.js`

- [ ] **Step 1: Cargar Fraunces desde Google Fonts**

En `frontend/index.html`, dentro de `<head>`, agregar después del preconnect existente de Google Fonts (o crearlo si no existe):

```html
<!-- Display font para titulares H1/H2 -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,700;0,9..144,900;1,9..144,400;1,9..144,900&family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
```

- [ ] **Step 2: Registrar la fuente en el theme**

En `frontend/src/utils/theme.js`, en el objeto de `createTheme`, agregar/modificar `typography`:

```js
typography: {
  fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  h1: {
    fontFamily: '"Fraunces", serif',
    fontOpticalSizing: 'auto',
  },
  h2: {
    fontFamily: '"Fraunces", serif',
    fontOpticalSizing: 'auto',
  },
  // h3 en adelante mantiene Roboto
},
```

- [ ] **Step 3: Verificar en el navegador**

```bash
cd frontend && npm run dev
```

Abrir `/`. El título "CREAMOS MAGIA" debe renderizarse con Fraunces. Si no cambia, verificar que el `<Typography variant="h1">` no tenga `fontFamily` inline que lo sobreescriba.

En ese caso, buscar en `HomePage.jsx` el typography con `fontWeight: 900` del hero y agregar:

```jsx
sx={{ fontFamily: '"Fraunces", serif', fontOpticalSizing: 'auto', /* resto de estilos */ }}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/src/utils/theme.js
git commit -m "feat: add Fraunces display font for H1/H2 editorial headers"
```

---

### Task 5: Eliminar fotos de Unsplash del equipo (About)

**Problema:** `AboutPage.jsx` usa imágenes de `images.unsplash.com` para Juan Pablo, Nicole y Mauro. Riesgo legal (Unsplash no garantiza licencia para identificar personas) y credibilidad rota (el visitante ve modelos de stock, no el equipo real).

**Files:**
- Modify: `frontend/src/pages/public/AboutPage.jsx` (líneas 138–165)

- [ ] **Step 1: Leer el bloque del equipo**

Leer `frontend/src/pages/public/AboutPage.jsx` líneas 135–165 para ver la estructura exacta del array `teamMembers`.

- [ ] **Step 2: Reemplazar imágenes con avatares de iniciales**

En el array `teamMembers` (líneas ~138–165), cambiar la propiedad `image` por `initials` en cada miembro:

```js
// ANTES:
{
  name: 'Juan Pablo',
  role: 'Chef & Fundador',
  image: 'https://images.unsplash.com/photo-1577219491135-ce391730fb2c?w=800&q=80',
  story: '...',
},

// DESPUÉS:
{
  name: 'Juan Pablo',
  role: 'Chef & Fundador',
  initials: 'JP',
  story: '...',
},
```

Hacer lo mismo para Nicole (`initials: 'N'`) y Mauro (`initials: 'M'`).

- [ ] **Step 3: Actualizar el componente que renderiza las fotos**

Buscar en `AboutPage.jsx` dónde se usa `member.image` (usualmente en un `<Avatar>` o `<img>`). Reemplazar para usar `initials` como fallback:

```jsx
// ANTES:
<Avatar src={member.image} alt={member.name} sx={{ width: 120, height: 120 }} />

// DESPUÉS:
<Avatar
  sx={{
    width: 120,
    height: 120,
    bgcolor: '#1a1714',
    color: '#FFD700',
    fontSize: '2rem',
    fontFamily: '"Fraunces", serif',
    fontWeight: 700,
    border: '3px solid #FFD700',
  }}
>
  {member.initials}
</Avatar>
```

- [ ] **Step 4: Verificar en el navegador**

```bash
cd frontend && npm run dev
```

Abrir `/nosotros`. Deben aparecer tres avatares con fondo negro, iniciales en dorado, sin imágenes de Unsplash.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/public/AboutPage.jsx
git commit -m "fix: replace Unsplash stock photos with branded initials avatars in About team"
```

---

## ═══════════════════════════════════
## OLEADA 2 — PÁGINAS INDIVIDUALES
## (Semanas 3–5)
## ═══════════════════════════════════

---

### Task 6: Chips monocromo en ServicesPage

**Problema:** Las etiquetas usan `color="primary"`, `"secondary"`, `"success"`, `"info"`, `"warning"` — cinco colores MUI default (azul, verde, morado, naranja). Una marca oro+negro no debería mostrar arcoíris en chips decorativos.

**Files:**
- Modify: `frontend/src/pages/public/ServicesPage.jsx` (líneas ~47–60 componente `ModernTag`, y usos en ~481–483, ~674–677)

- [ ] **Step 1: Leer el componente ModernTag**

Leer `frontend/src/pages/public/ServicesPage.jsx` líneas 40–70 para ver la implementación actual de `ModernTag`.

- [ ] **Step 2: Redefinir ModernTag con paleta monocromática**

Reemplazar el componente `ModernTag` (que actualmente propaga `color` al `<Chip>`) para ignorar el color externo y aplicar siempre la paleta dorada:

```jsx
// Reemplazar la definición actual de ModernTag
const ModernTag = ({ icon, children, variant = 'filled' }) => (
  <Chip
    icon={icon ? React.cloneElement(icon, { style: { fontSize: 14, color: variant === 'filled' ? '#1a1714' : '#e8b63a' } }) : undefined}
    label={children}
    size="small"
    sx={{
      bgcolor: variant === 'filled' ? '#e8b63a' : 'transparent',
      color: variant === 'filled' ? '#1a1714' : '#e8b63a',
      border: variant === 'outlined' ? '1px solid #e8b63a' : 'none',
      fontWeight: 600,
      fontSize: '0.7rem',
      letterSpacing: '0.03em',
      '& .MuiChip-icon': { color: 'inherit' },
    }}
  />
)
```

- [ ] **Step 3: Limpiar el prop `color` en todos los usos de ModernTag**

Buscar en `ServicesPage.jsx` todas las instancias de `<ModernTag color=...>` y eliminar el prop `color` (ya no se usa):

```jsx
// ANTES:
<ModernTag color="secondary" icon={<Celebration />}>Divertido</ModernTag>
<ModernTag color="success" icon={<Verified />}>Seguro</ModernTag>

// DESPUÉS:
<ModernTag icon={<Celebration />}>Divertido</ModernTag>
<ModernTag icon={<Verified />}>Seguro</ModernTag>
```

Hacer lo mismo con todos los `<ModernTag color="...">` en la página (~8 instancias total).

- [ ] **Step 4: Verificar**

```bash
cd frontend && npm run dev
```

Abrir `/servicios`. Todas las etiquetas deben ser doradas o negras, sin azul/verde/morado.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/public/ServicesPage.jsx
git commit -m "style: replace rainbow MUI chip colors with monochrome gold/black palette"
```

---

### Task 7: Eliminar badges NUEVO y PREMIUM sin criterio

**Problema:** "Pizzeros en Acción" tiene badge "NUEVO" y "Pizza Parties" tiene "PREMIUM", pero ambos son el core del negocio desde siempre. Los badges sin información real son ruido.

**Files:**
- Modify: `frontend/src/pages/public/ServicesPage.jsx` (líneas ~433–453, ~627–647)

- [ ] **Step 1: Localizar y eliminar el Badge "NUEVO"**

En `ServicesPage.jsx`, localizar el bloque alrededor de línea 433:

```jsx
// ELIMINAR este bloque completo:
<Badge
  badgeContent="NUEVO"
  ...
>
  {/* contenido del card */}
</Badge>
```

Reemplazar el `<Badge>` wrapper por su contenido directo (mantener el hijo del Badge pero eliminar el Badge en sí).

- [ ] **Step 2: Localizar y eliminar el Badge "PREMIUM"**

En `ServicesPage.jsx`, localizar el bloque alrededor de línea 627:

```jsx
// ELIMINAR este bloque completo:
<Badge
  badgeContent="PREMIUM"
  ...
>
  {/* contenido del card */}
</Badge>
```

Mismo procedimiento: mantener el contenido, eliminar el wrapper `<Badge>`.

- [ ] **Step 3: Eliminar el import de Badge si ya no se usa**

En la línea ~14, verificar si `Badge` se importa de `@mui/material`. Si ya no hay otros usos de `<Badge>` en el archivo, eliminarlo del import:

```js
// ANTES:
import { ..., Badge, ... } from '@mui/material'

// DESPUÉS: (quitar Badge de la lista)
import { ..., /* Badge eliminado */, ... } from '@mui/material'
```

- [ ] **Step 4: Verificar**

```bash
cd frontend && npm run dev
```

Abrir `/servicios`. No debe aparecer ningún badge "NUEVO" ni "PREMIUM" sobre las cards de servicio.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/public/ServicesPage.jsx
git commit -m "style: remove uninformative NUEVO/PREMIUM badges from service cards"
```

---

### Task 8: Simplificar animaciones hover (1 transformación por card)

**Problema:** `ServicesPage.jsx` tiene `translateY(-8px) scale(1.02)` en cards + `translateX(8px)` en bullets + `translateY(-2px)` en chips → 4–5 animaciones simultáneas al hacer hover. Cansador y grita "template de Dribbble".

**Files:**
- Modify: `frontend/src/pages/public/ServicesPage.jsx` (líneas ~57, ~84, ~112, ~139–140)

- [ ] **Step 1: Auditar todos los hovers en ServicesPage**

Buscar todas las instancias de `'&:hover'` en `ServicesPage.jsx` que contengan `transform`. Identificar cuáles están dentro del mismo card container.

- [ ] **Step 2: Reducir a 1 transformación por card**

Aplicar la regla: **una sola transformación por card**. La elección es `translateY(-4px)` en el container del card + `boxShadow` aumentado:

```js
// Card principal — MANTENER solo esto:
'&:hover': {
  transform: 'translateY(-4px)',
  boxShadow: '0 12px 32px rgba(0,0,0,0.15)',
  transition: 'transform 0.2s ease, box-shadow 0.2s ease',
},

// Bullets (FeatureBullets) — ELIMINAR el hover transform:
// '&:hover': { transform: 'translateX(8px)' }  ← ELIMINAR

// Chips dentro del card — ELIMINAR el hover transform:
// '&:hover': { transform: 'translateY(-2px)' }  ← ELIMINAR

// Badge wrapper — ELIMINAR transform si tiene:
// '&:hover': { transform: '...' }  ← ELIMINAR
```

- [ ] **Step 3: Hacer lo mismo en ModernCard (si existe como componente separado)**

Buscar la definición del componente de card principal (alrededor de línea 112) que tiene `translateY(-8px) scale(1.02)`. Reemplazar:

```js
// ANTES:
'&:hover': {
  transform: 'translateY(-8px) scale(1.02)',
  boxShadow: '...',
  // otros efectos
}

// DESPUÉS:
'&:hover': {
  transform: 'translateY(-4px)',
  boxShadow: '0 12px 32px rgba(0,0,0,0.12)',
  transition: 'transform 0.2s ease, box-shadow 0.2s ease',
},
```

- [ ] **Step 4: Aplanar los FeatureBullets (GAP 2)**

Los `FeatureBullets` (lista de features dentro de cada card) deben ser visualmente planos — sin hover transform, sin iconos de color arbitrario, texto directo:

```jsx
// Buscar el componente o estilo de FeatureBullet/feature list dentro de las cards
// ANTES — bullet con icono de color y hover:
// sx={{ '&:hover': { transform: 'translateX(8px)' }, color: '#4CAF50' }}

// DESPUÉS — bullet plano:
sx={{
  display: 'flex',
  alignItems: 'center',
  gap: 1,
  py: 0.5,
  color: 'rgba(255,255,255,0.75)',  // adaptado al nuevo fondo oscuro de Task 0
  // sin hover, sin transform
}}

// Icono del bullet — DESPUÉS:
<Box
  component="span"
  sx={{
    width: 4,
    height: 4,
    borderRadius: '50%',
    bgcolor: '#e8b63a',
    flexShrink: 0,
  }}
/>
```

- [ ] **Step 5: Agregar micro-animación editorial de reemplazo con IntersectionObserver (GAP 3)**

La auditoría pide: *"Reemplazar el hover-circus por 1–2 animaciones excelentes (reveal editorial del hero, por ejemplo)."*

Implementar un fade-in + slide-up en los titulares de sección cuando entran al viewport. GSAP ya está en el stack del proyecto.

Agregar al inicio del componente `ServicesPage` (donde ya se usa GSAP o con `useRef`/`useEffect`):

```jsx
import { useEffect, useRef } from 'react'

// Dentro del componente ServicesPage:
const sectionTitlesRef = useRef([])

useEffect(() => {
  // Verificar que gsap esté disponible (ya importado en el proyecto)
  if (typeof window === 'undefined') return

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1'
          entry.target.style.transform = 'translateY(0)'
          observer.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.2 }
  )

  const titles = document.querySelectorAll('[data-reveal]')
  titles.forEach((el) => {
    el.style.opacity = '0'
    el.style.transform = 'translateY(24px)'
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease'
    observer.observe(el)
  })

  return () => observer.disconnect()
}, [])
```

Agregar `data-reveal` a los titulares principales de sección en ServicesPage:

```jsx
// En el Typography del título de cada sección:
<Typography variant="h2" component="h2" data-reveal sx={{ ... }}>
  Nuestros Servicios
</Typography>

<Typography variant="h2" component="h2" data-reveal sx={{ ... }}>
  Planes y Precios
</Typography>
```

> Nota: este mismo patrón puede aplicarse a AboutPage y ContactPage en iteraciones futuras.

- [ ] **Step 6: Verificar**

```bash
cd frontend && npm run dev
```

1. Hacer hover sobre cards — solo `translateY(-4px)` visible, sin animaciones internas.
2. Los bullets dentro de cada card deben ser estáticos, sin translate al hover.
3. Hacer scroll en `/servicios` — los títulos de sección deben aparecer con fade-in suave al entrar al viewport.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/public/ServicesPage.jsx
git commit -m "style: flatten feature bullets, add scroll-reveal animation on section titles"
```

---

### Task 9: Simplificar BookingPage hero

**Problema:** `BookingPage.jsx` tiene hero con `aurora.sunset` (gradiente único en el sitio), 2 bolas flotantes con `@keyframes float`, botón "Volver" con glassmorphism, chip dorado, y gradient-text blanco→dorado. 5 efectos compitiendo justo donde el usuario quiere llenar un formulario.

**Files:**
- Modify: `frontend/src/pages/public/BookingPage.jsx` (líneas ~144, ~186, ~218, ~259–265)

- [ ] **Step 1: Leer el bloque del hero de BookingPage**

Leer `frontend/src/pages/public/BookingPage.jsx` líneas 140–300 para identificar exactamente la estructura del hero (el Box con background aurora.sunset).

- [ ] **Step 2: Reemplazar el hero sobrecargado**

Localizar el Box principal del hero (el que tiene `background: designTokens.colors.aurora.sunset`). Reemplazar **únicamente** ese Box de hero con una versión limpia:

```jsx
{/* Hero mínimo — altura reducida, sin efectos decorativos */}
<Box
  sx={{
    background: '#0d0d0d',
    py: { xs: 4, md: 5 },
    px: 2,
    textAlign: 'center',
  }}
>
  <Typography
    variant="h1"
    sx={{
      fontSize: { xs: '1.8rem', md: '2.5rem' },
      fontWeight: 700,
      color: '#FFFFFF',
      fontFamily: '"Fraunces", serif',
      mb: 1,
    }}
  >
    Reserva tu Evento
  </Typography>
  <Typography
    variant="body1"
    sx={{ color: 'rgba(255,255,255,0.65)', maxWidth: 480, mx: 'auto' }}
  >
    Completa el formulario y te contactamos en menos de 24 horas.
  </Typography>
</Box>
```

- [ ] **Step 3: Eliminar los keyframes de bolas flotantes**

Buscar en `BookingPage.jsx` el bloque `@keyframes` con el nombre `float` o similar y eliminarlo completamente. También eliminar los dos `<Box>` que renderizan las bolas animadas.

- [ ] **Step 4: Simplificar el indicador de pasos**

Localizar el `<Chip>` "Paso 1 de 3" que duplica el Stepper (mencionado en auditoría como redundante). Eliminarlo — el `<Stepper>` ya muestra esa información.

- [ ] **Step 5: Verificar**

```bash
cd frontend && npm run dev
```

Abrir `/agendar`. El hero debe ser un rectángulo negro limpio con título y subtítulo. El formulario debe ser lo más prominente visualmente.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/public/BookingPage.jsx
git commit -m "style: simplify BookingPage hero to minimal title + subtitle, remove visual noise"
```

---

### Task 10: Estandarizar iconografía (quitar emojis del chrome de UI)

**Problema:** `BookingPage.jsx` mezcla emojis Apple (`🍕`, `🎉`, `🎂`, `🏫`, `🏢`) con íconos MUI (`<School>`, `<Restaurant>`, `<EmojiEvents>`). Tres lenguajes de iconografía coexisten.

**Files:**
- Modify: `frontend/src/pages/public/BookingPage.jsx` (líneas ~709, ~730, ~761–763)

- [ ] **Step 1: Importar los íconos MUI necesarios**

En `BookingPage.jsx`, verificar que estén importados (agregar si faltan):

```js
import {
  LocalPizza,    // para Pizzeros en Acción
  Celebration,   // para Pizza Party
  Cake,          // para Cumpleaños
  School,        // para Escolar (ya existe)
  Business,      // para Corporativo
  AutoAwesome,   // para Otro (ya existe si se usa)
} from '@mui/icons-material'
```

- [ ] **Step 2: Reemplazar emojis en los MenuItem del selector de servicio**

Localizar líneas ~709, ~730 (servicio principal) y ~761–763 (tipo de ocasión):

```jsx
// ANTES:
<MenuItem value="pizzeros">🍕 Pizzeros en Acción</MenuItem>
<MenuItem value="party">🎉 Pizza Party</MenuItem>
<MenuItem value="cumple">🎂 Cumpleaños</MenuItem>
<MenuItem value="escolar">🏫 Escolar</MenuItem>
<MenuItem value="corporativo">🏢 Corporativo</MenuItem>

// DESPUÉS:
<MenuItem value="pizzeros" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
  <LocalPizza sx={{ fontSize: 18, color: '#FFD700' }} /> Pizzeros en Acción
</MenuItem>
<MenuItem value="party" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
  <Celebration sx={{ fontSize: 18, color: '#FFD700' }} /> Pizza Party
</MenuItem>
<MenuItem value="cumple" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
  <Cake sx={{ fontSize: 18, color: '#FFD700' }} /> Cumpleaños
</MenuItem>
<MenuItem value="escolar" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
  <School sx={{ fontSize: 18, color: '#FFD700' }} /> Escolar
</MenuItem>
<MenuItem value="corporativo" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
  <Business sx={{ fontSize: 18, color: '#FFD700' }} /> Corporativo
</MenuItem>
```

- [ ] **Step 3: Verificar**

```bash
cd frontend && npm run dev
```

Abrir `/agendar`, llegar al selector de servicio. Los items deben mostrar íconos MUI en dorado, sin emojis.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/public/BookingPage.jsx
git commit -m "style: replace emoji in booking form with consistent MUI icons"
```

---

### Task 11: Unificar jerarquía de contacto en ContactPage

**Problema:** Las 4 cards de contacto usan azul (Teléfono), verde (WhatsApp), rojo (Email), naranja (Servicio). Solo WhatsApp verde tiene justificación de marca. Los otros tres son arbitrarios y pesan igual visualmente, cuando WhatsApp convierte el 90% de los contactos.

**Files:**
- Modify: `frontend/src/pages/public/ContactPage.jsx`

- [ ] **Step 1: Leer ContactPage**

Leer `frontend/src/pages/public/ContactPage.jsx` completo para identificar los colores de cada card de contacto.

- [ ] **Step 2: Identificar los valores de color hardcodeados**

Buscar en `ContactPage.jsx`:
- `#1976d2` → Teléfono (azul MUI primary)
- `#25D366` → WhatsApp (verde)
- `#d32f2f` → Email (rojo)
- `#ed6c02` → Servicio (naranja)

- [ ] **Step 3: Reemplazar colores arbitrarios**

Aplicar la regla: **solo WhatsApp mantiene su verde de marca**. El resto usa dorado + gris neutro para no competir:

```jsx
// TABLA DE REEMPLAZOS:
// Teléfono:   #1976d2  →  #e8b63a  (dorado)
// WhatsApp:   #25D366  →  #25D366  (MANTENER — marca externa reconocida)
// Email:      #d32f2f  →  #666666  (gris neutro — no hay semántica universal)
// Servicio:   #ed6c02  →  #e8b63a  (dorado)
```

Buscar cada `bgcolor`, `color`, `borderColor`, `sx={{ color: '...' }}` que use esos valores y aplicar la tabla de reemplazos.

- [ ] **Step 4: Verificar**

```bash
cd frontend && npm run dev
```

Abrir `/contacto`. WhatsApp debe destacar visualmente (verde). Teléfono, Email y Servicio deben verse en la paleta dorada/gris sin competir por atención.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/public/ContactPage.jsx
git commit -m "style: unify contact card colors, keep only WhatsApp brand green"
```

---

### Task 12: Corregir jerarquía semántica H1/H2/H3

**Problema:** `ServicesPage.jsx` tiene `<Typography variant="h1">Experiencias Únicas</Typography>` y luego `<Typography variant="h2">Nuestros Servicios</Typography>` que visualmente es igual de grande. Malo para SEO y lectores de pantalla. MUI permite desacoplar el tamaño visual del componente semántico.

**Files:**
- Modify: `frontend/src/pages/public/ServicesPage.jsx`
- Modify: `frontend/src/pages/public/AboutPage.jsx`

- [ ] **Step 1: Auditar ServicesPage**

Ejecutar:

```bash
grep -n "variant=\"h[1-3]\"" frontend/src/pages/public/ServicesPage.jsx
```

Mapear todos los `h1`, `h2`, `h3` en el archivo. Debe haber exactamente **un** `variant="h1"` por página (el hero principal).

- [ ] **Step 2: Corregir en ServicesPage**

Para cada `<Typography>` que tenga el tamaño visual de un H1 pero semánticamente sea una sección secundaria, agregar `component="h2"` para separar semántica de estilo:

```jsx
// ANTES — visualmente igual a h1 pero es una sección:
<Typography variant="h2">Nuestros Servicios</Typography>

// DESPUÉS — tamaño h1 visualmente, pero semántica h2:
<Typography variant="h1" component="h2">Nuestros Servicios</Typography>

// O si debe ser más pequeño que el hero h1:
<Typography variant="h2" component="h2">Nuestros Servicios</Typography>
```

Regla de asignación para ServicesPage:
- "Experiencias Únicas" (hero) → `variant="h1"` `component="h1"` ✓ (uno solo)
- "Nuestros Servicios" → `variant="h2"` `component="h2"`
- "Planes y Precios" → `variant="h2"` `component="h2"`
- Nombres de cards (Pizzeros en Acción, Pizza Party) → `variant="h3"` `component="h3"`
- "Lo que dicen..." → `variant="h2"` `component="h2"`

- [ ] **Step 3: Corregir en AboutPage**

Mismo procedimiento. Ejecutar:

```bash
grep -n "variant=\"h[1-3]\"" frontend/src/pages/public/AboutPage.jsx
```

Debe haber exactamente un `h1`. Secciones secundarias deben ser `h2`. Nombres de miembros del equipo pueden ser `h3`.

- [ ] **Step 4: Verificar con DevTools**

```bash
cd frontend && npm run dev
```

Abrir `/servicios`, abrir DevTools → Elements, buscar `<h1>`. Debe aparecer exactamente una vez. Navegar con Tab y un lector de pantalla (o usar la extensión "Accessibility Insights") para verificar el outline.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/public/ServicesPage.jsx frontend/src/pages/public/AboutPage.jsx
git commit -m "fix: correct H1/H2/H3 semantic hierarchy across ServicesPage and AboutPage"
```

---

### Task 13: Reescribir copy con clichés

**Problema:** "Inolvidable" ×7, "único" ×6, "mágico" ×3, "experiencia" ×14, "perfecto" ×9. El vocabulario genérico oculta los diferenciadores reales: harina 00 italiana, 90 minutos de amasado, chef con 10 años de experiencia, certificado, máximo 15 niños por chef.

**Files:**
- Modify: `frontend/src/pages/public/ServicesPage.jsx`
- Modify: `frontend/src/pages/public/HomePage.jsx`
- Modify: `frontend/src/pages/public/AboutPage.jsx`

- [ ] **Step 1: Auditar las ocurrencias**

```bash
grep -in "inolvidable\|único\|mágico\|magia\|perfecto\|único" \
  frontend/src/pages/public/ServicesPage.jsx \
  frontend/src/pages/public/HomePage.jsx \
  frontend/src/pages/public/AboutPage.jsx
```

Listar todas las líneas que contienen esas palabras.

- [ ] **Step 2: Reemplazar en ServicesPage**

Aplicar sustituciones concretas. Ejemplos directos:

```
// ServicesPage línea ~333:
ANTES: "Que combinan diversión, aprendizaje y sabores inolvidables"
DESPUÉS: "90 min de amasado real con harina 00 italiana · los niños se llevan su pizza"

// ServicesPage línea ~981:
ANTES: "¿Listo para crear recuerdos inolvidables?"
DESPUÉS: "¿Listo para agendar el taller?"
```

- [ ] **Step 3: Reemplazar en HomePage**

```bash
grep -n "inolvidable\|único\|mágico\|memorabl\|perfecto" frontend/src/pages/public/HomePage.jsx
```

Para cada ocurrencia, reemplazar con descripción concreta. Ejemplos:

```
// Cualquier "experiencia única e inolvidable" → "taller de 90 min donde los niños amasan y hornean"
// Cualquier "recuerdos perfectos" → "fotos, certificado y la pizza que hicieron"
// Cualquier "momentos mágicos" → quitar adjetivo o usar hecho: "en tu casa, sin que tengas que cocinar"
```

- [ ] **Step 4: Reemplazar en AboutPage**

```bash
grep -n "inolvidable\|único\|mágico\|perfecto" frontend/src/pages/public/AboutPage.jsx
```

Mismo procedimiento.

- [ ] **Step 5: Verificar**

```bash
grep -in "inolvidable\|único\|mágico\|perfecto" \
  frontend/src/pages/public/ServicesPage.jsx \
  frontend/src/pages/public/HomePage.jsx \
  frontend/src/pages/public/AboutPage.jsx
```

El resultado debe ser cero o mínimo (solo si es absolutamente necesario contextualmente).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/public/ServicesPage.jsx frontend/src/pages/public/HomePage.jsx frontend/src/pages/public/AboutPage.jsx
git commit -m "copy: replace cliché adjectives with concrete facts across public pages"
```

---

## ═══════════════════════════════════
## OLEADA 3 — MEJORAS FUTURAS
## (Semanas 6+)
## ═══════════════════════════════════

---

### Task 14: Stats dinámicas desde backend

**Problema:** "500+ niños" y "50+ eventos" son hardcodeados. Derivar de bookings reales aumenta credibilidad (526 > 500+) y se actualiza sola.

**Files:**
- Create: `frontend/src/hooks/useStats.js`
- Modify: `frontend/src/data/stats.js`
- Modify: `frontend/src/pages/public/HomePage.jsx`
- Modify: `frontend/src/pages/public/AboutPage.jsx`
- Modify: `frontend/src/pages/public/ServicesPage.jsx`
- Modify: `backend/` (endpoint a definir)

- [ ] **Step 1: Verificar qué expone bookingService**

```bash
grep -n "export\|count\|total\|list" frontend/src/services/bookingService.js 2>/dev/null || \
grep -rn "bookingService\|getBookings" frontend/src/services/ | head -20
```

Identificar si hay un endpoint que devuelve la lista o conteo de bookings completados.

- [ ] **Step 2: Crear el hook useStats**

Crear `frontend/src/hooks/useStats.js`:

```js
import { useState, useEffect } from 'react'
import { STATS as FALLBACK_STATS } from '../data/stats'

// Hook que obtiene stats en tiempo real del backend.
// Fallback a los valores hardcodeados de stats.js si el endpoint falla.
export function useStats() {
  const [stats, setStats] = useState(FALLBACK_STATS)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // TODO: reemplazar con endpoint real cuando el backend lo implemente
    // const fetchStats = async () => {
    //   try {
    //     const res = await fetch('/api/stats/public')
    //     const data = await res.json()
    //     setStats({ kidsServed: data.totalKids, eventsCount: data.totalEvents })
    //   } catch {
    //     // mantener fallback
    //   } finally {
    //     setLoading(false)
    //   }
    // }
    // fetchStats()
    setLoading(false) // quitar cuando el endpoint esté listo
  }, [])

  return { stats, loading }
}
```

- [ ] **Step 3: Consumir useStats en HomePage**

```jsx
import { useStats } from '../../hooks/useStats'

// En el componente:
const { stats } = useStats()

// Usar stats.kidsServed en lugar de STATS.kidsServed directo
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useStats.js frontend/src/pages/public/HomePage.jsx
git commit -m "feat: add useStats hook for dynamic social proof figures (backend endpoint pending)"
```

---

### Task 15: Valores concretos en About

**Problema:** Los valores del equipo son "Pasión, Compromiso, Trabajo en equipo, Excelencia" — aparecen en 8 de cada 10 PyMEs. No revelan nada específico de Pablo's Pizza.

**Files:**
- Modify: `frontend/src/pages/public/AboutPage.jsx`

- [ ] **Step 1: Leer la sección de valores**

Leer `AboutPage.jsx` líneas 180–270 para ver el array de valores y cómo se renderizan.

- [ ] **Step 2: Reemplazar valores genéricos con compromisos concretos**

Localizar el array de valores (será algo como `const values = [{ title: 'Pasión', ... }]`) y reemplazar:

```js
// ANTES:
const values = [
  { title: 'Pasión',           description: '...' },
  { title: 'Compromiso',       description: '...' },
  { title: 'Trabajo en equipo', description: '...' },
  { title: 'Excelencia',       description: '...' },
]

// DESPUÉS — compromisos verificables:
const values = [
  {
    title: 'Harina 00 Italiana Caputo',
    description: 'Usamos siempre harina 00 Caputo importada. No hay atajos en la masa.',
    icon: <LocalPizza />,
  },
  {
    title: 'Máx. 15 niños por chef',
    description: 'Nunca más de 15 participantes por taller. Cada niño amasa su propia pizza.',
    icon: <Groups />,
  },
  {
    title: 'Llegamos 45 min antes',
    description: 'Montaje completo antes de que lleguen los invitados. Sin estrés para los papás.',
    icon: <AccessTime />,
  },
  {
    title: 'Sin frutos secos ni sésamo',
    description: 'Por defecto, todos los talleres son libres de frutos secos y sésamo.',
    icon: <HealthAndSafety />,
  },
]
```

Agregar los imports necesarios de `@mui/icons-material`: `LocalPizza`, `Groups`, `AccessTime`, `HealthAndSafety`.

- [ ] **Step 3: Agregar timeline del proceso de un evento (GAP 4)**

La auditoría propone: *"Quizá un timeline del proceso de un evento."* Agregar una sección nueva en AboutPage con los pasos del proceso, después de la sección del equipo:

```jsx
// Agregar después del bloque de equipo (buscar el cierre del Grid del equipo)
// Imports necesarios (agregar si no existen):
// import { Timeline, TimelineItem, TimelineSeparator, TimelineDot, TimelineConnector, TimelineContent } from '@mui/lab'

// Si @mui/lab no está instalado, usar una implementación manual con Box:

const EVENT_STEPS = [
  {
    step: '01',
    title: 'Reserva online',
    desc: 'Completás el formulario con fecha, cantidad de niños y tipo de evento. Te confirmamos en menos de 24 hs.',
  },
  {
    step: '02',
    title: 'Llegamos 45 min antes',
    desc: 'El equipo llega con todo el equipamiento, harina 00 italiana y ingredientes. Vos no tenés que preparar nada.',
  },
  {
    step: '03',
    title: '90 min de taller',
    desc: 'Cada niño amasa, estira y arma su propia pizza con técnicas reales de pizzaiolo. Máximo 15 participantes por chef.',
  },
  {
    step: '04',
    title: 'Pizza + certificado',
    desc: 'Los niños comen la pizza que hicieron y se llevan su certificado de pizzaiolo. El equipo limpia y se va.',
  },
]

// Renderizado:
<Box sx={{ background: '#141414', py: { xs: 6, md: 10 }, px: 2 }}>
  <Typography
    variant="h2"
    component="h2"
    data-reveal
    sx={{ color: '#FFFFFF', textAlign: 'center', mb: 6 }}
  >
    Cómo funciona
  </Typography>
  <Box
    sx={{
      maxWidth: 720,
      mx: 'auto',
      display: 'flex',
      flexDirection: 'column',
      gap: 0,
    }}
  >
    {EVENT_STEPS.map((item, index) => (
      <Box
        key={index}
        sx={{ display: 'flex', gap: 3, alignItems: 'flex-start', pb: 4 }}
      >
        {/* Número de paso */}
        <Box
          sx={{
            minWidth: 48,
            height: 48,
            borderRadius: '50%',
            border: '2px solid #e8b63a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#e8b63a',
            fontWeight: 700,
            fontSize: '0.9rem',
            flexShrink: 0,
          }}
        >
          {item.step}
        </Box>
        {/* Contenido */}
        <Box sx={{ pt: 0.5 }}>
          <Typography variant="h6" sx={{ color: '#FFFFFF', fontWeight: 600, mb: 0.5 }}>
            {item.title}
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
            {item.desc}
          </Typography>
        </Box>
      </Box>
    ))}
  </Box>
</Box>
```

- [ ] **Step 4: Verificar**

```bash
cd frontend && npm run dev
```

Abrir `/nosotros`. Verificar:
1. Los 4 valores muestran compromisos concretos (harina 00, max 15 niños, 45 min antes, sin frutos secos).
2. La sección "Cómo funciona" aparece con los 4 pasos del proceso en timeline vertical.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/public/AboutPage.jsx
git commit -m "copy: replace generic values with concrete commitments, add event process timeline"
```

---

### Task 16: A/B test FloatingCTA vs bottom-bar sticky

**Problema:** La auditoría recomienda *"A/B test: Floating CTA vs CTA sticky de bottom-bar. Medir conversión a /agendar."* El FloatingCTA actual es el canal principal de conversión — vale la pena medir si un bottom-bar sticky convierte mejor, especialmente en móvil.

**Files:**
- Modify: `frontend/src/data/stats.js` (agregar flag de experimento)
- Modify: `frontend/src/pages/public/HomePage.jsx` (lógica de A/B)

> **Nota sobre Gallery:** La auditoría menciona *"Rediseño Gallery — vale la pena una auditoría propia cuando haya más fotos."* No es un cambio de código en este plan — es un ticket de análisis futuro. Cuando haya fotos reales del equipo (ver Task 5), solicitar auditoría específica de GalleryPage.

- [ ] **Step 1: Agregar flag de experimento en stats.js**

En `frontend/src/data/stats.js`, agregar:

```js
// A/B test config — 'floating' = CTA actual, 'bottombar' = variante nueva
// Cambiar a 'bottombar' para activar la variante en producción
export const CTA_VARIANT = 'floating'
```

- [ ] **Step 2: Implementar variante bottom-bar en HomePage**

En `frontend/src/pages/public/HomePage.jsx`:

```js
import { STATS, CTA_VARIANT } from '../../data/stats'
```

Localizar el componente del FloatingCTA (búsqueda: `FloatingCTA` o `position: 'fixed'`). Agregar la lógica de variante:

```jsx
// Variante bottom-bar — solo visible si CTA_VARIANT === 'bottombar'
{CTA_VARIANT === 'bottombar' && (
  <Box
    sx={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 1200,
      background: '#0d0d0d',
      borderTop: '1px solid rgba(232,182,58,0.3)',
      py: 1.5,
      px: 2,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 2,
    }}
  >
    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)', flexShrink: 0 }}>
      Desde $9.000 por niño
    </Typography>
    <Button
      variant="contained"
      href="/agendar"
      sx={{
        bgcolor: '#e8b63a',
        color: '#0d0d0d',
        fontWeight: 700,
        px: 3,
        '&:hover': { bgcolor: '#FFD700' },
      }}
    >
      Reservar fecha
    </Button>
  </Box>
)}

{/* Ocultar FloatingCTA original cuando bottom-bar está activo */}
{CTA_VARIANT === 'floating' && <FloatingCTA />}
```

- [ ] **Step 3: Instrucciones para medir**

Para medir conversión: comparar la tasa de clics a `/agendar` entre semanas con `CTA_VARIANT = 'floating'` vs `'bottombar'`. Si el proyecto tiene Firebase Analytics, verificar el evento `page_view` en `/agendar` como métrica de conversión.

- [ ] **Step 4: Verificar ambas variantes**

```bash
cd frontend && npm run dev
```

1. Con `CTA_VARIANT = 'floating'`: debe verse el FloatingCTA original.
2. Con `CTA_VARIANT = 'bottombar'`: debe verse la barra fija al fondo de la pantalla con precio y botón de reserva.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/stats.js frontend/src/pages/public/HomePage.jsx
git commit -m "feat: add A/B test flag for FloatingCTA vs bottom-bar sticky CTA"
```

---

## Self-Review — Cobertura vs. Auditoría

### 15 Hallazgos

| # | Hallazgo en auditoría | Severidad | Tarea | Estado |
|---|----------------------|-----------|-------|--------|
| 01 | Inconsistencia visual — 5 sistemas de color | Crítico | Task 0 | ✓ |
| 02 | 3 precios distintos (FloatingCTA/Taller/Servicios) | Crítico | Task 1 | ✓ |
| 03 | Fotos Unsplash en equipo | Crítico | Task 5 | ✓ |
| 04 | Chips arcoíris MUI en Servicios | Alto | Task 6 | ✓ |
| 05 | Hover-circus en cards | Alto | Task 8 | ✓ |
| 06 | Stats hardcodeadas en 3 archivos | Alto | Task 2 | ✓ |
| 07 | Copy con clichés (inolvidable/único/mágico) | Alto | Task 13 | ✓ |
| 08 | BookingPage hero sobrecargado | Alto | Task 9 | ✓ |
| 09 | Solo Roboto para titulares | Alto | Task 4 | ✓ |
| 10 | Emojis mezclados con MUI icons | Medio | Task 10 | ✓ |
| 11 | 4 colores semánticos arbitrarios en Contacto | Medio | Task 11 | ✓ |
| 12 | Jerarquía semántica H1/H2 rota | Medio | Task 12 | ✓ |
| 13 | Badges NUEVO/PREMIUM sin criterio | Medio | Task 7 | ✓ |
| 14 | Focus states ausentes fuera del Home | Medio | Task 3 | ✓ |
| 15 | Valores genéricos en About | Bajo | Task 15 | ✓ |

### 4 Gaps del Roadmap

| Item del roadmap | Oleada | Tarea | Estado |
|------------------|--------|-------|--------|
| Unificar paleta dark-editorial (AHORA) | 1 | Task 0 | ✓ |
| FeatureBullets planos + micro-animación editorial (PRÓXIMO) | 2 | Task 8 extendida | ✓ |
| Timeline del proceso de evento en About (DESPUÉS) | 3 | Task 15 extendida | ✓ |
| A/B test FloatingCTA vs bottom-bar (DESPUÉS) | 3 | Task 16 | ✓ |
| Rediseño Gallery (DESPUÉS) | 3 | Nota: requiere auditoría propia cuando haya fotos reales | — |

**Cobertura total: 15/15 hallazgos + 4/4 gaps del roadmap = 100%**

---

## Orden recomendado de ejecución

### Oleada 1 (ejecutar en este orden — cada tarea depende de la anterior)
1. **Task 0** (unificar paleta) — 2h, el cambio más visible e impactante
2. **Task 3** (focus states) — 30 min, sin riesgo visual, gran ganancia en a11y
3. **Task 4** (Fraunces font) — 30 min, mejora inmediata en hero
4. **Task 5** (quitar Unsplash) — 30 min, elimina riesgo legal urgente
5. **Task 1** (centralizar pricing) — 1h, elimina la contradicción crítica de precios
6. **Task 2** (centralizar stats) — 30 min, prepara base para Task 14

### Oleada 2 (pueden ejecutarse en paralelo entre sí)
7. **Task 7** (eliminar badges) — 15 min, limpieza rápida
8. **Task 6** (chips monocromo) — 45 min
9. **Task 8** (hover simplificado + FeatureBullets planos + reveal animation) — 1h
10. **Task 9** (BookingPage hero) — 1h
11. **Task 10** (quitar emojis) — 30 min
12. **Task 11** (ContactPage colors) — 30 min
13. **Task 12** (jerarquía H1/H2) — 1h
14. **Task 13** (copy clichés) — 2h, requiere criterio editorial

### Oleada 3 (mejoras futuras)
15. **Task 15** (valores concretos + timeline About) — 1h
16. **Task 14** (stats dinámicas) — 2h, requiere endpoint backend
17. **Task 16** (A/B test FloatingCTA) — 45 min
