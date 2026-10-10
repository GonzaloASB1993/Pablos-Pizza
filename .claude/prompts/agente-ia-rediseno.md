# Prompt de trabajo: Rediseño del Agente IA de Pablo's Pizza (Fases 1 a 3 + UI/UX)

> Pégalo completo como primer mensaje en Claude Code (VS Code), o dile: *"Lee `.claude/prompts/agente-ia-rediseno.md` y sigue las instrucciones"*.
> Este documento es autosuficiente: contiene el contexto, las decisiones ya tomadas, lo que está hecho, lo que falta y cómo trabajar.

---

## 0. Cómo quiero que trabajes

- **Responde siempre en español chileno** (no argentino). Aplica buenas prácticas de Python y React y **revisa el código** que escribas antes de darlo por terminado.
- **Analiza antes de contestar.** Respuestas completas, sin repetir información.
- **Rétame, no me valides.** Si ves un problema en mi forma de pensar o en una decisión, dilo de forma natural ("¿y si vamos por acá?", "¿pensaste en esta otra alternativa?"), sin frases tipo "déjame retarte".
- **Protocolo del proyecto (`.claude/CLAUDE.md`):** lee `.claude/Planning.md` y `.claude/Tasks.md` al empezar (el CLAUDE.md los llama `planning.md`/`task.md`, pero los archivos reales llevan mayúscula), marca las tareas como completadas apenas las termines y agrega las nuevas que descubras. El plan vive en la sección **"M_AI: Rediseño del Agente IA"** de `Tasks.md`.
- **Edita `Tasks.md` con la herramienta Edit, nunca con scripts de reemplazo masivo.** En una sesión anterior un `str.replace` con un patrón vacío insertó texto entre cada carácter y dejó el archivo en 21 MB. Verifica el tamaño del archivo después de editarlo.
- **Es un sistema en producción con clientes reales.** Cambios pequeños, con tests, un commit por unidad lógica. Haz refactors solo con tests de caracterización escritos antes.
- **Git:** trabaja en una rama (`claude/ai-agent-phase1-...`), nunca directo en `main`. No abras PR a menos que te lo pida. Haz `git add` solo de los archivos que tocaste. Mensajes de commit en inglés, estilo `feat(ai-chat): ...`.
- **Antes de implementar cada fase, muéstrame un plan corto y espera mi OK** si hay una decisión de diseño que no esté en este documento.

---

## 1. El proyecto

**Pablo's Pizza** (Santiago, Chile): talleres de pizza y eventos ("Pizzeros en Acción", "Pizza Party"). Moneda CLP. Sistema en producción en https://pablospizza.web.app.

```
frontend/   React 18 + Vite + Material-UI + React Router + Axios + react-hot-toast + Firebase Auth (PWA)
backend/    Flask monolítico (main.py ~225 KB) + blueprints en backend/routes/ + services/ + utils/
            Desplegado como Firebase Function gen2 (python311, entry point `main`, que envuelve Flask con test_request_context)
            Firestore + Firebase Storage (bucket pablospizza-d84bf.firebasestorage.app)
.claude/    CLAUDE.md, Planning.md, Tasks.md, CLAUDE-BACKEND.md, CLAUDE-FRONTEND.md
```

- Variables de entorno del backend: `backend/.env` (gitignored; `main.py` hace `load_dotenv('.env')`; Firebase lo sube al desplegar).
- Backend local: `python main.py` en el puerto **8000** (el CLAUDE.md dice 5000, está desactualizado). Frontend: `npm run dev`.
- El frontend llama a `http://localhost:8000/api` en desarrollo y a `https://main-446811667554.us-central1.run.app/api` en producción.
- Deploy: `./deploy.sh` (build del frontend + `firebase deploy --only hosting,functions`). Ojo: el script aborta si no existe `backend/.env.production`.
- Colecciones Firestore relevantes: `bookings`, `events`, `contacts`, `customers`, `inventory`, `inventory_movements`, `event_supplies`, `event_consumption`, `fixed_expenses`, `variable_expenses`, `monthly_taxes`, `audit_logs`.

