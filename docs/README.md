# Documentación de eSYNAPSE 360

Índice de toda la documentación del proyecto. Cada archivo tiene un dueño y se actualiza en un momento concreto del ciclo de trabajo (ver `01_metodo_de_trabajo.md`).

## Documentos de dirección (raíz del proyecto)

| Archivo | Qué es | Cuándo se actualiza |
|---|---|---|
| `../CLAUDE.md` | Visión, reglas de desarrollo, reglas de negocio, roadmap y método de trabajo. **Es la fuente de verdad** para quien construye. | Cuando cambia una regla o el estado de una fase |
| `../CHANGELOG.md` | Historial de versiones: qué cambió, qué migración exige, qué probar | En cada entrega |
| `../PENDIENTES.md` | Backlog priorizado (ahora / siguiente / después) | Al cerrar cada sesión de trabajo |
| `../PLAN_CADENA_OPERATIVA.md` | DD-03: diseño y fases de la cadena comercial → logística → laboratorio → cobranza | Al validar decisiones de la fase 3 |
| `../CONTEXTO_PROYECTO.md` | Contexto técnico acumulado (historial de decisiones y notas de sesiones) | Ocasional; se irá vaciando hacia `docs/` |
| `../SIGE_Flujos_Detallados.md` | Flujos funcionales originales por módulo (especificación inicial) | Referencia; no se edita |

## Esta carpeta

| Archivo | Contenido |
|---|---|
| `01_metodo_de_trabajo.md` | Ciclo por módulo, definición de "hecho", procedimiento de entrega, roles, ritmo |
| `02_arquitectura_y_convenciones.md` | Stack, estructura del código, convenciones, patrones obligatorios |
| `03_operacion_en_pc.md` | Cómo iniciar, actualizar, probar y respaldar el sistema en el PC de desarrollo |
| `04_formatos_implementados.md` | **Registro de plantillas del SIG implementadas**: código, versión, fecha y siglas que imprime cada PDF; qué hacer cuando una plantilla cambia |
| `modulos/Mxx_*.md` | **Ficha de cada módulo construido**: propósito, formatos, modelos, API, permisos, reglas, estado, pendientes |
| `decisiones/ADR-nnnn-*.md` | Decisiones de arquitectura (qué se decidió, por qué, qué se descartó) |
| `validacion/` | Plantilla de acta de validación de software (ISO/IEC 17025 7.11) y checklist de aceptación por módulo; las actas firmadas se guardan aquí |

## Estado de los módulos

| Módulo | Ficha | Estado |
|---|---|---|
| Núcleo (usuarios, roles, permisos, auditoría, configuración) | `modulos/M00_nucleo.md` | Construido · en uso |
| M6 Documentos | `modulos/M06_documentos.md` | Construido · en uso |
| M8 Hallazgos | `modulos/M08_hallazgos.md` | Construido · pendiente validación completa |
| M9 Acciones correctivas | `modulos/M09_acciones_correctivas.md` | Construido · pendiente validación |
| M10 Auditorías | `modulos/M10_auditorias.md` | Construido · en validación (formatos SIG-PRO-16) |
| M12 Competencia técnica | `modulos/M12_competencia_tecnica.md` | Construido · pendiente validación |
| M13 Equipos (+ trazabilidad e intervalos) | `modulos/M13_equipos.md` | Construido · en uso |

"Construido" = código, pruebas automáticas y migraciones listos. "Validado" = acta de validación firmada en `validacion/`.
