# eSYNAPSE 360 — Flujos Detallados por Módulo

## Metrindust S.A.C.
## Documento de referencia para desarrollo — Versión 1.0

> Este documento describe paso a paso qué ocurre en cada actividad de cada módulo del SIGE: qué hace el usuario, qué hace el sistema automáticamente, qué queda registrado en el log de auditoría, y cómo se conecta con otros módulos.

---

## CONVENCIONES

- **[USUARIO]** — Acción que realiza el usuario manualmente
- **[SISTEMA]** — Acción automática del sistema sin intervención del usuario
- **[BLOQUEA]** — Validación que impide continuar si no se cumple
- **[LOG]** — Registro automático en el log de auditoría
- **[ALERTA]** — Notificación automática enviada al usuario o responsable
- **[API]** — Llamada a sistema externo

---

## CAPA 0 — ADMINISTRACIÓN DEL SISTEMA

---

### 0.1 Gestión de Usuarios

**Flujo: Crear usuario**
1. [USUARIO] Administrador accede a Configuración → Usuarios → Nuevo
2. [USUARIO] Completa: nombres, apellidos, email, área, laboratorio (si aplica), cargo, teléfono
3. [USUARIO] Asigna uno o más roles al usuario
4. [SISTEMA] Valida que el email no exista previamente en el sistema
5. [BLOQUEA] Si el email ya existe → error "Email ya registrado"
6. [SISTEMA] Genera contraseña temporal y envía correo de bienvenida al email
7. [SISTEMA] Crea el usuario con estado "Activo"
8. [LOG] Registra: quién creó el usuario, cuándo, desde qué IP, qué roles asignó

**Flujo: Desactivar usuario**
1. [USUARIO] Administrador selecciona usuario → Desactivar
2. [SISTEMA] Cambia estado a "Inactivo"
3. [SISTEMA] Invalida todas las sesiones activas del usuario inmediatamente
4. [SISTEMA] El usuario no puede volver a iniciar sesión
5. [SISTEMA] Todos sus registros históricos permanecen intactos y visibles
6. [LOG] Registra: quién desactivó, a quién, cuándo y motivo si se proporcionó
7. [BLOQUEA] No se puede eliminar físicamente un usuario — solo desactivar

**Reglas:**
- Un usuario desactivado NO puede ser asignado a nuevas OTs o tareas
- Sus registros históricos (OTs firmadas, documentos aprobados, etc.) permanecen con su nombre
- Si el usuario tiene tareas pendientes, el sistema alerta antes de desactivar

---

### 0.2 Roles y Permisos

**Flujo: Crear rol**
1. [USUARIO] Administrador → Roles → Nuevo rol
2. [USUARIO] Define nombre del rol (ej: "Metrólogo", "Encargado de Lab", "Comercial")
3. [USUARIO] Para cada módulo del sistema, selecciona las operaciones permitidas:
   - Leer: puede ver registros
   - Crear: puede crear nuevos registros
   - Editar: puede modificar registros existentes
   - Aprobar: puede aprobar flujos de trabajo
   - Eliminar: puede desactivar registros (soft delete)
4. [SISTEMA] Guarda el rol con sus permisos
5. [LOG] Registra la creación del rol y todos los permisos asignados

**Flujo: Asignar rol a usuario**
1. [USUARIO] Selecciona usuario → Editar → Roles
2. [USUARIO] Asigna uno o más roles
3. [SISTEMA] Aplica los permisos inmediatamente — si el usuario tiene sesión activa, los permisos se actualizan en tiempo real
4. [LOG] Registra: quién asignó, a quién, qué rol, cuándo

**Reglas:**
- Un usuario con múltiples roles tiene la UNIÓN de todos sus permisos
- El rol "Administrador del Sistema" no puede modificarse ni eliminarse
- Cambios en permisos de un rol afectan a todos los usuarios con ese rol instantáneamente
- La firma digital tiene su propia configuración de autorización independiente de los roles

---

### 0.3 Log de Auditoría

**Qué registra automáticamente (sin configuración):**
- Inicio y cierre de sesión (usuario, IP, dispositivo, timestamp)
- Creación de cualquier registro (entidad, campos, valores)
- Edición de cualquier campo (valor anterior → valor nuevo)
- Cambio de estado de cualquier registro
- Intentos de acceso bloqueados (sin permiso o credenciales incorrectas)
- Aprobaciones y rechazos en flujos de trabajo
- Firmas digitales aplicadas
- Exportaciones de datos (quién exportó qué y cuándo)
- Llamadas a APIs externas (Odoo, firma digital, etc.)

**Estructura de cada entrada del log:**
```
timestamp       : 2026-06-04 14:32:17 UTC
usuario_id      : 42
usuario_nombre  : Juan Pérez
rol             : Metrólogo
ip              : 192.168.1.45
dispositivo     : Chrome 124 / Windows 11
modulo          : ordenes_trabajo
accion          : EDITAR
entidad         : OTItem
entidad_id      : 8821
campo           : resultado_calibracion
valor_anterior  : null
valor_nuevo     : conforme
referencia      : OT-2026-4021
```

**Reglas:**
- El log es INMUTABLE — ningún usuario, incluido el administrador, puede editar o eliminar entradas
- Retención mínima: 5 años
- Solo accesible por administradores del sistema
- Exportable a PDF o Excel para presentar en auditorías

---

### 0.4 Firma Digital Controlada

**Flujo: Firmar un certificado**
1. [SISTEMA] Cuando el certificado llega al estado "Listo para firma", notifica al firmante autorizado del laboratorio correspondiente
2. [USUARIO] Firmante autorizado recibe notificación y accede al certificado
3. [SISTEMA] Verifica que el usuario tiene autorización de firma para ese laboratorio específico
4. [BLOQUEA] Si el usuario no tiene autorización para ese laboratorio → error y log del intento
5. [USUARIO] Revisa el certificado completo
6. [USUARIO] Ingresa su contraseña como segundo factor de confirmación
7. [SISTEMA] Aplica la firma digital con: nombre del firmante, cargo, timestamp, hash del documento
8. [SISTEMA] Cambia estado del certificado a "Aprobado"
9. [LOG] Registra: quién firmó, qué certificado, cuándo, desde qué dispositivo, hash de la firma

**Reglas de autorización de firma:**
- Gerente Técnico → puede firmar certificados de TODOS los laboratorios
- Encargado de laboratorio → SOLO puede firmar certificados de su laboratorio asignado
- Nadie puede firmar usando credenciales de otra persona
- Si el firmante está desactivado → sus firmas previas son válidas, pero no puede firmar nuevas

---

## NIVEL 1 — PROCESOS ESTRATÉGICOS

---

### M1 — Planeamiento Estratégico

**Flujo: Crear plan estratégico**
1. [USUARIO] Gerencia accede a Planeamiento → Nuevo Plan
2. [USUARIO] Define: nombre del plan, período (ej: 2026-2028), responsable, fecha de aprobación esperada
3. [USUARIO] Registra Misión, Visión y Valores de la organización
4. [USUARIO] Crea análisis FODA:
   - Para cada ítem: tipo (F/O/D/A), descripción, prioridad (alta/media/baja)
5. [USUARIO] Define objetivos estratégicos vinculados a cada perspectiva del BSC:
   - Perspectiva financiera
   - Perspectiva de clientes
   - Perspectiva de procesos internos
   - Perspectiva de aprendizaje y crecimiento
6. [USUARIO] Para cada objetivo: descripción, indicador vinculado (→ M4), meta, responsable, plazo
7. [USUARIO] Envía el plan a aprobación
8. [SISTEMA] Cambia estado a "En revisión"
9. [USUARIO] Gerencia General aprueba
10. [SISTEMA] Cambia estado a "Aprobado" y activa el seguimiento automático
11. [LOG] Registra todo el proceso de creación y aprobación

**Flujo: Seguimiento de objetivos**
1. [SISTEMA] Calcula automáticamente el avance de cada objetivo desde los indicadores vinculados (M4)
2. [SISTEMA] Compara avance real vs meta programada
3. [SISTEMA] Si avance < 80% de lo esperado → genera alerta al responsable del objetivo
4. [SISTEMA] Si objetivo vencido sin cierre → genera alerta escalonada: responsable → gerencia
5. [USUARIO] Responsable registra acciones tomadas e hitos alcanzados
6. [LOG] Cada actualización de avance queda registrada

**Estados del Plan:**
```
Borrador → En revisión → Aprobado → En ejecución → Cerrado
```

**Automatizaciones:**
- El dashboard ejecutivo (M4) se alimenta automáticamente del plan estratégico
- Los cambios al plan aprobado generan solicitud en Gestión de Cambios (M17)
- Al final del período, el sistema genera alerta para iniciar el nuevo plan

---

### M2 — Gestión Legal y Cumplimiento

**Flujo: Registrar nuevo requisito legal**
1. [USUARIO] Área de calidad o legal accede a Legal → Nuevo Requisito
2. [USUARIO] Completa: norma, artículo, descripción, tipo (legal/regulatorio/contractual), fecha de publicación, fecha de vigencia
3. [USUARIO] Evalúa aplicabilidad: sí/no/parcial
4. [USUARIO] Si aplica: asigna responsable y define frecuencia de evaluación
5. [SISTEMA] Genera agenda de evaluaciones periódicas
6. [SISTEMA] Programa alertas de vencimiento: 30, 15 y 7 días antes
7. [LOG] Registra la creación del requisito

**Flujo: Evaluar cumplimiento**
1. [ALERTA] Sistema notifica al responsable que hay una evaluación programada
2. [USUARIO] Responsable accede al requisito → Evaluar
3. [USUARIO] Selecciona resultado: Cumple / Cumple parcialmente / No cumple / No aplica
4. [USUARIO] Adjunta evidencias (documentos, registros, capturas)
5. [USUARIO] Agrega observaciones
6. Si resultado = "No cumple":
   - [SISTEMA] Genera automáticamente un Hallazgo en M8
   - [SISTEMA] Vincula el hallazgo al requisito incumplido
   - [ALERTA] Notifica al jefe de área y al responsable de calidad
7. [SISTEMA] Registra la evaluación con fecha y responsable
8. [LOG] Registra quién evaluó, resultado, evidencias adjuntas

**Automatizaciones:**
- Alertas: 30d → responsable, 15d → responsable + jefe, 7d → responsable + jefe + gerencia
- Requisito vencido sin evaluación → bloquea el cierre del período en Revisión por la Dirección (M5)
- Cambios normativos detectados (ingresados manualmente) → alerta a todos los responsables afectados

