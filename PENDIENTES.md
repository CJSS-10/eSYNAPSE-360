# eSYNAPSE 360 — Backlog

> Se actualiza al cerrar cada sesión. Tres listas: **Ahora** (en lo que se trabaja), **Siguiente** (lo próximo, en orden), **Después** (registrado, sin fecha). Las decisiones pendientes van aparte: no son tareas, bloquean tareas.
> Versión actual: ver `backend/VERSION` · Historial: `CHANGELOG.md` · Método: `docs/01_metodo_de_trabajo.md`

## Ahora

- [ ] **Validaciones en pantalla**: mientras la base sea de desarrollo, se hacen en el sistema normal (decisión de César, 2026-10-22). El **modo pruebas** (0.8.5, `Iniciar modo pruebas.bat`: copia de la base y de los archivos, puertos 8001/5174, aviso «MODO PRUEBAS») pasa a ser obligatorio para validar y capacitar desde que se carguen datos reales. M17 Cambios y M18 Quejas validados el 2026-10-22.
- [ ] **Datos de prueba en la base real**: el sistema está en desarrollo (César, 2026-10-22): los registros de prueba ya hechos se quedan; se descartan en la puesta en marcha, al pasar a PostgreSQL (fase 3.0), con una base inicial que conserve solo catálogos y cargas reales. Lo único que se retira ahora son los usuarios temporales activos: «prueba_sst_ev» y su rol.
- [ ] **Firmar las actas de validación en lote** (decisión de César del 2026-10-20: se firman todas juntas cuando estén cerrados los módulos del SIG). Listas en PDF en `docs/validacion/`: M10 (0.2.8), M9 (0.2.15) y M7 (0.4.1). Se cargan en Documentos y se firman con el flujo de elaboración, revisión y aprobación.

- [ ] **Rediseño de la interfaz** (ADR-0007): construido del 0.8.12 al 0.8.20 (correcciones visuales, módulo estándar, alineación por tipo de dato en 31 tablas principales y 25 de fichas, escala de severidad única, tipografía y paleta, fichas en panel con barra de etapas, Tablero del SIG, títulos y pestañas unificados, menú lateral por área con pendientes, etiquetas sin mayúsculas sostenidas, Mis tareas por urgencia, Calendario y vencimientos del Tablero). Rediseño cerrado hasta recibir comentarios de las usuarias. **Opcional después:** búsqueda global Ctrl+K (requiere un endpoint), estilo de Login, revisión de accesibilidad y de modo oscuro completo, vista en tableta. **Queda:** validar en pantalla con la Coordinadora y la Asistente SIG y ajustar; definir las etapas de Hallazgos y de Riesgos si se quiere barra de etapas en ellos (hoy su modelo no las declara).

## Siguiente (en orden) — decisión del 12-10-2026: continuar con los módulos del SIG; la cadena operativa queda en espera

1. [x] **Cerrar M10 Auditorías**: cerrado en 0.2.8 (secuencia del procedimiento, etapas de solo lectura, formatos iguales a las plantillas, listas ISO completas). Acta de validación preparada, pendiente de firma.
2. [ ] **Regla "etapa cerrada = solo lectura" (ADR-0005) en los módulos ya construidos.** Ya declaran `ETAPAS` / `etapas_abiertas`: M10 Auditorías, M8 Hallazgos, M9 Acciones correctivas, M7 Procesos (ficha), M17 Cambios, M18 Quejas, M3 Riesgos (riesgos y oportunidades de mejora), M23 SST (ATS e incidentes). **Faltan:** M6 Documentos (metadatos de una versión aprobada), M12 Competencia y M13 Equipos (evaluaciones, calibraciones y cartas ya emitidas; hoy solo tienen el candado «reenviar»). Revisar campo por campo y acción por acción, con pruebas.
3. [ ] **Módulos del SIG pendientes**: M23 SST (capacitaciones, inducción y simulacros, después) · M22 Medio ambiente (0.9.0) · M11 Cumplimiento · M1 Planeamiento · M4 Indicadores · M5 Revisión por la dirección. Ya construidos: M18, M3, M2, M17, M7, M23 hasta 0.8.8. Cada uno con su ficha en `docs/modulos/`, formatos reales en `PROCEDIMIENTOS SIG/` antes de construir, pruebas y acta de validación.

## En espera — Cadena operativa (fase 3), con diseño aprobado en `PLAN_CADENA_OPERATIVA.md`

