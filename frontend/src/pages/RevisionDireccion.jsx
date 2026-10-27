import { useCallback, useEffect, useRef, useState } from 'react'
import { CalendarDays, CheckCircle2, ChevronDown, ChevronRight, ClipboardCheck, Database, FileText, ListChecks, Lock, Paperclip, Pencil, Plus, Trash2, UserPlus } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import BarraPasos from '../components/BarraPasos.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import NavModulo from '../components/NavModulo.jsx'
import EncabezadoModulo from '../components/ui/EncabezadoModulo.jsx'
import EtapaMini from '../components/ui/EtapaMini.jsx'
import { Vistas } from '../components/NavModulo.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora, hoy } from '../lib/fecha.js'
import { useAbrirDesdeEnlace } from '../lib/enlaces.js'

const ANIO = new Date().getFullYear()
const MES = new Date().getMonth() + 1
const MESES = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SET', 'OCT', 'NOV', 'DIC']
const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
// Colores de estado (regla 10): ámbar preparación (análisis) · azul reunión (ejecución) · verde cerrada · rojo anulada.
const PASOS = [['preparacion', 'Preparación'], ['reunion', 'Reunión'], ['cerrada', 'Cerrada']]
const TONO = { preparacion: 'ambar', reunion: 'azul', cerrada: 'verde', anulada: 'rojo' }
const BADGE = { gris: 'badge badge-gris', ambar: 'badge badge-ambar', azul: 'badge badge-azul', verde: 'badge badge-verde', rojo: 'badge badge-rojo' }
const TONO_ACUERDO = (a) => (a.estado === 'cerrado' ? 'verde' : a.vencido ? 'rojo' : a.estado === 'en_proceso' ? 'azul' : 'gris')
const soles = (v) => (v == null || v === '' ? '—' : `S/ ${Number(v).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
const elementoCorto = (c) => (c ? `${c.startsWith('e-') ? 'Entrada' : 'Salida'} ${c.slice(2)})` : '—')

const GRUPOS = [
  { clave: 'revisiones', nombre: 'Revisiones', icono: ClipboardCheck, secciones: [{ clave: 'revisiones', nombre: 'Revisiones' }] },
  { clave: 'programa', nombre: 'Programa anual', icono: CalendarDays, secciones: [{ clave: 'programa', nombre: 'Programa anual' }] },
  { clave: 'plan', nombre: 'Plan de acción', icono: ListChecks, secciones: [{ clave: 'plan', nombre: 'Plan de acción' }] },
]

function Seccion({ titulo, tono, children, extra }) {
  const borde = { ambar: 'border-amber-500/30 bg-amber-500/5', azul: 'border-esynapse-600/30 bg-esynapse-600/5', verde: 'border-emerald-500/30 bg-emerald-500/5' }[tono]
    || 'border-slate-200 dark:border-slate-800'
  return (
    <div className={`space-y-2 rounded-lg border p-3 text-xs ${borde}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">{titulo}</p>
        {extra}
      </div>
      <div className="text-slate-600 dark:text-slate-300">{children}</div>
    </div>
  )
}
const Dato = ({ etiqueta, valor }) => <p><strong className="text-slate-700 dark:text-slate-200">{etiqueta}:</strong> {valor || '—'}</p>
function MsgError({ texto }) {
  const ref = useRef(null)
  useEffect(() => { if (texto) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }, [texto])
  return texto ? <p ref={ref} className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p> : null
}

/* Credencial de quien firma en pantalla: contraseña de su usuario o PIN personal (regla de firma de personas). */
function Credencial({ forma, valor, onChange }) {
  const v = valor || {}
  const pin = (k, ph) => <input type="password" inputMode="numeric" autoComplete="off" placeholder={ph} className={`${inp} !w-24 !py-1 text-xs`} value={v[k] || ''} onChange={(e) => onChange({ ...v, [k]: e.target.value.replace(/\D/g, '').slice(0, 6) })} />
  if (forma === 'usuario') return <input type="password" autoComplete="off" placeholder="Contraseña de su usuario" className={`${inp} !w-48 !py-1 text-xs`} value={v.clave || ''} onChange={(e) => onChange({ ...v, clave: e.target.value })} />
  if (forma === 'activo') return pin('pin', 'PIN')
  if (forma === 'bloqueado') return <span className="text-[11px] text-red-600">PIN bloqueado: restablézcalo en SST › EPP › Por trabajador</span>
  return <span className="flex gap-1">{pin('pin_nuevo', 'Nuevo PIN')}{pin('pin_confirmacion', 'Confirme')}</span>
}

/* Bloques de datos del sistema de una entrada. */
function DatosSistema({ bloques }) {
  if (!bloques?.length) return <p className="text-[11px] text-slate-400">Aún no se generan los datos del sistema.</p>
  return (
    <div className="grid gap-2 md:grid-cols-2">
      {bloques.map((b, i) => (
        <div key={i} className="rounded border border-slate-200 dark:border-slate-700">
          <p className="border-b border-slate-200 bg-slate-50 px-2 py-1 font-semibold dark:border-slate-700 dark:bg-slate-800/60">{b.titulo}</p>
          {b.filas?.length > 0 && (
            <table className="tabla-ficha w-full text-[11px]"><tbody>
              {b.filas.map(([e, v], j) => <tr key={j} className="border-b border-slate-100 last:border-0 dark:border-slate-800"><td className="px-2 py-0.5 text-left">{e}</td><td className="px-2 py-0.5 text-right font-medium">{v}</td></tr>)}
            </tbody></table>
          )}
          {b.nota && <p className="px-2 py-1 text-[11px] italic text-slate-500 dark:text-slate-400">{b.nota}</p>}
        </div>
      ))}
    </div>
  )
}

export default function RevisionDireccion() {
  const { tienePermiso } = useAuth()
  const [pestana, setPestana] = useState('revisiones')
  const [cat, setCat] = useState(null)
  const [trabajadores, setTrabajadores] = useState([])
  const [puestos, setPuestos] = useState([])
  const [irRevision, setIrRevision] = useState(null)
  useEffect(() => {
    api.revision.catalogos().then(setCat).catch(() => {})
    api.org.trabajadores().then((x) => setTrabajadores((x.results ?? x).filter((w) => w.estado === 'activo'))).catch(() => {})
    api.org.puestos().then((x) => setPuestos(x.results ?? x)).catch(() => {})
  }, [])
  // Enlace directo ?abrir=<id> (búsqueda global): abre la revisión en su pestaña
  useAbrirDesdeEnlace((id) => { setPestana('revisiones'); setIrRevision(id) })
  const comun = { cat, trabajadores, puestos, tienePermiso }
  return (
    <div className="space-y-4">
      <EncabezadoModulo seccion="Estratégico" titulo="Revisión por la dirección"
        descripcion="La alta dirección revisa el SIG a intervalos planificados: se prepara con los datos del sistema, se realiza en reunión con acta firmada y sus acuerdos se siguen en el plan de acción.">
        <NavModulo grupos={GRUPOS} seccion={pestana} onCambiar={setPestana} />
      </EncabezadoModulo>
      {pestana === 'revisiones' && <Revisiones {...comun} abrirId={irRevision} onAbierto={() => setIrRevision(null)} />}
      {pestana === 'programa' && <Programa {...comun} />}
      {pestana === 'plan' && <PlanAccion {...comun} onIrRevision={(id) => { setIrRevision(id); setPestana('revisiones') }} />}
    </div>
  )
}

