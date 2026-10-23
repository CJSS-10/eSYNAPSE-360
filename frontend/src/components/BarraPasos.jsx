import { Lock } from 'lucide-react'

/**
 * Barra de etapas de un registro (ADR-0005 y ADR-0007), el sello visual del sistema:
 * las etapas cerradas llevan candado (solo lectura), la actual se destaca y las futuras
 * se ven punteadas. Dentro del panel de detalle queda fija arriba al desplazarse.
 * Con `onElegir`, las etapas cerradas se abren en consulta y la elegida se marca (`vista`).
 */
export default function BarraPasos({ pasos, actual, cerrado = false, vista, onElegir }) {
  return (
    <nav aria-label="Etapas del registro"
      className="sticky -top-4 z-10 -mx-6 border-b border-slate-200 bg-white/95 px-6 pb-3 pt-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95">
      <ol className="flex items-start">
        {pasos.map((nombre, i) => {
          const hecho = cerrado || i < actual
          const enCurso = !cerrado && i === actual
          const futuro = !cerrado && i > actual
          const elegido = onElegir && vista === i
          const contenido = (
            <>
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[13px] font-bold ${
                hecho ? 'bg-slate-500 text-white dark:bg-slate-600'
                : enCurso ? 'bg-esynapse-600 text-white'
                : 'border-2 border-dashed border-slate-300 bg-white text-slate-400 dark:border-slate-600 dark:bg-slate-900'} ${
                elegido || (enCurso && !onElegir) ? 'ring-4 ring-esynapse-600/20' : ''}`}>
                {hecho ? <Lock className="h-3.5 w-3.5" aria-label="Cerrada" /> : i + 1}
              </span>
              <span className={`text-[13px] leading-tight ${
                enCurso ? 'font-semibold text-esynapse-700 dark:text-esynapse-300'
                : hecho ? 'font-medium text-slate-700 dark:text-slate-200' : 'text-slate-400'} ${elegido ? 'underline underline-offset-4' : ''}`}>{nombre}</span>
            </>
          )
          return (
            <li key={nombre} className="relative flex flex-1 flex-col pr-2" aria-current={enCurso ? 'step' : undefined}>
              {i < pasos.length - 1 && (
                <span aria-hidden="true" className={`absolute left-9 right-1 top-[15px] h-[3px] rounded ${hecho ? 'bg-slate-400 dark:bg-slate-500' : 'bg-slate-200 dark:bg-slate-700'}`} />
              )}
              {onElegir ? (
                <button type="button" disabled={futuro} onClick={() => onElegir(i)}
                  title={futuro ? 'Etapa futura: se habilita al completar la anterior' : hecho ? 'Consultar (solo lectura)' : 'Etapa en curso'}
                  className="relative z-[1] flex flex-col items-start gap-1.5 text-left disabled:cursor-not-allowed">{contenido}</button>
              ) : (
                <div className="relative z-[1] flex flex-col items-start gap-1.5">{contenido}</div>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
