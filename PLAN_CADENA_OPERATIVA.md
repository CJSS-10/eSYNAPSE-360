# Plan de traslado de la cadena operativa a eSYNAPSE 360

**Documento de diseño DD-03** · Versión 0.1 · 10 de octubre de 2026 · Estado: aprobado para construcción
**Origen:** `Sistema Metrindust` (DD-01 Modelo de procesos, DD-02 Arquitectura), ajustado con las respuestas de César del 10-10-2026.
**Alcance:** procesos P01–P11 (comercial → logística → laboratorio → entrega → facturación → cierre) implementados **dentro de eSYNAPSE 360** (Django + DRF + React), no como sistema aparte.

---

## 0. Decisión de fondo

El proyecto `Sistema Metrindust` (FastAPI + SQLAlchemy + Mantine) **no se migra como código**: se toma su **diseño** y se reimplementa sobre eSYNAPSE. Razones:

1. eSYNAPSE ya tiene lo que ese proyecto reconstruía desde cero: usuarios, roles, permisos, auditoría, configuración, documentos (M6), equipos y patrones con vigencia (M13), autorizaciones técnicas por método (M12).
2. La puerta de liberación de OT (G06) exige "técnico autorizado + patrón vigente": en eSYNAPSE se resuelve consultando M12 y M13 directamente. En un sistema separado habría que duplicar esos maestros.
3. La trazabilidad SIG ↔ operación (un trabajo no conforme termina en Hallazgos M8 y Acciones Correctivas M9) solo existe si todo vive en el mismo sistema.

Lo que **sí** se adopta del proyecto anterior, como reglas de arquitectura en Django:

| Regla | Qué significa en eSYNAPSE |
|---|---|
| Expediente como agregación | Todo objeto operativo lleva `expediente` (FK). La cronología se arma desde eventos, no desde texto. |
| Máquinas de estado explícitas | Nada cambia `estado` con un `PATCH` suelto. Cada objeto tiene transiciones permitidas, cada transición valida su puerta, exige actor y motivo, y escribe el evento en la misma transacción. |
| Eventos append-only | Tabla de eventos de dominio sin edición ni borrado (complementa el log de auditoría actual). |
| Maestros versionados por vigencia | Tarifas, catálogo de servicios, métodos y plantillas con `vigente_desde / vigente_hasta`. El expediente guarda **la versión usada**. |
| Puertas con prueba | Toda puerta Gnn tiene al menos una prueba automática que la hace fallar. |

---

## 1. Decisiones fijadas (respuestas del 10-10-2026)

