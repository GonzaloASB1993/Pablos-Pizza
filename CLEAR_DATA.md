# Limpiar datos de la galería

Para borrar todos los eventos de la galería pública y empezar desde cero:

## Método 1: Desde el navegador

1. Ve a https://pablospizza.web.app
2. Abre las herramientas de desarrollador (F12)
3. Ve a la pestaña "Console"
4. Ejecuta estos comandos:

```javascript
// Limpiar todos los eventos
localStorage.removeItem('events');

// Limpiar toda la galería
localStorage.removeItem('gallery');

// Limpiar agendamientos si quieres empezar todo desde cero
localStorage.removeItem('bookings');

// Refrescar la página
location.reload();
```

## Método 2: Desde la aplicación

Los datos se limpiarán automáticamente la próxima vez que:
1. Recargues la página
2. Entres al admin por primera vez

## Verificar que está limpio

Después de limpiar, ve al admin:
- Menú "Eventos" debe estar vacío
- Menú "Galería" debe estar vacío
- Puedes empezar a crear eventos reales

## Para empezar a usar el sistema:

1. **Crear un agendamiento** en el menú "Agendamientos"
2. **Confirmarlo** (cambia status a "confirmado")
3. **Completarlo** (marca como "completado" y crea evento automáticamente)
4. **Subir fotos** desde el menú "Eventos" → botón "Fotos"
5. **Ver en galería** pública desde el menú "Galería"

¡Ya está listo para usar con datos reales!