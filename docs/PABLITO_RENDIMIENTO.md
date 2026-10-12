# Pablito: rendimiento (latencia) medido

Fecha: 12-10-2026. Rama `main`, commits locales (sin push ni deploy).
Todo lo de abajo sale de `backend/scripts/bench_pablito.py` (API real de Anthropic + `FakeFirestore`, nunca Firestore real) y de los
`timings` que ahora guarda cada mensaje en `whatsapp_inbox/{sid}.timings`. Los JSON crudos están en `docs/bench/`.

## 1. Dónde se va el tiempo (hallazgo principal)

* Una ronda de modelo cuesta **~1,0 s fijos + ~5 ms por token de salida** (una llamada con 40 tokens de salida: 1,1-1,3 s). Con
  el prefijo de 11k tokens cacheado la ronda cuesta solo ~180 ms más que una llamada sin prefijo (1282 vs 1098 ms, p50 de 8).
* Por eso el tiempo de un turno es casi `nº de rondas x 1,2-1,7 s`. **La palanca real es quitar rondas**, no afinar el modelo.
* Infraestructura antes del modelo (claim + cuota + lock + leer conversación): ~285 ms a 40 ms por viaje a Firestore. Typing síncrono
  del worker: ~600 ms medidos desde esta máquina (Twilio, TLS nuevo cada vez).
* Cold start: `import main` 2,8 s local; el SDK de Anthropic tarda 2,5-5 s en importarse (ya se hace en `prewarm`). La primera
  llamada de un proceso nuevo cuesta ~5-6 s (import + conexión); una escritura de caché fría de 11k tokens cuesta solo ~1,2 s
  (medido 4+5 veces con prefijos únicos), así que los 15-19 s fríos de producción eran cold start del worker, no el tamaño del prompt.

## 2. Variantes de modelo (baseline, 11 escenarios x 3 repeticiones, caché tibio)

| variante | media de p50 por escenario | p50 global | p95 global | llamadas a herramientas vs Sonnet low |
|---|---|---|---|---|
| a) `claude-sonnet-5-5` effort low (actual) | 2535 ms | 2568 | 3713 | referencia |
| b) Sonnet + thinking apagado (`{"type":"between_tools"}`) | 2833 ms | 3088 | 4099 | igual salvo `agendar` |
| c) `claude-haiku-5-5` (adaptive) | 2266 ms | 2232 | 4081 | **distintas** en stock, agendar, gasto |
| c2) Haiku sin thinking | 1917 ms | 2111 | 2829 | **distintas** en stock, agendar, compra |