- [ ] **Fase 3.0 — Cimientos operativos**: instalar PostgreSQL en el PC, migrar la base, dividir `esynapse_sig` en apps por módulo (ADR-0004), maestros (Laboratorio como catálogo, Cliente, Contacto, Series de documento, Ubicaciones, Transportistas), máquina de estados y eventos, expediente con código y cronología. Pruebas en verde al terminar. `Respaldar.bat` a `pg_dump`.
- [ ] **Fase 3.1 — Comercial (M24)**: oportunidades, revisión de requisitos por ítem, catálogo y tarifas versionadas, cotización con revisiones y PDF, aceptación con evidencia, nota de pedido con fecha de compromiso.
- [ ] **Fase 3.2 — Logística de entrada**: recepción contra NP, guía de ingreso, acta, equipo histórico del cliente, inspección con fotos, cuarentena, etiquetas térmicas, ubicaciones y movimientos.
- [ ] **Fase 3.3 — OT y ejecución (M25)**: OT general con líneas por equipo/laboratorio (ADR-0003), vista por laboratorio, puerta G06 con M12/M13, registro técnico versionado, modo sin conexión.
- [ ] **Fase 3.4 — Certificados**: series por tipo de servicio, revisor ≠ ejecutor, plantillas, emisión con número, hash y firma PAdES, reemplazo controlado.
- [ ] Fases 3.5 (logística de salida), 3.6 (guías y facturas electrónicas, cobranza), 3.7 (cierre y tableros).

## Después (sin fecha)

**Riesgos y oportunidades (M3)** — ficha `docs/modulos/M03_riesgos.md`
- [x] Construido en 0.6.0 (app `riesgos`) con las decisiones de César del 2026-10-21 (13 categorías; equivalencias de procesos; varias acciones por registro). Validado en pantalla (2026-10-21; firmas con un usuario de prueba «prueba_gg», ya desactivado). Falta el acta.
- [ ] Datos de la carga para revisar en la matriz: R-075 estaba repetido (el segundo pasó a R-107, cuyo texto es una acción —regalo de bloqueadores— más que un riesgo: retirarlo o fusionarlo con R-075); R-075 y R-107 sin valoración (y son de SST/salud: evaluar si van al IPERC); R-019, R-022, R-031, R-034 y R-051 requieren acción y no tienen tratamiento; R-053 (aceptar) sin decisión documentada.
- [ ] Observaciones al procedimiento para su próxima versión: categorías (13, como el formato); versión «00» en el formato de la matriz.

**Requisitos legales (M2)** — construido en 0.7.0 (ficha `docs/modulos/M02_legal.md`); validado en pantalla el 2026-10-21 (cierre firmado con un usuario de prueba «prueba_gsig», ya desactivado); falta el acta. Validación completa del 2026-10-21 (lista, obligaciones, evaluación, derogación con evaluación abierta, permisos de lector, integración con Hallazgos y Cambios, PDF de los cinco ámbitos); firmas con usuarios de prueba desactivados al terminar. Revisar: Nº 033-2000-ITINCI (Medio Ambiente) figura «Vigente» pero su observación dice «Derogado por D.S. 003-2015-PRODUCE» → derogarla. Datos de prueba: norma «PRUEBA DA-acr-02P» (derogada) con dos obligaciones, norma anulada «PRUEBA DA-acr-01P», evaluación 2026 · Semestre 1 de Acreditación (cerrada; su columna sale después de la del Semestre 2 porque se abrió antes de la corrección), norma «PRUEBA DA-acr-06D» (Acreditación) con dos obligaciones, evaluación 2026 · Semestre 2 de Acreditación, hallazgo NC-013-2026 y solicitud de cambio SC-005-2026. Datos de la carga para revisar: 217 obligaciones sin enlazar a su norma de la lista (el texto del documento legal no coincidía con un código); la matriz de Medio Ambiente tenía fecha de actualización 2022; Sociolaboral sin evaluaciones registradas. Decisiones de César (2026-10-21): evaluación semestral; ámbito nuevo «Acreditación» (requisitos de INACAL); caja de control ASIG · GSIG · GG con la fecha y versión del procedimiento (confirmar). Observaciones al procedimiento: 5.a «Área General» → «Gerencia General»; título de la hoja «Otros requisitos»; fecha 2022 en Monitoreo MA.

