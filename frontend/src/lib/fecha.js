// Formateo de fechas consistente en todo el sistema.
// Fecha: AAAA-MM-DD (año, mes y día con dos dígitos).
// Hora: formato de 12 horas con a. m. / p. m.

export function fecha(iso) {
  if (!iso) return ''
  // Una fecha sin hora ('2026-10-14') se devuelve tal cual: convertirla a Date
  // la interpretaría en UTC y en Perú (UTC-5) retrocedería un día.
  if (typeof iso === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

// Fecha local de hoy (AAAA-MM-DD). No usar toISOString(): da la fecha en UTC (en Lima, desde las 19:00 ya es mañana).
export function hoy() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function fechaHora(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  let h = d.getHours()
  const ampm = h >= 12 ? 'p. m.' : 'a. m.'
  h = h % 12
  if (h === 0) h = 12
  const hh = String(h).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${fecha(iso)} ${hh}:${min} ${ampm}`
}
