# Método de trabajo

Cómo se construye, entrega y valida cada módulo de eSYNAPSE 360. Es un ciclo corto, pensado para un equipo de dos: **César** (dueño del producto: decide, valida y acepta) y el **asistente de desarrollo** (construye, prueba y documenta).

## 1. Ciclo por módulo

| Etapa | Qué se hace | Entregable | Dónde queda |
|---|---|---|---|
| **1. Requisitos** | Se define qué hace el módulo, qué formatos reales del SIG replica (archivos en `PROCEDIMIENTOS SIG/`), qué reglas de negocio aplica y cómo se sabrá que está bien (**criterios de aceptación**). | Ficha del módulo, secciones 1–3 | `docs/modulos/Mxx_*.md` |
| **2. Diseño** | Modelos, estados y transiciones, permisos, endpoints, decisiones que haya que tomar. Si una decisión es de arquitectura, se escribe un ADR. | Ficha, secciones 4–6; ADR si aplica | `docs/modulos/`, `docs/decisiones/` |
| **3. Construcción** | Código backend y frontend, migraciones y **pruebas automáticas de las reglas de negocio**. Nada se da por terminado sin prueba. | Código + pruebas en verde | Git |
| **4. Validación** | César recorre el checklist de aceptación en su PC, en **modo pruebas** (`Iniciar modo pruebas.bat`: copia de la base, sin tocar datos ni correlativos reales). Lo que falle vuelve a construcción. | Acta de validación | `docs/validacion/Mxx_acta_AAAA-MM-DD.md` |
| **5. Entrega** | Se sube la versión, se registra en el CHANGELOG qué cambió y qué migración exige, se sincroniza la carpeta limpia y se hace commit. | Versión nueva | `CHANGELOG.md`, `backend/VERSION`, Git |

Un módulo puede pasar varias veces por 3 → 4 antes de la 5. Las correcciones pequeñas (un campo, un texto) no requieren acta nueva: se anotan en el CHANGELOG.

## 2. Definición de "hecho"

Un módulo o cambio está **hecho** solo cuando se cumple todo esto:

1. El código compila y la suite completa de pruebas está en verde (`Probar.bat`).
2. Las reglas de negocio nuevas tienen al menos una prueba que las hace fallar si se rompen.
3. Si cambió el modelo de datos, existe la migración y `makemigrations --check` no detecta diferencias.
4. La ficha del módulo está actualizada (modelos, endpoints, reglas, pendientes).
5. El `CHANGELOG.md` tiene la entrada con la versión, los cambios y la instrucción de actualización.
6. César lo validó en pantalla (para módulos completos: acta de validación firmada).
7. Está sincronizado a la carpeta limpia y en Git.

Los códigos del SIG (SIG-PRO-16-r02, MET-PRO-04…) aparecen **solo** en los PDF generados y en esta documentación; nunca en textos de la interfaz ni en comentarios del código (regla 11 del CLAUDE.md).

## 3. Procedimiento de entrega

Cada entrega del asistente termina con este bloque, siempre igual:

```
Versión: 0.x.y
Cambios: (resumen en lenguaje de negocio)
Migración: sí (0041) / no
Pasos: 1) cerrar el sistema  2) Aplicar actualizacion.bat  3) Iniciar eSYNAPSE 360.bat
Probar: (qué recorrer en pantalla para validar)
```

Y César, en su PC:

1. Cierra las ventanas del backend y del frontend.
2. Ejecuta `Aplicar actualizacion.bat` si la entrega dice que hay migración (el lanzador también lo detecta y lo aplica solo).
3. Ejecuta `Probar.bat` cuando quiera confirmar que todo sigue consistente.
4. Prueba lo indicado y reporta.
5. Cuando una entrega queda aceptada: `Sincronizar carpeta limpia.bat` y commit en Git.

## 4. Numeración de versiones

`MAYOR.MENOR.PARCHE` (ej. `0.2.3`):

- **MAYOR** `0` mientras el sistema no esté en producción; pasa a `1` con el primer uso real.
- **MENOR** sube al cerrar una fase del roadmap o un módulo completo nuevo.
- **PARCHE** sube con cada entrega intermedia (correcciones, mejoras dentro de un módulo).

La versión vive en `backend/VERSION`, la muestra la pantalla de configuración y la API pública, y la registra cada respaldo.

## 5. Ritmo y comunicación

- **Una sesión = una entrega** o un avance claro con su registro en CHANGELOG y PENDIENTES.
- **Revisión semanal corta**: estado del backlog (`PENDIENTES.md`), qué se cerró, qué sigue, qué decisión falta.
- Las decisiones que cambian el diseño (como "una OT con varios laboratorios") se escriben el mismo día en un ADR o en el plan correspondiente, no se dejan en el chat.
- Lo que no puede decidirse sin César queda como pregunta abierta numerada en el documento que corresponda (P-nn), nunca implícito.

## 6. Reglas que no se negocian

- No se corren migraciones con el servidor encendido (ya corrompió la base una vez).
- No se borra nada físicamente: soft delete siempre.
- No se entrega sin pruebas en verde.
- Un módulo nuevo (fase 3 en adelante) nace como app Django propia, no se agrega a `esynapse_sig` (ADR-0004).
- Los formatos PDF se replican 1:1 desde el formato real del procedimiento; si el formato no está en `PROCEDIMIENTOS SIG/`, se pide antes de construir. Cada PDF imprime la versión, fecha y siglas de **su** plantilla; el registro vive en `04_formatos_implementados.md` y se actualiza cuando una plantilla cambia de versión.