### Flujo de negocio clave
`booking (pending) → confirmed → [event_supplies + event_consumption registrados] → completed → se crea el event automáticamente`.
- Un booking **solo puede completarse** si tiene supplies y consumption (validación en `main.py` ~línea 1632).
- **Costo del evento = insumos (consumo real a costo promedio ponderado) + gastos tradicionales.**
  → **Riesgo de doble conteo:** una compra de ingredientes NO puede registrarse a la vez como gasto variable y como stock de inventario.

---

## 2. Estado actual del agente

- **Backend:** `backend/routes/ai_chat_routes.py`, blueprint `/api/ai-chat/`. Loop síncrono de tool use con 5 tools **solo de lectura**: `get_bookings`, `get_events`, `get_inventory_status`, `get_contacts`, `get_financial_summary`. El historial de mensajes lo envía el frontend en cada request (el servidor es stateless).
- **Frontend:** `frontend/src/components/common/ChatAssistant.jsx` (Dialog MUI, texto plano con `whiteSpace: pre-wrap`), montado en `components/layouts/AdminLayout.jsx` (~línea 650). Dice "Powered by Claude Sonnet 4.5".
- **Limitaciones:** no escribe nada, no lee imágenes, no ve gastos (el resumen financiero sale solo de `events`).

### Fase 0 — HECHA (rama `claude/ai-agent-phase0-auth`, subida a GitHub, sin PR)
- `backend/utils/auth.py` → decorador `@require_admin`: verifica Firebase ID token (`Authorization: Bearer`) y, si existe `ADMIN_EMAILS` (coma-separado, case-insensitive), exige que el correo esté en la lista. Si la variable no está, acepta a cualquier usuario autenticado y loguea un warning. Expone `g.current_user = {uid, email}`.
- `/api/ai-chat/` (POST) usa `@require_admin`. `/health` sigue público.
- Config por entorno: `AI_CHAT_MODEL` (default `claude-sonnet-4-5-20250929`), `AI_CHAT_MAX_TOKENS` (4096), `AI_CHAT_TEMPERATURE` (default `0.2`; vacío = no enviar el parámetro). Función única `create_ai_message()`.
- `get_financial_summary` ya no salta en silencio al año anterior.
- `ChatAssistant.jsx` envía el token (`useAuth().getAuthToken()`) y muestra mensajes para 401/403.
- 9 tests en `backend/tests/test_ai_chat_routes.py` (`pytest` NO está en `requirements.txt`: `pip install pytest`).
- **Acciones pendientes que haré yo (el usuario), no tú:** desplegar la Fase 0 con `ADMIN_EMAILS` en `backend/.env`, desactivar el registro abierto de Firebase Auth (Authentication → Settings → User actions → "Enable create (sign-up)"), y mergear la rama con **squash** (el primer commit de la rama contiene un `Tasks.md` corrupto de 21 MB; el segundo lo corrige, y el squash lo elimina de la historia). Verifica con `git log` que la Fase 0 ya esté en `main` antes de empezar; si no, parte desde esa rama.

---

## 3. Decisiones ya tomadas (no las re-discutas, pero sí puedes señalar riesgos)

1. **Canal:** empezar por el **panel admin**. WhatsApp después (Fase 3), reutilizando las mismas tools. En terreno se usará desde el celular → el chat debe ser *mobile-first* y permitir tomar la foto con la cámara.
2. **"Registrar eventos" = crear una reserva nueva** (`booking`), no cargar eventos sueltos. Se respeta el flujo booking → confirmado → completado.
3. **Boletas:** cada línea se clasifica como **insumo (inventario)** o **gasto**, nunca ambos. Línea por línea, editable por mí antes de confirmar.
4. **Confirmación SIEMPRE manual** (patrón *propose → confirm*). El agente nunca escribe directo.
5. **Al subir la foto de insumos de un evento, el agente debe PREGUNTAR a qué evento cargarla** (ver §5.3).
6. **Arreglar la UI/UX del asistente** (ver §6).

