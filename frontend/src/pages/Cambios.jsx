import { useCallback, useEffect, useRef, useState } from 'react'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import { AlertTriangle, Check, FileText, Image, Lock, Pencil, Plus, RefreshCw, RotateCcw, Search, Trash2, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import { useCatalogoProcesos } from '../components/SelectorProceso.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora, hoy as hoyLocal } from '../lib/fecha.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import { Vistas } from '../components/NavModulo.jsx'
import BarraPasos from '../components/BarraPasos.jsx'
import { useAbrirDesdeEnlace } from '../lib/enlaces.js'

// Colores de estado (regla 10): gris inicial · ámbar evaluación/aprobación · azul planificación/implementación ·
// violeta verificación · verde cerrado · rojo rechazado.
const COLOR_ESTADO = {
  solicitado: 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
  en_evaluacion: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  en_aprobacion: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  rechazado: 'bg-red-500/15 text-red-600 dark:text-red-400',
  archivado: 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
  en_planificacion: 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  en_implementacion: 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  en_verificacion: 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
  temporal_vigente: 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  cerrado: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
}
const PASOS = [['solicitado', 'Solicitud'], ['en_evaluacion', 'Evaluación'], ['en_aprobacion', 'Aprobación'],
  ['en_planificacion', 'Planificación'], ['en_implementacion', 'Implementación'], ['en_verificacion', 'Eficacia'], ['cerrado', 'Cerrado']]
// Un cambio temporal tiene un paso más: queda en vigor hasta registrar su fin.
const pasosDe = (c) => (c?.temporalidad === 'temporal' ? [...PASOS.slice(0, 6), ['temporal_vigente', 'En vigor'], PASOS[6]] : PASOS)
const ETAPAS_PRORROGA = ['en_implementacion', 'en_verificacion', 'temporal_vigente']
const FORM_VACIO = { proceso_solicitante: '', fecha_solicitud: '', prioridad: 'media', origen: 'interno', motivo_origen: '', descripcion: '', justificacion: '' }
const CAMPOS_EVAL = ['factibilidad_tecnica', 'aspectos_operativos', 'aspectos_financieros', 'procesos_afectados', 'alcance', 'beneficios',
  'impactos', 'riesgos', 'controles', 'consecuencias', 'clasificacion', 'es_tecnico', 'afecta_clientes', 'responsable_evaluador', 'equipo_evaluador']
const CAMPOS_PLAN = ['fecha_planificacion', 'prevision', 'temporalidad', 'fecha_reversion', 'fuentes', 'fuente_otro',
  'responsable_implementacion', 'plazo_implementacion', 'equipo_implementacion']
const CAMPOS_EFIC = ['se_implemento', 'fue_eficaz', 'criterios_eficacia', 'verificacion', 'reversion', 'detalle_reversion', 'fecha_reversion_real', 'sac_derivada']
const hoy = () => hoyLocal()
const siNo = (v) => (v == null ? '—' : v ? 'Sí' : 'No')
const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'

function Seccion({ titulo, tono, children }) {
  const tonos = { ambar: 'border-amber-500/30 bg-amber-500/5', azul: 'border-esynapse-600/30 bg-esynapse-600/5', violeta: 'border-violet-500/30 bg-violet-500/5' }
  return (
    <div className={`rounded-lg border p-3 text-xs ${tonos[tono] || 'border-slate-200 dark:border-slate-800'}`}>
      <p className="mb-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">{titulo}</p>
      <div className="space-y-2 text-slate-600 dark:text-slate-300">{children}</div>
    </div>
  )
}
function Dato({ etiqueta, valor }) {
  return <p><strong className="text-slate-700 dark:text-slate-200">{etiqueta}:</strong> <span className="whitespace-pre-wrap">{valor || '—'}</span></p>
}
const toggle = (lista, v) => (lista.includes(v) ? lista.filter((x) => x !== v) : [...lista, v])

export default function Cambios() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const procesos = useCatalogoProcesos()
  const [items, setItems] = useState([])
  const [cat, setCat] = useState(null)
  const [usuarios, setUsuarios] = useState([])
  const [docs, setDocs] = useState([])
  const [sacs, setSacs] = useState([])
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('')
  const [soloAbiertos, setSoloAbiertos] = useState(false)
  const [modalForm, setModalForm] = useState(false)
  const [editandoId, setEditandoId] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [d, setD] = useState(null)
  const [error, setError] = useState('')
  const [evalF, setEvalF] = useState({})
  const [planF, setPlanF] = useState({})
  const [eficF, setEficF] = useState({})
  const [docsF, setDocsF] = useState([])
  const [actF, setActF] = useState(null)
  const [comF, setComF] = useState(null)
  const [fotoF, setFotoF] = useState(null)
  const [completar, setCompletar] = useState(null)
  const [finF, setFinF] = useState(null)
  const [prorF, setProrF] = useState(null)

  // El aviso de error se lleva a la vista: la acción puede estar al final de una ficha larga.
  const errorRef = useRef(null)
  useEffect(() => { if (error && errorRef.current) errorRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [error])

  const puedeEditar = tienePermiso('cambios', 'editar')
  const puedeAprobar = tienePermiso('cambios', 'aprobar')

  const filtros = useCallback(() => {
    const p = new URLSearchParams()
    if (buscar) p.set('buscar', buscar)
    if (estado) p.set('estado', estado)
    if (soloAbiertos) p.set('abiertos', '1')
    return `?${p}`
  }, [buscar, estado, soloAbiertos])
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const r = await ultima(api.cambios.listar(filtros()))
    setItems(r.results ?? r)
  }, [filtros])
  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
    api.cambios.catalogos().then(setCat).catch(() => {})
    api.usuarios.listar().then((r) => setUsuarios(r.results ?? r)).catch(() => {})
    api.documentos.listar('?page_size=500').then((r) => setDocs(r.results ?? r)).catch(() => {})
    api.sac.listar('?page_size=500').then((r) => setSacs(r.results ?? r)).catch(() => {})
  }, [])

  const cargarFormularios = (c) => {
    setEvalF(Object.fromEntries(CAMPOS_EVAL.map((k) => [k, c[k] ?? (Array.isArray(c[k]) ? [] : '')])))
    setPlanF(Object.fromEntries(CAMPOS_PLAN.map((k) => [k, c[k] ?? ''])))
    setEficF(Object.fromEntries(CAMPOS_EFIC.map((k) => [k, c[k] ?? ''])))
    setDocsF(c.documentos_actualizados || [])
    setActF(null); setComF(null); setFotoF(null); setCompletar(null); setFinF(null); setProrF(null)
  }
  const abrir = async (id) => {
    setError('')
    const c = await api.cambios.detalle(id)
    setD(c)
    cargarFormularios(c)
  }
  const refrescar = async (c) => {
    await cargar()
    if (!c && !d) return
    const n = c || await api.cambios.detalle(d.id)
    if (!d || n.estado !== d.estado) cargarFormularios(n)
    else { setActF(null); setComF(null); setFotoF(null); setCompletar(null); setFinF(null); setProrF(null) }
    setD(n)
  }
  const accion = async (fn) => {
    setError('')
    try { const r = await fn(); await refrescar(r && r.id ? r : null) } catch (e) { setError(e.message) }
  }
  const abrirPdf = async (promesa) => {
    setError('')
    try {
      const url = URL.createObjectURL(await promesa)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  // --- Solicitud (nueva / corregir) ---
  const nueva = () => { setForm({ ...FORM_VACIO, fecha_solicitud: hoy() }); setEditandoId(null); setError(''); setModalForm(true) }
  const corregir = () => {
    setForm(Object.fromEntries(Object.keys(FORM_VACIO).map((k) => [k, d[k] ?? ''])))
    setEditandoId(d.id); setError(''); setModalForm(true)
  }
  const guardarSolicitud = async (e) => {
    e.preventDefault()
    setError('')
    const datos = { ...form, proceso_solicitante: form.proceso_solicitante || null }
    try {
      if (editandoId) { await api.cambios.editar(editandoId, datos); setModalForm(false); await refrescar() }
      else { const c = await api.cambios.crear(datos); setModalForm(false); await cargar(); await abrir(c.id) }
    } catch (e2) { setError(e2.message) }
  }

  const difiere = (f, campos) => d && campos.some((k) => {
    const a = f[k]; const b = d[k]
    if (Array.isArray(a)) return JSON.stringify([...a].sort()) !== JSON.stringify([...(b || [])].sort())
    if (typeof a === 'boolean') return a !== Boolean(b)
    return String(a ?? '') !== String(b == null ? '' : b)
  })
  // Campos que admiten vacío como «sin dato» (relaciones, fechas y sí/no); los textos se envían tal cual.
  const NULABLES = ['responsable_evaluador', 'fecha_planificacion', 'fecha_reversion', 'responsable_implementacion',
    'plazo_implementacion', 'fecha_reversion_real', 'sac_derivada', 'se_implemento', 'fue_eficaz']
  const vacioANull = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v === '' && NULABLES.includes(k) ? null : (v ?? (NULABLES.includes(k) ? null : ''))]))
  const guardarEval = () => accion(() => api.cambios.editar(d.id, vacioANull({ ...evalF, clasificacion: evalF.clasificacion || '' })))
  const guardarPlan = () => accion(() => api.cambios.editar(d.id, vacioANull(planF)))
  const guardarEfic = () => accion(() => api.cambios.editar(d.id, {
    ...vacioANull(eficF), se_implemento: eficF.se_implemento === '' ? null : eficF.se_implemento === true || eficF.se_implemento === 'true',
    fue_eficaz: eficF.fue_eficaz === '' ? null : eficF.fue_eficaz === true || eficF.fue_eficaz === 'true', reversion: eficF.reversion || 'ninguna',
  }))
  const guardarDocs = () => accion(() => api.cambios.editar(d.id, { documentos_actualizados: docsF }))

  // --- Actividades ---
  const guardarActividad = () => accion(() => (actF.id
    ? api.cambios.accion(d.id, 'editar_actividad', { actividad_id: actF.id, ...actF })
    : api.cambios.accion(d.id, 'agregar_actividad', actF)))
  const quitarActividad = async (a) => {
    if (!await confirmar({ titulo: 'Quitar actividad', mensaje: `¿Quitar «${a.actividad}» del plan?`, textoConfirmar: 'Quitar', peligro: true })) return
    accion(() => api.cambios.accion(d.id, 'quitar_actividad', { actividad_id: a.id }))
  }
  const completarActividad = () => accion(async () => {
    const fd = new FormData()
    fd.append('actividad_id', completar.id); fd.append('seguimiento', completar.seguimiento || '')
    if (completar.evidencia) fd.append('evidencia', completar.evidencia)
    return api.cambios.subir(d.id, 'completar_actividad', fd)
  })
  const registrarComunicacion = () => accion(async () => {
    const fd = new FormData()
    Object.entries(comF).forEach(([k, v]) => { if (v) fd.append(k, v) })
    return api.cambios.subir(d.id, 'comunicar', fd)
  })
  const subirFoto = () => accion(async () => {
    const fd = new FormData()
    Object.entries(fotoF).forEach(([k, v]) => { if (v) fd.append(k, v) })
    return api.cambios.subir(d.id, 'agregar_foto', fd)
  })

  // --- Resolución y cierre ---
  const firmar = (titulo, mensaje) => confirmar({ titulo, mensaje, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
  const aprobar = async () => {
    const clave = await firmar('Aprobar el cambio', `Como Gerente General aprueba ${d.codigo}. Los procesos afectados recibirán el aviso de revisar su ficha.`)
    if (clave !== null) accion(() => api.cambios.accion(d.id, 'resolver', { aprobado: true, password: clave }))
  }
  const rechazar = async () => {
    const motivo = await confirmar({ titulo: 'Rechazar el cambio', mensaje: 'Indique el motivo. Luego podrá reevaluarse o archivarse.', textoConfirmar: 'Continuar', peligro: true, entrada: { etiqueta: 'Motivo del rechazo', obligatorio: true, multilinea: true } })
    if (motivo === null) return
    const clave = await firmar('Firmar el rechazo', 'Confirme con su contraseña.')
    if (clave !== null) accion(() => api.cambios.accion(d.id, 'resolver', { aprobado: false, comentarios: motivo, password: clave }))
  }
  const conMotivo = (titulo, nombre, etiqueta) => async () => {
    const motivo = await confirmar({ titulo, mensaje: 'El motivo queda en el historial del cambio.', textoConfirmar: titulo.split(' ')[0], entrada: { etiqueta, obligatorio: true, multilinea: true } })
    if (motivo !== null) accion(() => api.cambios.accion(d.id, nombre, { motivo }))
  }
  const simple = (nombre, titulo, mensaje) => async () => {
    if (!await confirmar({ titulo, mensaje, textoConfirmar: 'Continuar' })) return
    accion(() => api.cambios.accion(d.id, nombre))
  }
  // --- Cambio temporal en vigor ---
  const registrarFin = () => accion(async () => {
    const fd = new FormData()
    Object.entries(finF).forEach(([k, v]) => { if (v) fd.append(k, v) })
    return api.cambios.subir(d.id, 'registrar_fin_temporal', fd)
  })
  const prorrogar = async () => {
    const clave = await firmar('Prorrogar el cambio temporal', `Como Gerente General amplía el fin de ${d.codigo} del ${fecha(d.fecha_reversion)} al ${prorF.fecha_nueva}.`)
    if (clave !== null) accion(() => api.cambios.accion(d.id, 'prorrogar', { ...prorF, password: clave }))
  }
  const nuevoPermanente = async () => {
    if (!await confirmar({ titulo: 'Volver permanente el cambio', mensaje: `Se registra una nueva solicitud que referencia ${d.codigo}, con su propia evaluación y aprobación. Este cambio sigue en vigor hasta registrar su fin.`, textoConfirmar: 'Registrar solicitud' })) return
    setError('')
    try { const n = await api.cambios.accion(d.id, 'nuevo_cambio_permanente'); await cargar(); await abrir(n.id) } catch (e) { setError(e.message) }
  }
  const anular = async () => {
    if (!await confirmar({ titulo: 'Anular solicitud', mensaje: `¿Anular ${d.codigo}? Solo para una solicitud registrada por error.`, textoConfirmar: 'Anular', peligro: true })) return
    try { await api.cambios.anular(d.id); setD(null); await cargar() } catch (e) { setError(e.message) }
  }

  const nombreProceso = (id) => procesos.find((p) => p.id === Number(id))?.nombre
  const motivos = (cat?.motivos_origen || {})[form.origen] || []
  const usuariosOpc = [['', '— Seleccionar —'], ...usuarios.map((u) => [String(u.id), u.nombre_completo])]
  const sel = (etiqueta, valor, onChange, opciones, extra = {}) => (
    <div>
      <label className={lbl}>{etiqueta}</label>
      <select className={inp} value={valor ?? ''} onChange={onChange} {...extra}>
        {opciones.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
      </select>
    </div>
  )
  const area = (etiqueta, f, setF, k, rows = 2) => (
    <div>
      <label className={lbl}>{etiqueta}</label>
      <CampoAmpliable multilinea rows={rows} titulo={etiqueta} value={f[k] || ''} onChange={(v) => setF({ ...f, [k]: v })} />
    </div>
  )
  const casillas = (opciones, valor, onChange) => (
    <div className="grid gap-1 sm:grid-cols-2">
      {opciones.map(([k, t]) => (
        <label key={k} className="flex cursor-pointer items-start gap-1.5"><input type="checkbox" className="mt-0.5 accent-esynapse-600" checked={(valor || []).includes(k)} onChange={() => onChange(toggle(valor || [], k))} /> {t}</label>
      ))}
    </div>
  )
  const usuariosMulti = (valor, onChange) => (
    <div className="flex flex-wrap gap-x-3 gap-y-1">
      {usuarios.map((u) => (
        <label key={u.id} className="flex cursor-pointer items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" checked={(valor || []).includes(u.id)} onChange={() => onChange(toggle(valor || [], u.id))} /> {u.nombre_completo}</label>
      ))}
    </div>
  )

  const pasos = pasosDe(d)
  const pasoActual = d ? pasos.findIndex(([e]) => e === d.estado) : -1
  const evalSinGuardar = d?.estado === 'en_evaluacion' && difiere(evalF, CAMPOS_EVAL)
  const planSinGuardar = d?.estado === 'en_planificacion' && difiere(planF, CAMPOS_PLAN)
  const eficSinGuardar = d?.estado === 'en_verificacion' && difiere(eficF, CAMPOS_EFIC)
  const actsEditables = d && ['en_evaluacion', 'en_planificacion'].includes(d.estado) && puedeEditar
  const comunicacionAbierta = d && ['en_planificacion', 'en_implementacion', 'en_verificacion', 'temporal_vigente'].includes(d.estado) && puedeEditar
  const quedaEnVigor = d && d.temporalidad === 'temporal' && (eficF.reversion || 'ninguna') !== 'total'
  const pendientes = d ? d.actividades.filter((a) => !a.completada).length : 0

  const barra = !d ? null : {
    solicitado: puedeEditar && { titulo: 'Cerrar la solicitud', nota: 'Pasa a evaluación del Área SIG.', botones: [{ texto: 'Enviar a evaluación', accion: simple('enviar_evaluacion', 'Enviar a evaluación', 'La solicitud queda de solo lectura y pasa al Área SIG.') }] },
    en_evaluacion: puedeEditar && { titulo: 'Cerrar la evaluación', nota: 'Pasa a la aprobación del Gerente General.', bloqueo: evalSinGuardar ? 'Guarde primero la evaluación.' : '', botones: [{ texto: 'Enviar a aprobación', accion: simple('enviar_aprobacion', 'Enviar a aprobación', 'La evaluación y el plan de ejecución quedan para la resolución del Gerente General.') }] },
    en_aprobacion: puedeAprobar && { titulo: 'Resolución del Gerente General', nota: 'Se firma con su contraseña.', botones: [{ texto: 'Rechazar', accion: rechazar, peligro: true }, { texto: 'Aprobar', accion: aprobar }] },
    rechazado: puedeEditar && { titulo: 'Cambio rechazado', nota: 'Puede reevaluarse con la propuesta ajustada o archivarse.', botones: [{ texto: 'Archivar', accion: conMotivo('Archivar el cambio', 'archivar', 'Motivo del archivo'), secundario: true }, { texto: 'Reevaluar', accion: conMotivo('Reevaluar el cambio', 'reevaluar', 'Qué se ajusta') }] },
    en_planificacion: puedeEditar && { titulo: 'Cerrar la planificación', nota: d.requiere_planificacion ? 'Cambio mayor o técnico: la planificación completa es obligatoria.' : 'Cambio menor: basta el plan de ejecución; si no registra responsable y plazo de implementación, se toman de sus actividades.', aviso: d.afecta_clientes && !d.comunicaciones.some((c) => c.destinatario === 'clientes') ? 'Afecta a clientes o actividades acreditadas: comunique a los clientes antes de implementar.' : '', bloqueo: planSinGuardar ? 'Guarde primero la planificación.' : '', botones: [{ texto: 'Iniciar implementación', accion: simple('iniciar_implementacion', 'Iniciar implementación', 'La planificación queda de solo lectura.') }] },
    en_implementacion: puedeEditar && { titulo: 'Cerrar la implementación', nota: pendientes ? `Faltan ${pendientes} actividad(es).` : 'Todas las actividades están completas.', aviso: d.comunicaciones.length ? '' : 'Aún no se registra la comunicación del cambio.', botones: [{ texto: 'Pasar a verificación de la eficacia', accion: simple('pasar_a_verificacion', 'Pasar a verificación', 'El Gerente SIG verificará la eficacia del cambio.') }] },
    en_verificacion: puedeEditar && (quedaEnVigor
      ? { titulo: 'Confirmar la eficacia', nota: `Cambio temporal: queda en vigor hasta registrar su fin (previsto el ${fecha(d.fecha_reversion)}). Exige documentos vigentes y acciones derivadas cerradas.`, bloqueo: eficSinGuardar ? 'Guarde primero la verificación.' : '', botones: [{ texto: 'Confirmar eficacia', accion: simple('cerrar', 'Confirmar la eficacia', `La verificación queda de solo lectura y ${d.codigo} pasa a «Temporal en vigor».`) }] }
      : { titulo: 'Cerrar el cambio', nota: 'Exige eficacia registrada, documentos vigentes y acciones derivadas cerradas.', bloqueo: eficSinGuardar ? 'Guarde primero la verificación.' : '', botones: [{ texto: 'Cerrar el cambio', accion: simple('cerrar', 'Cerrar el cambio', `${d.codigo} queda cerrado.`) }] }),
    temporal_vigente: (puedeAprobar || tienePermiso('cambios', 'crear')) && { titulo: 'Cambio temporal en vigor', nota: `Se cierra al registrar su fin (sección 8). Fin previsto: ${fecha(d.fecha_reversion)}.`, botones: [
      ...(tienePermiso('cambios', 'crear') && !d.cambios_permanentes.length ? [{ texto: 'Volverlo permanente (nueva solicitud)', accion: nuevoPermanente, secundario: true }] : []),
    ] },
    cerrado: puedeAprobar && { titulo: 'Cambio cerrado', nota: 'Solo se reabre con motivo.', botones: [{ texto: 'Reabrir', accion: conMotivo('Reabrir el cambio', 'reabrir', 'Motivo de la reapertura'), secundario: true }] },
  }[d.estado]

  useAbrirDesdeEnlace(abrir)   // enlace directo ?abrir=<id> (búsqueda, Mis tareas, campana)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2"><TituloModulo seccion="Sistema de gestión" titulo="Cambios" descripcion="Solicitudes de cambio con su evaluación de impacto, su implementación y la verificación de su eficacia." /></div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => abrirPdf(api.cambios.seguimientoPdf(filtros()))} className="btn-secondary"><FileText className="h-4 w-4" /> Imprimir seguimiento</button>
          {tienePermiso('cambios', 'crear') && <button onClick={nueva} className="btn-primary"><Plus className="h-4 w-4" /> Nueva solicitud</button>}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input-esynapse w-64 pl-9" placeholder="Buscar código o descripción…" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <select className="input-esynapse w-56" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {(cat ? [['solicitado', 'Solicitado'], ['en_evaluacion', 'En evaluación'], ['en_aprobacion', 'En aprobación'], ['rechazado', 'Rechazado'], ['archivado', 'Archivado'], ['en_planificacion', 'En planificación'], ['en_implementacion', 'En implementación'], ['en_verificacion', 'En verificación'], ['temporal_vigente', 'Temporal en vigor'], ['cerrado', 'Cerrado']] : []).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
        <div className="ml-auto"><Vistas opciones={[['abiertos', 'Abiertos'], ['todos', 'Todos']]} valor={soloAbiertos ? 'abiertos' : 'todos'} onChange={(v) => setSoloAbiertos(v === 'abiertos')} /></div>
      </div>
      {error && !d && !modalForm && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-3 py-3">N° de solicitud</th><th className="px-3 py-3 text-right">Fecha</th><th className="px-3 py-3">Solicitante</th><th className="px-3 py-3">Área</th>
              <th className="px-3 py-3">Descripción</th><th className="px-3 py-3 text-center">Prioridad</th><th className="px-3 py-3">Responsable de la implementación</th>
              <th className="px-3 py-3 text-center">¿Se implementó?</th><th className="px-3 py-3 text-center">¿Fue eficaz?</th><th className="px-3 py-3 text-center">Estado</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id} onClick={() => abrir(c.id)} className="cursor-pointer border-b border-slate-100 last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="whitespace-nowrap px-3 py-3 font-mono text-xs font-medium">{c.codigo}</td>
                <td className="whitespace-nowrap px-3 py-3 text-xs text-right">{fecha(c.fecha_solicitud)}</td>
                <td className="px-3 py-3 text-xs">{c.solicitante_nombre || '—'}</td>
                <td className="px-3 py-3 text-xs">{c.area || '—'}</td>
                <td className="max-w-xs truncate px-3 py-3" title={c.descripcion}>{c.descripcion}</td>
                <td className="px-3 py-3 text-xs text-center">{c.prioridad_display}{c.clasificacion ? ` · ${c.clasificacion === 'mayor' ? 'mayor' : 'menor'}` : ''}</td>
                <td className="px-3 py-3 text-xs">{c.responsable_implementacion_nombre || '—'}</td>
                <td className="px-3 py-3 text-xs text-center">{siNo(c.se_implemento)}</td>
                <td className="px-3 py-3 text-xs text-center">{siNo(c.fue_eficaz)}</td>
                <td className="px-3 py-3 text-center">
                  <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_ESTADO[c.estado]}`}>{c.estado_display}</span>
                  {c.reversion_vencida && <span className="ml-1 rounded bg-red-500/15 px-1.5 py-0.5 text-[11px] font-medium text-red-600" title={`Fin previsto: ${fecha(c.fecha_reversion)}`}>fin vencido</span>}
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={10} className="px-4 py-8 text-slate-400">Sin solicitudes de cambio</td></tr>}
          </tbody>
        </table>
      </div>

      {/* Solicitud: nueva o corrección */}
      <Modal abierto={modalForm} titulo={editandoId ? 'Corregir la solicitud' : 'Nueva solicitud de cambio'} onCerrar={() => setModalForm(false)} ancho="max-w-2xl">
        <form onSubmit={guardarSolicitud} className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">{sel('Proceso solicitante', form.proceso_solicitante, (e) => setForm({ ...form, proceso_solicitante: e.target.value }),
              [['', '— Elige el proceso —'], ...procesos.flatMap((p) => (p.padre ? [] : [[String(p.id), p.nombre], ...procesos.filter((s) => s.padre === p.id).map((s) => [String(s.id), `   ${s.nombre}`])]))], { required: true })}</div>
            <div><label className={lbl}>Fecha de solicitud</label><input type="date" max={hoy()} className={inp} required value={form.fecha_solicitud} onChange={(e) => setForm({ ...form, fecha_solicitud: e.target.value })} /></div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {sel('Prioridad', form.prioridad, (e) => setForm({ ...form, prioridad: e.target.value }), cat?.prioridades || [])}
            {sel('Origen', form.origen, (e) => setForm({ ...form, origen: e.target.value, motivo_origen: '' }), cat?.origenes || [])}
            {sel('Motivo', form.motivo_origen, (e) => setForm({ ...form, motivo_origen: e.target.value }), [['', '— Seleccionar —'], ...motivos.map((m) => [m, m])], { required: true })}
          </div>
          {area('Descripción del cambio', form, setForm, 'descripcion', 3)}
          {area('Justificación del cambio', form, setForm, 'justificacion', 3)}
          {!editandoId && <p className="text-[11px] text-slate-500 dark:text-slate-400">Al registrar se asigna el número de solicitud. Usted figura como solicitante.</p>}
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalForm(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">{editandoId ? 'Guardar corrección' : 'Registrar solicitud'}</button>
          </div>
        </form>
      </Modal>

      {/* Detalle */}
      <Modal abierto={Boolean(d) && !modalForm} titulo={d ? `${d.codigo} — ${d.descripcion.slice(0, 70)}` : ''} onCerrar={() => setD(null)} panel ancho="max-w-5xl">
        {d && (
          <div className="space-y-3 text-sm">
            <BarraPasos pasos={pasos.map(([, nombre]) => nombre)} actual={pasoActual} cerrado={d.estado === 'cerrado'} />

            <div className="flex flex-wrap items-center gap-2">
              <button onClick={() => abrirPdf(api.cambios.pdf(d.id))} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Solicitud (PDF)</button>
              <button onClick={() => abrirPdf(api.cambios.planificacionPdf(d.id))} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Planificación (PDF)</button>
              {d.etapas_abiertas.includes('solicitud') && puedeEditar
                ? <button onClick={corregir} className="btn-secondary !py-1 text-xs"><Pencil className="h-3.5 w-3.5" /> Corregir solicitud</button>
                : <span className="flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Solicitud de solo lectura</span>}
              {d.estado === 'solicitado' && tienePermiso('cambios', 'eliminar') && <button onClick={anular} className="btn-secondary !py-1 text-xs text-red-500"><Trash2 className="h-3.5 w-3.5" /> Anular</button>}
              <span className={`ml-auto rounded px-2 py-0.5 text-[11px] font-medium ${COLOR_ESTADO[d.estado]}`}>{d.estado_display}</span>
            </div>
            {d.reversion_vencida && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600"><AlertTriangle className="mr-1 inline h-3.5 w-3.5" />Cambio temporal: pasó la fecha prevista de fin ({fecha(d.fecha_reversion)}) sin registrarse. Registre su fin o prorróguelo.</p>}
            {error && <p ref={errorRef} className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}

            <Seccion titulo="1. Solicitud de cambio">
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <Dato etiqueta="Solicitante" valor={d.solicitante_nombre} />
                <Dato etiqueta="Proceso solicitante" valor={d.proceso_solicitante_nombre} />
                <Dato etiqueta="Fecha de solicitud" valor={fecha(d.fecha_solicitud)} />
                <Dato etiqueta="Prioridad" valor={d.prioridad_display} />
                <Dato etiqueta="Origen" valor={`${d.origen_display}: ${d.motivo_origen || '—'}`} />
                {d.sac_origen_codigo && <Dato etiqueta="Acción correctiva que lo origina" valor={d.sac_origen_codigo} />}
                {d.cambio_origen_codigo && <Dato etiqueta="Vuelve permanente el cambio temporal" valor={d.cambio_origen_codigo} />}
              </div>
              <Dato etiqueta="Descripción" valor={d.descripcion} />
              <Dato etiqueta="Justificación" valor={d.justificacion} />
            </Seccion>

            {d.estado === 'en_evaluacion' && puedeEditar ? (
              <Seccion titulo="2. Evaluación del cambio (Área SIG)" tono="ambar">
                <div className="grid gap-3 md:grid-cols-3">
                  {area('Factibilidad técnica', evalF, setEvalF, 'factibilidad_tecnica')}
                  {area('Aspectos operativos', evalF, setEvalF, 'aspectos_operativos')}
                  {area('Aspectos financieros', evalF, setEvalF, 'aspectos_financieros')}
                </div>
                <div><label className={lbl}>Procesos afectados</label>
                  {casillas(procesos.filter((p) => p.is_active).map((p) => [p.id, p.padre ? `↳ ${p.nombre}` : p.nombre]), evalF.procesos_afectados, (v) => setEvalF({ ...evalF, procesos_afectados: v }))}</div>
                {area('Alcance (detalle de áreas, equipos o actividades)', evalF, setEvalF, 'alcance')}
                <div><label className={lbl}>Impactos que aplican</label>{casillas(cat?.impactos || [], evalF.impactos, (v) => setEvalF({ ...evalF, impactos: v }))}</div>
                <div className="grid gap-3 md:grid-cols-2">
                  {area('Beneficios del cambio', evalF, setEvalF, 'beneficios')}
                  {area('Riesgos e impactos identificados', evalF, setEvalF, 'riesgos')}
                  {area('Controles establecidos', evalF, setEvalF, 'controles')}
                  {area('Consecuencias de no realizarlo', evalF, setEvalF, 'consecuencias')}
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  {sel('Clasificación', evalF.clasificacion, (e) => setEvalF({ ...evalF, clasificacion: e.target.value }), [['', '— Seleccionar —'], ...(cat?.clasificaciones || [])])}
                  <label className="flex items-center gap-1.5 pt-5"><input type="checkbox" className="accent-esynapse-600" checked={Boolean(evalF.es_tecnico)} onChange={(e) => setEvalF({ ...evalF, es_tecnico: e.target.checked })} /> Cambio técnico (personal, patrones, métodos, software, condiciones ambientales)</label>
                  <label className="flex items-center gap-1.5 pt-5"><input type="checkbox" className="accent-esynapse-600" checked={Boolean(evalF.afecta_clientes)} onChange={(e) => setEvalF({ ...evalF, afecta_clientes: e.target.checked })} /> Afecta requisitos acordados con clientes o actividades acreditadas</label>
                </div>
                {sel('Responsable del equipo evaluador', String(evalF.responsable_evaluador || ''), (e) => setEvalF({ ...evalF, responsable_evaluador: e.target.value ? Number(e.target.value) : '' }), usuariosOpc)}
                <div><label className={lbl}>Equipo evaluador</label>{usuariosMulti(evalF.equipo_evaluador, (v) => setEvalF({ ...evalF, equipo_evaluador: v }))}</div>
                <div className="flex justify-end"><button disabled={!evalSinGuardar} onClick={guardarEval} className="btn-primary !py-1.5 text-xs disabled:opacity-40">Guardar evaluación</button></div>
              </Seccion>
            ) : d.factibilidad_tecnica && (
              <Seccion titulo="2. Evaluación del cambio">
                <div className="grid gap-x-4 md:grid-cols-3">
                  <Dato etiqueta="Factibilidad técnica" valor={d.factibilidad_tecnica} />
                  <Dato etiqueta="Aspectos operativos" valor={d.aspectos_operativos} />
                  <Dato etiqueta="Aspectos financieros" valor={d.aspectos_financieros} />
                </div>
                <Dato etiqueta="Procesos afectados" valor={d.procesos_afectados_nombres.join(', ')} />
                {d.alcance && <Dato etiqueta="Alcance" valor={d.alcance} />}
                <Dato etiqueta="Impactos" valor={(cat?.impactos || []).filter(([k]) => d.impactos.includes(k)).map(([, t]) => t.split(':')[0]).join(', ')} />
                <Dato etiqueta="Beneficios" valor={d.beneficios} />
                <Dato etiqueta="Riesgos e impactos" valor={d.riesgos} />
                <Dato etiqueta="Controles" valor={d.controles} />
                <Dato etiqueta="Consecuencias de no realizarlo" valor={d.consecuencias} />
                <Dato etiqueta="Clasificación" valor={[d.clasificacion_display, d.es_tecnico && 'técnico', d.afecta_clientes && 'afecta a clientes o acreditación'].filter(Boolean).join(' · ')} />
                <Dato etiqueta="Equipo evaluador" valor={[d.responsable_evaluador_nombre && `${d.responsable_evaluador_nombre} (responsable)`, ...d.equipo_evaluador_nombres].filter(Boolean).join(', ')} />
              </Seccion>
            )}

            {(d.actividades.length > 0 || actsEditables) && (
              <Seccion titulo={`3. Plan de ejecución${d.requiere_planificacion ? ' — cambio mayor o técnico' : ''}`} tono={d.estado === 'en_implementacion' ? 'azul' : ''}>
                <table className="tabla-ficha w-full text-xs">
                  <thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="py-1">Actividad</th><th>Responsable</th><th>Recursos</th><th className="text-right">Plazo</th><th>Seguimiento</th><th /></tr></thead>
                  <tbody>
                    {d.actividades.map((a) => (
                      <tr key={a.id} className="border-t border-slate-100 dark:border-slate-800">
                        <td className="py-1.5">{a.actividad}</td><td>{a.responsable_nombre || '—'}</td><td>{a.recursos || '—'}</td><td className="text-right">{a.plazo ? fecha(a.plazo) : '—'}</td>
                        <td>{a.completada ? <span className="text-emerald-600"><Check className="mr-0.5 inline h-3 w-3" />{a.seguimiento} ({fecha(a.fecha_completada)}){a.evidencia_url && <a href={a.evidencia_url} target="_blank" rel="noreferrer" className="ml-1 underline">evidencia</a>}</span> : (a.seguimiento || '—')}</td>
                        <td className="whitespace-nowrap">
                          {actsEditables && <><button title="Corregir" className="p-1" onClick={() => setActF({ id: a.id, actividad: a.actividad, responsable: a.responsable || '', recursos: a.recursos, plazo: a.plazo || '' })}><Pencil className="h-3.5 w-3.5" /></button>
                            <button title="Quitar" className="p-1 text-red-500" onClick={() => quitarActividad(a)}><X className="h-3.5 w-3.5" /></button></>}
                          {d.estado === 'en_implementacion' && puedeEditar && !a.completada && <button className="btn-secondary !py-0.5 text-[11px]" onClick={() => setCompletar({ id: a.id, seguimiento: '', evidencia: null })}>Completar</button>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {actsEditables && !actF && <button className="btn-secondary !py-1 text-xs" onClick={() => setActF({ actividad: '', responsable: '', recursos: '', plazo: '' })}><Plus className="h-3.5 w-3.5" /> Agregar actividad</button>}
                {actF && (
                  <div className="grid gap-2 rounded border border-slate-200 p-2 md:grid-cols-[3fr_2fr_2fr_1fr_auto] dark:border-slate-700">
                    <input className={inp} placeholder="Actividad" value={actF.actividad} onChange={(e) => setActF({ ...actF, actividad: e.target.value })} />
                    <select className={inp} value={String(actF.responsable || '')} onChange={(e) => setActF({ ...actF, responsable: e.target.value ? Number(e.target.value) : '' })}>{usuariosOpc.map(([v, n]) => <option key={v} value={v}>{v ? n : '— Responsable —'}</option>)}</select>
                    <input className={inp} placeholder="Recursos" value={actF.recursos} onChange={(e) => setActF({ ...actF, recursos: e.target.value })} />
                    <input type="date" className={inp} value={actF.plazo || ''} onChange={(e) => setActF({ ...actF, plazo: e.target.value })} />
                    <div className="flex gap-1"><button className="btn-primary !py-1 text-xs" disabled={!actF.actividad.trim()} onClick={guardarActividad}>Guardar</button><button className="btn-secondary !py-1 text-xs" onClick={() => setActF(null)}>Cancelar</button></div>
                  </div>
                )}
                {completar && (
                  <div className="space-y-2 rounded border border-esynapse-600/30 p-2">
                    <CampoAmpliable multilinea placeholder="Qué se hizo (seguimiento)" value={completar.seguimiento} onChange={(v) => setCompletar({ ...completar, seguimiento: v })} />
                    <div className="flex flex-wrap items-center gap-2">
                      <label className="btn-secondary !py-1 cursor-pointer text-xs">Adjuntar evidencia<input type="file" className="hidden" onChange={(e) => setCompletar({ ...completar, evidencia: e.target.files[0] || null })} /></label>
                      {completar.evidencia && <span className="text-[11px]">{completar.evidencia.name}</span>}
                      <button className="btn-primary ml-auto !py-1 text-xs" disabled={!completar.seguimiento.trim()} onClick={completarActividad}>Marcar completada</button>
                      <button className="btn-secondary !py-1 text-xs" onClick={() => setCompletar(null)}>Cancelar</button>
                    </div>
                  </div>
                )}
              </Seccion>
            )}

            {d.resultado && (
              <Seccion titulo="4. Resolución del cambio">
                <div className="grid gap-x-4 md:grid-cols-3">
                  <Dato etiqueta="Resolución" valor={d.resultado === 'aprobado' ? 'Aprobado' : 'Rechazado'} />
                  <Dato etiqueta="Por" valor={d.resuelto_por_nombre} />
                  <Dato etiqueta="Fecha" valor={fechaHora(d.fecha_resolucion)} />
                </div>
                {d.motivo_resolucion && <Dato etiqueta="Comentarios" valor={d.motivo_resolucion} />}
              </Seccion>
            )}
            {d.historial.length > 1 && <p className="text-[11px] text-slate-500">Historial: {d.historial.map((h) => `${fecha(h.fecha)} ${h.accion}${h.motivo ? ` (${h.motivo})` : ''}`).join(' · ')}</p>}

            {d.estado === 'en_planificacion' && puedeEditar ? (
              <Seccion titulo={`5. Planificación del cambio${d.requiere_planificacion ? ' (obligatoria: cambio mayor o técnico)' : ''}`} tono="azul">
                <div className="grid gap-3 md:grid-cols-4">
                  <div><label className={lbl}>Fecha de planificación</label><input type="date" className={inp} value={planF.fecha_planificacion || ''} onChange={(e) => setPlanF({ ...planF, fecha_planificacion: e.target.value })} /></div>
                  {sel('Previsto / no previsto', planF.prevision, (e) => setPlanF({ ...planF, prevision: e.target.value }), [['', '—'], ...(cat?.prevision || [])])}
                  {sel('Temporal / permanente', planF.temporalidad, (e) => setPlanF({ ...planF, temporalidad: e.target.value }), [['', '—'], ...(cat?.temporalidad || [])])}
                  {planF.temporalidad === 'temporal' && <div><label className={lbl}>Fecha prevista de fin</label><input type="date" className={inp} value={planF.fecha_reversion || ''} onChange={(e) => setPlanF({ ...planF, fecha_reversion: e.target.value })} /></div>}
                </div>
                <div><label className={lbl}>Fuente u origen del cambio</label>{casillas(cat?.fuentes || [], planF.fuentes, (v) => setPlanF({ ...planF, fuentes: v }))}
                  <input className={`${inp} mt-1`} placeholder="Otros" value={planF.fuente_otro || ''} onChange={(e) => setPlanF({ ...planF, fuente_otro: e.target.value })} /></div>
                <div className="grid gap-3 md:grid-cols-2">
                  {sel('Responsable del equipo de implementación', String(planF.responsable_implementacion || ''), (e) => setPlanF({ ...planF, responsable_implementacion: e.target.value ? Number(e.target.value) : '' }), usuariosOpc)}
                  <div><label className={lbl}>Plazo de implementación</label><input type="date" className={inp} value={planF.plazo_implementacion || ''} onChange={(e) => setPlanF({ ...planF, plazo_implementacion: e.target.value })} /></div>
                </div>
                <div><label className={lbl}>Equipo de implementación</label>{usuariosMulti(planF.equipo_implementacion, (v) => setPlanF({ ...planF, equipo_implementacion: v }))}</div>
                <div className="flex justify-end"><button disabled={!planSinGuardar} onClick={guardarPlan} className="btn-primary !py-1.5 text-xs disabled:opacity-40">Guardar planificación</button></div>
              </Seccion>
            ) : d.responsable_implementacion && (
              <Seccion titulo="5. Planificación del cambio">
                <div className="grid gap-x-4 md:grid-cols-3">
                  <Dato etiqueta="Fecha" valor={fecha(d.fecha_planificacion)} />
                  <Dato etiqueta="Tipo" valor={[d.prevision_display, d.temporalidad_display].filter(Boolean).join(' · ')} />
                  {d.temporalidad === 'temporal' && <Dato etiqueta="Fin previsto" valor={`${fecha(d.fecha_reversion)}${d.prorrogas.length ? ` (prorrogado ${d.prorrogas.length} vez/veces)` : ''}`} />}
                  <Dato etiqueta="Responsable" valor={d.responsable_implementacion_nombre} />
                  <Dato etiqueta="Plazo" valor={fecha(d.plazo_implementacion)} />
                  <Dato etiqueta="Equipo" valor={d.equipo_implementacion_nombres.join(', ')} />
                </div>
                <Dato etiqueta="Fuente" valor={[...(cat?.fuentes || []).filter(([k]) => d.fuentes.includes(k)).map(([, t]) => t), d.fuente_otro].filter(Boolean).join(', ')} />
              </Seccion>
            )}

            {['en_planificacion', 'en_implementacion', 'en_verificacion', 'temporal_vigente', 'cerrado'].includes(d.estado) && (
              <Seccion titulo="6. Implementación y comunicación">
                <div>
                  <p className="font-semibold">Documentos actualizados</p>
                  {d.estado === 'en_implementacion' && puedeEditar ? (
                    <div className="space-y-1">
                      <select className={inp} value="" onChange={(e) => { const v = Number(e.target.value); if (v && !docsF.includes(v)) setDocsF([...docsF, v]) }}>
                        <option value="">+ Agregar un documento de la lista maestra…</option>
                        {docs.map((x) => <option key={x.id} value={x.id}>{x.codigo} — {x.titulo}</option>)}
                      </select>
                      <div className="flex flex-wrap gap-1">{docsF.map((id) => { const x = docs.find((y) => y.id === id); return <span key={id} className="rounded bg-esynapse-600/10 px-1.5 py-0.5">{x ? `${x.codigo} ${x.titulo}` : id}<button className="ml-1" onClick={() => setDocsF(docsF.filter((y) => y !== id))}><X className="inline h-3 w-3" /></button></span> })}</div>
                      {difiere({ documentos_actualizados: docsF }, ['documentos_actualizados']) && <button className="btn-primary !py-1 text-xs" onClick={guardarDocs}>Guardar documentos</button>}
                    </div>
                  ) : (
                    <p>{d.documentos_actualizados_info.length ? d.documentos_actualizados_info.map((x) => `${x.codigo} ${x.titulo} (vigente: ${x.version_vigente || '—'}${x.version_en_proceso ? `; en curso: ${x.version_en_proceso}` : ''})`).join(' · ') : '—'}</p>
                  )}
                </div>
                <div>
                  <p className="font-semibold">Comunicación del cambio</p>
                  {d.comunicaciones.length === 0 && <p className="text-slate-400">Sin comunicaciones registradas.</p>}
                  {d.comunicaciones.map((c) => <p key={c.id}>{fecha(c.fecha)} · {c.destinatario_display} · {c.medio_display}: {c.resumen}{c.evidencia_url && <a href={c.evidencia_url} target="_blank" rel="noreferrer" className="ml-1 underline">evidencia</a>}</p>)}
                  {comunicacionAbierta && !comF && <button className="btn-secondary mt-1 !py-1 text-xs" onClick={() => setComF({ destinatario: 'personal', medio: 'email', fecha: hoy(), resumen: '', evidencia: null })}><Plus className="h-3.5 w-3.5" /> Registrar comunicación</button>}
                  {comF && (
                    <div className="mt-1 space-y-2 rounded border border-slate-200 p-2 dark:border-slate-700">
                      <div className="grid gap-2 md:grid-cols-3">
                        {sel('A quién', comF.destinatario, (e) => setComF({ ...comF, destinatario: e.target.value }), cat?.destinatarios || [])}
                        {sel('Medio', comF.medio, (e) => setComF({ ...comF, medio: e.target.value }), cat?.medios || [])}
                        <div><label className={lbl}>Fecha</label><input type="date" max={hoy()} className={inp} value={comF.fecha} onChange={(e) => setComF({ ...comF, fecha: e.target.value })} /></div>
                      </div>
                      <CampoAmpliable multilinea placeholder="Qué se comunicó: descripción, impactos, fecha de implementación, controles" value={comF.resumen} onChange={(v) => setComF({ ...comF, resumen: v })} />
                      <div className="flex flex-wrap items-center gap-2">
                        <label className="btn-secondary !py-1 cursor-pointer text-xs">Adjuntar evidencia<input type="file" className="hidden" onChange={(e) => setComF({ ...comF, evidencia: e.target.files[0] || null })} /></label>
                        {comF.evidencia && <span className="text-[11px]">{comF.evidencia.name}</span>}
                        <button className="btn-primary ml-auto !py-1 text-xs" disabled={!comF.resumen.trim()} onClick={registrarComunicacion}>Registrar</button>
                        <button className="btn-secondary !py-1 text-xs" onClick={() => setComF(null)}>Cancelar</button>
                      </div>
                    </div>
                  )}
                </div>
                <div>
                  <p className="font-semibold">Registro fotográfico</p>
                  <div className="flex flex-wrap gap-2">
                    {d.fotos.map((f) => (
                      <a key={f.id} href={f.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 rounded bg-slate-100 px-2 py-1 dark:bg-slate-800"><Image className="h-3.5 w-3.5" />{f.momento_display}{f.descripcion ? `: ${f.descripcion}` : ''}
                        {comunicacionAbierta && <button className="ml-1 text-red-500" onClick={(e) => { e.preventDefault(); accion(() => api.cambios.accion(d.id, 'quitar_foto', { foto_id: f.id })) }}><X className="h-3 w-3" /></button>}
                      </a>
                    ))}
                    {d.fotos.length === 0 && <span className="text-slate-400">Sin fotos.</span>}
                  </div>
                  {comunicacionAbierta && !fotoF && <button className="btn-secondary mt-1 !py-1 text-xs" onClick={() => setFotoF({ momento: 'antes', descripcion: '', archivo: null })}><Plus className="h-3.5 w-3.5" /> Agregar foto</button>}
                  {fotoF && (
                    <div className="mt-1 flex flex-wrap items-end gap-2 rounded border border-slate-200 p-2 dark:border-slate-700">
                      {sel('Momento', fotoF.momento, (e) => setFotoF({ ...fotoF, momento: e.target.value }), cat?.momentos_foto || [])}
                      <input className={`${inp} !w-56`} placeholder="Descripción" value={fotoF.descripcion} onChange={(e) => setFotoF({ ...fotoF, descripcion: e.target.value })} />
                      <label className="btn-secondary !py-1 cursor-pointer text-xs">Elegir foto<input type="file" accept="image/*" className="hidden" onChange={(e) => setFotoF({ ...fotoF, archivo: e.target.files[0] || null })} /></label>
                      {fotoF.archivo && <span className="text-[11px]">{fotoF.archivo.name}</span>}
                      <button className="btn-primary !py-1 text-xs" disabled={!fotoF.archivo} onClick={subirFoto}>Subir</button>
                      <button className="btn-secondary !py-1 text-xs" onClick={() => setFotoF(null)}>Cancelar</button>
                    </div>
                  )}
                </div>
              </Seccion>
            )}

            {d.estado === 'en_verificacion' && puedeEditar ? (
              <Seccion titulo="7. Verificación de la eficacia (Gerente SIG)" tono="violeta">
                <div className="grid gap-3 md:grid-cols-2">
                  {sel('¿Se implementó?', String(eficF.se_implemento ?? ''), (e) => setEficF({ ...eficF, se_implemento: e.target.value === '' ? '' : e.target.value === 'true' }), [['', '—'], ['true', 'Sí'], ['false', 'No']])}
                  {sel('¿Fue eficaz?', String(eficF.fue_eficaz ?? ''), (e) => setEficF({ ...eficF, fue_eficaz: e.target.value === '' ? '' : e.target.value === 'true' }), [['', '—'], ['true', 'Sí'], ['false', 'No']])}
                </div>
                <div><label className={lbl}>Se verificó que</label>{casillas(cat?.criterios_eficacia || [], eficF.criterios_eficacia, (v) => setEficF({ ...eficF, criterios_eficacia: v }))}</div>
                {area('Verificación (cómo se comprobó: verificaciones técnicas, auditoría, seguimiento, comparaciones)', eficF, setEficF, 'verificacion')}
                <div className="grid gap-3 md:grid-cols-3">
                  {sel('Reversión por ineficacia', eficF.reversion || 'ninguna', (e) => setEficF({ ...eficF, reversion: e.target.value }), cat?.reversiones || [])}
                  {eficF.reversion && eficF.reversion !== 'ninguna' ? <div><label className={lbl}>Fecha de la reversión</label><input type="date" className={inp} value={eficF.fecha_reversion_real || ''} onChange={(e) => setEficF({ ...eficF, fecha_reversion_real: e.target.value })} /></div> : <div />}
                  {sel('Acción correctiva derivada', String(eficF.sac_derivada || ''), (e) => setEficF({ ...eficF, sac_derivada: e.target.value ? Number(e.target.value) : '' }), [['', '— Ninguna —'], ...sacs.map((s) => [String(s.id), s.codigo])])}
                </div>
                {eficF.reversion && eficF.reversion !== 'ninguna' && area('Detalle de la reversión', eficF, setEficF, 'detalle_reversion')}
                {d.temporalidad === 'temporal' && <p className="rounded bg-esynapse-600/10 px-2 py-1.5 text-[11px]">Cambio temporal: la reversión de arriba es solo si no fue eficaz. Si se mantiene, al confirmar la eficacia queda «en vigor» y su fin previsto ({fecha(d.fecha_reversion)}) se registra después.</p>}
                <div className="flex justify-end"><button disabled={!eficSinGuardar} onClick={guardarEfic} className="btn-primary !py-1.5 text-xs disabled:opacity-40">Guardar verificación</button></div>
              </Seccion>
            ) : d.fue_eficaz != null && (
              <Seccion titulo="7. Verificación de la eficacia">
                <div className="grid gap-x-4 md:grid-cols-3">
                  <Dato etiqueta="¿Se implementó?" valor={siNo(d.se_implemento)} />
                  <Dato etiqueta="¿Fue eficaz?" valor={siNo(d.fue_eficaz)} />
                  <Dato etiqueta="Reversión por ineficacia" valor={d.reversion_display} />
                </div>
                <Dato etiqueta="Verificación" valor={d.verificacion} />
                {d.detalle_reversion && <Dato etiqueta="Detalle de la reversión" valor={`${d.detalle_reversion} (${fecha(d.fecha_reversion_real)})`} />}
                {d.sac_derivada_codigo && <Dato etiqueta="Acción correctiva derivada" valor={d.sac_derivada_codigo} />}
              </Seccion>
            )}

            {d.temporalidad === 'temporal' && [...ETAPAS_PRORROGA, 'cerrado'].includes(d.estado) && (
              <Seccion titulo={d.estado === 'temporal_vigente' ? '8. Cambio temporal en vigor' : '8. Cambio temporal'} tono={d.estado === 'temporal_vigente' ? 'azul' : ''}>
                <div className="grid gap-x-4 md:grid-cols-3">
                  <Dato etiqueta="Fin previsto" valor={fecha(d.fecha_reversion)} />
                  {d.fin_temporal_fecha && <Dato etiqueta="Fin registrado" valor={`${fecha(d.fin_temporal_fecha)} · ${d.fin_temporal_por_nombre || ''}`} />}
                </div>
                {d.fin_temporal_detalle && <p><strong className="text-slate-700 dark:text-slate-200">Qué se restituyó:</strong> {d.fin_temporal_detalle}{d.fin_temporal_evidencia_url && <a href={d.fin_temporal_evidencia_url} target="_blank" rel="noreferrer" className="ml-1 underline">evidencia</a>}</p>}
                {d.prorrogas.length > 0 && <div><p className="font-semibold">Prórrogas</p>{d.prorrogas.map((x, i) => <p key={i}>{fecha(x.fecha)} · {x.usuario}{x.sigla ? ` (${x.sigla})` : ''}: del {x.fecha_anterior} al {x.fecha_nueva} — {x.motivo}</p>)}</div>}
                {d.cambios_permanentes.length > 0 && <Dato etiqueta="Solicitud para volverlo permanente" valor={d.cambios_permanentes.map((x) => `${x.codigo} (${x.estado_display})`).join(', ')} />}
                {ETAPAS_PRORROGA.includes(d.estado) && puedeAprobar && !prorF && <button className="btn-secondary !py-1 text-xs" onClick={() => setProrF({ fecha_nueva: '', motivo: '' })}>Prorrogar el fin previsto</button>}
                {prorF && (
                  <div className="grid gap-2 rounded border border-slate-200 p-2 md:grid-cols-[1fr_3fr_auto] dark:border-slate-700">
                    <div><label className={lbl}>Nueva fecha prevista de fin</label><input type="date" min={hoy()} className={inp} value={prorF.fecha_nueva} onChange={(e) => setProrF({ ...prorF, fecha_nueva: e.target.value })} /></div>
                    <div><label className={lbl}>Motivo de la prórroga</label><CampoAmpliable multilinea value={prorF.motivo} onChange={(v) => setProrF({ ...prorF, motivo: v })} /></div>
                    <div className="flex items-end gap-1"><button className="btn-primary !py-1 text-xs" disabled={!prorF.fecha_nueva || !prorF.motivo.trim()} onClick={prorrogar}>Firmar prórroga</button><button className="btn-secondary !py-1 text-xs" onClick={() => setProrF(null)}>Cancelar</button></div>
                  </div>
                )}
                {d.estado === 'temporal_vigente' && puedeEditar && !finF && <button className="btn-primary !py-1 text-xs" onClick={() => setFinF({ fecha: hoy(), detalle: '', evidencia: null })}>Registrar el fin del cambio temporal</button>}
                {finF && (
                  <div className="space-y-2 rounded border border-esynapse-600/30 p-2">
                    <div className="grid gap-2 md:grid-cols-[1fr_3fr]">
                      <div><label className={lbl}>Fecha en que terminó</label><input type="date" max={hoy()} className={inp} value={finF.fecha} onChange={(e) => setFinF({ ...finF, fecha: e.target.value })} /></div>
                      <div><label className={lbl}>Qué se restituyó</label><CampoAmpliable multilinea value={finF.detalle} onChange={(v) => setFinF({ ...finF, detalle: v })} /></div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <label className="btn-secondary !py-1 cursor-pointer text-xs">Adjuntar evidencia<input type="file" className="hidden" onChange={(e) => setFinF({ ...finF, evidencia: e.target.files[0] || null })} /></label>
                      {finF.evidencia && <span className="text-[11px]">{finF.evidencia.name}</span>}
                      <button className="btn-primary ml-auto !py-1 text-xs" disabled={!finF.fecha || !finF.detalle.trim()} onClick={registrarFin}>Registrar fin y cerrar el cambio</button>
                      <button className="btn-secondary !py-1 text-xs" onClick={() => setFinF(null)}>Cancelar</button>
                    </div>
                  </div>
                )}
              </Seccion>
            )}

            {d.estado === 'cerrado' && (
              <Seccion titulo={d.temporalidad === 'temporal' ? '9. Cierre del cambio' : '8. Cierre del cambio'}>
                <div className="grid gap-x-4 md:grid-cols-2"><Dato etiqueta="Cerrado por" valor={d.cerrado_por_nombre} /><Dato etiqueta="Fecha" valor={fechaHora(d.fecha_cierre)} /></div>
              </Seccion>
            )}
            {d.reaperturas.length > 0 && <p className="text-[11px] text-slate-500"><RotateCcw className="mr-1 inline h-3 w-3" />Reaperturas: {d.reaperturas.map((r) => `${fecha(r.fecha)} ${r.usuario}: ${r.motivo}${r.fin_temporal ? ` (fin temporal anulado: ${r.fin_temporal.fecha})` : ''}`).join(' · ')}</p>}

            {barra && <BarraEtapa titulo={barra.titulo} nota={barra.nota} aviso={barra.aviso} bloqueo={barra.bloqueo} botones={barra.botones} />}
          </div>
        )}
      </Modal>
    </div>
  )
}