---

### M3 — Gestión de Riesgos y Oportunidades

**Flujo: Identificar y evaluar riesgo**
1. [USUARIO] Accede a Riesgos → Nuevo Riesgo
2. [USUARIO] Completa: descripción, fuente, categoría (operacional/estratégico/legal/ambiental/SST), proceso vinculado (M7)
3. [USUARIO] Evalúa probabilidad (1-5) e impacto (1-5)
4. [SISTEMA] Calcula nivel de riesgo: Probabilidad × Impacto
   - 1-4: Bajo (verde)
   - 5-9: Medio (amarillo)
   - 10-16: Alto (naranja)
   - 17-25: Crítico (rojo)
5. Si nivel = Crítico:
   - [ALERTA] Notificación inmediata a la Gerencia General
   - [SISTEMA] Requiere plan de tratamiento en las próximas 48 horas
6. [USUARIO] Define controles: tipo (preventivo/detectivo/correctivo), descripción, responsable, plazo
7. [USUARIO] Guarda el riesgo
8. [LOG] Registra identificación, evaluación y controles definidos

**Flujo: Riesgo materializado**
1. [USUARIO] Marca el riesgo como "Materializado"
2. [SISTEMA] Genera automáticamente un Hallazgo en M8 vinculado al riesgo
3. [SISTEMA] El hallazgo hereda: proceso afectado, descripción del riesgo, responsable
4. [ALERTA] Notifica al responsable del proceso y a la gerencia
5. [LOG] Registra el evento de materialización

**Flujo: Monitoreo de controles**
1. [SISTEMA] Según frecuencia definida, genera tarea de revisión de eficacia del control
2. [ALERTA] Notifica al responsable del control
3. [USUARIO] Evalúa eficacia: Eficaz / Parcialmente eficaz / No eficaz
4. Si no eficaz → [SISTEMA] Genera hallazgo y requiere redefinir el control
5. [LOG] Registra cada revisión

---

### M4 — Indicadores y Dashboards BI

**Flujo: Crear indicador**
1. [USUARIO] Accede a Indicadores → Nuevo
2. [USUARIO] Define: nombre, tipo (estratégico/operativo/proceso), descripción, fórmula, unidad de medida
3. [USUARIO] Define fuente de datos:
   - Interna automática: el sistema calcula desde datos de otros módulos (ej: % OTs cerradas a tiempo)
   - Interna manual: el responsable ingresa el valor periódicamente
4. [USUARIO] Define: meta, frecuencia de medición, responsable, proceso vinculado (M7)
5. [USUARIO] Define umbrales de alerta: % amarillo, % rojo
6. [SISTEMA] Activa el indicador y comienza a medirlo según frecuencia

**Flujo: Medición automática (indicadores internos)**
1. [SISTEMA] Según frecuencia (diaria/semanal/mensual), calcula el valor desde la base de datos
2. [SISTEMA] Compara el valor con la meta y umbrales
3. [SISTEMA] Actualiza el estado: En meta (verde) / En alerta (amarillo) / Crítico (rojo)
4. Si estado = Amarillo → [ALERTA] Notifica al responsable
5. Si estado = Rojo → [ALERTA] Notifica al responsable y al jefe de área
6. Si estado = Rojo por 2 períodos consecutivos → [SISTEMA] Genera hallazgo automático en M8
7. [LOG] Registra cada medición con valor, estado y timestamp

**Ejemplos de indicadores automáticos:**
- % OTs entregadas a tiempo (desde M25)
- % Certificados con reproceso (desde M25)
- % Hallazgos cerrados en plazo (desde M8)
- % Acciones correctivas eficaces (desde M9)
- Días promedio de cobranza (desde M30)
- % Equipos con calibración vigente (desde M13)
- Índice de satisfacción del cliente (desde M18)
- % Documentos vigentes vs vencidos (desde M6)

**Flujo: Dashboard ejecutivo**
1. [SISTEMA] Consolida indicadores en tiempo real en el dashboard
2. [USUARIO] Gerencia ve: KPIs con semáforos, tendencias, gráficos comparativos
3. [USUARIO] Puede filtrar por período, área, proceso
4. [USUARIO] Puede exportar a PDF o Excel para reportes
5. [SISTEMA] Alimenta automáticamente la Revisión por la Dirección (M5)

---

### M5 — Revisión por la Dirección

**Flujo: Preparar y ejecutar revisión**
1. [USUARIO] Programa la revisión: fecha, participantes, período a revisar
2. [SISTEMA] Genera automáticamente el informe de entrada consolidando:
   - Estado de indicadores del período (M4)
   - Resultados de auditorías (M10)
   - Estado de hallazgos y AC (M8, M9)
   - Estado de riesgos (M3)
   - Quejas y satisfacción del cliente (M18)
   - Estado del cumplimiento normativo (M11)
   - Cambios internos y externos relevantes (M17)
   - Resultados de ensayos de aptitud (M15)
   - Estado de recursos y competencias (M12, M21)
3. [ALERTA] Notifica a los participantes con el informe adjunto
4. [USUARIO] Ejecuta la reunión
5. [USUARIO] Registra decisiones y acuerdos: descripción, responsable, plazo, prioridad
6. [USUARIO] Aprueba el acta
7. [SISTEMA] Genera plan de seguimiento de decisiones
8. [ALERTA] Notifica a cada responsable de decisión
9. Si decisión implica cambio en proceso → [SISTEMA] Genera solicitud en M17

**Flujo: Seguimiento de decisiones**
1. [SISTEMA] Monitorea el cumplimiento de cada decisión según su plazo
2. [ALERTA] 7 días antes del plazo → alerta al responsable
3. [ALERTA] Al vencimiento sin cumplimiento → alerta escalonada
4. [USUARIO] Responsable marca la decisión como cumplida y adjunta evidencia
5. [LOG] Registra el cumplimiento con fecha y evidencia

---

## NIVEL 2 — PROCESOS OPERATIVOS

---

## BLOQUE A — SGI CORE

---

### M6 — Gestión Documental

**Flujo: Crear documento nuevo**
1. [USUARIO] Accede a Documentos → Nuevo
2. [USUARIO] Completa: código, título, tipo (procedimiento/instructivo/formato/registro/plan/manual/política), proceso vinculado
3. [USUARIO] Sube el archivo (PDF, DOCX, XLSX)
4. [USUARIO] Completa metadatos: objetivo, alcance, responsable de elaboración
5. [SISTEMA] Asigna versión "1.0" automáticamente
6. [SISTEMA] Crea el flujo de aprobación según el tipo de documento:
   - Elaborado por → Revisado por → Aprobado por
7. [SISTEMA] Cambia estado a "Borrador"
8. [LOG] Registra creación con usuario, timestamp y archivo

**Flujo: Revisión y aprobación**
1. [ALERTA] El sistema notifica al revisor que tiene un documento pendiente
2. [USUARIO] Revisor accede al documento, lo lee
3. [USUARIO] Aprueba la revisión con comentarios opcionales
4. [ALERTA] Sistema notifica al aprobador
5. [USUARIO] Aprobador lee el documento
6. [USUARIO] Aprueba → aplica firma digital
7. [SISTEMA] Cambia estado a "Vigente"
8. [SISTEMA] Asigna fecha de vigencia y fecha de próxima revisión
9. [SISTEMA] Notifica a todos los usuarios del proceso vinculado que hay un nuevo documento vigente
10. [LOG] Registra cada paso del flujo con usuario y timestamp

**Flujo: Actualizar documento vigente**
1. [USUARIO] Accede al documento vigente → Crear nueva versión
2. [BLOQUEA] No se puede editar directamente un documento vigente
3. [SISTEMA] Crea una copia con versión "2.0" (o la siguiente)
4. [SISTEMA] El documento original sigue vigente hasta que la nueva versión sea aprobada
5. [USUARIO] Edita el documento, sube el nuevo archivo, registra resumen de cambios
6. [SISTEMA] Inicia el mismo flujo de revisión y aprobación
7. Cuando la nueva versión es aprobada:
   - [SISTEMA] La versión anterior cambia a estado "Obsoleto"
   - [SISTEMA] La nueva versión pasa a "Vigente"
   - [ALERTA] Notifica al proceso vinculado del cambio de versión
8. [LOG] Registra el historial completo de versiones

**Flujo: Alertas de vencimiento**
1. [SISTEMA] Monitoria las fechas de próxima revisión de todos los documentos vigentes
2. [ALERTA] 30 días antes → alerta al responsable del documento
3. [ALERTA] 15 días antes → alerta al responsable + encargado del proceso
4. [ALERTA] 7 días antes → alerta al responsable + encargado + gerencia de calidad
5. [ALERTA] Documento vencido → estado cambia a "Por vencer" y se bloquea su uso en nuevas OTs
6. [LOG] Registra el vencimiento y las alertas enviadas

**Reglas críticas:**
- Documentos obsoletos NO se eliminan — se conservan con historial completo
- Un documento que no ha pasado por aprobación NO puede ser referenciado en OTs ni procedimientos
- La búsqueda siempre muestra la versión vigente por defecto; versiones anteriores accesibles bajo "Historial"

---

### M7 — Gestión de Procesos

**Flujo: Crear proceso en el mapa**
1. [USUARIO] Accede a Procesos → Nuevo Proceso
2. [USUARIO] Define: código, nombre, tipo (estratégico/operativo/soporte), objetivo, alcance
3. [USUARIO] Asigna dueño del proceso
4. [USUARIO] Completa la caracterización:
   - Entradas (qué recibe el proceso)
   - Salidas (qué entrega el proceso)
   - Proveedores internos (procesos que le envían entradas)
   - Clientes internos (procesos que reciben sus salidas)
   - Recursos necesarios
5. [USUARIO] Vincula documentos del proceso (procedimientos, instructivos, formatos)
6. [USUARIO] Vincula indicadores de desempeño (M4)
7. [USUARIO] Vincula riesgos identificados (M3)
8. [SISTEMA] Publica el proceso en el mapa de procesos
9. [LOG] Registra la creación

**Flujo: Actualización del proceso**
1. [USUARIO] Dueño del proceso detecta necesidad de cambio
2. [USUARIO] Registra el cambio propuesto con justificación
3. [SISTEMA] Genera solicitud de cambio en M17 (Gestión de Cambios)
4. Una vez aprobado el cambio:
5. [USUARIO] Actualiza la caracterización del proceso
6. [SISTEMA] Actualiza automáticamente las vinculaciones (documentos, indicadores, riesgos)
7. [ALERTA] Notifica a todos los usuarios del proceso
8. [LOG] Registra el cambio con versión anterior y nueva