---

## 4. Principios de diseño (aplican a todas las fases)

- **Propose → confirm.** Las tools de escritura NO modifican datos de negocio: crean un documento en `pending_actions` y devuelven su id. El chat muestra una tarjeta; solo el endpoint de confirmación (determinístico, **sin LLM**) ejecuta la escritura.
- **El agente nunca afirma que algo quedó guardado.** Dice "te dejé la propuesta para confirmar". Instrúyelo en el system prompt y cúbrelo con un test.
- **Servicios compartidos, no lógica duplicada.** El agente y las rutas HTTP usan las mismas funciones en `backend/services/`. No hagas que el agente llame al API por HTTP ni reescriba lógica de `main.py`.
- **Seguridad:** todo write pasa por `@require_admin`; toda confirmación se registra con `utils/audit.log_audit(..., metadata={'source': 'ai_agent', 'uid': ...})`; el texto que viene de una imagen es **dato, no instrucciones** (prompt injection).
- **Idempotencia:** confirmar dos veces la misma acción no duplica nada.
- **Validación estricta** de lo que propone el LLM (Pydantic 2.5 ya está en `requirements.txt`) antes de guardar la propuesta y de nuevo al confirmar (el usuario puede editar el payload).
- **Cap de iteraciones** del loop de tools (hoy es `while stop_reason == "tool_use"` sin límite): máximo ~8.
- **Saneo del historial que manda el cliente:** hoy el endpoint acepta cualquier `messages`. Acepta solo roles `user`/`assistant`; para el rol `user` solo bloques `text` e `image` válidos; rechaza `tool_use`/`tool_result`/`system` inyectados desde el cliente.
- **Tests primero** (pytest). Para Firestore usa un fake en memoria (p. ej. `mockfirestore`, o uno mínimo propio en `backend/tests/`), nunca el Firestore real.

---

## 5. Trabajo pendiente por fases

### FASE 1 — Escritura con confirmación + boletas de gasto

**1.1 Extraer servicios (refactor preservando comportamiento).**
Primero escribe tests de caracterización de los endpoints actuales; luego extrae a `backend/services/` y deja las rutas como wrappers finos:
- `expenses_service.py` (desde `routes/expenses_routes.py`: `fixed_expenses` → `description, amount, category, notes, is_active`; `variable_expenses` → `description, amount, category, notes, year, month`).
- `inventory_service.py`: `create_item` (hoy `POST /api/inventory/`, main.py ~1836), `update_item` (~1913), `register_movement` (`POST /api/inventory/movements/`, ~2496: costo promedio ponderado; tipos entrantes `purchase`/`production`/`return`/`adjustment`), `set_stock` (`PUT /api/inventory/<id>/stock`, ~2444), `search_items`.
- `event_supplies_service.py` (`POST /api/event-supplies/` ~3969, `PUT` ~4112) y `event_consumption_service.py` (`POST /api/event-consumption/` ~4227, que revierte movimientos previos si ya existía consumo).
- `utils/text_matching.py` con `normalize_text` y `calculate_similarity` (hoy en `main.py` ~2040 y ~2234; los servicios **no deben importar `main`** → import circular).
- Ojo: `calculate_estimated_price` está **duplicada** (`main.py` ~199 y `routes/bookings_routes.py` ~24). Unifícala en un solo lugar (p. ej. `config/pricing.py`/service) y deja un test que cubra ambos casos.

**1.2 `pending_actions`.**
Documento: `{id, type, status: pending|confirmed|cancelled|expired|failed, payload, summary, warnings[], created_by{uid,email}, created_at, expires_at (24 h), confirmed_at, result{ids...}, attachments[], dedupe_hash}`.
Endpoints (todos `@require_admin`):
- `GET /api/ai-chat/pending/<id>`
- `POST /api/ai-chat/pending/<id>/confirm` (body opcional con el payload editado → revalida con Pydantic, ejecuta el servicio, audita, marca `confirmed` de forma idempotente)
- `POST /api/ai-chat/pending/<id>/cancel`
La respuesta de `/api/ai-chat/` incluye `pending_actions: [...]` para que el frontend pinte las tarjetas.