const abrirPdf = async (promesa, setError) => {
  setError('')
  try {
    const url = URL.createObjectURL(await promesa)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (e) { setError(e.message) }
}

// ===================================================================================================== revisiones
const FORM_VACIO = { tipo: 'ordinaria', motivo_extraordinaria: '', detalle_motivo: '', fecha: '', lugar: '', periodo_desde: `${ANIO}-01-01`, periodo_hasta: '', responsable_recopilacion: '', responsable_verificacion: '' }
const CAMPOS_PREP = Object.keys(FORM_VACIO)

function Revisiones({ cat, trabajadores, tienePermiso, abrirId, onAbierto }) {
  const confirmar = useConfirm()
  const [anio, setAnio] = useState('')
  const [items, setItems] = useState([])
  const [detalle, setDetalle] = useState(null)
  const [modal, setModal] = useState(false)
  const [form, setForm] = useState(FORM_VACIO)
  const [error, setError] = useState('')
  const puedeEditar = tienePermiso('revision_direccion', 'editar')
  const puedeAprobar = tienePermiso('revision_direccion', 'aprobar')

  const cargar = useCallback(async () => {
    const d = await api.revision.revisiones(anio ? `?anio=${anio}` : '')
    setItems(d.results ?? d)
  }, [anio])
  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  const abrir = async (id) => { setError(''); setDetalle(await api.revision.revision(id)) }
  useEffect(() => { if (abrirId) { abrir(abrirId).catch(() => {}); onAbierto() } }, [abrirId])

  const crear = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const datos = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v === '' ? null : v]))
      datos.tipo = form.tipo
      datos.motivo_extraordinaria = form.motivo_extraordinaria
      datos.detalle_motivo = form.detalle_motivo
      datos.lugar = form.lugar
      const r = await api.revision.crear(datos)
      setModal(false)
      await cargar()
      setDetalle(r)
    } catch (e2) { setError(e2.message) }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <select className={`${inp} w-40`} aria-label="Año" value={anio} onChange={(e) => setAnio(e.target.value)}>
          <option value="">Todos los años</option>
          {[ANIO + 1, ANIO, ANIO - 1, ANIO - 2].map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <div className="ml-auto flex gap-2">
          {tienePermiso('revision_direccion', 'crear') && <button onClick={() => { setForm({ ...FORM_VACIO, fecha: hoy(), periodo_hasta: hoy() }); setError(''); setModal(true) }} className="btn-primary"><Plus className="h-4 w-4" /> Nueva revisión</button>}
        </div>
      </div>

      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig min-w-[900px]">
          <thead>
            <tr>
              <th scope="col">N° de informe</th><th scope="col" className="text-center">Tipo</th>
              <th scope="col" className="text-right">Fecha</th><th scope="col" className="text-right">Periodo evaluado</th>
              <th scope="col" className="text-center">Entradas analizadas</th><th scope="col" className="text-center">Acuerdos cerrados</th>
              <th scope="col" className="text-center">Etapa</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => {
              const paso = Math.max(0, PASOS.findIndex(([e]) => e === r.estado))
              return (
                <tr key={r.id} className="fila" onClick={() => abrir(r.id)}>
                  <td className="whitespace-nowrap font-semibold text-esynapse-700 dark:text-esynapse-300">{r.codigo}</td>
                  <td className="text-center">{r.tipo_display}</td>
                  <td className="whitespace-nowrap text-right">{fecha(r.fecha) || '—'}</td>
                  <td className="whitespace-nowrap text-right">{r.periodo_desde ? `${fecha(r.periodo_desde)} – ${fecha(r.periodo_hasta)}` : '—'}</td>
                  <td className="text-center">{r.resumen.entradas_completas} / {r.resumen.entradas}</td>
                  <td className="text-center">{r.resumen.acuerdos ? `${r.resumen.acuerdos_cerrados} / ${r.resumen.acuerdos}` : '—'}</td>
                  <td className="text-center"><EtapaMini total={3} actual={paso} tono={TONO[r.estado]} texto={r.estado_display} /></td>
                </tr>
              )
            })}
            {items.length === 0 && <tr><td colSpan={7} className="py-8 text-center text-slate-400">Sin revisiones registradas</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal abierto={modal} titulo="Nueva revisión por la dirección" onCerrar={() => setModal(false)} ancho="max-w-2xl">
        <form onSubmit={crear} className="space-y-3">
          <FormPreparacion form={form} setForm={setForm} cat={cat} trabajadores={trabajadores} />
          <p className="text-[11px] text-slate-500 dark:text-slate-400">Se asigna el N° de informe y se crean las 23 entradas y las 10 salidas de la agenda.</p>
          <MsgError texto={error} />
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModal(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">Registrar</button>
          </div>
        </form>
      </Modal>

      <Modal abierto={Boolean(detalle) && !modal} titulo={detalle ? `${detalle.codigo} — Revisión ${detalle.tipo_display.toLowerCase()}` : ''} onCerrar={() => { setDetalle(null); cargar() }} panel ancho="max-w-5xl">
        {detalle && <DetalleRevision d={detalle} setD={setDetalle} cat={cat} trabajadores={trabajadores} puedeEditar={puedeEditar} puedeAprobar={puedeAprobar}
          puedeAnular={tienePermiso('revision_direccion', 'eliminar')} confirmar={confirmar} onAnulada={() => { setDetalle(null); cargar() }} />}
      </Modal>
    </div>
  )
}

