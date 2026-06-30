import { useState, useEffect, Fragment } from 'react'
import { FileText, Plus, Pencil, Trash2, Save } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { api } from '../lib/api.js'
import { useConfirm } from '../context/ConfirmContext.jsx'

// Intervalo de Calibración (MET-PRO-04-r08, método OIML D10).
// Edición en matriz: años en filas, puntos en columnas (Resultado · Incert. · EMP).
const fnum = (v, n = 3) => (v === null || v === undefined || v === '' || isNaN(v)) ? '—' : Number(v).toFixed(n)
const IB = 'rounded p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'
const VACIA = { resultado: '', incertidumbre: '', emp: '' }
const k = (pid, anio) => `${pid}_${anio}`
// Solo los patrones (misma regla que el backend: la clasificación contiene "patrón").
const esPatron = (e) => (e?.clasificacion || '').toLowerCase().includes('patr')

// Construye el estado de la matriz (años + celdas) a partir del resumen del backend.
const construir = (resumen) => {
  const ps = resumen?.puntos || []
  const set = new Set()
  ps.forEach((p) => (p.resultados || []).forEach((r) => set.add(r.anio)))
  const anios = [...set].sort((a, b) => a - b)
  const celdas = {}
  ps.forEach((p) => (p.resultados || []).forEach((r) => {
    celdas[k(p.id, r.anio)] = { resultado: r.resultado ?? '', incertidumbre: r.incertidumbre ?? '', emp: r.emp ?? '' }
  }))
  return { anios, celdas }
}