| ID | Decisión | Consecuencia de diseño |
|---|---|---|
| **D-01** | **Una OT agrupa varios equipos, incluso de distintos laboratorios.** Reemplaza al DD-03 anterior ("una OT por equipo"). | La OT es el contenedor; la unidad de trabajo es la **línea OT-equipo-laboratorio**. Cada metrólogo ve solo las líneas de su laboratorio. |
| **D-02** | La OT hereda la **fecha de compromiso** de la cotización, validada en la nota de pedido. | `fecha_compromiso` viaja cotización → NP → OT. Cambiarla exige motivo y queda en historial. |
| **D-03** | La OT se **completa cuando todas sus líneas están cerradas**. No hay cierre parcial de OT, pero sí entrega parcial de equipos. | Estado de OT derivado del menos avanzado de sus líneas. |
| **D-04** | **Un certificado por equipo y por parámetro.** Un equipo calibrado en dos laboratorios genera dos certificados. | Certificado ↔ línea OT (1:1). OT ↔ certificados (1:N). |
| **D-05** | Numeración de OT: `OT 0001-2026`, reinicio anual. | Secuencia por año en base de datos, nunca `MAX()+1`. |
| **D-06** | **Correlativo de documento técnico por tipo de servicio**, reinicio anual: `MT-00001-2026` calibración · `MP-0001-2026` mantenimiento preventivo · `MC-0001-2026` correctivo · `IT-0001-2026` informe técnico · otros configurables. | Catálogo de **series** administrable desde Configuración. El número se asigna **solo al emitir**; un borrador nunca consume número. |
| **D-07** | Revisor y firmante **distintos del ejecutor**, siempre. | Coincide con la regla 7 del CLAUDE.md: metrólogo elabora → encargado revisa → firmante autorizado firma. El sistema lo hace imposible de saltar. |
| **D-08** | Trabajo **en sitio frecuente (4–5 por semana) sin conexión**. | Captura de datos técnicos en **modo sin conexión** (PWA) con sincronización posterior. Es requisito, no mejora. |
| **D-09** | Correlativos de OT y certificado **arrancan desde cero** con el sistema. | Sin regla de coexistencia con numeración anterior. |
| **D-10** | Logística **mixta**: minivan, camión, motorizado, personal, cliente o courier por aplicativo. | `modalidad_traslado` y `transportista` por movimiento. |
| **D-11** | **Guías de remisión emitidas desde el sistema** (hoy en otro software). | Integración con SUNAT vía OSE/PSE por adaptador (proveedor por definir). Primero registro manual + PDF; luego emisión electrónica. |
| **D-12** | **Etiquetas térmicas** por equipo al recibirlo. | Generación de etiqueta (ZPL/PDF) con código del ítem y expediente, impresión desde el navegador. |
| **D-13** | Política de pago (anticipo, crédito) y **retención de certificado** varían por cliente; se definen más adelante. | Campos configurables por cliente con valores por defecto; la puerta G09 los lee. |
| **D-14** | Descuentos: hoy cada ejecutivo aprueba. | Sin regla de niveles por ahora; se registra quién aplicó el descuento. |
| **D-15** | Facturación **se construye en el sistema** (no Odoo, por ahora). | Comprobantes vía OSE/PSE, misma mecánica que las guías. Última fase. |
| **D-16** | **PostgreSQL desde ahora.** | Se migra eSYNAPSE antes de construir OT. Desarrollo y producción siguen separados. |
| **D-17** | **Firma PAdES desde el inicio** (ya existe en eSYNAPSE). | Cada firmante autorizado necesita su certificado digital (.p12). |

**Pendiente menor (P-01):** confirmar si dentro de la serie MT se distingue el certificado **acreditado** (símbolo INACAL) del **no acreditado**, o si es solo una marca en el documento. Propuesta: marca `acreditado` en la línea OT (heredada de la revisión de requisitos) que habilita el símbolo en la plantilla; la serie no cambia.

---

## 2. Mapa de procesos → módulos de eSYNAPSE

| Proceso (DD-01) | Módulo eSYNAPSE | App Django | Estado hoy |
|---|---|---|---|
| P01 Captar y calificar | **M24 CRM** | `comercial` (nueva) | No existe |
| P02 Revisar solicitud | M24 CRM + **Expediente** | `comercial` | No existe |
| P03 Cotizar y aceptar | M24 CRM | `comercial` | No existe |
| P04 Nota de pedido | M24 CRM | `comercial` | No existe |
| P05 Recibir y custodiar | **Logística** | `logistica` (nueva) | No existe |
| P06 Programar y liberar OT | **M25 OT** | `operaciones` (nueva) | No existe (usa M12, M13) |
| P07 Ejecutar trabajo técnico | M25 OT | `operaciones` | No existe (usa M14 Métodos, aún sin construir) |
| P08 Revisar y emitir documento | M25 OT (certificados) | `operaciones` | Firma PAdES existe en M6 |
| P09 Entregar | Logística | `logistica` | No existe |
| P10 Facturar y cobrar | **M30 Cobranzas** | `finanzas` (nueva) | No existe |
| P11 Cerrar y aprender | Expediente + M8/M9/M19 | `comercial` | M8/M9 existen |

Maestros nuevos en `core` o `comercial`: **Cliente**, **Contacto**, **Laboratorio** (hoy es texto libre en Usuario y Equipo; pasa a catálogo), **Catálogo de servicios** con **tarifas versionadas**, **Series de documentos**, **Transportistas**, **Ubicaciones**.