function FormPreparacion({ form, setForm, cat, trabajadores }) {
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const optT = [['', '— Seleccionar —'], ...trabajadores.map((t) => [String(t.id), `${t.nombre_completo} (${t.puesto_nombre || ''})`])]
  const sel = (k, et, op) => <div><label className={lbl}>{et}</label><select className={inp} value={String(form[k] ?? '')} onChange={set(k)}>{op.map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></div>
  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-3">
        {sel('tipo', 'Tipo', cat?.tipos || [['ordinaria', 'Ordinaria'], ['extraordinaria', 'Extraordinaria']])}
        {form.tipo === 'extraordinaria' && <div className="md:col-span-2">{sel('motivo_extraordinaria', 'Motivo', [['', '— Seleccionar —'], ...(cat?.motivos || [])])}</div>}
      </div>
      {form.tipo === 'extraordinaria' && <CampoAmpliable multilinea placeholder="Detalle del motivo" value={form.detalle_motivo} onChange={(v) => setForm({ ...form, detalle_motivo: v })} />}
      <div className="grid gap-3 md:grid-cols-4">
        <div><label className={lbl}>Fecha de la revisión</label><input type="date" className={inp} value={form.fecha || ''} onChange={set('fecha')} /></div>
        <div><label className={lbl}>Periodo evaluado desde</label><input type="date" className={inp} value={form.periodo_desde || ''} onChange={set('periodo_desde')} /></div>
        <div><label className={lbl}>Periodo evaluado hasta</label><input type="date" className={inp} value={form.periodo_hasta || ''} onChange={set('periodo_hasta')} /></div>
        <div><label className={lbl}>Lugar / modalidad</label><input className={inp} placeholder="Sala de reuniones, virtual…" value={form.lugar} onChange={set('lugar')} /></div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {sel('responsable_recopilacion', 'Responsable de la recopilación de la información', optT)}
        {sel('responsable_verificacion', 'Responsable de la verificación de la información', optT)}
      </div>
    </div>
  )
}

