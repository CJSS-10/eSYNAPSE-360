import { useCallback, useEffect, useState } from 'react'
import { ScrollText } from 'lucide-react'
import { api } from '../lib/api.js'

const ACCIONES = [
  '', 'LOGIN', 'LOGOUT', 'LOGIN_FALLIDO', 'CREAR', 'EDITAR', 'ELIMINAR',
  'APROBAR', 'FIRMAR', 'EXPORTAR', 'ACCESO_BLOQUEADO',
]

export default function Auditoria() {
  const [entradas, setEntradas] = useState([])
  const [total, setTotal] = useState(0)
  const [accion, setAccion] = useState('')
  const [pagina, setPagina] = useState(1)

  const cargar = useCallback(async () => {
    const params = new URLSearchParams({ page: pagina })
    if (accion) params.set('accion', accion)
    try {
      const data = await api.auditoria(`?${params}`)
      setEntradas(data.results ?? data)
      setTotal(data.count ?? 0)
    } catch { /* sin permiso */ }
  }, [accion, pagina])

  useEffect(() => { cargar() }, [cargar])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <ScrollText className="h-6 w-6 text-esynapse-500" />
        <h1 className="text-2xl font-bold">Log de auditoría</h1>
        <span className="text-sm text-slate-500 dark:text-slate-400">({total} entradas — inmutable)</span>
      </div>

      <select
        className="input-esynapse w-56"
        value={accion}
        onChange={(e) => { setAccion(e.target.value); setPagina(1) }}
      >
        {ACCIONES.map((a) => (
          <option key={a} value={a}>{a || 'Todas las acciones'}</option>
        ))}
      </select>

      <div className="card-esynapse overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-left uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-3 py-2">Timestamp</th>
              <th className="px-3 py-2">Usuario</th>
              <th className="px-3 py-2">Acción</th>
              <th className="px-3 py-2">Entidad</th>
              <th className="px-3 py-2">Campo</th>
              <th className="px-3 py-2">Anterior → Nuevo</th>
              <th className="px-3 py-2">IP</th>
            </tr>
          </thead>
          <tbody>
            {entradas.map((e) => (
              <tr key={e.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-[11px]">
                  {new Date(e.timestamp).toLocaleString('es-PE')}
                </td>
                <td className="px-3 py-2">{e.usuario_nombre}</td>
                <td className="px-3 py-2">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                    e.accion === 'ACCESO_BLOQUEADO' || e.accion === 'LOGIN_FALLIDO'
                      ? 'bg-red-500/15 text-red-500'
                      : e.accion === 'CREAR'
                        ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                        : 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300'
                  }`}>
                    {e.accion_display}
                  </span>
                </td>
                <td className="px-3 py-2">{e.entidad}{e.entidad_id ? ` #${e.entidad_id}` : ''}</td>
                <td className="px-3 py-2 font-mono text-[11px]">{e.campo || '—'}</td>
                <td className="max-w-xs truncate px-3 py-2 text-slate-500 dark:text-slate-400" title={`${e.valor_anterior ?? ''} → ${e.valor_nuevo ?? ''}`}>
                  {e.valor_anterior || e.valor_nuevo
                    ? `${e.valor_anterior ?? '∅'} → ${e.valor_nuevo ?? '∅'}`
                    : '—'}
                </td>
                <td className="px-3 py-2 font-mono text-[11px]">{e.ip || '—'}</td>
              </tr>
            ))}
            {entradas.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-400">Sin entradas</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {total > 25 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <button className="btn-secondary !py-1" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>
            Anterior
          </button>
          <span className="text-slate-500">Página {pagina} de {Math.ceil(total / 25)}</span>
          <button className="btn-secondary !py-1" disabled={pagina >= Math.ceil(total / 25)} onClick={() => setPagina(pagina + 1)}>
            Siguiente
          </button>
        </div>
      )}
    </div>
  )
}
