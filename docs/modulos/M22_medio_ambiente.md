# M22 · Medio ambiente

**App:** `ambiente` (app propia, ADR-0004) · **Permisos:** módulo `medio_ambiente` · **Estado:** 0.10.0 en construcción · **Pruebas:** `ambiente/tests/`
**Procedimientos:** Identificación de aspectos y evaluación de impactos ambientales (Ver. 00), Uso eficiente de energía eléctrica (Ver. 00), Uso eficiente del agua (Ver. 00), Gestión integral de residuos sólidos (Ver. 01). **Formatos que replica:** Matriz de identificación de aspectos y evaluación de impactos ambientales; Pesaje de residuos sólidos.

## 1. Propósito
Identificar y evaluar los aspectos ambientales (situación normal, anormal y de emergencia, con perspectiva de ciclo de vida), determinar los significativos y sus controles operacionales; medir el desempeño ambiental (consumo de energía y agua, residuos generados y dispuestos) y preparar la declaración anual de residuos (SIGERSOL). Cubre ISO 14001 6.1.2, 6.1.3 (vínculo con Requisitos legales), 8.1 y 9.1.

## 2. Decisiones (César, 2026-10-24)
| Tema | Decisión |
|---|---|
| Significancia | Regla del procedimiento: significativo si la suma de los cinco criterios es ≥ 10 **o** si el cumplimiento legal es 3 (no cumple). Los aspectos positivos se identifican pero no se evalúan. |
| Carga inicial | La matriz en Excel (330 filas en 12 hojas) se carga **consolidada**: un aspecto común a todos los laboratorios se registra una vez (alcance «Todos los laboratorios»); «potencial incendio», una vez para toda la empresa; se corrigen sumas manuales y positivos evaluados. Se entrega la lista de cambios para revisión. |
| Consumos | Se registra el consumo mensual de energía (kWh) y agua (m³) del recibo, con monto y archivo, e indicadores (por mes, por trabajador, frente al mismo mes del año anterior). Debe añadirse a los procedimientos de energía y agua. |
| Aprobación de la matriz | La aprueban **los miembros titulares del Comité de SST, todos** (unanimidad), con su firma (contraseña o PIN) o el acta en papel firmada por todos. Toda modificación posterior la deja pendiente de nueva aprobación (como el IPERC). |
| Catálogos | Proceso: catálogo oficial (vacío = todos los procesos). Lugar: Organización (áreas y laboratorios) o un alcance general (toda la empresa, todos los laboratorios, oficinas) o un lugar descrito (p. ej. comedor). Responsable: puesto de Organización. Requisito legal: obligación de Requisitos legales (ámbito ambiental). |

## 3. Registros y reglas
- **Aspecto ambiental:** lugar, proceso, actividad, aspecto, impacto, situaciones (N/A/E), generación (directa/indirecta), clase (positivo/negativo), etapa del ciclo de vida, controles existentes, evaluación A–E (1 a 3) con resultado y significancia, control operacional, registro asociado, responsable, plazo (obligatorio si es significativo), obligación legal vinculada. Retirar = baja lógica con motivo.
- **Cumplimiento legal (criterio A):** si el aspecto está vinculado a una obligación, se propone desde su última evaluación de cumplimiento: no cumple → 3; pendiente → 2; cumple o no aplica → 1.
- **Pesaje de residuos (PES-NNN-AAAA):** formato del laboratorio: no peligrosos (tacho azul: papel, cartón, otros; tacho blanco: botellas, plástico, PVC, otros), peligrosos (tacho rojo: líquidos en litros y sólidos en kg), RAEE (cantidad y kg); tipo de pesaje (ingreso al almacén / salida); firma de quien registra.
- **Disposición:** fecha, tipo de residuo, kg, destino (municipal, operadora EO-RS, reciclaje, donación, venta, acopio RAEE), operadora y su registro, manifiesto, certificado adjunto.
- **Resumen anual:** toneladas por mes, peligrosos y no peligrosos, generadas y dispuestas, para la declaración anual.
- **Consumo mensual:** tipo (energía/agua), año, mes, consumo, monto, recibo adjunto; un registro por tipo y mes.

## 4. Criterios de aceptación
1. La significancia sigue la regla del procedimiento (≥ 10 o incumplimiento legal); un positivo no se evalúa.
2. Un aspecto significativo exige control operacional, responsable y plazo.
3. La matriz se aprueba solo con la firma de todos los titulares del comité (o el acta en papel de todos); un cambio posterior la deja pendiente.
4. El PDF de la matriz replica el formato con su encabezado, bloques y colores; el del pesaje, el suyo.
5. Los consumos no se duplican por tipo y mes; los indicadores se calculan solos.
6. El resumen anual de residuos suma los pesajes y disposiciones del año en toneladas.
