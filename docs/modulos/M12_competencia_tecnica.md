# M12 · Competencia Técnica

**App:** `esynapse_sig` · **Estado:** construido, pendiente validación · **Pruebas:** `test_competencia.py`
**Formatos que replica:** procedimiento MET-PRO-12 — r01 Entrenamiento y supervisión · r02 Autorización del personal · r03 Entrevista de seguimiento (archivos en `PROCEDIMIENTOS SIG/MET-PRO-12/`).

## 1. Propósito

Autorizar al personal técnico por **método y magnitud** (entrenamiento → supervisión → autorización → seguimiento), gestionar quién puede firmar certificados y con qué alcance, y sostener las reglas 5 (técnico autorizado) y 7 (firma controlada) del sistema. Será consultado por las órdenes de trabajo (fase 3).

## 2. Modelos

| Modelo | Para qué |
|---|---|
| `MetodoCalibracion` | Catálogo de métodos/procedimientos por magnitud (provisional hasta M14) |
| `ControlValidez` | Catálogo de controles de validez (comparación intralaboratorio, etc.) |
| `ProcesoEntrenamiento` | Formato r01: tutor, actividades con documento, fecha y conformidad (con adjunto por actividad), período de supervisión, checklist de supervisión, nota teórica, control de validez, resultado |
| `Autorizacion` | Formato r02: usuario, método, magnitud, `funciones` (ejecutar, supervisar, revisar, firmar…), `alcance_firma` (todos / laboratorio), laboratorio, estado, frecuencia y fecha de seguimiento |
| `EvaluacionSeguimiento` | Formato r03: entrevista con preguntas y puntajes (establecido/obtenido), total, mínimo, máximo, resultado, decisión (mantener/suspender/reautorizar) |
| `PerfilCompetencia` | Perfil por cargo: educación, formación, experiencia |

**Estados de autorización:** `en_entrenamiento → vigente → suspendida / revocada`.

## 3. Función clave

`esta_autorizado(usuario, metodo=None, funcion='ejecutar', laboratorio=None)` → `True` solo con autorización **vigente y activa** para ese método y función. Para `funcion='firmar'` evalúa el alcance: `todos` (Gerente Técnico) o `laboratorio` (encargado, solo el suyo).

## 4. API

`/api/metodos-calibracion/`, `/api/controles-validez/` (catálogos) · `/api/autorizaciones/` (`seguimientos`, `autorizacion_pdf`) · `/api/procesos-entrenamiento/` (`entrenamiento_pdf`, `subir_adjunto`) · `/api/evaluaciones-seguimiento/` (`seguimiento_pdf`) · `/api/perfiles-competencia/` · `/api/solicitudes-competencia/` (candado: aprobar, devolver, rechazar, reenviar).

Las tres entidades principales pasan por el **candado de aprobación**: sin permiso de aprobar, crear/editar/eliminar queda como solicitud pendiente.

## 5. Reglas

- Sin autorización vigente no se ejecuta ni se firma (regla 5 y 7).
- El adjunto de una actividad de entrenamiento se abre desde la pantalla pero **no se imprime** en el PDF.
- Seguimientos vencidos generan alertas en Mis tareas / Calendario.
- Los PDF replican los tres formatos; solo imprimen lo que se llenó.
- (0.2.11) El entrenamiento exige método, tutor y al menos una actividad. La autorización exige método y funciones; quien firma, alcance (y laboratorio si es por laboratorio); la vigente, fecha. Una sola autorización activa (vigente o en entrenamiento) por persona y método. Pruebas en `test_recorrido_reglas.py`.
- (0.2.12) **Vigente exige entrenamiento superado** del mismo método: actividades y supervisión conformes, tutor de supervisión, nota teórica ≥ 14 y control de validez satisfactorio. Entrenamiento concluido = solo lectura y no se elimina. Exención solo para el cargo Gerente Técnico, con sustento. Suspendida → se reautoriza solo con re-entrenamiento superado posterior a la suspensión (`suspendida_en`); revocada no se reactiva.
- (0.2.12) **Seguimiento calculado en el servidor** (`calcular_puntajes`): total = Σ obtenido; máximo = puntaje por pregunta × n.°; mínimo = 70 % del máximo; satisfactorio si mínimo ≤ total ≤ máximo. Con no satisfactorio no se mantiene ni reautoriza. Pruebas en `test_competencia_autorizacion.py`.

## 6. Pendientes

- Validación completa con un proceso real de autorización.
- Al construir M14 (Métodos) el catálogo `MetodoCalibracion` se reemplaza/vincula con las versiones vigentes de método.
