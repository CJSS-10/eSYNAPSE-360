import { useRef } from 'react'
import { useIndicador } from '../lib/movimiento.js'

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
  const ref = useRef(null)
  const caja = useIndicador(ref, '[aria-current="true"]', grupo.clave)
  return (
    <nav className="space-y-3">
      <div ref={ref} className="relative flex gap-5 overflow-x-auto overflow-y-hidden whitespace-nowrap border-b border-slate-200 dark:border-slate-800">
        {grupos.map((g) => {
          const I = g.icono
          const activo = g === grupo
          return (
            <button key={g.clave} onClick={() => !activo && onCambiar(g.secciones[0].clave)} aria-current={activo ? 'true' : undefined}
              className={`flex items-center gap-1.5 border-b-2 border-transparent px-0.5 pb-2 pt-1 text-sm transition-colors ${activo ? 'font-semibold text-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>
              {I && <I className="h-4 w-4" />}{g.nombre}
            </button>
          )
        })}
        {caja && <span aria-hidden="true" className="mov-indicador pointer-events-none absolute bottom-0 h-0.5 rounded-full bg-esynapse-500" style={{ left: caja.left, width: caja.width }} />}
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
  // El fondo blanco de la opción elegida se desliza hasta la nueva (movimiento, 27-10-2026)
  const ref = useRef(null)
  const caja = useIndicador(ref, '[aria-pressed="true"]', valor)
  return (
    <div ref={ref} role="group" className="relative inline-flex flex-wrap gap-0.5 rounded-lg bg-slate-100 p-0.5 text-xs dark:bg-slate-800/60">
      {caja && (
        <span aria-hidden="true" className="mov-indicador pointer-events-none absolute rounded-md bg-white shadow-sm dark:bg-slate-900"
          style={{ left: caja.left, top: caja.top, width: caja.width, height: caja.height }} />
      )}
      {opciones.map(([k, n]) => (
        <button key={k} type="button" onClick={() => onChange(k)} aria-pressed={valor === k}
          className={`relative rounded-md px-3 py-1 transition-colors ${valor === k ? 'font-semibold text-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>{n}</button>
      ))}
    </div>
  )
}
