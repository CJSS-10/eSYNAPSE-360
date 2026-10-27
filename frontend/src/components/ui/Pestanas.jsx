import { useRef } from 'react'
import { useIndicador } from '../../lib/movimiento.js'

// Pestañas estándar de un módulo (ADR-0007): una fila subrayada bajo el título, con el
// mismo estilo que la navegación por grupos (NavModulo). opciones: [[clave, nombre, Icono?]]
// La línea de la pestaña activa se desliza hasta la elegida (movimiento, 27-10-2026).
export default function Pestanas({ opciones, valor, onChange }) {
  const ref = useRef(null)
  const caja = useIndicador(ref, '[aria-selected="true"]', valor)
  return (
    <div ref={ref} role="tablist" className="relative flex gap-5 overflow-x-auto overflow-y-hidden whitespace-nowrap border-b border-slate-200 dark:border-slate-800">
      {opciones.map(([k, nombre, Icono]) => {
        const activa = valor === k
        return (
          <button key={k} type="button" role="tab" aria-selected={activa} onClick={() => onChange(k)}
            className={`flex items-center gap-1.5 border-b-2 border-transparent px-0.5 pb-2 pt-1 text-sm transition-colors ${activa
              ? 'font-semibold text-slate-900 dark:text-white'
              : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>
            {Icono && <Icono className="h-4 w-4" />}{nombre}
          </button>
        )
      })}
      {caja && (
        <span aria-hidden="true" className="mov-indicador pointer-events-none absolute bottom-0 h-0.5 rounded-full bg-esynapse-500"
          style={{ left: caja.left, width: caja.width }} />
      )}
    </div>
  )
}