---

### M8 — Hallazgos

**Flujo: Registrar hallazgo manualmente**
1. [USUARIO] Accede a Hallazgos → Nuevo
2. [USUARIO] Selecciona tipo: NC Mayor / NC Menor / Observación / Oportunidad de Mejora
3. [USUARIO] Selecciona fuente: Auditoría interna / Auditoría externa / Inspección / Queja / Seguimiento / Indicador / Riesgo materializado / Otro
4. [USUARIO] Vincula al proceso afectado (M7)
5. [USUARIO] Vincula al requisito normativo incumplido si aplica (M11)
6. [USUARIO] Describe el hallazgo con detalle: qué se detectó, dónde, cuándo
7. [USUARIO] Adjunta evidencias: fotos, documentos, registros (→ Centro de Evidencias)
8. [SISTEMA] Asigna código correlativo automático (ej: NC-2026-089)
9. [SISTEMA] Cambia estado a "Registrado"
10. [ALERTA] Notifica al dueño del proceso afectado
11. Si tipo = NC Mayor → [SISTEMA] Genera automáticamente una Acción Correctiva (M9)
12. [LOG] Registra creación con todos los campos

**Flujo: Hallazgo generado automáticamente**
El sistema genera hallazgos automáticamente desde múltiples fuentes:

| Fuente | Disparador |
|--------|-----------|
| M4 Indicadores | Indicador en estado Crítico por 2 períodos consecutivos |
| M3 Riesgos | Riesgo marcado como materializado |
| M2 Legal | Evaluación de cumplimiento resulta "No cumple" |
| M10 Auditorías | Hallazgo registrado durante la ejecución de auditoría |
| M18 Quejas | Queja relacionada con resultados técnicos |
| M13 Equipos | Verificación intermedia resulta no conforme |
| M15 Ensayos | Resultado de ensayo de aptitud insatisfactorio |

En todos los casos:
- [SISTEMA] Crea el hallazgo con la fuente identificada y referencia al registro origen
- [SISTEMA] Vincula automáticamente al proceso afectado
- [ALERTA] Notifica al responsable del proceso y a calidad

**Flujo: Seguimiento y cierre**
1. Responsable recibe notificación
2. [USUARIO] Analiza el hallazgo y define si requiere corrección inmediata o AC
3. [USUARIO] Para NC Menores sin AC: registra la corrección realizada y evidencia
4. [SISTEMA] Si hay AC vinculada → el hallazgo no puede cerrarse hasta que la AC esté verificada como eficaz
5. [USUARIO] Una vez resuelta la causa → solicita cierre del hallazgo
6. [USUARIO] Responsable de calidad verifica el cierre
7. [SISTEMA] Cambia estado a "Cerrado"
8. [LOG] Registra todo el ciclo de vida del hallazgo

**Estados:**
```
Registrado → En análisis → Acción asignada → En seguimiento → Verificado → Cerrado
                                                                          → Reabierto (si AC no es eficaz)
```

---

### M9 — Acciones Correctivas

**Flujo completo: De la apertura al cierre**

**ETAPA 1: Apertura**
1. [SISTEMA] AC generada automáticamente desde NC Mayor, o
1. [USUARIO] AC creada manualmente desde un hallazgo
2. [SISTEMA] Asigna código correlativo (ej: AC-2026-034)
3. [SISTEMA] Vincula la AC al hallazgo de origen
4. [USUARIO] Asigna responsable de la AC y fecha límite de análisis
5. [ALERTA] Notifica al responsable
6. [LOG] Registra apertura

**ETAPA 2: Análisis de causa raíz**
1. [USUARIO] Responsable accede a la AC → Análisis de causa raíz
2. [USUARIO] Selecciona método: 5 Porqués / Ishikawa (diagrama de causa-efecto) / Otro
3. Si método = 5 Porqués:
   - [USUARIO] Registra el problema
   - [USUARIO] ¿Por qué ocurrió? (Causa 1)
   - [USUARIO] ¿Por qué ocurrió la causa 1? (Causa 2)
   - [USUARIO] Continúa hasta identificar la causa raíz (máximo 5 niveles)
4. Si método = Ishikawa:
   - [USUARIO] Define las 6M: Mano de obra, Máquina, Método, Material, Medición, Medio ambiente
   - [USUARIO] Para cada M, lista las causas posibles
   - [USUARIO] Identifica la causa raíz más probable
5. [BLOQUEA] No puede avanzar a definir el plan sin registrar la causa raíz
6. [LOG] Registra el análisis completo

**ETAPA 3: Plan de acción**
1. [USUARIO] Define las actividades del plan:
   - Para cada actividad: descripción, responsable, fecha límite, recursos necesarios
2. [BLOQUEA] El plan debe tener al menos UNA actividad con responsable y fecha
3. [USUARIO] Envía el plan para aprobación (si el flujo lo requiere)
4. [SISTEMA] Cambia estado a "Plan definido"
5. [ALERTA] Notifica a los responsables de cada actividad
6. [LOG] Registra el plan

**ETAPA 4: Ejecución**
1. [USUARIO] Cada responsable ejecuta su actividad
2. [USUARIO] Marca la actividad como completada y adjunta evidencia
3. [SISTEMA] Monitorea el avance del plan
4. [ALERTA] 3 días antes del plazo → alerta al responsable de la actividad
5. [ALERTA] Actividad vencida → alerta escalonada: responsable → jefe de área → gerencia de calidad
6. Cuando todas las actividades están completadas:
7. [SISTEMA] Cambia estado a "Ejecutada — pendiente verificación"
8. [ALERTA] Notifica al responsable de calidad para verificar eficacia

**ETAPA 5: Verificación de eficacia**
1. [BLOQUEA] La verificación debe realizarla una persona DIFERENTE al responsable de la AC
2. [USUARIO] Verificador accede a la AC → Verificar eficacia
3. [USUARIO] Evalúa si las acciones eliminaron la causa raíz
4. [USUARIO] Registra método de verificación, evidencias y conclusión
5. Si resultado = Eficaz:
   - [SISTEMA] Cambia estado de la AC a "Cerrada"
   - [SISTEMA] Cambia estado del hallazgo vinculado a "Cerrado"
   - [ALERTA] Notifica al responsable del proceso y a calidad
   - [SISTEMA] Sugiere registrar lección aprendida en M19
6. Si resultado = No eficaz:
   - [SISTEMA] Cambia estado a "Reabierta"
   - [ALERTA] Notifica al responsable con urgencia
   - [USUARIO] Se requiere nuevo análisis de causa raíz
   - [LOG] Registra el resultado de la verificación y la reapertura

**Automatizaciones:**
- El % de AC eficaces al primer intento es un indicador automático en M4
- El tiempo promedio de cierre de AC es un indicador automático en M4
- AC con más de 2 reaperturas genera alerta especial a la gerencia

---

### M10 — Auditorías

**Flujo: Programa anual de auditorías**
1. [USUARIO] Responsable de calidad accede a Auditorías → Programa Anual → Nuevo
2. [USUARIO] Define el período y los criterios para seleccionar qué auditar:
   - Todos los procesos deben auditarse al menos una vez al año
   - Normas: ISO 9001, ISO 14001, ISO 45001, ISO/IEC 17025
3. [USUARIO] Crea las auditorías planificadas: proceso a auditar, norma, trimestre, duración estimada
4. [USUARIO] Envía el programa a aprobación de la gerencia
5. [SISTEMA] Guarda el programa y programa alertas trimestrales
6. [LOG] Registra la creación del programa

**Flujo: Planificar auditoría específica**
1. [ALERTA] 30 días antes de la auditoría programada, el sistema recuerda al responsable
2. [USUARIO] Responsable de calidad accede a la auditoría → Planificar
3. [USUARIO] Asigna auditor líder y equipo auditor
4. [BLOQUEA] El auditor NO puede auditar el proceso del que es responsable
5. [USUARIO] Define fechas y horarios de ejecución
6. [USUARIO] Crea o selecciona checklists según la norma y el proceso
7. [SISTEMA] Configura los checklists con los requisitos aplicables
8. [USUARIO] Notifica al dueño del proceso auditado
9. [LOG] Registra la planificación

**Flujo: Ejecutar auditoría**
1. [USUARIO] Auditor accede a la auditoría → Ejecutar
2. Para cada ítem del checklist:
   - [USUARIO] Evalúa: Cumple / No cumple / No aplica / Oportunidad de mejora
   - [USUARIO] Registra evidencias: entrevistas realizadas, documentos revisados, registros verificados
   - Si resultado = No cumple:
     - [USUARIO] Describe el hallazgo en detalle
     - [USUARIO] Adjunta evidencia fotográfica o documental
     - [SISTEMA] Crea automáticamente un registro en M8 (Hallazgos)
     - [SISTEMA] Vincula el hallazgo a esta auditoría
3. [USUARIO] Completa el informe de auditoría:
   - Resumen ejecutivo
   - Fortalezas detectadas
   - Hallazgos (NC y observaciones)
   - Conclusiones
   - Recomendaciones
4. [USUARIO] Firma el informe como auditor líder
5. [SISTEMA] Cambia estado a "Informe elaborado"
6. [ALERTA] Notifica al dueño del proceso auditado

**Flujo: Seguimiento post-auditoría**
1. [SISTEMA] Monitorea el estado de los hallazgos generados en la auditoría
2. [BLOQUEA] La auditoría no puede cerrarse si quedan hallazgos sin AC asignada
3. [USUARIO] Una vez todas las AC están en curso → cierra la auditoría formalmente
4. [SISTEMA] Alimenta el informe de Revisión por la Dirección (M5) automáticamente
5. [LOG] Registra todo el ciclo

---

### M11 — Cumplimiento Normativo

**Flujo: Configurar la matriz maestra**
1. [USUARIO] Responsable de calidad configura las normas aplicables:
   - ISO 9001:2015 (cláusulas 4-10)
   - ISO 14001:2015 (cláusulas 4-10)
   - ISO 45001:2018 (cláusulas 4-10)
   - ISO/IEC 17025:2017 (secciones 4-8)
   - Ley 29783 (artículos aplicables)
2. [USUARIO] Para cada requisito: vincula el proceso que lo implementa, los documentos que lo evidencian, los registros que lo soportan, los indicadores que miden su eficacia
3. [SISTEMA] Genera la matriz con el estado de cada requisito
4. El % de requisitos cumplidos se publica automáticamente como indicador (M4)

