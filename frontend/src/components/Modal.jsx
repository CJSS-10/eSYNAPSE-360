import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

/**
 * Ventana del sistema.
 * - Normal: centrada, para formularios y confirmaciones.
 * - `panel`: panel ancho de altura completa a la derecha, para la ficha de un registro con
 *   etapas (ADR-0007): da espacio de página sin perder la lista de atrás; el título queda fijo
 *   arriba y el contenido se desplaza debajo (la barra de etapas se fija bajo el título).
 * El clic fuera NO la cierra: evita perder formularios a medio llenar. Cerrar requiere la X o Cancelar.
 * Se dibuja directamente en <body>: dentro de la página animada, «fixed» quedaba encerrado.
 */
export default function Modal({ abierto, titulo, onCerrar, children, ancho = 'max-w-lg', panel = false }) {
  if (!abierto) return null
  if (panel) {
    return createPortal(
      <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
        <section role="dialog" aria-modal="true" aria-label={titulo}
          className="panel-entrada flex h-full w-full max-w-6xl flex-col border-l border-slate-200 bg-white shadow-pop dark:border-slate-800 dark:bg-slate-900"
          onClick={(e) => e.stopPropagation()}>
          <header className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 px-6 py-4 dark:border-slate-800">
            <h2 className="text-lg font-semibold leading-snug">{titulo}</h2>
            <button onClick={onCerrar} aria-label="Cerrar"
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">
              <X className="h-5 w-5" />
            </button>
          </header>
          <div className="flex-1 overflow-y-auto px-6 pb-8 pt-4">{children}</div>
        </section>
      </div>,
      document.body,
    )
  }
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        className={`card-esynapse w-full ${ancho} max-h-[90vh] overflow-y-auto p-5`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{titulo}</h2>
          <button onClick={onCerrar} aria-label="Cerrar" className="rounded p-1 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800">
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  )
}