**Organización y personal (núcleo, ADR-0006)** — construido en 0.8.2
- [x] Decisión de César (2026-10-22): áreas, puestos y trabajadores como datos únicos del núcleo, mantenidos desde Administración; RRHH (fase 5) los extiende. Trabajadores: Administración; áreas, puestos y perfiles: SIG.
- [x] Validado en pantalla el 2026-10-22: organigrama, perfil de puesto (visto en Competencia técnica), alta de trabajador, usuario creado y vinculado (tomó cargo, área y laboratorio), cambio de puesto (la firma cambió sola), cese (usuario desactivado), puestos e área del organigrama en SST, aviso en Configuración. Datos de prueba: trabajador «PRUEBA Ana Ríos Organización» (cesado) y usuario «prueba_org» (desactivado); el perfil de «Metrólogo» quedó en la versión 2 sin contenido (se cargó y se borró en la prueba).
- [ ] Revisar el organigrama y los puestos propuestos en la carga (a quién reporta cada uno, siglas de firma que faltan, si Logística depende de la Gerencia Técnica o de Administración, laboratorios de Gases y Análisis Químico por separado).
- [ ] Registrar a los trabajadores y vincular cada usuario a su trabajador (sus firmas toman cargo y sigla del puesto).
- [ ] Cargar los perfiles de puesto (manual de funciones) en Puestos.
- [ ] Asignar el área del organigrama a las filas IPERC de las hojas «Gerencias», «Comedor», «Terceros» y «Análisis Químico y Gases» (o dejarlas como lugar o grupo).
- [x] 0.8.3: ATS (ejecutantes), IPERC (responsables, filtro por área) y riesgos del trabajador alineados con Organización y personal. Validado en pantalla el 2026-10-22 (riesgos de un metrólogo de Fuerza y Presión: 60 filas; ATS con un trabajador y un externo; responsables y filtro por área; PDF). Datos de prueba: trabajador «PRUEBA Luis Paz SST» (cesado) y ATS «PRUEBA 0.8.3» (anulado).
- [ ] Revisar los puestos creados desde la matriz IPERC: «Supervisor de SSOMA» (Gerencia SIG), «Encargado de Recursos Humanos» y «Encargado de Compras» (Administración). Si alguno equivale a un puesto existente, cambie las filas y desactívelo.
- [ ] Llevar al catálogo: ubicación de equipos (revisar con la fase 3) y área de la entrevista de seguimiento.