---

## 3. Modelo de objetos (ajustado a D-01 y D-04)

### 3.1 Expediente y comercial

```
Cliente ── Contacto
   │
Oportunidad (SOL-AAAA-NNNNN)  → al calificar crea →  Expediente (MET-SRV-AAAA-NNNNN)
                                                          │
                                   ┌──────────────────────┼──────────────────────┐
                              ItemPrevisto           Cotizacion (COT NNNN-AAAA)   NotaPedido (NP NNNN-AAAA)
                              (revisión de           ├─ CotizacionRevision Rn      ├─ NotaPedidoLinea
                               requisitos por ítem)  └─ CotizacionLinea            └─ fecha_compromiso ✔
```

- **Expediente**: pocas columnas (código, cliente, responsable, estado, prioridad, modalidad laboratorio/en sitio, sede, fechas). Todo lo demás apunta a él.
- **ItemPrevisto** (P02): por cada equipo previsto, decisión: magnitud → laboratorio → método vigente → acreditado / no acreditado / subcontratado / no factible → **esta decisión viaja hasta el certificado**.
- **Cotización** con revisiones; solo una activa; la revisión fija la **tarifa vigente a su fecha**.
- **Nota de pedido**: confirma líneas aceptadas, orden de compra, condiciones de pago, modalidad y **fecha de compromiso**. Sin NP no hay recepción ni OT.

### 3.2 Logística de entrada

```
NotaPedido ─► GuiaIngreso (nº del cliente o propia) ─► ActaRecepcion ─► Item (recibido)
                                                                          ├─ EquipoCliente (histórico: marca/modelo/serie)
                                                                          ├─ Etiqueta (térmica)
                                                                          ├─ Ubicacion + Movimiento (cada traslado)
                                                                          └─ condición: aceptado / condicionado / cuarentena
```

### 3.3 Orden de trabajo (D-01)

```
OrdenTrabajo (OT 0001-2026)
  ├─ nota_pedido, expediente, fecha_compromiso (heredada), estado derivado
  └─ LineaOT  (= un equipo en un laboratorio para un parámetro)
       ├─ item, laboratorio, magnitud/parámetro, metodo + versión
       ├─ tecnico (G06: M12.esta_autorizado), patrones previstos (G06: M13 vigente)
       ├─ acreditado (de ItemPrevisto)
       ├─ estado: pendiente → asignada → en_ejecucion → completada → en_revision → cerrada | observada
       ├─ RegistroTecnico v1, v2… (nunca sobrescribir) + UsoPatron (los realmente usados)
       └─ DocumentoTecnico (1:1) ── serie MT/MP/MC/IT ── nº solo al emitir ── PAdES
```

Reglas:
- Un equipo con dos parámetros = dos `LineaOT` (pueden ser de laboratorios distintos) = dos certificados.
- El metrólogo ve **solo las líneas de su laboratorio**; el coordinador ve la OT completa.
- La OT pasa a `completada` cuando **todas** sus líneas están `cerrada`. Un equipo puede entregarse cuando sus líneas están cerradas aunque la OT siga abierta (entrega parcial).
- `observada` devuelve la línea a ejecución con motivo; el registro anterior queda como versión.

### 3.4 Documento técnico

- `borrador → en_revision → aprobado → emitido → reemplazado | retirado`.
- Al **emitir**: toma el siguiente número de la **serie del tipo de servicio** y el año, congela los datos en JSON, genera PDF, calcula hash, **firma PAdES** con el certificado digital del firmante (regla 7: Gerente Técnico todos los laboratorios; encargado solo el suyo).
- Corrección después de emitido = **nuevo documento** con referencia al reemplazado; el anterior queda visible como inválido.

### 3.5 Logística de salida y cobranza

- **GuiaSalida** (GRE) por evento de entrega, con transportista y modalidad (D-10). Primero PDF propio; luego emisión electrónica vía adaptador OSE/PSE.
- **Entrega**: receptor, fecha/hora, evidencia (firma/foto). Regla 3 del CLAUDE.md: entrega y envío de certificado son eventos independientes; alerta si el certificado no se envió tras la entrega.
- **Factura** (CPE) N:M con expedientes mediante líneas; **Pago**; estado de cobranza independiente del expediente.