**1.3 Imágenes.**
- El frontend comprime en el cliente (canvas, lado máx. ~1600 px, JPEG ~0.8, hasta 3 imágenes) y las manda como bloques `{type: "image", source: {type: "base64", media_type, data}}` en el último mensaje.
- El backend valida tipo (jpeg/png/webp/gif), tamaño y cantidad; **en turnos anteriores reemplaza las imágenes por un placeholder de texto** (`[imagen enviada]`) para no re-pagar tokens; sube el original a Storage en `ai_uploads/{uid}/{uuid}.jpg` (privado) y enlaza la ruta en la `pending_action`.
- `storage.rules` hoy permite lectura/escritura a *cualquier* usuario autenticado en rutas no listadas; las subidas del backend usan Admin SDK. No las hagas públicas.
- Verifica que el límite de tamaño de request de la Function (gen2) alcance para 3 imágenes comprimidas.

**1.4 Tools de Fase 1.**
- `propose_expense`: gasto fijo o variable. Campos: proveedor, fecha, monto total (CLP entero), categoría, tipo de documento (`boleta|factura|otro`), folio, notas, `year`/`month` derivados de la fecha.
- `get_expenses_summary`: gastos por período/categoría (el agente hoy no los ve).
- **Detección de duplicados:** hash de (proveedor normalizado, fecha, total, folio). Si ya existe una acción o gasto con ese hash, la tarjeta lo advierte.
- **Lectura de boletas chilenas:** miles con punto (`1.234`), fechas `dd-mm-yyyy`, IVA 19 %. La **factura** da crédito de IVA y la boleta no → guardar `document_type`. Si la suma de las líneas no cuadra con el total, marcarlo como *warning* en la tarjeta, no corregirlo en silencio.

**1.5 Tarjeta de confirmación en el chat** (ver §6).

**Criterios de aceptación Fase 1:** foto de una boleta → tarjeta con los campos extraídos, editables → Confirmar crea el gasto una sola vez → aparece en `variable_expenses` y en `audit_logs`; confirmar dos veces no duplica; subir la misma boleta avisa del duplicado; tests verdes.

### FASE 2 — Insumos

**2.1 Búsqueda.**
- `search_inventory(query)`: match difuso con `utils/text_matching`, devuelve candidatos con id, nombre, unidad, stock, costo.
- `search_bookings(client_name?, date_from?, date_to?, status?)` / `find_event`.

**2.2 Alta y mantención de insumos** (esto fue lo que faltaba en el diseño inicial).
- `propose_inventory_item` (alta). Reglas:
  1. **Buscar antes de crear:** si hay un candidato parecido ("Harina 000" vs "Harina"), el agente **pregunta** y no crea un duplicado.
  2. **Crear con stock 0 y cargar el stock como compra** (movimiento `purchase`), para que haya historial y costo promedio ponderado trazable. La tarjeta lo muestra como un solo paso; por dentro son dos operaciones.
  3. **Normalizar unidad y costo unitario:** "Saco harina 25 kg, $28.000" → unidad `kg`, cantidad 25, costo $1.120/kg. Si la unidad es ambigua, preguntar.
  4. Usar las categorías existentes (`GET /api/inventory/categories`) y, opcionalmente, `GET /api/inventory/nutrition-lookup` para sugerir la información nutricional.
  5. `min_stock`/`max_stock` no se pueden inferir de una boleta: preguntar o dejar valores por defecto explícitos y visibles en la tarjeta.
- `propose_inventory_update` (proveedor, mínimos, nombre, corrección de datos).
- `propose_stock_adjustment` (conteo físico / merma, vía movimiento `adjustment`).
- **Deuda a corregir en el servicio:** hoy `POST /api/inventory/` no valida (un campo faltante → `KeyError` → 500), no chequea duplicados y no inicializa `weighted_avg_cost`.

