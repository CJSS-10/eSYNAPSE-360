# ADR-0006 · Organización y personal: datos maestros únicos en el núcleo

**Fecha:** 2026-10-22 · **Estado:** vigente · **Origen:** propuesta de César al construir SST («¿los puestos, procesos y áreas no deberían salir de un lugar centralizado?»)

## Contexto

El mismo concepto vivía en varios lugares sin relación entre sí:

- **Puesto / cargo:** texto libre en cada usuario (cargo y sigla de firma), un catálogo propio en Competencia técnica (perfil por puesto) y otro en SST (puestos de la matriz IPERC).
- **Área / laboratorio:** texto en el usuario, una lista simple en Configuración, texto en la matriz IPERC, en la entrevista de seguimiento, en la ubicación de equipos y en el alcance de firma de certificados.
- **Proceso:** ya centralizado en el módulo Procesos.

Cada módulo nuevo (accidentes, EPP, capacitaciones, la OT) habría creado su propia copia, y los reportes cruzados (accidentes por puesto, exámenes por área) no habrían cuadrado.

## Decisión

1. **Áreas, puestos y trabajadores son datos maestros del núcleo**, en la app `organizacion`, igual que Usuarios y Configuración: siempre habilitados, no se venden por separado (`MODULOS_NUCLEO`). Pantalla «Organización y personal» en el menú Administración, con permiso propio (`organizacion`).
   - **Área:** gerencias, áreas y laboratorios en un solo organigrama (depende de), con su proceso principal, sede, piso y puesto responsable.
   - **Puesto:** nombre, sigla de firma, área, a quién reporta, tipo (propio / tercero) y **perfil del puesto** (educación, formación, experiencia, habilidades, funciones), versionado.
   - **Trabajador:** persona con puesto, área, ingreso y cese; usuario del sistema **opcional** (no todo trabajador usa el sistema, pero todos reciben EPP, pasan exámenes o se capacitan).
2. **Consulta abierta, mantenimiento con permiso:** cualquier usuario activo lee los catálogos (todos los módulos los usan); crearlos o cambiarlos exige el permiso «organización». El documento de identidad solo lo ve quien gestiona la organización.
3. **Cada módulo guarda solo lo suyo**, referido al puesto o al trabajador: SST (peligros, EPP y exámenes por puesto), Competencia técnica (autorizaciones, entrenamiento; el perfil lo consulta del puesto), OT (quién ejecuta y firma).
4. **El usuario vinculado a un trabajador toma de su puesto el cargo, la sigla y el área** (y el laboratorio, si su área lo es). Los campos de texto del usuario se conservan como copia sincronizada porque todas las firmas del sistema los leen; se retirarán al migrar a PostgreSQL. Un usuario sin trabajador (cuenta externa o de sistema) mantiene sus datos escritos.
5. **El futuro módulo de RRHH (fase 5) extiende el núcleo** (legajo, contratos, vacaciones, asistencia, desempeño); no lo reemplaza ni duplica. Un cliente que no adquiera RRHH mantiene igual su organización desde Administración.
6. Nada se elimina: áreas y puestos se desactivan (solo sin dependientes activos); el trabajador se cesa (y su usuario se desactiva).
7. **Procesos** se quedan en su módulo; las áreas y los puestos apuntan a procesos principales.

## Mantenimiento en Metrindust

- Trabajadores (ingresos, ceses, cambios de puesto): Administración o quien lleve el personal.
- Áreas, puestos y perfiles: el SIG (son información documentada: organigrama y manual de funciones). Sin flujo de aprobación adicional; todo cambio queda en el historial y el perfil se versiona.

## Alternativas descartadas

- **Dentro del módulo RRHH:** los módulos se pueden desactivar y RRHH está en la fase 5; SST, Competencia o la OT dependerían de un módulo opcional o inexistente.
- **Listas genéricas clave–valor en Configuración** (como la lista anterior de áreas): no soportan relaciones (área → puesto → trabajador, organigrama, perfil versionado).
- **Que cada módulo mantenga su catálogo:** es lo que se quería evitar.

## Consecuencias

- Migraciones de traslado: lista de áreas y laboratorios de Configuración y datos escritos en los usuarios (`organizacion 0002`), puestos de SST (`sst 0005`), perfiles de Competencia (`esynapse_sig 0070`).
- El «Laboratorio como catálogo» previsto en los maestros de la fase 3.0 queda cubierto por las áreas de tipo laboratorio.
- Pendiente de llevar al catálogo: ubicación de equipos (es un lugar, se revisará con la fase 3) y área de la entrevista de seguimiento.
