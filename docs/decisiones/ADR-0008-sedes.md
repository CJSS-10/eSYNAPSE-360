# ADR-0008 — Sedes como catálogo único del núcleo

- **Fecha:** 2026-10-24
- **Estado:** Aceptada (César)
- **Relacionada:** ADR-0006 (Organización y personal: catálogos únicos)

## Contexto

La organización opera en más de un local (Metrindust: sede operativa de 3 pisos, alquilada, con un medidor de luz y
uno de agua por piso; y sede administrativa). Las áreas tenían la sede y el piso como texto libre, y Medio ambiente
registraba un único consumo mensual por servicio. El sistema se comercializará para otros laboratorios, que tendrán
un número variable de sedes.

## Decisión

1. **Sede, Nivel y Suministro** son datos maestros de Organización y personal (app `organizacion`), como áreas,
   puestos y trabajadores. Cualquier módulo los consulta; nadie crea su propio catálogo de lugares.
2. La sede solo indica si sus **instalaciones son propias o alquiladas** (sin datos del arrendador ni del contrato,
   decisión de César). Una sola sede principal.
3. **Suministro** = servicio (energía eléctrica o agua) con su medidor, de toda la sede o de un nivel. Su consumo se
   obtiene por **lectura del medidor** o por **recibo**. Agregar otro servicio es ampliar una lista de opciones.
4. Todo registro ligado a un lugar físico apunta a la sede (y al nivel si aplica): áreas, consumos (por suministro),
   pesajes, disposiciones, aspectos ambientales. Los trabajadores pertenecen a la sede de su área.
5. La migración convierte los textos existentes en sedes y niveles sin perder ninguno.
6. La ubicación de la sede se elige del **catálogo de ubigeos del Perú** (`core.Ubigeo`, codificación INEI completa,
   selectores encadenados); distrito, provincia y departamento no se escriben a mano. El mismo catálogo servirá a
   clientes, proveedores y cualquier dirección del sistema.

## Consecuencias

- Indicadores por sede, por piso y de toda la organización sin dobles registros.
- Pendiente de adoptar la sede (por orden de valor): inspecciones y elementos de seguridad de SST (hoy «lugar»/«piso»
  en texto), requisitos legales por sede (hoy «proceso / sede» en texto), equipos e instalaciones del laboratorio,
  plan de emergencia y brigadas.