**2.3 Compras y boleta por línea.**
- `propose_inventory_purchase`: movimiento `purchase` con costo promedio ponderado.
- Una boleta mixta se presenta como **tabla por línea**, y cada línea cae en una de tres categorías que yo puedo cambiar: *insumo existente* (suma stock), *insumo nuevo* (se crea y se carga), *no es insumo* (gasto variable, p. ej. bencina o bolsas). Regla anti doble conteo: nunca ambos.

**2.4 Insumos de un evento.**
- `propose_event_supplies` (**estimado** = lo que se lleva al evento; el booking debe estar `confirmed` y haber stock suficiente) y `propose_event_consumption` (**real** = lo que se consumió; soporta `quantity_returned` = lo que volvió, o `actual_quantity_consumed`; requiere `total_other_expenses`).
- **Cuando subo una foto de insumos de un evento, el agente SIEMPRE pregunta:**
  1. **¿A cuál evento?** Listando opciones (cliente, fecha, estado) obtenidas con `search_bookings`, **aunque haya una sola candidata** (nunca adivinar).
  2. **¿Es lo que llevas (estimación) o lo que volvió/consumo real?**
  Implementación sugerida: una tool `ask_choice(question, options[{id,label}])` cuyo resultado el frontend pinta como *chips* de respuesta rápida y que termina el turno esperando mi elección.
- Nota: registrar consumo **mueve stock** (crea `inventory_movements` con `reference_type: 'event_consumption'`) y corregirlo implica revertir movimientos; por eso la confirmación es obligatoria.

**Criterios de aceptación Fase 2:** (a) foto de boleta mixta → tabla por línea, cambio una línea de insumo a gasto, confirmo, y no queda doble conteo; (b) insumo nuevo desde boleta queda con stock 0 + movimiento de compra y costo unitario correcto; (c) foto de insumos de evento → el agente pregunta evento y tipo antes de proponer; (d) tests de duplicados de insumo, normalización de unidades y de idempotencia.

### FASE 3 — Reservas y WhatsApp

**3.1 `propose_booking`.** Usa el servicio de bookings (precio con `calculate_estimated_price`). **Ojo con efectos secundarios:** `create_booking` (`routes/bookings_routes.py` ~39) envía una plantilla de WhatsApp (`send_whatsapp_template(..., 'new_booking', ...)`) y un email al admin; y al pasar a `confirmed` (`update_booking` ~162) envía email y WhatsApp **al cliente**. Define con claridad qué dispara el agente (propuesta: crear la reserva en `pending` con la notificación al admin igual que hoy; **el agente no confirma reservas**) y déjalo documentado y cubierto con tests (con los servicios de envío mockeados).

**3.2 Canal WhatsApp** (después de que el panel esté estable). Ya existe Twilio (`services/whatsapp_service.py`, solo envío con plantillas aprobadas). Hay que sumar: webhook entrante con **validación de firma `X-Twilio-Signature`**, **allowlist de números** autorizados, descarga de media (`MediaUrl0`, requiere autenticación básica de Twilio), estado de conversación en Firestore (por teléfono), confirmación por respuesta ("SI"/"NO") reutilizando `pending_actions`, y la restricción de la ventana de 24 h de WhatsApp.

---

## 6. UI/UX del asistente (transversal; hazlo junto con la tarjeta de la Fase 1)

Hoy: Dialog con texto plano, `onKeyPress` (obsoleto), sin markdown, sin adjuntos, sin estado de herramientas, sin persistencia, no pensado para el celular.

