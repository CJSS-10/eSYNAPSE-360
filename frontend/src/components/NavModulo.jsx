/**
 * Navegación de un módulo en tres niveles, cada uno con su propio estilo:
 *  1. Grupos: una sola fila subrayada (no salta de línea; se desplaza de lado en pantallas angostas).
 *  2. Secciones del grupo: píldoras (la fila no aparece si el grupo tiene una sola sección).
 *  3. Vistas internas de una sección: control segmentado pequeño (`Vistas`), dentro del contenido.
 *
 * grupos: [{ clave, nombre, icono, secciones: [{ clave, nombre }] }]
 */
export default function NavModulo({ grupos, seccion, onCambiar }) {
  const grupo = grupos.find((g) => g.secciones.some((s) => s.clave === seccion)) || grupos[0]
  return (
    <nav className="space-y-3">
      <div className="flex gap-5 overflow-x-auto overflow-y-hidden whitespace-nowrap border-b border-slate-200 dark:border-slate-800">
        {grupos.map((g) => {
          const I = g.icono
          const activo = g === grupo
          return (
            <button key={g.clave} onClick={() => !activo && onCambiar(g.secciones[0].clave)}
              className={`flex items-center gap-1.5 border-b-2 px-0.5 pb-2 pt-1 text-sm transition-colors ${activo ? 'border-esynapse-500 font-semibold text-slate-900 dark:text-white' : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>
              {I && <I className="h-4 w-4" />}{g.nombre}
            </button>
          )
        })}
      </div>
      {grupo.secciones.length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          {grupo.secciones.map((s) => (
            <button key={s.clave} onClick={() => onCambiar(s.clave)}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${s.clave === seccion ? 'border-esynapse-500/50 bg-esynapse-500/15 font-semibold text-esynapse-600 dark:text-esynapse-300' : 'border-slate-200 text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800'}`}>
              {s.nombre}
            </button>
          ))}
        </div>
      )}
    </nav>
  )
}

/** Vistas internas de una sección (nivel 3): control segmentado. opciones: [[clave, nombre]] */
export function Vistas({ opciones, valor, onChange }) {
  return (
    <div className="inline-flex flex-wrap gap-0.5 rounded-lg bg-slate-100 p-0.5 text-xs dark:bg-slate-800/60">
      {opciones.map(([k, n]) => (
        <button key={k} onClick={() => onChange(k)}
          className={`rounded-md px-3 py-1 ${valor === k ? 'bg-white font-semibold text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>{n}</button>
      ))}
    </div>
  )
}
