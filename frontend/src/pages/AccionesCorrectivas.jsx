import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Download, Plus, Search, Wrench, XCircle } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'

const FUENTES = [
  ['auditoria_interna', 'Auditoría interna'], ['auditoria_externa', 'Auditoría externa'],
  ['revision_direccion', 'Revisión por la Dirección'], ['queja', 'Queja'], ['otros', 'Otros'],
]

const NORMAS = [
  ['iso_9001', 'ISO 9001'], ['iso_14001', 'ISO 14001'],
  ['iso_45001', 'ISO 45001 / Ley 29783'], ['iso_17025', 'NTP ISO/IEC 17025'],
]

const COLOR_NORMA = {
  'ISO 9001': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'ISO 14001': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  'ISO 45001 / Ley 29783': 'bg-red-500/15 text-red-600 dark:text-red-400',
  'NTP ISO/IEC 17025': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
}

const CHIP_NORMA = {
  iso_9001: 'border-esynapse-500 bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  iso_14001: 'border-emerald-500 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  iso_45001: 'border-red-500 bg-red-500/15 text-red-600 dark:text-red-400',
  iso_17025: 'border-amber-500 bg-amber-500/15 text-amber-600 dark:text-amber-400',
}

const ESTADOS = [
  ['registrada', 'Registrada'], ['en_analisis', 'En análisis de causa'],
  ['en_implementacion', 'En implementación'], ['en_verificacion', 'En verificación'],
  ['cerrada_conforme', 'Cerrada conforme'], ['cerrada_sin_ac', 'Cerrada (solo corrección)'],
]

const COLOR_ESTADO = {
  'Registrada': 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
  'En análisis de causa': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  'En implementación': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'En verificación de eficacia': 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
  'Cerrada conforme': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  'Cerrada (solo corrección)': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
}

const PASOS = ['registrada', 'en_analisis', 'en_implementacion', 'en_verificacion', 'cerrada']
const NOMBRE_PASO = ['Registro', 'Análisis de causa', 'Implementación', 'Verificación', 'Cierre']

const FORM_VACIO = {
  fuente: 'auditoria_interna', fuente_detalle: '', normas: [], hallazgo: '',
  auditor: '', auditado: '', requisito_auditado: '', descripcion_nc: '', responsable: '',
}

