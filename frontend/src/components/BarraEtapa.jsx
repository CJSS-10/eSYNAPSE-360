import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-react'

/**
 * Barra al final de una etapa con la acción que la cierra. Muestra qué falta
 * para habilitarla (`bloqueo`), un aviso que no bloquea (`aviso`) o una nota
 * de lo que sigue (`nota`).
 * botones: [{ texto, accion, peligro?, secundario? }]
 */
export default function BarraEtapa({ titulo, nota, aviso, bloqueo, botones = [] }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-esynapse-600/40 bg-esynapse-600/5 p-3">
      <div className="text-xs text-slate-600 dark:text-slate-300">
        <p className="font-semibold">{titulo}</p>
        {aviso && <p className="text-[11px] text-amber-600 dark:text-amber-400"><AlertTriangle className="mr-1 inline h-3 w-3" />{aviso}</p>}
        {bloqueo
          ? <p className="text-[11px] text-slate-500 dark:text-slate-400">{bloqueo}</p>
          : nota && <p className="text-[11px] text-slate-500 dark:text-slate-400">{nota}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        {botones.map((b) => (
          <button key={b.texto} type="button" disabled={Boolean(bloqueo) && !b.secundario} onClick={b.accion}
            className={`${b.peligro ? 'btn-danger' : b.secundario ? 'btn-secondary' : 'btn-primary'} !py-1.5 text-xs disabled:opacity-50`}>
            {b.peligro ? <XCircle className="h-3.5 w-3.5" /> : !b.secundario && <CheckCircle2 className="h-3.5 w-3.5" />} {b.texto}
          </button>
        ))}
      </div>
    </div>
  )
}
