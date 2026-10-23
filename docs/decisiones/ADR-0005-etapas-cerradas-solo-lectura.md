# ADR-0005 · Una etapa cerrada es de solo lectura (regla general del sistema)

**Fecha:** 2026-10-13 · **Estado:** vigente · **Origen:** decisión de César al validar M10

## Contexto

Los procesos del sistema son secuencias de etapas (programar → planificar → ejecutar → informar → cerrar; registrar → analizar → tratar → cerrar; elaborar → revisar → aprobar). Hasta ahora, al avanzar de etapa los datos de las etapas previas seguían editables: una auditoría en ejecución permitía cambiar su plan, un informe generado permitía seguir cargando listas y actas. Eso rompe la trazabilidad: lo impreso y firmado en una etapa debe coincidir con lo registrado.

## Decisión

1. **En todo módulo del sistema, cuando una etapa de una secuencia se cierra (el registro avanza a la siguiente), los datos de esa etapa y de las anteriores pasan a solo lectura.** Se ven, se imprimen, no se modifican.
2. **Una etapa futura tampoco se edita por adelantado**: sus datos se capturan cuando el registro llega a ella.
3. La regla la aplica el **servidor** (rechaza el cambio con un mensaje que nombra la etapa y el campo); la pantalla la refleja deshabilitando los campos y marcando la sección como "solo lectura". Nunca se confía solo en la pantalla.
4. Cada módulo declara sus etapas en el modelo: nombre, estados en los que sigue abierta y campos que le pertenecen (patrón `ETAPAS` de `Auditoria`). Las acciones (agregar integrante, generar lista, registrar acta…) exigen su etapa abierta.
5. **Corregir algo de una etapa cerrada no es editarla**: se hace por el mecanismo controlado que corresponda (reabrir con motivo y nueva revisión, como el programa anual; nueva versión, como los documentos; reapertura de hallazgo). Si el módulo no tiene ese mecanismo, se diseña antes de permitir la excepción; no se abre la puerta "por si acaso".
6. Las **desviaciones registradas como tales** (reprogramar una auditoría, que conserva el mes original y anota el nuevo con motivo) sí se permiten mientras la etapa que las contiene siga abierta, porque no modifican lo aprobado: lo complementan con trazabilidad.

## Aplicación

| Módulo | Etapas | Estado |
|--------|--------|--------|
| M10 Auditorías | Programa (solo Programada) → Plan (hasta Planificada) → Ejecución: listas, actas, hallazgos (solo En ejecución) → Informe (hasta En informe) → Cerrada (todo solo lectura) | **Aplicado** (0.2.6) |
| M10 Programa anual | Aprobado = solo lectura; reabrir con motivo sube la revisión | Aplicado (0.2.6) |
| M6 Documentos | Versión aprobada es inmutable; cambios = nueva versión | Ya cumplía por diseño; verificar edición de metadatos |
| M8 Hallazgos | Registrado → En análisis → En tratamiento → Cerrado (reabrir controlado) | Pendiente de revisar campo por campo |
| M9 Acciones correctivas | Registrada → En análisis → En implementación → En verificación → Cerrada | Pendiente de revisar campo por campo |
| M12 Competencia, M13 Equipos | Registros históricos (evaluaciones, calibraciones, cartas) no se editan una vez emitidos; cambios por candado de aprobación | Pendiente de revisar |
| Fase 3 (OT, certificados, logística) | Se diseña con esta regla desde el inicio | — |

## Alternativas descartadas

- Bloquear solo al cerrar el registro completo (lo que había): deja ventanas de edición entre etapas y los PDF ya emitidos dejan de coincidir con los datos.
- Bloquear solo en pantalla: cualquier cliente de la API lo saltaría.

## Consecuencias

- Toda ficha de módulo (`docs/modulos/`) incluye la tabla de etapas y qué campo pertenece a cuál.
- Toda regla de etapa tiene prueba automática que falla si se relaja.
- Los módulos ya construidos se revisan uno por uno (tarea en `PENDIENTES.md`); los nuevos nacen con la regla.
