# Seguridad: rutas públicas (Lote 5)

Todo `/api/*` exige un token de administrador salvo lo que sigue. Estas rutas son públicas a propósito (las usa el
sitio real) y por eso se endurecen con listas blancas, validaciones y límites de uso.

## Qué es público

| Ruta | Quién la usa | Protección |
|---|---|---|
| `POST /api/bookings/` | formulario `/agendar` | lista blanca + validación (`sanitize_public_booking`), 5/min y 30/día por IP |
| `POST /api/contacts` | formulario de contacto | lista blanca + validación (`sanitize_public_contact`), 5/min y 20/día por IP |
| `GET /api/settings/comunas-lejanas` | formulario `/agendar` | solo lectura |
| `POST /api/payments/create-preference` | pago de abono | monto > 0 y <= saldo, `description` <= 200, 10/min por IP |
| `GET /api/payments/status/<id>` | página de resultado del pago | 60/min por IP |
| `POST /api/payments/webhook` | MercadoPago | firma `x-signature` (ver abajo) |
| galería pública (GET) | sitio | solo lectura |

## Reservas públicas (`POST /api/bookings/`)

`booking_service.sanitize_public_booking(data, db)` corre SOLO en la ruta pública. `create_booking` (usado por el
agente de WhatsApp y el panel) no cambia.

- Solo se aceptan: `client_name`, `client_email`, `client_phone`, `service_type`, `event_type`, `event_date`,
  `event_time`, `location`, `duration_hours`, `participants`, `pizzeros_participants`, `party_participants`,
  `pizza_quantity`, `special_requests`, `services_selected`, `selected_comuna`, `source`, `source_other`.
  Todo lo demás (`payments`, `payment_summary`, `financials`, `customer_id`, `status`, `estimated_price`, `id`, `notes`...)
  se descarta en silencio. `status` siempre queda `pending` y `estimated_price` se calcula en el servidor.
- `comuna_lejana_extra` lo decide el servidor: es el `cargo` de `settings/comunas_lejanas` (default 20000) solo si
  `selected_comuna` está en la lista configurada (sin distinguir mayúsculas ni tildes); en cualquier otro caso 0.
  Lo que mande el cliente se ignora.
- Límites: nombre 100, email 120 (con formato), teléfono 20, textos libres 1000, `participants`/`pizzeros_participants`/
  `party_participants`/`pizza_quantity` entre 0 y 500, `duration_hours` entre 0 y 24, `event_date` ISO válido,
  `event_type` en `birthday|corporate|school|private`, `service_type` en `workshop|pizza_party|pizzeros|party`.
- Un valor inválido o faltante responde 400 con un mensaje en español.

## Contacto público (`POST /api/contacts`)

Acepta `name` (100), `email` (120, formato), `phone` (20, opcional), `subject` (200), `message` (1000). `priority` ya no
la elige el cliente: siempre `normal`; la cambia el administrador desde el panel. Campos extra se descartan.

## Rate limits

Con Flask-Limiter y la clave de `utils/limiter.py::client_key` (la entrada N desde la DERECHA de `X-Forwarded-For`,
N = `TRUSTED_PROXY_HOPS`, default 1). Respuesta 429 en JSON (`{"error": "Rate limit exceeded", ...}`).

IMPORTANTE: el almacenamiento es `memory://`, o sea POR INSTANCIA. Con varias instancias de Cloud Run (o tras un
reinicio) el contador se reparte o se reinicia, así que es una MITIGACIÓN contra abuso casual, no una garantía. Para
un límite estricto hay que mover el storage a Redis/Memorystore o poner reglas en Cloud Armor. Verifica
`TRUSTED_PROXY_HOPS` contra los logs reales (ver cuántas entradas agrega Google al header) antes de confiar en los
límites por IP.

## Webhook de MercadoPago

- Verifica `x-signature` (`ts=...,v1=...`): manifiesto `id:{data.id};request-id:{x-request-id};ts:{ts};` (el campo que
  falta se omite; `data.id` va en minúsculas si es alfanumérico), HMAC-SHA256 con `MP_WEBHOOK_SECRET`, comparación en
  tiempo constante y rechazo de `ts` con más de 5 minutos.
- Modo por defecto SOLO REGISTRO: con firma inválida o ausente se escribe un warning (sin body ni secreto) y se sigue
  procesando. Con `MP_WEBHOOK_ENFORCE=true` una firma inválida responde 401 y no se procesa nada.
- Sin `MP_WEBHOOK_SECRET` no se verifica (se loguea una sola vez que falta).
- El body nunca se loguea (solo ids). Antes de registrar un pago aprobado se comprueba que `external_reference`
  sea una reserva existente con un registro `mp_payments` y que el monto coincida (±1) con una preferencia de esa
  reserva; si no, se ignora y se loguea.
- El agregado del pago a la reserva es idempotente y ocurre dentro de una transacción (busca `mp_payment_id` en
  `payments`, y por compatibilidad `#<id>` en `notes`).
- Errores internos siguen respondiendo 200 (para que MercadoPago no reintente sin fin).

## Variables nuevas

| Variable | Qué hace |
|---|---|
| `MP_WEBHOOK_SECRET` | clave secreta de Webhooks de MercadoPago; activa la verificación de firma |
| `MP_WEBHOOK_ENFORCE` | `true` = rechazar con 401 firmas inválidas; otro valor/ausente = solo registrar |
| `TRUSTED_PROXY_HOPS` | cuántos proxies de confianza agregan entradas a `X-Forwarded-For` (default 1) |

## Pasos manuales pendientes (los hace una persona)

1. En el panel de MercadoPago (Tus integraciones > Webhooks) copiar la **clave secreta** y guardarla como
   `MP_WEBHOOK_SECRET` en el entorno del backend (Cloud Run / `.env.yaml`). No commitearla.
2. Desplegar y observar 1-2 semanas en modo registro: buscar en los logs `invalid x-signature`. Deben ser cero para los
   pagos reales; si aparecen, revisar el manifiesto antes de forzar.
3. Cuando no haya advertencias, poner `MP_WEBHOOK_ENFORCE=true`.
4. Revisar `TRUSTED_PROXY_HOPS` con los logs reales.
