# M13 · Equipos (control del equipamiento)

**App:** `esynapse_sig` · **Estado:** construido, en uso · **Pruebas:** `test_candado_aprobacion.py` (control de cambios sobre equipos)
**Formatos que replica:** procedimiento MET-PRO-04 — r01 Hoja de vida · r02 Inventario · r03 Programa anual (mantenimiento, calibración, comprobaciones, caracterización) · r04 Cartas de trazabilidad · r05/r06/r07 Informes · r08 Intervalo de calibración · r09 Control de salida y entrada (archivos en `PROCEDIMIENTOS SIG/MET-PRO-04/`).

## 1. Propósito

Hoja de vida de cada equipo y patrón, estado de calibración y vigencia, bitácoras (calibración, mantenimiento, comprobaciones), programa anual por laboratorio, movimientos (salida/retorno), informes, cartas de trazabilidad metrológica e intervalos de calibración. Sostiene la regla 6 (patrón vigente), que las órdenes de trabajo consultarán en la fase 3.

## 2. Modelos

| Modelo | Para qué |
|---|---|
| `Equipo` | Ficha: `codigo` (prefijo por magnitud: M-, TH-, FP-…), nombre, magnitud y clasificación (catálogos), laboratorio, datos técnicos, periodicidad, fecha de última y próxima calibración, estado (operativo, calibrado, inoperativo, baja), certificado e imagen |
| `MagnitudEquipo`, `ClasificacionEquipo` | Catálogos administrables (clasificaciones "patrón de …" activan la regla de patrón vigente) |
| `RegistroEquipo` | Bitácoras: calibración, mantenimiento, comprobación intermedia/funcional, caracterización |
| `ActividadPrograma` | Programa anual: actividad, año, frecuencia, meses |
| `MovimientoEquipo` | Salida y retorno con motivo, destino, responsable |
| `InformeEquipo` | Informes numerados (mantenimiento, comprobación, caracterización) |
| `CartaTrazabilidad`, `NodoTrazabilidad` | Carta por magnitud; nodos jerárquicos con varios padres, nivel y categoría |
| `PuntoIntervalo`, `ResultadoIntervalo` | Matriz años × puntos: resultado, incertidumbre, EMP (método OIML D10) |
| `SolicitudCambioEquipo` | Candado de aprobación: entidad, operación, payload, estado (pendiente, aprobada, devuelta, rechazada), **reutilizado por otros módulos vía `modulo`** |

## 3. API

`/api/equipos/`: `registrar_calibracion`, `agregar_registro`, `eliminar_registro`, `marcar_inoperativo`, `reactivar`, `dar_baja`, `agregar_actividad`, `programar`, `registrar_movimiento`, `registrar_retorno`, `registrar_informe`, `inventario_pdf`, `programa`, `programa_pdf`, `ficha_pdf`, `bitacora_pdf`, `laboratorios`, `resumen`.
`/api/cartas-trazabilidad/` (`carta_pdf`), `/api/nodos-trazabilidad/` (`rellenar_desde_equipo`), `/api/puntos-intervalo/` (`guardar_matriz`, `intervalo_pdf`), `/api/resultados-intervalo/`, `/api/magnitudes-equipo/`, `/api/clasificaciones-equipo/`, `/api/solicitudes-cambio-equipo/` (`aprobar`, `devolver`, `rechazar`, `reenviar`, `pendientes_count`, `mis_devueltas_count`).

## 4. Reglas

- **Control de cambios**: sin permiso `aprobar`, el alta/edición/baja de equipos, bitácoras, actividades, movimientos, informes, intervalos y nodos queda pendiente (202) hasta que un supervisor la apruebe, devuelva o rechace. Probado automáticamente.
- Al registrar una calibración se recalcula la próxima según la periodicidad; el estado pasa a calibrado/vencido.
- **Regla 6 (patrón vigente)**: la asignación de un patrón con calibración vencida se bloqueará en la OT (fase 3.3); hoy el módulo expone la vigencia (`fecha_proxima_calibracion`, estado) para que esa puerta la consulte.
- El programa anual (PDF r03) agrupa calibración+mantenimiento, comprobación intermedia+caracterización y comprobación funcional.
- Eliminar = dar de baja (conserva historial).
- (0.2.11) La próxima calibración es posterior a la calibración. Fuera de servicio exige motivo; reactivar solo desde fuera de servicio. Un equipo dado de baja es de solo lectura (no se calibra, no sale, no se programa, no se reactiva). Una sola salida abierta a la vez y un solo retorno por salida. Pruebas en `test_recorrido_reglas.py`.

## 5. Pantallas

`Equipos` (lista, ficha con pestañas: datos, calibraciones, bitácoras, programa, movimientos, informes, intervalo de calibración, carta de trazabilidad; bandeja de cambios pendientes), `Programa anual`, `Intervalo de calibración` (matriz), `Trazabilidad`.

## 6. Pendientes

- Corregido en 0.2.0: reenviar una solicitud devuelta respondía 404 (filtro de bandeja aplicado a acciones de detalle).
- Candado: pruebas sobre entidades distintas de "equipo" (bitácora, intervalo, nodo).
- Fase 3: `Laboratorio` pasa de texto libre a catálogo compartido.
