# Diseño: Pablito, bloques B y C

Diseñado por un agente arquitecto (Opus 5.5) sobre el código de la rama del bloque A; implementado por subagentes Sonnet 5.5 y
revisado por Opus antes de desplegar. Es el contrato de implementación: si algo del código real contradice este texto, manda el código
y se anota la diferencia al final.

## Reglas transversales (todos los sub-bloques)
- Todo endpoint nuevo va en `ai_chat_bp` con `@require_admin`. Nada nuevo es público salvo el webhook de Twilio (firma + allowlist).
- El agente solo PROPONE; solo `pending_actions_service.confirm` (o los comandos deterministas de abajo) escribe datos del negocio.
- Idempotencia siempre: ids deterministas (`uuid5`), transacciones, batch para escrituras que deben ir juntas.
- Reloj de negocio: `utils/clock.py` (`today_cl`, `now_cl`), nunca `datetime.now()` para "hoy".
- Tests con el Firestore falso (`tests/fakes.py`); NUNCA tocar producción. Cada sub-bloque crea **su propio archivo de test**.
- Textos al usuario en español chileno, cortos (3-4 líneas).
- No imprimir ni copiar secretos; nunca `firebase deploy --debug`; `backend/.env` no se lee ni se edita desde un sub-bloque.
- Hallazgos previos que condicionan el diseño:
  - `whatsapp_agent._save_conversation` hacía `set()` sin merge: cualquier campo nuevo se borraba en el turno siguiente (se corrige en B0).
  - Las respuestas instantáneas por TwiML del webhook no actualizaban "último mensaje del usuario" (rompe la ventana de 24 h de C; se corrige en B0).

## B0 – Refactor previo (secuencial)
En `backend/services/whatsapp_agent.py`, `process_inbox` se parte en etapas, con los tests de caracterización existentes:
1. `_claim`
2. `_gather(db, deps, messages: list[dict]) -> Inbound` (recibe una **lista** aunque hoy tenga un elemento). `Inbound`: dataclass con
   `phone, sids, text, image_blocks, transcripts, unsupported, forwarded, button_payload`.
3. `_dispatch_commands(...)`: recorre `COMMAND_HANDLERS = [(matcher, handler), ...]`; cada feature agrega una línea.
4. `_agent_turn(...)`

Además: colección **`whatsapp_contacts/{tel}`** con `{last_user_message_at, alert_prefs, last_confirmed, updated_at}`, siempre con
`set(merge=True)`; el webhook la "toca" en todo mensaje que pasa la allowlist (incluidas las respuestas TwiML y los botones).
`_save_conversation` pasa a merge (solo sus campos).

## B1 – Notas de voz (Google Speech-to-Text)
Decisión: **API v2 por REST** con `google.auth.default()` + `AuthorizedSession` (vienen con firebase-admin; sin dependencia nueva;
el transcriptor se inyecta como `deps.transcribe` en los tests). Descartado: librería `google-cloud-speech` (grpc, arranque en frío),
API v1 OGG_OPUS (exige `sampleRateHertz` exacto; v2 trae `autoDecodingConfig`), long-running (obliga a GCS, innecesario).

`backend/services/speech_service.py`:
- `transcribe(data, content_type, phrases=None) -> {'text','confidence'|None,'seconds'}`
- `ogg_opus_seconds(data) -> float|None`: granule position de la última página `OggS` (bytes 6-14, int64 LE) menos el pre-skip de
  `OpusHead` (bytes 10-11), dividido por 48000.
- `POST https://speech.googleapis.com/v2/projects/pablospizza-d84bf/locations/global/recognizers/_:recognize`, body:
  `{"config":{"autoDecodingConfig":{},"languageCodes":["es-CL"],"model":"long","features":{"enableAutomaticPunctuation":true},
  "adaptation":{"phraseSets":[{"inlinePhraseSet":{"phrases":[{"value":"pizzeros","boost":10},...]}}]}},"content":"<base64>"}`
- `phrases`: pizzeros, pizza party, boleta, factura, merma, Líder, Jumbo, Lo Valledor + hasta 100 nombres de insumos (caché 10 min).
- Respuesta: concatenar `results[].alternatives[0].transcript`; `confidence` 0/ausente = desconocida.
- Env: `AI_WHATSAPP_STT_MODEL` (por defecto `long`; probar `chirp_2` si no alcanza). Verificar a mano que `es-CL` esté soportado; si no, `es-US`.

