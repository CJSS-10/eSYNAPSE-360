# Registro de cambios — eSYNAPSE 360

Cada entrega registra: versión, fecha, cambios en lenguaje de negocio, si exige migración y qué probar. La versión instalada se lee en `backend/VERSION` y se muestra en Configuración. Formato de versión: ver `docs/01_metodo_de_trabajo.md` §4.

---

## 0.14.4 — 2026-10-27 · Búsqueda global, enlaces directos a cada ficha y avisos de guardado

**Migración:** no. Si el backend no se reinicia solo, cerrar su ventana e iniciar de nuevo; recargar la página (Ctrl + F5).

### Nuevo
- **Búsqueda global** en la barra superior, también con **Ctrl + K**:
  - busca por código o texto, **con o sin tildes** («manometro» encuentra «Manómetro»), en hallazgos, acciones correctivas, quejas, cambios, auditorías, documentos, equipos, riesgos y oportunidades, trabajo no conforme y revisiones por la dirección; también encuentra los módulos por nombre;
  - hasta 6 resultados por módulo, primero los de código exacto; solo muestra lo que el usuario puede leer y lo que no está dado de baja;
  - con el teclado: ↑ ↓ para moverse, Enter para abrir, Esc para cerrar.
- **Enlace directo a la ficha** (`/modulo?abrir=<id>`): elegir un resultado de la búsqueda, una tarea en Mis tareas, una notificación de la campana o un pendiente del Tablero **abre directamente la ficha del registro** (antes llevaba solo a la lista del módulo). Las tareas del buzón ahora incluyen el registro al que pertenecen.
- **Avisos de guardado** en la esquina inferior derecha, iguales en todas las pantallas, según la acción: «Registrado», «Cambios guardados», «Aprobado», «Devuelto para corrección», «Rechazado», «Firma registrada», «Enviado», «Enviado a cierre», «Cerrado», «Dado de baja», «Restaurado», «Archivo adjuntado», «Evaluación registrada» o «Guardado». Duran 3 segundos y no se repiten si un formulario guarda en varios pasos. Los errores siguen mostrándose junto al formulario, como hasta ahora.

### Técnico
- Servicio `GET /api/buscar/?q=` (`esynapse_sig/panel.py`, `BuscarView`): respeta licencias y permisos de lectura por módulo.
- `lib/enlaces.js` (`useAbrirDesdeEnlace`, `rutaRegistro`): la ficha se abre solo en la pantalla que queda tras la transición de página.
- `lib/avisos.js` y `components/Avisos.jsx`: cada escritura exitosa de la API avisa sola; las de sesión, búsqueda y PDF no avisan.

### Qué probar
- Ctrl + K desde cualquier pantalla: «SAC-06», «FP-02», «manometro», «extintores», «equipos».
- En Mis tareas y en la campana, al hacer clic en una tarea se abre su ficha.
- Guardar, aprobar o dar de baja algo de prueba: el aviso en la esquina inferior derecha.

---

## 0.14.3 — 2026-10-27 · Interfaz: Equipos al estándar y microinteracciones en todo el sistema

**Migración:** no. Recargar la página (Ctrl + F5). El filtro nuevo del PDF de inventario toma efecto al reiniciar el backend (o solo, si corre con recarga automática).

### Equipos (sin cambiar las columnas del inventario, por decisión de César)
- **Filtro de calibración** como control segmentado: *Todos · Calibración vencida · Vence en 30 días* (antes, una casilla «solo vencida» en otra fila). El PDF del inventario respeta los tres.
- **Encabezado con una sola acción principal** («Nuevo equipo»). «Cambios por aprobar» aparece como aviso ámbar solo cuando hay alguno; «Mis solicitudes» se resalta solo si tienes alguna devuelta; «Catálogos» queda como botón discreto.
- **Ficha**: las bandas azul marino en mayúsculas pasan a las secciones estándar del resto de fichas (el PDF de la hoja de vida no cambia).
- Pestañas y actividades en tipo oración y sin abreviar: «Programa anual», «Intervalo de calibración», «Carta de trazabilidad», «Ficha técnica», «Comprobaciones intermedias», «Comprobación intermedia / funcional».
- El código del equipo va en el color del texto, como en los demás módulos.

### Microinteracciones (todo el sistema)
- La **línea de la pestaña activa** se desliza hasta la elegida (pestañas de módulo y grupos de navegación).
- El **fondo de la opción elegida** en los controles segmentados (Abiertas / Todas y similares) se desliza.
- La **selección del menú lateral** se desliza entre opciones; los **contadores** rebotan cuando cambian.
- **«Por construir»** se despliega con animación de altura.
- **Fichas y ventanas**: el fondo se atenúa con un desenfoque leve; la ficha entra desde la derecha y la ventana aparece con una ligera ampliación.
- **Barra de etapas**: al avanzar, el tramo hacia la nueva etapa se rellena de izquierda a derecha.
- **Botones** que se hunden levemente al pulsarlos.

### Corregido
- Entre las 12:11 y las 13:40 del 27-10-2026 la pantalla de Equipos no cargaba: un cambio quedó aplicado a medias. Resuelto en esta versión.

### Qué probar
- Equipos: los tres filtros de calibración y el PDF; el aviso de cambios por aprobar (con un usuario aprobador y un cambio pendiente); la ficha con secciones claras.
- Cambiar de pestaña en Riesgos, SST u Organización; Abiertas / Todas en Quejas o Acciones correctivas; navegar por el menú; abrir y cerrar «Por construir»; avanzar una etapa en una acción correctiva de prueba.

---

## 0.14.2 — 2026-10-27 · Interfaz: pantalla de ingreso y Tablero con movimiento

**Migración:** no. Recargar la página (Ctrl + F5).

### Cambiado (propuesta visual del 27-10-2026, aprobada por César para estas dos pantallas)
- **Pantalla de ingreso**:
  - panel de marca a la izquierda, en azul Metrindust, con un dial de calibración cuya aguja barre lentamente, una señal que se desplaza, las cuatro normas y la versión;
  - el formulario a la derecha; en pantallas angostas el panel se oculta y queda solo el formulario;
  - si el usuario o la contraseña no son correctos, el formulario se sacude una vez y el mensaje aparece junto a los campos.
- **Tablero**:
  - el saludo va en una franja azul con regla graduada y señal de calibración en movimiento lento; los vencidos, los que vencen en la semana y las tareas asignadas se muestran en grande y llevan a su sección;
  - las cifras cuentan desde cero al cargar;
  - las tarjetas de cada módulo entran escalonadas, llevan arriba un filete con el color de su norma (el mismo de su etiqueta) y se elevan al pasar el mouse;
  - las filas de vencimientos y tus pendientes entran una tras otra.
- **Reglas de movimiento** comunes en la hoja de estilos (`mov-*`): solo se animan posición y opacidad, con duraciones de 120 a 750 ms. Si Windows tiene activado «reducir animaciones», no se anima nada.

### Qué probar
- Cerrar sesión y volver a entrar: el panel de marca, y la sacudida con una contraseña incorrecta.
- Tablero: la franja, el conteo de las cifras y las tarjetas al pasar el mouse; también en modo oscuro.

---

## 0.14.1 — 2026-10-27 · Cumplimiento: por sede y PDF de la matriz

**Migración:** sí (`cumplimiento 0002–0003`: evaluación por sede y registro del formato impreso). Cerrar la ventana del backend → `Aplicar actualizacion.bat` → `Iniciar` → recargar (Ctrl + F5).

### Decisiones de César (2026-10-27)
- **SIG completo y por sede, con calificación individual**
  - Cada requisito tiene su propia evaluación para el SIG completo y para cada sede (estado y cómo se cumple o evidencia en la sede, obligatorio).
  - Las calificaciones **no se comparten ni se combinan**: una sede sin evaluar queda «sin evaluar» y su porcentaje solo considera lo evaluado en ella.
  - Dónde se ve:
    - el tablero muestra el cumplimiento por sede;
    - la matriz tiene la vista «SIG completo / sede»;
    - las cláusulas comunes se reflejan con su evaluación por sede;
    - la brecha registrada como hallazgo puede indicar la sede (va como lugar de detección).
- **PDF «Matriz de evaluación del cumplimiento de requisitos»** (formato nuevo, A4 horizontal):
  - cabecera con caja de control (código «POR ASIGNAR» hasta registrarlo en la lista maestra y vincularlo en Configuración); sin pie de página;
  - alcance, normas, fecha y emisor;
  - resumen por norma y por sede;
  - evidencia en alerta;
  - una matriz por norma con estado del SIG y de cada sede coloreado, cómo se cumple, documentos, hallazgo y última evaluación.
  - Se emite completo (botón «Matriz completa (PDF)») o por norma y sede (botón «PDF» en cada matriz).

---

## 0.14.0 — 2026-10-27 · M11 Cumplimiento

**Migración:** sí (`cumplimiento 0001`: evaluaciones, otros requisitos y cortes). Cerrar la ventana del backend → `Aplicar actualizacion.bat` → `Iniciar` → recargar (Ctrl + F5).

### Nuevo (diseño acordado con César el 2026-10-26) — ficha `docs/modulos/M11_cumplimiento.md`
- **Matriz de cumplimiento por norma** (ISO 9001, 14001, 45001 por cláusula; NTP ISO/IEC 17025 por numeral, más los ítems de seguimiento del organismo de acreditación), con el catálogo de requisitos de Auditorías.
- **Evaluación por requisito:**
  - estado: cumple / parcial / no cumple / no aplica, este último con justificación obligatoria;
  - proceso responsable (catálogo de Procesos), cómo se cumple, documentos de la lista maestra y evidencia;
  - fecha, autor e historial.
- **Correspondencia entre normas:** las cláusulas comunes de la estructura de alto nivel se evalúan una vez y se registran en las otras normas ISO (la 8.2 solo entre 14001 y 45001).
- **Evidencia automática** desde 20 verificaciones de los módulos (programa de auditorías, revisión por la dirección, riesgos e imparcialidad, evaluación legal, IPERC, aspectos ambientales, Comité de SST, Programa SSOMA, capacitación, autorizaciones, calibración de equipos, lista maestra, fichas de proceso y conteos de acciones correctivas, quejas, trabajo no conforme, cambios, monitoreos y consumos).
  - Un requisito que cumple o cumple en parte pasa a **en riesgo** si su evidencia está en alerta o si la evaluación tiene más de 12 meses.
- **Brecha → hallazgo:** un requisito parcial o incumplido se registra como hallazgo (NC mayor, NC menor u observación) con un clic; su tratamiento sigue en Hallazgos y Acciones correctivas.
- **Otros requisitos** (organismo de acreditación, entidad certificadora, clientes): se registran, se evalúan y se dan de baja con motivo.
- **Tablero:**
  - % de cumplimiento y cobertura por norma;
  - requisitos que requieren atención;
  - estado de la evidencia del sistema;
  - cumplimiento por proceso;
  - **cortes** para ver la evolución.
- **Revisión por la dirección:** la entrada de desempeño muestra el grado de cumplimiento actual de cada norma.

---

## 0.13.2 — 2026-10-27 · Trabajo no conforme: Jefe de Laboratorio

**Migración:** sí (`organizacion 0007`: crea el puesto «Jefe de Laboratorio»). Cerrar la ventana del backend → `Aplicar actualizacion.bat` → `Iniciar` → recargar (Ctrl + F5).

### Cambio (César, 2026-10-27) — procedimiento ajustado
- La reanudación de un trabajo **técnico** la autoriza el **Gerente Técnico o el Jefe de Laboratorio** (antes: Supervisor de Laboratorio). El administrativo sigue a cargo del Gerente SIG.
- Nuevo puesto **«Jefe de Laboratorio»** en Organización (reporta al Gerente Técnico, área y proceso de laboratorio). «Supervisor de Laboratorio» y «Encargado de Laboratorio» se mantienen, pero ya no autorizan la reanudación.
- Para que alguien autorice: en Organización › Trabajadores, asignarle el puesto «Jefe de Laboratorio» y vincularlo a su usuario.
- La Tabla N° 2 de consulta (nivel Alto) dice «Reanudación solo con autorización del Gerente Técnico o Jefe de Laboratorio», como en el procedimiento ajustado.

---

## 0.13.1 — 2026-10-27 · Trabajo no conforme: tablas de consulta

**Migración:** no. Basta recargar (Ctrl + F5).

### Mejora (César, 2026-10-27)
- **Tablas del procedimiento a la vista**: la Tabla N° 1 (responsabilidades y autoridades) y la Tabla N° 2 (niveles de riesgo y acciones) se consultan en una ventana sin salir del registro. Se abren con el botón «Tablas del procedimiento» del encabezado, «Tablas N° 1 y 2» en cada registro, «Ver Tabla N° 2» junto al nivel de riesgo (asignación y evaluación) y «Responsabilidades (Tabla N° 1)» en el tratamiento. Texto fiel al procedimiento versión 01.

---

## 0.13.0 — 2026-10-27 · M16 Trabajo no conforme

**Migración:** sí (`tnc 0001–0002`: registros, OT y certificados revisados, evidencias; habilita el módulo y registra el formato impreso). Cerrar la ventana del backend → `Aplicar actualizacion.bat` → `Iniciar` → recargar (Ctrl + F5).

### Nuevo (César, 2026-10-27) — replica el procedimiento de control de trabajos y salidas no conformes (versión 01) y su registro
- **Registro** (TSNC-NNN-AAAA): tipo TNC o SNC, naturaleza técnica o administrativa, categoría del incidente, área o laboratorio, reportado por, fechas de detección y de reporte al Gerente SIG y Gerente Técnico, fuente de detección, OT y certificados, equipos involucrados y descripción. La fuente «Queja del cliente» exige la queja de origen y «No conformidad» el hallazgo de origen.
- **Etapas** (lo de una etapa cerrada queda de solo lectura): registro → tratamiento → autorización → evaluación → cierre.
  - El Gerente Técnico o el Gerente SIG asigna el **nivel de riesgo** (Tabla N° 2) y el responsable del tratamiento, con su contraseña.
  - **Tratamiento:** acciones ¿aplica? / ¿ejecutada? (detención, repetición, retención, notificación al cliente, análisis de impacto retroactivo, equipo fuera de servicio), corrección y nota del cliente. Nivel **Alto** exige detención y análisis retroactivo (y equipo fuera de servicio si es un equipo). **Análisis de impacto retroactivo:** periodo, última condición conforme, OT y certificados (¿entregado?, ¿afectado?, acción), notificación, certificado anulado y de reemplazo, conclusión; un certificado entregado y afectado exige notificar al cliente. «Equipo fuera de servicio» ejecutado deja el equipo como inoperativo en Equipos.
  - **Autorización de la reanudación** con contraseña: trabajo técnico → Gerente Técnico o Supervisor de Laboratorio; administrativo → Gerente SIG (el Gerente Comercial solo gestiona la devolución del monto cancelado, según el procedimiento ajustado el 2026-10-27). Si no se acepta, vuelve al tratamiento.
  - **Evaluación de la importancia** (Área SIG): validez, requisitos del SIG, competencia, nivel confirmado; el sistema cuenta los **eventos similares** (misma área y categoría, 12 meses). La acción correctiva es obligatoria con nivel Alto o con 3 eventos similares.
  - **Cierre:** vincula o crea la solicitud de acción correctiva desde el registro, evidencias (texto y archivos) y firma.
- **PDF** del Registro en dos páginas con la disposición del formato.
- **Mis tareas:** asignar nivel, tratar, autorizar, evaluar y cerrar, según el puesto y el permiso.
- **Revisión por la dirección**, entrada p): trabajos y salidas no conformes del periodo por tipo, nivel, cerrados y con SAC.

---

## 0.12.0 — 2026-10-26 · M5 Revisión por la dirección

**Migración:** sí (`revision 0001–0002`: programa anual, revisiones, entradas, salidas, asistentes y acuerdos; habilita el módulo y registra sus tres formatos impresos). Cerrar la ventana del backend → `Aplicar actualizacion.bat` → `Iniciar` → recargar (Ctrl + F5).

### Nuevo (César, 2026-10-26) — replica el procedimiento versión 01 y sus formatos r01, r02 y r03
- **Programa anual**: las 23 entradas y las 10 salidas de la agenda con su responsable (puesto), los meses programados (P) y ejecutados (E) y observaciones. Un mes futuro no se marca ejecutado. PDF con el formato del Programa.
- **Revisión** (N° IRD-NN-AAAA, ordinaria o extraordinaria con motivo) en tres etapas; lo de una etapa cerrada queda de solo lectura:
  - **Preparación**: fecha, lugar, periodo evaluado y responsables de recopilar y verificar la información. El botón «Generar datos del sistema» trae, para el periodo, los datos de cada entrada desde los módulos construidos (contexto y riesgos, objetivos SSOMA, documentos, acuerdos anteriores, auditorías, acciones correctivas, quejas, mejoras, capacitación, requisitos legales, medio ambiente, SST, IPERC, Comité, simulacros y monitoreos). Las entradas sin fuente aún (volumen de trabajo, retroalimentación, recursos, validez de resultados, proveedores) se informan en el análisis. Para convocar, todas las entradas deben tener análisis o marcarse «sin actividad en el periodo».
  - **Reunión**: asistentes con firma de asistencia (contraseña de su usuario o PIN), salidas a) a j), acuerdos con elemento de origen, responsable, plazo y **costo estimado**, conclusiones, observaciones y comunicación de resultados a los trabajadores y al Comité de SST.
  - **Cerrar** exige conclusiones, las salidas a) a i), todos los asistentes firmados, entre ellos el Gerente SIG y el Gerente General, y la contraseña de quien cierra (permiso de aprobar).
  - PDF del Informe con encabezado en cada página y pie de documento confidencial.
- **Plan de acción**: todos los acuerdos con filtro de pendientes. Tras el cierre de la revisión solo se registran la evidencia (texto y archivo), el seguimiento del 1.er y 2.º semestre y el estado; el **V°B° de cumplimiento** exige evidencia y contraseña. PDF del Plan de Acción por revisión. Los acuerdos abiertos alimentan la entrada d) de la siguiente revisión.
- **Mis tareas**: el responsable de un acuerdo lo ve hasta cerrarlo (vencido si pasó la fecha).
- Una revisión registrada por error se **anula con motivo** en preparación o en reunión; cerrada ya no se anula.

