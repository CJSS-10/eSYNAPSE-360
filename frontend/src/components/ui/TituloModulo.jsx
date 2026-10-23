// Título estándar de la pantalla principal de un módulo (ADR-0007): sección del sistema,
// nombre del módulo y una explicación breve de para qué sirve.
export default function TituloModulo({ seccion, titulo, descripcion }) {
  return (
    <div className="min-w-0">
      {seccion && <p className="text-[13px] text-slate-500 dark:text-slate-400">{seccion}</p>}
      <h1 className="text-[26px] font-semibold leading-tight tracking-tight text-slate-900 dark:text-white">{titulo}</h1>
      {descripcion && <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">{descripcion}</p>}
    </div>
  )
}
