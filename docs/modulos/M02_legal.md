# M2 · Requisitos legales y otros requisitos

**App:** `legal` (app propia, ADR-0004) · **Estado:** construido en 0.7.0 (en validación) · **Pruebas:** `legal/tests/test_legal.py`
**Procedimiento:** Identificación, Acceso y Evaluación de Requisitos Legales y Otros Requisitos Ver. 01 (carpeta `PROCEDIMIENTOS SIG/`). **Formatos que replica:** Lista de Requisitos Legales y Otros Requisitos y Matriz de Evaluación de Cumplimiento Legal.

## 1. Propósito

Identificar, acceder, analizar, actualizar, comunicar, implementar y evaluar el cumplimiento de los requisitos legales y otros requisitos (ISO 14001 6.1.3 y 9.1.2, ISO 45001 6.1.3 y 9.1.2, Ley 29783), y ahora también los requisitos de acreditación.

## 2. Decisiones (César, 2026-10-21)

| Tema | Decisión |
|---|---|
| Frecuencia de evaluación | **Semestral** para todos los ámbitos (el procedimiento dice «mínimo 12 meses»; el Excel de SST tenía cuatrimestres). La periodicidad de cada artículo se mantiene como dato. |
| Ámbitos | SST, Medio Ambiente, Obligaciones Sociolaborales, Otros requisitos y **Acreditación** (nuevo: requisitos de INACAL). |
| Caja de control de los PDF | Versión **01** · 2026-01-02 (la del procedimiento) · Elaborado **ASIG** · Revisado **GSIG** · Aprobado **GG**. La lista maestra manda cuando el formato esté vinculado. |
| Histórico | Las evaluaciones de 2025 del Excel se cargan como evaluaciones cerradas (cuatrimestres de SST y otros requisitos; anual de Medio Ambiente). |

## 3. Registros y reglas

- **Requisito (norma):** ámbito, tema, ítem, tipo, código, nombre, fecha de aprobación, modificatorias, observaciones, procesos involucrados, aplicabilidad y consecuencias del incumplimiento (6.2). Una norma derogada queda como registro y no se edita; sus obligaciones salen de las evaluaciones siguientes. Cambio normativo = «modificatoria» (queda en la revisión) y, si exige adecuarse, «solicitud de cambio» (origen externo: requisitos legales).
- **Comunicación (6.4):** fecha, medio (correo, reunión, publicación), destinatarios y qué se comunicó.
- **Obligación (artículo a cumplir):** documento/registro que evidencia, documento legal asociado (o la norma de la lista), artículo, extracto, proceso/sede, responsable, periodicidad, observaciones. Baja con motivo.
- **Evaluación (6.6):** por ámbito y semestre; una en curso por ámbito; carga todas las obligaciones vigentes como pendientes (las que se agregan durante la evaluación se suman). Resultado por obligación: cumple / no cumple / no aplica (estos dos con explicación) y evidencia. **Cierre con firma**: exige todo evaluado; cada incumplimiento se registra como **hallazgo** (6.7) para su acción correctiva. Cerrada = solo lectura.
- **Indicadores:** % de cumplimiento por ámbito (cumple ÷ evaluadas) con la escala del formato (Bueno > 80 %, Regular 70–80 %, Malo < 70 %), tendencia, evaluación vencida (más de seis meses sin evaluar), cumplimiento global (meta 100 %).

## 4. API

| Ruta | Permiso | Qué hace |
|---|---|---|
| `/api/requisitos-legales/` | leer · crear · editar · eliminar | Lista (filtros `ambito`, `tema`, `estado`, `proceso`, `buscar`); DELETE anula solo sin obligaciones |
| `POST .../registrar_modificacion/` · `derogar/` · `comunicar/` · `solicitar_cambio/` | editar | Cambio normativo, comunicación, solicitud de cambio |
| `GET .../catalogos/` · `indicadores/` · `lista_pdf/?ambito=` | leer | Listas, indicadores, PDF de la lista |
| `/api/obligaciones-legales/` + `dar_de_baja/` | leer · crear · editar | Artículos a cumplir |
| `/api/evaluaciones-legales/` (GET, POST, DELETE) | leer · crear · eliminar | Evaluaciones; DELETE anula una en curso sin resultados |
| `GET .../{id}/resultados/` · `POST .../evaluar/` (multipart) | leer · editar | Resultados |
| `POST .../{id}/cerrar/` | aprobar | Cierre con firma; hallazgos por incumplimiento |
| `GET .../matriz_pdf/?ambito=&anio=` | leer | Matriz del año con una columna por evaluación y el resumen por tema |

## 5. Criterios de aceptación

1. Lista por ámbito con sus temas, modificatorias y estado; PDF igual al formato.
2. Derogar retira las obligaciones de las evaluaciones; la norma derogada no se edita.
3. Una evaluación en curso por ámbito; no cierra con pendientes ni sin firma; incumplimiento → hallazgo.
4. Evaluación cerrada de solo lectura.
5. Carga inicial de la lista (299 normas), la matriz (447 obligaciones) y las evaluaciones de 2025.