**Flujo: Evaluación de cumplimiento**
1. [SISTEMA] Genera agenda de evaluaciones (mínimo anual, o antes de auditorías externas)
2. [ALERTA] Notifica al responsable de cada cláusula/requisito
3. [USUARIO] Evalúa el estado: Cumplido / Parcialmente cumplido / No cumplido / No aplica
4. [USUARIO] Adjunta evidencias
5. Si resultado = "No cumplido" → [SISTEMA] Genera hallazgo en M8 automáticamente
6. [SISTEMA] Actualiza el % global de cumplimiento por norma
7. [LOG] Registra la evaluación

---

### M17 — Gestión de Cambios

**Flujo: Solicitar cambio**
1. [USUARIO] Cualquier usuario puede solicitar un cambio desde cualquier módulo
2. [USUARIO] Completa: descripción del cambio, justificación, módulo/entidad afectada, urgencia
3. [SISTEMA] Crea la solicitud con código correlativo
4. [ALERTA] Notifica al responsable de calidad para evaluación
5. [LOG] Registra la solicitud

**Flujo: Evaluar impacto**
1. [USUARIO] Responsable de calidad evalúa el impacto:
   - Procesos afectados
   - Normas afectadas (¿cambia el alcance de acreditación?)
   - Riesgos del cambio
   - Recursos necesarios
2. Si el cambio afecta el alcance de acreditación (17025):
   - [BLOQUEA] Requiere aprobación del Director Técnico además de la gerencia
3. [USUARIO] Define plan de implementación: actividades, responsables, cronograma
4. [USUARIO] Envía a aprobación
5. [USUARIO] Gerencia aprueba o rechaza con justificación
6. [LOG] Registra la evaluación y decisión

**Flujo: Implementar y verificar**
1. [USUARIO] Responsable implementa el cambio según el plan
2. [USUARIO] Marca actividades completadas
3. Si el cambio modifica un documento → [SISTEMA] Genera nueva versión en M6
4. Si el cambio modifica un proceso → [SISTEMA] Actualiza la caracterización en M7
5. Si el cambio modifica un método de calibración → [SISTEMA] Requiere nueva validación en M14
6. [USUARIO] Verificador confirma que el cambio fue implementado correctamente
7. [SISTEMA] Cierra la solicitud de cambio
8. [LOG] Registra todo el proceso

---

### M18 — Quejas, Reclamos y Satisfacción

**Flujo: Registrar queja**
1. [USUARIO] Comercial o calidad registra la queja (puede venir por cualquier canal)
2. [USUARIO] Completa: cliente, canal (email/teléfono/presencial/portal), descripción, categoría, prioridad
3. [USUARIO] Si la queja está relacionada con una OT específica → la vincula
4. [SISTEMA] Asigna código correlativo
5. [SISTEMA] Envía acuse de recibo automático al cliente (si tiene email registrado)
6. [ALERTA] Notifica al responsable designado para investigar
7. Si la queja es sobre resultados de calibración → [SISTEMA] Genera TNC en M16
8. [LOG] Registra la queja

**Flujo: Investigar y resolver**
1. [USUARIO] Responsable investiga: qué ocurrió, por qué, impacto en el cliente
2. [USUARIO] Define acciones: corrección inmediata y/o AC (→ M9)
3. [USUARIO] Documenta la respuesta al cliente
4. [USUARIO] Registra el envío de la respuesta con fecha
5. [USUARIO] Verifica que el cliente quedó conforme
6. [SISTEMA] Cierra la queja
7. [LOG] Registra todo el proceso

**Flujo: Encuesta de satisfacción**
1. Cuando una OT es entregada (logística registra la devolución):
2. [SISTEMA] Genera automáticamente una encuesta de satisfacción
3. [SISTEMA] Envía la encuesta al cliente por email o disponible en el portal
4. [SISTEMA] Espera respuesta por 15 días
5. Si el cliente responde:
   - [SISTEMA] Registra la puntuación y comentarios
   - Si puntuación < umbral definido → [ALERTA] Notifica al responsable comercial
6. [SISTEMA] Calcula el índice de satisfacción mensual como indicador en M4

---

### M19 — Gestión del Conocimiento

**Flujo: Registrar lección aprendida**
1. Al cerrar una AC eficazmente:
   - [SISTEMA] Sugiere al responsable registrar una lección aprendida
2. [USUARIO] Accede a Conocimiento → Nueva Lección
3. [USUARIO] Completa: fuente (qué AC u evento la originó), contexto, descripción del problema, solución aplicada, recomendación para el futuro, proceso vinculado
4. [SISTEMA] Vincula automáticamente a la AC o auditoría de origen
5. [USUARIO] Publica la lección (queda disponible para todo el personal autorizado)
6. [LOG] Registra la publicación

**Flujo: Registrar caso técnico**
1. [USUARIO] Técnico o encargado de lab accede a Conocimiento → Nuevo Caso Técnico
2. [USUARIO] Completa: tipo de equipo, problema encontrado, diagnóstico, solución aplicada
3. [SISTEMA] El caso queda en estado "Borrador — pendiente validación"
4. [USUARIO] Técnico senior o encargado valida el caso
5. [SISTEMA] Publica el caso en la base de conocimiento
6. [LOG] Registra la validación y publicación

---

## BLOQUE B — LABORATORIO ISO/IEC 17025

---

### M12 — Competencia Técnica

**Flujo: Registrar perfil de competencia**
1. [USUARIO] Director Técnico define el perfil de competencia por cargo técnico:
   - Requisitos de educación (título, especialidad)
   - Requisitos de experiencia (años, tipo)
   - Competencias técnicas por magnitud y método
   - Formaciones obligatorias
2. [USUARIO] Asocia el perfil al cargo en el organigrama
3. [LOG] Registra la creación del perfil

**Flujo: Evaluar y autorizar técnico**
1. [USUARIO] Director Técnico o encargado de lab accede a Competencia → Nuevo Registro
2. [USUARIO] Selecciona el técnico a evaluar
3. [USUARIO] Selecciona el método/magnitud para el que se evalúa
4. [USUARIO] Registra la evaluación:
   - Tipo: Inicial / Periódica / Reentrenamiento
   - Método de evaluación: Examen escrito / Evaluación práctica supervisada / Ambos
   - Fecha de evaluación
   - Resultado: Competente / En formación / No competente
   - Evaluador (diferente al evaluado)
   - Evidencias: registros de evaluación, muestras de trabajo, observación directa
5. Si resultado = Competente:
   - [USUARIO] Emite la autorización formal
   - [USUARIO] Define fecha de vencimiento de la autorización
   - [SISTEMA] Registra la autorización activa
   - [SISTEMA] Actualiza la matriz de competencias
6. Si resultado = No competente:
   - [USUARIO] Define plan de formación y reentrenamiento
   - [SISTEMA] Registra como "En formación" — no puede ejecutar calibraciones del método
7. [LOG] Registra toda la evaluación

**Flujo: Alertas de vencimiento de autorización**
1. [SISTEMA] Monitorea las fechas de vencimiento de TODAS las autorizaciones activas
2. [ALERTA] 30 días antes → notifica al técnico y al encargado de lab
3. [ALERTA] 15 días antes → notifica al técnico + encargado + Director Técnico
4. [ALERTA] 7 días antes → notifica a todos + gerencia técnica
5. Al vencer:
   - [SISTEMA] Cambia estado de la autorización a "Vencida"
   - [SISTEMA] Bloquea automáticamente al técnico para nuevas asignaciones del método
   - [ALERTA] Alerta crítica a Director Técnico
6. [BLOQUEA] El sistema impide asignar el técnico a OTs del método si la autorización está vencida

**Flujo: Reentrenamiento**
1. [USUARIO] Director Técnico crea un plan de reentrenamiento
2. [USUARIO] Registra las actividades de formación: capacitaciones, práctica supervisada, etc.
3. [USUARIO] Al completar el reentrenamiento → realiza nueva evaluación
4. Si resultado = Competente → nueva autorización con fecha de vencimiento
5. [LOG] Registra todo el proceso de reentrenamiento

---

### M13 — Equipos e Instrumentos

**Flujo: Registrar equipo nuevo (patrón)**
1. [USUARIO] Accede a Equipos → Nuevo
2. [USUARIO] Completa la hoja de vida:
   - Código interno (asignado por el sistema, formato configurable)
   - Descripción, marca, modelo, número de serie
   - Magnitud que mide
   - Rango de medición
   - Resolución, exactitud
   - Ubicación (laboratorio, estante)
   - Responsable
   - Fecha de adquisición
   - Documentos asociados: manual, especificaciones del fabricante
3. [SISTEMA] Activa el equipo con estado "Activo — requiere calibración inicial"
4. [LOG] Registra la creación

**Flujo: Registrar calibración**
1. [USUARIO] Accede al equipo → Calibraciones → Nueva
2. [USUARIO] Completa:
   - Tipo: Interna / Externa
   - Si externa: laboratorio calibrador, número de certificado de calibración
   - Fecha de calibración
   - Fecha de vencimiento
   - Resultado: Conforme / No conforme (con observaciones)
   - Incertidumbre de calibración
   - Trazabilidad: patrón utilizado, certificado del patrón, trazabilidad hasta patrón nacional/internacional
3. [SISTEMA] Registra la calibración en el historial del equipo
4. [SISTEMA] Actualiza la fecha de vencimiento de calibración
5. [SISTEMA] Programa alertas de vencimiento
6. Si resultado = No conforme:
   - [SISTEMA] Cambia estado del equipo a "Fuera de servicio"
   - [SISTEMA] Genera hallazgo en M8
   - [SISTEMA] Evalúa el impacto en trabajos previos (ver flujo de impacto retroactivo)
7. [LOG] Registra la calibración

**Flujo: Verificación intermedia**
1. [SISTEMA] Según la frecuencia definida para cada equipo, genera tarea de verificación
2. [ALERTA] Notifica al responsable del equipo
3. [USUARIO] Ejecuta la verificación según el procedimiento establecido
4. [USUARIO] Registra: fecha, método, resultado de la verificación, criterio de aceptación, estado
5. Si resultado = Conforme:
   - [SISTEMA] Registra la verificación como satisfactoria
   - [SISTEMA] El equipo sigue disponible
6. Si resultado = No conforme:
   - [SISTEMA] Cambia estado del equipo a "Fuera de servicio"
   - [SISTEMA] Genera hallazgo en M8
   - [SISTEMA] Inicia evaluación de impacto retroactivo (ver abajo)
   - [ALERTA] Notifica urgente al Director Técnico y al encargado del lab
