import { useCallback, useEffect, useRef, useState } from 'react'
import { BookOpen, FileText, Lock, Paperclip, Plus, Search, Trash2 } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import BarraPasos from '../components/BarraPasos.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import TablasTNC, { VerTabla } from '../components/TablasTNC.jsx'
import EncabezadoModulo from '../components/ui/EncabezadoModulo.jsx'
import EtapaMini from '../components/ui/EtapaMini.jsx'
import { Vistas } from '../components/NavModulo.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora, hoy } from '../lib/fecha.js'
import { useAbrirDesdeEnlace } from '../lib/enlaces.js'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
// Etapas y colores (regla 10): gris registro · azul tratamiento · ámbar autorización y evaluación · violeta cierre ·
// verde cerrado · rojo anulado.
const PASOS = [['registrado', 'Registro'], ['tratamiento', 'Tratamiento'], ['autorizacion', 'Autorización'],
  ['evaluacion', 'Evaluación'], ['cierre', 'Cierre'], ['cerrado', 'Cerrado']]
const TONO = { registrado: 'gris', tratamiento: 'azul', autorizacion: 'ambar', evaluacion: 'ambar', cierre: 'violeta', cerrado: 'verde', anulado: 'rojo' }
const BADGE = { gris: 'badge badge-gris', ambar: 'badge badge-ambar', azul: 'badge badge-azul', violeta: 'badge badge-violeta', verde: 'badge badge-verde', rojo: 'badge badge-rojo' }
// Niveles de riesgo con la escala del sistema: Alto rojo · Medio ámbar · Bajo verde.
const NIVEL = { alto: 'badge badge-rojo', medio: 'badge badge-ambar', bajo: 'badge badge-verde' }
const sn = (v) => (v == null ? '—' : v ? 'Sí' : 'No')
const SN_OPC = [['', '—'], ['true', 'Sí'], ['false', 'No']]
const aBool = (v) => (v === '' || v == null ? null : v === true || v === 'true')
const deBool = (v) => (v == null ? '' : String(v))

