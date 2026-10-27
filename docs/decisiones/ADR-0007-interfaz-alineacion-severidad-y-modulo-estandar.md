# ADR-0007 · Interfaz: alineación de tablas por tipo de dato, escala de severidad única y módulo estándar

**Fecha:** 2026-10-23 · **Estado:** vigente · **Origen:** recorrido de pantallas del 23-10-2026 y maqueta de rediseño aprobada por César («dale con los 3»). Reemplaza la regla 13 de CLAUDE.md (tablas centradas).

## Contexto

El recorrido de pantallas mostró tres problemas que se repetían en todos los módulos:

- **Tablas centradas:** las descripciones se leían a saltos y las columnas cortas (N° de OT, cliente, estado) se partían en varias líneas o desbordaban la tabla.
- **Dos escalas de riesgo con colores distintos:** Riesgos y oportunidades e IPERC (SST) usaban palabras iguales («Moderado», «Importante») con colores diferentes, y el análisis de trabajo seguro otra paleta más.
- **Cada módulo con su propio encabezado y navegación:** título con ícono, pestañas en píldora, pestañas subrayadas, casilla «Solo abiertas», etc.

## Decisión

1. **Alineación en tablas según el tipo de dato** (reemplaza la regla 13): texto, códigos, nombres y procedencia a la izquierda; estados, clasificaciones y sí/no al centro; fechas, plazos y cantidades a la derecha. Códigos y etiquetas nunca se parten en dos líneas. Se aplica con la clase `tabla-sig` (estilos en `frontend/src/index.css`); las tablas que aún no tienen la clase conservan el centrado anterior hasta que su módulo se adapte al estándar, para no desordenar de golpe más de 70 tablas.
2. **Escala de severidad única de cinco niveles** (`frontend/src/lib/severidad.js`): cada metodología conserva sus nombres, pero el mismo nivel tiene siempre el mismo color y el nombre va siempre escrito.

   | Nivel | Riesgos y oportunidades | IPERC | Análisis de trabajo seguro |
   |---|---|---|---|
   | 1 | No significativo | Trivial | — |
   | 2 | Tolerado | Tolerable | Tolerable |
   | 3 | Moderado | Moderado | Poco significativo |
   | 4 | Importante | Importante | Significativo |
   | 5 | Crítico | Intolerable | Intolerable |

   Las etiquetas usan el tono suave del nivel; el mapa de calor de Riesgos usa el relleno sólido.
3. **Módulo estándar** para la pantalla principal de cada módulo:
   - `EncabezadoModulo`: sección del sistema, título, explicación breve de una línea y acciones a la derecha; debajo, las pestañas si el módulo las tiene.
   - Filtros en una fila: búsqueda, selectores y, a la derecha, el control segmentado `Vistas` (p. ej. Abiertas / Todas) en lugar de casillas.
   - Tabla `tabla-sig` dentro de `card-esynapse`, con encabezados en tipo normal (sin mayúsculas sostenidas), descripciones en hasta dos líneas y la etapa en miniatura (`EtapaMini`) en los módulos con flujo por etapas.
   - Piloto: Acciones correctivas (0.8.13). Los demás módulos se adaptan uno a la vez, cuando se trabaje en ellos.

## Alternativas descartadas

- **Quitar el centrado en todas las tablas a la vez:** las tablas existentes no tienen clases por columna; quedarían todas a la izquierda, incluidas cantidades y matrices de conteo, sin cumplir la regla nueva.
- **Mantener una escala por módulo:** perpetúa que «Importante» signifique colores distintos según la pantalla.

## Pendiente (no forma parte de esta decisión)

La página de detalle de registro en lugar de ventana, el Tablero como panel del SIG y el cambio de tipografía y paleta base quedan en la maqueta para aprobarse por separado.

## Ampliación (2026-10-23, misma fecha)

César aprobó también el resto de la maqueta («dale con todo»), implementado del 0.8.14 al 0.8.17:

- **Tipografía IBM Plex Sans** instalada en el proyecto (sin depender de internet), con números de ancho fijo; **azul Metrindust** (`esynapse-600` = #1f4e9b) como color principal; **modo oscuro azul marino**.
- **Ficha de registro en panel ancho de altura completa** (`Modal` con `panel`) en lugar de ventana centrada, y **barra de etapas común** (`BarraPasos`): etapas cerradas con candado, la actual destacada, las futuras punteadas, fija bajo el título. Se eligió panel y no página aparte para conservar la lista detrás y no rehacer la navegación de cada módulo.
- **Tablero del SIG**: vencimientos por módulo (vencido, 7, 30, 60 y 90 días), estado por módulo y pendientes de la persona.
- **Título estándar** (`TituloModulo`) y tabla principal `tabla-sig` en los módulos.

## Ampliación (César, 2026-10-24)

- **Encabezados de columna centrados** horizontal y verticalmente en todas las tablas del sistema (regla global en `frontend/src/index.css`, gana sobre las clases de alineación de cada columna). La alineación por tipo de dato aplica solo a las celdas de datos.