7. [LOG] Registra la verificación

**Flujo: Evaluación de impacto retroactivo (equipo fuera de tolerancia)**
Este flujo se activa cuando un equipo patrón es encontrado fuera de tolerancia:
1. [SISTEMA] Identifica la última verificación conforme del equipo
2. [SISTEMA] Busca TODAS las OTs donde se usó este equipo desde esa fecha hasta hoy
3. [SISTEMA] Lista las OTs afectadas con sus clientes y certificados
4. [SISTEMA] Genera un registro de Trabajo No Conforme (M16) vinculado a cada OT afectada
5. [ALERTA] Notifica urgente al Director Técnico con la lista de OTs afectadas
6. [USUARIO] Director Técnico evalúa el impacto real de cada OT
7. [USUARIO] Para cada OT define disposición: repetir calibración / emitir corrección / notificar al cliente

**Flujo: Mantenimiento**
1. [SISTEMA] Según el plan de mantenimiento, genera tarea preventiva
2. [ALERTA] Notifica al responsable del mantenimiento
3. [USUARIO] Ejecuta el mantenimiento
4. [USUARIO] Registra: tipo (preventivo/correctivo), descripción, resultado, materiales usados, próximo mantenimiento
5. [SISTEMA] Descuenta materiales del inventario (M28)
6. [LOG] Registra en el historial del equipo

**Alertas automáticas de calibración:**
- 30 días antes del vencimiento → técnico y encargado
- 15 días antes → técnico + encargado + Director Técnico
- 7 días antes → todos + gerencia
- Al vencer → bloqueo automático del equipo para nuevas OTs

---

### M14 — Métodos y Mediciones

**Flujo: Registrar y validar método nuevo**
1. [USUARIO] Director Técnico accede a Métodos → Nuevo
2. [USUARIO] Completa:
   - Código, nombre, norma de referencia (si aplica)
   - Magnitud, rango de aplicación
   - Tipo: calibración / verificación / ensayo
   - Indica si es del alcance de acreditación
3. [USUARIO] Registra la validación/verificación del método:
   - Parámetros evaluados: repetibilidad, reproducibilidad, exactitud, linealidad, etc.
   - Criterios de aceptación
   - Resultados obtenidos
   - Conclusión: Validado / Verificado
4. [BLOQUEA] Un método sin validación/verificación documentada no puede usarse en OTs
5. [USUARIO] Registra la estimación de incertidumbre:
   - Fuentes de incertidumbre identificadas
   - Modelo matemático
   - Cálculo de incertidumbre combinada y expandida
   - CMC (Capacidad de Medición y Calibración) del laboratorio
6. Si es del alcance de acreditación → requiere aprobación del Director Técnico con firma digital
7. [SISTEMA] Publica el método como "Aprobado — en uso"
8. [LOG] Registra todo el proceso

**Flujo: Cambio en método vigente**
1. [USUARIO] Se detecta necesidad de modificar un método en uso
2. [USUARIO] Crea solicitud en M17 (Gestión de Cambios)
3. Una vez aprobado el cambio:
4. [USUARIO] Actualiza el método: nueva versión con los cambios documentados
5. [USUARIO] Si los cambios son significativos → revalidación requerida
6. [SISTEMA] La versión anterior queda como "Obsoleta" pero conservada en historial
7. [ALERTA] Notifica a todos los técnicos autorizados para ese método
8. [LOG] Registra el cambio de versión

**Flujo: Registro de medición en OT**
Cuando se ejecuta una calibración en M25, el registro de medición incluye:
- OT y ítem de OT vinculados
- Método aplicado (versión específica)
- Equipos patrón utilizados (con sus calibraciones vigentes vinculadas)
- Técnico ejecutor (con su autorización vigente vinculada)
- Condiciones ambientales en el momento de la medición
- Lecturas obtenidas
- Valores de referencia
- Errores calculados
- Incertidumbre de medición reportada
- Resultado: conforme / no conforme

---

### M15 — Ensayos de Aptitud

**Flujo: Programar y participar en intercomparación**
1. [USUARIO] Director Técnico accede a Ensayos → Nuevo
2. [USUARIO] Define: proveedor del ensayo de aptitud, magnitud, método evaluado, ronda, fecha de participación
3. [USUARIO] Asigna técnico y equipo patrón para la ejecución
4. [SISTEMA] Registra la participación programada
5. [ALERTA] Notifica al técnico asignado de la fecha de ejecución

**Flujo: Ejecución y análisis de resultados**
1. [USUARIO] Técnico ejecuta la medición siguiendo el procedimiento normal
2. [USUARIO] Registra el valor reportado al proveedor y la incertidumbre
3. [USUARIO] Cuando llega el informe del proveedor:
   - Ingresa el valor de referencia asignado
   - Ingresa la incertidumbre del valor de referencia
4. [SISTEMA] Calcula automáticamente:
   - Z Score: z = (x - X) / σ donde x=valor reportado, X=valor referencia, σ=desviación estándar
   - Error normalizado: En = (x - X) / √(U²lab + U²ref)
5. [SISTEMA] Determina el resultado:
   - Z Score |z| ≤ 2: Satisfactorio
   - Z Score 2 < |z| ≤ 3: Cuestionable
   - Z Score |z| > 3: Insatisfactorio
   - En ≤ 1: Satisfactorio / En > 1: No satisfactorio
6. Si resultado = Insatisfactorio:
   - [SISTEMA] Genera hallazgo automático en M8
   - [ALERTA] Notifica urgente al Director Técnico
   - [SISTEMA] Requiere análisis de causa raíz y AC
7. Si resultado = Cuestionable:
   - [ALERTA] Notifica al Director Técnico para evaluación
   - [USUARIO] Director evalúa si se requiere AC preventiva
8. [SISTEMA] Registra el resultado en el historial del método
9. [SISTEMA] Analiza tendencias: si hay patrón de sesgo sistemático → alerta

---

### M16 — Trabajo No Conforme

**Flujo: Identificar trabajo no conforme**
Puede originarse de múltiples fuentes:
- Técnico detecta error durante la ejecución
- Verificación intermedia falla en equipo patrón ya usado
- Queja del cliente sobre un resultado
- Resultado insatisfactorio en ensayo de aptitud

1. [USUARIO/SISTEMA] Crea registro de TNC
2. [USUARIO] Describe: qué trabajo no cumplió, por qué, en qué etapa fue detectado (en proceso / post entrega)
3. [SISTEMA] Vincula automáticamente a la OT afectada
4. [SISTEMA] Genera hallazgo en M8

**Flujo: Evaluación de impacto**
1. [USUARIO] Director Técnico evalúa el alcance del impacto:
   - ¿Afecta solo esta OT o también OTs anteriores?
   - Si afecta OTs anteriores: ¿desde cuándo? (ej: si el equipo patrón falló, desde la última verificación conforme)
2. [SISTEMA] Si hay equipos involucrados → ejecuta flujo de impacto retroactivo (ver M13)
3. [USUARIO] Identifica todas las OTs y clientes afectados
4. [USUARIO] Define la disposición para cada OT afectada:
   - Repetir la calibración
   - Corregir el resultado y emitir certificado corregido
   - Anular el certificado
   - Informar al cliente para que tome decisión

**Flujo: Notificación al cliente**
1. Si el trabajo no conforme ya fue entregado al cliente:
2. [BLOQUEA] La notificación al cliente es OBLIGATORIA
3. [USUARIO] Redacta la notificación explicando: qué ocurrió, qué certificados están afectados, qué acción se tomará
4. [USUARIO] Envía la notificación (email + registro en el sistema)
5. [SISTEMA] Registra la fecha de envío y el contenido de la notificación
6. [LOG] Registra todo el proceso de notificación

**Flujo: Cierre del TNC**
1. [USUARIO] Ejecuta la disposición definida
2. [USUARIO] Verifica que se implementó correctamente
3. [SISTEMA] Cierra el TNC
4. [SISTEMA] El hallazgo vinculado progresa a través de M9 (AC)
5. [LOG] Registra el cierre

---

## BLOQUE C — SST Y MEDIO AMBIENTE

---

### M23 — Seguridad y Salud en el Trabajo

**Flujo: Identificación de peligros y evaluación de riesgos (IPERC)**
1. [USUARIO] Responsable SST accede a SST → IPERC → Nueva Evaluación
2. [USUARIO] Selecciona el área y el puesto de trabajo
3. [USUARIO] Para cada actividad del puesto:
   - Identifica el peligro
   - Describe el riesgo asociado
   - Evalúa probabilidad (1-3) y severidad (1-3)
   - Calcula el nivel de riesgo: P × S
   - Define controles según jerarquía: Eliminación / Sustitución / Control de ingeniería / Control administrativo / EPP
4. [SISTEMA] Clasifica el nivel de riesgo: Bajo/Medio/Alto/Crítico
5. Si riesgo = Crítico → [ALERTA] Notificación inmediata al jefe del área y gerencia
6. [USUARIO] Revisa y aprueba el IPERC
7. [SISTEMA] Publica el IPERC y programa revisión anual
8. [LOG] Registra

**Flujo: Registrar incidente o accidente**
1. [USUARIO] Responsable SST o supervisor registra el evento
2. [USUARIO] Completa:
   - Tipo: Incidente / Accidente / Casi accidente
   - Fecha, hora, lugar exacto
   - Descripción detallada
   - Persona involucrada (si hay lesionado)
   - Testigos
   - Causas inmediatas (condición/acto inseguro)
   - Causas básicas (factores personales/del trabajo)
   - Acciones inmediatas tomadas
   - Días perdidos (si accidente)
3. [SISTEMA] Asigna código correlativo
4. Si accidente mortal o incapacitante:
   - [ALERTA] Notificación urgente a gerencia
   - [SISTEMA] Genera alerta de obligación de notificación a SUNAFIL en 24h
5. [SISTEMA] Genera hallazgo en M8 automáticamente
6. [LOG] Registra el evento

**Flujo: Investigación de accidente**
1. [BLOQUEA] Todo accidente debe investigarse dentro de las 24 horas
2. [ALERTA] Sistema alerta si han pasado 24h sin investigación registrada
3. [USUARIO] Comité SST realiza la investigación
4. [USUARIO] Registra: causa raíz, factores contribuyentes, árbol de causas
5. [USUARIO] Define acciones correctivas → genera AC en M9
6. [USUARIO] Aprueba el informe de investigación
7. [LOG] Registra toda la investigación