function Seccion({ titulo, tono, children, extra }) {
  const borde = { ambar: 'border-amber-500/30 bg-amber-500/5', azul: 'border-esynapse-600/30 bg-esynapse-600/5', violeta: 'border-violet-500/30 bg-violet-500/5', verde: 'border-emerald-500/30 bg-emerald-500/5' }[tono]
    || 'border-slate-200 dark:border-slate-800'
  return (
    <div className={`space-y-2 rounded-lg border p-3 text-xs ${borde}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">{titulo}</p>
        {extra}
      </div>
      <div className="space-y-2 text-slate-600 dark:text-slate-300">{children}</div>
    </div>
  )
}
const Dato = ({ etiqueta, valor }) => <p><strong className="text-slate-700 dark:text-slate-200">{etiqueta}:</strong> {valor || '—'}</p>
function MsgError({ texto }) {
  const ref = useRef(null)
  useEffect(() => { if (texto) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }, [texto])
  return texto ? <p ref={ref} className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p> : null
}
const Sel = ({ etiqueta, valor, onChange, opciones, disabled }) => (
  <div>{etiqueta && <label className={lbl}>{etiqueta}</label>}
    <select disabled={disabled} className={inp} value={valor ?? ''} onChange={(e) => onChange(e.target.value)}>
      {opciones.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
    </select></div>
)
const abrirPdf = async (promesa, setError) => {
  setError('')
  try { const url = URL.createObjectURL(await promesa); window.open(url, '_blank'); setTimeout(() => URL.revokeObjectURL(url), 60000) } catch (e) { setError(e.message) }
}

const REG_VACIO = { tipo: 'tnc', naturaleza: 'tecnica', categoria: '', area: '', reportado_por: '', fecha_deteccion: '', fecha_reporte: '', fuente: '', queja: '', hallazgo: '', referencias: '', equipos: [], descripcion: '' }
const CAMPOS_TRAT = ['correccion', 'correccion_por', 'correccion_fecha', 'nota_cliente', 'periodo_desde', 'periodo_hasta', 'ultima_condicion', 'notificacion_cliente', 'notificacion_fecha_medio', 'certificado_anulado', 'certificado_reemplazo', 'conclusion_retroactivo']
const CAMPOS_EVAL = ['afecta_validez', 'incumple_sig', 'compromete_competencia', 'nivel_confirmado', 'evaluacion', 'amerita_sac']

export default function TrabajoNoConforme() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const [cat, setCat] = useState(null)
  const [op, setOp] = useState({ quejas: [], hallazgos: [], equipos: [], sacs: [] })
  const [areas, setAreas] = useState([])
  const [trab, setTrab] = useState([])
  const [items, setItems] = useState([])
  const [vista, setVista] = useState('abiertos')
  const [buscar, setBuscar] = useState('')
  const [nivel, setNivel] = useState('')
  const [detalle, setDetalle] = useState(null)
  const [modal, setModal] = useState(false)
  const [tabla, setTabla] = useState(null)
  const [form, setForm] = useState(REG_VACIO)
  const [error, setError] = useState('')

  useEffect(() => {
    api.tnc.catalogos().then(setCat).catch(() => {})
    api.tnc.opciones().then(setOp).catch(() => {})
    api.org.areas().then((x) => setAreas((x.results ?? x).filter((a) => a.is_active !== false))).catch(() => {})
    api.org.trabajadores().then((x) => setTrab((x.results ?? x).filter((t) => t.estado === 'activo'))).catch(() => {})
  }, [])
  const cargar = useCallback(async () => {
    const p = new URLSearchParams()
    if (vista === 'abiertos') p.set('abiertos', '1')
    if (buscar) p.set('buscar', buscar)
    if (nivel) p.set('nivel_riesgo', nivel)
    const d = await api.tnc.listar(`?${p}`)
    setItems(d.results ?? d)
  }, [vista, buscar, nivel])
  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  const abrir = async (id) => { setError(''); setDetalle(await api.tnc.detalle(id)) }

  const registrar = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const datos = { ...form }
      for (const c of ['queja', 'hallazgo', 'fecha_reporte']) if (!datos[c]) datos[c] = null
      const t = await api.tnc.crear(datos)
      setModal(false); await cargar(); setDetalle(t)
    } catch (e2) { setError(e2.message) }
  }
  const optT = [['', '— Seleccionar —'], ...trab.map((t) => [String(t.id), `${t.nombre_completo} (${t.puesto_nombre || ''})`])]
  const comun = { cat, op, areas, trab, optT, verTabla: setTabla }

  useAbrirDesdeEnlace(abrir)   // enlace directo ?abrir=<id> (búsqueda, Mis tareas, campana)

  return (
    <div className="space-y-4">
      <EncabezadoModulo seccion="Laboratorio" titulo="Trabajo no conforme"
        descripcion="Trabajos y salidas no conformes: se registran, se tratan según su nivel de riesgo, se autoriza la reanudación, el Área SIG evalúa su importancia y se cierran."
        acciones={<>
          <button onClick={() => setTabla(2)} className="btn-secondary"><BookOpen className="h-4 w-4" /> Tablas del procedimiento</button>
          {tienePermiso('trabajo_no_conforme', 'crear') && (
            <button onClick={() => { setForm({ ...REG_VACIO, fecha_deteccion: hoy(), fecha_reporte: hoy() }); setError(''); setModal(true) }} className="btn-primary"><Plus className="h-4 w-4" /> Registrar TNC o SNC</button>
          )}
        </>} />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className={`${inp} w-72 pl-9`} placeholder="Buscar código, descripción, OT o certificado" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <select className={`${inp} w-44`} aria-label="Nivel de riesgo" value={nivel} onChange={(e) => setNivel(e.target.value)}>
          <option value="">Todos los niveles</option>
          {(cat?.niveles || []).map(([v, n]) => <option key={v} value={v}>Nivel {n.toLowerCase()}</option>)}
        </select>
        <div className="ml-auto"><Vistas opciones={[['abiertos', 'Abiertos'], ['todos', 'Todos']]} valor={vista} onChange={setVista} /></div>
      </div>

      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig min-w-[1000px]">
          <thead><tr>
            <th>N° de registro</th><th className="text-center">Tipo</th><th>Descripción</th><th>Área o laboratorio</th>
            <th className="text-right">Detección</th><th className="text-center">Nivel</th><th className="text-center">SAC</th><th className="text-center">Etapa</th>
          </tr></thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id} className="fila" onClick={() => abrir(t.id)}>
                <td className="whitespace-nowrap font-semibold text-esynapse-700 dark:text-esynapse-300">{t.codigo}</td>
                <td className="text-center">{t.tipo.toUpperCase()}</td>
                <td className="max-w-sm"><span className="line-clamp-2" title={t.descripcion}>{t.descripcion}</span></td>
                <td>{t.area_nombre}</td>
                <td className="whitespace-nowrap text-right">{fecha(t.fecha_deteccion)}</td>
                <td className="text-center">{t.nivel_riesgo ? <span className={NIVEL[t.nivel_riesgo]}>{t.nivel_display}</span> : '—'}</td>
                <td className="whitespace-nowrap text-center">{t.sac_codigo || '—'}</td>
                <td className="text-center"><EtapaMini total={6} actual={Math.max(0, PASOS.findIndex(([e]) => e === t.estado))} tono={TONO[t.estado]} texto={t.estado_display} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-center text-slate-400">{vista === 'abiertos' ? 'No hay registros abiertos' : 'Sin registros'}</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal abierto={modal} titulo="Registrar trabajo o salida no conforme" onCerrar={() => setModal(false)} ancho="max-w-3xl">
        <form onSubmit={registrar} className="space-y-3">
          <FormRegistro form={form} setForm={setForm} {...comun} />
          <p className="text-[11px] text-slate-500 dark:text-slate-400">Al registrar se asigna el código TSNC. El Gerente Técnico (o el Gerente SIG si es administrativo) asigna el nivel de riesgo al iniciar el tratamiento.</p>
          <MsgError texto={error} />
          <div className="flex justify-end gap-2"><button type="button" onClick={() => setModal(false)} className="btn-secondary">Cancelar</button><button type="submit" className="btn-primary">Registrar</button></div>
        </form>
      </Modal>

      <Modal abierto={Boolean(detalle) && !modal} titulo={detalle ? `${detalle.codigo} — ${detalle.tipo_display}` : ''} onCerrar={() => { setDetalle(null); cargar() }} panel ancho="max-w-5xl">
        {detalle && <Detalle d={detalle} setD={setDetalle} {...comun} tienePermiso={tienePermiso} confirmar={confirmar} onAnulado={() => { setDetalle(null); cargar() }} />}
      </Modal>
      <TablasTNC tabla={tabla} onCerrar={() => setTabla(null)} />
    </div>
  )
}

function FormRegistro({ form, setForm, cat, op, areas, optT }) {
  const set = (k) => (v) => setForm({ ...form, [k]: v })
  const [filtroEq, setFiltroEq] = useState('')
  const eqs = op.equipos.filter((e) => !filtroEq || `${e.codigo} ${e.nombre}`.toLowerCase().includes(filtroEq.toLowerCase()))
  const toggleEq = (id) => setForm({ ...form, equipos: form.equipos.includes(id) ? form.equipos.filter((x) => x !== id) : [...form.equipos, id] })
  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-4">
        <Sel etiqueta="Tipo" valor={form.tipo} onChange={set('tipo')} opciones={cat?.tipos || []} />
        <Sel etiqueta="Naturaleza" valor={form.naturaleza} onChange={set('naturaleza')} opciones={cat?.naturalezas || []} />
        <Sel etiqueta="Categoría del incidente" valor={form.categoria} onChange={set('categoria')} opciones={[['', '— Seleccionar —'], ...(cat?.categorias || [])]} />
        <Sel etiqueta="Área o laboratorio" valor={String(form.area || '')} onChange={set('area')} opciones={[['', '— Seleccionar —'], ...areas.map((a) => [String(a.id), a.nombre])]} />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <div className="md:col-span-2"><Sel etiqueta="Reportado por" valor={String(form.reportado_por || '')} onChange={set('reportado_por')} opciones={optT} /></div>
        <div><label className={lbl}>Fecha de detección</label><input type="date" max={hoy()} className={inp} value={form.fecha_deteccion || ''} onChange={(e) => set('fecha_deteccion')(e.target.value)} /></div>
        <div><label className={lbl}>Reporte al GSIG y GT</label><input type="date" max={hoy()} className={inp} value={form.fecha_reporte || ''} onChange={(e) => set('fecha_reporte')(e.target.value)} /></div>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <Sel etiqueta="Fuente de detección" valor={form.fuente} onChange={set('fuente')} opciones={[['', '— Seleccionar —'], ...(cat?.fuentes || [])]} />
        {form.fuente === 'queja' && <Sel etiqueta="Queja de origen" valor={String(form.queja || '')} onChange={set('queja')} opciones={[['', '— Seleccionar —'], ...op.quejas.map((q) => [String(q.id), `${q.codigo} · ${q.texto}`])]} />}
        {form.fuente === 'no_conformidad' && <Sel etiqueta="No conformidad de origen" valor={String(form.hallazgo || '')} onChange={set('hallazgo')} opciones={[['', '— Seleccionar —'], ...op.hallazgos.map((h) => [String(h.id), `${h.codigo} · ${h.texto}`])]} />}
        <div className={form.fuente === 'queja' || form.fuente === 'no_conformidad' ? '' : 'md:col-span-2'}><label className={lbl}>OT / certificados involucrados</label><input className={inp} placeholder="p. ej. OT-2026-0450; CP-1123-2026" value={form.referencias} onChange={(e) => set('referencias')(e.target.value)} /></div>
      </div>
      <div>
        <label className={lbl}>Equipos involucrados ({form.equipos.length})</label>
        <input className={`${inp} mb-1 !py-1 text-xs`} placeholder="Filtrar equipos por código o nombre" value={filtroEq} onChange={(e) => setFiltroEq(e.target.value)} />
        <div className="grid max-h-28 gap-0.5 overflow-y-auto rounded-lg border border-slate-200 p-2 text-xs md:grid-cols-2 dark:border-slate-700">
          {eqs.map((e) => <label key={e.id} className="flex cursor-pointer items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" checked={form.equipos.includes(e.id)} onChange={() => toggleEq(e.id)} /> {e.codigo} · {e.nombre}</label>)}
          {eqs.length === 0 && <span className="text-slate-400">Sin equipos</span>}
        </div>
      </div>
      <div><label className={lbl}>Descripción del TNC o SNC</label><CampoAmpliable multilinea rows={3} titulo="Descripción" value={form.descripcion} onChange={set('descripcion')} /></div>
    </div>
  )
}

function Detalle({ d, setD, cat, op, areas, trab, optT, verTabla, tienePermiso, confirmar, onAnulado }) {
  const [error, setError] = useState('')
  const [reg, setReg] = useState(null)
  const [ini, setIni] = useState({ nivel_riesgo: '', responsable_tratamiento: '' })
  const [trat, setTrat] = useState({})
  const [acc, setAcc] = useState({})
  const [fila, setFila] = useState(null)
  const [aut, setAut] = useState({ acepta: '', sustento: '', asignado_a: '' })
  const [ev, setEv] = useState({})
  const [cie, setCie] = useState({ sac: '', evidencias: '' })
  const [adj, setAdj] = useState({ archivo: null, descripcion: '' })
  const puedeEditar = tienePermiso('trabajo_no_conforme', 'editar')
  const puedeAprobar = tienePermiso('trabajo_no_conforme', 'aprobar')
  const nombreAccion = Object.fromEntries(cat?.acciones || [])

  useEffect(() => {
    setTrat(Object.fromEntries(CAMPOS_TRAT.map((c) => [c, d[c] ?? ''])))
    setAcc(d.acciones || {})
    setEv(Object.fromEntries(CAMPOS_EVAL.map((c) => [c, typeof d[c] === 'boolean' || d[c] === null ? deBool(d[c]) : d[c] ?? ''])))
    setCie({ sac: d.sac ? String(d.sac) : '', evidencias: d.evidencias || '' })
    setAut({ acepta: '', sustento: '', asignado_a: '' })
  }, [d.id, d.estado, d.updated_at])

  const ejecutar = async (fn) => {
    setError('')
    try { const r = await fn(); if (r && r.id === d.id && r.acciones !== undefined) setD(r); else setD(await api.tnc.detalle(d.id)); return true } catch (e) { setError(e.message); return false }
  }
  const pedirClave = async (titulo, mensaje) => {
    const c = await confirmar({ titulo, mensaje, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
    return c === null || c === undefined ? null : c
  }
  const paso = Math.max(0, PASOS.findIndex(([e]) => e === d.estado))
  const en = (e) => d.estado === e && puedeEditar

  // Tratamiento
  const tratSinGuardar = d.estado === 'tratamiento' && (CAMPOS_TRAT.some((c) => String(trat[c] ?? '') !== String(d[c] ?? '')) || JSON.stringify(acc) !== JSON.stringify(d.acciones || {}))
  const guardarTrat = () => ejecutar(() => {
    const datos = { ...trat, acciones: acc }
    for (const c of ['correccion_por', 'correccion_fecha', 'periodo_desde', 'periodo_hasta']) if (!datos[c]) datos[c] = null
    return api.tnc.editar(d.id, datos)
  })
  const setAccion = (c, k, v) => setAcc({ ...acc, [c]: { ...(acc[c] || {}), [k]: v, ...(k === 'aplica' && v !== true ? { ejecutada: null } : {}) } })
  const evSinGuardar = d.estado === 'evaluacion' && CAMPOS_EVAL.some((c) => String(ev[c] ?? '') !== String(typeof d[c] === 'boolean' || d[c] === null ? deBool(d[c]) : d[c] ?? ''))
  const guardarEv = () => ejecutar(() => api.tnc.editar(d.id, { ...ev, afecta_validez: aBool(ev.afecta_validez), incumple_sig: aBool(ev.incumple_sig), compromete_competencia: aBool(ev.compromete_competencia), amerita_sac: aBool(ev.amerita_sac) }))
  const cieSinGuardar = d.estado === 'cierre' && (cie.evidencias !== (d.evidencias || '') || cie.sac !== (d.sac ? String(d.sac) : ''))
  const guardarCie = () => ejecutar(() => api.tnc.editar(d.id, { evidencias: cie.evidencias, sac: cie.sac || null }))

  const anular = async () => {
    const motivo = await confirmar({ titulo: 'Anular registro', textoConfirmar: 'Anular', peligro: true, mensaje: `¿Anular ${d.codigo}? Solo para un registro hecho por error; queda en el sistema como anulado.`, entrada: { etiqueta: 'Motivo', obligatorio: true, multilinea: true } })
    if (motivo === null || motivo === undefined) return
    try { await api.tnc.accion(d.id, 'anular', { motivo }); onAnulado() } catch (e) { setError(e.message) }
  }
  const editarReg = () => setReg({ ...Object.fromEntries(Object.keys(REG_VACIO).map((c) => [c, d[c] ?? ''])), equipos: d.equipos || [] })
  const guardarReg = () => ejecutar(async () => {
    const datos = { ...reg }
    for (const c of ['queja', 'hallazgo', 'fecha_reporte']) if (!datos[c]) datos[c] = null
    const r = await api.tnc.editar(d.id, datos); setReg(null); return r
  })

  const etapaFinal = {
    registrado: puedeAprobar && {
      titulo: 'Asignar el nivel de riesgo e iniciar el tratamiento', boton: 'Firmar e iniciar el tratamiento',
      bloqueo: reg ? 'Guarde primero el registro.' : !ini.nivel_riesgo ? 'Asigne el nivel de riesgo (Tabla N° 2).' : !ini.responsable_tratamiento ? 'Designe al responsable del tratamiento.' : '',
      accion: async () => { const c = await pedirClave('Nivel de riesgo', `Nivel ${ini.nivel_riesgo}. El registro queda de solo lectura y empieza el tratamiento.`); if (c !== null) ejecutar(() => api.tnc.accion(d.id, 'iniciar_tratamiento', { ...ini, password: c })) },
    },
    tratamiento: puedeEditar && {
      titulo: 'Concluir el tratamiento y pasar a la autorización de la reanudación', boton: 'Pasar a autorización',
      bloqueo: tratSinGuardar ? 'Guarde primero el tratamiento.' : '',
      accion: () => ejecutar(() => api.tnc.accion(d.id, 'pasar_autorizacion')),
    },
    autorizacion: puedeEditar && {
      titulo: 'Autorizar la reanudación del trabajo', boton: 'Firmar decisión',
      nota: d.naturaleza === 'tecnica' ? 'Autoriza el Gerente Técnico o el Jefe de Laboratorio.' : 'Autoriza el Gerente SIG.',
      bloqueo: !aut.acepta ? 'Indique si acepta el TNC o SNC corregido como conforme.' : !aut.sustento.trim() ? 'Sustente su decisión.' : '',
      accion: async () => { const c = await pedirClave('Autorización de la reanudación', aut.acepta === 'true' ? 'Acepta el TNC o SNC corregido y autoriza la reanudación.' : 'No acepta: el registro vuelve al tratamiento.'); if (c !== null) ejecutar(() => api.tnc.accion(d.id, 'autorizar', { acepta: aut.acepta === 'true', sustento: aut.sustento, asignado_a: aut.asignado_a || null, password: c })) },
    },
    evaluacion: puedeAprobar && {
      titulo: 'Registrar la evaluación de la importancia', boton: 'Firmar evaluación',
      bloqueo: evSinGuardar ? 'Guarde primero la evaluación.' : '',
      accion: async () => { const c = await pedirClave('Evaluación de la importancia', 'La evaluación queda firmada y pasa al cierre.'); if (c !== null) ejecutar(() => api.tnc.accion(d.id, 'evaluar', { password: c })) },
    },
    cierre: puedeAprobar && {
      titulo: 'Cerrar el registro', boton: 'Firmar cierre',
      bloqueo: cieSinGuardar ? 'Guarde primero el cierre.' : (d.amerita_sac && !d.sac) ? 'Vincule o cree la solicitud de acción correctiva.' : (!(d.evidencias || '').trim() && !(d.adjuntos || []).length) ? 'Registre las evidencias archivadas.' : '',
      accion: async () => { const c = await pedirClave('Cierre', 'El registro queda cerrado y de solo lectura.'); if (c !== null) ejecutar(() => api.tnc.accion(d.id, 'cerrar', { password: c })) },
    },
  }[d.estado] || null

  const filas = d.afectaciones || []
  const retro = (acc.retroactivo || {}).aplica || filas.length > 0
  return (
    <div className="space-y-3 text-sm">
      <BarraPasos pasos={PASOS.map(([, n]) => n)} actual={paso} cerrado={d.estado === 'cerrado'} />
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => abrirPdf(api.tnc.pdf(d.id), setError)} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Registro (PDF)</button>
        <button onClick={() => verTabla(2)} className="btn-secondary !py-1 text-xs"><BookOpen className="h-3.5 w-3.5" /> Tablas N° 1 y 2</button>
        {['registrado', 'tratamiento'].includes(d.estado) && tienePermiso('trabajo_no_conforme', 'eliminar') && <button onClick={anular} className="btn-secondary !py-1 text-xs text-red-500"><Trash2 className="h-3.5 w-3.5" /> Anular</button>}
        {d.nivel_riesgo && <span className={NIVEL[d.nivel_riesgo]}>Nivel {d.nivel_display.toLowerCase()}</span>}
        <span className={`ml-auto ${BADGE[TONO[d.estado]]}`}>{d.estado_display}</span>
      </div>

      {/* Registro */}
      <Seccion titulo="Descripción del TNC o SNC" extra={d.estado === 'registrado' && puedeEditar ? (!reg && <button onClick={editarReg} className="btn-secondary !py-1 text-xs">Editar</button>) : <span className="flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Registro cerrado</span>}>
        {reg ? (
          <div className="space-y-2"><FormRegistro form={reg} setForm={setReg} cat={cat} op={op} areas={areas} optT={optT} />
            <div className="flex gap-2"><button onClick={guardarReg} className="btn-primary !py-1.5 text-xs">Guardar</button><button onClick={() => setReg(null)} className="btn-secondary !py-1.5 text-xs">Cancelar</button></div></div>
        ) : (<>
          <div className="grid gap-x-4 gap-y-1 md:grid-cols-2">
            <Dato etiqueta="Tipo y naturaleza" valor={`${d.tipo_display} · ${d.naturaleza_display}`} />
            <Dato etiqueta="Categoría" valor={d.categoria_display} />
            <Dato etiqueta="Área o laboratorio" valor={d.area_nombre} />
            <Dato etiqueta="Reportado por" valor={d.reportado_nombre} />
            <Dato etiqueta="Detección / reporte al GSIG y GT" valor={`${fecha(d.fecha_deteccion)} / ${fecha(d.fecha_reporte) || '—'}`} />
            <Dato etiqueta="Fuente" valor={`${d.fuente_display}${d.queja_codigo ? ` · ${d.queja_codigo}` : ''}${d.hallazgo_codigo ? ` · ${d.hallazgo_codigo}` : ''}`} />
            <Dato etiqueta="OT / certificados" valor={d.referencias} />
            <Dato etiqueta="Equipos" valor={(d.equipos_detalle || []).map((e) => `${e.codigo} (${e.estado})`).join(', ')} />
          </div>
          <p className="whitespace-pre-wrap">{d.descripcion}</p>
        </>)}
        {d.estado === 'registrado' && puedeAprobar && !reg && (
          <div className="grid gap-2 rounded-lg border border-dashed border-esynapse-500/50 p-2 md:grid-cols-2">
            <Sel etiqueta={<span className="flex items-center justify-between gap-2">Nivel de riesgo (Tabla N° 2; ante duda, el mayor)<VerTabla n={2} onAbrir={verTabla} /></span>} valor={ini.nivel_riesgo} onChange={(v) => setIni({ ...ini, nivel_riesgo: v })} opciones={[['', '— Seleccionar —'], ...(cat?.niveles || [])]} />
            <Sel etiqueta="Responsable del tratamiento" valor={ini.responsable_tratamiento} onChange={(v) => setIni({ ...ini, responsable_tratamiento: v })} opciones={optT} />
          </div>
        )}
      </Seccion>

      {/* Tratamiento */}
      {paso >= 1 && d.estado !== 'anulado' && (
        <Seccion titulo={`Tratamiento — responsable: ${d.responsable_nombre || '—'}`} tono={en('tratamiento') ? 'azul' : undefined}
          extra={<span className="flex items-center gap-3">{d.firma_nivel?.nombre && <span className="text-[11px] text-slate-400">Nivel asignado por {d.firma_nivel.nombre}</span>}<VerTabla n={1} onAbrir={verTabla} texto="Responsabilidades (Tabla N° 1)" /></span>}>
          <table className="tabla-ficha w-full max-w-xl">
            <thead><tr><th>Acción</th><th className="text-center">¿Aplica?</th><th className="text-center">¿Ejecutada?</th></tr></thead>
            <tbody>
              {(cat?.acciones || []).map(([c, n]) => {
                const a = (en('tratamiento') ? acc : d.acciones || {})[c] || {}
                return (
                  <tr key={c}><td className="text-left">{n}</td>
                    <td className="text-center">{en('tratamiento') ? <select className={`${inp} !w-20 !py-0.5 text-xs`} value={deBool(a.aplica)} onChange={(e) => setAccion(c, 'aplica', aBool(e.target.value))}>{SN_OPC.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select> : sn(a.aplica)}</td>
                    <td className="text-center">{en('tratamiento') ? (a.aplica ? <input type="checkbox" className="h-4 w-4 accent-esynapse-600" checked={Boolean(a.ejecutada)} onChange={(e) => setAccion(c, 'ejecutada', e.target.checked)} /> : '—') : (a.aplica ? sn(a.ejecutada) : '—')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {d.nivel_riesgo === 'alto' && en('tratamiento') && <p className="text-[11px] text-red-500">Nivel Alto: aplican la detención del trabajo y el análisis de impacto retroactivo{d.categoria === 'equipo' && (d.equipos || []).length ? ', y el equipo fuera de servicio' : ''}.</p>}
          {en('tratamiento') ? (
            <div className="space-y-2">
              <div><label className={lbl}>Corrección del TNC o SNC</label><CampoAmpliable multilinea rows={2} titulo="Corrección" value={trat.correccion || ''} onChange={(v) => setTrat({ ...trat, correccion: v })} /></div>
              <div className="grid gap-2 md:grid-cols-3">
                <Sel etiqueta="Realizada por" valor={String(trat.correccion_por || '')} onChange={(v) => setTrat({ ...trat, correccion_por: v })} opciones={optT} />
                <div><label className={lbl}>Fecha</label><input type="date" max={hoy()} className={inp} value={trat.correccion_fecha || ''} onChange={(e) => setTrat({ ...trat, correccion_fecha: e.target.value })} /></div>
                <div><label className={lbl}>Nota del cliente (si aplica)</label><input className={inp} value={trat.nota_cliente || ''} onChange={(e) => setTrat({ ...trat, nota_cliente: e.target.value })} /></div>
              </div>
            </div>
          ) : (<>
            <p className="whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Corrección:</strong> {d.correccion || '—'}</p>
            <Dato etiqueta="Realizada por" valor={[d.correccion_por_nombre, fecha(d.correccion_fecha)].filter(Boolean).join(' · ')} />
            {d.nota_cliente && <Dato etiqueta="Nota del cliente" valor={d.nota_cliente} />}
          </>)}

          {retro && (
            <div className="space-y-2 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
              <p className="font-semibold">Análisis de impacto retroactivo y notificación al cliente</p>
              {en('tratamiento') ? (
                <div className="grid gap-2 md:grid-cols-4">
                  <div><label className={lbl}>Periodo revisado desde</label><input type="date" className={inp} value={trat.periodo_desde || ''} onChange={(e) => setTrat({ ...trat, periodo_desde: e.target.value })} /></div>
                  <div><label className={lbl}>hasta</label><input type="date" className={inp} value={trat.periodo_hasta || ''} onChange={(e) => setTrat({ ...trat, periodo_hasta: e.target.value })} /></div>
                  <div className="md:col-span-2"><label className={lbl}>Última condición conforme</label><input className={inp} placeholder="p. ej. calibración del patrón del 2026-09-20" value={trat.ultima_condicion || ''} onChange={(e) => setTrat({ ...trat, ultima_condicion: e.target.value })} /></div>
                </div>
              ) : <Dato etiqueta="Periodo revisado" valor={d.periodo_desde ? `del ${fecha(d.periodo_desde)} al ${fecha(d.periodo_hasta)} · última condición conforme: ${d.ultima_condicion || '—'}` : ''} />}
              <table className="tabla-sig w-full">
                <thead><tr><th>N° OT</th><th>N° certificado</th><th className="text-center">¿Entregado?</th><th className="text-center">¿Afectado?</th><th className="text-center">Acción</th>{en('tratamiento') && <th />}</tr></thead>
                <tbody>
                  {filas.map((f) => (
                    <tr key={f.id}><td>{f.ot}</td><td>{f.certificado}</td><td className="text-center">{sn(f.entregado)}</td>
                      <td className="text-center">{f.afectado ? <span className="badge badge-rojo">Sí</span> : 'No'}</td><td className="text-center">{f.accion_display}</td>
                      {en('tratamiento') && <td className="whitespace-nowrap text-center"><button onClick={() => setFila({ ...f })} className="mr-2 text-esynapse-500 hover:underline">editar</button><button onClick={() => ejecutar(() => api.tnc.accion(d.id, 'quitar_afectacion', { id: f.id }))} className="text-red-500 hover:underline">quitar</button></td>}
                    </tr>
                  ))}
                  {filas.length === 0 && <tr><td colSpan={6} className="py-2 text-center text-slate-400">Sin OT ni certificados revisados</td></tr>}
                </tbody>
              </table>
              {en('tratamiento') && (fila ? (
                <div className="grid items-end gap-2 md:grid-cols-6">
                  <div><label className={lbl}>N° OT</label><input className={inp} value={fila.ot} onChange={(e) => setFila({ ...fila, ot: e.target.value })} /></div>
                  <div><label className={lbl}>N° certificado</label><input className={inp} value={fila.certificado} onChange={(e) => setFila({ ...fila, certificado: e.target.value })} /></div>
                  <label className="flex items-center gap-1.5 pb-2"><input type="checkbox" className="accent-esynapse-600" checked={fila.entregado} onChange={(e) => setFila({ ...fila, entregado: e.target.checked })} /> Entregado</label>
                  <label className="flex items-center gap-1.5 pb-2"><input type="checkbox" className="accent-esynapse-600" checked={fila.afectado} onChange={(e) => setFila({ ...fila, afectado: e.target.checked })} /> Afectado</label>
                  <Sel etiqueta="Acción" valor={fila.accion} onChange={(v) => setFila({ ...fila, accion: v })} opciones={cat?.acciones_afectacion || []} />
                  <div className="flex gap-1"><button onClick={async () => { if (await ejecutar(() => api.tnc.accion(d.id, 'afectacion', fila))) setFila(null) }} className="btn-primary !py-1.5 text-xs">{fila.id ? 'Guardar' : 'Agregar'}</button><button onClick={() => setFila(null)} className="btn-secondary !py-1.5 text-xs">×</button></div>
                </div>
              ) : <button onClick={() => setFila({ ot: '', certificado: '', entregado: false, afectado: false, accion: 'ninguna' })} className="flex items-center gap-1 text-xs text-esynapse-500 hover:underline"><Plus className="h-3.5 w-3.5" /> Agregar OT o certificado</button>)}
              {en('tratamiento') ? (
                <div className="space-y-2">
                  <div className="grid gap-2 md:grid-cols-2">
                    <div><label className={lbl}>Notificación al cliente</label><input className={inp} value={trat.notificacion_cliente || ''} onChange={(e) => setTrat({ ...trat, notificacion_cliente: e.target.value })} /></div>
                    <div><label className={lbl}>Fecha y medio</label><input className={inp} value={trat.notificacion_fecha_medio || ''} onChange={(e) => setTrat({ ...trat, notificacion_fecha_medio: e.target.value })} /></div>
                    <div><label className={lbl}>Certificado anulado N°</label><input className={inp} value={trat.certificado_anulado || ''} onChange={(e) => setTrat({ ...trat, certificado_anulado: e.target.value })} /></div>
                    <div><label className={lbl}>Certificado de reemplazo N°</label><input className={inp} value={trat.certificado_reemplazo || ''} onChange={(e) => setTrat({ ...trat, certificado_reemplazo: e.target.value })} /></div>
                  </div>
                  <div><label className={lbl}>Conclusión del análisis de impacto retroactivo</label><CampoAmpliable multilinea rows={2} titulo="Conclusión" value={trat.conclusion_retroactivo || ''} onChange={(v) => setTrat({ ...trat, conclusion_retroactivo: v })} /></div>
                </div>
              ) : (<>
                <Dato etiqueta="Notificación al cliente" valor={[d.notificacion_cliente, d.notificacion_fecha_medio].filter(Boolean).join(' · ')} />
                <Dato etiqueta="Certificado anulado / reemplazo" valor={[d.certificado_anulado, d.certificado_reemplazo].filter(Boolean).join(' → ')} />
                <Dato etiqueta="Conclusión" valor={d.conclusion_retroactivo} />
              </>)}
            </div>
          )}
          {en('tratamiento') && <div className="flex items-center gap-3"><button onClick={guardarTrat} className={`${tratSinGuardar ? 'btn-primary' : 'btn-secondary'} !py-1.5 text-xs`}>Guardar tratamiento</button>{tratSinGuardar && <span className="text-[11px] text-amber-600 dark:text-amber-400">Cambios sin guardar</span>}</div>}
        </Seccion>
      )}

      {/* Autorización */}
      {paso >= 2 && d.estado !== 'anulado' && (
        <Seccion titulo="Autorización para la reanudación del trabajo" tono={en('autorizacion') ? 'ambar' : undefined}>
          {d.firma_autorizacion?.nombre ? (<>
            <Dato etiqueta="¿Acepta el TNC o SNC corregido como conforme?" valor={sn(d.acepta)} />
            <Dato etiqueta="Responsable y fecha" valor={`${d.firma_autorizacion.nombre} (${d.firma_autorizacion.cargo || ''}) · ${fechaHora(d.firma_autorizacion.fecha)}`} />
            <Dato etiqueta="Asignado a" valor={d.asignado_nombre} />
            <p className="whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Sustento:</strong> {d.sustento_autorizacion}</p>
          </>) : en('autorizacion') && (
            <div className="space-y-2">
              <div className="flex flex-wrap gap-4">
                {[['true', 'Sí, se acepta y se autoriza la reanudación'], ['false', 'No se acepta (vuelve al tratamiento)']].map(([v, t]) => (
                  <label key={v} className="flex cursor-pointer items-center gap-1.5"><input type="radio" name="acepta" className="accent-esynapse-600" checked={aut.acepta === v} onChange={() => setAut({ ...aut, acepta: v })} /> {t}</label>
                ))}
              </div>
              <CampoAmpliable multilinea rows={2} titulo="Sustento" placeholder="Sustente su decisión" value={aut.sustento} onChange={(v) => setAut({ ...aut, sustento: v })} />
              <div className="max-w-sm"><Sel etiqueta="Reanudación asignada a" valor={aut.asignado_a} onChange={(v) => setAut({ ...aut, asignado_a: v })} opciones={optT} /></div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">Si la respuesta es No, se debe considerar volver a ejecutar el trabajo si aún es posible; de no ser posible, notificar al cliente y anular el trabajo.</p>
            </div>
          )}
        </Seccion>
      )}

      {/* Evaluación */}
      {paso >= 3 && d.estado !== 'anulado' && (
        <Seccion titulo="Evaluación de la importancia (Área SIG)" tono={en('evaluacion') ? 'ambar' : undefined}
          extra={<span className="text-[11px] text-slate-500">Eventos similares (misma área y categoría, 12 meses): <strong>{d.eventos_similares ?? (d.similares || []).length}</strong>{(d.registros_similares || d.similares || []).length > 1 ? ` · ${(d.registros_similares?.length ? d.registros_similares : d.similares).join(', ')}` : ''}</span>}>
          {d.estado === 'evaluacion' && puedeAprobar ? (
            <div className="space-y-2">
              <div className="grid gap-2 md:grid-cols-3">
                <Sel etiqueta="¿Afecta la validez de los resultados?" valor={ev.afecta_validez} onChange={(v) => setEv({ ...ev, afecta_validez: v })} opciones={SN_OPC} />
                <Sel etiqueta="¿Incumple requisitos y alcances del SIG?" valor={ev.incumple_sig} onChange={(v) => setEv({ ...ev, incumple_sig: v })} opciones={SN_OPC} />
                <Sel etiqueta="¿Compromete la competencia técnica?" valor={ev.compromete_competencia} onChange={(v) => setEv({ ...ev, compromete_competencia: v })} opciones={SN_OPC} />
                <Sel etiqueta={<span className="flex items-center justify-between gap-2">Nivel de riesgo confirmado<VerTabla n={2} onAbrir={verTabla} /></span>} valor={ev.nivel_confirmado} onChange={(v) => setEv({ ...ev, nivel_confirmado: v })} opciones={[['', '—'], ...(cat?.niveles || [])]} />
                <Sel etiqueta="¿Amerita una solicitud de acción correctiva?" valor={ev.amerita_sac} onChange={(v) => setEv({ ...ev, amerita_sac: v })} opciones={SN_OPC} />
              </div>
              <CampoAmpliable multilinea rows={3} titulo="Evaluación" placeholder="Análisis de la importancia: magnitud, frecuencia e impacto en la validez de los resultados" value={ev.evaluacion || ''} onChange={(v) => setEv({ ...ev, evaluacion: v })} />
              <p className="text-[11px] text-slate-500 dark:text-slate-400">La acción correctiva es obligatoria si el nivel confirmado es Alto o hay 3 o más eventos similares en 12 meses; en Medio, cuando puede volver a ocurrir o hay duda sobre el cumplimiento del SIG.</p>
              <div className="flex items-center gap-3"><button onClick={guardarEv} className={`${evSinGuardar ? 'btn-primary' : 'btn-secondary'} !py-1.5 text-xs`}>Guardar evaluación</button>{evSinGuardar && <span className="text-[11px] text-amber-600 dark:text-amber-400">Cambios sin guardar</span>}</div>
            </div>
          ) : d.firma_evaluacion?.nombre ? (<>
            <div className="grid gap-x-4 md:grid-cols-3">
              <Dato etiqueta="¿Afecta la validez?" valor={sn(d.afecta_validez)} /><Dato etiqueta="¿Incumple el SIG?" valor={sn(d.incumple_sig)} /><Dato etiqueta="¿Compromete la competencia?" valor={sn(d.compromete_competencia)} />
              <Dato etiqueta="Nivel confirmado" valor={d.nivel_confirmado_display} /><Dato etiqueta="¿Amerita SAC?" valor={sn(d.amerita_sac)} /><Dato etiqueta="Realizada por" valor={`${d.firma_evaluacion.nombre} · ${fecha(d.firma_evaluacion.fecha)}`} />
            </div>
            <p className="whitespace-pre-wrap">{d.evaluacion}</p>
          </>) : <p className="text-slate-400">Pendiente de evaluación por el Área SIG.</p>}
        </Seccion>
      )}

      {/* Cierre */}
      {paso >= 4 && d.estado !== 'anulado' && (
        <Seccion titulo="Cierre del registro (Área SIG)" tono={d.estado === 'cierre' ? 'violeta' : d.estado === 'cerrado' ? 'verde' : undefined}>
          {d.estado === 'cierre' && puedeAprobar ? (
            <div className="space-y-2">
              {d.amerita_sac && (
                <div className="flex flex-wrap items-end gap-2">
                  {!d.sac && <div className="min-w-[16rem]"><Sel etiqueta="Solicitud de acción correctiva" valor={cie.sac} onChange={(v) => setCie({ ...cie, sac: v })} opciones={[['', '— Vincular una existente —'], ...op.sacs.map((s) => [String(s.id), `${s.codigo} · ${s.texto}`])]} /></div>}
                  {!d.sac && <button onClick={() => ejecutar(() => api.tnc.accion(d.id, 'crear_sac'))} className="btn-secondary !py-2 text-xs"><Plus className="h-3.5 w-3.5" /> Crear SAC con este registro</button>}
                  {d.sac_codigo && <span className="pb-2 text-[11px]">Vinculada: <strong>{d.sac_codigo}</strong> ({d.sac_estado})</span>}
                </div>
              )}
              <div><label className={lbl}>Evidencias archivadas</label><CampoAmpliable multilinea rows={2} titulo="Evidencias" value={cie.evidencias} onChange={(v) => setCie({ ...cie, evidencias: v })} /></div>
              <div className="flex items-center gap-3"><button onClick={guardarCie} className={`${cieSinGuardar ? 'btn-primary' : 'btn-secondary'} !py-1.5 text-xs`}>Guardar</button>{cieSinGuardar && <span className="text-[11px] text-amber-600 dark:text-amber-400">Cambios sin guardar</span>}</div>
            </div>
          ) : (<>
            <Dato etiqueta="Solicitud de acción correctiva" valor={d.sac_codigo ? `${d.sac_codigo} (${d.sac_estado})` : (d.amerita_sac ? 'Pendiente' : 'No amerita')} />
            <Dato etiqueta="Evidencias" valor={d.evidencias} />
            {d.firma_cierre?.nombre && <p className="text-[11px] text-emerald-600 dark:text-emerald-400">Cerrado por {d.firma_cierre.nombre} el {fechaHora(d.firma_cierre.fecha)}.</p>}
          </>)}
        </Seccion>
      )}

      {/* Adjuntos */}
      <Seccion titulo="Evidencias adjuntas">
        {(d.adjuntos || []).length === 0 && <p className="text-slate-400">Sin archivos adjuntos.</p>}
        {(d.adjuntos || []).map((a) => <p key={a.id}><a href={a.url} target="_blank" rel="noreferrer" className="text-esynapse-500 underline">{a.descripcion || 'Archivo'}</a> · {fecha(a.created_at)}</p>)}
        {puedeEditar && !['cerrado', 'anulado'].includes(d.estado) && (
          <div className="flex flex-wrap items-center gap-2">
            <label className="btn-secondary cursor-pointer !py-1 text-xs"><Paperclip className="h-3.5 w-3.5" /> {adj.archivo ? adj.archivo.name : 'Elegir archivo'}
              <input type="file" className="hidden" onChange={(e) => { if (e.target.files[0]) setAdj({ ...adj, archivo: e.target.files[0] }); e.target.value = '' }} /></label>
            <input className={`${inp} !w-64 !py-1 text-xs`} placeholder="Descripción (p. ej. carta al cliente)" value={adj.descripcion} onChange={(e) => setAdj({ ...adj, descripcion: e.target.value })} />
            <button disabled={!adj.archivo} onClick={async () => { const fd = new FormData(); fd.append('archivo', adj.archivo); fd.append('descripcion', adj.descripcion); if (await ejecutar(() => api.tnc.adjuntar(d.id, fd))) setAdj({ archivo: null, descripcion: '' }) }} className="btn-primary !py-1 text-xs disabled:opacity-50">Adjuntar</button>
          </div>
        )}
      </Seccion>

      {(d.historial || []).length > 0 && (
        <details className="text-[11px] text-slate-500"><summary className="cursor-pointer">Historial</summary>
          {(d.historial || []).map((h, i) => <p key={i}>{h.fecha.replace('T', ' ')} · {h.usuario} · {h.accion}{h.motivo ? `: ${h.motivo}` : ''}{h.sustento ? `: ${h.sustento}` : ''}</p>)}
        </details>
      )}
      {etapaFinal && <BarraEtapa titulo={etapaFinal.titulo} nota={etapaFinal.nota} bloqueo={etapaFinal.bloqueo} botones={[{ texto: etapaFinal.boton, accion: etapaFinal.accion }]} />}
      <MsgError texto={error} />
    </div>
  )
}