export default function IntervaloCalibracion({ puedeEditar }) {
  const confirmar = useConfirm()
  const [equipos, setEquipos] = useState([])
  const [sel, setSel] = useState('')
  const [data, setData] = useState(null)
  const [puntos, setPuntos] = useState([])
  const [anios, setAnios] = useState([])
  const [celdas, setCeldas] = useState({})
  const [dirty, setDirty] = useState(false)
  const [error, setError] = useState('')
  // Modales
  const [modalPunto, setModalPunto] = useState(false)
  const [formPunto, setFormPunto] = useState({ valor_nominal: '' })
  const [puntoEdit, setPuntoEdit] = useState(null)
  const [modalAnio, setModalAnio] = useState(false)
  const [formAnio, setFormAnio] = useState('')

  useEffect(() => { api.equipos.listar('?incluir_inactivos=1').then((d) => setEquipos(d.results ?? d)).catch(() => {}) }, [])

  const aplicarResumen = (resp, fresco = true) => {
    setData(resp)
    setPuntos(resp.puntos || [])
    const base = construir(resp)
    if (fresco) {
      setAnios(base.anios); setCeldas(base.celdas); setDirty(false)
    } else {
      // Tras un cambio estructural (punto): conservar ediciones sin guardar.
      setAnios((prev) => [...new Set([...prev, ...base.anios])].sort((a, b) => a - b))
      setCeldas((prev) => ({ ...base.celdas, ...prev }))
    }
  }

  const cargar = async (id) => {
    setSel(id); setError('')
    if (!id) { setData(null); setPuntos([]); setAnios([]); setCeldas({}); setDirty(false); return }
    try { aplicarResumen(await api.puntosIntervalo.resumen(`?equipo=${id}`), true) } catch (e) { setError(e.message) }
  }
  const refrescarPunto = async () => {
    try { aplicarResumen(await api.puntosIntervalo.resumen(`?equipo=${sel}`), false) } catch (e) { setError(e.message) }
  }

  // --- Puntos (columnas) ---
  const abrirPuntoNuevo = () => { setPuntoEdit(null); setFormPunto({ valor_nominal: '' }); setModalPunto(true) }
  const abrirPuntoEdit = (p) => { setPuntoEdit(p.id); setFormPunto({ valor_nominal: p.valor_nominal || '' }); setModalPunto(true) }
  const guardarPunto = async () => {
    if (!formPunto.valor_nominal.trim()) { setError('Indica el valor nominal.'); return }
    try {
      if (puntoEdit) await api.puntosIntervalo.editar(puntoEdit, { valor_nominal: formPunto.valor_nominal })
      else await api.puntosIntervalo.crear({ equipo: sel, valor_nominal: formPunto.valor_nominal })
      setModalPunto(false); await refrescarPunto()
    } catch (e) { setError(e.message) }
  }
  const eliminarPunto = async (p) => {
    if (!await confirmar({ titulo: 'Eliminar punto', mensaje: `¿Eliminar el punto ${p.valor_nominal} y sus resultados?`, textoConfirmar: 'Eliminar', peligro: true })) return
    try {
      await api.puntosIntervalo.eliminar(p.id)
      setCeldas((prev) => { const n = { ...prev }; anios.forEach((a) => delete n[k(p.id, a)]); return n })
      await refrescarPunto()
    } catch (e) { setError(e.message) }
  }

  // --- Años (filas) ---
  const abrirAnioNuevo = () => {
    const sug = anios.length ? Math.max(...anios) + 1 : new Date().getFullYear()
    setFormAnio(String(sug)); setModalAnio(true)
  }
  const agregarAnio = () => {
    const a = Number(formAnio)
    if (!a || a <= 0) { setError('Indica un año válido.'); return }
    if (anios.includes(a)) { setError('Ese año ya existe.'); return }
    const prev = anios.length ? Math.max(...anios) : null   // para prellenar el EMP
    setCeldas((c) => {
      const n = { ...c }
      puntos.forEach((p) => {
        const empPrev = prev != null ? (c[k(p.id, prev)]?.emp ?? '') : ''
        n[k(p.id, a)] = { resultado: '', incertidumbre: '', emp: empPrev }
      })
      return n
    })
    setAnios((prevA) => [...prevA, a].sort((x, y) => x - y))
    setDirty(true); setModalAnio(false); setError('')
  }
  const eliminarAnio = async (a) => {
    if (!await confirmar({ titulo: 'Eliminar año', mensaje: `¿Quitar el año ${a} de todos los puntos?`, textoConfirmar: 'Quitar', peligro: true })) return
    setCeldas((c) => { const n = { ...c }; puntos.forEach((p) => delete n[k(p.id, a)]); return n })
    setAnios((prev) => prev.filter((x) => x !== a))
    setDirty(true)
  }

  // --- Celdas ---
  const cval = (pid, a, campo) => (celdas[k(pid, a)]?.[campo] ?? '')
  const setCelda = (pid, a, campo, val) => {
    setCeldas((prev) => ({ ...prev, [k(pid, a)]: { ...(prev[k(pid, a)] || VACIA), [campo]: val } }))
    setDirty(true)
  }

  const guardar = async () => {
    setError('')
    const lista = []
    puntos.forEach((p) => anios.forEach((a) => {
      const c = celdas[k(p.id, a)]
      if (c && (c.resultado !== '' || c.incertidumbre !== '' || c.emp !== '')) {
        lista.push({ punto: p.id, anio: a, resultado: Number(c.resultado || 0), incertidumbre: Number(c.incertidumbre || 0), emp: Number(c.emp || 0) })
      }
    }))
    try {
      const resp = await api.puntosIntervalo.guardarMatriz({ equipo: sel, celdas: lista })
      if (resp?.pendiente) {
        setDirty(false)
        await confirmar({
          titulo: 'Cambio pendiente de aprobación',
          mensaje: resp.detail || 'El cambio quedó registrado y pendiente de aprobación por un supervisor.',
          textoConfirmar: 'Entendido', textoCancelar: 'Cerrar',
        })
        return
      }
      aplicarResumen(resp, true)
    } catch (e) { setError(e.message) }
  }

  const imprimir = async () => {
    setError('')
    try {
      const blob = await api.puntosIntervalo.pdf(`?equipo=${sel}`)
      const url = URL.createObjectURL(blob); window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  const perTxt = (c) => (c?.periodo == null ? 'DERIVA 0' : `${c.periodo.toFixed(1)} años`)
  const calcDe = (pid) => (data?.puntos || []).find((p) => p.id === pid)?.calculo

  return (
    <div className="space-y-3">
      {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="flex flex-wrap items-center gap-3">
        <select className="input-esynapse w-72" value={sel} onChange={(e) => cargar(e.target.value)}>
          <option value="">Selecciona un patrón…</option>
          {equipos.filter(esPatron).map((eq) => <option key={eq.id} value={eq.id}>{eq.codigo} · {eq.nombre}</option>)}
        </select>
        {sel && data && (
          <span className="rounded-lg bg-esynapse-500/10 px-3 py-1.5 text-sm font-semibold text-esynapse-600 dark:text-esynapse-300">
            Intervalo del patrón: {data.intervalo_patron == null ? '—' : `${data.intervalo_patron.toFixed(1)} años`}
          </span>
        )}
        {puedeEditar && (
          <>
            <button onClick={abrirPuntoNuevo} className="btn-secondary" disabled={!sel} title={!sel ? 'Selecciona un patrón primero' : 'Agregar punto'}><Plus className="h-4 w-4" /> Agregar punto</button>
            <button onClick={abrirAnioNuevo} className="btn-secondary" disabled={!sel || puntos.length === 0} title={!sel ? 'Selecciona un patrón primero' : (puntos.length === 0 ? 'Primero agrega al menos un punto' : 'Agregar año')}><Plus className="h-4 w-4" /> Agregar año</button>
            <button onClick={guardar} className="btn-primary" disabled={!dirty}><Save className="h-4 w-4" /> Guardar</button>
          </>
        )}
        <button onClick={imprimir} disabled={!sel} className="btn-secondary ml-auto" title="Generar PDF"><FileText className="h-4 w-4" /> Generar PDF</button>
      </div>

      {!sel && <p className="py-8 text-center text-sm text-slate-400">Selecciona un patrón para registrar sus puntos y años (OIML D10).</p>}

      {sel && puntos.length === 0 && (
        <p className="py-8 text-center text-sm text-slate-400">Este patrón aún no tiene puntos. Agrega el primero con "Agregar punto" y luego los años.</p>
      )}

      {sel && puntos.length > 0 && (
        <>
          {dirty && <p className="rounded bg-amber-500/10 px-3 py-1.5 text-xs text-amber-600 dark:text-amber-400">Tienes cambios sin guardar. Presiona <strong>Guardar</strong> para registrar y recalcular el periodo.</p>}
          <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/60">
                  <th rowSpan={2} className="sticky left-0 z-10 bg-slate-50 px-2 py-1.5 text-left font-semibold dark:bg-slate-800/60">Año</th>
                  {puntos.map((p) => (
                    <th key={p.id} colSpan={3} className="border-l border-slate-200 px-2 py-1 text-center font-semibold dark:border-slate-700">
                      <span className="inline-flex items-center gap-1">
                        {p.valor_nominal}
                        {puedeEditar && (
                          <>
                            <button onClick={() => abrirPuntoEdit(p)} className={IB} title="Editar punto"><Pencil className="h-3 w-3" /></button>
                            <button onClick={() => eliminarPunto(p)} className={`${IB} text-red-500`} title="Eliminar punto"><Trash2 className="h-3 w-3" /></button>
                          </>
                        )}
                      </span>
                    </th>
                  ))}
                </tr>
                <tr className="bg-slate-50 text-[10px] uppercase text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
                  {puntos.map((p) => (
                    <Fragment key={p.id}>
                      <th className="border-l border-slate-200 px-1 py-1 font-medium dark:border-slate-700">Resultado</th>
                      <th className="px-1 py-1 font-medium">Incert.</th>
                      <th className="px-1 py-1 font-medium">EMP</th>
                    </Fragment>
                  ))}
                </tr>
              </thead>
              <tbody>
                {anios.length === 0 && (
                  <tr><td colSpan={1 + puntos.length * 3} className="py-3 text-center text-[11px] text-slate-400">Sin años. Agrega el primero con "Agregar año".</td></tr>
                )}
                {anios.map((a) => (
                  <tr key={a} className="border-t border-slate-100 dark:border-slate-800/60">
                    <td className="sticky left-0 z-10 bg-white px-2 py-1 font-semibold dark:bg-slate-900">
                      <span className="inline-flex items-center gap-1">
                        {a}
                        {puedeEditar && <button onClick={() => eliminarAnio(a)} className={`${IB} text-red-500`} title="Quitar año"><Trash2 className="h-3 w-3" /></button>}
                      </span>
                    </td>
                    {puntos.map((p) => (
                      <Fragment key={p.id}>
                        <td className="border-l border-slate-100 px-0.5 py-0.5 dark:border-slate-800/60">
                          <input type="number" step="any" disabled={!puedeEditar} className="input-esynapse w-20 px-1 py-1 text-center text-xs" value={cval(p.id, a, 'resultado')} onChange={(e) => setCelda(p.id, a, 'resultado', e.target.value)} />
                        </td>
                        <td className="px-0.5 py-0.5">
                          <input type="number" step="any" disabled={!puedeEditar} className="input-esynapse w-20 px-1 py-1 text-center text-xs" value={cval(p.id, a, 'incertidumbre')} onChange={(e) => setCelda(p.id, a, 'incertidumbre', e.target.value)} />
                        </td>
                        <td className="px-0.5 py-0.5">
                          <input type="number" step="any" disabled={!puedeEditar} className="input-esynapse w-20 px-1 py-1 text-center text-xs" value={cval(p.id, a, 'emp')} onChange={(e) => setCelda(p.id, a, 'emp', e.target.value)} />
                        </td>
                      </Fragment>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Resumen por punto (último cálculo guardado) */}
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {puntos.map((p) => {
              const c = calcDe(p.id)
              return (
                <div key={p.id} className="rounded-md bg-slate-50 px-3 py-2 text-xs dark:bg-slate-800/40">
                  <span className="font-semibold">{p.valor_nominal}</span>{' · '}
                  <span className="text-slate-500 dark:text-slate-400">EMP {fnum(c?.emp)} · Umáx {fnum(c?.umax)} · Tol {fnum(c?.tolerancia)} · Deriva máx {fnum(c?.deriva_maxima)}</span>{' · '}
                  <span className="font-semibold text-esynapse-600 dark:text-esynapse-300">Periodo OIML D10: {perTxt(c)}</span>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* Modal punto */}
      <Modal abierto={modalPunto} titulo={puntoEdit ? 'Editar punto' : 'Nuevo punto nominal'} onCerrar={() => setModalPunto(false)} ancho="max-w-sm">
        <div className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Valor nominal</span>
            <input className="input-esynapse" value={formPunto.valor_nominal} onChange={(e) => setFormPunto({ valor_nominal: e.target.value })} placeholder="5 bar, 10 bar…" />
          </label>
          <div className="flex justify-end gap-2">
            <button onClick={() => setModalPunto(false)} className="btn-secondary">Cancelar</button>
            <button onClick={guardarPunto} className="btn-primary">{puntoEdit ? 'Guardar' : 'Crear'}</button>
          </div>
        </div>
      </Modal>

      {/* Modal año */}
      <Modal abierto={modalAnio} titulo="Agregar año de calibración" onCerrar={() => setModalAnio(false)} ancho="max-w-xs">
        <div className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Año</span>
            <input type="number" className="input-esynapse" value={formAnio} onChange={(e) => setFormAnio(e.target.value)} placeholder="2025" />
          </label>
          <p className="text-xs text-slate-400">Se agrega una fila en blanco para todos los puntos. El EMP se prellena con el del año anterior (puedes cambiarlo).</p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setModalAnio(false)} className="btn-secondary">Cancelar</button>
            <button onClick={agregarAnio} className="btn-primary">Agregar</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