**Flujo: Control de EPP**
1. [USUARIO] Responsable SST registra entrega de EPP al trabajador:
   - Tipo de EPP, talla, cantidad, fecha de entrega, fecha de vencimiento
2. [USUARIO] Trabajador firma la entrega mediante firma digital en el sistema
3. [SISTEMA] Registra en el legajo del trabajador
4. [ALERTA] EPP próximo a vencer → alerta al responsable SST para reposición
5. [BLOQUEA] Trabajador con EPP vencido genera alerta de restricción de acceso a área de riesgo
6. [LOG] Registra cada entrega de EPP

**Flujo: Vigilancia médica**
1. [USUARIO] RRHH o SST registra exámenes médicos:
   - Tipo: Ingreso / Periódico / Retiro
   - Fecha del examen
   - Resultado de aptitud: Apto / Apto con restricciones / No apto
   - Restricciones si aplica
   - Fecha del próximo examen
2. [ALERTA] 30 días antes del próximo examen → alerta al trabajador y RRHH
3. [ALERTA] Examen vencido → alerta a RRHH y al jefe directo
4. [LOG] Registra en el legajo del trabajador

---

### M22 — Medio Ambiente

**Flujo: Identificación de aspectos ambientales**
1. [USUARIO] Responsable de MA accede a MA → Aspectos → Nuevo
2. [USUARIO] Vincula al proceso que genera el aspecto (M7)
3. [USUARIO] Describe: actividad, aspecto ambiental (qué genera), impacto (qué efecto tiene)
4. [USUARIO] Define condición: Normal / Anormal / Emergencia
5. [USUARIO] Evalúa la significancia según los criterios definidos (frecuencia, severidad, normativa, partes interesadas)
6. Si aspecto es significativo:
   - [SISTEMA] Requiere definir controles operacionales
   - [USUARIO] Define controles: procedimientos, instructivos, monitoreo
7. [SISTEMA] Publica en la matriz de aspectos e impactos
8. [LOG] Registra

**Flujo: Registro de consumos ambientales**
1. [USUARIO] Responsable de MA ingresa lecturas periódicas (mensual):
   - Consumo de agua (m³)
   - Consumo de energía eléctrica (kWh)
   - Consumo de gas (m³ o kg)
   - Generación de residuos sólidos por tipo (kg)
2. [SISTEMA] Compara con el período anterior y con las metas definidas
3. Si desviación > umbral configurado:
   - [ALERTA] Notifica al responsable de MA y al jefe del área
4. [SISTEMA] Actualiza los indicadores ambientales en M4
5. [LOG] Registra

**Flujo: Registro de residuos peligrosos**
1. [USUARIO] Registra cada movimiento de residuo peligroso:
   - Tipo de residuo, clasificación (según normativa peruana)
   - Cantidad, unidad de medida
   - Fecha de generación, área de origen
   - Disposición final, empresa gestora autorizada
   - Número de manifiesto de manejo de residuos
2. [SISTEMA] Mantiene el registro histórico completo de trazabilidad
3. [ALERTA] Si el almacenamiento temporal supera el plazo legal → alerta urgente
4. [LOG] Registra cada movimiento

---

## BLOQUE D — OPERACIONES

---

### M26 — Compras

**Flujo: Solicitar compra**
1. [USUARIO] Cualquier área puede crear una solicitud de compra
2. [USUARIO] Completa: ítem(s) requeridos, cantidad, especificaciones técnicas, justificación, urgencia
3. [SISTEMA] Asigna código correlativo
4. [USUARIO] Jefe del área aprueba la solicitud
5. [ALERTA] Notifica al área de compras
6. Si la compra afecta al servicio de calibración (patrones, materiales de referencia, servicios externos):
   - [SISTEMA] Requiere evaluación previa del proveedor (M27)
   - [BLOQUEA] No puede emitirse OC a proveedor no homologado si el ítem es crítico
7. [LOG] Registra la solicitud

**Flujo: Emitir y gestionar orden de compra**
1. [USUARIO] Compras cotiza con proveedores homologados
2. [USUARIO] Selecciona proveedor y crea la OC:
   - Proveedor (debe estar activo en M27)
   - Ítems, precios, cantidades
   - Condiciones de entrega y pago
   - Fecha de entrega esperada
3. Si el monto supera el umbral definido → requiere aprobación de gerencia
4. [USUARIO] Aprueba y emite la OC
5. [ALERTA] Notifica al proveedor (o genera documento para enviar)
6. [LOG] Registra la OC

**Flujo: Recepción de bienes o servicios**
1. [USUARIO] Al recibir el pedido, el almacén registra la recepción
2. [USUARIO] Verifica: cantidad, especificaciones, estado del bien
3. Si conforme: [SISTEMA] Registra la recepción y actualiza el inventario (M28)
4. Si no conforme:
   - [USUARIO] Registra la no conformidad con detalle
   - [SISTEMA] Genera incidencia al proveedor (M27)
   - [SISTEMA] Genera hallazgo en M8
5. [LOG] Registra la recepción

---

### M27 — Proveedores

**Flujo: Registrar y homologar proveedor**
1. [USUARIO] Compras accede a Proveedores → Nuevo
2. [USUARIO] Completa: razón social, RUC, tipo, categoría (crítico/regular), contactos
3. [USUARIO] Inicia el proceso de homologación:
   - Solicita documentos: ficha RUC, certificados de calidad, acreditación (si aplica), referencias
   - Evalúa los requisitos definidos para su categoría
4. Si proveedor de calibración externa:
   - [BLOQUEA] Debe presentar certificado de acreditación vigente (INACAL u otro OA reconocido)
   - [SISTEMA] Requiere registrar el certificado y su fecha de vencimiento
   - [ALERTA] Al vencer la acreditación del proveedor → alerta para actualización
5. [USUARIO] Registra el resultado de la homologación
6. [SISTEMA] Cambia estado a "Homologado — Activo"
7. [LOG] Registra el proceso

**Flujo: Evaluación periódica**
1. [SISTEMA] Genera tarea de evaluación según la frecuencia definida (mínimo anual)
2. [ALERTA] Notifica al responsable de compras
3. [USUARIO] Evalúa al proveedor en criterios:
   - Calidad del producto/servicio (1-5)
   - Cumplimiento de plazos (1-5)
   - Precio competitivo (1-5)
   - Atención y soporte (1-5)
4. [SISTEMA] Calcula puntuación total y clasifica: A/B/C/D
5. Si clasificación = D:
   - [SISTEMA] Cambia estado a "Suspendido"
   - [BLOQUEA] Sistema no permite generar OC a proveedor suspendido
   - [ALERTA] Notifica al proveedor (si aplica) con plan de mejora requerido
6. [LOG] Registra la evaluación

---

### M28 — Inventarios

**Flujo: Entrada de inventario**
1. Al recibir una compra confirmada en M26:
   - [SISTEMA] Genera automáticamente la entrada de inventario
2. [USUARIO] Verifica y confirma la entrada
3. [USUARIO] Define ubicación en el almacén (estante, posición)
4. [SISTEMA] Actualiza el stock disponible
5. [SISTEMA] Si el ítem tiene trazabilidad de lote/serie → registra número de lote/serie
6. [LOG] Registra la entrada con referencia a la OC

**Flujo: Salida de inventario**
1. Cuando una OT requiere materiales o una tarea de mantenimiento requiere repuestos:
   - [SISTEMA] Genera la salida vinculada al documento de origen (OT o OM)
2. [USUARIO] Confirma la salida
3. [SISTEMA] Descuenta del stock disponible
4. Si el stock cae por debajo del mínimo:
   - [ALERTA] Notifica al responsable de compras
   - [SISTEMA] Puede generar solicitud de compra automática (configurable)
5. [LOG] Registra la salida con referencia

---

### M34 — Mantenimiento

**Flujo: Plan preventivo anual**
1. [USUARIO] Responsable de mantenimiento crea el plan anual
2. [USUARIO] Para cada equipo o instalación: define frecuencia, actividades de mantenimiento, responsable
3. [SISTEMA] Genera las órdenes de mantenimiento preventivo automáticamente según el plan
4. [ALERTA] 7 días antes de cada mantenimiento programado → notifica al responsable

**Flujo: Ejecutar mantenimiento**
1. [USUARIO] Accede a la orden de mantenimiento
2. [USUARIO] Ejecuta y registra: actividades realizadas, tiempo, materiales usados, observaciones, resultado
3. [SISTEMA] Descuenta materiales del inventario (M28)
4. [SISTEMA] Calcula y actualiza MTBF (tiempo medio entre fallas) y MTTR (tiempo medio de reparación)
5. [SISTEMA] Publica los indicadores en M4
6. Si durante el mantenimiento se detecta un problema → [USUARIO] Registra y genera orden de mantenimiento correctivo
7. [LOG] Registra

**Flujo: Mantenimiento correctivo**
1. [USUARIO] Reporta la falla con descripción, impacto operativo, urgencia
2. Si el equipo afectado es un patrón de calibración → [SISTEMA] Evalúa impacto en OTs activas
3. [USUARIO] Ejecuta la reparación y registra
4. [LOG] Registra todo el proceso

---

## BLOQUE E — CADENA COMERCIAL Y DE SERVICIO

---

### M24 — Comercial y CRM

**Flujo: Registrar cliente**
1. [USUARIO] Comercial accede a CRM → Clientes → Nuevo
2. [USUARIO] Completa: razón social, RUC, tipo, sector económico, dirección (una o más), contactos (nombre, cargo, email, teléfono)
3. [USUARIO] Define condiciones comerciales: condición de pago habitual, descuentos aplicables
4. [SISTEMA] Crea el cliente activo
5. [LOG] Registra

**Flujo: Registrar oportunidad comercial**
1. [USUARIO] Ejecutivo de ventas registra la oportunidad:
   - Cliente vinculado
   - Descripción del servicio requerido
   - Valor estimado
   - Probabilidad de cierre (%)
   - Fecha esperada de cierre
   - Fuente: referido / portal / llamada / visita
2. [SISTEMA] La oportunidad entra al pipeline comercial
3. [SISTEMA] Calcula el valor ponderado: valor × probabilidad
4. [LOG] Registra

**Flujo: Crear cotización**
1. [USUARIO] Desde la oportunidad → Crear cotización
2. [USUARIO] Agrega ítems de la cotización:
   - Descripción del equipo a calibrar (marca, modelo, serie si se conoce)
   - Magnitud de calibración
   - Método de calibración aplicable (M14)
   - Rango de calibración requerido
   - Puntos de calibración
   - Precio unitario
   - ¿Incluye servicio de recojo? (sí/no)
   - ¿Incluye servicio de entrega? (sí/no)
