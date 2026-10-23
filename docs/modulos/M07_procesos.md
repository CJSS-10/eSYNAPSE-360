# M7 · Procesos

**App:** `procesos` (app propia, ADR-0004) · **Estado:** **cerrado** en 0.4.1 (acta `docs/validacion/M07_acta_2026-10-21.md`, por firmar) · **Pruebas:** `procesos/tests/test_procesos.py` (22)
**Documentos fuente:** mapa de procesos y fichas de caracterización en `PROCEDIMIENTOS SIG/Procesos (propuesta)/` (revisión aprobada por César el 2026-10-21). **Formatos que replica:** Ficha de Caracterización de Procesos y Mapa de Procesos.

## 1. Propósito

Mantener el catálogo oficial de procesos del SIG, su mapa y la ficha de caracterización de cada proceso (ISO 9001 4.4), con control de versiones y firmas, y que los demás módulos usen ese catálogo en lugar de escribir el proceso a mano.

## 2. Decisiones (César, 2026-10-20 y 2026-10-21)

| Tema | Decisión |
|---|---|
| Código del formato | Un solo código para todas las fichas: SIG-M-01-r03. Cada ficha se identifica por el proceso. El mapa es SIG-M-01-r02. |
| Firmas | Elabora el Asistente SIG, revisa el Gerente SIG, aprueba el Gerente General. |
| Caja de control de los PDF | Versión y fecha del formato (ficha 01 · 2025-02-22; mapa 00 · 2025-01-10), no la versión de cada ficha; la lista maestra manda cuando el formato esté vinculado. |
| Responsable de Gestión Estratégica | Gerente General. |
| Metas de indicadores | Las de la propuesta. Los resultados se registran a mano en la ficha hasta que exista M4 Indicadores. |
| Actualización automática | El mapa y lo vinculado (documentos, NC, quejas, auditorías) se actualizan solos. El contenido aprobado de una ficha nunca lo cambia el sistema: cuando se aprueba un documento del proceso, se crea el aviso «ficha por revisar» para su responsable. |
| Carga inicial | Las 18 fichas de la propuesta se cargan como versión 01 en elaboración, para que pasen por las firmas. |

## 3. Catálogo de procesos

Proceso: nombre, tipo (estratégico / operativo / soporte), proceso padre (subprocesos del SIG), cargo responsable, usuario responsable (recibe los avisos), detalle que se muestra en el mapa, orden, activo. Un proceso no se elimina: se desactiva (y no puede desactivarse si tiene subprocesos activos).

## 4. Ficha de caracterización (versionada)

Contenido igual al formato: objetivo, responsable, alcance, tipo; actividades (subtítulo opcional, proceso proveedor, entrada, actividad, medida de control, proceso cliente, salida); documentos asociados (vinculados a la lista maestra o descritos); registros; recursos humano, económico y tecnológico; indicadores (nombre, cálculo, meta, frecuencia, responsable).

Proveedor y cliente se eligen del catálogo; lo que no es un proceso (Cliente, Proveedor externo, Todos los procesos) va como texto.

### Etapas (etapa cerrada = solo lectura, ADR-0005)

| Etapa | Estado | Qué ocurre | Quién |
|---|---|---|---|
| Elaboración | En elaboración | Se edita todo el contenido. Para enviarla se firma con contraseña. | Asistente SIG |
| Revisión | En revisión | Conforme → firma y pasa a aprobación. Con observaciones → vuelve a elaboración con comentarios. | Gerente SIG (no quien elaboró) |
| Aprobación | En aprobación | Aprueba con firma → vigente. Devolver → vuelve a elaboración con comentarios. | Gerente General (no quien revisó) |
| Vigente | Vigente | Solo lectura. La anterior pasa a obsoleta. Los avisos pendientes del proceso quedan atendidos por esta versión. | — |

Cambiar una ficha vigente = «Nueva versión» con motivo (copia la vigente). Solo una versión en curso por proceso.

## 5. Indicadores y avisos

- Resultado de indicador: proceso, indicador, periodo (mes), valor, estado (cumple / en riesgo / no cumple), comentario. Se conserva entre versiones si el indicador mantiene su nombre.
- Aviso «ficha por revisar»: se crea al aprobar una versión de un documento vinculado al proceso, o a mano con motivo. Se atiende al aprobar la siguiente versión de la ficha, o se descarta con motivo («no requiere cambio»).

## 6. Catálogo en otros módulos

- Documentos, Hallazgos (y la SAC que nace de ellos), registro de NC desde Quejas y hallazgos de Auditorías guardan el proceso del catálogo; el texto del proceso se sigue imprimiendo igual en sus PDF.
- Los textos existentes se vinculan al catálogo cuando coinciden con un nombre (o «SIG», «Alta Dirección»); los demás quedan sin vincular y se pueden corregir.
- En Auditorías, «Áreas / procesos a auditar» se elige del catálogo (sigue siendo texto en el programa).

## 7. Criterios de aceptación

1. El mapa se arma desde el catálogo: un proceso nuevo aparece en su banda sin más pasos; uno desactivado desaparece.
2. Solo la versión en elaboración se edita; el servidor rechaza cambios a una versión en revisión, aprobación, vigente u obsoleta, nombrando la etapa.
3. Enviar, revisar y aprobar exigen contraseña; quien revisa no es quien elaboró y quien aprueba no es quien revisó.
4. Aprobar deja la versión vigente, la anterior obsoleta y atiende los avisos pendientes.
5. Nueva versión exige motivo y que no haya otra en curso; copia actividades, documentos, registros e indicadores.
6. Aprobar en Documentos una versión de un documento vinculado a un proceso crea su aviso.
7. La ficha muestra lo vinculado: documentos, NC abiertas, SAC en curso, quejas y auditorías del año.
8. El PDF de la ficha replica el formato; el del mapa replica el mapa.
9. Hallazgos y Quejas eligen el proceso del catálogo; los PDF existentes no cambian.

## 8. API

| Recurso / acción | Operación | Regla |
|---|---|---|
| `/api/procesos/` CRUD (`?todos=1` incluye inactivos) | leer / crear / editar | DELETE = desactivar (no con subprocesos activos); `reactivar` |
| `/api/procesos/mapa/` | leer | Catálogo por banda, con ficha, semáforo de indicadores, avisos y vinculados |
| `/api/procesos/{id}/vinculados/` | leer | Documentos, NC abiertas, SAC en curso, quejas y auditorías del año (incluye subprocesos) |
| `/api/procesos/mapa_pdf/` | leer | Mapa de procesos |
| `/api/fichas-proceso/` (`?proceso=`) | leer / crear / editar | POST solo para la primera ficha (v01); PATCH solo en elaboración, con listas completas de actividades, documentos, registros e indicadores (lo que falta se da de baja) |
| `/api/fichas-proceso/{id}/enviar` · `revisar` · `aprobar` | editar / aprobar / aprobar | Con `password` (firma) |
| `/api/fichas-proceso/{id}/devolver` | aprobar | Con `comentarios`; anula las firmas de la ronda |
| `/api/fichas-proceso/{id}/nueva_version` | crear | Desde la vigente, con `motivo`, sin otra en curso |
| `/api/fichas-proceso/{id}/pdf/` | leer | Ficha de caracterización |
| `/api/avisos-proceso/` (`?proceso=`, `?pendientes=1`) · `{id}/descartar` | leer / crear / editar | Descartar con `motivo` |
| `/api/resultados-indicador/` | leer / crear / editar / eliminar | Un resultado por indicador y mes; DELETE = baja lógica |
