# Checklist de aceptación de un módulo

Se recorre en el PC con datos reales antes de dar un módulo por validado. Lo completa César (o el responsable del proceso) y queda adjunto al acta de validación. Copiar este archivo como `Mxx_checklist_AAAA-MM-DD.md` y marcar cada punto.

**Módulo:** ____ · **Versión probada:** ____ · **Fecha:** ____ · **Quién prueba:** ____

## A. Acceso y permisos

- [ ] Un usuario sin permiso sobre el módulo no lo ve en el menú ni accede por URL.
- [ ] Un usuario con solo "leer" ve pero no puede crear ni editar (botones ocultos y API responde 403).
- [ ] Las operaciones de aprobar (cerrar, firmar, aprobar) solo las ejecuta quien tiene ese permiso.
- [ ] Si el módulo tiene candado: un cambio de alguien sin "aprobar" queda pendiente, el aprobador lo ve en la bandeja y puede aprobar, devolver y rechazar; el solicitante puede corregir y reenviar.

## B. Flujo principal

- [ ] Crear un registro con datos reales del laboratorio (no "prueba 123").
- [ ] Recorrer todos los estados en orden; en cada paso el estado y el color coinciden con la regla 10 del CLAUDE.md.
- [ ] Intentar saltarse una precondición (cerrar sin conclusiones, planificar sin líder…): el sistema lo impide con un mensaje claro.
- [ ] Eliminar un registro: desaparece de la lista pero sigue existiendo (soft delete) y puede verse con "incluir inactivos" si aplica.

## C. Formatos y PDF

- [ ] Cada PDF del módulo coincide con el formato real del procedimiento (secciones, orden, columnas, encabezado con código, versión y firmas).
- [ ] Todo dato que el PDF muestra tiene dónde ingresarse en el sistema (ningún campo sale vacío por falta de captura).
- [ ] Los datos de empresa (nombre, dirección, responsable, logo) salen de Configuración.

## D. Integración con otros módulos

- [ ] Lo que este módulo genera para otro aparece donde debe (ejemplo: hallazgo de auditoría → Hallazgos; NC mayor → requiere acción correctiva).
- [ ] Las alertas del módulo aparecen en Mis tareas y Calendario con la fecha correcta.

## E. Auditoría y trazabilidad

- [ ] Cada acción queda en el Log de auditoría con usuario, fecha, valor anterior y nuevo.
- [ ] Las firmas registran usuario, cargo, fecha e IP; no se puede firmar sin contraseña.

## F. Pruebas automáticas

- [ ] `Probar.bat` termina en OK en la versión probada.

## Resultado

- [ ] **Aceptado** sin observaciones.
- [ ] **Aceptado con observaciones** (listar abajo; no bloquean el uso).
- [ ] **Rechazado** (listar abajo; vuelve a construcción).

Observaciones:

1.
2.
3.