---

## 4. Puertas en términos de eSYNAPSE

| Puerta | Verifica | De dónde sale el dato |
|---|---|---|
| G01 | Cliente vigente, contacto con canal, necesidad descrita | Cliente, Contacto, Oportunidad |
| G02 | Todo ítem con laboratorio, método vigente y clasificación de alcance | ItemPrevisto + M14 Métodos (o catálogo provisional) |
| G03 | Cotización `aceptada` con evidencia escrita, vigencia no vencida | Cotización, adjunto |
| G04 | NP vigente ligada a cotización aceptada, fecha de compromiso, anticipo si la política del cliente lo exige | NotaPedido, Cliente.politica_pago |
| G05 | Ítem identificado, condición, foto, ubicación, acta; diferencias contra NP registradas | ActaRecepcion, Item |
| **G06** | Por línea: ítem trabajable, NP cubre el ítem, **técnico con autorización vigente** (M12), **patrones vigentes** (M13), método vigente | LineaOT → `esta_autorizado()` + `Equipo.calibracion_vigente` |
| G07 | Registro completo, patrones usados vigentes a la fecha, condiciones ambientales en rango o desviación justificada, firmado por el técnico | RegistroTecnico, UsoPatron |
| **G08** | Revisor autorizado en la magnitud, **revisor ≠ ejecutor**, checklist completo, serie coincide con tipo de servicio | DocumentoTecnico, M12 |
| G09 | Ítems cerrados o con excepción, accesorios conciliados, GRE emitida, pago registrado si el cliente lo exige | Entrega, Cliente.retiene_certificado |
| G10 | Hito facturable alcanzado, NP vigente, datos tributarios válidos, sin factura previa para las mismas líneas | Factura |
| G11 | Todo entregado o devuelto, documentos emitidos, factura aceptada o excepción, sin líneas abiertas | Expediente |

Segregaciones que el sistema hace imposibles: Comercial no edita resultados técnicos · el ejecutor no revisa ni firma su propio certificado · Administración no toca datos técnicos · Recepción no modifica cotizaciones.

---

## 5. Fases de construcción

Cada fase termina con algo demostrable en pantalla. Tiempos estimados con dedicación parcial alta.

| Fase | Contenido | Demostración de salida | Est. |
|---|---|---|---|
| **3.0 Cimientos operativos** | Migración a **PostgreSQL** (D-16). Maestros: Laboratorio (catálogo), Cliente, Contacto, Series de documentos, Ubicaciones, Transportistas. Máquina de estados genérica + eventos de dominio. Expediente con código y cronología. | Un expediente creado, transicionado y auditado desde la interfaz | 2–3 sem |
| **3.1 Comercial (M24)** | Oportunidad e interacciones · Revisión de requisitos por ítem (G02) · Catálogo y tarifas versionadas · Cotización con revisiones y PDF · Aceptación con evidencia (G03) · Nota de pedido con fecha de compromiso (G04) | Una cotización real emitida, aceptada y con NP | 4–5 sem |
| **3.2 Logística de entrada** | Recepción contra NP · Guía de ingreso · Acta · Equipo histórico del cliente · Inspección con fotos · Cuarentena · **Etiquetas térmicas** (D-12) · Ubicaciones y movimientos | Recepción real de un lote con etiquetas y acta | 3 sem |
| **3.3 OT y ejecución (M25)** | **OT general multi-laboratorio** con líneas por equipo/parámetro (D-01) · Vista por laboratorio para el metrólogo · G06 con M12/M13 · Registro técnico versionado + uso de patrones · **Modo sin conexión** para trabajo en sitio (D-08), que incluye el ATS en campo en el celular con firmas en pantalla (decisión del 2026-10-22; hoy el ATS de campo se lleva en papel y se adjunta) | Una OT real con equipos de dos laboratorios ejecutada, incluida una captura en sitio sin internet | 6–8 sem |
| **3.4 Certificados** | Series MT/MP/MC/IT (D-06) · Revisión con checklist y revisor ≠ ejecutor (G08) · Plantilla por tipo · Emisión con número, hash y **firma PAdES** (D-17) · Reemplazo y retiro controlados · Alerta "certificado no enviado tras entrega" | Un certificado real emitido y firmado digitalmente desde el sistema | 4–5 sem |
| **3.5 Logística de salida** | Preparación de despacho · **Guía de remisión desde el sistema** (D-11): PDF propio primero · Constancia de entrega · Retención por pago según cliente (D-13) · Custodia prolongada con alertas | Entrega real con guía y constancia | 3 sem |
| **3.6 Guías y facturas electrónicas** | Adaptador OSE/PSE (proveedor por definir) · Emisión electrónica de GRE · Facturas (D-15) con estados SUNAT · Pagos y cobranza (M30) · Políticas de pago por cliente | Guía y factura reales aceptadas por SUNAT | 4–5 sem |
| **3.7 Cierre y tableros** | Cierre con paquete de evidencia (G11) · Reclamos ligados al expediente (M18) · Indicadores operativos (M4) | Tablero usado en reunión semanal | 2–3 sem |

