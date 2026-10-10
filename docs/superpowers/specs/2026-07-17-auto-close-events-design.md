# Auto-cierre de eventos con margen 70% — Diseño

**Fecha:** 2026-07-17
**Estado:** Aprobado

## Problema

El sistema envía WhatsApp diarios recordando cerrar eventos vencidos. El cliente no
tiene tiempo para cerrar eventos con costos reales, se le acumulan, y los
recordatorios diarios le molestan. Ya decidió que quiere cerrar todo con un margen
de utilidad del 70%.

## Solución (Opción A: auto-cierre silencioso)

Invertir el default: en vez de recordar hasta que el usuario cierre, el sistema
cierra solo y avisa únicamente cuando algo requiere atención.

### Componentes

1. **`services/auto_close_service.py`** (nuevo): lógica de cierre extraída de
   `complete_past_events_70margin.py` (construcción del documento `event`,
   cálculo costo/utilidad, actualización del booking). El script CLI pasa a
   reutilizar este módulo.

2. **Job del scheduler**: `check_overdue_events` en
   `services/scheduler_service.py` deja de enviar recordatorios y pasa a:
   - Buscar bookings `pending`/`confirmed` con `event_date <= hoy - AUTO_CLOSE_DAYS`.
   - Cerrarlos con margen `AUTO_CLOSE_MARGIN` (crear evento `completed` +
     actualizar booking), con `source: auto_close_70margin` y nota
     "Cerrado automáticamente con margen 70%".
   - Si un booking no se puede cerrar (sin `estimated_price`), enviar UN aviso
     por WhatsApp (una sola vez por booking, no diario).

3. **Configuración** (variables de entorno):
   - `AUTO_CLOSE_MARGIN` (default `0.70`)
   - `AUTO_CLOSE_DAYS` (default `3`)

4. **Backlog**: el primer run del job cierra los eventos ya acumulados.

### Fuera de alcance (YAGNI)

- Resumen mensual informativo (posible Opción C futura).
- UI nueva en el admin.
- Cambios en reportes: ya leen `profit`/`financials` del evento.

### Trade-off aceptado

Los reportes de utilidad pasan a ser estimados (70% fijo) salvo que se edite un
evento a mano con costos reales. El cliente lo acepta explícitamente.
