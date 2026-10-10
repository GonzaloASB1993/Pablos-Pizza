# Asistente por WhatsApp

El mismo asistente del panel, pero por WhatsApp: le escribes (texto o foto) al número de Pablo's Pizza y te responde.
**Solo propone; nunca guarda nada hasta que respondas SI a esa propuesta.**

## Cómo se usa
- Escribes normal: *"¿qué eventos tengo esta semana?"*, o mandas la foto de una boleta.
- Si el asistente necesita que elijas (por ejemplo a qué evento corresponden unos insumos), te manda una lista numerada:
  respondes con el número.
- Cuando deja una propuesta, te la resume y espera:
  - **SI** confirma · **NO** cancela.
  - Con varias propuestas: **SI 1**, **SI 2**, **SI todas**, **NO 1**, **NO todas**.
  - Si quieres cambiar algo, dilo con tus palabras ("mejor son 6 kg") y deja una propuesta nueva; las anteriores se cancelan solas.
- Una propuesta vence a las 24 horas. La conversación se reinicia si pasan más de 6 horas sin escribir.
- "SI" y "NO" solo valen como confirmación cuando hay una propuesta pendiente; si no, el asistente los lee como texto normal.

## Seguridad
- **Solo responde a números autorizados**: por defecto `ADMIN_WHATSAPP_NUMBER` y `PARTNER_WHATSAPP_NUMBER`
  (se puede cambiar con `AI_WHATSAPP_ALLOWED`). Cualquier otro número (clientes que respondan a un aviso) se ignora en silencio.
- **El webhook valida la firma de Twilio** (`X-Twilio-Signature`): sin firma válida responde 403 y no guarda nada.
- Interruptor general: `AI_WHATSAPP_ENABLED=true`. Apagado (por defecto) el webhook no hace nada.
- Límite diario por número: `AI_WHATSAPP_DAILY_LIMIT` (por defecto 100 mensajes).
- Cada mensaje se procesa una sola vez (idempotente por `MessageSid`), aunque Twilio o Firestore lo reenvíen.
- Todo lo que se confirma por WhatsApp queda en `audit_logs` con `source: ai_agent` y el número (`whatsapp:+56…`).

## Cómo funciona por dentro
1. Twilio llama a `POST /api/whatsapp/webhook`. Se verifica firma y número, se guarda el mensaje en `whatsapp_inbox/{MessageSid}` y se responde
   200 al tiro (Twilio solo espera 15 segundos).
2. Un trigger de Firestore (`whatsapp_inbox_worker`, timeout de 5 minutos) procesa el mensaje: descarga las fotos, corre el asistente
   y responde por la API de Twilio.
3. Estado de la conversación en `whatsapp_conversations/{teléfono}` (solo texto; las fotos nunca se guardan ahí).

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
| `AI_WHATSAPP_MODE` | `trigger` | `inline` procesa dentro del webhook (plan B si el trigger de Firestore no se puede usar) |
| `WHATSAPP_WEBHOOK_URL` | (la URL de la petición) | solo si Twilio firma una URL distinta a la que ve la función |

## Limitaciones conocidas
- Solo texto y fotos (los audios y documentos reciben una respuesta explicando eso).
- Las propuestas no se pueden editar campo por campo como en el panel: se corrigen pidiéndolo por texto.
- WhatsApp solo deja responder libremente dentro de las 24 horas siguientes a tu último mensaje. El asistente solo responde a lo que le
  escribes, así que no le afecta; si algún día manda avisos por iniciativa propia, tendrán que ser plantillas aprobadas por Meta.
