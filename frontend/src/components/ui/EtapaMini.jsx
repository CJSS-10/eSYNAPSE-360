// Etapa de un registro en miniatura, para las filas de tabla: un segmento por etapa
// (las ya cerradas en gris, la actual con el color de su estado, las futuras vacías)
// y debajo el nombre del estado. Los colores siguen la regla de estados del sistema.
const SEGMENTO = {
  gris: 'bg-slate-500', ambar: 'bg-amber-500', azul: 'bg-esynapse-600', violeta: 'bg-violet-500', verde: 'bg-emerald-500', rojo: 'bg-red-500',
}
// Nombres completos de las clases (Tailwind solo genera las que encuentra escritas).
const ETIQUETA = {
  gris: 'badge badge-gris', ambar: 'badge badge-ambar', azul: 'badge badge-azul', violeta: 'badge badge-violeta', verde: 'badge badge-verde', rojo: 'badge badge-rojo',
}

export default function EtapaMini({ total = 5, actual = 0, tono = 'gris', texto }) {
  return (
    <span className="inline-flex flex-col items-center gap-1.5">
      <span className="flex w-24 gap-0.5" aria-hidden="true">
        {Array.from({ length: total }, (_, i) => (
          <span key={i} className={`h-1.5 flex-1 rounded-sm ${
            i < actual ? 'bg-slate-400 dark:bg-slate-500' : i === actual ? SEGMENTO[tono] : 'bg-slate-200 dark:bg-slate-700'}`} />
        ))}
      </span>
      <span className={ETIQUETA[tono] || ETIQUETA.gris}>{texto}</span>
    </span>
  )
}