Límites: síncrono hasta 60 s / 10 MB. Se rechaza ANTES de llamar a la API si `ogg_opus_seconds > 58` o pesa > 2 MB:
"Uf, muy largo 😅 ¿me lo mandas en audios de menos de 1 minuto?". Tope diario de costo `AI_WHATSAPP_STT_DAILY_SECONDS=900`
(contado con `Increment` en `stt_seconds` del doc de cuota).

Integración en `_gather`: los `audio/*` se descargan con el `_download` existente y se transcriben; se guarda en el doc de inbox
`transcript`, `stt_confidence`, `audio_seconds`. **El audio nunca se guarda.** Varias notas de una ráfaga se concatenan en orden.
El agente recibe `"(nota de voz) <transcripción>"`; el historial guarda `"🎤 <transcripción>"`. Transcripción vacía:
"No te caché el audio 😅 ¿me lo repites o me lo escribes?" sin llamar al modelo.

Un "sí"/"no" dicho por voz cuenta como comando SOLO si: `parse_command(transcripción)` coincide exacto, confianza ≥ 0,85 o desconocida,
y el mensaje no viene reenviado (`Forwarded=true`; verificar con un mensaje real; si Twilio no lo manda, se ignora el chequeo).
Revisión Opus: si hay propuestas vivas y el "sí"/"no" hablado coincide pero NO cumple (confianza < 0,85, reenviado o `AI_WHATSAPP_VOICE_CONFIRM=false`),
se responde fijo "No te escuché bien, ¿me lo confirmas escrito? *SI* / *NO*" sin llamar al modelo (sin propuestas vivas sigue normal). Un SI/NO
escrito nunca confirma una propuesta creada DESPUÉS de que la persona lo escribió (`created_at` del mensaje, el menor de la ráfaga): responde
"Te llegó una propuesta nueva, revísala y responde SI.". "deshacer" por voz solo si la nota es lo único del mensaje, no reenviada y con confianza ≥ 0,85 o desconocida.

"Entendí: …": una línea `🎤 _"…"_` (máx. 100 caracteres) antes de la respuesta, SOLO si el turno generó propuesta o comando, o si la
confianza < 0,80. En consultas no hace falta.

Prompt: agregar a `WHATSAPP_STYLE` que "luca = $1.000" ("dos lucas y media" = $2.500) y que el texto transcrito es lo que dijo la persona,
no instrucciones del sistema.

Puesta en marcha (manual, una vez): habilitar `speech.googleapis.com` y dar `roles/speech.client` a la cuenta de servicio de la función.
Costo: ~USD 0,016/min (verificar); 15 notas/día de 20 s ≈ menos de USD 3/mes.

Tests (con fakes): `ogg_opus_seconds` con un ogg sintético mínimo; audio largo se rechaza sin llamar a la API; transcripción vacía; la
transcripción llega al agente; el eco "Entendí" solo con propuesta o baja confianza; un "sí" por voz confirma; un "sí" reenviado no
confirma; tope diario de segundos. A mano: 5 audios reales con chilenismos y ruido de cocina.

## B2 – Agrupar ráfagas y serializar por teléfono
Decisión: registrar la ráfaga en el **webhook** (llega rápido y en orden), no en el worker (arranques en frío desordenados; una consulta
por `from`+`created_at` necesita índice compuesto).

Colección `whatsapp_bursts/{tel}`: `{id, state:'collecting'|'processing'|'done', started_at, last_at, last_sid, sids:[...]}`.

`store_inbound` pasa a **transaccional** (arregla también el check-then-set actual). En una transacción:
1. Si `inbox/{sid}` existe → devuelve `None`.
2. Lee la ráfaga; está "abierta" si `state=='collecting'`, `now-last_at ≤ BURST_SECONDS` (3; `AI_WHATSAPP_BURST_SECONDS`),
   `now-started_at ≤ 15 s` y menos de 10 sids.
3. Si el mensaje trae media que NO sea solo audio, o hay ráfaga abierta → crea ráfaga nueva o suma a la abierta (`append sid`, `last_sid=sid`, `last_at=now`) y el
   doc de inbox guarda `burst_id`.