### Ajustes tras la validación en pantalla (2026-10-26)
- Programa anual: las celdas de los meses se ven como casillas (antes no se notaba dónde hacer clic).
- Los datos del sistema de cada entrada se alinean como tabla de ficha (concepto a la izquierda, cifra a la derecha).
- Los mensajes de error de la ficha se desplazan a la vista; textos de los bloqueos de etapa más claros.
- Entrada b): la descripción de cada objetivo del Programa SSOMA se muestra completa (antes se cortaba).

---

## 0.11.0 — 2026-10-24 · Sedes: catálogo único y Medio ambiente por sede

**Migración:** sí (`organizacion 0004–0006`: sedes, niveles y suministros; convierte la sede y el piso que las áreas tenían como texto; ubigeo de la sede. `core 0017–0018`: catálogo de ubigeos del Perú. `ambiente 0003–0004`: consumo por suministro y sede en pesajes, disposiciones y aspectos). Cerrar la ventana del backend → `Iniciar` → recargar (Ctrl + F5).

### Nuevo (César, 2026-10-24)
- **Organización y personal › Sedes**: cada sede con nombre, código corto, dirección y distrito, **instalaciones propias o alquiladas**, sede principal y puesto responsable; sus **niveles / pisos**; y sus **suministros** de energía eléctrica y agua (de toda la sede o de un piso), con número de medidor, empresa prestadora, cómo se obtiene el consumo (lectura del medidor o recibo) y responsable del registro. Las áreas eligen sede y piso del catálogo (antes texto libre). Nada se borra: sedes, niveles y suministros se desactivan si no tienen dependientes activos.
- **Energía y agua por suministro**: se registra la **lectura del medidor** y el sistema calcula el consumo con la lectura anterior (la primera vez o si se cambió el medidor, se indica la lectura inicial con motivo). No acepta una lectura menor que la anterior ni mayor que la del mes siguiente; corregir o anular un mes recalcula el siguiente. También por recibo, dato del arrendador o estimado (marcado). Foto del medidor o recibo como evidencia. Aviso si el consumo supera en 50 % el promedio de los meses anteriores o si faltan meses.
- **Indicadores** por sede o de toda la organización: consumo mensual, registrados/esperados, por trabajador de la sede, frente al año anterior; detalle por suministro (clic para corregir, «+» para registrar el mes) y total por sede.
- **Mis tareas**: el responsable de cada suministro ve el registro del mes anterior pendiente (plazo: día 5).
- **Residuos y aspectos**: pesajes y disposiciones indican su sede (obligatoria cuando hay sedes) y se filtran por sede, igual que el resumen anual; un aspecto puede limitarse a una sede.
- **Ubigeos del Perú** (César): catálogo completo con codificación INEI — 25 departamentos, 196 provincias y 1 893 distritos, incluidos los de creación reciente. La dirección de la sede se elige con departamento → provincia → distrito encadenados (componente reutilizable para clientes y proveedores).
- **Configuración ordenada por pestañas** (César): Empresa (datos de la empresa y del empleador, lado a lado), Producto (solo el propietario), Formatos impresos (con filtro por módulo, búsqueda y cuántos están vinculados a la lista maestra) y Módulos.

### Datos
- El consumo de prueba de septiembre 2026 (1 250 kWh) queda como registro sin suministro: se suma al total y puede anularse.

---

## 0.10.2 — 2026-10-24 · Encabezados de tabla centrados y un solo bloque de firmas del Comité en los PDF

**Migración:** no. Recargar la página (Ctrl + F5); el backend toma los cambios de los PDF al reiniciarse solo.

### Cambiado (César, 2026-10-24)
- Los **encabezados de columna** de todas las tablas se muestran centrados horizontal y verticalmente. Los datos de cada columna conservan su alineación según el tipo de dato (texto a la izquierda, estados al centro, fechas y cantidades a la derecha).
- **Todo lo que firma el Comité de SST lleva el mismo bloque en el PDF**: «REALIZADO Y APROBADO POR» con nombre y cargo de cada titular, cómo firmó (usuario, PIN, acta en papel o formato original) y debajo la fecha de cada firma. Se aplica a la matriz IPERC, el programa anual de capacitación, la **matriz de aspectos ambientales** (antes una línea de texto) y el **Programa SSOMA** (antes una columna «Aprobado por»). Si está pendiente de aprobación, imprime a los titulares vigentes con las casillas en blanco y el aviso en rojo. La fila crece con el texto para que no se corten nombres largos.

### Validado en pantalla
- Programa SSOMA 2026: reprogramado (versión 2) y aprobado por los 4 titulares; con una firma faltante se rechaza nombrando al titular.
- Aprobación de la matriz IPERC y del programa de capacitación: piden los 4 titulares.

---

## 0.10.1 — 2026-10-24 · Todo lo que aprueba el Comité de SST lo firman sus cuatro titulares

**Migración:** sí (`sst 0019`: acta en papel de la aprobación del Programa SSOMA). Cerrar la ventana del backend → `Iniciar` → recargar (Ctrl + F5).

### Cambiado (César, 2026-10-24)
- **Una sola regla para el Comité:** la matriz IPERC, el programa anual de capacitación, la matriz de aspectos ambientales y el **Programa SSOMA** se aprueban con la firma de **todos** los titulares (contraseña de su usuario o PIN), o con el acta en papel firmada por todos. Antes IPERC y capacitación pedían la mitad más uno.
- **Programa SSOMA:** ya no lo aprueba solo quien lo registra; usa la firma del Comité (en pantalla o acta en papel). Reprogramarlo exige el permiso de aprobar.
- Las aprobaciones ya registradas no cambian. El quórum de las **reuniones** del comité sigue siendo la mitad más uno de los titulares (es asistencia, no aprobación).
- Componente común de firma del Comité en pantalla.

### Datos de prueba (desarrollo)
- Comité 2025-2027: dados de baja los dos miembros de prueba; registrados como titulares César Soto Soria (presidente), Erika Vega Rondo (secretaria), Mauricio López Falcón y Miryam Canaza Choquehuanca, con su trabajador y usuario de prueba para validar las firmas (puestos y DNI de prueba).

---

## 0.10.0 — 2026-10-24 · M22 Medio ambiente (nuevo módulo)

**Migración:** sí (`ambiente 0001` y `0002`: módulo nuevo, formatos impresos y carga de la matriz de aspectos). Cerrar la ventana del backend → `Iniciar` → recargar (Ctrl + F5). El rol que lo use necesita el permiso del módulo «Medio Ambiente».

### Nuevo
- **Medio ambiente** (menú Seguridad, salud y ambiente), según los procedimientos de aspectos e impactos, uso eficiente de energía y agua, y gestión de residuos sólidos:
  - **Aspectos e impactos:** lugar (área, laboratorios, oficinas, toda la empresa u otro), proceso del catálogo, situación N/A/E, generación, clase, ciclo de vida, controles, evaluación A–E con la tabla de valoración, control operacional, registro asociado, responsable (puesto) y plazo. **Significativo si suma ≥ 10 o hay incumplimiento legal** (regla del procedimiento); los positivos no se evalúan. El criterio A se propone desde la evaluación de cumplimiento de la obligación legal vinculada. PDF con el formato.
  - **Aprobación de la matriz por todos los titulares del Comité de SST** (usuario o PIN, o acta en papel); un cambio posterior la deja pendiente.
  - **Residuos sólidos:** pesajes con el formato (no peligrosos por tacho, peligrosos líquidos y sólidos, RAEE), cierre firmado, PDF; disposición con operadora, manifiesto y certificado (los peligrosos solo a una EO-RS); resumen anual en kg y toneladas para la declaración.
  - **Energía y agua:** consumo mensual del recibo (kWh, m³, monto, archivo) e indicadores: por trabajador y frente al mismo mes del año anterior.
- Carga: la matriz en Excel (330 filas en 12 hojas) consolidada en **176 aspectos, 5 significativos** (incendio y 4 por incumplimiento legal). Lista de cambios para revisar: `docs/modulos/M22_carga_matriz.md`.

### Cambiado
- La firma del Comité de SST admite exigir a **todos** los titulares (además de la mitad más uno).

### Qué probar
- Medio ambiente › Aspectos e impactos: filtros por lugar, «Significativos», editar un aspecto (el resultado y la significancia se recalculan), PDF.
- Aprobación del Comité: con los titulares reales registrados.
- Residuos: un pesaje con varias líneas → firmar y cerrar → PDF; una disposición; resumen anual.
- Energía y agua: registrar un mes y ver los indicadores.

---

## 0.9.4 — 2026-10-24 · «Mostrar anulados» y PDF de la ficha técnica

**Migración:** no. Recargar la página (Ctrl + F5).

### Nuevo
- **Mostrar anulados** (César, 2026-10-24): en la hoja de vida y el programa de un equipo (interruptor junto a las pestañas), en el equipo auditor y en las firmas de cada versión de un documento se ven los registros dados de baja, tachados, con quién y cuándo. En Equipos los **restaura** quien aprueba en Equipos; en Auditorías, mientras el plan esté abierto. Las firmas anuladas no se restauran: se vuelve a firmar.

### Cambiado
- **Equipos › Ficha Técnica › Generar PDF** imprime solo la ficha técnica (antes incluía todas las bitácoras); cada pestaña imprime la suya. La hoja de vida completa queda disponible por el sistema (`?completa=1`).
- Quien solo lee la hoja de vida también puede generar el PDF de cada bitácora.
- Dar de baja una fila de la hoja de vida explica que se conserva y se puede restaurar.

### Validado en pantalla
- Dar de baja y restaurar una fila de la hoja de vida (PRUEBA-01); Enter sobre «Cancelar» no confirma; ficha técnica en 1 página (antes 7); archivos sin sesión bloqueados; listados completos (21 usuarios, 21 hallazgos); calendario; programa de inspecciones.

---

## 0.9.3 — 2026-10-24 · Nunca se borra: baja lógica en lo que aún se eliminaba

**Migración:** sí (`esynapse_sig 0072`). Cerrar la ventana del backend → `Iniciar` → recargar (Ctrl + F5).

### Cambiado (regla 3, decisión de César 2026-10-24)
- **Documentos:** las firmas de una versión cuyo archivo se reemplaza, o cuya publicación falla, quedan **anuladas** con fecha y motivo (antes se borraban). Se puede volver a firmar.
- **Equipos:** quitar una fila de la hoja de vida, retirar una actividad del programa anual o vaciar una celda del intervalo de calibración la **da de baja**; la celda se reactiva si vuelve a llenarse (un solo registro por punto y año).
- **Auditorías:** quitar un integrante del equipo auditor lo da de baja (queda quién lo integró).
- Las pantallas y PDF muestran solo lo vigente; lo dado de baja se conserva en la base y en el log de auditoría.
- Quedan con borrado (con registro completo en el log), por ser configuración o casillas vacías: requisitos de un perfil de la matriz de EPP, permisos de un rol al reemplazar su matriz y casillas pendientes vacías de una evaluación legal en curso.

---

## 0.9.2 — 2026-10-24 · Revisión integral: seguridad, integridad de registros y fechas

**Migración:** no. Cerrar la ventana del backend → `Iniciar` → recargar (Ctrl + F5) y **volver a iniciar sesión** (cambió la clave secreta del sistema).

### Seguridad
- La clave secreta salió del código (estaba publicada en GitHub): se lee de `backend/.env` (se crea solo; no va a Git ni a la carpeta limpia). Los certificados internos de firma siguen abriéndose.
- El rol de Administrador del Sistema solo lo asigna o retira el propietario, por cualquier vía; las rutas sueltas de permisos y asignaciones quedan de consulta (sin borrado físico).
- `is_active` de un usuario no cambia por edición directa; reactivar un usuario funciona; la cuenta del propietario solo la modifica él.
- La matriz de permisos de un rol se guarda todo o nada; contraseñas débiles rechazadas (validadores de Django).
- Organización: vincular un usuario a un trabajador o desactivarlo al registrar el cese exige el permiso de editar usuarios.
- Una escritura sin operación declarada ya no se evalúa como lectura (por omisión exige editar).
- Firmas de terceros con contraseña: 5 intentos fallidos bloquean 15 minutos (antes sin límite); el bloqueo del PIN ya no se elude con intentos simultáneos.
- La IP del log y de las firmas no se toma de una cabecera que el cliente puede inventar.
- Log de auditoría ampliado a Quejas, Procesos, Cambios, Riesgos, Legal, SST y Capacitación (antes solo núcleo, SIG y Organización); el PIN nunca se registra; un error del log no tumba la operación.
- Calendario: cada bloque se muestra solo a quien puede leer ese módulo.
- **Archivos subidos solo para usuarios del sistema** (César, 2026-10-24): `/media` exige una cookie firmada que se entrega al iniciar sesión y se renueva con el token; sin sesión, o con el usuario desactivado, responde «solo para usuarios del sistema». Excepción: los logos de la pantalla de ingreso. Fotos y logos se piden por el mismo origen de la pantalla.
- SST: en el programa de inspecciones, una inspección cuenta como realizada solo cuando está firmada (César, 2026-10-24).

### Integridad de registros
- Inducción: al guardar una parte, el cliente solo marca temas, documentos y calificaciones; textos y puntos son los guardados (la nota ya no se puede inflar); enlaces validados; una inducción anulada no avanza.
- Equipos: registrar calibración directa, quitar filas de la hoja de vida y devolver un equipo al servicio requieren aprobación; los resultados de intervalo solo cambian con «guardar matriz».
- Competencia: una autorización suspendida no se reautoriza sin re-entrenamiento por ningún camino; corregir un seguimiento antiguo no vuelve a aplicar su decisión.
- Documentos: la edición directa solo cambia el código; quien elaboró no revisa ni aprueba.
- Acciones correctivas: una solicitud solo se desactiva en registro y libera su No Conformidad.
- SST: corregir un dato del mes no pisa las horas-hombre ajustadas; la fecha de reporte de un evento no se edita; quórum con titulares en funciones en la fecha (sin bajas ni cesados); un ATS validado no se anula y anular exige eliminar; reprogramar el Programa SSOMA exige aprobar; vigilancia médica muestra «Sin próximo examen» en vez de «vigente».
- Riesgos: con la aceptación firmada no cambia la valoración; mover el plazo de una acción de la matriz pide motivo y queda en el historial.
- Quejas y Cambios: un registro anulado no avanza; una queja reabierta no se anula.
- Legal: no se borran resultados ya registrados al anular una obligación; catálogo de temas sin duplicados.
- Procesos: no se registran resultados de periodos futuros (también al editar).
- Capacitación: avance «a la fecha» con la fecha vigente; no se cierra una sesión con fecha futura; acta de aprobación anterior al último cambio rechazada; año no numérico sin error.
- Auditorías: correlativo numérico (AI-100 después de AI-99).

### Fechas (hora de Lima)
- Fechas «de hoy», vencimientos y correlativos con la fecha local (antes UTC: desde las 19:00 salía el día siguiente). Firmas e historiales se guardan con hora local; los PDF y pantallas convierten también los registros antiguos.

### Pantallas
- Los listados traen todos los registros (antes se cortaban en 25 sin avisar).
- Enter sobre «Cancelar» ya no confirma acciones destructivas.
- Un error pasajero del servidor ya no cierra la sesión; doble clic ya no duplica registros.
- Intervalo de calibración: celdas vacías no se guardan como 0.
- Calendario: «siguiente mes» ya no salta meses; PDF con el motivo del error; configuración pública sin depender del token.

---

## 0.9.1 — 2026-10-23 · Capacitación: duración automática y contenido de la inducción configurable

**Migración:** sí (`capacitacion 0004`: versión e historial del contenido de la inducción; `0005`: revierte la versión 2 que creó por error la validación en pantalla al reenviar el contenido sin cambios —corregido: ya no cuenta como cambio lo que solo difiere en forma—). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Cambiado
- **Lista de asistencia:** la duración se calcula sola con «Desde» y «Hasta» (el servidor aplica la misma regla); «Hasta» anterior a «Desde» se rechaza. Sin horas, la duración se sigue indicando a mano.
- **Contenido de la inducción** (pestaña del mismo nombre) como configuración controlada:
  - lista de verificación de temas, documentos y preguntas: agregar, corregir, quitar y **reordenar**;
  - **enlaces** por tema (material) y por documento; enlace de la evaluación en línea;
  - documentos **vinculados a la lista maestra**: toman nombre, código y versión vigente, con enlace al archivo;
  - cada cambio exige **motivo**, sube la **versión** y queda en el **historial** (quién, cuándo, qué cambió);
  - las inducciones ya registradas conservan el contenido con que se hicieron.
- La inducción muestra los enlaces del material y de los documentos entregados.

### Qué probar
- Nueva lista de asistencia: Desde 10:50, Hasta 12:20 → duración 1,5 (bloqueada, «calculada»).
- Contenido de la inducción › Editar: agregar un tema con enlace, vincular un documento de la lista maestra, mover una pregunta, guardar con motivo → versión 2 e historial.

---

## 0.9.0 — 2026-10-23 · Capacitación e inducción (nuevo módulo)

**Migración:** sí (`core 0016`, `capacitacion 0001` a `0003`, `sst 0018`: módulo nuevo, programas 2026 y 2025, contenido de la inducción y secretaria actual del Comité). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5). El rol que lo use necesita el permiso del módulo «Capacitación e Inducción».

### Nuevo
- **Capacitación e inducción** (menú Soporte), según el procedimiento de gestión del personal:
  - **Programa anual de capacitación** con indicadores (avance del año y a la fecha, capacitaciones de SST frente al mínimo legal de 4), reprogramación con motivo (RP), cancelación y **aprobación del Comité de SST** (firma de los titulares con usuario o PIN, o acta en papel); si se agregan o corrigen capacitaciones queda pendiente de aprobar. PDF con el formato (grilla P/R/RP y pie del Comité).
  - **Listas de asistencia** (inducción, capacitación, entrenamiento, simulacro, charla…): asistentes que firman con su usuario o PIN (o la lista en papel), notas con certificado de aprobación (≥ 14) o participación, material y constancias, cierre firmado que marca realizada la capacitación del programa, y **evaluación de la eficacia** con alerta a los 6 meses. PDF con el formato.
  - **Inducción** en sus tres partes (organizacional, del SIG y específica del cargo) con temas, documentos y evaluación del formato; cada parte se aprueba con 14 y, si se desaprueba, se repite sola. PDF con el formato.
  - **Por trabajador:** inducción y capacitaciones que le corresponden en el año, si asistió y horas.
  - **Contenido de la inducción** editable por el Área SIG.
