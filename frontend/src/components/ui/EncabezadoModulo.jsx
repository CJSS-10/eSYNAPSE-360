// Encabezado estándar de un módulo: sección del sistema, título, explicación breve y acciones.
// Debajo (children) van, si el módulo las tiene, sus pestañas.
export default function EncabezadoModulo({ seccion, titulo, descripcion, acciones, children }) {
  return (
    <header className="space-y-1">
      {seccion && <p className="text-[13px] text-slate-500 dark:text-slate-400">{seccion}</p>}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[26px] font-semibold leading-tight tracking-tight text-slate-900 dark:text-white">{titulo}</h1>
          {descripcion && <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">{descripcion}</p>}
        </div>
        {acciones && <div className="flex flex-wrap items-center gap-2">{acciones}</div>}
      </div>
      {children && <div className="pt-3">{children}</div>}
    </header>
  )
}