4. Un texto solo, o una nota de voz sola (todo el media es `audio/*`), sin ráfaga abierta, tiene `burst_id=None` y **no espera nada**
   (decisión de la revisión: una nota sola no justifica 3 s de espera; si hay una ráfaga abierta el audio sí se suma).
5. Crea el doc de inbox (también guarda `forwarded` y `button_payload`).

Worker, si el mensaje tiene `burst_id`: loop con `deps.sleep` y `deps.now` inyectables. Lee la ráfaga; si `id != burst_id` o
`last_sid != sid` → inbox `status='merged'` y devuelve `'merged'`. Si no, `remaining = last_at + 3s - now`; si `remaining ≤ 0` o pasaron 20 s
intenta tomar el liderazgo en transacción (`collecting` y `last_sid==sid` → `processing`); si lo logra lee los docs de `sids` en orden y llama
`_gather(list)`; si no, merged. Al terminar la ráfaga pasa a `done`. Imágenes: máx. 3 **por ráfaga** (`MAX_IMAGES`, porque el agente
rechaza más de 3 imágenes en un mensaje, `ai_chat_history.MAX_IMAGES_PER_MESSAGE`); si hay más, se agrega "Leí las primeras 3 fotos".
Cuota: el líder cobra `len(mensajes)` (una ráfaga de N cuenta N) con `Increment` en transacción.

Lock por teléfono `whatsapp_locks/{tel}` `{owner_sid, until}`: se adquiere por transacción antes de cargar la conversación (libre, vencido o propio →
`until = now + 300 s`, el timeout del worker); si no, reintenta cada 1 s hasta 120 s y luego se rinde (`LockBusy`, "Sigo con tu mensaje anterior…"):
un lock solo se toma cuando venció (`until <= now`), nunca se roba a un turno vivo; se libera en `finally`. Arregla una carrera que ya existe: dos
mensajes seguidos pisan el historial y un "SI" puede evaluarse contra propuestas que aún no existen.

Casos borde aceptados (documentar): texto primero y foto 1 s después dan dos respuestas (el texto nunca espera; opcional
`AI_WHATSAPP_TEXT_BURST_SECONDS`, por defecto 0); si el líder se cae (el trigger tiene `retry:false`) la ráfaga se pierde, como un mensaje suelto hoy.

Tests (fake + reloj falso): álbum de 3 → un líder, dos merged, una respuesta, el agente recibe las 3 imágenes; foto + texto 1 s después se juntan;
texto solo no llama a `sleep`; reintento de Twilio → un doc de inbox y un append; líder tardío (arranque en frío del primero) → una sola
respuesta; lock: el segundo turno espera y ve el historial del primero.

## B3 – "deshacer" (WhatsApp y panel)
`backend/services/undo_service.py`, registro por tipo: `check(db, action) -> plan` y `apply(db, action, user, undo_id) -> result`;
si no se puede, `CannotUndo(reason, suggestion)`. En WhatsApp, deshacer **también pasa por propose → confirm**: tipo de acción `undo`
con payload `{target_action_id}` cuyo executor llama a `undo_service.undo`.

Estado en el action original: `undo: {state:'processing'|'done'|'failed', undo_id, at, by, result:{snapshots…}}`, `status` sigue `confirmed`
(no rompe el panel). Claim transaccional (`None`/`failed` → `processing`); ids deterministas `uuid5(action_id:undo:…)`; las escrituras de cada undo
van en UN batch; auditoría `log_audit(email,'undo','pending_action',id, changes={type,result,snapshots}, metadata={source:'whatsapp'|'panel'})`.
No se puede deshacer un `undo`. Ventanas: 24 h desde WhatsApp ("lo último"), 7 días desde el panel; mismas reglas de seguridad.

Primitiva compartida en `inventory_service`: `check_movement_revertible(db, movement_id)` + `revert_movement_exact(db, movement_id, reversal_id, reason, batch)`.
Revertible solo si: el movimiento existe y no está `reverted`; **no hay movimientos posteriores del mismo `item_id`** (consulta por igualdad de
`item_id`, filtro de `created_at` en Python, sin índice); y `current_stock` / `weighted_avg_cost` del ítem coinciden con `stock_after` /
`avg_cost_after` (tolerancia 1e-6). Al revertir: el ítem vuelve a `stock_before`/`avg_cost_before` (recalcula `total_value`, `cost_per_unit`,
`needs_restock`), se crea un movimiento `movement_type:'reversal'` con `reverts_movement_id`, y el original queda `reverted:true, reversal_movement_id`.
**Exacto o no se hace** (el costo promedio ponderado no se puede "des-promediar").