- Cargados: programa 2026 (36 capacitaciones, 27 realizadas —incluye el Reglamento Interno de Trabajo reprogramado y realizado el 2026-05-14—, aprobado por el Comité el 2026-05-11) y 2025 como histórico.
- SST › Inicio muestra los indicadores de capacitación y enlaza al módulo.

### Cambiado
- Comité de SST: la secretaria actual es Erika Vega Rondo.
- La firma del Comité (IPERC y programa de capacitación) usa un solo mecanismo común.

### Qué probar
- Capacitación e inducción › Programa anual 2026: indicadores, PDF y «Registrar asistencia» en una capacitación pendiente → asistentes, firmas, cierre → la capacitación queda «Realizado».
- Inducción: nueva inducción de un trabajador → completar y firmar las tres partes.

---

## 0.8.21 — 2026-10-23 · Hallazgos: el responsable se toma de donde se designa

**Migración:** no. Recargar la página (Ctrl + F5).

### Cambiado
- La columna «Responsable» de Hallazgos (y la ficha) muestra el responsable del tratamiento designado al **evaluar la solicitud de acción correctiva**; en observaciones y oportunidades de mejora, el de Riesgos y oportunidades / mejora continua. Mientras no se designe, «Por designar» (ámbar).
- El formulario «Registrar hallazgo» ya no pide responsable (se designa en un solo lugar).

### Qué probar
- Hallazgos: las NC con solicitud aún no evaluada muestran «Por designar»; las cerradas muestran a su responsable.

---

## 0.8.20 — 2026-10-23 · Interfaz: Mis tareas por urgencia, Calendario y vencimientos del Tablero

**Migración:** no. Recargar la página (Ctrl + F5).

### Cambiado
- **Mis tareas ordenada por urgencia**: grupos *Vencidas · Esta semana · Más adelante · Sin plazo*, cada tarea con su fecha y el plazo relativo («mañana», «en 7 días», «hace 3 días»), el estado con su color y el módulo como etiqueta. Si hay tareas de más de un módulo, se filtran con un clic. Se quitó el número suelto junto al título.
- **Calendario**:
  - explicación bajo el título, como el resto de módulos;
  - el día de hoy marcado con un círculo azul, fines de semana sombreados, días pasados atenuados;
  - cada pendiente con una barra del color de su módulo (acciones correctivas, auditorías, calibración, revisión de documentos, seguimiento de competencia) y leyenda completa;
  - lo vencido aparece en rojo (antes las acciones en verde claro se confundían con «cerrado»);
  - «y N más» abre la vista del día.
- **Tablero, vencimientos**: los módulos sin plazos en 90 días ya no ocupan filas de guiones; se listan en una línea al pie. Las etiquetas muestran el código y la fecha (el detalle, al pasar el mouse) en lugar de un texto cortado.

### Qué probar
- Mis tareas: que lo vencido salga primero y en rojo.
- Calendario: el día de hoy, el color de cada módulo y lo vencido en rojo; «y N más» en un día con más de tres pendientes.
- Tablero: la línea «Sin vencimientos en los próximos 90 días» y las etiquetas con código y fecha.

---

## 0.8.19 — 2026-10-23 · Interfaz: menú lateral, etiquetas de sección y contenido de las fichas

**Migración:** no. **Reiniciar el sistema** (cambió la configuración de estilos: fuente de los códigos) y recargar la página (Ctrl + F5).

### Cambiado
- **Menú lateral por área de trabajo**: General (Tablero, Mis tareas, Calendario), Sistema de gestión, Estratégico, Laboratorio, Seguridad, salud y ambiente, y Administración al final. Los títulos de grupo van en tipo normal, sin «Nivel 1 / Nivel 2».
- **Pendientes al lado de cada módulo**: tus tareas, hallazgos abiertos, solicitudes de acción correctiva abiertas y quejas abiertas. Se actualizan al cambiar de pantalla y cada 2 minutos; un módulo sin permiso no muestra conteo.
- **Módulos aún no construidos** reunidos al final en una sola línea plegable «Por construir», con la fase en que llegan (antes ocupaban la mitad del menú con candados).
- Nombres más claros: «Dashboard» pasa a **Tablero**; «Acciones correctivas», «Competencia técnica», «Riesgos y oportunidades».
- **Etiquetas de sección sin mayúsculas sostenidas** en todas las pantallas y fichas (87 etiquetas y encabezados internos): se leen en tipo normal, a 12 px, con contraste suficiente también en modo oscuro.
- **Textos diminutos de 9 y 10 px suben a 11 px** (88 lugares: notas, chips, ayudas bajo los campos).
- **Tablas dentro de las fichas** (25: plan de acción, evaluación de eficacia, acuerdos y seguimiento del Comité, EPP, vigilancia médica, inspecciones, versiones de la ficha de proceso, indicadores, matriz legal, entre otras) con un estilo compacto común y la misma regla de alineación que las tablas principales: texto a la izquierda, estados al centro, fechas y cantidades a la derecha. La lista de procesos pasa al estándar de tabla principal.
- **Códigos de registro en IBM Plex Mono**, de la misma familia que el texto (antes, la fuente monoespaciada del sistema operativo).

### Sin cambios a propósito
- Las bandas oscuras de la hoja de vida de Equipos, de la caracterización de Procesos y del programa de auditoría conservan mayúsculas: reproducen los formatos impresos.
- Matrices de conteo, mapa de calor, matriz de permisos y la tabla de intervalos de calibración siguen centradas: son cuadrículas.

### Qué probar
- Menú lateral: grupos nuevos, conteos al lado de Mis tareas, Hallazgos, Acciones correctivas y Quejas; abrir «Por construir»; contraer y expandir el menú.
- Abrir una ficha (acción correctiva cerrada, reunión del Comité, entrega de EPP): etiquetas en tipo normal y fechas alineadas a la derecha.
- Un usuario sin permiso de Quejas no debe ver Quejas ni su conteo.

---

## 0.8.18 — 2026-10-23 · Interfaz: pestañas unificadas, tablas restantes y barra de etapas en más registros

**Migración:** no. Recargar la página (Ctrl + F5).

### Cambiado
- **Un solo estilo de pestañas**: Riesgos y oportunidades, Requisitos legales y Organización y personal pasan de botones agrupados arriba a la derecha a pestañas subrayadas bajo el título, como SST, Equipos y Competencia.
- **22 tablas más con alineación por tipo de dato**: Organización y personal (áreas, puestos, trabajadores), matriz IPERC, análisis de trabajo seguro y servicios, puestos de SST, incidentes y enfermedades, inspecciones, equipos de emergencia, plantillas y monitoreos, entregas y catálogo de EPP, vigilancia médica y evaluaciones, actas y seguimiento de acuerdos del Comité, roles, log de auditoría y formatos impresos.
- **Barra de etapas común** también en Cambios y en Incidentes, accidentes y emergencias.

### Sin cambios a propósito
- Las matrices de conteo (Resumen de SST, mapa de calor de Riesgos), la matriz de permisos de Roles y las listas de verificación de inspección conservan el centrado: son cuadrículas, no listas.
- Hallazgos y Riesgos no llevan barra de etapas: su modelo no declara una secuencia de etapas; ponerla sería inventar un flujo.

### Qué probar
- Riesgos, Requisitos legales y Organización: pestañas subrayadas bajo el título.
- Abrir un cambio y un incidente: barra de etapas fija arriba.

---

## 0.8.17 — 2026-10-23 · Interfaz: los módulos pasan al estándar

**Migración:** no. Recargar la página (Ctrl + F5).

### Cambiado
- **Título estándar en todos los módulos** (sección del sistema, nombre y una explicación breve de para qué sirve, sin el ícono suelto): hallazgos, acciones correctivas, quejas, documentos, auditorías, cambios, riesgos y oportunidades, requisitos legales, competencia técnica, equipos, SST, organización y personal, usuarios, roles, configuración, log de auditoría, mis tareas y calendario. El encabezado de Procesos usa el mismo estilo.
- **Tabla principal alineada por tipo de dato** en hallazgos, quejas, documentos, cambios, riesgos y oportunidades, requisitos legales, equipos, auditorías y usuarios: texto y códigos a la izquierda, estados y clasificaciones al centro, fechas y cantidades a la derecha; encabezados sin mayúsculas sostenidas; las fechas no se parten.
- **«Abiertas / Todas»** con el control segmentado en quejas y cambios (antes, casilla).

### Corregido
- Las clases de alineación y de espaciado de cada celda no se aplicaban dentro de las tablas del estándar (la regla general pesaba más); ahora prevalecen.

### Qué probar
- Recorrer los módulos: el título con su explicación, las tablas sin desplazamiento lateral (salvo Equipos, que tiene 16 columnas) y las fechas en una línea.

---

## 0.8.16 — 2026-10-23 · Tablero del SIG

**Migración:** no. Recargar la página (Ctrl + F5).

### Nuevo
- **Tablero como panel del SIG** (reemplaza los cuatro indicadores y el gráfico de equipos):
  - **Vencimientos**: una fila por módulo (quejas, acciones correctivas, riesgos y oportunidades, calibración de equipos, revisión de documentos, seguimiento de competencia, auditorías programadas) y columnas Vencido, 7 días, 8 a 30, 31 a 60 y 61 a 90 días. Cada código lleva al módulo; si hay más de tres, «y N más».
  - **Resumen arriba**: cuántos vencidos, cuántos vencen esta semana y cuántas tareas tienes asignadas.
  - **Estado por módulo** con su norma: solicitudes por etapa, hallazgos abiertos, quejas con plazo vencido, matriz IPERC por nivel (escala única), equipos, riesgos con acciones vencidas y documentos por revisar.
  - **Tus pendientes** con su estado y su fecha de vencimiento.
- Un módulo sin permiso o sin respuesta no aparece en el Tablero.

### Qué probar
- Tablero: las quejas RQ-002 y RQ-003 aparecen como vencidas; las acciones de SAC-06-2026, en los próximos 7 días; los riesgos con acciones vencidas, con «y N más».

---

## 0.8.15 — 2026-10-23 · Interfaz: la ficha de cada registro se abre en un panel ancho con la barra de etapas fija

**Migración:** no. Recargar la página (Ctrl + F5).

### Cambiado
- **Fichas de registro en panel ancho de altura completa** (a la derecha, con la lista visible detrás): acciones correctivas, hallazgos, documentos, auditorías, cambios, competencia técnica, equipos, requisitos legales, quejas, riesgos y oportunidades, análisis de trabajo seguro, incidentes y accidentes, e inspecciones. El título queda fijo arriba; el contenido se desplaza debajo. Los formularios y confirmaciones siguen en ventana centrada.
- **Barra de etapas común** (acciones correctivas, quejas y auditorías): las etapas cerradas llevan candado (solo lectura), la actual se destaca y las futuras se ven punteadas; queda fija bajo el título al desplazarse por la ficha. En auditorías, las etapas cerradas se siguen abriendo en consulta.

### Qué probar
- Abrir una SAC, una queja y una auditoría: el panel ocupa la altura completa, la barra de etapas queda visible al bajar y la X cierra el panel.

---

## 0.8.14 — 2026-10-23 · Interfaz: tipografía IBM Plex Sans y paleta Metrindust

**Migración:** no. **Cerrar las dos ventanas del sistema y volver a `Iniciar`** (el servidor del frontend debe releer la configuración de estilos).

### Cambiado
- **Tipografía IBM Plex Sans**, instalada dentro del proyecto (no depende de internet; licencia OFL en `frontend/src/assets/fonts`). Reemplaza a Inter, que se descargaba de Google. Números de ancho fijo en todo el sistema, para que códigos, fechas y cantidades se alineen.
- **Azul Metrindust** como color principal (botones, enlaces, elemento activo) en lugar del azul eléctrico anterior.
- **Modo oscuro azul marino** en lugar de casi negro (fondo, superficies y bordes).

---

## 0.8.13 — 2026-10-23 · Interfaz: módulo estándar, tablas alineadas por tipo de dato y escala de severidad única

**Migración:** no. Solo cambia el frontend: recargar la página (Ctrl + F5).

### Nuevo
- **Módulo estándar (piloto en Acciones correctivas):** encabezado con la sección, el título, una explicación breve y las acciones; filtros en una fila con el control «Abiertas / Todas» en lugar de la casilla; tabla con la **etapa en miniatura** (cinco segmentos: etapas cerradas en gris, la actual con el color de su estado) y la descripción de la no conformidad en hasta dos líneas.
- **Alineación por tipo de dato** en las tablas del estándar: texto y códigos a la izquierda, estados y clasificación al centro, fechas a la derecha (ADR-0007, reemplaza la regla de tablas centradas). Las demás tablas conservan el centrado hasta adaptar su módulo.
- **Escala de severidad única** de cinco niveles para Riesgos y oportunidades, IPERC y análisis de trabajo seguro: el mismo nivel tiene el mismo color en todo el sistema; cada metodología conserva sus nombres. El mapa de calor de Riesgos usa la misma escala.

### Corregido
- Las etiquetas de estado y de norma del componente común no mostraban su color (la hoja de estilos no generaba esas clases). Visible, por ejemplo, en Procesos.

### Qué probar
- Acciones correctivas: encabezado nuevo, «Abiertas / Todas», etapa en miniatura y colores de estado; abrir una SAC funciona igual que antes.
- Riesgos (matriz y mapa de calor) y SST (Resumen y matriz IPERC): los niveles con la escala única.
- Procesos: las etiquetas de estado vuelven a tener color.

---

## 0.8.12 — 2026-10-23 · Interfaz: correcciones visuales detectadas en el recorrido de pantallas

**Migración:** no. Solo cambia el frontend: si el sistema está abierto, basta recargar la página (Ctrl + F5).

### Corregido
- **Ventanas de detalle y de texto ampliado**: el fondo oscuro no cubría la barra superior ni el menú lateral (la animación de la página encerraba la ventana). Ahora la ventana se dibuja sobre toda la pantalla.
- **Cambio de tema claro/oscuro**: en pantallas con tablas grandes (p. ej. SST) la página quedaba sin responder varios segundos; ahora el cambio es inmediato.
- **Etiquetas de estado y de nivel** (38 en todos los módulos): ya no se parten en dos líneas («En implementación», «En evaluación», «En cartera») y suben de 10 a 11 px para leerse mejor.
- **Quejas**: el N° de OT ya no se parte en dos líneas; el cliente y el detalle tienen anchos que permiten ver todas las columnas sin desplazamiento lateral.
- **Riesgos**: la tabla de la matriz cabe completa (la columna «Situación» quedaba cortada) y el aviso de acciones vencidas no se parte.
- **Tablero**: el gráfico de equipos por estado se dibuja sin animación, para que aparezca siempre al cargar.

### Qué probar
- Acciones correctivas → abrir una SAC → el fondo oscuro cubre toda la pantalla, incluida la barra superior.
- SST → cambiar a modo oscuro y volver: el cambio es inmediato.
- Quejas y Riesgos → todas las columnas visibles, estados en una sola línea.

---

## 0.8.11 — 2026-10-22 · SST: la matriz IPERC la aprueba el Comité · firma con usuario o PIN

**Migración:** sí (`sst 0016` y `0017`: aprobaciones de la matriz, carga de la aprobación del 15/12/2025 y retiro de filas mal cargadas). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **Aprobación de la matriz IPERC por el Comité de SST** (Matriz IPERC → «Aprobación del Comité»): se eligen las hojas (una, varias o todas), la fecha y, si se quiere, la reunión; firma cada titular presente (mínimo la mitad más uno) o se adjunta el acta firmada en papel. Reemplaza la «revisión del área» de una sola persona.
- Si una fila cambia después de aprobada, la hoja queda **pendiente de aprobación** (aviso en la matriz y en el Resumen).
- **PDF de la matriz con el pie del formato**: datos del empleador y «Realizado y aprobado por» con cada miembro, su firma y la fecha; si la hoja está pendiente, imprime a los titulares vigentes con las casillas en blanco para firmar.
- Cargada la aprobación vigente: todas las hojas, 15/12/2025, con los cuatro miembros del formato.

### Cambiado
- **Regla de firma para todo el sistema**: quien tiene usuario firma con la **contraseña de su usuario**; quien no, con su **PIN**. Aplica a la entrega de EPP, al cargo de resultados médicos y a la aprobación del IPERC.

### Corregido
- La carga inicial de la matriz había tomado como filas el pie de cada hoja (razón social, RUC, domicilio): 32 filas retiradas con su motivo. La matriz vigente tiene 353 filas.
- Firma de varias personas: se validan todas las credenciales antes de guardar nada (un PIN nuevo no queda creado si otra firma falla).
- Competencia técnica: después de las 19:00 no se podía reautorizar una autorización suspendida ese mismo día (la fecha de la suspensión se tomaba en hora UTC).

### Qué probar
- Planificación → Matriz IPERC → ver el estado «Aprobada» → editar una fila de un área → queda «Pendiente de aprobación» → «Aprobación del Comité» → firmar → vuelve a «Aprobada»; imprimir el PDF del área y ver el pie.

---

## 0.8.10 — 2026-10-22 · SST: «Tipo de lista» en las plantillas de inspección

**Migración:** no. Recargar la página (Ctrl + F5).

### Cambiado
- En las plantillas de inspección, el campo «Familia» se llama ahora **«Tipo de lista»**, con opciones en lenguaje del procedimiento — Lista de equipos · Contenido de un equipo · Lista de preguntas · Lista de trabajadores — y una línea que explica la opción elegida.

### Qué probar
- SST → Operación → Inspecciones → Plantillas: ver la columna «Tipo de lista» y abrir una plantilla.

---

## 0.8.9 — 2026-10-22 · SST: navegación ordenada por grupos

**Migración:** no. Solo pantalla: recargar la página (Ctrl + F5).

