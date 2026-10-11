# Pablito: el asistente por WhatsApp

Pablito es el mismo asistente del panel, pero por WhatsApp: le escribes (texto o foto) al número de Pablo's Pizza y te responde.
**Solo propone; nunca guarda nada hasta que respondas SI a esa propuesta.**

## Cómo se usa
- Escribes normal: *"¿qué eventos tengo esta semana?"*, o mandas la foto de una boleta.
- Si el asistente necesita que elijas (por ejemplo a qué evento corresponden unos insumos), te manda una lista numerada:
  respondes con el número.
- Cuando deja una propuesta, te la resume y espera:
  - **SI** confirma · **NO** cancela.
  - Con varias propuestas: **SI 1**, **SI 2**, **SI todas**, **NO 1**, **NO todas**.
  - Si quieres cambiar algo, dilo con tus palabras ("mejor son 6 kg") y deja una propuesta nueva; las anteriores se cancelan solas.
- Una propuesta vence a las 24 horas. La conversación se reinicia si pasan más de 24 horas sin escribir (`AI_WHATSAPP_MEMORY_HOURS`).
- Memoria acotada: máx. 16 mensajes, 600 caracteres por mensaje y 6.000 en total (se botan los pares más viejos; las propuestas largas quedan resumidas con una línea `[Propuesta 1: ...]`).
- Además, en cada turno Pablito recibe como DATOS (segundo bloque de `system`, sin caché, nunca en el historial ni en el mensaje de la persona) las últimas 8 propuestas de las últimas 48 h con su estado (`services/recent_activity.py`), para responder "¿guardaste lo de ayer?" aunque la conversación ya se haya reiniciado.
- "SI" y "NO" solo valen como confirmación cuando hay una propuesta pendiente; si no, el asistente los lee como texto normal.

## Deshacer
- Después de un **SI**, escribe **deshacer** (también *deshaz*, *deshace*, *revertir*): Pablito propone deshacer lo último que confirmaste
  (*"↩️ ¿Deshago Compra Líder $23.450? SI / NO"*) y recién con tu **SI** lo hace. Si confirmaste varias cosas con un solo SI:
  **deshacer 1**, **deshacer 2** o **deshacer todas**.
- **Exacto o no se hace.** Se deshace solo si todo sigue tal como lo dejó la acción. Si no, te dice por qué y qué hacer:
  - un insumo con movimientos posteriores (otra compra, merma, consumo) no se revierte, porque el costo promedio no se puede
    "des-promediar": te propone hacer un conteo;
  - una reserva ya confirmada (al cliente le llegó el aviso) se cancela desde el panel; una pendiente se cancela **sin avisar al cliente**
    (el aviso interno de "reserva nueva" ya salió y eso no se retira);
  - un gasto editado, un consumo que reemplazó a otro, un evento ya completado o una estimación de insumos con consumo registrado
    se corrigen desde el panel;
  - acciones confirmadas antes de esta función: *"Esa es antigua, hazlo desde el panel"*.
- Ventana: 24 horas desde WhatsApp, 7 días desde el panel (`GET /api/ai-chat/pending/<id>/undo-preview` y `POST /api/ai-chat/pending/<id>/undo`).
  Un deshacer no se puede deshacer. Deshacer dos veces no duplica nada.
- Por dentro (`services/undo_service.py`): el estado queda en el action original (`undo: {state, undo_id, at, by, result}`, su `status`
  sigue `confirmed`); el chequeo y todas las escrituras de un deshacer van en **una sola transacción de Firestore** junto con la marca `done` (los insumos se vuelven a
  leer dentro de la transacción: si un movimiento llega justo en medio, el deshacer se aborta); los datos borrados quedan
  como *snapshot* en `undo.result` y en `audit_logs` (`action: undo`). Lo último confirmado por SI se recuerda en
  `whatsapp_contacts/{tel}.last_confirmed`.

## Rapidez y mensajes cortos
- **Saludos y "ayuda" se responden al instante** (menos de un segundo, sin modelo ni cola).
- **"Escribiendo…"**: apenas llega tu mensaje, Twilio muestra que Pablito está escribiendo (función beta de Twilio; si tu cuenta no la tiene, simplemente no aparece).
- **Respuestas de 3 o 4 líneas**, sin tablas ni listas largas, una pregunta a la vez, y solo las advertencias que cambian la decisión.
- **"SI" / "NO" no pasan por el modelo**: se atienden en menos de un segundo.
- **Arranque en frío**: la librería de IA y pandas se cargan solo cuando se necesitan (arranque de 4,7 s a 1,6 s en las pruebas) y una función programada (`keep_warm`, cada 4 minutos de 7 a 23 h, hora de Santiago) mantiene calientes `main` y el procesador, gratis.
- **Diagnóstico**: cada mensaje procesado guarda en `whatsapp_inbox/{sid}.timings` cuánto tardó cada etapa (`queue_ms`, `media_ms`, `agent_ms`, `send_ms`, `total_ms`).