**Seguridad y Salud en el Trabajo (M23)** — ficha `docs/modulos/M23_sst.md`
- [x] Plan acordado con César (2026-10-22): 0.8.0 puestos + IPERC + ATS; 0.8.1 ATS en campo (agregado el 2026-10-22); 0.8.2 Organización y personal y 0.8.3 su alineación con SST (agregados el 2026-10-22); 0.8.4 incidentes y accidentes; 0.8.5 saneamiento (modo pruebas, agregado el 2026-10-22); 0.8.6 inspecciones y monitoreos; 0.8.7 EPP (firma del trabajador con PIN), Comité (resultado de la elección + actas firmadas adjuntas), Programa SSOMA y vigilancia médica; 0.9.0 Medio ambiente.
- [x] Formatos faltantes diseñados (2026-10-22) en `PROCEDIMIENTOS SIG/Formatos SST (propuesta)/`: Registro de enfermedades ocupacionales, Registro de exámenes médicos ocupacionales (solo aptitud, sin diagnóstico) y Registro de inducción, capacitación, entrenamiento y simulacros. Falta que César los revise y los cargue en la lista maestra.
- [x] Construido 0.8.0 (app `sst`): catálogo de puestos, matriz IPERC (385 filas cargadas de 16 hojas), ATS y sus PDF. Validado en pantalla el 2026-10-22 (fila nueva → requiere control → trabajo detenido → controlado → retirada; filtros por área, puesto, nivel y situación; ATS con etapas, rechazo por riesgo intolerable, contraseña incorrecta y validación firmada; revisión del área firmada; PDF). Segunda ronda del 2026-10-22 desde la pantalla, en un navegador aparte con usuarios de prueba: validación del ATS con la ventana de firma (contraseña incorrecta y correcta), anulación con motivo, revisión del área firmada, impresión de ATS y matriz, y usuario solo lector (sin botones de edición; el servidor rechaza con 403). Usuarios «prueba_sst», «prueba_sst_sup» y «prueba_sst_lec» y sus roles temporales, ya desactivados. Falta el acta. Datos de prueba: fila IPR-386 (retirada), ATS-001-2026 y ATS-002-2026 (validados), ATS-003-2026 (anulado), revisiones del 2026-10-22 de Fuerza y Presión y de Temperatura y Humedad (fijan la fecha de actualización del PDF de esas áreas: si no corresponde, registre de nuevo la revisión real).
- [x] **26 filas cuyo índice de probabilidad estaba escrito a mano** en el Excel: recalculadas en la carga (observación en el historial de cada una). Revisadas el 2026-10-22: las 26 quedan aceptables (14 Moderado, 11 Tolerable, 1 Trivial), todas con controles y ninguna exige evaluación residual. César conforme.
- [x] Construido 0.8.1 (ATS en campo: formato de Metrindust o del cliente, ATS tipo, envío a campo, recepción con adjunto, revisión de SST). Validado en pantalla el 2026-10-22: ATS tipo creado desde la pantalla; ATS en campo preparado desde el tipo, enviado (PDF), transcripción con la preparación bloqueada, recepción con archivo, devolución con observación, nueva recepción y revisión firmada; ATS con formato del cliente (sin etapas ni PDF) recibido y revisado con observación; guardar ATS como tipo; resumen con pendientes; listas de sugerencias en SST y Requisitos legales. Firmas con el usuario temporal «prueba_sst_rev», ya desactivado. Datos de prueba: ATS tipo «PRUEBA — Calibración de balanzas en planta» y «PRUEBA — Balanza camionera» (desactivarlos cuando carguen los reales), ATS-004-2026 y ATS-005-2026 (revisados).
- [ ] Cargar los ATS tipo de los servicios que se hacen en campo (balanzas en planta, manómetros en línea, tanques…): se crean en la pestaña «ATS tipo» o se guardan desde un ATS ya preparado.
- [ ] 32 filas del Excel sin evaluación (sin índices ni situación): evaluarlas en el sistema (aparecen como «sin evaluar»).
- [x] Equivalencias de puestos de la carga confirmadas por César (2026-10-22): «Encargado logístico» → Coordinador Logístico; «Gerente de I+D» → Gerente de I+D+i; las filas «todas las actividades» del área tomaron los puestos del área.

**SST — incidentes, accidentes, enfermedades y estadísticas (0.8.4)**
- [x] Decisiones de César (2026-10-22): acciones vía hallazgo → solicitud de acción correctiva; horas-hombre propuestas desde Organización y editables; índices de la R.M. 050-2013-TR; todo en una entrega.
- [x] Construido 0.8.4. Validado en pantalla el 2026-10-22 (accidente leve AT-001-2026: reporte, afectado, investigación, conclusión y revisión firmadas → hallazgo NC-014-2026 + SAC-07-2026; los 4 PDF; estadísticas de octubre con HH propuestas 528 y editadas). Falta el acta.
- [ ] Datos de prueba de la validación 0.8.4: AT-001-2026 (en acciones), NC-014-2026, SAC-07-2026 y el trabajador «PRUEBA Mario Evento SST» se quedan hasta la puesta en marcha; el usuario temporal «prueba_sst_ev» y su rol se desactivan ya (ver «Ahora»).
- [ ] Observaciones a los formatos del procedimiento: la hoja «Estadística de accidentes» del Registro de estadísticas lleva el título «Registro de accidentes e incidentes peligrosos»; el formato «Datos para registro de estadísticas» usa fórmulas distintas (IF × 100 000; IG = días / (HH × 1000)) y horas-hombre fijas (3 × 8 × 5 × 4): corregir a las de la R.M. 050-2013-TR; el procedimiento remite a un «Anexo 1» de causas que no existe (Anexos: no aplica). El informe de investigación pide «N° proyecto»: el sistema imprime el cliente y la actividad.