3. [USUARIO] Define condiciones comerciales para ESTA cotización:
   - Condición de facturación: Adelantada / Parcial (% inicio + % fin) / Contra entrega / Contra certificado / Crédito (plazo)
   - Condición de pago: Contado / Crédito 30d / 60d / 90d
   - Plazo de entrega estimado
   - Vigencia de la cotización
4. [SISTEMA] Calcula el total automáticamente
5. [SISTEMA] Genera el número correlativo de cotización
6. [USUARIO] Genera el documento PDF de la cotización
7. [USUARIO] Envía al cliente
8. [LOG] Registra la creación

**Flujo: Cotización aprobada por el cliente**
1. [USUARIO] Registra la aprobación del cliente (fecha, medio de aprobación, documento de aprobación adjunto)
2. [SISTEMA] Cambia estado de la cotización a "Aprobada"
3. [SISTEMA] Las condiciones de facturación y pago quedan BLOQUEADAS — no pueden modificarse sin nueva versión
4. [SISTEMA] Notifica a logística para programar el recojo (si incluye servicio de recojo)
5. [SISTEMA] La cotización es ahora el contrato interno del sistema — todos los módulos heredan sus condiciones
6. [LOG] Registra la aprobación

**Flujo: Vencimiento de cotización**
1. [SISTEMA] Monitorea la vigencia de cotizaciones en estado "Enviada"
2. [ALERTA] 3 días antes de vencer → alerta al ejecutivo de ventas
3. Al vencer sin respuesta:
   - [SISTEMA] Cambia estado a "Vencida"
   - [ALERTA] Alerta al ejecutivo para seguimiento
4. [LOG] Registra el vencimiento

---

### Módulo Logística

**Flujo completo de logística:**

**ETAPA 1: Programar recojo**
1. [SISTEMA] Al aprobarse una cotización con recojo incluido, notifica a logística
2. [USUARIO] Coordinador logístico accede a Logística → Recojos → Programar
3. [USUARIO] Selecciona la cotización, confirma dirección de recojo, fecha y hora, contacto en el cliente
4. [USUARIO] Asigna: conductor, vehículo
5. [SISTEMA] Genera la Orden de Recojo con código correlativo
6. [ALERTA] Notifica al conductor con los detalles
7. [ALERTA] Notifica al cliente con la confirmación del recojo
8. [LOG] Registra

**ETAPA 2: Ejecutar el recojo**
1. [USUARIO] Conductor va a las instalaciones del cliente
2. [USUARIO] Registra en el sistema (app móvil o tablet):
   - Hora de llegada
   - Para cada equipo: descripción, marca, modelo, serie, estado físico al recoger (bueno/con daños/observaciones)
   - Adjunta fotos de cada equipo (evidencia del estado antes del traslado)
3. [USUARIO] Cliente firma la guía de salida de sus instalaciones (firma digital en tablet)
4. [SISTEMA] Genera la Guía de Custodia con todos los datos
5. [SISTEMA] Cambia estado de los equipos a "En tránsito — recojo"
6. [LOG] Registra el recojo con fotos y firma

**ETAPA 3: Recepción e ingreso al laboratorio**
1. [USUARIO] En el laboratorio, el personal de logística/recepción recibe los equipos
2. [USUARIO] Verifica cada equipo contra la cotización:
   - ¿El equipo corresponde a lo cotizado? (marca, modelo, tipo)
   - ¿El estado es el esperado?
3. Si hay discrepancias:
   - [USUARIO] Registra la discrepancia con detalle
   - [ALERTA] Notifica al ejecutivo de ventas para coordinación con el cliente
4. [USUARIO] Para cada equipo ingresado:
   - Asigna el código interno del laboratorio
   - Confirma o completa datos: descripción, marca, modelo, serie
   - Registra el estado de recepción
5. [SISTEMA] Cambia estado a "Ingresado en laboratorio"
6. [SISTEMA] HABILITA la creación de OT para estos equipos
7. [LOG] Registra el ingreso con todos los datos

**ETAPA 4: Distribución interna**
1. [USUARIO] Logística distribuye los equipos a los laboratorios correspondientes según la magnitud de calibración
2. [USUARIO] Para cada equipo: registra el laboratorio destino y el técnico receptor
3. [USUARIO] El técnico firma la recepción
4. [SISTEMA] Cambia estado a "Distribuido a laboratorio técnico"
5. [LOG] Registra la distribución

**ETAPA 5: Retiro del laboratorio**
1. Cuando el técnico completa la calibración y la OT pasa a estado "Calibrado/Completado":
2. [SISTEMA] Habilita el retiro por logística (NO requiere certificado aprobado)
3. [ALERTA] Notifica a logística que hay equipos listos para retiro
4. [USUARIO] Logística va al laboratorio y retira los equipos
5. [USUARIO] Registra el retiro: equipos retirados, estado al retiro
6. [SISTEMA] Cambia estado a "En almacén de tránsito"
7. [LOG] Registra el retiro

**ETAPA 6: Almacén de tránsito**
1. Los equipos están físicamente en el almacén esperando despacho
2. El sistema muestra en qué estado está el certificado de cada equipo: Pendiente / En revisión / Aprobado / Enviado
3. [SISTEMA] Solo habilita el despacho cuando el certificado está en estado "Aprobado"
4. [ALERTA] Si el certificado lleva más de X días sin aprobarse → alerta al Director Técnico
5. [ALERTA] Si el equipo lleva más de X días en almacén de tránsito → alerta a logística y comercial

**ETAPA 7: Devolución al cliente**
1. [USUARIO] Coordinador logístico programa la devolución:
   - Selecciona los equipos a despachar (con certificado aprobado)
   - Asigna fecha, conductor, vehículo
2. [ALERTA] Notifica al cliente con la fecha de entrega
3. [USUARIO] Conductor ejecuta la entrega
4. [USUARIO] Registra en el sistema:
   - Hora de entrega
   - Estado de los equipos al momento de la entrega
   - Fotos de evidencia
5. [USUARIO] Cliente firma la recepción (firma digital en tablet)
6. [SISTEMA] Cambia estado a "Entregado al cliente"
7. [SISTEMA] Registra la fecha de entrega para efectos de facturación
8. [SISTEMA] Dispara el envío del certificado según configuración (si no fue enviado antes)
9. Si la condición de facturación es "contra entrega" → [SISTEMA] Notifica a administración para emitir factura
10. [SISTEMA] Genera encuesta de satisfacción automática y la envía al cliente (M18)
11. [LOG] Registra la entrega con fotos y firma

**Eventos de certificado (independiente de la entrega física):**
1. Cuando el certificado es aprobado en M25:
   - [SISTEMA] Disponible para descarga en el portal del cliente (fase futura)
   - [SISTEMA] Puede enviarse por email automáticamente (configurable)
2. [SISTEMA] Monitorea si el certificado fue enviado
3. [ALERTA] Si el equipo fue entregado hace X días y el certificado no fue enviado → alerta urgente

---

### M25 — Órdenes de Trabajo (OT)

**Flujo: Crear OT**
1. [BLOQUEA] Solo se puede crear OT para equipos que tienen ingreso de logística validado
2. [USUARIO] Accede a Órdenes de Trabajo → Nueva OT
3. [SISTEMA] Muestra solo los equipos ingresados sin OT asignada
4. [USUARIO] Selecciona los equipos a incluir en la OT
5. [SISTEMA] Hereda automáticamente de la cotización: cliente, condiciones, métodos requeridos, precios
6. [USUARIO] Para cada ítem de la OT:
   - Confirma o ajusta el método de calibración
   - Asigna el técnico responsable
   - [BLOQUEA] Sistema verifica que el técnico tiene autorización vigente para ese método y magnitud (M12)
   - [BLOQUEA] Sistema verifica que existe al menos un equipo patrón vigente disponible para el método (M13)
7. [USUARIO] Define la prioridad y fecha compromiso de entrega
8. [SISTEMA] Genera el número correlativo de OT (ej: OT-2026-4021)
9. [SISTEMA] Cambia estado a "Creada"
10. [ALERTA] Notifica al técnico asignado
11. [LOG] Registra la creación

**Flujo: Ejecución técnica**
1. [USUARIO] Técnico accede a su OT
2. [USUARIO] Registra el inicio de calibración:
   - Hora de inicio
   - Condiciones ambientales: temperatura, humedad, presión (con registro del equipo de control ambiental)
   - Equipos patrón a utilizar (el sistema verifica que tienen calibración vigente)
3. [USUARIO] Ejecuta la calibración según el método establecido
4. [USUARIO] Registra los resultados:
   - Para cada punto de calibración: lectura del patrón, lectura del equipo bajo calibración, error calculado
   - El sistema puede importar datos desde el equipo si tiene interfaz (futuro)
5. [USUARIO] Registra la hora de fin de calibración
6. [SISTEMA] Calcula automáticamente: errores, incertidumbre, estado del equipo (en tolerancia / fuera de tolerancia)
7. [USUARIO] Revisa los resultados calculados
8. Si resultado = fuera de tolerancia:
   - [SISTEMA] Alerta al técnico que el equipo está fuera de tolerancia
   - [USUARIO] Evalúa si corresponde a Trabajo No Conforme (M16)
9. [SISTEMA] Cambia estado del ítem a "Ejecutado"
10. Cuando todos los ítems están ejecutados:
    - [SISTEMA] Cambia estado de la OT a "Ejecución completada"
    - [ALERTA] Notifica al encargado de laboratorio para revisión y certificación
11. [LOG] Registra toda la ejecución

**Flujo: Elaborar y aprobar certificado**
1. [USUARIO] El sistema pre-genera el certificado con todos los datos de la OT y la ejecución
2. [USUARIO] Técnico revisa el borrador del certificado en pantalla
3. [USUARIO] Técnico lo marca como "Elaborado"
4. Si hay encargado de laboratorio:
   - [ALERTA] Notifica al encargado para revisión
   - [USUARIO] Encargado revisa el certificado
   - [USUARIO] Encargado lo aprueba → pasa al firmante autorizado
5. [ALERTA] Notifica al firmante autorizado (encargado del lab o GT según corresponda)
6. [USUARIO] Firmante revisa el certificado
7. [USUARIO] Firmante ingresa su contraseña → firma el certificado digitalmente
8. [SISTEMA] Aplica la firma con: nombre, cargo, fecha, hora, hash del documento
9. [SISTEMA] Cambia estado del certificado a "Aprobado"
10. [SISTEMA] Cambia estado de la OT a "Certificado aprobado"
11. [SISTEMA] Habilita el despacho en logística
12. [LOG] Registra cada paso del flujo de firma con usuario, timestamp y hash

