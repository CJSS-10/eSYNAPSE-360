// Badge / chip semántico reutilizable.
// Tonos de estado (regla del proyecto): gris · ambar · azul · violeta · verde · rojo
// Normas: iso9001 · iso14001 · iso45001 · iso17025
// Nombres completos de las clases: Tailwind solo genera las que encuentra escritas
// (con `badge-${tono}` los colores nunca llegaban a la hoja de estilos).
const CLASE = {
  gris: 'badge-gris', ambar: 'badge-ambar', azul: 'badge-azul', violeta: 'badge-violeta', verde: 'badge-verde', rojo: 'badge-rojo',
  iso9001: 'badge-iso9001', iso14001: 'badge-iso14001', iso45001: 'badge-iso45001', iso17025: 'badge-iso17025',
}

export default function Badge({ tono = 'gris', children, className = '', ...props }) {
  return (
    <span className={`badge ${CLASE[tono] || CLASE.gris} ${className}`} {...props}>
      {children}
    </span>
  )
}

// Mapea el nombre de norma visible -> tono de badge.
export const TONO_NORMA = {
  'ISO 9001': 'iso9001',
  'ISO 14001': 'iso14001',
  'ISO 45001 / Ley 29783': 'iso45001',
  'NTP ISO/IEC 17025': 'iso17025',
}

// Mapea un estado visible -> tono semántico.
export const TONO_ESTADO = {
  'En elaboración': 'gris',
  'En revisión': 'ambar',
  'En aprobación': 'azul',
  'Vigente': 'verde',
  'Completado': 'verde',
  'Cerrado': 'verde',
  'Obsoleto': 'rojo',
  'Vencido': 'rojo',
  'Rechazado': 'violeta',
  'Reabierto': 'violeta',
  'Registrada': 'gris',
  'Recibida': 'gris',
  'En análisis de causa': 'ambar',
  'En evaluación': 'ambar',
  'En implementación': 'azul',
  'Acción correctiva': 'azul',
  'Corrección': 'azul',
  'En verificación de eficacia': 'violeta',
  'Por vencer': 'ambar',
  'Devuelto': 'ambar',
}

export function NormaBadge({ nombre }) {
  return <Badge tono={TONO_NORMA[nombre] || 'gris'}>{nombre}</Badge>
}

export function EstadoBadge({ estado }) {
  return <Badge tono={TONO_ESTADO[estado] || 'gris'}>{estado}</Badge>
}