**SST — inspecciones y monitoreos (0.8.6)**
- [x] Decisiones de César (2026-10-22): motor de plantillas (tres familias: por elemento, por preguntas, por trabajador) con los 11 formatos cargados; inventario de elementos de seguridad y vehículos con alertas de vencimiento; «No conforme» con acción inmediata y hallazgo opcional; inspecciones y monitoreos en una sola entrega.
- [x] Construido 0.8.6: inventario de elementos de seguridad, 11 plantillas cargadas, inspecciones con acciones y hallazgo opcional, programa de inspecciones, programa anual de monitoreos, registro de monitoreos y seguimiento de recomendaciones (cargados 2025-2026). Validado en pantalla el 2026-10-22: dos extintores con alerta de vencimiento; INS-001-2026 (completar como conforme, NC, aviso antes de pedir la firma, acción, firma con usuario temporal ya desactivado, hallazgo NC-016-2026, acción completada → cerrada, PDF); inspección de EPP con «Requiere cambio» invertido (INS-002-2026, anulada); programa sin alertas de meses anteriores al sistema; monitoreos con sus tres PDF. Falta el acta. Datos de prueba: PRUEBA-EXT-01 y PRUEBA-EXT-02, INS-001-2026, NC-016-2026 y su solicitud.
- [ ] Registrar el inventario real: extintores (con fechas de recarga y prueba hidrostática), luces de emergencia, detectores, escaleras, botiquines por piso, kit antiderrame del laboratorio de Análisis Químico, vehículos y motos (SOAT y revisión técnica).
- [ ] Revisar las recomendaciones cargadas del monitoreo 2025: responsable de cada una y estado (se infirió de la columna de observaciones).
- [ ] Observaciones a los formatos del procedimiento de seguimiento y medición: el formato de extintores imprime el código del de botiquines (r01 en lugar de r02); el Programa anual del SIG imprime el código r16 en lugar de r15; el procedimiento no fija la frecuencia de los detectores, escaleras ni EPP (el sistema usa mensual, trimestral y bimestral según los Excel).

**SST — EPP y vigilancia médica (0.8.7) · Comité y Programa SSOMA (0.8.8)**
- [x] Decisiones de César (2026-10-22): firma del trabajador con PIN personal (papel adjunto como respaldo); sin stock de EPP en SST (se integra con Inventarios); dos entregas (0.8.7 EPP y vigilancia médica; 0.8.8 Comité y Programa SSOMA); capacitaciones después.
- [x] Construido 0.8.7 (EPP: catálogo, matriz por puesto, entregas con PIN, devoluciones; vigilancia médica). Validado en pantalla el 2026-10-22: trabajador de prueba de Masa y Volumen; «traer los que faltan» trajo los 10 EPP de su fila de la matriz; panel de firma con PIN nuevo; firma (responsable temporal ya desactivado + PIN creado), reposición por daño con PIN errado (avisa intentos) y correcto, situación por trabajador y PDF; evaluación médica EMO-001-2026 (apto con restricciones, próximo examen a 12 meses por ser operativo, firma, vista por trabajador, PDF). Falta el acta. Datos de prueba: trabajador «Rosa PRUEBA EPP», EPP-001-2026, EPP-002-2026, EMO-001-2026.
- [ ] Definir la **vida útil** de cada EPP del catálogo (la matriz no la traía): sin ella no se alerta la renovación.
- [ ] Matriz de EPP: asignar el perfil «Motorizado» a un puesto del organigrama (no existe; ¿Conductor / Operador Logístico?) y confirmar qué significa «x*» (se cargó como «según la tarea»). La fila de administrativos se aplicó a los puestos de oficina; revisar.
- [ ] Revisar el formato propuesto del registro de exámenes médicos y cargarlo en la lista maestra.
- [x] Construido 0.8.8 (Comité SST: miembros, reuniones con acta firmada adjunta, acuerdos; Programa anual SSOMA 2026 cargado; cargo de entrega de resultados médicos con PIN; Anexo 4). Validado en pantalla el 2026-10-22 con usuario temporal (ya desactivado): miembros de prueba como presidente y secretario (alertas resueltas; rechaza repetir al trabajador), T-Registro, reunión 001-2026-CSST (rechazo sin quórum, cierre con acta adjunta, solo lectura, PDF), seguimiento del acuerdo, ejecución de un mes del programa con evidencia (anulada luego; rechaza mes futuro), cargo de resultados de EMO-001-2026 con PIN nuevo (se restableció el PIN de la trabajadora de prueba) y Anexo 4 con reemplazo. Falta el acta.
- [x] 0.8.11 (César, 2026-10-22): la matriz IPERC la aprueba el Comité (por hojas; pendiente si cambia; pie del formato en el PDF); regla de firma: contraseña si tiene usuario, PIN si no. Se retiraron 32 filas del pie mal cargadas (353 vigentes).
- [x] 0.8.11 validado en pantalla el 2026-10-23 con usuarios temporales (desactivados): cambio en una fila de Comedor → «Pendiente de aprobación» → aprobación del Comité con un titular por contraseña de usuario y otro por PIN nuevo; contraseña errada rechazada nombrando a la persona; vuelve a «Aprobada»; PDF con el pie del formato. Ajuste: si una firma falla, ya no se guarda el PIN nuevo de los demás.
- [ ] **Dato de prueba**: la hoja Comedor tiene una aprobación del 23/10/2026 firmada por los miembros de prueba (PRUEBA Mario, Rosa PRUEBA). Al registrar al Comité real, volver a aprobar Comedor (y las hojas que cambien); la aprobación del 15/12/2025 de las demás quedó cargada.
- [x] 0.8.9 (César, 2026-10-22): navegación de SST en tres niveles (grupos subrayados, secciones en píldoras, vistas en control segmentado) con el componente común de navegación de módulos. Aplicarlo a otros módulos cuando tengan más de 5 secciones.
- [ ] **Datos de prueba de 0.8.8 en la base real**: miembros «PRUEBA Mario Evento SST» (presidente) y «Rosa PRUEBA EPP» (secretaria) en el comité 2025-2027 — darlos de baja al registrar a los miembros reales; reunión 001-2026-CSST con acta de prueba; **Anexo 4 de 2025 registrado como PRUEBA**: reemplácelo («reemplazar») con el cargo real o el sistema lo mostrará al día; T-Registro con fecha de prueba 2025-06-10: corregir con la real.
- [ ] **Anexo 4 de 2025 (para después, César 2026-10-23)**: el registro actual es de prueba (PDF sin contenido real, observación «PRUEBA») y hace que Vigilancia médica lo muestre «Al día». Por confirmar: ¿se presentó el informe de 2025? Si se presentó → «reemplazar» con el cargo real, fecha real y motivo «Se reemplaza el registro de prueba». Si no se presentó → agregar en el sistema «anular registro de prueba» para que vuelva el aviso de vencido.
- [ ] Registrar en Organización y personal a los 4 miembros del comité 2025-2027 (César Soto, Ana Aguilar, Miryam Canaza, Mauricio López) y luego en Comité de SST; registrar la fecha del T-Registro y adjuntar las actas de elección e instalación.
- [ ] El formato de acta de reunión del comité (SIG-PRO-13-r08) es copia del acta de instalación: el sistema imprime un acta de reunión propia; revisar y actualizar el formato en la lista maestra.

