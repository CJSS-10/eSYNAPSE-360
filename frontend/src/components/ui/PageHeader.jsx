// Encabezado de página con el estilo del título estándar de módulo (ADR-0007):
// título, descripción y acciones. El ícono ya no se muestra (se conserva el parámetro).
export default function PageHeader({ icon, title, subtitle, actions, className = '' }) {  // eslint-disable-line no-unused-vars
  return (
    <div className={`flex flex-wrap items-end justify-between gap-4 ${className}`}>
      <div className="min-w-0">
        <h1 className="text-[26px] font-semibold leading-tight tracking-tight text-slate-900 dark:text-white">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
