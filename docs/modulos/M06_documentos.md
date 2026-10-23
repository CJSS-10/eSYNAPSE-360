# M6 · Gestión Documental

**App:** `esynapse_sig` · **Estado:** construido, en uso · **Pruebas:** `test_documentos_segundo_factor.py`

## 1. Propósito

Control de la información documentada del SIG: lista maestra, versiones con flujo de aprobación y firma electrónica, documentos externos con verificación de vigencia, archivado y jerarquía padre–hijo (procedimiento → formatos).

## 2. Modelos

| Modelo | Para qué |
|---|---|
| `Documento` | Ficha: `codigo` (único), `titulo`, `tipo` (política, manual, reglamento, plan, programa, procedimiento, formato, PETS…), `proceso`, `normas_aplicables`, `soporte`, `origen` (interno/externo), `entidad_emisora`, retención, frecuencia de revisión, `padre`, `archivado` |
| `VersionDocumento` | Cada versión: archivo, estado, fechas de aprobación y vigencia, `requiere_recarga` |
| `FirmaVersion` | Firma electrónica por rol (elabora/revisa/aprueba): usuario, cargo, IP, hash del archivo |
| `ObservacionVersion` | Observaciones del revisor/aprobador, resueltas o no |
| `ArchivoVersion` | Archivo anotado por el revisor |
| `VerificacionExterna` | Verificación periódica de vigencia de documentos externos |
| `FormatoImpreso` | Catálogo de los PDF que genera el sistema (clave, nombre, módulo, código del formato) y su vínculo con el documento de la lista maestra del que la caja de control toma versión, fecha y firmas (`docs/04_formatos_implementados.md`) |

**Estados de versión:** `borrador → en_revision → en_aprobacion → vigente` · `obsoleto` (al aprobarse una nueva) · `rechazado`.

## 3. API (`/api/documentos/`)

| Acción | Operación | Regla |
|---|---|---|
| `editar_ficha` | editar | Exige `password` del usuario (segundo factor) |
| `reemplazar_archivo`, `activar` | editar | |
| `enviar_revision` | editar | borrador → en revisión |
| `revisar`, `aprobar`, `devolver`, `rechazar` | aprobar | Cada firma exige `password`; aprobar deja la versión anterior `obsoleto` |
| `nueva_version` | crear | Un documento vigente no se edita: se versiona |
| `verificar_vigencia` | editar | Solo documentos externos |
| `archivar` / `desarchivar` | eliminar | |
| `externos_por_verificar`, `por_vencer` | leer | Alertas (alimentan Mis tareas y Calendario) |

`/api/formatos-impresos/`: lista de formatos del sistema con lo que imprimirá su caja de control (`control`: código, versión, fecha, siglas, origen); `PATCH` del vínculo `documento` solo para administradores. Pantalla: Configuración → Formatos impresos.

## 4. Reglas de negocio

- Nadie firma con credenciales de otro: toda firma exige la contraseña del usuario autenticado y guarda hash del archivo (regla 7 del CLAUDE.md).
- Un documento externo no pasa por aprobación: se controla por verificación de vigencia.
- La versión vigente anterior pasa a obsoleta al aprobar la nueva; el historial se conserva.
- (0.2.11) Un documento archivado no entra al flujo de firma ni a nueva versión (se desarchiva primero). El resumen de cambios no puede ser igual a la contraseña del usuario.
- Firma digital PAdES disponible (`firma_digital.py`, endesive) con certificado `.pfx` por usuario en `backend/certificados/usuarios/`.

## 5. Formatos

El PDF firmado es el propio archivo del documento. La configuración del sistema aporta siglas de elaborado/revisado/aprobado para los formatos de otros módulos.

## 6. Pendientes

- Confirmar descarga del "archivo anotado" con los cambios del revisor.
- Instalar `ca_sige360_publico.cer` como confianza en los PC (check verde en Adobe).
- Carga de los documentos reales del SIG.
