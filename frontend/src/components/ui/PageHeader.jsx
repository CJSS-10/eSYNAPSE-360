// Encabezado de página consistente: ícono + título + descripción + acciones.
export default function PageHeader({ icon: Icon, title, subtitle, actions, className = '' }) {
  return (
    <div className={`flex flex-wrap items-start justify-between gap-3 ${className}`}>
      <div className="flex items-start gap-3">
        {Icon && (
          <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-esynapse-600/12 text-esynapse-600 dark:text-esynapse-300">
            <Icon className="h-5 w-5" />
          </span>
        )}
        <div>
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="mt-0.5 text-sm muted">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