## Seguridad
- **Solo responde a números autorizados**: por defecto `ADMIN_WHATSAPP_NUMBER` y `PARTNER_WHATSAPP_NUMBER`
  (se puede cambiar con `AI_WHATSAPP_ALLOWED`). Cualquier otro número (clientes que respondan a un aviso) se ignora en silencio.
- **El webhook valida la firma de Twilio** (`X-Twilio-Signature`): sin firma válida responde 403 y no guarda nada.
- Interruptor general: `AI_WHATSAPP_ENABLED=true`. Apagado (por defecto) el webhook no hace nada.
- Límite diario por número: `AI_WHATSAPP_DAILY_LIMIT` (por defecto 100 mensajes; el día es el de Chile, no UTC). Una ráfaga de N mensajes cuenta N.
- Un "SI" / "NO" nunca toca una propuesta creada **después** de que lo escribiste (responde "Te llegó una propuesta nueva, revísala y responde SI.").
- Los errores guardados en `whatsapp_inbox.error` y los de descarga de medios no llevan URLs (la URL de Twilio contiene el Account SID).
- Cada mensaje se procesa una sola vez (idempotente por `MessageSid`), aunque Twilio o Firestore lo reenvíen.
- Todo lo que se confirma por WhatsApp queda en `audit_logs` con `source: ai_agent` y el número (`whatsapp:+56…`).

## Cómo funciona por dentro
1. Twilio llama a `POST /api/whatsapp/webhook`. Se verifica firma y número, se guarda el mensaje en `whatsapp_inbox/{MessageSid}` y se responde
   200 al tiro (Twilio solo espera 15 segundos).
2. Un trigger de Firestore (`whatsapp_inbox_worker`, timeout de 5 minutos) procesa el mensaje: descarga las fotos, corre el asistente
   y responde por la API de Twilio.
3. Estado de la conversación en `whatsapp_conversations/{teléfono}` (solo texto; las fotos nunca se guardan ahí).

### Ráfagas y un turno a la vez
- Si mandas varias fotos seguidas (un álbum) o una foto y su texto, llegan como mensajes sueltos. El webhook los junta en
  `whatsapp_bursts/{teléfono}` (se cierra tras 3 s sin mensajes nuevos, 15 s en total o 10 mensajes). Solo el worker del **último** mensaje
  responde, una vez, con todo; los demás terminan en estado `merged` (no es error; el líder cobra cuota por todos: una ráfaga de N mensajes
  cuenta N). **Máximo 3 fotos por ráfaga** (no por mensaje): el agente rechaza más de 3 imágenes en un mismo mensaje, así que si mandas más la
  respuesta parte con "Leí las primeras 3 fotos". Límite conocido; subirlo exigiría repartir las fotos en varios turnos del agente.
- Un texto solo, o una nota de voz sola, no espera nada (no abre ráfaga); un audio sí se suma a una ráfaga que ya estaba abierta. Caso aceptado: texto primero y foto 1 s después dan dos respuestas
  (`AI_WHATSAPP_TEXT_BURST_SECONDS` > 0 hace esperar también a los textos).
- `whatsapp_locks/{teléfono}`: un turno del agente a la vez por número, para que el segundo vea el historial del primero (un "SI" nunca se
  evalúa contra propuestas que aún no existen). Vence a los 300 s (el timeout del worker) y solo se toma cuando venció: un turno espera hasta 120 s y, si el otro sigue vivo, se rinde con
  "Sigo con tu mensaje anterior…" (nunca le roba el lock a un turno que sigue corriendo). Se libera siempre.
- Si el worker líder se cae (el trigger no reintenta), esa ráfaga se pierde, igual que un mensaje suelto hoy.

## Puesta en marcha (una vez)
1. En `backend/.env` agrega `AI_WHATSAPP_ENABLED=true` (y, opcional, `AI_WHATSAPP_ALLOWED=+569…,+569…`).
2. Despliega: `firebase deploy --only functions --project pablospizza-d84bf` (crea la función `whatsapp_inbox_worker`).
3. En la consola de Twilio, en el remitente de WhatsApp (`TWILIO_WHATSAPP_FROM`) → **When a message comes in**:
   `https://main-4kqeqojbsq-uc.a.run.app/api/whatsapp/webhook` · método **HTTP POST**.
   (Esto reemplaza cualquier otro webhook entrante que ese remitente tuviera configurado.)
4. Escríbele "hola" desde tu número. Si no responde, mira `whatsapp_inbox` en Firestore: el campo `status` (`received`, `processing`,
   `done`, `failed`, `ignored`) y `error` dicen qué pasó.

