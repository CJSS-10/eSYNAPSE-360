# Acta de validación de software — eSYNAPSE 360

Registro de validación exigido por la NTP ISO/IEC 17025:2017 (7.11.2: el software que afecta los resultados o los registros del laboratorio debe validarse antes de su uso y después de cualquier cambio). Se emite una por módulo (o por cambio relevante) y se archiva en esta carpeta como `Mxx_acta_AAAA-MM-DD.md`. Se imprime y firma, o se firma digitalmente desde M6.

---

**Sistema:** eSYNAPSE 360 · **Versión:** ____ · **Módulo / cambio validado:** ____
**Fecha de validación:** ____ · **Ambiente:** PC de desarrollo (SQLite) / Servidor (PostgreSQL)

## 1. Alcance de la validación

Qué funciones se validan y qué registros del laboratorio afectan (por ejemplo: "M10 Auditorías: programa, plan, listas de verificación, informe; afecta registros de auditoría interna del SIG").

## 2. Requisitos verificados

| N° | Requisito / regla | Procedimiento o norma que lo exige | Cómo se verificó | Resultado |
|---|---|---|---|---|
| 1 | | | Prueba automática `test_…` / recorrido manual | Conforme / No conforme |
| 2 | | | | |
| 3 | | | | |

## 3. Pruebas realizadas

- **Automáticas:** `Probar.bat` en la versión indicada → resultado: ____ pruebas, ____ OK.
- **Manuales:** checklist de aceptación adjunto (`Mxx_checklist_AAAA-MM-DD.md`).
- **Datos usados:** reales / anonimizados / de prueba.

## 4. Desviaciones encontradas y tratamiento

| N° | Desviación | Acción | Versión que la corrige | Estado |
|---|---|---|---|---|
| | | | | |

## 5. Conclusión

- [ ] El módulo **es apto para su uso** en el alcance indicado.
- [ ] Es apto **con restricciones** (indicar cuáles).
- [ ] **No es apto**; se requiere nueva validación tras corregir.

## 6. Control de cambios posterior

Todo cambio al módulo se registra en `CHANGELOG.md`. Un cambio que afecte reglas de negocio, cálculos o formatos impresos exige una nueva acta (puede ser abreviada, referenciando esta).

## 7. Firmas

| Rol | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Realizó la validación | | | | |
| Responsable del proceso | | | | |
| Responsable del SIG | | | | |
