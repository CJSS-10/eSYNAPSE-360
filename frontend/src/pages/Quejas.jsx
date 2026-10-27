import { useCallback, useEffect, useState } from 'react'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import { AlertTriangle, CheckCircle2, FileText, Lock, MessageSquareWarning, Paperclip, Pencil, Plus, RotateCcw, Search, Trash2, XCircle } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import BarraPasos from '../components/BarraPasos.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import SelectorProceso from '../components/SelectorProceso.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora } from '../lib/fecha.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import { Vistas } from '../components/NavModulo.jsx'
import { useAbrirDesdeEnlace } from '../lib/enlaces.js'

// Colores de estado (regla 10): gris inicial · ámbar evaluación · azul tratamiento · violeta cierre · verde cerrada.
const COLOR_ESTADO = {
  recibida: 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
  en_evaluacion: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  en_tratamiento: 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  en_cierre: 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
  cerrada: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
}
const COLOR_PLAZO = {
  cumplido: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  cumplido_tarde: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  a_tiempo: 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
  por_vencer: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  vencido: 'bg-red-500/15 text-red-600 dark:text-red-400',
  no_registrado: 'bg-red-500/15 text-red-600 dark:text-red-400',
}
const TEXTO_PLAZO = { cumplido: 'cumplido', cumplido_tarde: 'cumplido fuera de plazo', a_tiempo: 'a tiempo', por_vencer: 'por vencer', vencido: 'vencido', no_registrado: 'no registrado' }
const PASOS = [['recibida', 'Recepción y validación'], ['en_evaluacion', 'Evaluación y decisión'], ['en_tratamiento', 'Tratamiento'], ['en_cierre', 'Cierre'], ['cerrada', 'Cerrada']]

const ahoraLocal = (iso) => {
  const d = iso ? new Date(iso) : new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}
const FORM_VACIO = {
  fecha_recepcion: '', recibido_por: '', tipo_reclamante: 'cliente', empresa: '', contacto: '', contacto_email: '',
  contacto_telefono: '', orden_trabajo: '', medio_recepcion: 'email', medio_otro: '', origen: 'tecnica', motivo: '',
  desde_encuesta: false, descripcion: '',
}
const CAMPOS_REGISTRO = Object.keys(FORM_VACIO)
const CAMPOS_EVAL = ['responsables', 'involucrados', 'fecha_evaluacion', 'evaluacion', 'investigacion', 'dentro_alcance',
  'plazo_ampliado', 'motivo_ampliacion', 'fecha_compromiso', 'cliente_solicita_informe']
const CAMPOS_TRAT = ['acciones', 'responsable_acciones', 'requiere_tnc', 'certificado_original', 'certificado_nuevo', 'seguimiento', 'fecha_seguimiento']

function Seccion({ titulo, tono, children }) {
  return (
    <div className={`rounded-lg border p-3 text-xs ${tono === 'verde' ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-slate-200 dark:border-slate-800'}`}>
      <p className="mb-1 text-xs font-semibold text-slate-500 dark:text-slate-400">{titulo}</p>
      <div className="text-slate-600 dark:text-slate-300">{children}</div>
    </div>
  )
}
function Dato({ etiqueta, valor }) {
  return <p><strong className="text-slate-700 dark:text-slate-200">{etiqueta}:</strong> {valor || '—'}</p>
}
const siNo = (v) => (v == null ? '' : v ? 'Sí' : 'No')