| Tipo | Datos a guardar en `result` | Se permite si… | Efecto |
|---|---|---|---|
| `expense` | ya tiene `collection, expense_id` | el doc existe y no fue editado (`updated_at`−`created_at` < 5 s) | snapshot + delete |
| `inventory_receipt` | ya tiene `lines[{item_id, movement_id, expense_id}]` | **todas** las líneas son revertibles; un ítem `new` no tiene otros movimientos | reversal por línea; borra los gastos; borra el ítem nuevo (con snapshot) |
| `inventory_update` | **agregar** `before`/`after` de los campos (fallback `context.before`) | los campos actuales == `after` | `update_item(before)` |
| `stock_adjustment` | ya tiene `movement_id` (delta=0: "no cambió nada") | movimiento revertible | reversal |
| `event_supplies` | **agregar** `created`/`previous` (`items, notes, estimated_total_cost`) + `prev_estimated_supply_cost` | sin consumo registrado después | borrar o restaurar el anterior + financials |
| `event_consumption` | **agregar** `replaced:bool`, `prev_financials` (`total_expenses, supply_cost, other_expenses, profit`) | `replaced == False`, reserva no `completed`, y todos sus movimientos son los últimos de cada ítem | devolver el stock, **borrar** los movimientos (no marcarlos: `plan_consumption` los volvería a "devolver"), borrar el consumo y restaurar financials |
| `booking` | **agregar** `customer_created` | `status == 'pending'` y sin insumos | nuevo `booking_service.cancel_pending_booking` (`cancelled`, `cancel_reason`, sin notificar) + `Increment(-1)` en el cliente |

Mensajes cuando no se puede, siempre con alternativa: "Ya hubo movimientos de harina después, no lo puedo deshacer exacto. Te propongo un
conteo: dime cuánto hay." / "Ya la confirmaste y al cliente le llegó el aviso; cancélala desde el panel." / tras deshacer una reserva: "Ojo: el
aviso de reserva nueva ya les llegó." Las acciones confirmadas antes de este cambio sin los datos nuevos responden "Esa es antigua, hazlo desde el panel".

Flujo WhatsApp: al confirmar un "SI", `whatsapp_contacts.last_confirmed=[{id,n,at}]`; comando determinista `deshacer|deshaz|deshace|revertir [n|todas]`;
se corre el check y se crea la propuesta `undo`: "↩️ ¿Deshago *Compra Líder $23.450*? *SI* / *NO*".
Panel: `GET /api/ai-chat/pending/<id>/undo-preview` y `POST /api/ai-chat/pending/<id>/undo`, ambos `@require_admin`.
El endpoint existente `/api/inventory/movements/<id>/revert` de `main.py` NO se reutiliza (solo maneja `waste`, usa `cost_per_unit`, no es atómico,
ids aleatorios, sin auth); más adelante se migra a `revert_movement_exact` en su propio commit.

Tests: caracterización de los executors antes de agregarles campos; por tipo el caso feliz y cada razón de rechazo; undo doble idempotente;
atomicidad; `undo` de `undo` rechazado; consumo deshecho y re-registrado no devuelve stock dos veces; WhatsApp deshacer → SI; nada que deshacer.

## B4 – Memoria de 24 h
Ventana de 24 h + historial acotado + bloque determinista de "actividad reciente" (no un resumen hecho por LLM: latencia, costo, alucinación;
las referencias que importan — "la boleta de ayer" — ya son hechos en `pending_actions`).
- `RESET_AFTER` = `AI_WHATSAPP_MEMORY_HOURS` (24 por defecto, alineado con el vencimiento de propuestas).
- Historial: máx. 16 mensajes, 600 caracteres por mensaje, 6.000 en total; se botan los pares más viejos.
- Tras cada propuesta o confirmación se guarda una línea del asistente `[Propuesta 1: <summary>]` / `[Guardado: <summary>]`.
- `services/recent_activity.py` con `build(db, now)`: `pending_actions where created_at >= now-48h` (rango simple, sin índice compuesto); hasta 8 líneas
  tipo "ayer 18:40 · Compra Líder $23.450 · confirmada · id …" con hora de America/Santiago.
