// Pestañas estándar de un módulo (ADR-0007): una fila subrayada bajo el título, con el
// mismo estilo que la navegación por grupos (NavModulo). opciones: [[clave, nombre, Icono?]]
export default function Pestanas({ opciones, valor, onChange }) {
  return (
    <div role="tablist" className="flex gap-5 overflow-x-auto overflow-y-hidden whitespace-nowrap border-b border-slate-200 dark:border-slate-800">
      {opciones.map(([k, nombre, Icono]) => {
        const activa = valor === k
        return (
          <button key={k} type="button" role="tab" aria-selected={activa} onClick={() => onChange(k)}
            className={`flex items-center gap-1.5 border-b-2 px-0.5 pb-2 pt-1 text-sm transition-colors ${activa
              ? 'border-esynapse-500 font-semibold text-slate-900 dark:text-white'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>
            {Icono && <Icono className="h-4 w-4" />}{nombre}
          </button>
        )
      })}
    </div>
  )
}
