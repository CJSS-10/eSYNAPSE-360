// Tarjeta de indicador (KPI) para el Dashboard.
const TONOS = {
  azul: 'bg-esynapse-600/12 text-esynapse-600 dark:text-esynapse-300',
  verde: 'bg-emerald-500/12 text-emerald-600 dark:text-emerald-300',
  ambar: 'bg-amber-500/15 text-amber-600 dark:text-amber-300',
  rojo: 'bg-red-500/12 text-red-600 dark:text-red-300',
  violeta: 'bg-violet-500/12 text-violet-600 dark:text-violet-300',
  gris: 'bg-slate-500/12 text-slate-600 dark:text-slate-300',
}

export default function KpiCard({ icon: Icon, label, value, hint, tono = 'azul', onClick }) {
  const Comp = onClick ? 'button' : 'div'
  return (
    <Comp
      onClick={onClick}
      className={`card-esynapse card-pad text-left ${onClick ? 'card-hover cursor-pointer' : ''}`}
    >
      <div className="flex items-center justify-between">
        <p className="section-title">{label}</p>
        {Icon && (
          <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${TONOS[tono] || TONOS.azul}`}>
            <Icon className="h-5 w-5" />
          </span>
        )}
      </div>
      <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900 dark:text-white">{value}</p>
      {hint && <p className="mt-1 text-xs muted">{hint}</p>}
    </Comp>
  )
}