export default function Quejas() {
  const { tienePermiso, usuario } = useAuth()
  const confirmar = useConfirm()
  const [items, setItems] = useState([])
  const [cat, setCat] = useState(null)
  const [usuarios, setUsuarios] = useState([])
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('')
  const [soloAbiertas, setSoloAbiertas] = useState(false)
  const [modalForm, setModalForm] = useState(false)
  const [editandoId, setEditandoId] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [detalle, setDetalle] = useState(null)
  const [error, setError] = useState('')
  // Formularios por etapa
  const [valForm, setValForm] = useState({ relacionada: '', motivo: '' })
  const [evalForm, setEvalForm] = useState({})
  const [decForm, setDecForm] = useState({ procedente: '', fundamento: '' })
  const [tratForm, setTratForm] = useState({})
  const [ncForm, setNcForm] = useState({ tipo_nc: 'nc_menor', proceso: '', requisito: '' })
  const [cierreForm, setCierreForm] = useState({})
  const [comForm, setComForm] = useState(null)
  const [adjunto, setAdjunto] = useState({ archivo: null, descripcion: '' })

  const puedeEditar = tienePermiso('quejas', 'editar')
  const puedeAprobar = tienePermiso('quejas', 'aprobar')

  const filtros = useCallback(() => {
    const p = new URLSearchParams()
    if (buscar) p.set('buscar', buscar)
    if (estado) p.set('estado', estado)
    if (soloAbiertas) p.set('abiertas', '1')
    return `?${p}`
  }, [buscar, estado, soloAbiertas])
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const d = await ultima(api.quejas.listar(filtros()))
    setItems(d.results ?? d)
  }, [filtros])
  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
    api.quejas.catalogos().then(setCat).catch(() => {})
    api.usuarios.listar().then((d) => setUsuarios(d.results ?? d)).catch(() => {})
  }, [])

  const nombreUsuario = (id) => usuarios.find((u) => u.id === Number(id))?.nombre_completo || ''
  const abrirPdf = async (promesa) => {
    setError('')
    try {
      const url = URL.createObjectURL(await promesa)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  const cargarFormularios = (d) => {
    setValForm({ relacionada: '', motivo: '' })
    setEvalForm({
      responsables: d.responsables || [], involucrados: d.involucrados || [], fecha_evaluacion: d.fecha_evaluacion || '',
      evaluacion: d.evaluacion || '', investigacion: d.investigacion || '', dentro_alcance: d.dentro_alcance == null ? '' : String(d.dentro_alcance),
      plazo_ampliado: Boolean(d.plazo_ampliado), motivo_ampliacion: d.motivo_ampliacion || '', fecha_compromiso: d.fecha_compromiso || '',
      cliente_solicita_informe: Boolean(d.cliente_solicita_informe),
    })
    setDecForm({ procedente: '', fundamento: '' })
    setTratForm({
      acciones: d.acciones || '', responsable_acciones: d.responsable_acciones || '', requiere_tnc: Boolean(d.requiere_tnc),
      certificado_original: d.certificado_original || '', certificado_nuevo: d.certificado_nuevo || '',
      seguimiento: d.seguimiento || '', fecha_seguimiento: d.fecha_seguimiento || '',
    })
    setCierreForm({ comunicacion_cliente: d.comunicacion_cliente || '', medio_cierre: d.medio_cierre || 'email',
      conformidad_cliente: d.conformidad_cliente || '', notificado_por: usuario?.id || '' })
    setComForm(null)
    setAdjunto({ archivo: null, descripcion: '' })
  }
  const abrirDetalle = async (id) => {
    setError('')
    const d = await api.quejas.detalle(id)
    setDetalle(d)
    cargarFormularios(d)
  }
  const refrescar = async () => {
    await cargar()
    if (!detalle) return
    const d = await api.quejas.detalle(detalle.id)
    if (d.estado !== detalle.estado) cargarFormularios(d)
    setDetalle(d)
  }
  const accion = async (fn) => {
    setError('')
    try { await fn(); await refrescar() } catch (e) { setError(e.message) }
  }

  // --- Registro (nueva / corregir) ---
  const nueva = () => { setForm({ ...FORM_VACIO, fecha_recepcion: ahoraLocal(), recibido_por: usuario?.id || '' }); setEditandoId(null); setError(''); setModalForm(true) }
  const corregirRegistro = () => {
    setForm({ ...FORM_VACIO, ...Object.fromEntries(CAMPOS_REGISTRO.map((c) => [c, detalle[c] ?? ''])), fecha_recepcion: ahoraLocal(detalle.fecha_recepcion) })
    setEditandoId(detalle.id); setError(''); setModalForm(true)
  }
  const guardarRegistro = async (e) => {
    e.preventDefault()
    setError('')
    const datos = { ...form, fecha_recepcion: new Date(form.fecha_recepcion).toISOString(), recibido_por: form.recibido_por || null }
    try {
      if (editandoId) { await api.quejas.editar(editandoId, datos); setModalForm(false); await refrescar() }
      else { const q = await api.quejas.crear(datos); setModalForm(false); await cargar(); await abrirDetalle(q.id) }
    } catch (e2) { setError(e2.message) }
  }

  // Formularios de etapa con cambios sin guardar
  const difiere = (f, campos) => detalle && campos.some((c) => {
    const a = f[c]; const b = detalle[c]
    if (Array.isArray(a)) return JSON.stringify([...a].map(Number).sort()) !== JSON.stringify([...(b || [])].map(Number).sort())
    if (typeof a === 'boolean') return a !== Boolean(b)
    return String(a ?? '') !== String(b == null ? '' : b)
  })
  const evalSinGuardar = detalle?.estado === 'en_evaluacion' && difiere(evalForm, CAMPOS_EVAL)
  const tratSinGuardar = detalle?.estado === 'en_tratamiento' && difiere(tratForm, CAMPOS_TRAT)
  const guardarEval = () => accion(() => api.quejas.editar(detalle.id, {
    ...evalForm, dentro_alcance: evalForm.dentro_alcance === '' ? null : evalForm.dentro_alcance === 'true',
    fecha_evaluacion: evalForm.fecha_evaluacion || null, fecha_compromiso: evalForm.fecha_compromiso || null,
  }))
  const guardarTrat = () => accion(() => api.quejas.editar(detalle.id, {
    ...tratForm, responsable_acciones: tratForm.responsable_acciones || null, fecha_seguimiento: tratForm.fecha_seguimiento || null,
  }))

  const pasoActual = (d) => PASOS.findIndex(([e]) => e === d.estado)
  const toggle = (lista, id) => (lista.map(Number).includes(Number(id)) ? lista.filter((x) => Number(x) !== Number(id)) : [...lista, Number(id)])
  const inp = 'input-esynapse'
  const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
  const sel = (etiqueta, valor, onChange, opciones, props = {}) => (
    <div>
      <label className={lbl}>{etiqueta}</label>
      <select className={inp} value={valor} onChange={onChange} {...props}>
        {opciones.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
      </select>
    </div>
  )
  const usuariosOpc = (vacio) => [['', vacio], ...usuarios.map((u) => [String(u.id), u.nombre_completo])]
  const motivos = (cat?.motivos || {})[form.origen] || []

  const reabrir = async () => {
    const motivo = await confirmar({ titulo: 'Reabrir queja', textoConfirmar: 'Reabrir',
      mensaje: 'La queja vuelve a la etapa que corresponde a su resultado. El cierre anterior queda en el historial.',
      entrada: { etiqueta: 'Motivo', placeholder: 'p. ej. el cliente no quedó conforme', obligatorio: true, multilinea: true } })
    if (motivo === null || motivo === undefined) return
    await accion(() => api.quejas.reabrir(detalle.id, motivo))
  }
  const anular = async () => {
    if (!await confirmar({ titulo: 'Anular queja', textoConfirmar: 'Anular', peligro: true,
      mensaje: `¿Anular ${detalle.codigo}? Solo para una queja registrada por error; queda en el sistema como anulada.` })) return
    try { await api.quejas.anular(detalle.id); setDetalle(null); await cargar() } catch (e) { setError(e.message) }
  }
  const cerrarQueja = async () => {
    if (!await confirmar({ titulo: 'Cerrar queja', textoConfirmar: 'Cerrar',
      mensaje: `Se registra la comunicación del resultado al cliente y la queja ${detalle.codigo} queda cerrada.` })) return
    await accion(() => api.quejas.cerrar(detalle.id, { ...cierreForm, notificado_por: cierreForm.notificado_por || null }))
  }
  const registrarComunicacion = () => accion(async () => {
    const fd = new FormData()
    fd.append('tipo', comForm.tipo); fd.append('medio', comForm.medio); fd.append('resumen', comForm.resumen)
    if (comForm.fecha) fd.append('fecha', new Date(comForm.fecha).toISOString())
    if (comForm.evidencia) fd.append('evidencia', comForm.evidencia)
    await api.quejas.comunicar(detalle.id, fd)
    setComForm(null)
  })
  const subirAdjunto = () => accion(async () => {
    const fd = new FormData()
    fd.append('archivo', adjunto.archivo); fd.append('descripcion', adjunto.descripcion)
    await api.quejas.adjuntar(detalle.id, fd)
    setAdjunto({ archivo: null, descripcion: '' })
  })

  const d = detalle
  // Acción que cierra la etapa en curso, con lo que falta para habilitarla.
  const sinAcuse = d && !(d.comunicaciones || []).some((c) => c.tipo === 'acuse')
  const etapaFinal = !d || !puedeEditar ? null : {
    recibida: {
      titulo: 'Cerrar la etapa de recepción y validación',
      boton: 'Registrar validación',
      aviso: sinAcuse ? 'Aún no se registra el acuse de recibo con el código (plazo de 24 horas).' : '',
      bloqueo: !valForm.relacionada ? 'Indique en «2. Validación» si la queja está relacionada.'
        : (valForm.relacionada === 'false' && !valForm.motivo.trim()) ? 'Indique por qué no está relacionada.' : '',
      accion: () => accion(() => api.quejas.validar(d.id, { relacionada: valForm.relacionada === 'true', motivo: valForm.motivo })),
    },
    en_evaluacion: puedeAprobar ? {
      titulo: 'Cerrar la etapa de evaluación con la decisión',
      boton: 'Registrar decisión',
      bloqueo: evalSinGuardar ? 'Guarde primero la evaluación.'
        : !decForm.procedente ? 'Indique en «4. Decisión» si la queja es procedente.'
          : !decForm.fundamento.trim() ? 'Escriba el fundamento de la decisión.' : '',
      accion: () => accion(() => api.quejas.decidir(d.id, { procedente: decForm.procedente === 'true', fundamento: decForm.fundamento })),
    } : null,
    en_tratamiento: {
      titulo: 'Cerrar la etapa de tratamiento',
      boton: 'Tratamiento concluido → Cierre',
      bloqueo: tratSinGuardar ? 'Guarde primero el tratamiento.' : '',
      accion: () => accion(() => api.quejas.pasarACierre(d.id)),
    },
    en_cierre: {
      titulo: 'Cerrar la queja',
      boton: 'Registrar comunicación y cerrar',
      bloqueo: !cierreForm.comunicacion_cliente?.trim() ? 'Escriba en «6. Cierre» lo comunicado al cliente.'
        : (d.resultado === 'procedente' && !cierreForm.conformidad_cliente) ? 'Indique la conformidad del cliente.' : '',
      accion: cerrarQueja,
    },
  }[d.estado] || null
  useAbrirDesdeEnlace(abrirDetalle)   // enlace directo ?abrir=<id> (búsqueda, Mis tareas, campana)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <TituloModulo seccion="Sistema de gestión" titulo="Quejas" descripcion="Quejas de clientes y partes interesadas, desde la recepción hasta la respuesta y el cierre." />
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => abrirPdf(api.quejas.seguimientoPdf(filtros()))} className="btn-secondary" title="Registro de seguimiento de quejas (con los filtros aplicados)">
            <FileText className="h-4 w-4" /> Imprimir seguimiento
          </button>
          {tienePermiso('quejas', 'crear') && <button onClick={nueva} className="btn-primary"><Plus className="h-4 w-4" /> Nueva queja</button>}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input-esynapse w-64 pl-9" placeholder="Buscar código, cliente, OT…" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <select className="input-esynapse w-52" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {PASOS.map(([v, n]) => <option key={v} value={v}>{v === 'recibida' ? 'Recibida' : v === 'en_evaluacion' ? 'En evaluación' : n === 'Cerrada' ? 'Cerrada' : `En ${n.toLowerCase()}`}</option>)}
        </select>
        <div className="ml-auto"><Vistas opciones={[['abiertas', 'Abiertas'], ['todas', 'Todas']]} valor={soloAbiertas ? 'abiertas' : 'todas'} onChange={(v) => setSoloAbiertas(v === 'abiertas')} /></div>
      </div>

      {/* Registro de seguimiento de quejas */}
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-3 py-3">N° de queja</th><th className="px-3 py-3 text-right">Fecha de recepción</th><th className="px-3 py-3">N° OT</th>
              <th className="px-3 py-3">Cliente</th><th className="px-3 py-3">Detalle de la queja</th><th className="px-3 py-3">Presentado por</th>
              <th className="px-3 py-3">Recibido por</th><th className="px-3 py-3 text-center">Análisis de aceptación</th><th className="px-3 py-3 text-center">¿Alcance acreditado?</th>
              <th className="px-3 py-3 text-center">Estado</th><th className="px-3 py-3 text-center">Plazos</th>
            </tr>
          </thead>
          <tbody>
            {items.map((q) => (
              <tr key={q.id} onClick={() => abrirDetalle(q.id)} className="cursor-pointer border-b border-slate-100 transition last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="whitespace-nowrap px-3 py-3 font-mono text-xs font-medium">{q.codigo}</td>
                <td className="whitespace-nowrap px-3 py-3 text-xs text-right">{fecha(q.fecha_recepcion)}</td>
                <td className="whitespace-nowrap px-3 py-3 text-xs">{q.orden_trabajo || '—'}</td>
                <td className="min-w-[8rem] px-3 py-3">{q.empresa}</td>
                <td className="max-w-[15rem] truncate px-3 py-3" title={q.descripcion}>{q.descripcion}</td>
                <td className="px-3 py-3 text-xs">{q.contacto || '—'}</td>
                <td className="px-3 py-3 text-xs">{q.recibido_por_nombre || '—'}</td>
                <td className="px-3 py-3 text-xs text-center">{q.resultado_display || (q.estado === 'recibida' ? 'Por validar' : 'En evaluación')}</td>
                <td className="px-3 py-3 text-xs text-center">{siNo(q.dentro_alcance) || '—'}</td>
                <td className="px-3 py-3 text-center"><span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_ESTADO[q.estado]}`}>{q.estado_display}</span></td>
                <td className="px-3 py-3 text-xs text-center">
                  {q.alerta ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_PLAZO[q.alerta.estado]}`} title={q.alerta.nombre}>{TEXTO_PLAZO[q.alerta.estado]}</span> : '—'}
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={11} className="px-4 py-8 text-center text-slate-400">Sin quejas</td></tr>}
          </tbody>
        </table>
      </div>

      {/* Registro / corrección del registro */}
      <Modal abierto={modalForm} titulo={editandoId ? 'Corregir registro de la queja' : 'Nueva queja'} onCerrar={() => setModalForm(false)} ancho="max-w-2xl">
        <form onSubmit={guardarRegistro} className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div><label className={lbl}>Fecha y hora de recepción</label>
              <input type="datetime-local" required className={inp} max={ahoraLocal()} value={form.fecha_recepcion} onChange={(e) => setForm({ ...form, fecha_recepcion: e.target.value })} /></div>
            {sel('Recibido por', String(form.recibido_por || ''), (e) => setForm({ ...form, recibido_por: e.target.value }), usuariosOpc('— Seleccionar —'))}
            {sel('Tipo de reclamante', form.tipo_reclamante, (e) => setForm({ ...form, tipo_reclamante: e.target.value }), cat?.tipos_reclamante || [])}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={lbl}>Nombre de la empresa</label><input required className={inp} value={form.empresa} onChange={(e) => setForm({ ...form, empresa: e.target.value })} /></div>
            <div><label className={lbl}>Representante o persona de contacto</label><input className={inp} value={form.contacto} onChange={(e) => setForm({ ...form, contacto: e.target.value })} /></div>
            <div><label className={lbl}>Correo del contacto</label><input type="email" className={inp} value={form.contacto_email} onChange={(e) => setForm({ ...form, contacto_email: e.target.value })} /></div>
            <div><label className={lbl}>Teléfono del contacto</label><input className={inp} value={form.contacto_telefono} onChange={(e) => setForm({ ...form, contacto_telefono: e.target.value })} /></div>
            <div><label className={lbl}>N° de orden de trabajo</label><input className={inp} value={form.orden_trabajo} onChange={(e) => setForm({ ...form, orden_trabajo: e.target.value })} /></div>
            <div className="grid grid-cols-2 gap-2">
              {sel('Medio de recepción', form.medio_recepcion, (e) => setForm({ ...form, medio_recepcion: e.target.value }), cat?.medios_recepcion || [])}
              {form.medio_recepcion === 'otros' && <div><label className={lbl}>Otro medio</label><input required className={inp} value={form.medio_otro} onChange={(e) => setForm({ ...form, medio_otro: e.target.value })} /></div>}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {sel('Origen', form.origen, (e) => setForm({ ...form, origen: e.target.value, motivo: '' }), cat?.origenes || [])}
            <div className="col-span-2">{sel('Motivo de la queja', form.motivo, (e) => setForm({ ...form, motivo: e.target.value }), [['', '— Seleccionar —'], ...motivos.map((m) => [m, m])], { required: true })}</div>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
            <input type="checkbox" className="h-3.5 w-3.5 accent-esynapse-600" checked={form.desde_encuesta} onChange={(e) => setForm({ ...form, desde_encuesta: e.target.checked })} />
            Originada en una encuesta de satisfacción (respuestas «Insatisfecho» o «Muy insatisfecho» repetidas)
          </label>
          <div><label className={lbl}>Descripción de la queja</label>
            <CampoAmpliable multilinea rows={3} required titulo="Descripción de la queja" value={form.descripcion} onChange={(v) => setForm({ ...form, descripcion: v })} /></div>
          {!editandoId && <p className="text-[11px] text-slate-500 dark:text-slate-400">Al registrar se asigna el código RQ. Envíe el acuse de recibo con ese código en un plazo no mayor a 24 horas y regístrelo en «Comunicaciones».</p>}
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalForm(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">{editandoId ? 'Guardar corrección' : 'Registrar queja'}</button>
          </div>
        </form>
      </Modal>

      {/* Detalle */}
      <Modal abierto={Boolean(d) && !modalForm} titulo={d ? `${d.codigo} — ${d.empresa}` : ''} onCerrar={() => setDetalle(null)} panel ancho="max-w-4xl">
        {d && (
          <div className="space-y-3 text-sm">
            <BarraPasos pasos={PASOS.map(([, nombre]) => nombre)} actual={pasoActual(d)} cerrado={d.estado === 'cerrada'} />

            <div className="flex flex-wrap items-center gap-2">
              <button onClick={() => abrirPdf(api.quejas.pdf(d.id))} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Reporte de queja (PDF)</button>
              {(d.etapas_abiertas || []).includes('registro') && puedeEditar
                ? <button onClick={corregirRegistro} className="btn-secondary !py-1 text-xs"><Pencil className="h-3.5 w-3.5" /> Corregir registro</button>
                : <span className="flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Registro de solo lectura (etapa cerrada)</span>}
              {d.estado === 'recibida' && tienePermiso('quejas', 'eliminar') && <button onClick={anular} className="btn-secondary !py-1 text-xs text-red-500"><Trash2 className="h-3.5 w-3.5" /> Anular</button>}
              {d.estado === 'cerrada' && puedeAprobar && <button onClick={reabrir} className="btn-secondary !py-1 text-xs"><RotateCcw className="h-3.5 w-3.5" /> Reabrir</button>}
              <span className={`ml-auto rounded px-2 py-0.5 text-[11px] font-medium ${COLOR_ESTADO[d.estado]}`}>{d.estado_display}{d.resultado_display ? ` · ${d.resultado_display}` : ''}</span>
            </div>

            {/* Plazos del procedimiento */}
            <div className="flex flex-wrap gap-2">
              {(d.plazos || []).map((p) => (
                <span key={p.clave} className={`rounded px-2 py-1 text-[11px] font-medium ${COLOR_PLAZO[p.estado]}`} title={`Límite: ${fechaHora(p.limite)}${p.cumplido ? ` · cumplido: ${fechaHora(p.cumplido)}` : ''}`}>
                  {['vencido', 'no_registrado'].includes(p.estado) && <AlertTriangle className="mr-1 inline h-3 w-3" />}{p.nombre}: {TEXTO_PLAZO[p.estado]}
                </span>
              ))}
            </div>

            {/* 1. Recepción y registro */}
            <Seccion titulo="1. Recepción y registro">
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <Dato etiqueta="Fecha de recepción" valor={fechaHora(d.fecha_recepcion)} />
                <Dato etiqueta="Recibido por" valor={d.recibido_por_nombre} />
                <Dato etiqueta="Registrado por" valor={d.registrado_por} />
                <Dato etiqueta="Tipo de reclamante" valor={d.tipo_reclamante_display} />
                <Dato etiqueta="Empresa" valor={d.empresa} />
                <Dato etiqueta="Contacto" valor={[d.contacto, d.contacto_email, d.contacto_telefono].filter(Boolean).join(' · ')} />
                <Dato etiqueta="N° de OT" valor={d.orden_trabajo} />
                <Dato etiqueta="Medio de recepción" valor={`${d.medio_recepcion_display}${d.medio_otro ? `: ${d.medio_otro}` : ''}`} />
                <Dato etiqueta="Origen y motivo" valor={`${d.origen_display}: ${d.motivo}${d.desde_encuesta ? ' (encuesta de satisfacción)' : ''}`} />
              </div>
              <p className="mt-1 whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Descripción:</strong> {d.descripcion}</p>
            </Seccion>

            {/* 2. Validación */}
            {d.estado === 'recibida' && puedeEditar ? (
              <div className="space-y-2 rounded-lg border border-slate-400/40 bg-slate-500/5 p-3">
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">2. Validación — ¿la queja está relacionada con las actividades de la empresa?</p>
                <div className="flex gap-4 text-xs">
                  {[['true', 'Sí, está relacionada'], ['false', 'No está relacionada']].map(([v, t]) => (
                    <label key={v} className="flex cursor-pointer items-center gap-1.5"><input type="radio" name="relacionada" className="accent-esynapse-600" checked={valForm.relacionada === v} onChange={() => setValForm({ ...valForm, relacionada: v })} /> {t}</label>
                  ))}
                </div>
                {valForm.relacionada === 'false' && <CampoAmpliable multilinea placeholder="Por qué no está relacionada (se comunicará al cliente)" value={valForm.motivo} onChange={(v) => setValForm({ ...valForm, motivo: v })} />}
              </div>
            ) : d.fecha_validacion && (
              <Seccion titulo="2. Validación">
                <div className="grid grid-cols-3 gap-x-4">
                  <Dato etiqueta="¿Relacionada con las actividades?" valor={siNo(d.relacionada)} />
                  <Dato etiqueta="Fecha" valor={fechaHora(d.fecha_validacion)} />
                  <Dato etiqueta="Validado por" valor={d.validado_por_nombre} />
                </div>
                {d.motivo_validacion && <p className="mt-1">{d.motivo_validacion}</p>}
              </Seccion>
            )}

            {/* 3. Evaluación e investigación + 4. Decisión */}
            {d.estado === 'en_evaluacion' && puedeEditar ? (
              <div className="space-y-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">3. Evaluación e investigación</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">El Gerente Técnico evalúa las quejas técnicas y el Gerente SIG las demás, con el personal involucrado. Revise los registros del servicio y casos similares.</p>
                <div className="grid grid-cols-2 gap-3">
                  {[['responsables', 'Responsables de la evaluación'], ['involucrados', 'Personal involucrado en el origen (no notificará el cierre)']].map(([campo, titulo]) => (
                    <div key={campo}>
                      <label className={lbl}>{titulo}</label>
                      <div className="max-h-28 space-y-0.5 overflow-y-auto rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-700">
                        {usuarios.map((u) => (
                          <label key={u.id} className="flex cursor-pointer items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" checked={(evalForm[campo] || []).map(Number).includes(u.id)} onChange={() => setEvalForm({ ...evalForm, [campo]: toggle(evalForm[campo] || [], u.id) })} /> {u.nombre_completo}</label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div><label className={lbl}>Fecha de evaluación</label><input type="date" className={inp} value={evalForm.fecha_evaluacion} onChange={(e) => setEvalForm({ ...evalForm, fecha_evaluacion: e.target.value })} /></div>
                  {sel('¿Dentro del alcance acreditado?', evalForm.dentro_alcance, (e) => setEvalForm({ ...evalForm, dentro_alcance: e.target.value }), [['', '—'], ['true', 'Sí'], ['false', 'No']])}
                  <label className="mt-6 flex items-center gap-2 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={evalForm.cliente_solicita_informe} onChange={(e) => setEvalForm({ ...evalForm, cliente_solicita_informe: e.target.checked })} /> El cliente solicita informe de resultados</label>
                </div>
                <CampoAmpliable multilinea titulo="Evaluación de la queja" placeholder="Evaluación de la queja" value={evalForm.evaluacion} onChange={(v) => setEvalForm({ ...evalForm, evaluacion: v })} />
                <CampoAmpliable multilinea titulo="Investigación / análisis de causas" placeholder="Investigación / análisis de causas" value={evalForm.investigacion} onChange={(v) => setEvalForm({ ...evalForm, investigacion: v })} />
                <label className="flex items-center gap-2 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={evalForm.plazo_ampliado} onChange={(e) => setEvalForm({ ...evalForm, plazo_ampliado: e.target.checked })} /> La investigación requiere ampliar el plazo (se notifica al cliente)</label>
                {evalForm.plazo_ampliado && (
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2"><CampoAmpliable placeholder="Motivo de la ampliación" value={evalForm.motivo_ampliacion} onChange={(v) => setEvalForm({ ...evalForm, motivo_ampliacion: v })} /></div>
                    <input type="date" className={inp} title="Nueva fecha comprometida" value={evalForm.fecha_compromiso} onChange={(e) => setEvalForm({ ...evalForm, fecha_compromiso: e.target.value })} />
                  </div>
                )}
                <div className="flex items-center gap-3">
                  <button onClick={guardarEval} className={`${evalSinGuardar ? 'btn-primary' : 'btn-secondary'} !py-1.5 text-xs`}>Guardar evaluación</button>
                  {evalSinGuardar && <span className="text-[11px] text-amber-600 dark:text-amber-400">Cambios sin guardar</span>}
                </div>
                {puedeAprobar && (
                  <div className="mt-2 space-y-2 border-t border-amber-500/20 pt-2">
                    <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">4. Decisión</p>
                    <div className="flex gap-4 text-xs">
                      {[['true', 'Procedente'], ['false', 'No procedente']].map(([v, t]) => (
                        <label key={v} className="flex cursor-pointer items-center gap-1.5"><input type="radio" name="procedente" className="accent-esynapse-600" checked={decForm.procedente === v} onChange={() => setDecForm({ ...decForm, procedente: v })} /> {t}</label>
                      ))}
                    </div>
                    <CampoAmpliable multilinea placeholder={decForm.procedente === 'false' ? 'Motivos de la no procedencia (se comunicarán al cliente)' : 'Fundamento de la decisión'} value={decForm.fundamento} onChange={(v) => setDecForm({ ...decForm, fundamento: v })} />
                  </div>
                )}
              </div>
            ) : (d.fecha_evaluacion || d.evaluacion) && (
              <Seccion titulo="3. Evaluación e investigación">
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  <Dato etiqueta="Responsables" valor={(d.responsables_nombres || []).join(', ')} />
                  <Dato etiqueta="Fecha de evaluación" valor={fecha(d.fecha_evaluacion)} />
                  <Dato etiqueta="Personal involucrado" valor={(d.involucrados_nombres || []).join(', ')} />
                  <Dato etiqueta="¿Dentro del alcance acreditado?" valor={siNo(d.dentro_alcance)} />
                </div>
                <p className="mt-1 whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Evaluación:</strong> {d.evaluacion}</p>
                <p className="whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Investigación / análisis de causas:</strong> {d.investigacion}</p>
                {d.plazo_ampliado && <p><strong className="text-slate-700 dark:text-slate-200">Plazo ampliado al {fecha(d.fecha_compromiso)}:</strong> {d.motivo_ampliacion}</p>}
                {d.fecha_decision && <p className="mt-1"><strong className="text-slate-700 dark:text-slate-200">4. Decisión ({fecha(d.fecha_decision)}, {d.decidido_por_nombre}): {d.resultado_display}.</strong> {d.fundamento_decision}</p>}
              </Seccion>
            )}

            {/* 5. Tratamiento */}
            {d.estado === 'en_tratamiento' && puedeEditar ? (
              <div className="space-y-2 rounded-lg border border-esynapse-600/30 bg-esynapse-600/5 p-3">
                <p className="text-xs font-semibold text-esynapse-600 dark:text-esynapse-300">5. Tratamiento</p>
                <CampoAmpliable multilinea titulo="Acciones a realizar" placeholder="Acciones a realizar (corrección del trabajo, rectificación de documentos, etc.)" value={tratForm.acciones} onChange={(v) => setTratForm({ ...tratForm, acciones: v })} />
                <div className="grid grid-cols-3 gap-3">
                  {sel('Responsable de las acciones', String(tratForm.responsable_acciones || ''), (e) => setTratForm({ ...tratForm, responsable_acciones: e.target.value }), usuariosOpc('— Designar —'))}
                  <div><label className={lbl}>Certificado reemplazado</label><input className={inp} placeholder="Si cambia el certificado" value={tratForm.certificado_original} onChange={(e) => setTratForm({ ...tratForm, certificado_original: e.target.value })} /></div>
                  <div><label className={lbl}>Nuevo certificado</label><input className={inp} value={tratForm.certificado_nuevo} onChange={(e) => setTratForm({ ...tratForm, certificado_nuevo: e.target.value })} /></div>
                </div>
                <label className="flex items-center gap-2 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={tratForm.requiere_tnc} onChange={(e) => setTratForm({ ...tratForm, requiere_tnc: e.target.checked })} /> Se trata como trabajo no conforme</label>
                <div className="grid grid-cols-4 gap-3">
                  <div className="col-span-3"><CampoAmpliable multilinea titulo="Seguimiento de las acciones" placeholder="Seguimiento: verificación de que las acciones se cumplieron y resolvieron la queja" value={tratForm.seguimiento} onChange={(v) => setTratForm({ ...tratForm, seguimiento: v })} /></div>
                  <div><label className={lbl}>Fecha del seguimiento</label><input type="date" className={inp} value={tratForm.fecha_seguimiento} onChange={(e) => setTratForm({ ...tratForm, fecha_seguimiento: e.target.value })} /></div>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <button onClick={guardarTrat} className={`${tratSinGuardar ? 'btn-primary' : 'btn-secondary'} !py-1.5 text-xs`}>Guardar tratamiento</button>
                  {tratSinGuardar && <span className="text-[11px] text-amber-600 dark:text-amber-400">Cambios sin guardar</span>}
                </div>
                {/* No conformidad */}
                <div className="mt-2 border-t border-esynapse-600/20 pt-2 text-xs">
                  {d.hallazgo_codigo ? (
                    <p>Registrada como No Conformidad <strong>{d.hallazgo_codigo}</strong> ({d.hallazgo_estado}){d.sac_codigo ? `, tratada en la ${d.sac_codigo}` : ' — genere su acción correctiva desde Hallazgos'}.</p>
                  ) : (
                    <div className="grid grid-cols-12 items-end gap-2">
                      <p className="col-span-12 text-[11px] text-slate-500 dark:text-slate-400">Si la queja evidencia una No Conformidad, regístrela: se crea en Hallazgos (procedencia Queja) y sigue el flujo de acción correctiva.</p>
                      <div className="col-span-3">{sel('Clasificación', ncForm.tipo_nc, (e) => setNcForm({ ...ncForm, tipo_nc: e.target.value }), [['nc_menor', 'NC Menor'], ['nc_mayor', 'NC Mayor']])}</div>
                      <div className="col-span-4"><label className={lbl}>Proceso afectado</label><SelectorProceso className={inp} value={ncForm.proceso} onChange={(v) => setNcForm({ ...ncForm, proceso: v })} /></div>
                      <div className="col-span-3"><label className={lbl}>Requisito incumplido</label><input className={inp} placeholder="p. ej. NTP-ISO/IEC 17025 7.8.2" value={ncForm.requisito} onChange={(e) => setNcForm({ ...ncForm, requisito: e.target.value })} /></div>
                      <button disabled={!ncForm.proceso.trim()} onClick={() => accion(() => api.quejas.registrarNc(d.id, ncForm))} className="btn-secondary col-span-2 !py-2 text-xs disabled:opacity-50">Registrar NC</button>
                    </div>
                  )}
                </div>
              </div>
            ) : (d.acciones || d.hallazgo_codigo) && (
              <Seccion titulo="5. Tratamiento">
                <p className="whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Acciones:</strong> {d.acciones}</p>
                <div className="grid grid-cols-2 gap-x-4">
                  <Dato etiqueta="Responsable" valor={d.responsable_acciones_nombre} />
                  <Dato etiqueta="No conformidad" valor={d.hallazgo_codigo ? `${d.hallazgo_codigo}${d.sac_codigo ? ` (${d.sac_codigo})` : ''}` : ''} />
                  <Dato etiqueta="Trabajo no conforme" valor={d.requiere_tnc ? 'Sí' : 'No'} />
                  <Dato etiqueta="Certificado" valor={d.certificado_nuevo ? `${d.certificado_nuevo} reemplaza al ${d.certificado_original}` : ''} />
                </div>
                <p className="whitespace-pre-wrap"><strong className="text-slate-700 dark:text-slate-200">Seguimiento ({fecha(d.fecha_seguimiento)}):</strong> {d.seguimiento}</p>
              </Seccion>
            )}

            {/* 6. Cierre */}
            {d.estado === 'en_cierre' && puedeEditar ? (
              <div className="space-y-2 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3">
                <p className="text-xs font-semibold text-violet-600 dark:text-violet-400">6. Cierre — comunicación del resultado al cliente</p>
                {d.resultado !== 'procedente' && <p className="text-[11px] text-slate-500 dark:text-slate-400">Comunique al cliente los motivos {d.resultado === 'no_relacionada' ? 'por los que la queja no está relacionada con las actividades de la empresa' : 'de la no procedencia'}.</p>}
                <CampoAmpliable multilinea titulo="Comunicación al cliente" placeholder="Lo comunicado al cliente" value={cierreForm.comunicacion_cliente} onChange={(v) => setCierreForm({ ...cierreForm, comunicacion_cliente: v })} />
                <div className="grid grid-cols-3 gap-3">
                  {sel('Medio', cierreForm.medio_cierre, (e) => setCierreForm({ ...cierreForm, medio_cierre: e.target.value }), cat?.medios_comunicacion || [])}
                  {d.resultado === 'procedente' && sel('Conformidad del cliente', cierreForm.conformidad_cliente, (e) => setCierreForm({ ...cierreForm, conformidad_cliente: e.target.value }), [['', '— Seleccionar —'], ...(cat?.conformidad || [])])}
                  {sel('Notificado por (no involucrado)', String(cierreForm.notificado_por || ''), (e) => setCierreForm({ ...cierreForm, notificado_por: e.target.value }), usuariosOpc('— Yo —'))}
                </div>
              </div>
            ) : d.estado === 'cerrada' && (
              <Seccion titulo="6. Cierre — conformidad del cliente" tono="verde">
                <p className="whitespace-pre-wrap">{d.comunicacion_cliente}</p>
                <div className="mt-1 grid grid-cols-2 gap-x-4">
                  <Dato etiqueta="Medio" valor={d.medio_cierre_display} />
                  <Dato etiqueta="Fecha de cierre" valor={fechaHora(d.fecha_cierre)} />
                  <Dato etiqueta="Notificado por" valor={d.notificado_por_nombre} />
                  <Dato etiqueta="Conformidad del cliente" valor={d.conformidad_cliente_display} />
                </div>
              </Seccion>
            )}
            {(d.reaperturas || []).map((r, i) => (
              <p key={i} className="text-[11px] text-violet-600 dark:text-violet-400">Reabierta el {fecha(r.fecha)} por {r.usuario}: {r.motivo}</p>
            ))}

            {/* Comunicaciones al reclamante */}
            <Seccion titulo="Comunicaciones al cliente o parte interesada">
              {(d.comunicaciones || []).length === 0 && <p className="text-slate-400">Aún no se registran comunicaciones.</p>}
              <div className="space-y-1">
                {(d.comunicaciones || []).map((c) => (
                  <div key={c.id} className="rounded border border-slate-200 px-2 py-1 dark:border-slate-800">
                    <p><strong className="text-slate-700 dark:text-slate-200">{c.tipo_display}</strong> · {fechaHora(c.fecha)} · {c.medio_display} · {c.registrado_por}
                      {c.evidencia_url && <a href={c.evidencia_url} target="_blank" rel="noreferrer" className="ml-1 text-esynapse-500 underline">evidencia</a>}</p>
                    <p className="whitespace-pre-wrap">{c.resumen}</p>
                  </div>
                ))}
              </div>
              {d.estado !== 'cerrada' && puedeEditar && (comForm ? (
                <div className="mt-2 space-y-2 rounded-lg border border-dashed border-esynapse-500/50 p-2">
                  <div className="grid grid-cols-3 gap-2">
                    {sel('Tipo', comForm.tipo, (e) => setComForm({ ...comForm, tipo: e.target.value }), (cat?.tipos_comunicacion || []).filter(([v]) => !['resultado', 'no_procede'].includes(v)))}
                    {sel('Medio', comForm.medio, (e) => setComForm({ ...comForm, medio: e.target.value }), cat?.medios_comunicacion || [])}
                    <div><label className={lbl}>Fecha y hora</label><input type="datetime-local" className={inp} max={ahoraLocal()} value={comForm.fecha} onChange={(e) => setComForm({ ...comForm, fecha: e.target.value })} /></div>
                  </div>
                  <CampoAmpliable multilinea placeholder="Resumen de lo comunicado" value={comForm.resumen} onChange={(v) => setComForm({ ...comForm, resumen: v })} />
                  <div className="flex flex-wrap items-center gap-2">
                    <label className="btn-secondary cursor-pointer !py-1 text-xs"><Paperclip className="h-3.5 w-3.5" /> {comForm.evidencia ? comForm.evidencia.name : 'Adjuntar evidencia'}
                      <input type="file" className="hidden" onChange={(e) => { if (e.target.files[0]) setComForm({ ...comForm, evidencia: e.target.files[0] }); e.target.value = '' }} /></label>
                    <button disabled={!comForm.resumen?.trim()} onClick={registrarComunicacion} className="btn-primary !py-1 text-xs disabled:opacity-50">Registrar</button>
                    <button onClick={() => setComForm(null)} className="btn-secondary !py-1 text-xs"><XCircle className="h-3.5 w-3.5" /></button>
                  </div>
                </div>
              ) : (
                <button onClick={() => setComForm({ tipo: (d.comunicaciones || []).some((c) => c.tipo === 'acuse') ? 'avance' : 'acuse', medio: 'email', fecha: ahoraLocal(), resumen: '', evidencia: null })}
                  className="mt-2 flex items-center gap-1 text-xs text-esynapse-500 hover:underline"><Plus className="h-3.5 w-3.5" /> Registrar comunicación</button>
              ))}
            </Seccion>

            {/* Documentos adjuntos */}
            <Seccion titulo="Documentos adjuntos">
              {(d.adjuntos || []).length === 0 && <p className="text-slate-400">Sin documentos adjuntos.</p>}
              {(d.adjuntos || []).map((a) => (
                <p key={a.id} className="flex items-center gap-2">
                  <a href={a.url} target="_blank" rel="noreferrer" className="text-esynapse-500 underline">{a.descripcion || a.nombre}</a>
                  {d.estado !== 'cerrada' && puedeEditar && <button onClick={() => accion(() => api.quejas.quitarAdjunto(d.id, a.id))} className="text-red-500 hover:underline">quitar</button>}
                </p>
              ))}
              {d.estado !== 'cerrada' && puedeEditar && (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <label className="btn-secondary cursor-pointer !py-1 text-xs"><Paperclip className="h-3.5 w-3.5" /> {adjunto.archivo ? adjunto.archivo.name : 'Elegir archivo'}
                    <input type="file" className="hidden" onChange={(e) => { if (e.target.files[0]) setAdjunto({ ...adjunto, archivo: e.target.files[0] }); e.target.value = '' }} /></label>
                  <input className="input-esynapse !w-64 !py-1 text-xs" placeholder="Descripción (p. ej. sustento del incumplimiento)" value={adjunto.descripcion} onChange={(e) => setAdjunto({ ...adjunto, descripcion: e.target.value })} />
                  <button disabled={!adjunto.archivo} onClick={subirAdjunto} className="btn-primary !py-1 text-xs disabled:opacity-50">Adjuntar</button>
                </div>
              )}
            </Seccion>

            {/* Cierre de la etapa actual: al final, después de comunicaciones y adjuntos */}
            {etapaFinal && (
              <BarraEtapa titulo={etapaFinal.titulo} aviso={etapaFinal.aviso} bloqueo={etapaFinal.bloqueo}
                botones={[{ texto: etapaFinal.boton, accion: etapaFinal.accion }]} />
            )}

            {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          </div>
        )}
      </Modal>
    </div>
  )
}