### Cambiado
- La barra de 13 pestañas de SST se reemplaza por una navegación en tres niveles, cada uno con su estilo:
  - **Grupos** (una fila subrayada, sin saltos de línea): Inicio · Planificación · Operación · Salud ocupacional · Eventos · Participación.
  - **Secciones** del grupo (píldoras): p. ej. Salud ocupacional → Vigilancia médica · Monitoreos · Enfermedades.
  - **Vistas** internas (control segmentado): p. ej. Vigilancia médica → Por trabajador · Evaluaciones médicas.
- SST abre en **Inicio (Resumen)**. «ATS tipo» pasa a ser una vista dentro de ATS. La nota de vigilancia médica queda separada de los botones.
- Componente común de navegación, listo para aplicarlo a otros módulos.

### Qué probar
- Recorrer los seis grupos y sus secciones; en Operación → ATS, cambiar entre «ATS» y «ATS tipo».

---

## 0.8.8 — 2026-10-22 · SST: Comité de SST, Programa anual SSOMA y cargo de resultados médicos

**Migración:** sí (`sst 0014` y `0015`: tablas nuevas, comité 2025-2027 y programa SSOMA 2026). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **Comité de SST** (pestaña nueva en SST): el comité del periodo con sus fechas, el registro en el T-Registro y las actas de elección e instalación adjuntas; **miembros** elegidos entre los trabajadores (empleador / trabajadores, titular / suplente, presidente y secretario) y bajas con motivo; alertas (no paritario, falta presidente o secretario, sin T-Registro, mandato por vencer, sin reunión del mes, acuerdos vencidos).
  - **Reuniones**: se programan con asistentes (quórum en vivo), agenda, desarrollo y acuerdos; el sistema imprime el **acta** para firmar y la reunión se cierra adjuntando el acta firmada (exige agenda y quórum). Cerrada no cambia.
  - **Seguimiento de acuerdos**: estado y comentario de avance; vencidos en rojo.
  - Cargado el comité 2025-2027 (instalado el 30 de mayo de 2025); sus miembros se registran cuando estén en Organización y personal.
- **Programa anual SSOMA** (pestaña nueva): objetivos y actividades con responsable, meses programados y ejecutados (clic en el mes, con evidencia), avance por actividad y por objetivo, aprobación con firma, **reprogramación** con motivo (nueva versión) y PDF con el formato. Cargado el programa 2026 del Excel.
- **Vigilancia médica**: **cargo de entrega de resultados** — el trabajador firma la recepción de su resultado con su PIN (el de los EPP) o se adjunta el cargo en papel; y **Anexo 4** — aviso del informe anual del año anterior (plazo 31 de marzo) y registro de su presentación (se corrige con «reemplazar» y motivo; queda la constancia).

### Qué probar
- Comité de SST → Agregar miembro (un trabajador como presidente del empleador, otro como secretario de los trabajadores) → ver cómo cambian las alertas.
- Reuniones → Nueva reunión → asistentes, agenda, un acuerdo → «Acta para imprimir» → adjuntar un PDF y «Cerrar con el acta firmada» → Seguimiento de acuerdos.
- Programa SSOMA 2026 → clic en un mes programado ya pasado → evidencia → ver el avance; PDF.
- Vigilancia médica → abrir una evaluación registrada → «Registrar entrega» → PIN del trabajador y su contraseña. Por trabajador → registrar el Anexo 4.

---

## 0.8.7 — 2026-10-22 · SST: EPP (entrega firmada con PIN) y vigilancia médica

**Migración:** sí (`sst 0012` y `0013`: tablas nuevas, catálogo de EPP y matriz por puesto). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **EPP** (pestaña nueva en SST), según el procedimiento de gestión de EPP:
  - **Catálogo** de 29 EPP (los del formato de entrega, con las marcas de la matriz) con tipo de protección, clasificación, certificación y **vida útil** (por definir: calcula la fecha de renovación).
  - **Matriz por puesto** cargada (administrativos, logística, metrología por laboratorio y servicio en campo), enlazada a los puestos de Organización y personal; editable y en PDF.
  - **Entrega**: dotación, reposición (con motivo; reemplaza el EPP anterior), cambio de puesto o campo; botón para traer lo que falta o toca renovar según la matriz. La firma el **responsable con su contraseña** y el **trabajador con su PIN** (lo crea en su primera entrega; se guarda cifrado; al quinto error se bloquea y SIG lo restablece). Si no puede firmar en pantalla, se adjunta el **cargo en papel**.
  - **Por trabajador**: lo que exige la matriz frente a lo entregado (falta, vigente, por renovar, vencido), estado del PIN y registro de entregas en PDF (dos entregas por hoja, como el formato).
  - **Devolución** por cese, rotación o cambio de puesto; alerta de cesados con EPP sin devolver.
- **Vigilancia médica** (pestaña nueva): evaluaciones médicas ocupacionales con la **aptitud** de cada trabajador (apto, con restricciones, no apto, observado), restricciones o recomendaciones **sin diagnóstico**, próximo examen (anual operativo, cada dos años administrativo) y certificado de aptitud adjunto; medidas correctivas; firma y PDF. Vista por trabajador con examen vencido, por vencer o faltante.

### Qué probar
- EPP → Entregas → Nueva entrega para un trabajador → «Traer los que faltan» → Firmar: el trabajador crea su PIN (dos veces) y usted pone su contraseña → ver el PDF.
- Segunda entrega (reposición, motivo «Daño»): firma con el PIN; un PIN errado avisa los intentos que quedan.
- Por trabajador: ver la situación frente a la matriz.
- Vigilancia médica → Nueva evaluación con dos trabajadores → aptitud y restricciones → firmar → ver «Por trabajador» y el PDF.

---

## 0.8.6 — 2026-10-22 · SST: inspecciones y monitoreos de agentes ocupacionales

**Migración:** sí (`sst 0010` y `0011`: tablas nuevas y carga de las plantillas y de los monitoreos 2025-2026). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **Inspecciones** (pestaña nueva en SST), según el procedimiento de seguimiento y medición:
  - **Plantillas**: los 11 formatos cargados (botiquines, extintores, luces de emergencia, SSTMA, detectores de humo, EPP, kit antiderrame, escaleras, movilidad, moto lineal, herramientas portátiles), con su escala, criterios o preguntas, frecuencia y caja de control. El SIG puede crear o cambiar plantillas sin programar; cada inspección guarda la estructura con la que se hizo.
  - **Elementos de seguridad**: inventario de extintores, luces, detectores, escaleras, botiquines, kits, vehículos y motos, con sus vencimientos (recarga, prueba hidrostática, SOAT, revisión técnica, productos del botiquín) y aviso 30 días antes. Se dan de baja con motivo.
  - **Inspección**: trae sus filas (los elementos del inventario, el contenido del botiquín o kit, las preguntas o los trabajadores del área); botón para completar lo vacío como conforme; cada «no conforme» exige acción inmediata, responsable y plazo antes de firmar. Firmada queda de solo lectura y se cierra al completar sus acciones. Desde un ítem relevante se registra el **hallazgo** con su solicitud de acción correctiva.
  - **Programa**: cada plantilla por mes según su frecuencia — realizada, en plazo, programada o atrasada — y alertas en la cabecera.
  - PDF de cada inspección con la cabecera y la tabla de su formato.
- **Monitoreos** (pestaña nueva en SST): **programa anual** por agente (programado / ejecutado, reprogramaciones en el historial), **registro** de cada monitoreo con resultados frente al límite máximo permisible, causas, conclusiones e informe adjunto (firmado), y **seguimiento de recomendaciones**. Cargados del Excel: programas 2025 y 2026, monitoreo MON-001-2025 y sus 20 recomendaciones. Los tres PDF.

- El programa no alerta como atrasados los meses anteriores a la carga de cada plantilla (esas inspecciones se llevaron en papel).
- Antes de pedir la contraseña, la pantalla avisa si faltan respuestas o acciones de los «no conforme»; guardar los datos del registro ya no borra las respuestas aún sin guardar.

### Qué probar
- Registrar dos extintores en «Elementos de seguridad» (uno con vencimiento pasado: ver la alerta).
- Nueva inspección de extintores → «Completar lo vacío como conforme» → marcar un NC → intentar firmar (pide la acción) → registrar acción, responsable y plazo → firmar → completar la acción → cerrada. Ver el PDF.
- Inspección SSTMA (preguntas) y de EPP (por trabajador) con su PDF.
- Monitoreos: ver el programa 2025 (diciembre ejecutado), el registro MON-001-2025 y el seguimiento de recomendaciones con sus PDF.

---

## 0.8.5 — 2026-10-22 · Saneamiento: modo pruebas y orden del taller

**Migración:** no. Para usar el modo pruebas: doble clic en `Iniciar modo pruebas.bat` (puede correr junto al sistema normal).

### Nuevo
- **Modo pruebas**: `Iniciar modo pruebas.bat` levanta el sistema sobre una **copia** de la base y de los archivos subidos, en `http://localhost:5174` (backend en el puerto 8001). Al iniciar pregunta si se renueva la copia desde la base real (por defecto no). Arriba de cada pantalla y en el ingreso se ve el aviso **«MODO PRUEBAS · copia de la base»**. Lo que se registra ahí no toca los datos ni los correlativos reales. La sesión es independiente de la del sistema normal.

### Seguridad
- Se retiró la contraseña del administrador que había quedado escrita por error en el resumen de cambios de una versión de un procedimiento y en su entrada del log (queda «prueba» y una entrada del log con el motivo). Falta cambiar esa contraseña.

### Validado
- **Cambios** y **Quejas** recorridos completos con los criterios de sus fichas (SC-006-2026 y RQ-004-2026): todas las reglas rechazan lo que deben y el flujo llega al cierre, la reapertura y el nuevo cierre.

### Corregido
- Cambios y Quejas: al intentar llenar un dato de una etapa que todavía no empieza, el mensaje decía que la etapa «está cerrada»; ahora dice que «aún no se abre».
- Registro de cambios: a las entregas 0.5.0 y 0.5.1 les faltaba el número de versión en el título.

### Orden
- Residuos del taller movidos a `_archivo/` (no se borraron): scripts de diagnóstico, base corrupta de junio, log de firma y carpetas de respaldo antiguas. Fuera de Git y de la carpeta limpia.
- Backlog al día: sección «Ahora», estado de la regla de etapa cerrada por módulo, plan de SST (inspecciones y monitoreos pasan a 0.8.6).

### Qué probar
- Abrir `Iniciar modo pruebas.bat`: ver el aviso en el ingreso y en la cabecera; registrar algo y comprobar que no aparece en el sistema normal (`localhost:5173`).

---

## 0.8.4 — 2026-10-22 · SST: incidentes, accidentes, enfermedades ocupacionales y estadísticas

**Migración:** sí (`core 0015`, `esynapse_sig 0071`, `sst 0008` y `0009`). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **Incidentes y accidentes** (pestaña nueva en SST), según el procedimiento de investigación de accidentes e incidentes: accidente de trabajo (AT), incidente peligroso (IP), incidente (IN) y emergencia (EM).
  - **Reporte**: fecha y hora, lugar, área y proceso, en campo o no, hechos, acciones inmediatas, primeros auxilios, testigos. Se marca si se reportó después de las 24 horas.
  - **Personas afectadas** (trabajador de Organización y personal o externo) con los datos del registro oficial: edad, sexo, antigüedad, turno, contrato, experiencia, horas trabajadas, SCTR, parte del cuerpo, tipo de lesión y días de descanso médico (actualizables hasta el cierre, con historial).
  - **Investigación**: equipo investigador (lo conforma el Comité SST; no incluye al involucrado ni a testigos), gravedad y grado de incapacidad, tipo de accidente, actos y condiciones subestándar, factores de trabajo y personales, qué sucedió y porqués, causas inmediatas y básicas, conclusiones, filas IPERC y si requiere actualizar la matriz.
  - **Concluir con firma** (elaborado) → **revisar con firma** (revisado): registra el **hallazgo** (fuente «Incidente / accidente de trabajo»; NC mayor si es incapacitante, mortal o incidente peligroso) y su **solicitud de acción correctiva**; las acciones y su eficacia se siguen en Acciones correctivas. El evento **se cierra** solo con la solicitud cerrada.
  - **Notificación al Ministerio de Trabajo** (accidente mortal o incidente peligroso) con fecha y constancia; alerta mientras falte.
  - Evidencias (fotos, croquis, declaraciones). Cada etapa cerrada queda de solo lectura.
- **Enfermedades ocupacionales** (sin datos personales de salud): enfermedad, área, afectados, expuestos, agente, causas; al firmarse registran hallazgo y solicitud de acción correctiva.
- **Estadísticas**: tabla mensual con trabajadores, horas-hombre (propuestas desde Organización y personal y editables), accidentes por gravedad y área, días perdidos, **índices de frecuencia, gravedad y accidentabilidad (R.M. 050-2013-TR)**, incidentes, enfermedades y descansos médicos; análisis del periodo firmado.
- PDF: **Registro de accidentes de trabajo**, **Registro de accidentes e incidentes peligrosos**, **Informe de investigación de accidentes y emergencias**, **Registro de enfermedades ocupacionales**, **Registro de estadísticas de SST** y **Datos para el registro de estadísticas**.
- **Configuración**: datos del empleador para los registros oficiales (razón social, RUC, actividad económica, aseguradora del SCTR); se cargaron los de Metrindust.

### Qué probar
- Reportar un accidente con una persona afectada, iniciar la investigación, completar el análisis, concluir y revisar con firma (ver el hallazgo y la solicitud en Acciones correctivas); imprimir el registro y el informe.
- Reportar un incidente peligroso y registrar la notificación al Ministerio.
- Revisar las estadísticas del año, ajustar las horas-hombre de un mes e imprimir los dos formatos.
- Revisar los datos del empleador en Configuración.

---

## 0.8.3 — 2026-10-22 · SST alineado con Organización y personal

**Migración:** sí (`sst 0006` y `0007`). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Cambiado
- **ATS: personal ejecutante** desde Trabajadores (se guarda con su puesto); el nombre escrito solo para personal externo, marcado como «externo». Un trabajador cesado o repetido no se acepta. Los ATS ya registrados quedan con sus nombres como externos.
- **IPERC: responsables de los controles** son puestos del catálogo (antes, texto). La carga los enlazó desde el texto de la matriz: «Alta Dirección» → Gerente General, «Gerente SIG», «Jefe de Logística» → Coordinador Logístico, «Encargado de laboratorio»; se crearon para revisar «Supervisor de SSOMA», «Encargado de Recursos Humanos» y «Encargado de Compras», que la matriz nombra y no estaban en el catálogo. El texto original se conserva y se limpió la referencia de celda que arrastraba el Excel («+A12:Z35»). El PDF imprime los puestos.
- **IPERC: filtro por área del organigrama.**
- **Organización y personal → trabajador: «Riesgos a los que está expuesto»** según la matriz IPERC (filas de su puesto en su área, de todos los puestos de su área y de los lugares comunes), con el nivel residual y el EPP. Visible para quien tiene acceso a SST.

### Qué probar
- Preparar un ATS eligiendo ejecutantes de Trabajadores y uno externo escrito a mano.
- En una fila IPERC, ver y cambiar los responsables; filtrar la matriz por área del organigrama.
- Abrir un trabajador en Organización y personal y revisar sus riesgos.

---

## 0.8.2 — 2026-10-22 · Organización y personal (núcleo)

**Migración:** sí (app nueva `organizacion` `0001`–`0003`; `core 0014`; `sst 0005`; `esynapse_sig 0070`). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **Organización y personal** (menú Administración): una sola fuente para todo el sistema (decisión de arquitectura ADR-0006).
  - **Áreas**: organigrama con gerencias, áreas y laboratorios; cada una con su proceso principal, sede, piso y puesto responsable.
  - **Puestos**: sigla de firma, área, a quién reporta, propio o tercero, y el **perfil del puesto** (educación, formación, experiencia, habilidades, funciones), versionado.
  - **Trabajadores**: puesto, área, ingreso, cese con motivo (desactiva su usuario del sistema) y reingreso; usuario del sistema opcional.
  - Historial de cambios en cada registro; nada se elimina (áreas y puestos se desactivan solo sin dependientes activos).
  - Consulta para todos los usuarios; cambios con el nuevo permiso «Organización y personal». El documento de identidad solo lo ve quien gestiona la organización.
- **Carga inicial (propuesta para revisar)**: organigrama de 22 áreas (6 gerencias, 4 áreas y 12 laboratorios con su piso) y 29 puestos con línea de reporte; siglas GG, GSIG, ASIG y GT.

### Cambiado
- **Usuarios**: se vinculan a su trabajador y toman de su puesto el cargo, la sigla de firma y el área (y el laboratorio, si su área lo es). Si cambia el puesto o su sigla, la firma cambia sola. Las cuentas sin trabajador (externas o de sistema) mantienen sus datos escritos.
- **Configuración**: la lista de áreas y laboratorios pasó a Organización y personal.
- **Competencia técnica**: los perfiles por puesto se consultan del puesto (se mantienen en Organización y personal); el laboratorio del alcance de firma se elige de la lista de laboratorios.
- **SST**: los puestos son los del catálogo único; la pestaña «Puestos» muestra cuántas filas IPERC tiene cada uno. Cada fila IPERC tiene además el **área del organigrama** (se completó sola en 299 filas; las hojas «Gerencias», «Comedor», «Terceros» y la de Análisis Químico y Gases quedan para asignar).

### Corregido en la validación
- «Mantenimiento» figuraba como laboratorio (venía así de la lista anterior): vuelve a ser un área (`organizacion 0003`).
- Usuario de un laboratorio: su área es la unidad de la que depende el laboratorio (p. ej. Gerencia Técnica) y su laboratorio, el laboratorio; antes repetía el laboratorio en ambos.

### Qué probar
- Revisar y corregir el organigrama y los puestos propuestos (nombres, a quién reporta, siglas que faltan).
- Registrar un trabajador, vincularlo a un usuario y comprobar que el usuario toma cargo, sigla y área; cambiarlo de puesto.
- Registrar el cese de un trabajador de prueba con usuario (el usuario queda desactivado).
- Cargar el perfil de un puesto y verlo en Competencia técnica → Perfiles por puesto.

---

## 0.8.1 — 2026-10-22 · SST: ATS en campo