**Cambios (M17)** — requisitos en `docs/modulos/M17_cambios.md`
- [x] Decisión de César (2026-10-21): todo cambio lo aprueba el Gerente General.
- [x] Aceptado por César (2026-10-21): clasificación mayor/menor además de la prioridad; plan de la Solicitud para cambios menores y Planificación obligatoria para mayores y técnicos.
- [x] Construido en 0.5.0 (app `cambios`). Validado el 2026-10-22 con los 9 criterios de la ficha (SC-006-2026, cambio mayor y técnico que afecta clientes: cada regla rechazada y luego cumplida; resolución firmada por un aprobador; aviso «ficha por revisar»; cierre, reapertura con motivo y nuevo cierre; los tres PDF; ficha en pantalla). Usuarios y roles temporales «prueba_val_*», ya desactivados. Falta el acta.
- [x] Cambio temporal: estado «Temporal en vigor», prórroga firmada por el GG y nueva solicitud para volverlo permanente (decisión de César 2026-10-21; 0.5.1).
- [ ] Observaciones al procedimiento para su próxima versión: «Control Mayor» → «Cambio Mayor»; la versión de los formatos se escribe 00.

**Procesos (M7)** — documentos fuente en revisión
- [x] Propuesta en `PROCEDIMIENTOS SIG/Procesos (propuesta)/` (mapa, 16 fichas corregidas y 2 nuevas). Decisiones de César del 2026-10-21 (hoja «Resumen» del registro de cambios): un solo código SIG-M-01-r03 para todas las fichas; Gerente General responsable de Gestión Estratégica; quedan las metas propuestas; fichas nuevas validadas; los documentos citados existen; lo demás se mantiene como se aplicó.
- [x] Mapa: se quitó «Procesos externos» de la leyenda (2026-10-21).
- [ ] Faltan dos datos: puntajes de Compras y de Calibración y Verificación en la priorización; códigos vigentes de COM-PRO-02, TH-PRO-01 (r01, r02, r06) e IT-02.
- [x] Firmas de fichas y mapa: elabora Asistente SIG, revisa Gerente SIG, aprueba Gerente General (2026-10-21; aplicado en la propuesta).
- [x] Construido en 0.4.0 (app `procesos`), ficha `docs/modulos/M07_procesos.md`. Requisitos acordados (bocetos del 2026-10-21): mapa generado del catálogo; ficha con proveedor/cliente del catálogo y documentos de la lista maestra; versión con revisión y aprobación (ASIG → GSIG → GG); el campo «proceso» de Documentos, Hallazgos, SAC, Quejas y Auditorías pasa a ser el catálogo (migrar los textos existentes); lo vinculado se actualiza solo; el contenido aprobado de la ficha nunca lo cambia el sistema: cuando se aprueba un documento o entra un módulo que afecta un proceso, se crea el aviso «ficha por revisar» para su responsable. Regla para módulos futuros: todo registro nuevo con proceso usa el catálogo.
- [x] **M7 cerrado** por César en 0.4.1; acta `docs/validacion/M07_acta_2026-10-21.md` (por firmar).
- [ ] Pasar las 18 fichas cargadas por las firmas (ASIG → GSIG → GG).
- [ ] Asignar en el catálogo el usuario que recibe los avisos de cada proceso.
- [ ] Vincular a la lista maestra los documentos de las fichas que figuran como «sin vincular» (a medida que se carguen en Documentos).
- [ ] Corregir los procesos «sin vincular» de los hallazgos de prueba o desactivarlos.