- **Móvil primero:** `fullScreen` en `<sm`, área de input fija abajo respetando el teclado, botón de cámara (`<input type="file" accept="image/*" capture="environment">`), previsualización con miniaturas y botón para quitar cada imagen.
- **Markdown** en las respuestas del agente (`react-markdown` + `remark-gfm`; sin HTML crudo), tablas y listas legibles.
- **Estados claros:** "Consultando inventario…" según las tools usadas (el backend ya devuelve `tools_used`). **Ojo:** el entry point `main()` de la Function envuelve Flask con `test_request_context` y arma la respuesta de una vez, así que *streaming SSE probablemente no funcione*; verifícalo antes de planificarlo y, si no se puede, usa estados de progreso simples.
- **Tarjetas de acción** (pending actions): resumen, campos editables, tabla por línea con selector de clasificación (insumo existente / nuevo / gasto), advertencias visibles (duplicado, total no cuadra, stock insuficiente), botones Confirmar / Cancelar, estado final (confirmada / cancelada / expirada / error) y deshabilitado tras resolver.
- **Chips de respuesta rápida** para `ask_choice` y sugerencias iniciales ("Subir boleta", "Insumos de un evento", "¿Qué tengo esta semana?").
- **Persistencia** de la conversación (al menos `localStorage` con try/catch; idealmente Firestore por usuario) y botón de nueva conversación.
- **Errores recuperables:** reintentar, sesión expirada (401), sin permiso (403), sin conexión.
- **Accesibilidad y pulido:** `aria-live` para mensajes nuevos, foco gestionado al abrir/cerrar, Enter envía y Shift+Enter hace salto de línea (`onKeyDown`), modo oscuro, textos en español neutro-chileno, actualizar el título ("Powered by…" según el modelo real).

---

## 7. Otras tareas y deuda registradas (en `Tasks.md`)

- **Migrar SDK y modelo:** `anthropic==0.40.0` (dic-2024) es anterior a thinking/effort/`refusal`. Subir el SDK y migrar a un modelo actual (p. ej. `claude-sonnet-5-5`): rechaza `temperature` (dejar `AI_CHAT_TEMPERATURE=""`), puede devolver `stop_reason: "refusal"`, bloques `thinking` que hay que reenviar tal cual en el loop de tools, y no admite `tool_choice` forzado. Usa la skill/refs `claude-api` y aprueba conmigo el cambio de costo antes de hacerlo. Haz tests del loop con el SDK nuevo.
- **Autenticación del resto del API:** solo `/api/ai-chat` verifica token; `/api/expenses`, `/api/inventory`, etc. están abiertos. Aplicar `@require_admin` ruta por ruta, **cuidando las rutas públicas** (crear reserva, contacto, galería pública, reseñas).
- Agregar `pytest` a un `requirements-dev.txt`.
- `isAdmin()` del frontend solo comprueba que haya email.
- Actualizar `.claude/CLAUDE.md` / `CLAUDE-BACKEND.md` con los endpoints nuevos y la corrección del puerto 8000.

---

## 8. Orden de trabajo sugerido

1. Confirma el estado: `git log`/`git status`, ¿está la Fase 0 en `main`? Corre `cd backend && pip install -r requirements.txt pytest && python -m pytest tests -q` (deben pasar 9).
2. Lee `Planning.md`, `Tasks.md` (sección M_AI), `ai_chat_routes.py`, `ChatAssistant.jsx` y los pedazos de `main.py` citados.
3. Propónme el plan detallado de la **Fase 1** (rama, archivos, orden de commits) y espera mi OK.
4. Implementa en este orden: tests de caracterización → servicios extraídos → `pending_actions` + endpoints → saneo del historial y cap de iteraciones → imágenes → `propose_expense`/`get_expenses_summary` → UI (tarjeta, adjuntos, markdown, móvil).
5. Al cerrar cada fase: tests verdes, build del frontend (`cd frontend && npm run build`), `Tasks.md` actualizado, y un resumen mío de qué probar a mano y qué variables de entorno o pasos de deploy nuevos hay.

## 9. Qué NO hacer
- No escribir datos sin confirmación manual ni dejar que el agente confirme por su cuenta.
- No registrar una misma compra como gasto e insumo a la vez.
- No adivinar el evento: siempre preguntar.
- No tocar rutas públicas (reservas, contacto, galería) al agregar autenticación sin probarlas.
- No desplegar ni abrir PRs sin que yo lo pida.
- No subir `.env`, claves ni `ServiceAccount.json`.