**Migración:** sí (`sst 0003` y `0004`). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **ATS en campo**: al preparar un ATS se indica dónde se realiza (instalaciones de Metrindust o en campo), el cliente y el formato que se usará (el de Metrindust o el del cliente).
  - **Envío a campo**: la preparación queda cerrada y, en el formato de Metrindust, se imprime prellenado para llenarlo y firmarlo en el lugar.
  - **Recepción**: al volver se transcribe lo que cambió (personal, equipos, horario, firmantes del cliente, etapas) y se adjunta el ATS firmado (foto o escaneo), con la fecha de ejecución y las observaciones de campo.
  - **Revisión de SST con firma**; puede devolverlo con observación. En el formato de Metrindust exige las etapas transcritas y, si quedó un riesgo intolerable, una observación.
  - El ATS en las instalaciones de Metrindust sigue con la validación previa con firma.
- **ATS tipo** (pestaña nueva): el ATS base de cada servicio (etapas, peligros, medidas y evaluación típicas, tipo de trabajo, proceso y filas IPERC). Al preparar un ATS se elige y se copia; también se puede guardar un ATS como tipo.
- **Resumen**: ATS por estado, trabajos en campo sin ATS recibido (con los días transcurridos) y ATS por revisar.
- Historial de cada ATS (preparación, envío, recepción, devoluciones, revisión, anulación).

### Cambiado
- En SST el campo «Proceso» muestra solo los procesos principales (las áreas del mapa). Las 29 filas IPERC y los 4 puestos de Logística que apuntaban a «Recepción de Equipos y/o Instrumentos» pasan a Metrología.
- Las listas de sugerencias (área y peligro del IPERC; tema y periodicidad en Requisitos legales; auditor y auditado del cronograma de Auditorías) usan una lista propia con los colores del sistema, en lugar de la del navegador, que se veía distinta.

### Qué probar
- Preparar un ATS en campo desde un ATS tipo, enviarlo a campo (se imprime), registrar la recepción con una foto y revisarlo con firma.
- Un ATS en campo con el formato del cliente: recepción con el archivo y revisión.
- Crear un ATS tipo y guardar un ATS como tipo.
- En una fila IPERC, abrir los desplegables de área y peligro.

---

## 0.8.0 — 2026-10-22 · Nuevo módulo: Seguridad y Salud en el Trabajo (M23), primera entrega

**Migración:** sí (app nueva `sst`: `0001` y `0002` con la carga inicial). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **SST** habilitado en el menú (Nivel 2 — SST y Medio Ambiente), según el procedimiento de identificación de peligros, evaluación de riesgos y controles:
  - **Catálogo de puestos de trabajo** (personal propio y terceros), enlazado al proceso; lo usarán EPP, vigilancia médica y capacitación.
  - **Matriz IPERC** por área: puestos expuestos, actividad, peligro (con la tabla de peligros y riesgos del anexo), riesgo, consecuencia, situación, controles existentes, evaluación (A+B+C+D) × severidad con el nivel y la aceptabilidad calculados, controles por jerarquía con responsable y evaluación residual. Situación de control: sin evaluar, controlado, **requiere control**, **trabajo detenido**. Historial de cambios por fila; retiro con motivo; revisión del área con firma (fecha de actualización del formato).
  - **Análisis de Trabajo Seguro (ATS-000-AAAA)**: datos del formato, tipo de trabajo, personal ejecutante, equipos, filas IPERC relacionadas y etapas con S×P antes y después de las medidas. **Validación con firma** del supervisor o prevencionista; no se valida con riesgo intolerable. Validado o anulado = solo lectura.
  - **Resumen** por área (niveles inicial y residual, situación de control, última revisión).
  - PDF de la **Matriz IPERC** (A3, una hoja por área, con los colores de nivel) y del **ATS**, con su caja de control.
- **Carga inicial**: 385 filas de las 16 hojas de la matriz en Excel, 29 puestos y la tabla de peligros (55). En 26 filas el índice de probabilidad estaba escrito a mano y el nivel salía menor: se cargaron recalculadas con la observación en su historial.
- Formatos diseñados para las entregas siguientes (en `PROCEDIMIENTOS SIG/Formatos SST (propuesta)/`): registro de enfermedades ocupacionales, registro de exámenes médicos ocupacionales y registro de inducción, capacitación, entrenamiento y simulacros.

### Corregido en la validación
- Historial de la fila IPERC: ya no registra «Puestos expuestos» como cambio cuando los puestos no cambiaron; la hora queda en la hora de Lima.
- ATS: al quitar una etapa, las demás se renumeran.
- PDF del ATS: la fecha y hora de la firma del supervisor salen en hora de Lima.
- Resumen: la columna «Última revisión» ya no se parte en varias líneas.
- SST: un error dentro de una ventana (p. ej., contraseña incorrecta al validar un ATS) se desplaza a la vista; antes quedaba arriba, fuera de la pantalla.

### Qué probar
- Matriz IPERC: filtrar por área y por puesto; abrir una fila Importante y ver su residual; imprimir el PDF de un área.
- Crear una fila con nivel Importante: queda «requiere control»; registrar controles y residual aceptable → «controlado». Retirarla con motivo.
- Revisión del área con firma.
- Crear un ATS con dos etapas, validarlo con firma e imprimirlo; intentar validarlo con una etapa intolerable (debe rechazarlo).

---

## 0.7.0 — 2026-10-21 · Nuevo módulo: Requisitos legales (M2)

**Migración:** sí (app nueva `legal`: `0001` y `0002` con la carga inicial). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **Requisitos legales** en el menú (Nivel 1 — Estratégicos), según el procedimiento de identificación, acceso y evaluación de requisitos legales y otros requisitos:
  - **Lista de requisitos** por ámbito — Seguridad y Salud en el Trabajo, Medio Ambiente, Obligaciones Sociolaborales, Otros requisitos y el nuevo **Acreditación** (requisitos de INACAL) —, agrupada por tema: tipo, código, nombre, fecha, modificatorias, observaciones, procesos involucrados y aplicabilidad.
  - **Cambio normativo**: registrar una modificatoria, **derogar** (sus obligaciones salen de las evaluaciones siguientes), **comunicar** a las áreas y abrir una **solicitud de cambio** (origen externo: requisitos legales).
  - **Obligaciones** (artículos a cumplir): documento o registro que evidencia, documento legal asociado, artículo, extracto, proceso/sede, responsable y periodicidad; baja con motivo.
  - **Evaluación semestral** por ámbito: carga las obligaciones vigentes como pendientes; cumple / no cumple / no aplica con evidencia; **cierre con firma**; cada incumplimiento se registra como **hallazgo** para su acción correctiva. Cerrada = solo lectura.
  - **Indicadores**: % de cumplimiento por ámbito y global (escala Bueno > 80 %, Regular 70–80 %, Malo < 70 %), tendencia, evaluación vencida.
  - PDF de la **Lista de requisitos legales** y de la **Matriz de evaluación de cumplimiento legal** (una columna por evaluación del año y resumen por tema), con su caja de control (versión 01 · 2026-01-02 · ASIG / GSIG / GG).
- **Carga inicial**: 299 normas, 447 obligaciones (230 enlazadas a su norma de la lista) y las evaluaciones de 2025 del Excel como cerradas (cuatrimestres de SST y otros requisitos; anual de Medio Ambiente).

### Corregido en la validación
- **Búsqueda en todas las listas** (Requisitos legales, Riesgos, Cambios, Hallazgos, Acciones correctivas, Auditorías, Documentos, Equipos, Quejas, Usuarios): al escribir rápido, una respuesta vieja podía pisar a la nueva y la lista mostraba resultados de una búsqueda anterior. Ahora solo se muestra la respuesta de la última búsqueda.
- Matriz de evaluación: las columnas de % de cumplimiento siguen el número del periodo (Semestre 1 antes que Semestre 2), aunque se hayan abierto en otro orden.
- Lista de requisitos: botón «Anular» para una norma registrada por error y sin obligaciones.

### Qué probar
- Revisar la lista de cada ámbito y abrir sus PDF.
- Crear una norma de Acreditación con una obligación; abrir la evaluación semestral, evaluarla y cerrarla con su firma (un «no cumple» crea un hallazgo).
- Registrar una modificatoria, comunicar y abrir una solicitud de cambio desde una norma.

## 0.6.0 — 2026-10-21 · Nuevo módulo: Riesgos y oportunidades (M3)

**Migración:** sí (app nueva `riesgos`: `0001` y `0002` con la carga inicial; `procesos 0005`). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **Riesgos** en el menú (Nivel 1 — Estratégicos), según el procedimiento de gestión de riesgos y oportunidades:
  - **Matriz de riesgos y oportunidades** (R-000 / O-000): proceso del catálogo, contexto que lo origina, categoría (13), fuente, causa → descripción → efecto, controles existentes y valoración P×I (riesgos) o V×B (oportunidades) con el nivel y «¿requiere acción?» calculados como en el formato.
  - **Tratamiento** con estrategia y **varias acciones** por registro (responsable, fechas, recursos, implementación documental, estado y evidencia). Aceptar un riesgo Importante o Crítico lo firma el Gerente General; las oportunidades en cartera las decide la Alta Dirección.
  - **Eficacia** por valoración residual: solo con las acciones ejecutadas y tres meses después de la ejecución; eficaz / sin cambio / no eficaz; si no fue eficaz, nuevo tratamiento (el ciclo anterior queda en el historial).
  - **Revaloración** con motivo (revisión anual o evento), **materialización** de un riesgo y **acción fuera de plazo** registradas como hallazgo, **retiro** con motivo.
  - **Matriz de oportunidades de mejora** (OM-000): fuente, detectado por, decisión con justificación, acción, seguimiento y eficacia (lograda, parcial, no lograda). Alerta si sigue en evaluación más de un año.
  - Las observaciones y oportunidades de mejora **derivadas desde Hallazgos** aparecen para registrarlas aquí.
  - **Contexto** (FODA y partes interesadas), **actualización** de la matriz y **supervisión** del Gerente Técnico con firma (control independiente).
  - **Indicadores** de ambas matrices, mapa de calor y alertas. PDF de las dos matrices en A3 horizontal.
- **Carga inicial**: 151 riesgos y oportunidades, 28 oportunidades de mejora y 59 elementos de contexto de los Excel vigentes.
- **Catálogo de procesos**: nuevo subproceso «Recepción de Equipos y/o Instrumentos» (de Metrología) y nuevo proceso de soporte «Marketing».

### Corregido en la validación
- Firmada la aceptación de un riesgo por el Gerente General, la estrategia y su decisión ya no se pueden editar; para cambiarlas se revalora el riesgo, lo que anula la firma (queda en el historial) y exige firmar de nuevo.
- PDF de la matriz: las casillas de nivel, ¿requiere acción?, estrategia y eficacia se ensanchan para que sus palabras no se partan.
- Mapa de calor: cada casillero muestra su valor (impacto × probabilidad) como la matriz de valoración del procedimiento; una marca indica cuántos registros caen en él y, al hacer clic, se listan sus códigos.
- Las listas de oportunidades de mejora y de contexto ya no se cortan en 25 registros; registrar desde un hallazgo toma su fuente real.

### Qué probar
- Registrar un riesgo, valorarlo, agregar una acción y «Registrar en la matriz»; marcar la acción ejecutada (con archivo) y ver que la verificación espera tres meses.
- Firmar la aceptación de un riesgo Importante (Gerente General) y la supervisión de la matriz.
- Registrar una oportunidad de mejora desde un hallazgo derivado; decidir, ejecutar y evaluar su eficacia.
- Indicadores y los dos PDF.

## 0.5.1 — 2026-10-21 · Cambios: el cambio temporal queda «en vigor» hasta registrar su fin

**Migración:** sí (`cambios 0003`). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Cambiado
- **Cambio temporal** (decisión de César): al confirmar la eficacia ya no se exige haberlo revertido. Pasa al nuevo estado **«Temporal en vigor»** (la verificación queda de solo lectura) y se cierra al **registrar su fin**: fecha real, qué se restituyó y evidencia.
- **Prórroga** del fin previsto: la firma el Gerente General con su contraseña, con motivo; queda el historial (fecha anterior y nueva).
- **Volverlo permanente**: desde un cambio en vigor se abre una nueva solicitud que lo referencia, con su propia evaluación y aprobación.
- La **reversión** de la verificación queda solo para un cambio **no eficaz**; el fin previsto de un temporal se registra aparte. La migración corrige los cambios temporales ya cerrados con «reversión» (SC-001-2026).
- **Cambio menor**: pasa a implementación solo con el plan de ejecución; el responsable y el plazo de implementación se toman de sus actividades si no se registran.
- Alerta **«fin vencido»** cuando pasa la fecha prevista sin registrar el fin. El PDF de Planificación muestra el fin previsto, la prórroga y el fin registrado.

### Corregido
- En la ficha del cambio, el aviso de error se lleva a la vista: antes quedaba arriba, fuera de la pantalla, y parecía que el botón (p. ej. «Firmar prórroga») no hacía nada.

### Qué probar
- Un cambio temporal: confirmar la eficacia → «Temporal en vigor» → prorrogar (firma del Gerente General) → registrar el fin → cerrado.

## 0.5.0 — 2026-10-21 · Nuevo módulo: Cambios (M17)

**Migración:** sí (app nueva `cambios`: `0001` y `0002` con el registro de sus tres formatos impresos; `procesos 0004`). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Nuevo
- **Cambios** en el menú del SIG Core, según el procedimiento de Control de Cambios:
  - **Solicitud**: proceso solicitante del catálogo, prioridad, origen interno o externo con su motivo, descripción y justificación. Número SC-NNN-AAAA.
  - **Evaluación** (Área SIG): factibilidad técnica, operativa y financiera; procesos afectados; impactos (calidad, ambiente, SST, técnico, imparcialidad, acreditación, legal); beneficios, riesgos, controles y consecuencias; **clasificación mayor o menor**, si es técnico y si afecta a clientes o actividades acreditadas; equipo evaluador y plan de ejecución.
  - **Aprobación**: la resuelve el **Gerente General**, con su contraseña. El rechazo exige motivo y puede reevaluarse o archivarse. Al aprobar, cada proceso afectado recibe el aviso «ficha por revisar».
  - **Planificación**: obligatoria para cambios mayores o técnicos (previsto/no previsto, temporal/permanente con fecha de reversión, fuentes, responsable, plazo y equipo); para un cambio menor basta el plan de ejecución.
  - **Implementación**: actividades completadas con seguimiento y evidencia, documentos actualizados de la lista maestra, comunicación (a clientes primero, si los afecta) y registro fotográfico antes/después.
  - **Eficacia y cierre**: se implementó, fue eficaz, criterios verificados, reversión, acción correctiva derivada. No cierra con documentos sin aprobar ni acciones derivadas abiertas. Alerta de reversión vencida en cambios temporales.
  - PDF de la **Solicitud**, la **Planificación** y el **Seguimiento de Cambios**.

### Qué probar
- Registrar una solicitud, evaluarla con una actividad y enviarla a aprobación; aprobarla con la contraseña del Gerente General y ver el aviso en Procesos.
- Planificar, iniciar la implementación, completar la actividad, registrar la comunicación y cerrar con la eficacia.
- Abrir los tres PDF.

## 0.4.1 — 2026-10-21 · La sesión ya no se cae al cargar varias cosas a la vez · versión de formatos en Procesos · **M7 cerrado**

**M7 Procesos cerrado** por César en esta versión. Acta de validación: `docs/validacion/M07_acta_2026-10-21.md` (por firmar).

**Migración:** sí (`procesos 0003`). Cerrar la ventana del backend → `Iniciar` → recargar la página (Ctrl + F5).

### Corregido
- **«No se pudo generar el documento (HTTP 401)»** al pedir un PDF: la sesión se había invalidado. Cuando el acceso vencía y la pantalla hacía varias consultas juntas (la ficha de un proceso carga cinco), cada una intentaba renovar la sesión con el mismo permiso; como el permiso se renueva una sola vez, las demás fallaban y cerraban la sesión. Ahora las consultas esperan una única renovación, y si otra pestaña ya la renovó se usa esa.
- Si la sesión realmente expira, el sistema lo dice («Tu sesión expiró. Vuelve a ingresar.») y lleva al ingreso, en lugar de mostrar un error técnico.

### Cambiado
- **PDF de la ficha de caracterización y del mapa de procesos**: la caja de control muestra la versión y la fecha del formato (ficha: 01 · 2025-02-22; mapa: 00 · 2025-01-10), no la versión de cada ficha. Cuando el formato se vincule a su documento en la lista maestra, se tomarán de allí. Firmas: ASIG · GSIG · GG.
- **Las fichas cargadas empiezan en la versión 01** (antes 02), para no confundirse con la versión del formato. Como es la primera versión, no lleva «motivo de la versión». El PDF de la ficha ya no imprime la nota «Ficha en elaboración: no es copia controlada». **Migración:** sí (`procesos 0003`, solo renumera).

## 0.4.0 — 2026-10-21 · Nuevo módulo: Procesos (M7)

**Migración:** sí (app nueva `procesos`: `0001` y `0002` con la carga inicial; `esynapse_sig 0069`). Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Nuevo
- **Procesos** en el menú del SIG Core:
  - **Mapa de procesos** armado desde el catálogo: bandas estratégica, principal y de soporte, con el estado de la ficha, las NC abiertas, el indicador del último periodo y los avisos de cada proceso. Un proceso nuevo aparece solo; uno desactivado desaparece. PDF del mapa con la disposición del mapa en Excel.
  - **Catálogo oficial** de procesos y subprocesos (los 9 del SIG cuelgan de «Sistema Integrado de Gestión»), con cargo responsable y usuario que recibe los avisos. Se desactiva, no se borra.
  - **Ficha de caracterización por versiones**: datos, actividades (proveedor y cliente elegidos del catálogo; Cliente, Proveedor externo, Todos los procesos como texto), documentos (vinculados a la lista maestra o descritos), registros, recursos e indicadores. Solo se edita en elaboración.
  - **Firmas**: elabora (Asistente SIG) → revisa (Gerente SIG) → aprueba (Gerente General), cada una con contraseña; quien revisa no es quien elaboró y quien aprueba no es quien revisó. Devolver con observaciones. Al aprobar, la versión anterior pasa a obsoleta y queda la huella del contenido aprobado. Cambiar una ficha vigente = «Nueva versión» con motivo.
  - **Resultados de indicadores** por mes (a mano hasta que exista el módulo de Indicadores).
  - **Fichas por revisar**: al aprobar en Documentos una versión de un documento vinculado a un proceso, su responsable recibe el aviso; se atiende al aprobar la siguiente versión de la ficha o se cierra con motivo («no requiere cambios»). También se registra a mano.
  - **PDF de la ficha** con la disposición del formato.
