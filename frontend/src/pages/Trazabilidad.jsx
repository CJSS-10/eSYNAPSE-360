import { useCallback, useEffect, useState } from 'react'
import { FileText, Plus, Pencil, Trash2, Link2 } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { api } from '../lib/api.js'
import { useConfirm } from '../context/ConfirmContext.jsx'

// Editor del árbol de Cartas de Trazabilidad (por magnitud + procedimiento).
// Un eslabón puede tener VARIOS padres (relaciones convergentes) y se ordena por nivel.
const NODO_VACIO = {
  entidad: '', descripcion: '', codigo: '', procedimiento: '',
  certificado: '', incertidumbre: '', nota: '', equipo: '', nivel: 1, padres: [],
}
const IB = 'rounded p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'

export default function Trazabilidad({ puedeEditar }) {
  const confirmar = useConfirm()
  const [cartas, setCartas] = useState([])
  const [sel, setSel] = useState(null)
  const [equipos, setEquipos] = useState([])
  const [error, setError] = useState('')
  const [modalCarta, setModalCarta] = useState(false)
  const [formCarta, setFormCarta] = useState({ magnitud: '', procedimiento_calibracion: '' })
  const [modalNodo, setModalNodo] = useState(false)
  const [formNodo, setFormNodo] = useState(NODO_VACIO)
  const [nodoEdit, setNodoEdit] = useState(null)

  const cargarCartas = useCallback(() => {
    api.cartasTrazabilidad.listar().then((d) => setCartas(d.results ?? d)).catch((e) => setError(e.message))
  }, [])
  useEffect(() => { cargarCartas() }, [cargarCartas])
  useEffect(() => { api.equipos.listar('?incluir_inactivos=1').then((d) => setEquipos(d.results ?? d)).catch(() => {}) }, [])

  const abrirCarta = async (id) => {
    setError('')
    try { setSel(await api.cartasTrazabilidad.detalle(id)) } catch (e) { setError(e.message) }
  }
  const refrescar = async () => { if (sel) setSel(await api.cartasTrazabilidad.detalle(sel.id)) }

  const crearCarta = async () => {
    if (!formCarta.magnitud.trim()) { setError('Indica la magnitud.'); return }
    try {
      const c = await api.cartasTrazabilidad.crear(formCarta)
      setModalCarta(false); setFormCarta({ magnitud: '', procedimiento_calibracion: '' })
      cargarCartas(); abrirCarta(c.id)
    } catch (e) { setError(e.message) }
  }

  const eliminarCarta = async () => {
    if (!sel) return
    if (!await confirmar({ titulo: 'Eliminar carta', mensaje: `¿Eliminar la carta de ${sel.magnitud}? Se desactiva (no se borra).`, textoConfirmar: 'Eliminar', peligro: true })) return
    try { await api.cartasTrazabilidad.eliminar(sel.id); setSel(null); cargarCartas() } catch (e) { setError(e.message) }
  }

  const nodos = sel?.nodos || []
  const nombreNodo = (n) => n.entidad || n.descripcion || n.codigo || ('#' + n.id)

  const abrirNodoNuevo = (padre) => {
    setNodoEdit(null)
    const base = { ...NODO_VACIO, padres: [] }
    if (padre) {
      base.padres = [padre.id]
      base.nivel = (padre.nivel || 1) + 1
    }
    setFormNodo(base); setModalNodo(true)
  }
  const abrirNodoEdit = (n) => {
    setNodoEdit(n.id)
    setFormNodo({
      entidad: n.entidad || '', descripcion: n.descripcion || '', codigo: n.codigo || '',
      procedimiento: n.procedimiento || '', certificado: n.certificado || '',
      incertidumbre: n.incertidumbre || '', nota: n.nota || '', equipo: n.equipo || '',
      nivel: n.nivel || 1, padres: [...(n.padres || [])],
    })
    setModalNodo(true)
  }

  const togglePadre = (id) => setFormNodo((f) => {
    const ps = f.padres || []
    return { ...f, padres: ps.includes(id) ? ps.filter((x) => x !== id) : [...ps, id] }
  })

  const avisoPendiente = async (resp) => {
    if (resp?.pendiente) {
      await confirmar({
        titulo: 'Cambio pendiente de aprobación',
        mensaje: resp.detail || 'El cambio quedó registrado y pendiente de aprobación por un supervisor.',
        textoConfirmar: 'Entendido', textoCancelar: 'Cerrar',
      })
      return true
    }
    return false
  }

  const guardarNodo = async () => {
    try {
      const data = { ...formNodo, carta: sel.id, equipo: formNodo.equipo || null, padres: formNodo.padres || [] }
      const resp = nodoEdit
        ? await api.nodosTrazabilidad.editar(nodoEdit, data)
        : await api.nodosTrazabilidad.crear(data)
      setModalNodo(false); await avisoPendiente(resp); await refrescar()
    } catch (e) { setError(e.message) }
  }

  const eliminarNodo = async (n) => {
    if (!await confirmar({ titulo: 'Eliminar eslabón', mensaje: '¿Eliminar este nodo y los que dependen de él?', textoConfirmar: 'Eliminar', peligro: true })) return
    try { const resp = await api.nodosTrazabilidad.eliminar(n.id); await avisoPendiente(resp); await refrescar() } catch (e) { setError(e.message) }
  }
  const rellenar = async (n) => {
    try { await api.nodosTrazabilidad.rellenarDesdeEquipo(n.id); await refrescar() } catch (e) { setError(e.message) }
  }

  // Al elegir un equipo del inventario, muestra sus datos registrados.
  const onEquipoChange = (id) => {
    const eq = equipos.find((x) => String(x.id) === String(id))
    if (!eq) { setFormNodo((f) => ({ ...f, equipo: '' })); return }
    setFormNodo((f) => ({
      ...f, equipo: id,
      entidad: eq.proveedor_calibracion || f.entidad,
      descripcion: eq.nombre || f.descripcion,
      codigo: eq.codigo || f.codigo,
      certificado: eq.n_certificado || f.certificado,
    }))
  }

  const imprimir = async () => {
    setError('')
    try {
      const blob = await api.cartasTrazabilidad.pdf(sel.id)
      const url = URL.createObjectURL(blob); window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  const niveles = [...new Set(nodos.map((n) => n.nivel || 1))].sort((a, b) => a - b)
  const porNivel = (lv) => nodos.filter((n) => (n.nivel || 1) === lv).sort((a, b) => (a.orden || 0) - (b.orden || 0))
  const nombrePadres = (n) => (n.padres || [])
    .map((pid) => { const p = nodos.find((x) => x.id === pid); return p ? nombreNodo(p) : '' })
    .filter(Boolean).join(', ')

  return (
    <div className="space-y-3">
      {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="flex flex-wrap items-center gap-3">
        <select className="input-esynapse w-72" value={sel?.id || ''} onChange={(e) => e.target.value && abrirCarta(e.target.value)}>
          <option value="">Selecciona una carta…</option>
          {cartas.map((c) => <option key={c.id} value={c.id}>{c.magnitud}{c.procedimiento_calibracion ? ` · ${c.procedimiento_calibracion}` : ''}</option>)}
        </select>
        {puedeEditar && (
          <button onClick={() => { setError(''); setModalCarta(true) }} className="btn-secondary">
            <Plus className="h-4 w-4" /> Nueva carta
          </button>
        )}
        {sel && (
          <button onClick={imprimir} className="btn-secondary ml-auto" title="Generar PDF del diagrama de trazabilidad">
            <FileText className="h-4 w-4" /> Generar PDF
          </button>
        )}
        {sel && puedeEditar && (
          <button onClick={eliminarCarta} className="btn-secondary text-red-500"><Trash2 className="h-4 w-4" /> Eliminar carta</button>
        )}
      </div>

      {!sel && <p className="py-8 text-center text-sm text-slate-400">Selecciona o crea una carta para armar su árbol de trazabilidad.</p>}

      {sel && (
        <div className="card-esynapse space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Carta de Trazabilidad — {sel.magnitud}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{sel.procedimiento_calibracion || 'Sin procedimiento'} · {nodos.length} eslabón(es)</p>
            </div>
            {puedeEditar && (
              <button onClick={() => abrirNodoNuevo(null)} className="btn-secondary"><Plus className="h-4 w-4" /> Agregar eslabón</button>
            )}
          </div>

          {nodos.length === 0
            ? <p className="py-6 text-center text-xs text-slate-400">Sin eslabones. Empieza por el patrón nacional/internacional (Nivel 1).</p>
            : niveles.map((lv) => (
              <div key={lv}>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Nivel {lv}</p>
                <div className="mt-1 space-y-1">
                  {porNivel(lv).map((n) => (
                    <div key={n.id} className="flex items-center gap-1.5 rounded-md border border-slate-200 px-2 py-1.5 dark:border-slate-700">
                      <div className="min-w-0 flex-1">
                        <span className="text-sm font-medium">{n.entidad || n.descripcion || '(sin nombre)'}</span>
                        {n.descripcion && n.entidad && <span className="text-xs text-slate-500 dark:text-slate-400"> · {n.descripcion}</span>}
                        {n.codigo && <span className="ml-1 font-mono text-xs text-slate-500">[{n.codigo}]</span>}
                        {n.equipo_codigo && <span className="ml-1 rounded bg-esynapse-500/10 px-1 text-[10px] text-esynapse-600 dark:text-esynapse-300">↳ {n.equipo_codigo}</span>}
                        {(n.padres || []).length > 0 && <span className="block text-[11px] text-slate-400">Es trazable a: {nombrePadres(n)}</span>}
                      </div>
                      {puedeEditar && (
                        <>
                          <button onClick={() => abrirNodoNuevo(n)} className={IB} title="Agregar un eslabón que se calibra con este"><Plus className="h-4 w-4" /></button>
                          {n.equipo && <button onClick={() => rellenar(n)} className={IB} title="Rellenar datos desde el equipo enlazado"><Link2 className="h-4 w-4" /></button>}
                          <button onClick={() => abrirNodoEdit(n)} className={IB} title="Editar"><Pencil className="h-4 w-4" /></button>
                          <button onClick={() => eliminarNodo(n)} className={`${IB} text-red-500`} title="Eliminar"><Trash2 className="h-4 w-4" /></button>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          <p className="text-xs text-slate-400">Cada eslabón puede ser "trazable a" varios patrones superiores; en el PDF se dibuja una flecha desde cada uno.</p>
        </div>
      )}

      <Modal abierto={modalCarta} titulo="Nueva carta de trazabilidad" onCerrar={() => setModalCarta(false)} ancho="max-w-md">
        <div className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Magnitud</span>
            <input className="input-esynapse" value={formCarta.magnitud} onChange={(e) => setFormCarta({ ...formCarta, magnitud: e.target.value })} placeholder="Masa, Presión…" />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Procedimiento de calibración</span>
            <input className="input-esynapse" value={formCarta.procedimiento_calibracion} onChange={(e) => setFormCarta({ ...formCarta, procedimiento_calibracion: e.target.value })} placeholder="PC-008…" />
          </label>
          <div className="flex justify-end gap-2">
            <button onClick={() => setModalCarta(false)} className="btn-secondary">Cancelar</button>
            <button onClick={crearCarta} className="btn-primary">Crear</button>
          </div>
        </div>
      </Modal>

      <Modal abierto={modalNodo} titulo={nodoEdit ? 'Editar eslabón' : 'Nuevo eslabón'} onCerrar={() => setModalNodo(false)} ancho="max-w-lg">
        <div className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Equipo del inventario (opcional)</span>
            <select className="input-esynapse" value={formNodo.equipo || ''} onChange={(e) => onEquipoChange(e.target.value)}>
              <option value="">— Patrón / entidad externa —</option>
              {equipos.map((eq) => <option key={eq.id} value={eq.id}>{eq.codigo} · {eq.nombre}</option>)}
            </select>
            <span className="mt-1 block text-[11px] text-slate-400">Al elegir un equipo se copian su proveedor de calibración, nombre, código y certificado.</span>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block"><span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Entidad que calibró</span>
              <input className="input-esynapse" value={formNodo.entidad} onChange={(e) => setFormNodo({ ...formNodo, entidad: e.target.value })} placeholder="INACAL-DM, PESATEC…" /></label>
            <label className="block"><span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Descripción del patrón</span>
              <input className="input-esynapse" value={formNodo.descripcion} onChange={(e) => setFormNodo({ ...formNodo, descripcion: e.target.value })} placeholder="Pesa F1 (10 kg)" /></label>
            <label className="block"><span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Código de identificación</span>
              <input className="input-esynapse" value={formNodo.codigo} onChange={(e) => setFormNodo({ ...formNodo, codigo: e.target.value })} placeholder="MP-08" /></label>
            <label className="block"><span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Nivel jerárquico</span>
              <select className="input-esynapse" value={formNodo.nivel || 1} onChange={(e) => setFormNodo({ ...formNodo, nivel: Number(e.target.value) })}>
                {[1, 2, 3, 4, 5, 6].map((nv) => <option key={nv} value={nv}>Nivel {nv}</option>)}
              </select></label>
            <label className="block"><span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">N° de certificado</span>
              <input className="input-esynapse" value={formNodo.certificado} onChange={(e) => setFormNodo({ ...formNodo, certificado: e.target.value })} placeholder="LM-C-313-2022" /></label>
            <label className="block"><span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Incertidumbre (U)</span>
              <input className="input-esynapse" value={formNodo.incertidumbre} onChange={(e) => setFormNodo({ ...formNodo, incertidumbre: e.target.value })} placeholder="U = 3,0 mg" /></label>
          </div>
          <label className="block"><span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Procedimiento / método</span>
            <textarea className="input-esynapse h-16" value={formNodo.procedimiento} onChange={(e) => setFormNodo({ ...formNodo, procedimiento: e.target.value })} placeholder="ME-003 / método de calibración…" /></label>
          <label className="block"><span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Nota (opcional)</span>
            <textarea className="input-esynapse h-16" value={formNodo.nota} onChange={(e) => setFormNodo({ ...formNodo, nota: e.target.value })} /></label>
          <div className="block">
            <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Es trazable a (uno o varios patrones superiores)</span>
            <div className="max-h-28 space-y-1 overflow-y-auto rounded border border-slate-200 p-2 dark:border-slate-700">
              {nodos.filter((n) => n.id !== nodoEdit).map((n) => (
                <label key={n.id} className="flex cursor-pointer items-center gap-2 text-xs">
                  <input type="checkbox" checked={(formNodo.padres || []).includes(n.id)} onChange={() => togglePadre(n.id)} className="h-3.5 w-3.5 accent-esynapse-600" />
                  <span>Nivel {n.nivel || 1} · {nombreNodo(n)}{n.codigo ? ` [${n.codigo}]` : ''}</span>
                </label>
              ))}
              {nodos.filter((n) => n.id !== nodoEdit).length === 0 && <span className="text-xs text-slate-400">Aún no hay otros eslabones para enlazar.</span>}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setModalNodo(false)} className="btn-secondary">Cancelar</button>
            <button onClick={guardarNodo} className="btn-primary">{nodoEdit ? 'Guardar' : 'Agregar'}</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