**Hito MVP = fin de la fase 3.5**: una solicitud real recorre P01→P09 completa en eSYNAPSE. A partir de ahí, un mes de operación en paralelo con el flujo actual antes de retirarlo.

**Motores de cálculo por método** (fórmulas de incertidumbre, etc.) se construyen **uno por uno después del MVP**, cada uno validado contra un certificado real reproducido dígito por dígito. El registro técnico genérico de la fase 3.3 ya guarda lecturas, patrones y condiciones; el cálculo específico se enchufa por método.

---

## 6. Lo que se reutiliza de eSYNAPSE sin tocar

| Existe hoy | Lo usa |
|---|---|
| Usuario, Rol, Permiso por módulo/operación | Todas las fases (permisos `comercial`, `logistica`, `ordenes_trabajo`, `cobranzas`) |
| Log de auditoría automático | Se complementa con eventos de dominio |
| M12 Competencia: `esta_autorizado(usuario, metodo, funcion, laboratorio)` | G06 (asignar técnico), G08 (revisor y firmante) |
| M13 Equipos: patrones con calibración vigente, hojas de vida | G06, G07 (uso de patrones), trazabilidad en el certificado |
| M6 Documentos: firma PAdES con endesive | Emisión del certificado |
| Candado de aprobación multi-módulo | Aprobación de cotizaciones, liberación de OT |
| Configuración del sistema (empresa, logo, firmas) | Cabecera de cotización, NP, acta, guía, certificado |
| Generación PDF con ReportLab | Todos los formatos operativos |
| M8 Hallazgos / M9 Acciones correctivas | Trabajo no conforme detectado en P07 o reclamo en P11 |

---

## 7. Decisiones aún abiertas

| ID | Pregunta | Bloquea |
|---|---|---|
| P-01 | Certificado acreditado vs. no acreditado dentro de la serie MT | Plantilla del certificado (fase 3.4) |
| P-02 | Proveedor OSE/PSE para guías y facturas electrónicas | Fase 3.6 |
| P-03 | Formato real del certificado de calibración y de la OT actual (archivos) | Plantillas de 3.3 y 3.4 — **se necesitan antes de empezar 3.3** |
| P-04 | Política de pago y retención por cliente (valores por defecto) | Fase 3.5 (puede arrancar con "crédito, no retiene") |
| P-05 | Inventario de métodos por laboratorio con versión vigente (M14 no está construido) | G02 y G06 pueden usar un catálogo provisional de métodos hasta construir M14 |

---

## 8. Siguiente paso

1. Confirmar este documento (en especial D-01 a D-08 y las fases).
2. Entregar los archivos de **P-03** (un certificado real y una OT real).
3. Arrancar **fase 3.0**: migración a PostgreSQL y maestros.
