// Formateo de fechas consistente en todo el sistema.
// Fecha: AAAA-MM-DD (año, mes y día con dos dígitos).
// Hora: formato de 12 horas con a. m. / p. m.

export function fecha(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
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
