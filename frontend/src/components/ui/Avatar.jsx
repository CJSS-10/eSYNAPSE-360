// Avatar reutilizable: muestra la foto si existe; si no, las iniciales.
export const iniciales = (n) =>
  ((n || '?').trim().split(/\s+/).slice(0, 2).map((s) => s[0] || '').join('').toUpperCase() || '?')

export default function Avatar({ src, nombre, className = 'h-9 w-9 text-xs' }) {
  if (src) {
    return (
      <img
        src={src}
        alt={nombre || 'avatar'}
        className={`shrink-0 rounded-full bg-slate-200 object-cover dark:bg-slate-800 ${className}`}
      />
    )
  }
  return (
    <span className={`flex shrink-0 items-center justify-center rounded-full bg-esynapse-600 font-bold text-white ${className}`}>
      {iniciales(nombre)}
    </span>
  )
}
