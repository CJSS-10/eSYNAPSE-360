import { X } from 'lucide-react'

export default function Modal({ abierto, titulo, onCerrar, children, ancho = 'max-w-lg' }) {
  if (!abierto) return null
  // El clic fuera del modal NO lo cierra: evita perder formularios a medio llenar.
  // Cerrar requiere acción explícita: botón Cancelar o la X.
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        className={`card-esynapse w-full ${ancho} max-h-[90vh] overflow-y-auto p-5`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{titulo}</h2>
          <button onClick={onCerrar} className="rounded p-1 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800">
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