**Quejas (M18)** — construido en 0.3.0
- [x] Validado el 2026-10-22 con los 8 criterios de `docs/modulos/M18_quejas.md` §6 (RQ-004-2026: validación, evaluación, decisión procedente firmada por un aprobador, NC-015-2026 sin duplicar, cierre rechazado si notifica un involucrado, reapertura con motivo, segundo cierre desde la pantalla, plazos marcados, los dos PDF). Falta el acta.
- [ ] Encuestas de satisfacción (parte de M18): construir cuando se tenga su formato; automatizar la regla del procedimiento (más de dos «Insatisfecho»/«Muy insatisfecho» en una misma pregunta → queja).
- [ ] Consulta del estado de la queja por el cliente con su código RQ: al publicar el sistema en un servidor con acceso desde internet.
- [ ] Trabajo no conforme: hoy es una marca en la queja; enlazar con M16 cuando se construya.
- [ ] Incluir las quejas en Mis tareas / Calendario (plazos por vencer) y en el tablero.

**Hallazgos y Acciones correctivas (M8/M9)**
- [ ] Emitir la nueva versión de la plantilla de la Solicitud de Acción Correctiva con la causa raíz como sección 7 (11 secciones, como ya imprime el sistema desde 0.2.13), aprobarla en Documentos y vincularla en Configuración → Formatos impresos para que el PDF tome su versión y fecha.
- [ ] Validar en pantalla los cambios de Hallazgos (0.2.9) con los criterios de `docs/modulos/M08_hallazgos.md` §5.
- [x] **M9 Acciones correctivas cerrado** en 0.2.15 (2026-10-20): ajustado al procedimiento, ficha con todas las secciones, agregar/corregir/quitar/reabrir acciones, PDF de 11 secciones y seguimiento en Arial 11. Acta preparada, por firmar.
- [ ] M9: decidir si la justificación de la evaluación es obligatoria cuando la NC se trata solo con corrección (recomendado).
- [ ] M9: plantilla del seguimiento — reflejar la hoja horizontal en su próxima versión.

**Formatos que el sistema aún no genera** (las plantillas están en `PROCEDIMIENTOS SIG/`; en 0.2.7 se igualaron todos los que sí genera)
- [ ] Equipos (M13): Informe de mantenimiento, Informe de comprobación intermedia, Control de salida y entrada del equipamiento (hoy solo existen como hojas de la bitácora; falta su captura y su PDF propio).
- [ ] Equipos (M13): Informe de caracterización (la plantilla es un libro con macros y cálculos por magnitud; definir si se replica el cálculo o se adjunta el archivo).
- [ ] Formatos del procedimiento de métodos: se construyen con M14.