- **Carga inicial**: el catálogo del mapa y las 18 fichas revisadas el 2026-10-21 entran como versión 02 en elaboración, para pasar por las firmas.

### Cambiado
- **El proceso se elige del catálogo** en Hallazgos, Acciones correctivas (NC nueva), Quejas (registrar NC) y Documentos; en Auditorías se agregan procesos del catálogo al campo de áreas. Los textos existentes se vinculan solos cuando coinciden con un proceso del catálogo («SIG» → Sistema Integrado de Gestión); los demás se muestran «sin vincular» para corregirlos. Los PDF siguen imprimiendo el nombre del proceso.
- Renombrar un proceso en el catálogo actualiza el texto en Documentos y Hallazgos.

## 0.3.0 — 2026-10-20 · Nuevo módulo: Quejas (M18)

**Migración:** sí (app nueva `quejas`: `0001` y `0002`). Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Nuevo
- **Quejas** según el procedimiento de gestión de quejas, en el menú del SIG Core:
  - **Recepción y registro** con código **RQ-NNN-AAAA** (correlativo por año), fecha y hora, recibido por, reclamante (empresa, contacto, correo, teléfono, tipo de parte interesada), N° de OT, medio de recepción, origen (gestión comercial, técnica o logística) con los motivos que enumera el procedimiento, marca de origen en encuesta de satisfacción y descripción.
  - **Validación** (¿relacionada con las actividades?); si no lo está, pasa a cierre comunicando los motivos.
  - **Evaluación e investigación**: responsables, personal involucrado, evaluación, investigación y análisis de causas, ¿dentro del alcance acreditado?, ampliación del plazo con motivo y nueva fecha, si el cliente pide informe.
  - **Decisión** (requiere permiso de aprobar): procedente o no procedente con fundamento.
  - **Tratamiento**: acciones, responsable, nuevo certificado que referencia al reemplazado, trabajo no conforme (marca), seguimiento y **«Registrar NC»** — crea la No Conformidad en Hallazgos (procedencia Queja) para seguir el flujo de acción correctiva.
  - **Cierre**: comunicación del resultado, medio, conformidad del cliente; la notifica alguien no involucrado en el origen. Reapertura con motivo e historial.
  - **Comunicaciones al cliente** (acuse, validación, ampliación, avance, informe, resultado) con fecha, medio, resumen y evidencia, y **plazos** del procedimiento: acuse 24 h, resultado de la validación 2 días hábiles, informe 7 días hábiles; la pantalla marca los vencidos y por vencer.
  - Documentos adjuntos (sustento). Etapa cerrada = solo lectura.
- **PDF «Reporte de Quejas»** y **«Registro de Seguimiento de Quejas»** con la disposición de sus plantillas (el seguimiento en Arial 11, hoja horizontal, como el de acciones correctivas). Se vinculan en Configuración → Formatos impresos.
- Primera app propia de un módulo (decisión de arquitectura sobre apps por módulo): `backend/quejas/`. `Probar.bat` incluye sus pruebas.

### Cambiado
- **Quejas y Acciones correctivas: el botón que cierra cada etapa va al final de la ficha** (después de comunicaciones, adjuntos y acciones), en una barra que indica qué falta para habilitarlo: registrar validación / decisión / tratamiento concluido / cerrar (quejas); registrar evaluación, aprobar plan (con verificador designado arriba), y eficaz / no eficaz (acciones correctivas). En implementación la barra informa cuántas acciones quedan.
- **La misma barra final en Auditorías, Hallazgos y Competencia técnica** (componente común):
  - Auditorías: cada etapa (aprobar y comunicar el plan, iniciar ejecución, actas de apertura y cierre, terminar ejecución, validar hallazgos, entregar informe y cerrar) cierra con la barra al final y dice qué falta (objetivo y alcance, auditor líder, cronograma, participantes y contenido del acta, ítems sin clasificar, conclusiones). El botón de aprobar el plan, que estaba antes del equipo auditor, quedó al final.
  - Hallazgos: «Generar SAC nueva», «Sumar a SAC abierta» y «Reclasificar» bajan al final de la ficha («Cerrar el registro: derivar la No Conformidad»).
  - Competencia técnica: el entrenamiento ya no se concluye cambiando un estado en una lista; «Guardar» lo deja en proceso y la barra final ofrece «Dar por superado» o «No conforme», con confirmación y la lista de lo que falta.

## 0.2.15 — 2026-10-20 · Completar acciones: evidencia visible, confirmación y reapertura · **M9 cerrado**

**M9 Acciones correctivas cerrado** por César en esta versión. Acta de validación: `docs/validacion/M09_acta_2026-10-20.md` (por firmar).

**Migración:** sí (`esynapse_sig 0068`). Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Cambiado
- **Adjuntar evidencia**: botón propio que muestra el nombre del archivo elegido (con «quitar»), en lugar del selector del navegador que no daba señal.
- **Completar** exige describir la verificación y pide confirmación; si es la última pendiente avisa lo que sigue (pasa a verificación de la eficacia o, si solo requería corrección, se cierra la solicitud).
- **Reabrir una acción completada por error**, con motivo, mientras la solicitud está en implementación o esperando la verificación de la eficacia (vuelve a implementación). Lo completado antes queda en el historial de la acción («Reabierta el … por …: motivo»); la verificación anterior se propone para corregirla y la evidencia se conserva salvo que se adjunte otra. Verificada la eficacia, ya no se reabre.
- El PDF imprime la verificación solo de las acciones completadas.
- **Seguimiento (PDF): toda la tabla en Arial 11**, un solo tamaño (antes cada celda se achicaba para caber en una línea). Para que estados, fechas y clasificación quepan a ese tamaño, la hoja pasa a horizontal y las columnas se reparten de nuevo.
- **Seguimiento: «Fecha de actualización»** = última modificación real de las solicitudes listadas (la solicitud, sus acciones o su NC de origen), no la fecha en que se imprime.
- Ficha de la SAC: en «Actualizaciones y cambios», preguntas y respuestas alineadas.

---

## 0.2.14 — 2026-10-20 · Correcciones y acciones correctivas: agregar, corregir y quitar en su sección

**Migración:** sí (`esynapse_sig 0067`). Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Cambiado
- **Agregar dentro de su sección**: «Agregar corrección» va en la sección 5 y «Agregar acción correctiva» en la 8, en lugar de un formulario suelto al final con selector de tipo. Mientras la etapa sigue abierta, la sección vacía dice «Aún no se registran» (antes decía «No se registraron», como si ya no se pudiera).
- **Corregir o quitar** una corrección o acción correctiva pendiente mientras su etapa sigue abierta (correcciones: hasta el análisis, o la implementación si solo requiere corrección; acciones correctivas: hasta aprobar el plan). Quitar es baja lógica: no se borra, deja de contar para el plan y el PDF. Cerrada la etapa, solo lectura.

- **«Guardar análisis» con aviso**: muestra «Cambios sin guardar» mientras el análisis en pantalla difiere de lo guardado; «Aprobar plan» queda deshabilitado hasta guardar el análisis (antes no daba ninguna señal y el plan se rechazaba por falta de causa raíz).

### Corregido
- Una SAC derivada de una auditoría del SIG integrado mostraba «sig_integrado» como norma y en el PDF no marcaba ninguna casilla: ahora marca ISO 9001, ISO 14001 e ISO 45001 (las existentes se corrigieron con la migración).

---

## 0.2.13 — 2026-10-20 · Solicitud de acción correctiva: toda la información del formato en pantalla

**Migración:** sí (`esynapse_sig 0066`, completa los registros existentes). Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Cambiado
- **La ficha de la SAC muestra todas las secciones del formato**, con su numeración, en consulta: procedencia (con fecha y N° de registro, auditor, auditado, normas), no conformidad, significancia y necesidad de AC (con la justificación), extensión, correcciones, análisis de causa (también los porqués de los ciclos anteriores), acciones correctivas, evaluación de la eficacia (evaluación, fecha y responsable de cada ciclo), actualizaciones y cambios, y conformidad (resultado, fecha de cierre y responsable). Antes, lo de las etapas cerradas solo se veía en el PDF.
- **Fecha de registro** editable al registrar la SAC (p. ej. la fecha de la auditoría); si se deja vacía, la de hoy. Es parte del registro (solo se corrige mientras está Registrada) y la NC creada con la solicitud toma esa fecha de detección.
- **Causa raíz como sección propia (7)**, aparte del análisis de causa, por decisión de César (la numeración del Excel estaba errada): el formato queda con 11 secciones — 6. Análisis de causa (5 porqués) · 7. Causa raíz · 8. Acciones correctivas · 9. Evaluación de la eficacia · 10. Actualizaciones y cambios · 11. Conformidad. Igual en el PDF y en la ficha.
- **Se registra quién verificó la eficacia** (el designado o quien tiene permiso de aprobar) y ese nombre se imprime como responsable en las secciones 9 y 11 del PDF. Las solicitudes ya verificadas toman al verificador designado.

---

## 0.2.12 — 2026-10-20 · Competencia: autorización con entrenamiento superado y totales del seguimiento en el servidor

**Migración:** sí (`esynapse_sig 0065`). Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Cambiado
- **La autorización exige entrenamiento superado** (decisión de César, según el procedimiento de autorización del personal técnico): una autorización queda **Vigente** solo si la persona superó el entrenamiento y el trabajo bajo supervisión del mismo método. «En entrenamiento» no lo exige.
- **Entrenamiento superado** = todas las actividades conformes, tutor de supervisión, todos los ítems de supervisión conformes, nota teórica de 14 o más y un control de validez satisfactorio. La pantalla muestra lo que falta. La conformidad de cada ítem se elige (Conforme / No conforme).
- **Entrenamiento concluido = solo lectura** (superado o no conforme): no se edita ni se elimina; un nuevo intento es un re-entrenamiento.
- **Gerente Técnico:** puede ser eximido del entrenamiento con sustento escrito (formación, experiencia, desempeño). Solo aplica a usuarios con cargo «Gerente Técnico».
- **Suspensión y reautorización:** una autorización suspendida se reautoriza solo con un re-entrenamiento superado después de la suspensión. Una revocada no se reactiva.
- **Seguimiento: el sistema calcula** total, máximo (puntaje por pregunta × n.° de preguntas), mínimo (70 % del máximo), n.° de preguntas y resultado, con las mismas fórmulas del formato. La pantalla los muestra en vivo y el PDF imprime lo calculado. El puntaje obtenido no puede superar al establecido.
- **Decisión coherente:** con resultado no satisfactorio no se puede «Mantener» ni «Reautorizar»; suspender o reautorizar exige indicar la autorización.
- Acciones correctivas — **análisis duplicado en el PDF tras una verificación «no eficaz»**: el nuevo ciclo heredaba el análisis anterior sin cambios y el PDF lo imprimía dos veces. Ahora el nuevo ciclo empieza con el análisis en blanco (con el botón «Partir del análisis del ciclo N» para revisarlo) y exige registrar la causa raíz antes de aprobar el plan; si tras revisarlo se confirma el mismo análisis, el PDF imprime «se revisó y se confirma el análisis del ciclo N» en lugar de repetirlo.
- Acciones correctivas: se quitaron de la pantalla y de los mensajes los números de sección del procedimiento (6.4, 6.3.3, 6.5, 6.6.3, 6.8), que confundían y quedarían desfasados si el procedimiento se renumera. Revisados los demás módulos: no había otros en pantalla; se limpiaron los comentarios del código que aún citaban códigos de formatos o secciones del procedimiento.

---

## 0.2.11 — 2026-10-20 · Recorrido de prueba de todos los módulos: reglas que faltaban

**Migración:** no. Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Corregido
- **Equipos:** la próxima calibración debe ser posterior a la calibración; «Fuera de servicio» exige motivo; un equipo **dado de baja queda de solo lectura** (no se calibra, no sale, no se programa, no se reactiva); «Reactivar» solo desde fuera de servicio; no se registra una segunda salida con otra abierta ni dos retornos de la misma salida.
- **Competencia técnica:** el entrenamiento exige método, tutor y al menos una actividad; quien firma exige alcance (y laboratorio si es por laboratorio); una autorización vigente exige fecha; no se permiten dos autorizaciones activas de la misma persona para el mismo método. Los botones de PDF ya no muestran códigos internos.
- **Documentos:** un documento archivado no entra al flujo de firma ni a nueva versión (aviso en pantalla); el resumen de cambios rechaza un texto igual a la contraseña del usuario (protección ante un pegado por error).
- **Tablero:** «Hallazgos abiertos» contaba también los cerrados; ahora cuenta registrados, en tratamiento y derivados.
- **Mensajes de error:** los errores por campo se muestran como texto legible, no como código.

---

## 0.2.10 — 2026-10-20 · Acciones correctivas según el procedimiento: etapas, ciclos y formatos impresos

**Migración:** sí (`esynapse_sig 0063` esquema y `0064` datos). Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Nuevo
- **PDF de la Solicitud de Acción Correctiva** igual a su formato (procedencia con casillas de normas y procedencia, no conformidad, significancia, extensión, correcciones, 5 porqués, acciones correctivas, eficacia, actualizaciones y conformidad).
- **Seguimiento a solicitudes de acciones correctivas y no conformidades:** la tabla principal de la pantalla tiene las columnas del formato (N° SAC, procedencia, descripción, responsable de la implementación, estado, fecha de cierre, clasificación) y se imprime en PDF igual al formato con «Imprimir seguimiento» (respeta los filtros).
- Campo **Personal / entidad auditora** (sección 1 de la solicitud).
- **Ciclos de análisis:** si la verificación resulta no eficaz, el análisis y la evaluación quedan en el historial («Ciclos anteriores») y se exige una acción correctiva nueva para aprobar el plan (6.8.3).

### Cambiado
- **«Nueva SAC» registra también su No Conformidad** en Hallazgos (clasificación NC mayor/menor y proceso), o toma una NC del registro que aún no se trate en otra solicitud; hereda su descripción y requisito.
- **Etapas de solo lectura:** el registro se corrige («Corregir registro») solo mientras la solicitud está Registrada; las acciones correctivas se agregan solo en el análisis y las correcciones hasta la implementación (si no requiere AC).
- **Responsable de la implementación obligatorio** al evaluar (6.3.3).
- La verificación de eficacia la hace el verificador designado o quien tiene permiso de aprobar.
- Hallazgos: nueva procedencia «Revisión por la dirección».
- Acciones correctivas: cada caja de texto (descripción de la NC, extensión, justificación, preguntas y respuestas de los porqués, causa raíz, acciones, verificación y eficacia) tiene un botón para abrirla en una ventana grande y redactar o revisar con espacio (componente reutilizable para los demás módulos).
- **Análisis de causa (5 porqués) con pregunta y respuesta:** el analista redacta cada pregunta según su análisis y registra su respuesta; la siguiente pregunta parte de la respuesta anterior (la pantalla sugiere la redacción), se pueden agregar más de cinco y la última respuesta puede usarse como causa raíz. El PDF imprime cada pregunta con su respuesta; los análisis anteriores (solo respuestas) se conservan.

### Corregido
- «Nueva SAC» con un hallazgo elegido no lo enlazaba (el hallazgo seguía como pendiente y no se cerraba con la solicitud).
- Detectado en la prueba en pantalla: tras una verificación «no eficaz» el texto de la evaluación quedaba escrito y se mezclaba con la siguiente; ahora se limpia al cambiar de etapa.
- Detectado en la prueba en pantalla: al pasar a análisis, el tipo de acción seguía en «Corrección»; ahora propone «Acción correctiva» cuando corresponde.
- Hallazgos: el código que queda libre al reclasificar (p. ej. una NC que pasa a observación) ya no se vuelve a asignar a otro hallazgo; sigue en el historial del reclasificado.

### Pruebas
- `test_acciones_correctivas.py` (10): NC creada con la SAC, clasificación obligatoria, SAC desde NC existente, registro editable solo en Registrada, responsable obligatorio, acciones por etapa, ciclo no eficaz, quién verifica, cierre solo con corrección, PDF de solicitud y seguimiento, 5 porqués con pregunta y respuesta; código de hallazgo no reutilizado. 136 pruebas en verde.

## 0.2.9 — 2026-10-17 · Hallazgos según el procedimiento de no conformidades y acciones correctivas

**Migración:** sí (`esynapse_sig 0061` esquema y `0062` datos). Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Cambiado
- **Toda No Conformidad (mayor o menor) se trata en una Solicitud de Acción Correctiva**; en la solicitud se evalúa si basta una corrección.
- **Sumar a una SAC abierta:** una NC del mismo problema se agrega como nueva ocurrencia a la solicitud en curso, en lugar de abrir otra. El sistema lista las solicitudes abiertas y marca las del mismo requisito o proceso como posible mismo problema. La solicitud muestra todas las NC que trata.
- **Observaciones y oportunidades de mejora** ya no tienen análisis ni cierre propios en Hallazgos: quedan **«Derivado a riesgos y oportunidades»**, como dice el procedimiento. Las abiertas pasan a ese estado; las cerradas se conservan.
- **Etapa cerrada = solo lectura:** el registro de un hallazgo se corrige («Corregir registro») solo mientras no se haya derivado a una solicitud; los de auditoría se corrigen desde la auditoría. El servidor rechaza el cambio nombrando el campo y la solicitud que ya lo trata.
- **Reclasificar** es una acción controlada con motivo: si cambia el prefijo toma un código nuevo y el anterior queda en el historial del hallazgo.
- Una NC de auditoría se deriva recién después de la reunión de cierre.
- El año del código del hallazgo es el del programa de auditoría (si nació en una) o el de la fecha de detección.
- Código de la solicitud **SAC-NN-AAAA**, como en el procedimiento (las existentes conservan su código).
- Mis tareas: el responsable ve las NC aún no derivadas a una solicitud.
- Listado de hallazgos: la columna «Tratamiento» muestra la SAC, «SAC pendiente» o «Riesgos y oport.».
- **Todas las tablas del sistema** muestran encabezados y contenido centrados (regla de diseño global); en Hallazgos el código y la SAC ya no se parten en dos líneas.