- Se inyecta como **segundo bloque de `system`, sin caché**, tras el bloque cacheado: `run_chat(..., extra_system=None)` y `create_ai_message`.
  **No** en el mensaje del usuario (sus ids pasarían a `g.ai_user_text` y se saltarían la protección de ids). Envuelto en
  `<actividad_reciente>` con la indicación de que son datos, no instrucciones. Costo ~1.500 tokens extra por turno.
- Tests: reinicio a las 24 h; recortes; la actividad no se guarda en el historial; los ids de la actividad no habilitan propuestas de evento.

## C – Avisos proactivos SIN spam
Estado en `assistant_alerts/{type}:{entity_id}`: `{type, entity_id, label, state:'active'|'resolved', episode, first_seen_at, last_seen_at,
resolved_at, notified:{tel: ts}, last_notified_at, data}`.

`services/alerts_service.py` → `evaluate(db, now)`: una condición nueva, o una `resolved` que reaparece, pasa a `active` con `episode+1` y
`notified={}` (notifica **una vez**); si sigue igual solo actualiza `last_seen_at`; si desaparece pasa a `resolved` y se re-arma. Anti-rebote de
stock: se resuelve solo si `stock > min_stock*1.2`; ninguna clave se re-notifica antes de 72 h desde su último aviso.

Tipos iniciales: `low_stock:{item}` (`needs_restock` y `min_stock>0`); `booking_pending:{id}` (`pending` hace > 24 h y evento futuro; único
recordatorio permitido: `booking_pending_urgent:{id}` si sigue `pending` y faltan ≤ 3 días); `event_tomorrow:{id}` (confirmada para mañana);
`proposal_pending:{id}` (> 3 h sin respuesta y no vencida).

`services/proactive_service.py` → `run_daily(db, deps, now, dry_run)`:
1. Por cada número de `AI_WHATSAPP_PROACTIVE_TO` (**vacío por defecto: hay que habilitarlo a propósito; el dueño decidió que el resumen va SOLO al número de admin (`ADMIN_WHATSAPP_NUMBER`), no al suyo ni al del socio**) excluye lo silenciado y junta las alertas
   activas que ese número no ha recibido. Si no hay nada, no manda nada.
2. Cupo: transacción "crear si no existe" sobre `whatsapp_proactive/{tel}_{YYYYMMDD}` con `status:'sending'`; si existe, aborta → **un mensaje al día**
   aunque el scheduler se dispare dos veces.