**Auditorías (M10)** — módulo cerrado en 0.2.8; lo siguiente son mejoras, no bloquean su uso
- [ ] Representante(s) del área auditada en el informe: exigir al menos un participante "Auditado" en las actas de apertura y cierre, y usar la columna "Auditado" del cronograma como respaldo (propuesto el 2026-10-16; César decidió postergarlo).
- [ ] Conectar las observaciones y oportunidades de mejora de auditoría (marcadas "riesgos y oportunidades") con M3 Riesgos cuando se construya, según el procedimiento de identificación de riesgos y oportunidades.
- [ ] Hacer editables áreas/procesos y fecha programada después de crear la auditoría.
- [ ] "Quitar integrante" del equipo auditor borra el registro: pasarlo a baja lógica (regla de no eliminar), conservando quién fue quitado y cuándo.
- [x] Control de versión/fecha/siglas de cada formato desde la lista maestra (0.2.5). Pendiente operativo: **registrar en Documentos los formatos como documentos tipo "formato"** (hijos de su procedimiento) y vincularlos en Configuración → Formatos impresos; cargar la **sigla del cargo** de cada firmante en Usuarios.

**Recorrido de prueba del 2026-10-20 (0.2.11) — observaciones no corregidas**
- [x] **Seguridad:** la contraseña del administrador escrita por error en el resumen de cambios de una versión de un procedimiento se retiró de ese campo y de su entrada del log (2026-10-22, a pedido de César; queda «prueba» y una entrada del log con el motivo; el PDF firmado no la contenía).
- [ ] **Seguridad:** cambiar la contraseña del usuario administrador (estuvo visible desde el 2026-10-20) y, hecho eso, la copia `backups/db_antes_retiro_dato_20261022_145932.sqlite3` deja de ser sensible.
- [x] Competencia: la autorización exige entrenamiento superado del mismo método (decisión de César, 0.2.12).
- [x] Competencia: totales del seguimiento calculados en el servidor (0.2.12).
- [ ] Competencia: registrar el cargo «Gerente Técnico» en Usuarios para que pueda usarse la exención de entrenamiento.
- [ ] Datos de prueba del recorrido por desactivar: AI-11-2027 (NC-001-2027, OBS-001-2027), autorizaciones 2-4, entrenamientos de prueba, seguimientos 1-2, equipo PRUEBA-01, SAC-02/04 con NC-008/009/010 y OBS-004.

**Módulos construidos — deuda y validación**
- [x] M9: pruebas automáticas del ciclo de la SAC y de la segregación (verifica el designado o quien puede aprobar) — 21 pruebas en 0.2.15.
- [ ] M8: validación completa con un hallazgo real (ciclo, reapertura, correlativos).
- [ ] M13: pruebas del candado sobre bitácora, intervalo y nodo; prueba de la regla de patrón vigente cuando exista la OT.
- [ ] M6: confirmar descarga del archivo anotado; instalar `ca_sige360_publico.cer` en los PC; cargar documentos reales del SIG; certificado `.pfx` de cada firmante.
- [x] Residuos del taller movidos a `_archivo/` (0.8.5, no se borraron): `_renametest3/`, los tres scripts de diagnóstico, la base corrupta de junio, `firma_error.log` y las carpetas `_broken_clean_git_*` y `_evicted_backups_*`. `obser.txt` se dejó (notas de César). `_archivo/` está fuera de Git y de la carpeta limpia.
- [ ] Mover el contenido útil de `CONTEXTO_PROYECTO.md` a `docs/` y dejarlo como histórico.

**Producción (cuando pase a servidor)**
- [ ] `SECRET_KEY`, base de datos y `DEBUG` por variables de entorno; HTTPS; política de contraseñas y bloqueo por intentos.
- [ ] Ambientes separados (pruebas / producción), respaldo automático fuera de sede, restauración probada.
- [ ] Manual de usuario por módulo.
- [ ] Multi-tenant (diseñado, no activado).

## Decisiones pendientes (bloquean tareas)

| ID | Pregunta | Bloquea | Quién responde |
|---|---|---|---|
| P-01 | ¿Dentro de la serie MT se distingue certificado acreditado (símbolo INACAL) de no acreditado, o es solo una marca en el documento? | Plantilla de certificado (3.4) | Calidad |
| P-02 | Proveedor OSE/PSE para guías y facturas electrónicas | Fase 3.6 | Administración |
| P-03 | **Archivos reales de un certificado de calibración y de una OT** (para replicar las plantillas 1:1) | Fases 3.3 y 3.4 — **se necesitan antes de empezar 3.3** | César |
| P-04 | Política de pago y retención de certificado por cliente (valores por defecto) | Fase 3.5 | Gerencia |
| P-05 | Inventario de métodos por laboratorio con versión vigente (M14 no existe aún) | G02 y G06 usan catálogo provisional | Calidad / Resp. técnico |
