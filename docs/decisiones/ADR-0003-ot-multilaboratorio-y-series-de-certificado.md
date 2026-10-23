# ADR-0003 · OT general con líneas por equipo y laboratorio; certificado por línea; series por tipo de servicio

**Fecha:** 2026-10-10 · **Estado:** vigente · Reemplaza la decisión DD-03 del diseño anterior ("una OT por equipo")

## Contexto

En Metrindust una orden de trabajo agrupa varios equipos de un mismo pedido, aunque pertenezcan a laboratorios distintos; cada metrólogo trabaja los equipos de su laboratorio. Un equipo con más de un parámetro de medición recibe un certificado por parámetro. Los certificados se numeran por tipo de servicio con reinicio anual.

## Decisión

1. **`OrdenTrabajo`** (`OT 0001-2026`, reinicio anual) es el contenedor: nota de pedido, expediente, **fecha de compromiso heredada** de cotización → NP, estado derivado.
2. **`LineaOT`** = un equipo en un laboratorio para un parámetro. Es la unidad de asignación (técnico, método, patrones), de ejecución, de revisión y de certificado. Cada metrólogo ve solo las líneas de su laboratorio.
3. La OT se completa cuando **todas** sus líneas están cerradas; la entrega de equipos puede ser parcial.
4. **Un certificado por línea**. Un equipo con dos parámetros tiene dos líneas y dos certificados.
5. **Series de documento técnico por tipo de servicio** (`MT-00001-2026` calibración, `MP-`, `MC-`, `IT-`, otras configurables), con reinicio anual y número asignado **solo al emitir**.
6. Revisor y firmante siempre distintos del ejecutor.

## Alternativas descartadas

- Una OT por equipo (DD-03 anterior): no corresponde a cómo opera el laboratorio.
- Series por laboratorio o por alcance acreditado: el laboratorio numera por tipo de servicio; el carácter acreditado es un atributo del documento (pendiente P-01).

## Consecuencias

- Las puertas G06 (liberar), G07 (ejecutar) y G08 (revisar/emitir) se evalúan **por línea**, no por OT.
- Los tableros muestran el estado de la OT como el menos avanzado de sus líneas.
- El catálogo de series se administra desde Configuración.