3. Ventana de 24 h: si `whatsapp_contacts.last_user_message_at` es de hace < 23 h 50 m → **texto libre** (máx. 4 líneas + "*silenciar stock* /
   *silenciar 2*"); si no → **plantilla**.
4. Marca `sent` en el doc diario y en el mismo batch guarda `notified[tel]`, el texto `detail`, `items:[keys numeradas]` y el sid.
Horario: cron `0 10 * * *` America/Santiago (**10:00, decidido por el dueño**) y el código solo envía entre 08:00 y 21:00. Ensayo: `AI_WHATSAPP_PROACTIVE_DRY_RUN=true` (valor por
defecto) escribe el doc con `status:'dry_run'` y no envía; además `GET /api/ai-chat/proactive/preview` (`@require_admin`) muestra el digest sin estado.

Plantilla (UTILITY, idioma `es`; no repetir el truco de "en con contenido en español"): script `backend/scripts/create_whatsapp_template.py`
(con `--dry-run`, `requests` contra la Content API; twilio 8.10 no trae `create`). `POST https://content.twilio.com/v1/Content`:
`{"friendly_name":"pablito_resumen_diario","language":"es","variables":{"1":"2","2":"stock bajo de harina y 1 reserva por confirmar"},
"types":{"twilio/quick-reply":{"body":"Hola, soy Pablito de Pablo's Pizza 🍕 Tienes {{1}} aviso(s) nuevo(s) de la operación: {{2}}. Toca Ver para el detalle.",
"actions":[{"title":"Ver","id":"digest_ver"}]}}}`. Aprobación: `POST /v1/Content/{HX}/ApprovalRequests/whatsapp` con
`{"name":"pablito_resumen_diario","category":"UTILITY"}`; estado con `GET` en la misma ruta. SID en `TEMPLATE_PABLITO_DIGEST_SID`. Al enviar se usa
`content_variables`; {{2}} sin saltos de línea y máx. 100 caracteres.

"Ver": en el webhook, si `ButtonPayload=='digest_ver'` o el texto es "ver" y hay un digest de < 48 h, se responde **por TwiML al tiro** con el `detail`
ya guardado, numerado, sin modelo. Esa respuesta abre la ventana de 24 h.

Comandos deterministas (preferencias en `whatsapp_contacts.alert_prefs = {muted_types[], muted_keys{}, paused:bool}`; son ajustes personales, no datos del
negocio, así que se aplican directo): `silencia stock|reservas|eventos|propuestas`, `silencia N`, `silencia todo` / `pausa avisos`,
`avísame de nuevo` / `activa avisos`, `avisos` (muestra el estado). El lenguaje natural ("no me avises de la harina") queda para una segunda fase.

Función programada en `main.py`: `@scheduler_fn.on_schedule(schedule="0 10 * * *", timezone=scheduler_fn.Timezone("America/Santiago"), timeout_sec=120)
def whatsapp_daily_digest(event)`; en `functions.yaml` copiar el formato de `keep_warm` (el manifiesto es el que usa el CLI). Con este job son 3 en
Cloud Scheduler (`check-overdue-events`, `keep_warm`, este): dentro del tramo gratis. Costo de mensajería ≈ USD 0,03 por envío, < USD 1/mes por número.

Tests: transiciones y re-armado; histéresis; cooldown de 72 h; doble ejecución → un solo envío; nada nuevo → nada se manda; silenciado respetado; texto vs
plantilla según `last_user_message_at`; horario nocturno; `dry_run` no envía; "Ver" responde el detalle; comandos. A mano: aprobación de la plantilla,
envío real a un solo número, botón Ver fuera de la ventana de 24 h.

## Seguridad transversal
- Inyección por imagen, audio o reenvío: se mitiga con propose → confirm; el SI/NO se lee solo del texto o audio original, nunca de lo que diga el
  modelo; los mensajes reenviados no son comandos; la actividad reciente va como bloque de sistema rotulado "datos".
- Abuso: allowlist, cuota diaria, tope de segundos de STT, tope de imágenes.
- Doble envío: idempotencia por MessageSid, ráfaga con líder único, cupo diario transaccional, undo idempotente.

## Orden de implementación y archivos
1. **B0** (un agente): `whatsapp_agent.py`, `whatsapp_routes.py` (touch de contacts), `test_whatsapp.py`.
2. En paralelo (worktrees):
   - **W-B2:** `whatsapp_agent.py` (`store_inbound`, entrada de `process_inbox`), `services/whatsapp_burst.py` nuevo, `test_whatsapp_burst.py`.
   - **W-B3:** `undo_service.py` nuevo; `inventory_service.py`, `booking_service.py`, `inventory_proposals.py`, `event_proposals.py`, `booking_proposals.py`
     (executors); `ai_chat_routes.py` (endpoints al final); `test_undo_*.py`.
   - **W-C:** `alerts_service.py`, `proactive_service.py`, el script nuevo, `main.py` (tras `keep_warm`), `functions.yaml`, el webhook ("Ver") y una línea de comando.
   - **W-B4:** `recent_activity.py` nuevo, `ai_chat_routes.py` (`run_chat`/`create_ai_message`) y la parte de `whatsapp_agent` que carga/guarda la conversación.
3. **W-B1** después de W-B2 (toca `_gather` y la cuota).
Conflictos esperables: `whatsapp_agent.py` (líneas de `COMMAND_HANDLERS` y constantes; merges triviales), `ai_chat_routes.py` (W-B3 al final, W-B4 en `run_chat`),
`docs/WHATSAPP_ASISTENTE.md` (lo actualiza el orquestador al final).

## Decisiones del dueño (10/10/2026)
- Resumen diario: **solo al número de admin**, a las **10:00 hora de Chile**, todos los días. Sigue en modo ensayo y sin destinatarios hasta que se apruebe la plantilla de Meta y se pruebe.
- "Eventos de mañana" **sí** cuenta como aviso (siempre dentro del tope de 1 mensaje al día).
- Un "sí" / "no" dicho por **nota de voz** **sí** puede confirmar, con las reglas estrictas de B1 (transcripción exacta, confianza alta, no reenviado).