### Corregido
- **Verificar la eficacia de una SAC fallaba** (la operación quedaba sin respuesta): ahora, si es eficaz, cierra la solicitud y todas sus NC; si no, vuelve a análisis de causa. La verifica el verificador designado al aprobar el plan (o quien puede aprobar).
- Una SAC cerrada solo con corrección (sin acción correctiva) ahora también cierra sus NC.
- Hallazgos: al abrir «Corregir registro» la ventana del detalle quedaba encima del formulario e impedía guardar (detectado en la prueba en pantalla).

### Pruebas
- `test_hallazgos.py` (9): NC con SAC y observación derivada, sumar ocurrencia a SAC abierta sin duplicar, no sumar a una SAC cerrada, cierre de la SAC (no eficaz / eficaz) cierra todas sus NC, registro editable hasta derivar, reclasificación con motivo, hallazgo de auditoría, año del código, baja lógica. 124 pruebas en verde.

## 0.2.8 — 2026-10-16 · Auditorías: un solo auditor líder y lista integrada ISO 9001/14001/45001 completa

**Migración:** sí (`esynapse_sig 0055` a `0060`; 0057 y 0059 ajustan el catálogo, las demás son de datos). Cerrar el sistema → `Aplicar actualizacion.bat` → `Iniciar`.

### Nuevo
- **Lista de verificación integrada ISO 9001 / ISO 14001 / ISO 45001 completa**: 165 preguntas (antes 48) bajo los títulos de cláusula de la estructura común (capítulos 4 a 10). Cubre todos los numerales de las tres normas, incluidos los que faltaban (p. ej. 9001 7.1.6, 8.5.5 y 8.5.6; 14001 8.1 perspectiva de ciclo de vida; 45001 6.1.2.3, 8.1.4 y 9.1.1). Cada pregunta empieza, en negrita, con la norma y el numeral exacto que la exige (p. ej. *ISO 9001: 7.1.5.2*; *ISO 14001: 8.2 · ISO 45001: 8.2*). Se elimina el código inventado "8.2e": la cláusula 8.2 agrupa los requisitos del servicio (9001) y la preparación ante emergencias (14001 y 45001), cada pregunta con su referencia. Las listas ya generadas conservan sus ítems; la nueva aplica a las que se generen desde ahora.
- **Listas por norma (ISO 9001, ISO 14001 o ISO 45001 auditadas solas)**: antes traían solo los títulos de cláusula, sin preguntas. Ahora cada una sale de la lista integrada con solo las preguntas que esa norma exige (9001: 105, 14001: 88, 45001: 102), citando solo su numeral, con los títulos de cláusula propios de la norma (p. ej. 8.2 "Preparación y respuesta ante emergencias" en 14001 y 45001) y la redacción propia en las preguntas comunes (sin aclaraciones "en SST" o "en ambiental"). Nro. correlativo por lista. Los selectores de cláusulas del programa y del plan siguen usando los títulos de cláusula.
- **Sistema Integrado y normas sueltas no se combinan** en una misma auditoría (se duplicarían preguntas en dos listas): al marcar uno se desmarca el otro y el servidor rechaza la combinación.
- En la lista integrada, la columna **Nro.** de las preguntas es un correlativo (1 a 165); los títulos de cláusula conservan su numeral (4, 4.1…). Antes se numeraban 4.1.a, 4.1.b…, que parecían numerales de la norma que no existen. El hallazgo que nace de una pregunta y el informe citan la norma y el numeral reales (p. ej. *ISO 9001 7.1.5.2*), no el número de fila.

### Corregido
- El auditor líder se definía en dos lugares (la lista "Auditor líder" del plan y el equipo auditor) y podían contradecirse: el plan imprimía a uno y la pantalla mostraba a otro. Ahora el líder se define **solo en el Equipo auditor** con el rol "Auditor líder", interno o externo; se retiró la lista del plan.
- Solo puede haber un auditor líder: el segundo se rechaza indicando quién lo es.
- Sin auditor líder en el equipo no se aprueba el plan (un integrante con rol "Auditor" no cuenta, aunque su cargo diga "líder").
- Plan, actas, informe, firmas, el listado y la franja de la auditoría muestran el mismo nombre, también cuando el líder es externo.
- Al agregar un integrante externo, el cargo se sugiere con el nombre de su rol.
- Plan de auditoría (PDF): el cronograma de entrevistas imprime solo las filas registradas en el sistema (antes completaba 27 filas vacías); sin entrevistas, una fila en blanco.
- Lista de verificación: el resultado se muestra como "Observación" (antes "Observa"), igual que en hallazgos y en el PDF.
- Actas de apertura y cierre (PDF): bajo "Representante de METRINDUST S.A.C." se imprime el nombre del responsable del sistema integrado de gestión registrado en Configuración (antes quedaba "(Nombre y Apellido)").
- Registros existentes: si el equipo no tenía líder, el usuario de la lista anterior pasa al equipo como líder; si el equipo ya tenía líder, manda el del equipo.

### Pruebas
- Lista integrada: prueba que comprueba que todos los numerales de las tres normas tienen pregunta y que cada pregunta cita su norma y numeral.
- `test_auditorias_lider.py`: líder único, líder externo, sin líder no se planifica, quitar al líder, el campo no se edita directamente, registros anteriores (114 pruebas en verde).

## 0.2.7 — 2026-10-16 · Auditorías internas: secuencia del procedimiento, una etapa a la vez; formatos PDF iguales a las plantillas

**Migración:** sí (`esynapse_sig 0052` a `0054`, además de las de 0.2.6 si aún no se aplicaron). Cerrar el sistema → `Iniciar` (las aplica solo).

### Nuevo
- **La auditoría sigue la secuencia del procedimiento de auditoría interna**, paso por paso: **1 Plan** → **2 Documentos de trabajo** → **3 Reunión de apertura** → **4 Ejecución** → **5 Conclusiones** → **6 Reunión de cierre** → **7 Informe** → **Cerrada**. Nuevos estados: Reunión de apertura, Conclusiones y Reunión de cierre.
- **Una etapa a la vez.** El detalle ya no es una página larga: la barra de pasos muestra solo la etapa en curso; las anteriores se abren con un clic en solo lectura ("Volver a la etapa actual") y las futuras no se abren. Una franja de contexto fija muestra código, programa, normas, área, líder y estado. Cada paso cierra con un único botón que pide confirmación.
- **Plan:** lo aprueba el **auditor líder** (o quien tenga permiso de aprobar) con "Aprobar y comunicar plan"; exige objetivo, alcance, líder y al menos una entrevista en el cronograma; se registra quién lo aprobó y cuándo. Aprobado, el plan, el equipo y el cronograma son de solo lectura.
- **Documentos de trabajo:** la lista de verificación se **prepara** aquí (generar ítems, documento de referencia) y es **opcional**, como dice el procedimiento; la **evaluación** (evidencia y conclusión C/NC/OBS/NA) se registra en la ejecución.
- **Actas:** cada reunión tiene su paso. Registrar el **acta de apertura** inicia la ejecución (fecha de inicio); registrar el **acta de cierre** congela los hallazgos y abre el informe (fecha de fin). Exigen participantes y la sección 2; una vez registradas no se editan.
- **Ejecución:** sin acta de apertura no se evalúa la lista ni se registran hallazgos.
- **Conclusiones (nuevo paso):** el equipo auditor consolida los hallazgos: los **reclasifica** (si cambia de NC a observación, toma el código del nuevo tipo), corrige su redacción o los **descarta** (baja lógica) y registra las **conclusiones de la auditoría** (grado de conformidad), obligatorias para pasar a la reunión de cierre. Lo validado es lo que se presenta en la reunión y se imprime en el informe.
- **Informe:** se completa después del acta de cierre (lugar, entrevistados, fortalezas, debilidades); las conclusiones se muestran tal como se validaron. "Entregar informe y cerrar" (o enviarlo a aprobación) registra la fecha del informe. Si el aprobador lo devuelve, se corrige el informe y se reenvía; las conclusiones ya comunicadas no cambian.
- **Destino de cada hallazgo:** toda no conformidad de auditoría (mayor o menor) requiere acción correctiva; las observaciones y oportunidades de mejora se marcan para **riesgos y oportunidades**, como indica el procedimiento (se conectarán cuando exista ese módulo).
- **Ventanas para redactar con espacio.** Cada ítem de la lista de verificación se abre en una ventana (clic en el requisito) con el texto completo del requisito tal como en el formato, campos amplios para documento de referencia y evaluación/evidencias, la conclusión, y botones Anterior / Siguiente que guardan al moverse; los campos se habilitan según la etapa (documento de referencia en preparación y ejecución; evaluación solo en ejecución). Los hallazgos se registran, corrigen (en Conclusiones) o leen en una ventana con descripción amplia, indicando a dónde irá su tratamiento.
- **Trazabilidad lista → hallazgo.** Cada ítem evaluado como **No cumple** u **Observación** aparece en Hallazgos como *pendiente de clasificar* (y con una etiqueta en la lista). Se seleccionan uno o varios y se decide: **registrar como hallazgo** (la ventana viene con requisito y evidencia precargados y tipo sugerido: No cumple → NC menor, Observación → observación; se reclasifica en Conclusiones), **sumar a un hallazgo existente** (un mismo problema que incumple varios requisitos) o **no genera hallazgo** con motivo obligatorio. Cada hallazgo muestra sus ítems de origen y cada ítem su hallazgo. "Validar hallazgos" no avanza mientras quede algún ítem sin decidir. Si un hallazgo se descarta, sus ítems vuelven a pendientes; si un ítem pasa a Cumple, se libera. Los hallazgos que no salen de la lista se siguen registrando directamente (la lista es opcional).
- Pantalla final de la auditoría cerrada con todos sus PDF (plan, actas, listas, informe) y los hallazgos con su destino.

- **Formatos PDF revisados uno por uno contra sus plantillas Excel/Word** (cada plantilla se convirtió a PDF y se comparó hoja por hoja con lo que genera el sistema). Se usaron los anchos de columna reales del Excel (la lectura anterior tomaba un ancho por defecto en columnas agrupadas y deformaba las proporciones) y la escala de impresión de cada hoja:
  - **Actas de apertura y cierre:** grilla del Excel; tipo de auditoría con rótulos In Situ / Remoto / Híbrido en azul y X en la casilla; 12 filas fijas de participantes con las casillas *Equipo auditor* / *Auditado*; secciones 2–4 con recuadro de altura fija; firmas "Representante de METRINDUST S.A.C." y "Auditor Líder"; fecha de la reunión (inicio o fin de la auditoría), no la de impresión; todo en una hoja.
  - **Informe:** estructura del Word con secciones numeradas 1 a 8 y literales a) a g) en el punto 4; tabla de registro; resultados con N°, norma, requisito, descripción y clasificación (solo hallazgos vigentes; la norma sale de los ítems de la lista o del requisito); firma con *Nombre* y *Fecha*; encabezado y pie "Documento confidencial" en cada hoja.
  - **Plan:** grilla de 47 columnas; casillas de normas (ISO 9001 / 14001 / 45001 / NTP ISO/IEC 17025 / Otros) y de tipo de auditoría con X; equipo auditor; cronograma de 27 filas; observaciones; firma del auditor líder; una hoja.
  - **Programa anual:** meses con el nombre completo en vertical; bloques *Elaborado por* / *Aprobado por* y leyenda de colores separados como en el Excel; 9 bloques preimpresos.
  - **Competencia:** *Entrenamiento y supervisión* (hoja 1 entrenamiento con 10 actividades y casillas Entrenamiento / Re-entrenamiento; hoja 2 trabajo bajo supervisión con 15 ítems y comentarios); *Autorización del personal* con el texto del Word, nombre centrado, literales a), b)… (obligaciones generales siempre y funciones según lo autorizado, con el método y el alcance de firma), lugar y fecha a la derecha y firma del Gerente Técnico; *Entrevista de seguimiento* con la grilla horizontal, 5 filas de preguntas y resultados en celdas combinadas.
  - **Equipos:** la **Hoja de Vida** ahora es el libro completo (Ficha técnica + Mantenimiento preventivo, Calibraciones, Verificaciones, Comprobaciones intermedias, Caracterización e Historial de sucesos, una hoja cada una); la ficha replica el Excel (casillas de clasificación, inicio de servicio y código, especificaciones en el orden del formato, recuadro de imagen); cada bitácora suelta lleva una línea con el equipo. **Inventario** con los rótulos del Excel y el estado calculado como el Excel: *Instrumento Calibrado* (verde), *Calibración Requerida* si la próxima calibración ya pasó (rojo; antes salía "calibrado" aunque estuviera vencido) o *No Aplica* (ámbar). **Programa de equipos** con la fila AÑO, "Frecuencia" y filas preimpresas. **Carta de trazabilidad** con cajas verdes, marcos por grupo, zona celeste para los patrones del laboratorio y flecha gruesa hacia el recuadro de instrumentos. **Intervalo de calibración** con las columnas desviación y tiempo, factores CENAM 0,2 / 0,7, periodo de calibración (PC) y periodo de comprobación (PV) a partir del último resultado.
  - Pendiente: los formatos *Informe de mantenimiento*, *Informe de comprobación intermedia* y *Control de salida y entrada del equipamiento* aún no se generan desde el sistema.

### Cambiado
- Plan de auditoría: el campo de criterios adicionales ahora sugiere otras normas (p. ej. ISO 50001, ISO/IEC 27001) y explica que se imprime en la casilla OTRO(S); antes sugería manuales y procedimientos y se confundía con los documentos de referencia.
- Se retira "Generar informe" desde la ejecución: el informe se habilita con el acta de cierre.
- Reprogramar se permite hasta antes de la reunión de apertura.
- Auditorías que estaban "En ejecución" sin acta de apertura pasan a "Reunión de apertura" (migración `0053`).

### Pruebas
- 103 en verde (5 nuevas de trazabilidad: pendientes que bloquean la validación, un hallazgo desde varios ítems, sumar a uno existente, descarte con motivo, reapertura al anular un hallazgo, liberación al pasar a Cumple). Nueva batería de la secuencia (`test_auditorias_etapas.py`): etapas abiertas por estado, plan con cronograma y aprobado por el líder, lista solo en documentos de trabajo y evaluación solo en ejecución, lista opcional, acta de apertura que inicia la ejecución y no se edita, consolidación (reclasificar, descartar, conclusiones obligatorias), acta de cierre que congela hallazgos, informe solo después del cierre, reprogramación solo antes de la apertura. Ayudante común `tests/flujo_auditoria.py`.

---

## 0.2.6 — 2026-10-12 · Programa anual bloqueado al aprobar, con ciclo de modificación y revisión

**Migración:** sí (`esynapse_sig 0044` a `0051`). Cerrar el sistema → `Iniciar` (las aplica solo).

**Después de actualizar:** ir a **Configuración → Identidad** y completar nombre de la empresa, dirección y responsable del SIG (hoy están vacíos); son los datos del bloque "1. Datos del laboratorio" de los formatos de auditoría. La sección Plan avisa en ámbar mientras falten.

### Nuevo
- **Regla general: una etapa cerrada es de solo lectura (ADR-0005).** Decisión de César: al avanzar de etapa, lo registrado en las etapas previas ya no se modifica; tampoco se captura por adelantado lo de una etapa futura. Aplicada en Auditorías: **Programa anual** (proceso, clase, normas, cláusulas, mes, observaciones, cambio de programa) solo mientras está Programada; **Plan** (objetivo, alcance, criterios, documentos, fecha de elaboración, cronograma, modalidad, líder, equipo auditor) hasta Planificada; **Ejecución** (listas de verificación, actas, hallazgos) solo En ejecución; **Informe** (lugar, personas entrevistadas, fortalezas, debilidades, conclusiones) hasta En informe; Cerrada = todo solo lectura. Reprogramar sigue permitido hasta antes de ejecutar (es una desviación registrada, no una edición). El servidor rechaza el cambio nombrando la etapa y el campo; en pantalla cada sección muestra "solo lectura" y sus campos deshabilitados. "Lugar" y "Personas entrevistadas" pasan de la sección Plan a la sección Informe (son datos del informe) con botón "Guardar informe". La regla se extiende a los demás módulos construidos (tarea en `PENDIENTES.md`) y rige para los nuevos.
- **El programa anual aprobado es de solo lectura.** No se pueden agregar ni quitar auditorías, ni cambiar lo que define el programa (proceso, tipo, clase, normas, cláusulas, mes programado, observaciones). Los datos del plan (objetivo, alcance, equipo, cronograma, actas, informe) y la **reprogramación** siguen permitidos: reprogramar registra la desviación en la fila "Reprogramado" sin alterar lo aprobado.
- **Modificar programa**: abre un programa aprobado para cambios con motivo obligatorio (queda "En modificación"); al volver a aprobarlo —directo o por el candado— sube la **revisión** (rev. 1, 2…), que se imprime en el PDF con quién lo modificó, cuándo y por qué.
- Un programa sin auditorías no se aprueba.
- Pantalla: estado y revisión del programa junto al selector; botón "Modificar programa"; aviso en la sección Programa anual de cada auditoría y en el formulario de creación cuando el programa está aprobado.
- **Cronograma de entrevistas**: las celdas de requisitos por norma ya no son texto libre; al hacer clic se abre el selector de cláusulas del catálogo (casillas, buscador, "Todas", "limpiar" y un atajo "usar las del programa" que copia las cláusulas definidas en el programa anual). Las columnas de normas fuera del alcance de la auditoría quedan deshabilitadas.
- El modal de confirmación del sistema ahora admite un **campo de texto** (motivo, conclusiones). Se eliminaron todos los diálogos nativos del navegador (`window.prompt`): modificar programa, devolver/rechazar en las bandejas de Auditorías, Competencia y Equipos, y corregir conclusiones al reenviar un cierre, usan el mismo modal con estilo del sistema (Enter confirma, Escape cancela, campo obligatorio cuando corresponde).