**Flujo: Calibración en campo (servicio in situ)**
1. [USUARIO] Comercial genera la OT antes de la visita (mínimo 1 día antes)
2. [USUARIO] Asigna técnicos autorizados para los métodos requeridos
3. [USUARIO] Los técnicos salen a campo con la OT asignada en su dispositivo
4. En campo:
   - Si el cliente permite dispositivos: el técnico registra directamente en la app/web
   - Si no permite dispositivos: el técnico registra en papel (formato controlado del M6)
5. Al regresar (si fue en papel):
   - [USUARIO] El técnico transcribe los datos al sistema
6. El flujo de certificación es idéntico al servicio en laboratorio
7. Para la devolución: si fue in situ, no hay equipo físico que devolver
   - [SISTEMA] El certificado se envía directamente por correo/portal al cliente
8. [LOG] Registra todo el proceso con indicación de servicio en campo

---

## NIVEL 3 — PROCESOS DE SOPORTE

---

### M21 — Recursos Humanos

**Flujo: Crear legajo digital de colaborador**
1. [USUARIO] RRHH accede a RRHH → Nuevo Colaborador
2. [USUARIO] Completa datos personales: nombres, DNI, fecha de nacimiento, contacto
3. [USUARIO] Completa datos laborales: cargo, área, laboratorio (si aplica), jefe directo, fecha de ingreso, tipo de contrato
4. [SISTEMA] Vincula automáticamente con el usuario del sistema (Capa 0) si ya existe
5. [USUARIO] Sube documentos al legajo: DNI, CV, certificados de educación, contrato firmado
6. [SISTEMA] Crea el legajo digital del colaborador
7. [LOG] Registra

**Flujo: Registrar capacitación**
1. [USUARIO] RRHH o el área responsable registra la capacitación:
   - Nombre, tipo (inducción/específica/simulacro/externa), modalidad, horas, fecha, instructor/proveedor
   - Lista de asistentes (vinculados a sus legajos)
2. [USUARIO] Adjunta lista de asistencia firmada o constancias
3. [USUARIO] Registra la evaluación post-capacitación si aplica (nota de examen)
4. [SISTEMA] Actualiza el historial de formación de cada participante
5. [SISTEMA] Si la capacitación es del tipo requerido en M12 → actualiza el registro de competencias automáticamente
6. [LOG] Registra

**Flujo: Evaluación de desempeño**
1. [SISTEMA] Según el ciclo definido (semestral/anual), genera el proceso de evaluación
2. [ALERTA] Notifica al evaluador (jefe directo)
3. [USUARIO] Jefe directo completa la evaluación por criterios definidos
4. [USUARIO] Califica y agrega comentarios de fortalezas y oportunidades de mejora
5. [USUARIO] Define el plan de desarrollo individual
6. [USUARIO] El colaborador tiene acceso a ver su evaluación y puede agregar comentarios
7. [SISTEMA] Registra la evaluación en el legajo
8. [LOG] Registra

---

### M29 — Facturación (Integración API)

**Nota: Este módulo NO se desarrolla internamente. Es una interfaz hacia Odoo u otro sistema de facturación electrónica.**

**Flujo: Trigger de facturación**
1. [SISTEMA] Detecta que se cumple la condición de facturación definida en la cotización:
   - Adelantada: al aprobar la cotización
   - Contra entrega: cuando logística confirma la devolución al cliente
   - Contra certificado: cuando el certificado es aprobado
   - Parcial: según los hitos definidos
   - Crédito: al aprobar la cotización, con fecha de vencimiento calculada
2. [SISTEMA] Prepara el payload de datos para la API:
   - Datos del cliente (RUC, razón social, dirección)
   - Ítems del servicio (descripción, cantidad, precio unitario, IGV)
   - Tipo de comprobante (factura/boleta)
   - Condición de pago y fecha de vencimiento
   - Referencia a la OT y cotización
3. [SISTEMA] Envía los datos a la API de Odoo
4. [API] Odoo genera el comprobante electrónico y lo envía a SUNAT
5. [API] Odoo retorna al SIGE: número de comprobante, serie, fecha, estado SUNAT
6. [SISTEMA] Registra el comprobante en el SIGE con todos los datos retornados
7. [SISTEMA] Genera automáticamente la cuenta por cobrar en M30
8. [LOG] Registra la emisión y los datos recibidos de la API

**Manejo de errores:**
1. Si la API falla → [ALERTA] Notifica a administración para gestión manual
2. [SISTEMA] Registra el intento fallido con detalle del error
3. [SISTEMA] Permite reintento manual desde el SIGE

---

### M30 — Cobranzas

**Flujo: Gestión de cuenta por cobrar**
1. [SISTEMA] Al emitirse un comprobante en M29, crea automáticamente la cuenta por cobrar:
   - Cliente, monto, fecha de vencimiento, referencia al comprobante
2. [SISTEMA] Monitorea constantemente el estado de pago

**Flujo: Alertas de cobro**
1. [ALERTA] 7 días antes del vencimiento → notifica al ejecutivo de ventas y a cobranzas
2. Al vencimiento sin pago:
   - [SISTEMA] Cambia estado a "Vencida"
   - [ALERTA] Notifica a cobranzas y jefe comercial
3. [ALERTA] 15 días de mora → alerta a gerencia comercial
4. [ALERTA] 30 días de mora → alerta a gerencia general
5. [ALERTA] 60 días de mora → [SISTEMA] Bloquea al cliente para nuevas cotizaciones (configurable)

**Flujo: Registrar pago**
1. [USUARIO] Cobranzas o administración registra el pago:
   - Monto pagado, fecha, medio de pago, referencia bancaria
2. [SISTEMA] Actualiza el saldo de la cuenta por cobrar
3. Si pago completo → [SISTEMA] Cambia estado a "Pagado"
4. Si pago parcial → [SISTEMA] Actualiza el saldo pendiente y mantiene el estado activo
5. [SISTEMA] Actualiza el indicador "Días promedio de cobranza" en M4
6. [LOG] Registra el pago

---

## MOTORES TRANSVERSALES

---

### Motor de Workflow y Automatización

**Cómo funciona:**
El motor de workflow define los estados posibles de cada entidad y las transiciones válidas entre ellos. Para cada transición puede configurarse:
- Quién puede ejecutarla (por rol o usuario específico)
- Condiciones previas que deben cumplirse (validaciones)
- Acciones automáticas al ejecutarla (cambios de estado, notificaciones, generación de registros)
- Escalamiento si no se atiende en el plazo definido

**Escalamiento automático:**
Cuando una tarea no es atendida:
- Nivel 1: Al responsable directo (ej: 24h)
- Nivel 2: Al jefe de área (ej: 48h)
- Nivel 3: A gerencia (ej: 72h)
- Los plazos y niveles son configurables por tipo de flujo

**Notificaciones:**
- In-app: aparece en el centro de notificaciones del sistema
- Email: enviado automáticamente con link directo al registro
- Push: notificación en dispositivo móvil (fase futura con app)

---

### Centro de Evidencias

**Cómo funciona:**
Todo archivo subido al sistema pasa por el Centro de Evidencias:
1. El archivo se almacena con un identificador único
2. Se calcula el hash del archivo (SHA-256) para verificar integridad
3. Se registran los metadatos: quién subió, cuándo, desde qué módulo, vinculado a qué entidad(es)
4. Una evidencia puede estar vinculada a múltiples entidades simultáneamente

**Acceso:**
- El usuario solo ve evidencias de las entidades a las que tiene permiso de acceso
- Los administradores pueden ver todas las evidencias con sus metadatos completos
- Las evidencias no se eliminan nunca — solo se desvinculan de entidades si corresponde

---

### Motor de Inteligencia Artificial

**Búsqueda semántica:**
El usuario puede hacer consultas en lenguaje natural:
- "¿Cuántas NC tuvimos en el laboratorio de temperatura este año?"
- "¿Qué OTs están atrasadas del cliente Minera Antamina?"
- "Muéstrame los técnicos cuya autorización vence en los próximos 30 días"
El sistema interpreta la consulta y devuelve los resultados correspondientes.

**Detección de anomalías:**
- Número inusualmente alto de hallazgos en un proceso específico
- Caída brusca en el indicador de OTs entregadas a tiempo
- Patrón de error sistemático en calibraciones de un técnico específico
- Aumento en el tiempo de respuesta de ciertos módulos

**Generación de informes:**
- Informe de gestión mensual generado automáticamente con gráficos e indicadores
- Resumen ejecutivo para la Revisión por la Dirección
- Reporte de conformidad por norma para auditorías externas

---

## RESUMEN DE AUTOMATIZACIONES CRÍTICAS

### El sistema genera automáticamente sin intervención del usuario:

| Disparador | Acción automática |
|-----------|------------------|
| Cotización aprobada | Notifica a logística para programar recojo |
| Equipo ingresado por logística | Habilita creación de OT |
| OT en estado "Calibrado" | Habilita retiro por logística |
| Certificado aprobado | Habilita despacho; envía al cliente |
| Entrega confirmada | Genera encuesta de satisfacción |
| Facturación según condición pactada | Llama a API de Odoo |
| Pago registrado | Actualiza cuenta por cobrar y libera bloqueo si aplica |
| Indicador en estado crítico 2 períodos | Genera hallazgo en M8 |
| Riesgo materializado | Genera hallazgo en M8 |
| Evaluación de cumplimiento "no cumple" | Genera hallazgo en M8 |
| NC Mayor registrada | Genera AC en M9 |
| AC cerrada como eficaz | Sugiere lección aprendida; cierra el hallazgo |
| Verificación intermedia no conforme | Saca equipo de servicio; evalúa impacto retroactivo |
| Autorización próxima a vencer | Alertas escalonadas |
| Calibración de patrón próxima a vencer | Alertas escalonadas; bloqueo al vencer |
| Documento próximo a vencer | Alertas escalonadas |
| Cliente sin pago 60+ días | Bloquea para nuevas cotizaciones |
| Resultado de ensayo de aptitud insatisfactorio | Genera hallazgo en M8 |

---

*eSYNAPSE 360 — Documento de Flujos Detallados v1.0*
*Metrindust S.A.C. — Junio 2026*
*Documento vivo: actualizar con cada decisión de diseño o cambio operativo*