## Variables de entorno
| Variable | Por defecto | Para qué |
|---|---|---|
| `AI_WHATSAPP_ENABLED` | `false` | interruptor general |
| `AI_WHATSAPP_ALLOWED` | admin + socio | números autorizados, separados por coma |
| `AI_WHATSAPP_DAILY_LIMIT` | `100` | mensajes por número y día |
| `AI_WHATSAPP_MEMORY_HOURS` | `24` | horas sin escribir tras las cuales la conversación se reinicia |
| `AI_WHATSAPP_TYPING` | `true` | muestra "escribiendo…" mientras prepara la respuesta |
| `AI_WHATSAPP_BURST_SECONDS` | `3` | silencio que se espera tras el último mensaje de una ráfaga (fotos) antes de responder |
| `AI_WHATSAPP_TEXT_BURST_SECONDS` | `0` | espera de un texto suelto por si llega una foto justo después (0 = no espera) |
| `AI_WHATSAPP_VOICE_CONFIRM` | `true` | `false` = un "sí"/"no" dicho por voz nunca confirma ni cancela (pide el SI / NO escrito) |
| `KEEP_WARM_URL` | URL de `main` | a qué dirección hace ping la función programada `keep_warm` |
| `AI_WHATSAPP_MODE` | `trigger` | `inline` procesa dentro del webhook (plan B si el trigger de Firestore no se puede usar) |
| `WHATSAPP_WEBHOOK_URL` | (la URL de la petición) | solo si Twilio firma una URL distinta a la que ve la función |

## Avisos (resumen diario)
Pablito puede mandarte **un resumen al día, a las 10:00 (hora de Chile), solo al número de admin y solo si hay algo nuevo**.
Está **apagado y en ensayo** hasta que lo actives a propósito.

**Qué avisa** (una alerta que sigue igual NO se vuelve a avisar; se re-arma cuando se resuelve y reaparece, y ninguna clave se repite antes de 72 h):
- stock bajo (`needs_restock` con mínimo > 0; se resuelve solo cuando el stock supera el mínimo x 1,2);
- reserva pendiente hace más de 24 h con evento futuro, y un único recordatorio urgente cuando faltan 3 días o menos;
- evento confirmado para mañana (cuenta como aviso, siempre dentro del tope de 1 mensaje al día);
- propuesta sin responder hace más de 3 h (y no vencida).

**Cómo llega**: si escribiste a Pablito en las últimas 24 h, va como texto libre (máx. 4 líneas); si no, como plantilla aprobada con un botón
*Ver*. Tocar *Ver* (o escribir "ver", hasta 48 h después) responde al tiro el detalle numerado, sin modelo.

**Comandos** (no usan el modelo; son ajustes personales y se aplican directo): `silencia stock|reservas|eventos|propuestas`, `silencia N`
(un aviso del último resumen), `silencia todo` / `pausa avisos`, `avísame de nuevo` / `activa avisos`, `avisos` (muestra el estado).

**Variables de entorno**
| Variable | Qué hace |
|---|---|
| `AI_WHATSAPP_PROACTIVE_TO` | Quién recibe el resumen. Vacío (por defecto) = no se manda nada. Solo se respeta el número de `ADMIN_WHATSAPP_NUMBER`; cualquier otro se ignora. |
| `AI_WHATSAPP_PROACTIVE_DRY_RUN` | `true` (por defecto): arma el resumen y lo deja en `whatsapp_proactive` con `status: dry_run`, sin enviar ni marcar nada como avisado. |
| `TEMPLATE_PABLITO_DIGEST_SID` | SID (`HX...`) de la plantilla aprobada. Sin él, fuera de la ventana de 24 h no se envía nada. |

**Puesta en marcha (manual, una vez)**
1. Crear la plantilla: `cd backend && python scripts/create_whatsapp_template.py --dry-run` para ver la solicitud; luego, con `TWILIO_ACCOUNT_SID` y
   `TWILIO_AUTH_TOKEN` en el entorno (nunca en el comando), `python scripts/create_whatsapp_template.py --approve`. Imprime el SID.
2. Esperar la aprobación de Meta (categoría UTILITY, normalmente minutos u horas): `python scripts/create_whatsapp_template.py --status HX...`.
3. Configurar `TEMPLATE_PABLITO_DIGEST_SID` y desplegar (la función programada `whatsapp_daily_digest` ya queda declarada en `functions.yaml`).
4. Con el ensayo activo, poner `AI_WHATSAPP_PROACTIVE_TO` = el número de admin y mirar un par de días: el resumen que habría salido queda en
   `whatsapp_proactive/<tel>_<AAAAMMDD>`, y `GET /api/ai-chat/proactive/preview` (admin) lo muestra en cualquier momento sin tocar nada.
5. Pasar a real: `AI_WHATSAPP_PROACTIVE_DRY_RUN=false`. Probar el botón *Ver* con el resumen llegado como plantilla (fuera de las 24 h).