### Corregido
- **Lista y programa**: el selector de programa ahora **filtra la lista** (antes mostraba todas las auditorías sin importar el programa elegido) y hay una columna "Programa" con el año de cada auditoría (o "sin programa"). Opción "Sin programa (extraordinarias)".
- **Programa obligatorio** para auditorías programadas (una programada sin programa nunca aparecía en ningún PDF). El formulario toma por defecto el programa seleccionado; las extraordinarias pueden ir sin programa.
- En el detalle se puede **mover una auditoría a otro programa** (no hacia uno aprobado ni desde uno aprobado).
- El código de la auditoría (`AI-NN-AAAA`) lleva el **año del programa anual** al que pertenece, no el año en que se registra: una auditoría del Programa 2027 creada en 2026 es `AI-01-2027`. Correlativo independiente por año; las extraordinarias sin programa usan el año en curso.
- **El código sigue al programa.** Si una auditoría que aún no se ejecutó (programada o planificada) se mueve a un programa de otro año, recibe el siguiente correlativo de ese año. Las que ya están en ejecución o cerradas conservan su código (ya está impreso en actas y listas) y **no se pueden cambiar de programa**. La migración `0045` corrige de una vez las auditorías existentes cuyo código no coincidía con el año de su programa (p. ej. `AI-04-2026` en el Programa 2027 pasa a `AI-0n-2027`). El número que se libera no se reutiliza: el correlativo del año continúa donde iba.

- **Lista de verificación NTP-ISO/IEC 17025 igual al formato del procedimiento.** El catálogo anterior tenía 35 filas resumidas (una por cláusula); el formato trae 175 filas con el texto completo de cada numeral (4.1.1 … 8.9.3, con las adiciones de la directriz de acreditación) más los 8 **ítems para considerar en las auditorías internas de seguimiento**. Ambos bloques se cargan desde el catálogo (migración `0049`), se evalúan en pantalla (el bloque de seguimiento aparece primero, con su título) y se imprimen en el PDF. El PDF replica el Word: título "Lista de verificación de auditoría NTP-ISO/IEC 17025", datos del laboratorio (5 filas), tabla "Miembros del equipo evaluador" con Función / Nombre completo y filas fijas Auditor líder / Auditor / Experto técnico, firma del líder y fecha antes de la lista, recuadro NOTAS, tabla de seguimiento, tabla de requisitos con doble encabezado (título del bloque · Documento de referencia · Evaluación · Conclusiones) y el **Anexo 1** con las disciplinas de calibración y su nota. La conclusión se imprime como C / NC / OBS / NA (en blanco si no se evaluó). La lista integrada 9001/14001/45001 comparte la misma cabecera y doble encabezado, como en su Word. Las listas 17025 generadas antes conservan sus 35 ítems; para tener la lista completa se genera de nuevo en una auditoría nueva.
- **PDF de la lista de verificación 17025 verificado contra el Word del procedimiento, página por página.** El texto de cada requisito conserva la presentación del formato: viñetas **a), b), c)…** con sangría (5.5, 6.2.5, 7.1.1, 8.9.2…), guiones anidados bajo su literal (8.7.1, 8.8.1), negritas de "Directriz DA-acr-06D:" y de los numerales de la directriz, y los espacios entre párrafos (migraciones `0050` y `0051`; las listas de auditorías no cerradas se actualizan, las cerradas no se tocan). Encabezado de la tabla de requisitos con celdas combinadas como el formato: el título del bloque abarca Nro. y Descripción, y **Documento de referencia** y **Evaluación** ocupan las dos filas del encabezado (antes se repetían); igual en la tabla de seguimiento (encabezado de tres filas). Capítulo, cláusula y primer numeral van en la misma fila (4 · 4.1 · 4.1.1), con los números alineados a su texto. Encabezado de control repetido en cada página; azul del formato (#16365C), anchos de columna de la grilla del Word, letra de 8 pt en requisitos y 10 pt en la cabecera, firma del líder con línea para firmar, NOTAS y salto de página antes de los ítems de seguimiento; Anexo 1 en página propia con la nota antes de la tabla, encabezado gris y "Electroquímicos" como celda combinada. Ninguna fila se parte entre páginas. La lista integrada 9001/14001/45001 usa la misma tabla.
- **Selectores de cláusulas (programa anual y cronograma) solo con números y subtítulos.** Con el catálogo 17025 completo, los selectores mostraban el texto íntegro de cada requisito. Ahora las secciones conservan su subtítulo (4.1 Imparcialidad, 6.2 Personal…) y los numerales de una norma con secciones se listan solo por número, sangrados bajo su sección, con el texto completo como ayuda al pasar el cursor. Solo se listan capítulos y cláusulas (4 · 4.1); los numerales de tercer nivel en adelante (4.1.1, 7.8.2.1…) no aparecen en los selectores porque se auditan dentro de su cláusula. Las cláusulas se sangran bajo su capítulo. Los ítems de seguimiento tampoco aparecen (son de la lista, no del programa). El texto íntegro sigue en la lista de verificación y en su PDF. El catálogo se entrega sin paginar (antes se cortaba en 25 filas, en 17025 justo en el 5.4) y, como respaldo, la pantalla recorre todas las páginas si el servidor llegara a responder paginado.
- **Plan de auditoría: fecha de elaboración.** El formato lleva "Auditoría interna N°" y "Fecha de elaboración" en la misma fila; el PDF no imprimía la fecha. Nuevo campo con selector en la sección Plan; si se deja vacío, se fija solo con la fecha en que la auditoría pasa a Planificada. Las auditorías ya planificadas antes de este campo reciben la fecha de su última modificación (migración `0047`); si aun así está vacía, el PDF imprime la fecha del día.
- **Hora en 12 horas** en los PDF: el cronograma de entrevistas del plan y la entrevista de seguimiento (competencia) imprimen `08:00 a. m.` / `02:30 p. m.`, igual que la pantalla (el selector sigue guardando 24 h).
- **Formato único de fecha `AAAA-MM-DD`** en todo el sistema. Los PDF ya lo usaban; en pantalla había 18 lugares (bandejas del candado, historial de documentos, movimientos de equipos, cierre de acciones correctivas, log de auditoría) que mostraban `14/10/2026` según el navegador. Todos pasan por el mismo helper (`lib/fecha.js`), que además deja de retroceder un día en fechas sin hora por la zona horaria.
- **Nombre de la empresa en los formatos**: si el campo "Nombre de la empresa" (Configuración → Identidad) está vacío, los PDF lo dejan en blanco; antes caían al nombre del producto y el plan decía "eSYNAPSE 360°" en "Empresa". Afectaba a los 10 generadores (auditorías, equipos, competencia). Dirección y Responsable del SIG se toman de la misma pantalla.

### Pruebas
- 94 en verde (nuevas: viñetas, sangrías y negritas del formato en catálogo, lista y PDF; lista 17025 con 183 filas y PDF; catálogo entero sin paginar; etapas cerradas por estado —planificada cierra el programa, ejecución cierra el plan, informe cierra la ejecución, cerrada todo— y etapa futura no editable; fecha de elaboración del plan, bloqueo de alta/baja/campos, plan y reprogramación permitidos, modificar con motivo, revisión al reaprobar directo y por candado, programa vacío, código con el año del programa, recodificación al mover y conservación en ejecución, hora 12 h y nombre de empresa).

---

## 0.2.5 — 2026-10-12 · Formatos impresos vinculados a la lista maestra

**Migración:** sí (`core 0013` sigla del cargo · `esynapse_sig 0043` catálogo de formatos). Cerrar el sistema → `Iniciar` (las aplica solo).

### Nuevo
- **Configuración → Formatos impresos.** Lista de los 15 PDF que genera el sistema (equipos, competencia, auditorías). Cada uno se vincula con su documento de la **lista maestra**; la caja de control del PDF imprime entonces el código, la **versión vigente**, su fecha y las siglas de quien elaboró, revisó y aprobó esa versión en Documentos. Al aprobar una nueva versión del formato en M6, todos los PDF la imprimen automáticamente. La pantalla muestra qué imprimirá cada formato y de dónde sale (lista maestra / respaldo / por defecto). Si un documento de la lista maestra ya tenía el mismo código del formato, quedó vinculado solo; el vínculo anterior de la Hoja de Vida se conservó.
- **Sigla del cargo** en Usuarios (ASIG, GSIG, GT, GG…): es la que se imprime como firma en los formatos.
- Una sola función resuelve la caja de control para **todos** los PDF (antes la Hoja de Vida y cada formato de Equipos tenían su propia lógica).

### Cambiado
- Auditorías: las cláusulas a auditar por norma se eligen con **casillas de selección múltiple** (con buscador, "Todas" y "limpiar"), y solo aparecen las normas marcadas en "Normas / criterios" (el Sistema Integrado habilita 9001, 14001 y 45001).

### Pruebas
- 72 en verde (nuevas: resolución desde lista maestra / respaldo / por defecto, firmante sin sigla, PDF imprime la versión vigente, API de formatos; humo de PDF de Equipos y Competencia).

---

## 0.2.4 — 2026-10-12 · M10 Auditorías: candado de aprobación e independencia del auditor

**Migración:** sí (`esynapse_sig 0042`, solo opciones). Cerrar el sistema → `Iniciar` (la aplica solo).

### Nuevo
- **Candado de aprobación en Auditorías.** Aprobar el programa anual y cerrar el informe pasan por el mismo control que Equipos y Competencia: quien tiene permiso de aprobar lo hace directo; quien no, deja una **solicitud pendiente** que el aprobador puede **aprobar, devolver para corrección o rechazar**. El solicitante ve sus solicitudes, corrige (por ejemplo, las conclusiones del informe) y reenvía. Botones "Cambios pendientes" y "Mis solicitudes" en Auditorías; "Aprobar programa" / "Enviar a aprobación" junto al selector del programa.
- **Independencia del auditor.** Al agregar un integrante que pertenece al área o laboratorio que se va a auditar, el sistema muestra un aviso (ISO 19011) sin bloquear la asignación; los observadores están exentos.

### Pruebas
- 58 en verde (nuevas: candado de programa e informe con aprobar/devolver/reenviar/rechazar, bandejas separadas por módulo, aviso de independencia).

Con esto **M10 Auditorías queda completo**; falta solo su acta de validación.

---

## 0.2.3 — 2026-10-12 · Versión, fecha y siglas por formato

**Migración:** no. Reiniciar el backend.

### Corregido
- La cabecera de control de cada PDF imprime la **versión, fecha y siglas de firma de su propia plantilla** (leídas de los archivos del procedimiento), en lugar de valores globales. Afecta a los siete formatos de auditoría y a los tres de competencia técnica. Ejemplos: programa anual v02 del 2026-01-12; actas e informe v00 del 2025-01-10 con revisado "GSIG"; listas de verificación v00 del 2026-01-12.
- Tabla de control de formatos en `ficha_pdf.py` (`CONTROL_FORMATOS`): al cambiar una plantilla se actualiza ahí.
- Nuevo `docs/04_formatos_implementados.md`: registro de todas las plantillas del SIG que el sistema imprime (código, versión, fecha, siglas, generador), procedimiento ante cambio de versión y observaciones sobre las plantillas.

---

## 0.2.2 — 2026-10-11 · Programa anual de auditorías fiel al formato

**Migración:** sí (`esynapse_sig 0041`). Cerrar el sistema → `Iniciar` (la aplica solo).

### Nuevo
- **Clase de auditoría**: interna (la ejecuta el SIG) o externa (INACAL, certificadora). El programa anual registra ambas y las distingue por color, como la leyenda del formato: azul interna, amarilla externa.
- **Requisitos a auditar por norma**: al crear la auditoría (y en su detalle) se eligen las cláusulas de ISO 9001, 14001, 45001 y 17025 desde el catálogo; salen en las cuatro columnas del programa.
- **Observaciones del programa anual** por auditoría.
- **Reprogramación** desde el detalle (nuevo mes + motivo obligatorio). El mes programado original se conserva: la fila "Programado" muestra el original y "Reprogramado" el nuevo.
- Mes programado se elige por nombre (selector) en lugar de número.

### Cambiado
- PDF del programa anual reconstruido 1:1: cabecera con elaborado/aprobado, fechas y leyenda de colores; columnas Norma y requisitos (4) · Proceso a auditar · Estado (Programado / Reprogramado / Ejecutado) · 12 meses · Observaciones. Se retiran "código" y "auditor líder", que el formato no tiene.

### Pruebas
- 49 pruebas en verde (nuevas: reprogramar conserva el mes original y exige motivo; clase, requisitos y observaciones se guardan; PDF con interna reprogramada y externa).

---

## 0.2.1 — 2026-10-10 · Selectores de fecha y hora en tema oscuro

**Migración:** no. Solo recargar el frontend.

### Corregido
- Los campos de fecha y hora (cronograma de entrevistas y cualquier otro del sistema) ya muestran el icono de calendario/reloj en el tema oscuro; antes se dibujaba en negro sobre fondo oscuro y parecían campos de texto. Ancho mínimo en fecha y hora del cronograma.

---

## 0.2.0 — 2026-10-10 · Ordenamiento del proyecto

**Migración:** sí (`esynapse_sig 0040`, solo etiquetas; no cambia datos). El lanzador la aplica solo.

### Nuevo
- **Pruebas automáticas** (47): autenticación y permisos, soft delete, configuración y versión, M12 técnico autorizado y firma controlada, candado de aprobación completo, M10 ciclo de auditoría, hallazgos → M8, lista integrada y los seis PDF, M6 segundo factor. `Probar.bat` las ejecuta.
- **Documentación** en `docs/`: método de trabajo, arquitectura y convenciones, operación en el PC, fichas de los 7 módulos construidos, 4 decisiones de arquitectura (ADR), plantilla de acta de validación (17025 7.11) y checklist de aceptación.
- **Versionado**: `backend/VERSION`, este CHANGELOG, versión visible en la API pública y en Configuración.
- **Scripts**: `Respaldar.bat` (base + media + certificados con fecha); el lanzador detecta y aplica migraciones pendientes antes de arrancar; `Aplicar actualizacion.bat` muestra la versión y advierte cerrar el servidor; `Sincronizar carpeta limpia.bat` incluye `docs/` y archivos de raíz, y excluye scripts de diagnóstico y credenciales.
- `PENDIENTES.md` convertido en backlog priorizado; `CLAUDE.md` con el estado real de fases y el método de trabajo.

### Corregido
- **Candado de aprobación**: reenviar una solicitud devuelta (y actuar sobre cualquier solicitud ya resuelta) respondía 404 porque el filtro "pendientes" de la bandeja se aplicaba también a las acciones de detalle. Afectaba Equipos y Competencia. Detectado por la nueva suite de pruebas.

---

## 0.1.9 — 2026-10-10 · Auditorías: formatos completos

**Migración:** sí (`esynapse_sig 0037, 0038, 0039` · `core 0012`).

- Lista de verificación **integrada** ISO 9001·14001·45001 (83 filas autoría propia; el formato real viene en blanco) y campo "documento de referencia" por ítem.
- Seis PDF reconstruidos 1:1 con el procedimiento de auditoría interna: programa anual (matriz programado/reprogramado/ejecutado), plan (datos del laboratorio, criterios, equipo, **cronograma de entrevistas** con columnas por norma, observaciones), actas de apertura y cierre (participantes con condición, 4 secciones, firmas), informe (registro, detalles, criterios, lugar, entrevistados, resultados, conclusiones, firma), listas (r06/r07 con encabezado real).
- Captura completa en pantalla: cronograma de entrevistas, lugar, personas entrevistadas, observaciones del plan, documentos de referencia, cargo de los auditores (se autocompleta), participantes y tres secciones de acta, documento de referencia y evaluación por ítem.
- Configuración: **dirección de la empresa** y **responsable del SIG** (salen en plan, informe y listas).
- El líder del equipo auditor se sincroniza como auditor líder; la validación de "Planificar" lo acepta.
- Criterios: las normas seleccionadas se muestran como criterio base; el campo queda para criterios adicionales.
- Botones PDF en Auditorías (plan, actas, listas, informe) y selector de programa anual con su PDF.

---

## 0.1.8 — 2026-10-07 · M12 Competencia técnica

**Migración:** sí (`esynapse_sig 0034, 0035, 0036`).

- Módulo completo por pestañas: entrenamiento, supervisión, autorización y seguimiento; perfiles por cargo; catálogos de métodos y controles de validez.
- Tres PDF fieles a los formatos de autorización del personal técnico (r01, r02, r03); solo imprimen lo llenado; adjuntos por actividad visibles en pantalla pero no en el PDF.
- Función `esta_autorizado` para técnico autorizado y firma controlada (alcance por laboratorio).
- Candado de aprobación generalizado a varios módulos (campo `modulo`), con **devolver para corrección** y **reenviar**; bandeja en Equipos y Competencia; alertas de seguimiento en Mis tareas y Calendario.

---

## 0.1.7 — 2026-10-06 · Equipos: intervalo de calibración y trazabilidad

**Migración:** sí (`esynapse_sig 0031, 0032, 0033`).

- Intervalo de calibración como **matriz años × puntos** (OIML D10) con guardado explícito, celdas en blanco y EMP prellenado del año anterior; PDF alineado al formato r08.
- Pestaña "Carta de trazabilidad" (antes "Trazabilidad") reordenada; nodos con varios padres, nivel y categoría; PDF r04.
- Candado de aprobación extendido a intervalo, carta, alta/baja de equipos y bitácoras.

---

## 0.1.0 – 0.1.6 — junio 2026 · Fases 0, 1 y 2 (parcial)

- **Fase 0**: proyecto Django + React, usuario personalizado, roles y permisos granulares por módulo y operación, middleware de auditoría, JWT, dashboard con sidebar, login, CRUD de usuarios, configuración de marca y licenciamiento por módulos.
- **Fase 1 — SIG Core**: M6 Documentos (versiones, aprobación con firma y segundo factor, documentos externos, archivado, firma PAdES), M8 Hallazgos (correlativos por tipo, ciclo y reapertura), M9 Acciones correctivas (causa raíz, plan, eficacia), M10 Auditorías (programa, planificación, checklists, informe).
- **Fase 2 — Laboratorio**: M13 Equipos (hoja de vida, bitácoras, programa anual, movimientos, informes, inventario; PDF r01–r09).
- Reconstrucción de la base de desarrollo el 24-06-2026 tras corrupción por accesos concurrentes.