* (b') `effort: "minimal"` **no existe**: la API acepta `low|medium|high|xhigh|max` (400 con `minimal` y con `none`). El equivalente
  (apagar el thinking) en Sonnet 5.5 se pide con `thinking: {"type": "between_tools"}`, y resultó **más lento** (+300 ms), no se aplica.
* Haiku gana 0,3-0,6 s pero cambia el comportamiento (agendar: pregunta con `ask_choice` y hace dos búsquedas; stock: llama
  `get_inventory_status` además; gasto: a veces `ask_choice`). El criterio era igualdad de llamadas: **no se aplica**. Quedan los
  knobs `AI_WHATSAPP_MODEL` / `AI_WHATSAPP_THINKING` (vacíos = sin cambio) solo para experimentar.
* `server-side fallback` (beta) vs endpoint normal: no se midió diferencia relevante; se deja como está.

## 3. Cambios aplicados, ganancia y flag

| # | cambio | ganancia medida | flag (default) |
|---|---|---|---|
| 1 | Instrumentación fina en `timings` (claim, typing, quota, lock, gather, load_conv, commands, agent, save, send, cada ronda con tokens/caché/stop, cada herramienta, espera del contexto) | observabilidad, 0 ms | siempre |
| 2 | **Snapshot de situación** como 3er bloque `system` sin caché (eventos 14 días, stock bajo, consultas sin responder; sin ids) | **-1,0 a -1,6 s p50** en preguntas de eventos/stock/consultas (quita una ronda); detalle en la tabla de abajo | `AI_WHATSAPP_CONTEXT` (true) |
| 3 | **Respuestas instantáneas sin modelo** para `stock de X` y `eventos de hoy/mañana` (formas exactas; cualquier duda va al modelo) | de ~2,4 s a ~0,3 s (solo bookkeeping; +1 lectura real de Firestore) | `AI_WHATSAPP_FAST_QUERIES` (true) |
| 4 | Typing del worker en hilo (antes bloqueaba hasta 1,5 s) y en el webhook solapado con el guardado | -0,2 a -0,6 s en el camino crítico del worker (600 ms medidos por llamada) | `AI_WHATSAPP_TYPING_ASYNC` (true) |
| 5 | Prefetch de actividad reciente + snapshot mientras corren cuota/lock/lectura de conversación | -124 ms (espera del contexto 124 ms -> 0 a 40 ms por lectura) | `AI_WHATSAPP_PREFETCH` (true) |
| 6 | `touch_contact` del webhook en paralelo con `store_inbound` | ~-40 ms hasta que se guarda el mensaje (y dispara el trigger); webhook 415 -> 253 ms simulado | `AI_WHATSAPP_WEBHOOK_PARALLEL` (true) |
| 7 | Modo `AI_WHATSAPP_MODE=inline_text` (texto en el propio webhook, medios por trigger) | evita la cola 0,5-1,8 s (dato real del dueño); **no medible offline** | `AI_WHATSAPP_MODE` (`trigger`, opt-in) |
| 8 | Fix: resultados de herramientas con timestamps de Firestore (`get_contacts`) hacían fallar el turno entero ("No pude procesar tu mensaje") | bug real encontrado por el benchmark ("qué hay pendiente" fallaba) | siempre |

### Tabla antes / después (p50 / p95 del turno completo del worker, ms; 3 repeticiones, Firestore simulado instantáneo)

"Antes" = commit 810bdd1 (baseline) con la variante `current`; "después" = defaults nuevos.

| escenario | antes p50 | antes p95 | después p50 | después p95 | rondas a/d | llamadas antes -> después |
|---|---|---|---|---|---|---|
| saludo (modelo) | 1682 | 2218 | 1481 | 1529 | 1/1 | - |
| stock de queso | 2364 | 2440 | ~290* | ~290* | 2/0 | search_inventory -> sin modelo |
| mañana (eventos) | 2618 | 2792 | ~290* | ~290* | 2/0 | get_bookings -> sin modelo |
| esta semana | 3315 | 3378 | 1925 | 2074 | 2/1 | get_bookings -> (snapshot) |
| agendar evento sábado | 3758 | 3918 | 3236 | 3646 | 2/1 | search_bookings -> (snapshot; respuesta más larga) |
| qué hay pendiente | falla (bug 8) | - | 1937 | 1967 | -/1 | get_bookings+get_contacts -> snapshot |
| registrar gasto | 2639 | 3249 | 1963 | 2358 | 1/1 | igual (sin herramientas) |
| ventas del mes | 2407 | 2763 | 2512 | 2553 | 2/2 | igual (get_financial_summary) |
| compra de harina | 2639 | 3512 | 2993 | 3363 | 2/2 | igual (search_inventory + propose) |
| "quiero registrar algo" | 1397 | 1402 | 1437 | 1656 | 1/1 | igual |
| deshacer | (comando, sin modelo) | | ~290* | | 0/0 | igual |
| tengo algo el sábado | (nuevo) | | 1407 | 1628 | -/1 | snapshot (antes ~2,6 s medido en A/B) |
| qué falta comprar | (nuevo) | | 1708 | 1716 | -/1 | A/B: 2619 -> 1672 |
| consultas sin responder | (nuevo) | | 1377 | 1421 | -/1 | A/B: 2909 -> 1431 |
| fecha lejana (3 nov) | (nuevo) | | 2687 | 2868 | -/2 | usa `search_bookings` (correcto, fuera de la ventana) |

\* con 40 ms por viaje a Firestore simulado (claim 81 + cuota 82 + lock 82 + conversación 40 + lectura 41). Con Firestore instantáneo da 1 ms.
Las diferencias en escenarios sin cambio de código (ventas, compra, gasto, vago) son ruido de la API (+-0,3 s).

A/B aislado del snapshot (misma sesión, `FAST_QUERIES=false` para no mezclar), p50 ms current -> ctx: semana 3361 -> 1777, mañana 2520 -> 1482,
faltan 2619 -> 1672, consultas 2909 -> 1431, sábado 2658 -> 1406, pendiente 3128 -> 1919, lejano 2551 -> 2546 (usa herramienta en ambos),
stock 2542 -> 3034 y agendar 3639 -> 3041 (n=3, ruido de longitud de respuesta; ver "riesgos").

## 4. Descartado (con motivo)

* **Haiku / sin thinking / effort distinto**: ver sección 2. Sin igualdad de llamadas o más lento.
* **Achicar el prefijo (paso 4)**: system 5075 tokens (WhatsApp 724 + web 4351), 18 herramientas 5994 tokens (`propose_receipt` 1062, `propose_booking` 873,
  `propose_expense` 803 son las mayores). Con caché tibio el prefijo entero cuesta ~180 ms y las herramientas ~30 ms, es decir ~16 ms por cada 1k tokens:
  recortar 1,5k tokens ahorraría ~25 ms y se pierde en el ruido, con riesgo de cambiar comportamiento. Con caché frío tampoco ayuda (la escritura de 11k cuesta ~1,2 s, igual
  que una llamada caliente). No se tocó ningún texto.
* **Pedir herramientas en paralelo (paso 3)**: Sonnet ya las pide en paralelo cuando son independientes (`compra2`: 3 `search_inventory` en una ronda); las
  rondas restantes son dependencias reales (buscar id -> proponer). No hay nada que mejorar en el prompt.
* **Paralelizar cuota + lock**: ahorraría ~1 viaje (40-80 ms) pero obliga a manejar un lock que no se puede cancelar mientras espera; riesgo en una ruta de seguridad
  por <3 % del turno. No se aplica. Tampoco `user_for` (es puro, sin E/S) ni la doble lectura de conversación (solo hay una lectura por turno; la otra es de
  `whatsapp_contacts` en el webhook y ahora va en paralelo).
* **Leer la conversación en paralelo con el lock**: una lectura anterior al lock puede ver historial viejo (carrera con el turno previo). No es seguro.
* **Conexión HTTP persistente a Anthropic**: reconectar tras 9 s inactivo cuesta +40-60 ms; no vale la pena.
* **Typing/inline por defecto**: `inline_text` no se activa por defecto (ver riesgos); `inline` completo sigue como estaba.
* **Fast path para "qué hay pendiente"**: ambiguo (reservas por confirmar, propuestas, consultas, stock); el snapshot lo resuelve en 1 ronda sin reconocer patrones frágiles.
  Tampoco "esta semana" / "fin de semana" (reglas de calendario del prompt); las cubre el snapshot.
* **Pre-importar más módulos en `prewarm`**: lo único pesado es el SDK de Anthropic y ya se carga.

## 5. Riesgos y qué verificar a mano

1. **Snapshot (`AI_WHATSAPP_CONTEXT`)**: es el cambio de más impacto y el que modifica respuestas. Probar por WhatsApp: "qué tengo esta semana", "tengo algo mañana",
   "qué falta comprar", una fecha a más de 14 días ("tengo algo el 3 de noviembre", debe usar herramienta), y "agenda un evento ..." (debe seguir avisando choques de fecha).
   El snapshot no trae ids: elegir un evento sigue exigiendo `search_bookings` + `ask_choice`. Si algo raro: `AI_WHATSAPP_CONTEXT=false` (no requiere deploy de código, sí de variables).
   Lecturas extra por mensaje: 3 consultas de un solo filtro (eventos 14 días, `inventory needs_restock==true`, `contacts status==pending`); Firestore crea los índices simples solos.
2. **Respuestas instantáneas**: solo "stock de X / cuánto queda de X" (el nombre debe coincidir palabra completa con un insumo, si no pasa al modelo) y
   "eventos/tengo algo hoy|mañana". Verificar el formato en WhatsApp real y que `service_type` real (`workshop`, `pizza_party`, o lista separada por comas) se vea bien.
   `AI_WHATSAPP_FAST_QUERIES=false` las apaga.
3. **Typing asíncrono**: los hilos se unen antes de terminar la función/respuesta (no quedan colgados). Si el indicador "escribiendo…" dejara de aparecer, `AI_WHATSAPP_TYPING_ASYNC=false`.
4. **`inline_text`**: Twilio corta a los 15 s; un turno de texto largo (p95 ~4 s hoy, pero un cold start suma 6+ s) podría pasarse y Twilio lo marcaría como error de
   webhook. La idempotencia está probada con tests (reintento del mismo `MessageSid` no crea otro doc ni ejecuta el agente dos veces: `store_inbound` transaccional + `_claim`),
   pero **no está demostrado en producción**: antes de activar, ver en Twilio Debugger que no haya reintentos y comparar `queue_ms` (ahora 0,5-1,8 s). Por eso queda opt-in.
5. **Nuevo `timings` en Firestore** (rondas y herramientas, ~1 KB por mensaje): sirve para ver la realidad en producción: `claim_ms`, `quota_ms`, `lock_ms`, `load_conv_ms`, `activity_ms`, `rounds[]`, `tools[]`.
   Con los números reales de Firestore se puede decidir si vale paralelizar más.
6. El benchmark usa Firestore simulado instantáneo: las herramientas aparecen con 0-1 ms; en producción cada herramienta suma 50-200 ms (lo dirá `timings.tools`).

## 6. Cómo reproducir

```
cd backend
python scripts/bench_pablito.py run --variants current --reps 3 --out ../docs/bench/after.json
python scripts/bench_pablito.py run --variants current,ctx,noquick --fs-latency-ms 40 --reps 3 --out x.json
python scripts/bench_pablito.py report ../docs/bench/after.json
python scripts/bench_pablito.py compare ../docs/bench/baseline.json ../docs/bench/after.json
```

Tests: `cd backend && python -m pytest tests -q` -> 1240 verdes (eran 1193; +47 nuevos).