export default function AccionesCorrectivas() {
  const { tienePermiso } = useAuth()
  const [items, setItems] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [hallazgos, setHallazgos] = useState([])
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('')
  const [soloAbiertas, setSoloAbiertas] = useState(false)
  const [modalCrear, setModalCrear] = useState(false)
  const [detalle, setDetalle] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [error, setError] = useState('')
  // Formularios por etapa
  const [evalForm, setEvalForm] = useState({ significancia: 'bajo', analisis_extension: '', requiere_ac: 'true', justificacion: '' })
  const [porques, setPorques] = useState(['', '', '', '', ''])
  const [causaRaiz, setCausaRaiz] = useState('')
  const [cambiosSig, setCambiosSig] = useState(false)
  const [actRiesgos, setActRiesgos] = useState(false)
  const [accForm, setAccForm] = useState({ tipo: 'correctiva', descripcion: '', fecha_propuesta: '', responsable: '' })
  const [verificador, setVerificador] = useState('')
  const [completar, setCompletar] = useState({}) // {accionId: {verificacion, archivo}}
  const [eficaciaTxt, setEficaciaTxt] = useState('')

  const cargar = useCallback(async () => {
    const p = new URLSearchParams()
    if (buscar) p.set('buscar', buscar)
    if (estado) p.set('estado', estado)
    if (soloAbiertas) p.set('abiertas', '1')
    const data = await api.sac.listar(`?${p}`)
    setItems(data.results ?? data)
  }, [buscar, estado, soloAbiertas])

  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
    api.usuarios.listar().then((d) => setUsuarios(d.results ?? d)).catch(() => {})
    api.hallazgos.listar('?estado=registrado').then((d) => setHallazgos(d.results ?? d)).catch(() => {})
  }, [])

  const abrirDetalle = async (id) => {
    setError('')
    const d = await api.sac.detalle(id)
    setDetalle(d)
    setEvalForm({ significancia: d.significancia || 'bajo', analisis_extension: d.analisis_extension || '',
      requiere_ac: 'true', justificacion: d.justificacion_evaluacion || '' })
    setPorques(d.porques?.length ? d.porques : ['', '', '', '', ''])
    setCausaRaiz(d.causa_raiz || '')
    setCambiosSig(Boolean(d.aplica_cambios_sig))
    setActRiesgos(Boolean(d.aplica_actualizar_riesgos))
    setVerificador(d.verificador || '')
    setEficaciaTxt('')
    setCompletar({})
    setAccForm({ tipo: 'correctiva', descripcion: '', fecha_propuesta: '', responsable: '' })
  }

  const refrescar = async () => { await cargar(); if (detalle) setDetalle(await api.sac.detalle(detalle.id)) }
  const accion = async (fn) => {
    setError('')
    try { await fn(); await refrescar() } catch (e) { setError(e.message) }
  }

  const crear = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const datos = { ...form, normas_aplicables: form.normas }
      delete datos.normas
      if (!datos.hallazgo) delete datos.hallazgo
      if (!datos.responsable) delete datos.responsable
      await api.sac.crear(datos)
      setModalCrear(false); setForm(FORM_VACIO); await cargar()
    } catch (e2) { setError(e2.message) }
  }

  const pasoActual = (d) => {
    if (!d) return -1
    if (d.estado.startsWith('cerrada')) return 4
    return PASOS.indexOf(d.estado)
  }

  const sel = (etiqueta, valor, onChange, opciones, props = {}) => (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">{etiqueta}</label>
      <select className="input-esynapse" value={valor} onChange={onChange} {...props}>
        {opciones.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
      </select>
    </div>
  )

  const esAuditoria = form.fuente.startsWith('auditoria')

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Wrench className="h-6 w-6 text-esynapse-500" />
          <h1 className="text-2xl font-bold">Acciones Correctivas</h1>
        </div>
        {tienePermiso('acciones_correctivas', 'crear') && (
          <button onClick={() => { setForm(FORM_VACIO); setError(''); setModalCrear(true) }} className="btn-primary">
            <Plus className="h-4 w-4" /> Nueva SAC
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input-esynapse w-64 pl-9" placeholder="Buscar código, descripción…"
            value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <select className="input-esynapse w-52" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={soloAbiertas} onChange={(e) => setSoloAbiertas(e.target.checked)}
            className="h-4 w-4 accent-esynapse-600" />
          Solo abiertas
        </label>
      </div>

      <div className="card-esynapse overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-4 py-3">N° SAC</th>
              <th className="px-4 py-3">Procedencia</th>
              <th className="px-4 py-3">Descripción</th>
              <th className="px-4 py-3">Responsable</th>
              <th className="px-4 py-3">Acciones</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Cierre</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.id} onClick={() => abrirDetalle(s.id)}
                className="cursor-pointer border-b border-slate-100 transition last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 font-mono text-xs font-medium">{s.codigo}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{s.fuente_display}</td>
                <td className="max-w-xs truncate px-4 py-3" title={s.descripcion_nc}>{s.descripcion_nc}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{s.responsable_nombre || '—'}</td>
                <td className="px-4 py-3 text-xs">{s.avance_acciones}</td>
                <td className="px-4 py-3">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_ESTADO[s.estado_display] || 'bg-slate-500/15'}`}>
                    {s.estado_display}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs">{s.fecha_cierre ? new Date(s.fecha_cierre).toLocaleDateString('es-PE') : '—'}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-400">Sin solicitudes</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Crear */}
      <Modal abierto={modalCrear} titulo="Nueva Solicitud de Acción Correctiva" onCerrar={() => setModalCrear(false)}>
        <form onSubmit={crear} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {sel('Procedencia', form.fuente, (e) => setForm({ ...form, fuente: e.target.value }), FUENTES)}
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Hallazgo vinculado (opcional)</label>
              <select className="input-esynapse" value={form.hallazgo} onChange={(e) => setForm({ ...form, hallazgo: e.target.value })}>
                <option value="">— Sin vincular —</option>
                {hallazgos.map((h) => <option key={h.id} value={h.id}>{h.codigo} — {h.proceso}</option>)}
              </select>
            </div>
          </div>
          {esAuditoria && (
            <div className="grid grid-cols-3 gap-3">
              <input className="input-esynapse" placeholder="Auditor" value={form.auditor} onChange={(e) => setForm({ ...form, auditor: e.target.value })} />
              <input className="input-esynapse" placeholder="Auditado" value={form.auditado} onChange={(e) => setForm({ ...form, auditado: e.target.value })} />
              <input className="input-esynapse" placeholder="Requisito auditado" value={form.requisito_auditado} onChange={(e) => setForm({ ...form, requisito_auditado: e.target.value })} />
            </div>
          )}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Normas</label>
            <div className="flex flex-wrap gap-2">
              {NORMAS.map(([clave, nombre]) => (
                <label key={clave} className={`cursor-pointer rounded-lg border px-2.5 py-1.5 text-xs transition ${
                  form.normas.includes(clave) ? CHIP_NORMA[clave]
                  : 'border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-300'}`}>
                  <input type="checkbox" className="hidden" checked={form.normas.includes(clave)}
                    onChange={(e) => setForm({ ...form, normas: e.target.checked ? [...form.normas, clave] : form.normas.filter((n) => n !== clave) })} />
                  {nombre}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Descripción de la No Conformidad</label>
            <textarea className="input-esynapse" rows={3} required value={form.descripcion_nc}
              onChange={(e) => setForm({ ...form, descripcion_nc: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Responsable del tratamiento</label>
            <select className="input-esynapse" value={form.responsable} onChange={(e) => setForm({ ...form, responsable: e.target.value })}>
              <option value="">— Por designar —</option>
              {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
            </select>
          </div>
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalCrear(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">Registrar SAC</button>
          </div>
        </form>
      </Modal>

      {/* Detalle */}
      <Modal abierto={Boolean(detalle)} titulo={detalle ? `${detalle.codigo} — Solicitud de Acción Correctiva` : ''}
        onCerrar={() => setDetalle(null)} ancho="max-w-3xl">
        {detalle && (
          <div className="space-y-4 text-sm">
            {/* Stepper */}
            <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-3 dark:bg-slate-800/60">
              {NOMBRE_PASO.map((nombre, i) => {
                const actual = pasoActual(detalle)
                const esActual = i === actual && !detalle.estado.startsWith('cerrada')
                const completado = i < actual || (detalle.estado.startsWith('cerrada') && i <= 4)
                return (
                  <div key={nombre} className="flex flex-1 items-center">
                    <div className="flex flex-1 flex-col items-center gap-1">
                      <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                        completado ? 'bg-emerald-500 text-white'
                        : esActual ? 'bg-esynapse-600 text-white ring-4 ring-esynapse-600/25'
                        : 'bg-slate-300 text-slate-600 dark:bg-slate-700 dark:text-slate-400'}`}>
                        {completado ? '✓' : i + 1}
                      </div>
                      <span className={`text-center text-[10px] leading-tight ${
                        esActual ? 'font-semibold text-esynapse-600 dark:text-esynapse-300'
                        : completado ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-slate-400'}`}>{nombre}</span>
                    </div>
                    {i < 4 && <div className={`mb-4 h-0.5 flex-1 ${completado ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-700'}`} />}
                  </div>
                )
              })}
            </div>

            {detalle.normas_display?.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {detalle.normas_display.map((n) => (
                  <span key={n} className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_NORMA[n] || 'bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>
                    {n}
                  </span>
                ))}
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 dark:text-slate-400">
              <p><strong className="text-slate-700 dark:text-slate-200">Procedencia:</strong> {detalle.fuente_display}</p>
              {detalle.hallazgo_codigo && <p><strong className="text-slate-700 dark:text-slate-200">Hallazgo:</strong> {detalle.hallazgo_codigo}</p>}
              {detalle.requisito_auditado && <p><strong className="text-slate-700 dark:text-slate-200">Requisito:</strong> {detalle.requisito_auditado}</p>}
              {detalle.significancia && <p><strong className="text-slate-700 dark:text-slate-200">Significancia:</strong> {detalle.significancia_display}</p>}
              <p><strong className="text-slate-700 dark:text-slate-200">Responsable:</strong> {detalle.responsable_nombre || 'Por designar'}</p>
              {detalle.verificador_nombre && <p><strong className="text-slate-700 dark:text-slate-200">Verificador:</strong> {detalle.verificador_nombre}</p>}
            </div>

            <div className="rounded-lg bg-slate-100 p-3 text-xs dark:bg-slate-800">
              <p className="mb-1 font-semibold text-slate-700 dark:text-slate-200">No Conformidad</p>
              <p className="text-slate-600 dark:text-slate-300">{detalle.descripcion_nc}</p>
            </div>

            {/* ETAPA 1: Evaluación */}
            {detalle.estado === 'registrada' && tienePermiso('acciones_correctivas', 'editar') && (
              <div className="space-y-2 rounded-lg border border-esynapse-600/30 bg-esynapse-600/5 p-3">
                <p className="text-xs font-semibold text-esynapse-600 dark:text-esynapse-300">Evaluación de la necesidad de AC (6.4)</p>
                <div className="grid grid-cols-2 gap-2">
                  {sel('Significancia', evalForm.significancia, (e) => setEvalForm({ ...evalForm, significancia: e.target.value }), [['bajo','Bajo'],['alto','Alto']])}
                  {sel('¿Requiere acción correctiva?', evalForm.requiere_ac, (e) => setEvalForm({ ...evalForm, requiere_ac: e.target.value }), [['true','Sí — requiere AC'],['false','No — solo corrección']])}
                </div>
                <textarea className="input-esynapse" rows={2} placeholder="Análisis de la extensión de la NC"
                  value={evalForm.analisis_extension} onChange={(e) => setEvalForm({ ...evalForm, analisis_extension: e.target.value })} />
                <textarea className="input-esynapse" rows={2} placeholder="Justificación (impacto, recurrencia, riesgo...)"
                  value={evalForm.justificacion} onChange={(e) => setEvalForm({ ...evalForm, justificacion: e.target.value })} />
                <button onClick={() => accion(() => api.sac.evaluar(detalle.id, { ...evalForm, requiere_ac: evalForm.requiere_ac === 'true' }))}
                  className="btn-primary !py-1.5 text-xs">Registrar evaluación</button>
              </div>
            )}

            {/* ETAPA 2: Análisis de causa */}
            {detalle.estado === 'en_analisis' && tienePermiso('acciones_correctivas', 'editar') && (
              <div className="space-y-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">Análisis de causa — 5 Porqués (6.5)</p>
                {porques.map((p, i) => (
                  <input key={i} className="input-esynapse" placeholder={`${i + 1}. ¿Por qué?`}
                    value={p} onChange={(e) => setPorques(porques.map((x, j) => j === i ? e.target.value : x))} />
                ))}
                <textarea className="input-esynapse" rows={2} placeholder="Causa raíz identificada"
                  value={causaRaiz} onChange={(e) => setCausaRaiz(e.target.value)} />
                <div className="flex gap-4 text-xs">
                  <label className="flex cursor-pointer items-center gap-1.5">
                    <input type="checkbox" className="h-3.5 w-3.5 accent-esynapse-600" checked={cambiosSig} onChange={(e) => setCambiosSig(e.target.checked)} />
                    Aplica cambios al SIG
                  </label>
                  <label className="flex cursor-pointer items-center gap-1.5">
                    <input type="checkbox" className="h-3.5 w-3.5 accent-esynapse-600" checked={actRiesgos} onChange={(e) => setActRiesgos(e.target.checked)} />
                    Actualizar matriz de riesgos
                  </label>
                </div>
                <button onClick={() => accion(() => api.sac.registrarAnalisis(detalle.id, {
                  porques: porques.filter((p) => p.trim()), causa_raiz: causaRaiz,
                  aplica_cambios_sig: cambiosSig, aplica_actualizar_riesgos: actRiesgos }))}
                  className="btn-secondary !py-1.5 text-xs">Guardar análisis</button>
              </div>
            )}

            {/* Análisis registrado (lectura) */}
            {detalle.causa_raiz && detalle.estado !== 'en_analisis' && (
              <div className="rounded-lg bg-amber-500/10 p-3 text-xs">
                <p className="mb-1 font-semibold text-amber-600 dark:text-amber-400">Causa raíz</p>
                <p className="text-slate-600 dark:text-slate-300">{detalle.causa_raiz}</p>
                {detalle.porques?.length > 0 && (
                  <ol className="mt-1 list-inside list-decimal text-slate-500 dark:text-slate-400">
                    {detalle.porques.map((p, i) => <li key={i}>{p}</li>)}
                  </ol>
                )}
              </div>
            )}

            {/* Acciones (siempre visibles si existen) */}
            {detalle.acciones.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Correcciones y acciones</p>
                {detalle.acciones.map((acc) => (
                  <div key={acc.id} className="rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-800">
                    <div className="flex items-center justify-between">
                      <p>
                        <span className={`mr-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                          acc.tipo === 'correccion' ? 'bg-slate-500/15 text-slate-500' : 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300'}`}>
                          {acc.tipo_display}
                        </span>
                        {acc.descripcion}
                      </p>
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        acc.estado === 'completada' ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-amber-500/15 text-amber-600 dark:text-amber-400'}`}>
                        {acc.estado_display}
                      </span>
                    </div>
                    <p className="text-slate-500 dark:text-slate-400">
                      Propuesta: {acc.fecha_propuesta} · {acc.responsable_nombre || 'sin responsable'}
                      {acc.fecha_completada && ` · Ejecutada: ${acc.fecha_completada}`}
                      {acc.evidencia_url && (
                        <a href={acc.evidencia_url} target="_blank" rel="noreferrer" className="ml-1 text-esynapse-500 underline">
                          <Download className="inline h-3 w-3" /> evidencia
                        </a>
                      )}
                    </p>
                    {acc.verificacion && <p className="text-emerald-600 dark:text-emerald-400">Verificación: {acc.verificacion}</p>}
                    {/* Completar (etapa implementación) */}
                    {detalle.estado === 'en_implementacion' && acc.estado === 'pendiente' && tienePermiso('acciones_correctivas', 'editar') && (
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <input className="input-esynapse !py-1 flex-1 text-xs" placeholder="Verificación de la acción"
                          value={completar[acc.id]?.verificacion || ''}
                          onChange={(e) => setCompletar({ ...completar, [acc.id]: { ...completar[acc.id], verificacion: e.target.value } })} />
                        <input type="file" className="w-44 text-xs text-slate-500 file:mr-1 file:rounded file:border-0 file:bg-slate-200 file:px-2 file:py-1 file:text-xs dark:file:bg-slate-700 dark:file:text-slate-200"
                          onChange={(e) => setCompletar({ ...completar, [acc.id]: { ...completar[acc.id], archivo: e.target.files[0] } })} />
                        <button onClick={() => accion(async () => {
                          const fd = new FormData()
                          fd.append('accion_id', acc.id)
                          fd.append('verificacion', completar[acc.id]?.verificacion || '')
                          if (completar[acc.id]?.archivo) fd.append('evidencia', completar[acc.id].archivo)
                          await api.sac.completarAccion(detalle.id, fd)
                        })} className="btn-primary !py-1 text-xs">
                          <CheckCircle2 className="h-3 w-3" /> Completar
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Agregar acción (análisis o implementación) */}
            {['en_analisis', 'en_implementacion'].includes(detalle.estado) && tienePermiso('acciones_correctivas', 'editar') && (
              <div className="grid grid-cols-12 items-end gap-2 rounded-lg border border-dashed border-slate-300 p-2 dark:border-slate-700">
                <div className="col-span-3">
                  {sel('Tipo', accForm.tipo, (e) => setAccForm({ ...accForm, tipo: e.target.value }), [['correctiva','Acción correctiva'],['correccion','Corrección']])}
                </div>
                <input className="input-esynapse col-span-4 !py-1.5 text-xs" placeholder="Descripción de la acción"
                  value={accForm.descripcion} onChange={(e) => setAccForm({ ...accForm, descripcion: e.target.value })} />
                <input type="date" className="input-esynapse col-span-2 !py-1.5 text-xs" value={accForm.fecha_propuesta}
                  onChange={(e) => setAccForm({ ...accForm, fecha_propuesta: e.target.value })} />
                <select className="input-esynapse col-span-2 !py-1.5 text-xs" value={accForm.responsable}
                  onChange={(e) => setAccForm({ ...accForm, responsable: e.target.value })}>
                  <option value="">Responsable</option>
                  {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
                </select>
                <button disabled={!accForm.descripcion || !accForm.fecha_propuesta}
                  onClick={() => accion(async () => {
                    const datos = { ...accForm }
                    if (!datos.responsable) delete datos.responsable
                    await api.sac.agregarAccion(detalle.id, datos)
                    setAccForm({ tipo: 'correctiva', descripcion: '', fecha_propuesta: '', responsable: '' })
                  })} className="btn-secondary col-span-1 !px-2 !py-1.5 text-xs">
                  <Plus className="h-3.5 w-3.5" />
                </button>
              </div>
            )}

            {/* Aprobar plan */}
            {detalle.estado === 'en_analisis' && tienePermiso('acciones_correctivas', 'aprobar') && (
              <div className="flex items-end gap-2 rounded-lg border border-esynapse-600/30 p-2">
                <div className="flex-1">
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Verificador de eficacia (6.6.3)</label>
                  <select className="input-esynapse" value={verificador} onChange={(e) => setVerificador(e.target.value)}>
                    <option value="">— Designar —</option>
                    {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
                  </select>
                </div>
                <button onClick={() => accion(() => api.sac.aprobarPlan(detalle.id, verificador))}
                  className="btn-primary !py-1.5 text-xs">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Aprobar plan → Implementación
                </button>
              </div>
            )}

            {/* Verificación de eficacia */}
            {detalle.estado === 'en_verificacion' && tienePermiso('acciones_correctivas', 'aprobar') && (
              <div className="space-y-2 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3">
                <p className="text-xs font-semibold text-violet-600 dark:text-violet-400">Evaluación de la eficacia (6.8)</p>
                <textarea className="input-esynapse" rows={2} placeholder="¿Las acciones eliminaron la causa y previenen la recurrencia? Evidencias…"
                  value={eficaciaTxt} onChange={(e) => setEficaciaTxt(e.target.value)} />
                <div className="flex gap-2">
                  <button onClick={() => accion(() => api.sac.verificarEficacia(detalle.id, true, eficaciaTxt))} className="btn-primary !py-1.5 text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Eficaz → Cerrar conforme
                  </button>
                  <button onClick={() => accion(() => api.sac.verificarEficacia(detalle.id, false, eficaciaTxt))} className="btn-danger !py-1.5 text-xs">
                    <XCircle className="h-3.5 w-3.5" /> No eficaz → Reanálisis
                  </button>
                </div>
              </div>
            )}

            {/* Cierre */}
            {detalle.estado.startsWith('cerrada') && (
              <div className="rounded-lg bg-emerald-500/10 p-3 text-xs">
                <p className="mb-1 font-semibold text-emerald-600 dark:text-emerald-400">
                  {detalle.estado_display} — {detalle.fecha_cierre && new Date(detalle.fecha_cierre).toLocaleString('es-PE')}
                </p>
                {detalle.evaluacion_eficacia && <p className="text-slate-600 dark:text-slate-300">{detalle.evaluacion_eficacia}</p>}
                {detalle.hallazgo_codigo && detalle.estado === 'cerrada_conforme' && (
                  <p className="mt-1 text-slate-500 dark:text-slate-400">El hallazgo {detalle.hallazgo_codigo} fue cerrado automáticamente.</p>
                )}
              </div>
            )}

            {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          </div>
        )}
      </Modal>
    </div>
  )
}