Anti-spam: el cupo diario es un documento `whatsapp_proactive/<tel>_<AAAAMMDD>` creado en una transacción, así que aunque el programador corra dos
veces sale un solo mensaje. Si el envío falla no se marca nada como avisado, pero ese día no se reintenta solo (las alertas salen al día siguiente).
Solo se envía entre las 08:00 y las 21:00 de Chile.

## Notas de voz
Las notas de voz (`audio/ogg`, `opus`, `mpeg`, `mp4`, `aac`, `amr`) se transcriben con Google Speech-to-Text (API v2 por REST, modelo `long`,
`es-US` (Google no acepta `es-CL` con el modelo `long`; verificado), con los nombres de insumos como vocabulario). El audio **nunca se guarda ni se registra**: solo queda el texto (`transcript`,
`stt_confidence`, `audio_seconds` en el doc de `whatsapp_inbox`). El agente recibe `(nota de voz) <texto>` y el historial guarda `🎤 <texto>`;
varias notas seguidas se juntan en orden. El texto transcrito es un dato de la persona, nunca instrucciones del sistema.
- Eco `🎤 _"…"_` (máx. 100 caracteres) antes de la respuesta solo si el turno dejó una propuesta o un comando, o si la confianza es < 0,80.
- Un "sí"/"no" por voz confirma o cancela SOLO si la nota es solo eso (transcripción exacta), la confianza es >= 0,85 o desconocida, el mensaje
  no viene reenviado y `AI_WHATSAPP_VOICE_CONFIRM` no es `false`. Si no (y hay propuestas esperando), responde fijo *"No te escuché bien,
  ¿me lo confirmas escrito? SI / NO"* sin llamar al modelo; sin propuestas esperando sigue como texto normal. Un "sí" por voz que sí se acepta
  muestra antes el eco de lo que se entendió. "deshacer" por voz funciona igual de estricto (solo propone: el SI lo da la persona).
- **Verificar con audios reales (pendiente):** (1) si la API de Google entrega `confidence` en `es-CL` (si viene 0 o falta, se trata como
  desconocida y el "sí" hablado se acepta; si eso no te acomoda, `AI_WHATSAPP_VOICE_CONFIRM=false` lo desactiva del todo); (2) reenviar una nota
  de voz real y comprobar que Twilio manda `Forwarded=true` (si no lo manda, un audio reenviado con "sí" podría confirmar: mismo interruptor).
- Límites: más de 58 s o 2 MB se rechaza sin llamar a Google ("Uf, muy largo…"); transcripción vacía o con error: "No te caché el audio…" sin
  llamar al modelo; tope diario `AI_WHATSAPP_STT_DAILY_SECONDS` (900 s por número, contador `stt_seconds` en el doc `whatsapp_quota`, día de Chile).
  El audio se descarga con tope de 2 MB. Un fallo de la transcripción también cobra (mínimo 5 s, o lo estimado por tamaño: AMR ~1600 B/s,
  mp3/aac ~4000 B/s; ogg usa la duración real) para que una API caída no sea un reintento gratis. Si en una ráfaga una nota quedó fuera del tope y otra
  se transcribió, la respuesta avisa "Una nota de voz no la pude escuchar (tope diario).". Una nota sola no abre ráfaga (no espera 3 s).
- Variables: `AI_WHATSAPP_STT_MODEL` (por defecto `long`; probar `chirp_2`), `AI_WHATSAPP_STT_DAILY_SECONDS`, `AI_WHATSAPP_STT_PROJECT` (opcional).
- **Puesta en marcha manual (una vez, no se hace desde el código):** habilitar la API `speech.googleapis.com` en el proyecto y dar
  `roles/speech.client` a la cuenta de servicio de la función. Verificar a mano que `es-CL` esté soportado por el modelo (si no, `es-US`) y probar
  5 audios reales con chilenismos y ruido de cocina. Costo estimado: ~USD 0,016/min (verificar).

## Limitaciones conocidas
- Solo texto, fotos y notas de voz (los documentos, videos y otros reciben una respuesta explicando eso).
- Si falla el ENVÍO de la respuesta a un "SI" que ya guardó, solo se registra en el log (no se manda "No pude procesar tu mensaje"); el gasto igual quedó guardado.
- "ver" (webhook) responde el detalle sin pasar por el historial de la conversación.
- Las propuestas no se pueden editar campo por campo como en el panel: se corrigen pidiéndolo por texto.
- WhatsApp solo deja responder libremente dentro de las 24 horas siguientes a tu último mensaje. El asistente solo responde a lo que le
  escribes; sus avisos por iniciativa propia (ver "Avisos") usan texto libre dentro de esa ventana y una plantilla aprobada por Meta fuera de ella.
