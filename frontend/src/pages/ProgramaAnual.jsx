import { useCallback, useEffect, useState } from 'react'
import { FileText } from 'lucide-react'
import { api } from '../lib/api.js'

// Actividades del Programa Anual. El PDF las reagrupa en 3 bloques.
const ACTIVIDADES = [
  ['calibracion', 'Calibración'],
  ['mantenimiento', 'Mantenimiento'],
  ['comprobacion_intermedia', 'Comprobación Intermedia'],
  ['comprobacion_funcional', 'Comprobación Funcional'],
  ['caracterizacion', 'Caracterización'],
]
const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

export default function ProgramaAnual({ puedeEditar }) {
  const [anio, setAnio] = useState(new Date().getFullYear())
  const [laboratorio, setLaboratorio] = useState('')
  const [labs, setLabs] = useState([])
  const [equipos, setEquipos] = useState([])
  const [error, setError] = useState('')

  const cargar = useCallback(() => {
    const p = new URLSearchParams({ anio: String(anio) })
    if (laboratorio) p.set('laboratorio', laboratorio)
    api.equipos.programa(`?${p}`).then((d) => setEquipos(d.equipos || [])).catch((e) => setError(e.message))
  }, [anio, laboratorio])
  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { api.equipos.laboratorios().then((d) => setLabs(d.results ?? d)).catch(() => {}) }, [])

  const actDe = (eq, tipo) => eq.actividades[tipo] || { frecuencia: '', meses: [] }

  const setActLocal = (eqId, tipo, cambios) => {
    setEquipos((prev) => prev.map((e) => e.id !== eqId ? e : {
      ...e,
      actividades: { ...e.actividades, [tipo]: { ...(e.actividades[tipo] || { frecuencia: '', meses: [] }), ...cambios } },
    }))
  }

  const guardar = async (eqId, tipo, frecuencia, meses) => {
    try { await api.equipos.programar(eqId, { tipo, anio, frecuencia: frecuencia || '', meses: meses || [] }) }
    catch (e) { setError(e.message) }
  }

  const toggleMes = (eq, tipo, mes) => {
    const a = actDe(eq, tipo)
    const meses = (a.meses || []).includes(mes) ? a.meses.filter((m) => m !== mes) : [...(a.meses || []), mes].sort((x, y) => x - y)
    setActLocal(eq.id, tipo, { meses })
    guardar(eq.id, tipo, a.frecuencia, meses)
  }

  const imprimir = async () => {
    setError('')
    const p = new URLSearchParams({ anio: String(anio) })
    if (laboratorio) p.set('laboratorio', laboratorio)
    try {
      const blob = await api.equipos.programaPdf(`?${p}`)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  return (
    <div className="space-y-3">
      {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Año</label>
        <input type="number" min="2000" max="2100" className="input-esynapse w-24" value={anio}
          onChange={(e) => setAnio(e.target.value.replace(/\D/g, '').slice(0, 4) || new Date().getFullYear())} />
        <select className="input-esynapse w-56" value={laboratorio} onChange={(e) => setLaboratorio(e.target.value)}>
          <option value="">Todos los laboratorios</option>
          {labs.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <button onClick={imprimir} className="btn-secondary ml-auto" title="Generar PDF del programa anual">
          <FileText className="h-4 w-4" /> Generar PDF
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
              <th className="px-2 py-2">Equipo</th>
              <th className="px-2 py-2">Código</th>
              <th className="px-2 py-2">Actividad</th>
              <th className="px-2 py-2">Frecuencia</th>
              {MESES.map((m) => <th key={m} className="px-1 py-2 text-center">{m}</th>)}
            </tr>
          </thead>
          <tbody>
            {equipos.map((eq) => ACTIVIDADES.map(([tipo, nombre], idx) => {
              const a = actDe(eq, tipo)
              return (
                <tr key={`${eq.id}-${tipo}`} className={`${idx === 0 ? 'border-t-2 border-slate-200 dark:border-slate-700' : 'border-t border-slate-100 dark:border-slate-800/60'}`}>
                  <td className="px-2 py-1 font-medium">{idx === 0 ? eq.nombre : ''}</td>
                  <td className="px-2 py-1 font-mono">{idx === 0 ? eq.codigo : ''}</td>
                  <td className="px-2 py-1 text-slate-500 dark:text-slate-400">{nombre}</td>
                  <td className="px-2 py-1">
                    <input className="input-esynapse !py-1 w-28 text-xs" placeholder="Anual / 6 meses" value={a.frecuencia || ''}
                      disabled={!puedeEditar}
                      onChange={(e) => setActLocal(eq.id, tipo, { frecuencia: e.target.value })}
                      onBlur={(e) => guardar(eq.id, tipo, e.target.value, a.meses)} />
                  </td>
                  {[...Array(12)].map((_, i) => {
                    const mes = i + 1
                    return (
                      <td key={i} className="px-1 py-1 text-center">
                        <input type="checkbox" checked={(a.meses || []).includes(mes)} disabled={!puedeEditar}
                          onChange={() => toggleMes(eq, tipo, mes)} className="h-3.5 w-3.5 accent-esynapse-600" />
                      </td>
                    )
                  })}
                </tr>
              )
            }))}
            {equipos.length === 0 && (
              <tr><td colSpan={16} className="px-3 py-6 text-center text-xs text-slate-400">Sin equipos para ese filtro.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400">Marca los meses programados de cada actividad. Se guarda automáticamente. El equipamiento auxiliar no se incluye. El PDF agrupa Calibración+Mantenimiento, Comprob. Intermedia+Caracterización y Comprob. Funcional.</p>
    </div>
  )
}