function DetalleRevision({ d, setD, cat, trabajadores, puedeEditar, puedeAprobar, puedeAnular, confirmar, onAnulada }) {
  const [error, setError] = useState('')
  const [prep, setPrep] = useState(null)
  const [abiertas, setAbiertas] = useState({})
  const [analisis, setAnalisis] = useState({})
  const [salidas, setSalidas] = useState({})
  const [reunion, setReunion] = useState({})
  const [nuevoAsistente, setNuevoAsistente] = useState('')
  const [cred, setCred] = useState({})
  const [acuerdo, setAcuerdo] = useState(null)
  const [reuniones, setReuniones] = useState([])
  const enPrep = d.estado === 'preparacion' && puedeEditar
  const enReunion = d.estado === 'reunion' && puedeEditar

  useEffect(() => {
    setAnalisis(Object.fromEntries(d.entradas.map((e) => [e.clave, { analisis: e.analisis, sin_actividad: e.sin_actividad }])))
    setSalidas(Object.fromEntries(d.salidas.map((s) => [s.clave, s.texto])))
    setReunion({ conclusiones: d.conclusiones, observaciones: d.observaciones, comunicacion_fecha: d.comunicacion_fecha || '', comunicacion_detalle: d.comunicacion_detalle, reunion_comite: d.reunion_comite || '' })
  }, [d.id, d.estado])
  useEffect(() => { if (d.estado === 'reunion') api.sst?.reuniones?.().then((x) => setReuniones(x.results ?? x)).catch(() => {}) }, [d.estado])

  const ejecutar = async (fn) => {
    setError('')
    try { const r = await fn(); if (r && r.id === d.id && r.entradas) setD(r); else setD(await api.revision.revision(d.id)); return true } catch (e) { setError(e.message); return false }
  }
  const pasoActual = Math.max(0, PASOS.findIndex(([e]) => e === d.estado))

  // --- preparación ---
  const editarPrep = () => setPrep(Object.fromEntries(CAMPOS_PREP.map((c) => [c, d[c] ?? ''])))
  const guardarPrep = () => ejecutar(async () => {
    const datos = { ...prep }
    for (const c of ['fecha', 'periodo_desde', 'periodo_hasta', 'responsable_recopilacion', 'responsable_verificacion']) if (datos[c] === '') datos[c] = null
    const r = await api.revision.editar(d.id, datos); setPrep(null); return r
  })
  const guardarEntrada = (clave) => ejecutar(() => api.revision.accion(d.id, 'entrada', { clave, ...analisis[clave] }))
  const entradaSinGuardar = (e) => (analisis[e.clave]?.analisis ?? '') !== (e.analisis ?? '') || Boolean(analisis[e.clave]?.sin_actividad) !== e.sin_actividad
  const completas = d.entradas.filter((e) => e.completa).length

  // --- reunión ---
  const salidaSinGuardar = (s) => (salidas[s.clave] ?? '') !== (s.texto ?? '')
  const reunionSinGuardar = d.estado === 'reunion' && ['conclusiones', 'observaciones', 'comunicacion_fecha', 'comunicacion_detalle', 'reunion_comite'].some((c) => String(reunion[c] ?? '') !== String(d[c] ?? ''))
  const guardarReunion = () => ejecutar(() => api.revision.editar(d.id, { ...reunion, comunicacion_fecha: reunion.comunicacion_fecha || null, reunion_comite: reunion.reunion_comite || null }))
  const firmar = (a) => ejecutar(async () => { const r = await api.revision.accion(d.id, 'firmar_asistente', { id: a.id, ...(cred[a.id] || {}) }); setCred({ ...cred, [a.id]: {} }); return r })
  const guardarAcuerdo = () => ejecutar(async () => { const r = await api.revision.accion(d.id, 'acuerdo', acuerdo); setAcuerdo(null); return r })

  const anular = async () => {
    const motivo = await confirmar({ titulo: 'Anular revisión', textoConfirmar: 'Anular', peligro: true, mensaje: `¿Anular ${d.codigo}? Solo para una revisión registrada por error (antes de su cierre); queda en el sistema como anulada.`, entrada: { etiqueta: 'Motivo', obligatorio: true, multilinea: true } })
    if (motivo === null || motivo === undefined) return
    try { await api.revision.accion(d.id, 'anular', { motivo }); onAnulada() } catch (e) { setError(e.message) }
  }
  const convocar = async () => {
    if (!await confirmar({ titulo: 'Convocar a la reunión', textoConfirmar: 'Convocar', mensaje: 'La preparación queda cerrada: los datos generales y el análisis de las entradas pasan a ser de solo lectura.' })) return
    await ejecutar(() => api.revision.accion(d.id, 'convocar'))
  }
  const cerrar = async () => {
    const c = await confirmar({ titulo: 'Cerrar la revisión', textoConfirmar: 'Firmar y cerrar', mensaje: 'El informe queda firmado y de solo lectura. Los acuerdos pasan al plan de acción para su seguimiento.', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
    if (c === null || c === undefined) return
    await ejecutar(() => api.revision.accion(d.id, 'cerrar', { password: c }))
  }

  const faltaPrep = [!d.fecha && 'la fecha', !d.periodo_desde && 'el inicio del periodo', !d.periodo_hasta && 'el fin del periodo', !d.responsable_recopilacion && 'el responsable de la recopilación', !d.responsable_verificacion && 'el responsable de la verificación'].filter(Boolean)
  const asistentes = d.asistentes || []
  const siglasFirmadas = asistentes.filter((a) => a.firma && Object.keys(a.firma).length).map((a) => a.sigla)
  const faltaCierre = [
    !(d.conclusiones || '').trim() && 'las conclusiones',
    d.salidas.some((s) => s.clave !== 'j' && !(s.texto || '').trim()) && 'las salidas a) a i) (escriba «Ninguna» si no hubo decisiones)',
    asistentes.length === 0 && 'los asistentes',
    asistentes.some((a) => !a.firma || !Object.keys(a.firma).length) && 'la firma de todos los asistentes',
    !siglasFirmadas.includes('GSIG') && 'la firma del Gerente SIG',
    !siglasFirmadas.includes('GG') && 'la firma del Gerente General',
  ].filter(Boolean)
  const etapaFinal = d.estado === 'preparacion' && puedeEditar ? {
    titulo: 'Cerrar la preparación y convocar a la reunión', boton: 'Convocar a la reunión', accion: convocar,
    bloqueo: prep ? 'Guarde primero los datos generales.' : faltaPrep.length ? `Falta: ${faltaPrep.join(', ')}.` : completas < d.entradas.length ? `Faltan ${d.entradas.length - completas} entradas por analizar (o marcar sin actividad en el periodo).` : '',
  } : d.estado === 'reunion' && puedeAprobar ? {
    titulo: 'Cerrar la revisión (informe firmado)', boton: 'Cerrar la revisión', accion: cerrar,
    bloqueo: reunionSinGuardar ? 'Guarde primero las conclusiones y la comunicación.' : faltaCierre.length ? `Falta: ${faltaCierre.join('; ')}.` : '',
  } : null

  const optT = [['', '— Seleccionar —'], ...trabajadores.map((t) => [String(t.id), t.nombre_completo])]
  return (
    <div className="space-y-3 text-sm">
      <BarraPasos pasos={PASOS.map(([, n]) => n)} actual={pasoActual} cerrado={d.estado === 'cerrada'} />
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => abrirPdf(api.revision.informePdf(d.id), setError)} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Informe (PDF)</button>
        <button onClick={() => abrirPdf(api.revision.planPdf(d.id), setError)} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Plan de acción (PDF)</button>
        {['preparacion', 'reunion'].includes(d.estado) && puedeAnular && <button onClick={anular} className="btn-secondary !py-1 text-xs text-red-500"><Trash2 className="h-3.5 w-3.5" /> Anular</button>}
        <span className={`ml-auto ${BADGE[TONO[d.estado]]}`}>{d.estado_display}</span>
      </div>

      {/* 1. Datos generales */}
      <Seccion titulo="Datos generales" tono={enPrep ? 'ambar' : undefined}
        extra={enPrep ? (!prep && <button onClick={editarPrep} className="btn-secondary !py-1 text-xs"><Pencil className="h-3.5 w-3.5" /> Editar</button>)
          : <span className="flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Etapa de preparación cerrada</span>}>
        {prep ? (
          <div className="space-y-2">
            <FormPreparacion form={prep} setForm={setPrep} cat={cat} trabajadores={trabajadores} />
            <div className="flex gap-2"><button onClick={guardarPrep} className="btn-primary !py-1.5 text-xs">Guardar</button><button onClick={() => setPrep(null)} className="btn-secondary !py-1.5 text-xs">Cancelar</button></div>
          </div>
        ) : (
          <div className="grid gap-x-4 gap-y-1 md:grid-cols-2">
            <Dato etiqueta="Tipo" valor={`${d.tipo_display}${d.motivo_display ? ` — ${d.motivo_display}` : ''}`} />
            <Dato etiqueta="Fecha y lugar" valor={[fecha(d.fecha), d.lugar].filter(Boolean).join(' · ')} />
            <Dato etiqueta="Periodo evaluado" valor={d.periodo_desde ? `del ${fecha(d.periodo_desde)} al ${fecha(d.periodo_hasta)}` : ''} />
            <Dato etiqueta="Recopilación de la información" valor={d.recopilacion_nombre} />
            <Dato etiqueta="Verificación de la información" valor={d.verificacion_nombre} />
            {d.detalle_motivo && <Dato etiqueta="Detalle del motivo" valor={d.detalle_motivo} />}
          </div>
        )}
      </Seccion>

      {/* 2. Entradas */}
      <Seccion titulo={`Agenda — entradas (${completas} de ${d.entradas.length} analizadas)`} tono={enPrep ? 'ambar' : undefined}
        extra={enPrep && <span className="flex items-center gap-2">
          {d.datos_generados && <span className="text-[11px] text-slate-400">Datos del {fechaHora(d.datos_generados)}</span>}
          <button onClick={() => ejecutar(() => api.revision.accion(d.id, 'generar_datos'))} className="btn-secondary !py-1 text-xs"><Database className="h-3.5 w-3.5" /> {d.datos_generados ? 'Actualizar' : 'Generar'} datos del sistema</button>
        </span>}>
        {enPrep && !d.datos_generados && <p className="mb-2 text-[11px] text-slate-500 dark:text-slate-400">Genere los datos del sistema para el periodo evaluado; luego escriba el análisis de cada entrada. Las entradas sin fuente en el sistema se informan en el análisis.</p>}
        <div className="space-y-1.5">
          {d.entradas.map((e) => {
            const ab = abiertas[e.clave]
            const a = analisis[e.clave] || {}
            return (
              <div key={e.clave} className="rounded border border-slate-200 dark:border-slate-700">
                <button type="button" onClick={() => setAbiertas({ ...abiertas, [e.clave]: !ab })} className="flex w-full items-center gap-2 px-2 py-1.5 text-left hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  {ab ? <ChevronDown className="h-3.5 w-3.5 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0" />}
                  <span className="flex-1"><strong>{e.clave})</strong> {e.titulo}</span>
                  {e.completa ? <span className="badge badge-verde">{e.sin_actividad && !e.analisis ? 'Sin actividad' : 'Analizada'}</span> : <span className="badge badge-ambar">Por analizar</span>}
                </button>
                {ab && (
                  <div className="space-y-2 border-t border-slate-200 p-2 dark:border-slate-700">
                    <DatosSistema bloques={e.datos} />
                    {enPrep ? (
                      <div className="space-y-1.5">
                        <CampoAmpliable multilinea rows={3} titulo={`Análisis — entrada ${e.clave})`} placeholder="Análisis del Gerente SIG: tendencia, cumplimiento, conclusiones para la dirección" value={a.analisis || ''} onChange={(v) => setAnalisis({ ...analisis, [e.clave]: { ...a, analisis: v } })} />
                        <div className="flex flex-wrap items-center gap-3">
                          <label className="flex items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" checked={Boolean(a.sin_actividad)} onChange={(ev) => setAnalisis({ ...analisis, [e.clave]: { ...a, sin_actividad: ev.target.checked } })} /> Sin actividad en el periodo</label>
                          <button onClick={() => guardarEntrada(e.clave)} className={`${entradaSinGuardar(e) ? 'btn-primary' : 'btn-secondary'} !py-1 text-xs`}>Guardar</button>
                          {entradaSinGuardar(e) && <span className="text-[11px] text-amber-600 dark:text-amber-400">Cambios sin guardar</span>}
                        </div>
                      </div>
                    ) : <p className="whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Análisis:</strong> {e.analisis || (e.sin_actividad ? 'Sin actividad en el periodo.' : '—')}</p>}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </Seccion>

      {d.estado !== 'preparacion' && <>
        {/* 3. Asistentes */}
        <Seccion titulo="Asistentes (firma de asistencia)" tono={enReunion ? 'azul' : undefined}>
          <table className="tabla-sig w-full">
            <thead><tr><th>N°</th><th>Nombre</th><th>Cargo</th><th className="text-center">Firma</th>{enReunion && <th />}</tr></thead>
            <tbody>
              {asistentes.map((a, i) => (
                <tr key={a.id}>
                  <td>{i + 1}</td><td>{a.nombre}</td><td>{a.cargo}{a.sigla ? ` (${a.sigla})` : ''}</td>
                  <td className="text-center">
                    {a.firma && Object.keys(a.firma).length
                      ? <span className="badge badge-verde" title={fechaHora(a.firma.fecha)}><CheckCircle2 className="mr-1 inline h-3 w-3" />Firmado {fecha(a.firma.fecha)} ({a.firma.metodo === 'pin' ? 'PIN' : 'contraseña'})</span>
                      : enReunion ? <span className="inline-flex items-center gap-1"><Credencial forma={a.forma_firma} valor={cred[a.id]} onChange={(v) => setCred({ ...cred, [a.id]: v })} /><button onClick={() => firmar(a)} className="btn-primary !py-1 text-xs">Firmar</button></span>
                        : <span className="text-slate-400">Sin firma</span>}
                  </td>
                  {enReunion && <td className="text-center">{!(a.firma && Object.keys(a.firma).length) && <button onClick={() => ejecutar(() => api.revision.accion(d.id, 'quitar_asistente', { id: a.id }))} className="text-red-500 hover:underline">quitar</button>}</td>}
                </tr>
              ))}
              {asistentes.length === 0 && <tr><td colSpan={5} className="py-3 text-center text-slate-400">Sin asistentes registrados</td></tr>}
            </tbody>
          </table>
          {enReunion && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <select className={`${inp} !w-80 !py-1 text-xs`} value={nuevoAsistente} onChange={(e) => setNuevoAsistente(e.target.value)}>
                {optT.filter(([v]) => !asistentes.some((a) => String(a.trabajador) === v)).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
              </select>
              <button disabled={!nuevoAsistente} onClick={async () => { if (await ejecutar(() => api.revision.accion(d.id, 'asistente', { trabajador: nuevoAsistente }))) setNuevoAsistente('') }} className="btn-secondary !py-1 text-xs disabled:opacity-50"><UserPlus className="h-3.5 w-3.5" /> Agregar asistente</button>
              <span className="text-[11px] text-slate-500 dark:text-slate-400">Cada asistente firma con la contraseña de su usuario o su PIN. Deben firmar el Gerente SIG y el Gerente General.</span>
            </div>
          )}
        </Seccion>

        {/* 4. Salidas */}
        <Seccion titulo="Agenda — salidas (decisiones y acciones)" tono={enReunion ? 'azul' : undefined}>
          <div className="space-y-2">
            {d.salidas.map((s) => (
              <div key={s.clave}>
                <p className="mb-0.5 font-medium text-slate-700 dark:text-slate-200">{s.clave}) {s.titulo}{s.clave !== 'j' && enReunion && <span className="text-red-500"> *</span>}</p>
                {enReunion ? (
                  <div className="flex items-start gap-2">
                    <div className="flex-1"><CampoAmpliable multilinea rows={2} titulo={`Salida ${s.clave})`} value={salidas[s.clave] || ''} onChange={(v) => setSalidas({ ...salidas, [s.clave]: v })} /></div>
                    {salidaSinGuardar(s) && <button onClick={() => ejecutar(() => api.revision.accion(d.id, 'salida', { clave: s.clave, texto: salidas[s.clave] }))} className="btn-primary !py-1 text-xs">Guardar</button>}
                  </div>
                ) : <p className="whitespace-pre-wrap">{s.texto || '—'}</p>}
              </div>
            ))}
          </div>
        </Seccion>

        {/* 5. Acuerdos */}
        <Seccion titulo="Acuerdos (plan de acción)" tono={enReunion ? 'azul' : undefined}
          extra={enReunion && !acuerdo && <button onClick={() => setAcuerdo({ descripcion: '', elemento: '', responsable: '', fecha_compromiso: '', costo_estimado: '' })} className="btn-secondary !py-1 text-xs"><Plus className="h-3.5 w-3.5" /> Agregar acuerdo</button>}>
          <table className="tabla-sig w-full">
            <thead><tr><th>N°</th><th>Acuerdo</th><th className="text-center">Elemento</th><th>Responsable</th><th className="text-right">Plazo</th><th className="text-right">Costo estimado</th><th className="text-center">Estado</th>{enReunion && <th />}</tr></thead>
            <tbody>
              {d.acuerdos.map((a) => (
                <tr key={a.id}>
                  <td>{a.numero}</td><td className="max-w-sm whitespace-pre-wrap">{a.descripcion}</td>
                  <td className="text-center" title={a.elemento_titulo}>{elementoCorto(a.elemento)}</td>
                  <td>{a.responsable_nombre || '—'}</td>
                  <td className="whitespace-nowrap text-right">{fecha(a.fecha_compromiso)}</td>
                  <td className="whitespace-nowrap text-right">{soles(a.costo_estimado)}</td>
                  <td className="text-center"><span className={BADGE[TONO_ACUERDO(a)]}>{a.vencido ? 'Vencido' : a.estado_display}</span></td>
                  {enReunion && <td className="whitespace-nowrap text-center">
                    <button onClick={() => setAcuerdo({ id: a.id, descripcion: a.descripcion, elemento: a.elemento, responsable: String(a.responsable || ''), fecha_compromiso: a.fecha_compromiso || '', costo_estimado: a.costo_estimado ?? '' })} className="mr-2 text-esynapse-500 hover:underline">editar</button>
                    <button onClick={() => ejecutar(() => api.revision.accion(d.id, 'quitar_acuerdo', { id: a.id }))} className="text-red-500 hover:underline">quitar</button>
                  </td>}
                </tr>
              ))}
              {d.acuerdos.length === 0 && <tr><td colSpan={8} className="py-3 text-center text-slate-400">Sin acuerdos</td></tr>}
            </tbody>
          </table>
          {acuerdo && (
            <div className="mt-2 space-y-2 rounded-lg border border-dashed border-esynapse-500/50 p-2">
              <CampoAmpliable multilinea rows={2} titulo="Acuerdo / acción" placeholder="Acuerdo o acción" value={acuerdo.descripcion} onChange={(v) => setAcuerdo({ ...acuerdo, descripcion: v })} />
              <div className="grid gap-2 md:grid-cols-4">
                <div className="md:col-span-2"><label className={lbl}>Elemento de la revisión que lo origina</label>
                  <select className={inp} value={acuerdo.elemento} onChange={(e) => setAcuerdo({ ...acuerdo, elemento: e.target.value })}>
                    <option value="">—</option>{(cat?.elementos || []).map(([v, n]) => <option key={v} value={v}>{n.length > 90 ? `${n.slice(0, 90)}…` : n}</option>)}
                  </select></div>
                <div><label className={lbl}>Responsable</label><select className={inp} value={acuerdo.responsable} onChange={(e) => setAcuerdo({ ...acuerdo, responsable: e.target.value })}>{optT.map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></div>
                <div className="grid grid-cols-2 gap-2">
                  <div><label className={lbl}>Fecha de cumplimiento</label><input type="date" className={inp} value={acuerdo.fecha_compromiso} onChange={(e) => setAcuerdo({ ...acuerdo, fecha_compromiso: e.target.value })} /></div>
                  <div><label className={lbl}>Costo estimado (S/)</label><input type="number" min="0" step="0.01" className={`${inp} text-right`} value={acuerdo.costo_estimado} onChange={(e) => setAcuerdo({ ...acuerdo, costo_estimado: e.target.value })} /></div>
                </div>
              </div>
              <div className="flex gap-2"><button onClick={guardarAcuerdo} className="btn-primary !py-1 text-xs">{acuerdo.id ? 'Guardar acuerdo' : 'Agregar'}</button><button onClick={() => setAcuerdo(null)} className="btn-secondary !py-1 text-xs">Cancelar</button></div>
            </div>
          )}
        </Seccion>

        {/* 6. Conclusiones y comunicación */}
        <Seccion titulo="Conclusiones, observaciones y comunicación de resultados" tono={enReunion ? 'azul' : d.estado === 'cerrada' ? 'verde' : undefined}>
          {enReunion ? (
            <div className="space-y-2">
              <div><label className={lbl}>Conclusiones <span className="text-red-500">*</span></label><CampoAmpliable multilinea rows={3} titulo="Conclusiones" value={reunion.conclusiones || ''} onChange={(v) => setReunion({ ...reunion, conclusiones: v })} /></div>
              <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} titulo="Observaciones" value={reunion.observaciones || ''} onChange={(v) => setReunion({ ...reunion, observaciones: v })} /></div>
              <div className="grid gap-2 md:grid-cols-4">
                <div><label className={lbl}>Comunicación: fecha</label><input type="date" className={inp} value={reunion.comunicacion_fecha || ''} onChange={(e) => setReunion({ ...reunion, comunicacion_fecha: e.target.value })} /></div>
                <div><label className={lbl}>Reunión del Comité de SST</label><select className={inp} value={String(reunion.reunion_comite || '')} onChange={(e) => setReunion({ ...reunion, reunion_comite: e.target.value })}>
                  <option value="">—</option>{reuniones.map((r) => <option key={r.id} value={r.id}>{r.codigo} · {fecha(r.fecha)}</option>)}</select></div>
                <div className="md:col-span-2"><label className={lbl}>Cómo se comunicó a los trabajadores y al Comité</label><CampoAmpliable value={reunion.comunicacion_detalle || ''} onChange={(v) => setReunion({ ...reunion, comunicacion_detalle: v })} /></div>
              </div>
              <div className="flex items-center gap-3"><button onClick={guardarReunion} className={`${reunionSinGuardar ? 'btn-primary' : 'btn-secondary'} !py-1.5 text-xs`}>Guardar</button>{reunionSinGuardar && <span className="text-[11px] text-amber-600 dark:text-amber-400">Cambios sin guardar</span>}</div>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Conclusiones:</strong> {d.conclusiones || '—'}</p>
              <p className="whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Observaciones:</strong> {d.observaciones || '—'}</p>
              <Dato etiqueta="Comunicación de resultados" valor={[fecha(d.comunicacion_fecha), d.reunion_comite_codigo && `Comité ${d.reunion_comite_codigo}`, d.comunicacion_detalle].filter(Boolean).join(' · ')} />
              {d.firma_cierre?.nombre && <p className="text-[11px] text-emerald-600 dark:text-emerald-400">Cerrada por {d.firma_cierre.nombre} el {fechaHora(d.firma_cierre.fecha)}.</p>}
            </div>
          )}
        </Seccion>
      </>}

      {etapaFinal && <BarraEtapa titulo={etapaFinal.titulo} bloqueo={etapaFinal.bloqueo} botones={[{ texto: etapaFinal.boton, accion: etapaFinal.accion }]} />}
      <MsgError texto={error} />
    </div>
  )
}

// ================================================================================================= programa anual
function Programa({ puestos, tienePermiso }) {
  const [anio, setAnio] = useState(ANIO)
  const [p, setP] = useState(undefined)
  const [error, setError] = useState('')
  const [obs, setObs] = useState({})
  const puedeEditar = tienePermiso('revision_direccion', 'editar')
  const cargar = useCallback(async () => { setP(await api.revision.programa(anio)) }, [anio])
  useEffect(() => { setP(undefined); cargar().catch((e) => setError(e.message)) }, [cargar])
  useEffect(() => { if (p) setObs(Object.fromEntries(p.items.map((i) => [i.id, i.observaciones]))) }, [p?.id])

  const item = async (it, datos) => {
    setError('')
    try { setP(await api.revision.itemPrograma(p.id, { id: it.id, ...datos })) } catch (e) { setError(e.message) }
  }
  // Clic en un mes: vacío → P → P/E → vacío (E solo en meses que ya pasaron o en curso).
  const ciclo = (it, m) => {
    const prog = it.meses.includes(m)
    const ejec = it.ejecutados.includes(m)
    const pasado = anio < ANIO || (anio === ANIO && m <= MES)
    let meses = it.meses
    let ejecutados = it.ejecutados
    if (!prog && !ejec) meses = [...meses, m]
    else if (prog && !ejec && pasado) ejecutados = [...ejecutados, m]
    else { meses = meses.filter((x) => x !== m); ejecutados = ejecutados.filter((x) => x !== m) }
    item(it, { meses, ejecutados })
  }
  const filas = (pref) => (p?.items || []).filter((i) => i.clave.startsWith(pref))
  const n0 = filas('e-').length

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <select className={`${inp} w-32`} aria-label="Año" value={anio} onChange={(e) => setAnio(Number(e.target.value))}>
          {[ANIO + 1, ANIO, ANIO - 1].map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        {p && <div className="flex items-center gap-2 text-xs"><label className="text-slate-500">Fecha de elaboración</label>
          <input type="date" disabled={!puedeEditar} className={`${inp} !w-40 !py-1 text-xs`} value={p.fecha_elaboracion || ''} onChange={async (e) => { try { setP(await api.revision.editarPrograma(p.id, { fecha_elaboracion: e.target.value })) } catch (er) { setError(er.message) } }} /></div>}
        <div className="ml-auto flex gap-2">
          {p && <button onClick={() => abrirPdf(api.revision.programaPdf(p.id), setError)} className="btn-secondary"><FileText className="h-4 w-4" /> Imprimir programa</button>}
          {p === null && tienePermiso('revision_direccion', 'crear') && <button onClick={async () => { try { await api.revision.crearPrograma(anio); await cargar() } catch (e) { setError(e.message) } }} className="btn-primary"><Plus className="h-4 w-4" /> Elaborar programa {anio}</button>}
        </div>
      </div>
      <MsgError texto={error} />
      {p === null && <p className="card-esynapse p-6 text-center text-sm text-slate-400">Aún no se elabora el programa de revisión por la dirección {anio}.</p>}
      {p && (
        <div className="card-esynapse overflow-x-auto">
          <table className="tabla-sig min-w-[1100px] text-xs">
            <thead>
              <tr><th>Ítem</th><th>Agenda</th><th>Responsable de la información</th>{MESES.map((m) => <th key={m} className="!px-1">{m}</th>)}<th>Observaciones</th></tr>
            </thead>
            <tbody>
              {[['ELEMENTOS DE ENTRADA', 'e-', 0], ['SALIDAS', 's-', n0]].map(([titulo, pref, base]) => [
                <tr key={titulo}><td colSpan={16} className="bg-esynapse-600/10 font-semibold">{titulo}</td></tr>,
                ...filas(pref).map((it, i) => (
                  <tr key={it.id}>
                    <td className="text-center">{base + i + 1}</td>
                    <td className="min-w-[18rem]">{it.titulo.replace(/^(Entrada|Salida) /, '')}</td>
                    <td><select disabled={!puedeEditar} className={`${inp} !w-44 !py-0.5 text-[11px]`} value={String(it.responsable || '')} onChange={(e) => item(it, { responsable: e.target.value || null })}>
                      <option value="">—</option>{puestos.map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}</select></td>
                    {MESES.map((_, k) => {
                      const m = k + 1
                      const prog = it.meses.includes(m)
                      const ejec = it.ejecutados.includes(m)
                      return (
                        <td key={m} className="!px-0.5 text-center">
                          <button disabled={!puedeEditar} onClick={() => ciclo(it, m)} title="Clic: programar → ejecutado → quitar"
                            className={`h-6 w-8 rounded text-[10px] font-semibold ${ejec ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : prog ? 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300' : 'border border-dashed border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800'}`}>
                            {prog && ejec ? 'P/E' : prog ? 'P' : ejec ? 'E' : ''}
                          </button>
                        </td>
                      )
                    })}
                    <td><input disabled={!puedeEditar} className={`${inp} !w-44 !py-0.5 text-[11px]`} value={obs[it.id] ?? ''} onChange={(e) => setObs({ ...obs, [it.id]: e.target.value })}
                      onBlur={() => (obs[it.id] ?? '') !== (it.observaciones ?? '') && item(it, { observaciones: obs[it.id] })} /></td>
                  </tr>
                )),
              ])}
            </tbody>
          </table>
          <p className="px-3 py-2 text-[11px] text-slate-500 dark:text-slate-400">P: programado · E: ejecutado. Clic en el mes para programarlo, marcarlo ejecutado o quitarlo.</p>
        </div>
      )}
    </div>
  )
}

// ================================================================================================= plan de acción
function PlanAccion({ tienePermiso, onIrRevision }) {
  const confirmar = useConfirm()
  const [vista, setVista] = useState('pendientes')
  const [items, setItems] = useState([])
  const [sel, setSel] = useState(null)
  const [f, setF] = useState({})
  const [error, setError] = useState('')
  const puedeEditar = tienePermiso('revision_direccion', 'editar')
  const cargar = useCallback(async () => { const d = await api.revision.acuerdos(vista === 'pendientes' ? '?estado=pendientes' : ''); setItems(d.results ?? d) }, [vista])
  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  const abrir = (a) => { setError(''); setSel(a); setF({ evidencia: a.evidencia, seguimiento_1: a.seguimiento_1, seguimiento_2: a.seguimiento_2, estado: a.estado, archivo: null }) }
  const editable = sel && sel.revision_estado === 'cerrada' && sel.estado !== 'cerrado' && puedeEditar

  const guardar = async () => {
    setError('')
    try {
      const fd = new FormData()
      for (const c of ['evidencia', 'seguimiento_1', 'seguimiento_2', 'estado']) fd.append(c, f[c] ?? '')
      if (f.archivo) fd.append('archivo_evidencia', f.archivo)
      const a = await api.revision.seguimiento(sel.id, fd)
      abrir(a); await cargar()
    } catch (e) { setError(e.message) }
  }
  const vb = async () => {
    const c = await confirmar({ titulo: 'V°B° de cumplimiento', textoConfirmar: 'Firmar', mensaje: `El acuerdo ${sel.revision_codigo} N.° ${sel.numero} queda cerrado y de solo lectura.`, entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
    if (c === null || c === undefined) return
    try { const a = await api.revision.cerrarAcuerdo(sel.id, c); abrir(a); await cargar() } catch (e) { setError(e.message) }
  }
  const sinGuardar = sel && (['evidencia', 'seguimiento_1', 'seguimiento_2', 'estado'].some((c) => (f[c] ?? '') !== (sel[c] ?? '')) || f.archivo)

  return (
    <div className="space-y-3">
      <div className="flex items-center"><div className="ml-auto"><Vistas opciones={[['pendientes', 'Pendientes'], ['todos', 'Todos']]} valor={vista} onChange={setVista} /></div></div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig min-w-[1000px]">
          <thead><tr><th>Revisión</th><th>N°</th><th>Acuerdo / acción</th><th className="text-center">Elemento</th><th>Responsable</th><th className="text-right">Fecha de cumplimiento</th><th className="text-right">Costo estimado</th><th className="text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id} className="fila" onClick={() => abrir(a)}>
                <td className="whitespace-nowrap font-semibold text-esynapse-700 dark:text-esynapse-300">{a.revision_codigo}</td>
                <td>{a.numero}</td>
                <td className="max-w-md"><span className="line-clamp-2" title={a.descripcion}>{a.descripcion}</span></td>
                <td className="text-center" title={a.elemento_titulo}>{elementoCorto(a.elemento)}</td>
                <td>{a.responsable_nombre || '—'}</td>
                <td className="whitespace-nowrap text-right">{fecha(a.fecha_compromiso)}</td>
                <td className="whitespace-nowrap text-right">{soles(a.costo_estimado)}</td>
                <td className="text-center"><span className={BADGE[TONO_ACUERDO(a)]}>{a.revision_estado !== 'cerrada' ? 'En reunión' : a.vencido ? 'Vencido' : a.estado_display}</span></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-center text-slate-400">{vista === 'pendientes' ? 'No hay acuerdos pendientes' : 'Sin acuerdos'}</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal abierto={Boolean(sel)} titulo={sel ? `${sel.revision_codigo} · Acuerdo N.° ${sel.numero}` : ''} onCerrar={() => setSel(null)} ancho="max-w-3xl">
        {sel && (
          <div className="space-y-3 text-sm">
            <Seccion titulo="Acordado en la reunión" extra={<button onClick={() => { setSel(null); onIrRevision(sel.revision) }} className="text-xs text-esynapse-500 hover:underline">Ver la revisión</button>}>
              <p className="whitespace-pre-wrap">{sel.descripcion}</p>
              <div className="mt-1 grid gap-x-4 md:grid-cols-2">
                <Dato etiqueta="Elemento que lo origina" valor={sel.elemento_titulo} />
                <Dato etiqueta="Responsable" valor={sel.responsable_nombre} />
                <Dato etiqueta="Fecha de cumplimiento" valor={fecha(sel.fecha_compromiso)} />
                <Dato etiqueta="Costo estimado" valor={soles(sel.costo_estimado)} />
              </div>
            </Seccion>
            <Seccion titulo="Seguimiento" tono={editable ? 'azul' : sel.estado === 'cerrado' ? 'verde' : undefined}>
              {sel.revision_estado !== 'cerrada' && <p className="text-[11px] text-slate-500">El seguimiento se registra cuando la revisión está cerrada.</p>}
              {editable ? (
                <div className="space-y-2">
                  <div><label className={lbl}>Evidencia de ejecución</label><CampoAmpliable multilinea rows={2} value={f.evidencia || ''} onChange={(v) => setF({ ...f, evidencia: v })} /></div>
                  <div className="grid gap-2 md:grid-cols-2">
                    <div><label className={lbl}>Seguimiento 1.er semestre</label><CampoAmpliable multilinea rows={2} value={f.seguimiento_1 || ''} onChange={(v) => setF({ ...f, seguimiento_1: v })} /></div>
                    <div><label className={lbl}>Seguimiento 2.º semestre</label><CampoAmpliable multilinea rows={2} value={f.seguimiento_2 || ''} onChange={(v) => setF({ ...f, seguimiento_2: v })} /></div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <select className={`${inp} !w-40 !py-1 text-xs`} value={f.estado} onChange={(e) => setF({ ...f, estado: e.target.value })}><option value="abierto">Abierto</option><option value="en_proceso">En proceso</option></select>
                    <label className="btn-secondary cursor-pointer !py-1 text-xs"><Paperclip className="h-3.5 w-3.5" /> {f.archivo ? f.archivo.name : 'Adjuntar evidencia'}
                      <input type="file" className="hidden" onChange={(e) => { if (e.target.files[0]) setF({ ...f, archivo: e.target.files[0] }); e.target.value = '' }} /></label>
                    {sel.archivo_evidencia_url && <a href={sel.archivo_evidencia_url} target="_blank" rel="noreferrer" className="text-xs text-esynapse-500 underline">archivo actual</a>}
                    <button onClick={guardar} className={`${sinGuardar ? 'btn-primary' : 'btn-secondary'} !py-1 text-xs`}>Guardar seguimiento</button>
                  </div>
                </div>
              ) : (
                <div className="space-y-1">
                  <Dato etiqueta="Evidencia" valor={sel.evidencia} />
                  {sel.archivo_evidencia_url && <a href={sel.archivo_evidencia_url} target="_blank" rel="noreferrer" className="text-esynapse-500 underline">Archivo de evidencia</a>}
                  <Dato etiqueta="Seguimiento 1.er semestre" valor={sel.seguimiento_1} />
                  <Dato etiqueta="Seguimiento 2.º semestre" valor={sel.seguimiento_2} />
                  {sel.firma_cierre?.nombre && <p className="text-[11px] text-emerald-600 dark:text-emerald-400">V°B° de cumplimiento: {sel.firma_cierre.nombre}, {fechaHora(sel.firma_cierre.fecha)}.</p>}
                </div>
              )}
            </Seccion>
            {editable && tienePermiso('revision_direccion', 'aprobar') && (
              <BarraEtapa titulo="V°B° de cumplimiento (cierra el acuerdo)" bloqueo={sinGuardar ? 'Guarde primero el seguimiento.' : !(sel.evidencia || '').trim() && !sel.archivo_evidencia_url ? 'Registre la evidencia de ejecución.' : ''}
                botones={[{ texto: 'Dar V°B° y cerrar', accion: vb }]} />
            )}
            <MsgError texto={error} />
          </div>
        )}
      </Modal>
    </div>
  )
}
