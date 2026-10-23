import { useCallback, useEffect, useState } from 'react'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import { CheckCircle2, Download, FileText, Lock, Pencil, Plus, Search, Trash2, Wrench, XCircle } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import BarraPasos from '../components/BarraPasos.jsx'
import SelectorProceso from '../components/SelectorProceso.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha } from '../lib/fecha.js'
import EncabezadoModulo from '../components/ui/EncabezadoModulo.jsx'
import EtapaMini from '../components/ui/EtapaMini.jsx'
import { Vistas } from '../components/NavModulo.jsx'

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
// Etapa (0 a 4) de cada estado y color de la etapa actual, para la etapa en miniatura de la lista.
const PASO_ESTADO = { registrada: 0, en_analisis: 1, en_implementacion: 2, en_verificacion: 3, cerrada_conforme: 4, cerrada_sin_ac: 4 }
const TONO_PASO = ['gris', 'ambar', 'azul', 'violeta', 'verde']
const NOMBRE_PASO = ['Registro', 'Análisis de causa', 'Implementación', 'Verificación', 'Cierre']

const FORM_VACIO = {
  fuente: 'auditoria_interna', fuente_detalle: '', normas: [], hallazgo: '',
  entidad_auditora: '', auditor: '', auditado: '', requisito_auditado: '', descripcion_nc: '', responsable: '',
  tipo_nc: 'nc_menor', proceso: '', fecha_registro: '',
}
const CAMPOS_REGISTRO = ['fuente', 'fuente_detalle', 'entidad_auditora', 'auditor', 'auditado', 'requisito_auditado',
  'descripcion_nc', 'responsable', 'fecha_registro']

// Bloque de consulta con la numeración de las secciones del formato.
function Seccion({ n, titulo, tono, children }) {
  return (
    <div className={`rounded-lg border p-3 text-xs ${tono === 'verde' ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-slate-200 dark:border-slate-800'}`}>
      <p className="mb-1 text-xs font-semibold text-slate-500 dark:text-slate-400">{n}. {titulo}</p>
      <div className="text-slate-600 dark:text-slate-300">{children}</div>
    </div>
  )
}

// En un nuevo ciclo, si tras revisarlo se confirmó lo mismo (porqués o causa raíz), no se repite.
function mismoAnalisisQueElCicloAnterior(d, campo) {
  const ant = (d.ciclos_anteriores || []).slice(-1)[0]
  if (!ant) return false
  if (campo === 'porques') return (d.porques || []).length > 0 && JSON.stringify(ant.porques || []) === JSON.stringify(d.porques || [])
  return Boolean((d.causa_raiz || '').trim()) && (ant.causa_raiz || '').trim() === (d.causa_raiz || '').trim()
}

function Dato({ etiqueta, valor }) {
  return <p><strong className="text-slate-700 dark:text-slate-200">{etiqueta}:</strong> {valor || '—'}</p>
}

export default function AccionesCorrectivas() {
  const { tienePermiso, usuario } = useAuth()
  const confirmar = useConfirm()
  const [items, setItems] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [hallazgos, setHallazgos] = useState([])
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('')
  const [soloAbiertas, setSoloAbiertas] = useState(false)
  const [modalCrear, setModalCrear] = useState(false)
  const [detalle, setDetalle] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [editandoId, setEditandoId] = useState(null)   // corrección del registro (solo Registrada)
  const [error, setError] = useState('')
  // Formularios por etapa
  const [evalForm, setEvalForm] = useState({ significancia: 'bajo', analisis_extension: '', requiere_ac: 'true', justificacion: '', responsable: '' })
  // Cadena de porqués: cada fila es la pregunta que redacta el analista y su respuesta.
  const PAR_VACIO = { pregunta: '', respuesta: '' }
  const aPar = (p) => (typeof p === 'string' ? { pregunta: '', respuesta: p } : { ...PAR_VACIO, ...p })
  const [porques, setPorques] = useState([PAR_VACIO])
  const [causaRaiz, setCausaRaiz] = useState('')
  const [cambiosSig, setCambiosSig] = useState(false)
  const [actRiesgos, setActRiesgos] = useState(false)
  const [nuevaAcc, setNuevaAcc] = useState(null)   // {tipo, descripcion, fecha_propuesta, responsable}
  const [editAcc, setEditAcc] = useState(null)     // {id, descripcion, fecha_propuesta, responsable}
  const [verificador, setVerificador] = useState('')
  const [completar, setCompletar] = useState({}) // {accionId: {verificacion, archivo}}
  const [eficaciaTxt, setEficaciaTxt] = useState('')

  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const p = new URLSearchParams()
    if (buscar) p.set('buscar', buscar)
    if (estado) p.set('estado', estado)
    if (soloAbiertas) p.set('abiertas', '1')
    const data = await ultima(api.sac.listar(`?${p}`))
    setItems(data.results ?? data)
  }, [buscar, estado, soloAbiertas])

  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
    api.usuarios.listar().then((d) => setUsuarios(d.results ?? d)).catch(() => {})
    cargarHallazgos()
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  // NC del registro de hallazgos que aún no se tratan en ninguna solicitud.
  const cargarHallazgos = () => api.hallazgos.listar('?estado=registrado')
    .then((d) => setHallazgos((d.results ?? d).filter((h) => ['nc_mayor', 'nc_menor'].includes(h.tipo) && !h.sac_codigo)))
    .catch(() => {})

  const abrirPdf = async (promesa) => {
    setError('')
    try {
      const url = URL.createObjectURL(await promesa)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  const filtros = () => {
    const p = new URLSearchParams()
    if (buscar) p.set('buscar', buscar)
    if (estado) p.set('estado', estado)
    if (soloAbiertas) p.set('abiertas', '1')
    return `?${p}`
  }

  const abrirDetalle = async (id) => {
    setError('')
    const d = await api.sac.detalle(id)
    setDetalle(d)
    setEvalForm({ significancia: d.significancia || 'bajo', analisis_extension: d.analisis_extension || '',
      requiere_ac: 'true', justificacion: d.justificacion_evaluacion || '', responsable: d.responsable || '' })
    setPorques(d.porques?.length ? d.porques.map(aPar) : [PAR_VACIO])
    setCausaRaiz(d.causa_raiz || '')
    setCambiosSig(Boolean(d.aplica_cambios_sig))
    setActRiesgos(Boolean(d.aplica_actualizar_riesgos))
    setVerificador(d.verificador || '')
    setEficaciaTxt('')
    setCompletar({})
    setNuevaAcc(null); setEditAcc(null)
  }

  const refrescar = async () => {
    await cargar()
    if (!detalle) return
    const d = await api.sac.detalle(detalle.id)
    setDetalle(d)
    // Al cambiar de etapa: la evaluación en blanco y sin formularios de acción abiertos.
    if (d.estado !== detalle.estado) { setEficaciaTxt(''); setNuevaAcc(null); setEditAcc(null) }
  }
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
      if (editandoId) {
        const cambios = Object.fromEntries(CAMPOS_REGISTRO.map((c) => [c, datos[c]]))
        cambios.normas_aplicables = datos.normas_aplicables
        if (!cambios.responsable) cambios.responsable = null
        if (!cambios.fecha_registro) cambios.fecha_registro = null
        await api.sac.editar(editandoId, cambios)
        setModalCrear(false); setEditandoId(null)
        await refrescar()
        return
      }
      if (!datos.hallazgo) delete datos.hallazgo
      else { delete datos.tipo_nc; delete datos.proceso }
      if (!datos.responsable) delete datos.responsable
      if (!datos.fecha_registro) delete datos.fecha_registro
      await api.sac.crear(datos)
      setModalCrear(false); setForm(FORM_VACIO); await cargar(); cargarHallazgos()
    } catch (e2) { setError(e2.message) }
  }

  const abrirCorreccion = () => {
    setForm({ ...FORM_VACIO, ...Object.fromEntries(CAMPOS_REGISTRO.map((c) => [c, detalle[c] ?? ''])),
      normas: detalle.normas_aplicables || [], hallazgo: '' })
    setError(''); setEditandoId(detalle.id); setModalCrear(true)
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

  // Secciones 5 (correcciones) y 8 (acciones correctivas) del formato: se
  // agregan, corrigen o quitan mientras su etapa sigue abierta; en la
  // implementación se registra su ejecución.
  const puedeEditar = tienePermiso('acciones_correctivas', 'editar')
  const filaFormulario = (f, setF, guardar, textoBoton) => (
    <div className="grid grid-cols-12 items-end gap-2 rounded-lg border border-dashed border-esynapse-500/50 p-2">
      <div className="col-span-6">
        <CampoAmpliable className="!py-1.5 text-xs" placeholder="Descripción" titulo="Descripción"
          value={f.descripcion} onChange={(v) => setF({ ...f, descripcion: v })} />
      </div>
      <input type="date" title="Fecha propuesta" className="input-esynapse col-span-2 !py-1.5 text-xs" value={f.fecha_propuesta || ''}
        onChange={(e) => setF({ ...f, fecha_propuesta: e.target.value })} />
      <select className="input-esynapse col-span-2 !py-1.5 text-xs" value={f.responsable || ''}
        onChange={(e) => setF({ ...f, responsable: e.target.value })}>
        <option value="">Responsable</option>
        {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
      </select>
      <div className="col-span-2 flex gap-1">
        <button type="button" disabled={!f.descripcion || !f.fecha_propuesta}
          onClick={() => accion(async () => { await guardar(); setF(null) })} className="btn-primary !px-2 !py-1.5 text-xs">{textoBoton}</button>
        <button type="button" onClick={() => setF(null)} className="btn-secondary !px-2 !py-1.5 text-xs">✕</button>
      </div>
    </div>
  )
  // Completar pide confirmación: si es la última pendiente, la solicitud pasa a
  // verificación de la eficacia (o se cierra, si solo requería corrección).
  const completarAccion = async (acc, verificacion, archivo) => {
    const pendientes = (detalle.acciones || []).filter((a) => a.estado === 'pendiente')
    const ultima = pendientes.length === 1
    const siguiente = !ultima ? '' : detalle.requiere_ac
      ? ' Es la última pendiente: la solicitud pasará a la verificación de la eficacia.'
      : ' Es la última pendiente: la solicitud se cerrará (solo requería corrección) y ya no podrá reabrirse.'
    if (!await confirmar({ titulo: `Completar ${acc.tipo_display.toLowerCase()}`, textoConfirmar: 'Completar',
      mensaje: `¿Registrar «${acc.descripcion}» como completada${archivo ? ` con la evidencia «${archivo.name}»` : ' sin adjuntar evidencia'}?${siguiente}` })) return
    await accion(async () => {
      const fd = new FormData()
      fd.append('accion_id', acc.id)
      fd.append('verificacion', verificacion)
      if (archivo) fd.append('evidencia', archivo)
      await api.sac.completarAccion(detalle.id, fd)
      setCompletar((c) => ({ ...c, [acc.id]: undefined }))
    })
  }
  const reabrirAccion = async (acc) => {
    const motivo = await confirmar({ titulo: `Reabrir ${acc.tipo_display.toLowerCase()}`, textoConfirmar: 'Reabrir',
      mensaje: `«${acc.descripcion}» volverá a Pendiente para corregir su verificación o evidencia. Lo registrado queda en el historial.`,
      entrada: { etiqueta: 'Motivo', placeholder: 'Por qué se reabre', obligatorio: true, multilinea: true } })
    if (motivo === null || motivo === undefined) return
    await accion(() => api.sac.reabrirAccion(detalle.id, acc.id, motivo))
  }
  const listaAcciones = (tipo, titulo) => {
    const lista = (detalle?.acciones || []).filter((a) => a.tipo === tipo)
    const abierta = (detalle?.etapas_abiertas || []).includes(tipo === 'correctiva' ? 'acciones' : 'correcciones')
    const n = titulo.split('.')[0]
    const nombre = titulo.split('. ')[1]
    if (!lista.length && !abierta) {
      // Sin registros: se indica en las etapas ya superadas (como en el formato).
      const superada = tipo === 'correccion' ? detalle?.estado !== 'registrada'
        : !['registrada', 'en_analisis'].includes(detalle?.estado)
      return superada ? <Seccion n={n} titulo={nombre}><p className="text-slate-400">No se registraron.</p></Seccion> : null
    }
    return (
      <Seccion n={n} titulo={nombre}>
        <div className="space-y-1">
          {lista.map((acc) => (
            editAcc?.id === acc.id ? (
              <div key={acc.id}>{filaFormulario(editAcc, setEditAcc, () => api.sac.editarAccion(detalle.id, { accion_id: acc.id, ...editAcc, responsable: editAcc.responsable || null }), 'Guardar')}</div>
            ) : (
            <div key={acc.id} className="rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-800">
              <div className="flex items-center justify-between">
                <p>
                  <span className={`mr-1 whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${
                    acc.tipo === 'correccion' ? 'bg-slate-500/15 text-slate-500' : 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300'}`}>
                    {acc.tipo_display}
                  </span>
                  {detalle.ciclo > 1 && <span className="mr-1 text-[11px] text-slate-500 dark:text-slate-400">ciclo {acc.ciclo}</span>}
                  {acc.descripcion}
                </p>
                <div className="flex shrink-0 items-center gap-1">
                  {acc.editable && puedeEditar && editAcc?.id !== acc.id && (
                    <>
                      <button type="button" title="Corregir" onClick={() => setEditAcc({ id: acc.id, descripcion: acc.descripcion, fecha_propuesta: acc.fecha_propuesta, responsable: acc.responsable || '' })}
                        className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700"><Pencil className="h-3.5 w-3.5" /></button>
                      <button type="button" title="Quitar" onClick={() => accion(() => api.sac.quitarAccion(detalle.id, acc.id))}
                        className="rounded p-1 text-slate-400 hover:bg-red-500/10 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                    </>
                  )}
                  <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${
                    acc.estado === 'completada' ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-amber-500/15 text-amber-600 dark:text-amber-400'}`}>
                    {acc.estado_display}
                  </span>
                </div>
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
              {acc.estado === 'completada' && acc.verificacion && <p className="text-emerald-600 dark:text-emerald-400">Verificación: {acc.verificacion}</p>}
              {(acc.reaperturas || []).map((r, i) => (
                <p key={i} className="text-[11px] text-violet-600 dark:text-violet-400">
                  Reabierta el {(r.fecha || '').slice(0, 10)} por {r.usuario}: {r.motivo}
                </p>
              ))}
              {/* Reabrir una acción completada por error (antes de verificar la eficacia) */}
              {acc.reabrible && puedeEditar && (
                <button type="button" onClick={() => reabrirAccion(acc)}
                  className="mt-1 text-[11px] text-violet-600 hover:underline dark:text-violet-400">Reabrir (completada por error)</button>
              )}
              {/* Completar (etapa implementación) */}
              {detalle.estado === 'en_implementacion' && acc.estado === 'pendiente' && puedeEditar && (() => {
                const c = completar[acc.id] || {}
                const verif = c.verificacion ?? acc.verificacion ?? ''
                return (
                  <div className="mt-2 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="min-w-[14rem] flex-1">
                        <CampoAmpliable className="!py-1 text-xs" placeholder="Verificación: qué se hizo y cómo se comprobó" titulo={`Verificación: ${acc.descripcion}`}
                          value={verif} onChange={(v) => setCompletar({ ...completar, [acc.id]: { ...c, verificacion: v } })} />
                      </div>
                      <label className="btn-secondary cursor-pointer !py-1 text-xs">
                        <FileText className="h-3.5 w-3.5" /> {c.archivo ? 'Cambiar evidencia' : 'Adjuntar evidencia'}
                        <input type="file" className="hidden"
                          onChange={(e) => { if (e.target.files[0]) setCompletar({ ...completar, [acc.id]: { ...c, archivo: e.target.files[0] } }); e.target.value = '' }} />
                      </label>
                      <button disabled={!verif.trim()} title={!verif.trim() ? 'Describa la verificación' : undefined}
                        onClick={() => completarAccion(acc, verif, c.archivo)} className="btn-primary !py-1 text-xs disabled:opacity-50">
                        <CheckCircle2 className="h-3 w-3" /> Completar
                      </button>
                    </div>
                    {c.archivo && (
                      <p className="flex items-center gap-2 text-[11px] text-slate-600 dark:text-slate-300">
                        <FileText className="h-3 w-3" /> {c.archivo.name}
                        <button type="button" className="text-red-500 hover:underline" onClick={() => setCompletar({ ...completar, [acc.id]: { ...c, archivo: null } })}>quitar</button>
                      </p>
                    )}
                    {!c.archivo && acc.evidencia_url && <p className="text-[11px] text-slate-400">Se conserva la evidencia adjunta antes; adjunte otra solo si la reemplaza.</p>}
                  </div>
                )
              })()}
            </div>
            )
          ))}
          {!lista.length && <p className="text-slate-400">Aún no se registran.</p>}
          {abierta && puedeEditar && (nuevaAcc?.tipo === tipo
            ? filaFormulario(nuevaAcc, setNuevaAcc, () => api.sac.agregarAccion(detalle.id, { ...nuevaAcc, responsable: nuevaAcc.responsable || undefined }), 'Agregar')
            : (
              <button type="button" onClick={() => setNuevaAcc({ tipo, descripcion: '', fecha_propuesta: '', responsable: '' })}
                className="flex items-center gap-1 text-xs text-esynapse-500 hover:underline">
                <Plus className="h-3.5 w-3.5" /> {tipo === 'correctiva' ? 'Agregar acción correctiva' : 'Agregar corrección'}
              </button>
            ))}
        </div>
      </Seccion>
    )
  }

  // El análisis en pantalla difiere de lo guardado (para avisar antes de aprobar el plan).
  const normPq = (lista) => JSON.stringify((lista || []).map(aPar)
    .map((p) => ({ pregunta: p.pregunta.trim(), respuesta: p.respuesta.trim() })).filter((p) => p.pregunta || p.respuesta))
  const analisisSinGuardar = Boolean(detalle) && detalle.estado === 'en_analisis' && (
    normPq(porques) !== normPq(detalle.porques) || causaRaiz.trim() !== (detalle.causa_raiz || '').trim()
    || cambiosSig !== Boolean(detalle.aplica_cambios_sig) || actRiesgos !== Boolean(detalle.aplica_actualizar_riesgos))

  // Acción que cierra la etapa en curso (al final de la ficha), con lo que falta para habilitarla.
  const etapaFinal = (() => {
    const d = detalle
    if (!d) return null
    const puedeAprobar = tienePermiso('acciones_correctivas', 'aprobar')
    if (d.estado === 'registrada' && puedeEditar) {
      return {
        titulo: 'Cerrar la etapa de registro y evaluación',
        nota: evalForm.requiere_ac === 'true' ? 'Pasa al análisis de causa.' : 'Sin acción correctiva: pasa a implementar las correcciones.',
        bloqueo: !evalForm.responsable ? 'Designe en «Evaluación de la necesidad de AC» al responsable de la implementación.' : '',
        botones: [{ texto: 'Registrar evaluación', accion: () => accion(() => api.sac.evaluar(d.id, { ...evalForm, requiere_ac: evalForm.requiere_ac === 'true' })) }],
      }
    }
    if (d.estado === 'en_analisis' && puedeAprobar) {
      const hayAc = (d.acciones || []).some((a) => a.tipo === 'correctiva' && a.ciclo === d.ciclo)
      return {
        titulo: 'Cerrar la etapa de análisis: aprobar el plan',
        nota: 'Pasa a la implementación de las acciones.',
        bloqueo: analisisSinGuardar ? 'Guarde primero el análisis de causa.'
          : !(d.causa_raiz || '').trim() ? 'Registre y guarde la causa raíz.'
            : !hayAc ? 'Agregue al menos una acción correctiva en «8. Acciones correctivas».'
              : !verificador ? 'Designe al verificador de eficacia.' : '',
        botones: [{ texto: 'Aprobar plan → Implementación', accion: () => accion(() => api.sac.aprobarPlan(d.id, verificador)) }],
      }
    }
    if (d.estado === 'en_implementacion') {
      const pendientes = (d.acciones || []).filter((a) => a.estado === 'pendiente').length
      return {
        titulo: 'Etapa de implementación',
        nota: `Se cierra al completar la última acción pendiente (quedan ${pendientes}); ${d.requiere_ac ? 'luego pasa a la verificación de la eficacia' : 'luego se cierra la solicitud'}.`,
        botones: [],
      }
    }
    if (d.estado === 'en_verificacion' && (puedeAprobar || (usuario && d.verificador === usuario.id))) {
      return {
        titulo: 'Cerrar la etapa de verificación',
        nota: 'Eficaz: se cierra la solicitud y sus No Conformidades. No eficaz: vuelve al análisis con un ciclo nuevo.',
        bloqueo: !eficaciaTxt.trim() ? 'Escriba la evaluación de la eficacia.' : '',
        botones: [
          { texto: 'Eficaz → Cerrar conforme', accion: () => accion(() => api.sac.verificarEficacia(d.id, true, eficaciaTxt)) },
          { texto: 'No eficaz → Reanálisis', peligro: true, accion: () => accion(() => api.sac.verificarEficacia(d.id, false, eficaciaTxt)) },
        ],
      }
    }
    return null
  })()

  const esAuditoria = form.fuente.startsWith('auditoria')

  return (
    <div className="space-y-4">
      <EncabezadoModulo
        seccion="Sistema de gestión"
        titulo="Acciones correctivas"
        descripcion="Cada no conformidad se trata en una solicitud que avanza por cinco etapas. Una etapa cerrada queda solo de lectura."
        acciones={<>
          <button onClick={() => abrirPdf(api.sac.seguimientoPdf(filtros()))} className="btn-secondary"
            title="Seguimiento a solicitudes de acciones correctivas y no conformidades (con los filtros aplicados)">
            <FileText className="h-4 w-4" /> Imprimir seguimiento
          </button>
          {tienePermiso('acciones_correctivas', 'crear') && (
            <button onClick={() => { setForm(FORM_VACIO); setError(''); setEditandoId(null); cargarHallazgos(); setModalCrear(true) }} className="btn-primary">
              <Plus className="h-4 w-4" /> Nueva SAC
            </button>
          )}
        </>}
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input-esynapse w-72 pl-9" placeholder="Buscar por código o descripción"
            aria-label="Buscar por código o descripción" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <select className="input-esynapse w-56" aria-label="Estado" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
        <div className="ml-auto">
          <Vistas opciones={[['abiertas', 'Abiertas'], ['todas', 'Todas']]} valor={soloAbiertas ? 'abiertas' : 'todas'}
            onChange={(v) => setSoloAbiertas(v === 'abiertas')} />
        </div>
      </div>

      {/* Seguimiento a solicitudes de acciones correctivas y no conformidades */}
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig min-w-[960px]">
          <thead>
            <tr>
              <th scope="col">N° SAC</th>
              <th scope="col">No conformidad</th>
              <th scope="col">Procedencia</th>
              <th scope="col" className="text-center">Etapa</th>
              <th scope="col">Responsable de la implementación</th>
              <th scope="col" className="text-right">Fecha de cierre</th>
              <th scope="col" className="text-center">Clasificación</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => {
              const paso = PASO_ESTADO[s.estado] ?? 0
              return (
                <tr key={s.id} onClick={() => abrirDetalle(s.id)} className="fila">
                  <td className="whitespace-nowrap font-semibold text-esynapse-700 dark:text-esynapse-300">{s.codigo}</td>
                  <td className="max-w-sm"><span className="line-clamp-2" title={s.descripcion_nc}>{s.descripcion_nc}</span></td>
                  <td className="text-slate-500 dark:text-slate-400">
                    {s.fuente_display}{s.fuente_detalle ? `: ${s.fuente_detalle}` : ''}
                  </td>
                  <td className="text-center"><EtapaMini actual={paso} tono={TONO_PASO[paso]} texto={s.estado_display} /></td>
                  <td className="text-slate-500 dark:text-slate-400">{s.responsable_nombre || '—'}</td>
                  <td className="whitespace-nowrap text-right">{s.fecha_cierre ? fecha(s.fecha_cierre) : '—'}</td>
                  <td className="whitespace-nowrap text-center text-slate-500 dark:text-slate-400">{s.clasificacion || '—'}</td>
                </tr>
              )
            })}
            {items.length === 0 && (
              <tr><td colSpan={7} className="py-8 text-center text-slate-400">{soloAbiertas ? 'No hay solicitudes abiertas' : 'Sin solicitudes'}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Crear */}
      <Modal abierto={modalCrear} titulo={editandoId ? 'Corregir registro de la solicitud' : 'Nueva Solicitud de Acción Correctiva'}
        onCerrar={() => { setModalCrear(false); setEditandoId(null) }}>
        <form onSubmit={crear} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {sel('Procedencia', form.fuente, (e) => setForm({ ...form, fuente: e.target.value }), FUENTES)}
            {!editandoId && (
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">No Conformidad del registro de hallazgos</label>
                <select className="input-esynapse" value={form.hallazgo} onChange={(e) => {
                  const h = hallazgos.find((x) => String(x.id) === e.target.value)
                  setForm({ ...form, hallazgo: e.target.value, ...(h ? { descripcion_nc: form.descripcion_nc || '' } : {}) })
                }}>
                  <option value="">— Registrar una NC nueva —</option>
                  {hallazgos.map((h) => <option key={h.id} value={h.id}>{h.codigo} — {h.proceso}</option>)}
                </select>
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Fecha de registro</label>
              <input type="date" className="input-esynapse" max={fecha(new Date())} value={form.fecha_registro || ''}
                onChange={(e) => setForm({ ...form, fecha_registro: e.target.value })} />
              <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">Si se deja vacía, se usa la fecha de hoy.</p>
            </div>
          </div>
          {form.fuente === 'otros' && (
            <input className="input-esynapse" placeholder="Detallar la procedencia" value={form.fuente_detalle}
              onChange={(e) => setForm({ ...form, fuente_detalle: e.target.value })} />
          )}
          {!editandoId && !form.hallazgo && (
            <div className="grid grid-cols-2 gap-3 rounded-lg border border-dashed border-slate-300 p-2 dark:border-slate-700">
              {sel('Clasificación de la NC', form.tipo_nc, (e) => setForm({ ...form, tipo_nc: e.target.value }), [['nc_mayor', 'NC Mayor'], ['nc_menor', 'NC Menor']])}
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Proceso afectado</label>
                <SelectorProceso required value={form.proceso} onChange={(v) => setForm({ ...form, proceso: v })} />
              </div>
              <p className="col-span-2 text-[11px] text-slate-500 dark:text-slate-400">La NC se registra también en Hallazgos (registro único) y queda tratada por esta solicitud.</p>
            </div>
          )}
          {esAuditoria && (
            <div className="grid grid-cols-3 gap-3">
              <input className="input-esynapse" placeholder="Personal / entidad auditora" value={form.entidad_auditora} onChange={(e) => setForm({ ...form, entidad_auditora: e.target.value })} />
              <input className="input-esynapse" placeholder="Auditor" value={form.auditor} onChange={(e) => setForm({ ...form, auditor: e.target.value })} />
              <input className="input-esynapse" placeholder="Auditado" value={form.auditado} onChange={(e) => setForm({ ...form, auditado: e.target.value })} />
            </div>
          )}
          <input className="input-esynapse" placeholder="Requisito incumplido (p. ej. ISO 17025 6.4.8)" value={form.requisito_auditado}
            onChange={(e) => setForm({ ...form, requisito_auditado: e.target.value })} />
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
            <CampoAmpliable multilinea rows={3} required={!form.hallazgo} value={form.descripcion_nc} titulo="Descripción de la No Conformidad"
              placeholder={form.hallazgo ? 'Si se deja vacío, se toma la descripción del hallazgo' : ''}
              onChange={(v) => setForm({ ...form, descripcion_nc: v })} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Responsable de la implementación</label>
            <select className="input-esynapse" value={form.responsable} onChange={(e) => setForm({ ...form, responsable: e.target.value })}>
              <option value="">— Por designar —</option>
              {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
            </select>
          </div>
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => { setModalCrear(false); setEditandoId(null) }} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">{editandoId ? 'Guardar corrección' : 'Registrar SAC'}</button>
          </div>
        </form>
      </Modal>

      {/* Detalle */}
      <Modal abierto={Boolean(detalle) && !modalCrear} titulo={detalle ? `${detalle.codigo} — Solicitud de Acción Correctiva` : ''}
        onCerrar={() => setDetalle(null)} panel ancho="max-w-3xl">
        {detalle && (
          <div className="space-y-4 text-sm">
            <BarraPasos pasos={NOMBRE_PASO} actual={pasoActual(detalle)} cerrado={detalle.estado.startsWith('cerrada')} />

            <div className="flex flex-wrap items-center gap-2">
              <button onClick={() => abrirPdf(api.sac.pdf(detalle.id))} className="btn-secondary !py-1 text-xs">
                <FileText className="h-3.5 w-3.5" /> PDF de la solicitud
              </button>
              {(detalle.etapas_abiertas || []).includes('registro') && tienePermiso('acciones_correctivas', 'editar') ? (
                <button onClick={abrirCorreccion} className="btn-secondary !py-1 text-xs"><Pencil className="h-3.5 w-3.5" /> Corregir registro</button>
              ) : (
                <span className="flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Registro de solo lectura (etapa cerrada)</span>
              )}
            </div>

            {/* Secciones 1 a 4 del formato (consulta) */}
            <Seccion n="1" titulo="Procedencia">
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <Dato etiqueta="Fecha de registro" valor={detalle.fecha_registro ? fecha(detalle.fecha_registro) : ''} />
                <Dato etiqueta="N° de registro" valor={detalle.codigo} />
                <Dato etiqueta="Procedencia" valor={`${detalle.fuente_display}${detalle.fuente_detalle ? `: ${detalle.fuente_detalle}` : ''}`} />
                <Dato etiqueta="Clasificación" valor={detalle.clasificacion} />
                <Dato etiqueta="Personal / entidad auditora" valor={detalle.entidad_auditora} />
                <Dato etiqueta="Requisito auditado" valor={detalle.requisito_auditado} />
                <Dato etiqueta="Auditor" valor={detalle.auditor} />
                <Dato etiqueta="Auditado" valor={detalle.auditado} />
                <Dato etiqueta="Registrado por" valor={detalle.registrado_por} />
                <Dato etiqueta="No conformidades que trata" valor={(detalle.hallazgos_vinculados || []).length
                  ? detalle.hallazgos_vinculados.map((h) => `${h.codigo}${h.es_origen ? '' : ' (ocurrencia sumada)'}`).join(', ')
                  : detalle.hallazgo_codigo} />
              </div>
              {detalle.normas_display?.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {detalle.normas_display.map((n) => (
                    <span key={n} className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_NORMA[n] || 'bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>{n}</span>
                  ))}
                </div>
              )}
            </Seccion>
            <Seccion n="2" titulo="No conformidad">
              <p className="whitespace-pre-wrap">{detalle.descripcion_nc}</p>
            </Seccion>
            {detalle.estado !== 'registrada' && (
              <>
                <Seccion n="3" titulo="Nivel de significancia y necesidad de acción correctiva">
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    <Dato etiqueta="Significancia" valor={detalle.significancia_display} />
                    <Dato etiqueta="¿Requiere acción correctiva?" valor={detalle.requiere_ac == null ? '' : detalle.requiere_ac ? 'Sí' : 'No — solo corrección'} />
                    <Dato etiqueta="Responsable de la implementación" valor={detalle.responsable_nombre} />
                    <Dato etiqueta="Verificador de eficacia" valor={detalle.verificador_nombre} />
                  </div>
                  {detalle.justificacion_evaluacion && <p className="mt-1"><strong className="text-slate-700 dark:text-slate-200">Justificación:</strong> {detalle.justificacion_evaluacion}</p>}
                </Seccion>
                <Seccion n="4" titulo="Análisis de la extensión de la no conformidad">
                  <p className="whitespace-pre-wrap">{detalle.analisis_extension || '—'}</p>
                </Seccion>
              </>
            )}

            {/* ETAPA 1: Evaluación */}
            {detalle.estado === 'registrada' && tienePermiso('acciones_correctivas', 'editar') && (
              <div className="space-y-2 rounded-lg border border-esynapse-600/30 bg-esynapse-600/5 p-3">
                <p className="text-xs font-semibold text-esynapse-600 dark:text-esynapse-300">Evaluación de la necesidad de AC</p>
                <div className="grid grid-cols-3 gap-2">
                  {sel('Significancia', evalForm.significancia, (e) => setEvalForm({ ...evalForm, significancia: e.target.value }), [['bajo','Bajo'],['alto','Alto']])}
                  {sel('¿Requiere acción correctiva?', evalForm.requiere_ac, (e) => setEvalForm({ ...evalForm, requiere_ac: e.target.value }), [['true','Sí — requiere AC'],['false','No — solo corrección']])}
                  {sel('Responsable de la implementación', evalForm.responsable, (e) => setEvalForm({ ...evalForm, responsable: e.target.value }),
                    [['', '— Designar —'], ...usuarios.map((u) => [String(u.id), u.nombre_completo])])}
                </div>
                <CampoAmpliable multilinea placeholder="Análisis de la extensión de la NC"
                  value={evalForm.analisis_extension} onChange={(v) => setEvalForm({ ...evalForm, analisis_extension: v })} />
                <CampoAmpliable multilinea placeholder="Justificación (impacto, recurrencia, riesgo...)"
                  value={evalForm.justificacion} onChange={(v) => setEvalForm({ ...evalForm, justificacion: v })} />
              </div>
            )}

            {listaAcciones('correccion', '5. Corrección')}

            {/* ETAPA 2: Análisis de causa */}
            {detalle.estado === 'en_analisis' && tienePermiso('acciones_correctivas', 'editar') && (
              <div className="space-y-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">Análisis de causa — 5 Porqués</p>
                {/* Cadena de los 5 porqués (Anexo 1): el analista redacta cada
                    pregunta según su análisis y registra la respuesta; la siguiente
                    pregunta parte de esa respuesta. */}
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Redacte la pregunta y su respuesta. La siguiente pregunta debe partir de la respuesta anterior; siga hasta llegar a una causa cuya eliminación evite que se repita (pueden ser más de cinco).
                </p>
                {(() => {
                  const ultimo = (detalle.ciclos_anteriores || []).slice(-1)[0]
                  const vacio = !causaRaiz.trim() && porques.every((p) => !p.pregunta.trim() && !p.respuesta.trim())
                  return ultimo && vacio ? (
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-violet-500/10 px-3 py-2 text-xs text-violet-700 dark:text-violet-300">
                      <span>Ciclo {detalle.ciclo}: las acciones del ciclo {ultimo.ciclo} no fueron eficaces. Revise el análisis de causa.</span>
                      <button type="button" className="btn-secondary !py-1 text-xs"
                        onClick={() => { setPorques((ultimo.porques || []).length ? ultimo.porques.map(aPar) : [PAR_VACIO]); setCausaRaiz(ultimo.causa_raiz || '') }}>
                        Partir del análisis del ciclo {ultimo.ciclo}
                      </button>
                    </div>
                  ) : null
                })()}
                {porques.map((p, i) => {
                  const previa = i > 0 ? porques[i - 1].respuesta.trim() : ''
                  const sugerida = i === 0 ? '¿Por qué ocurrió la No Conformidad?' : `¿Por qué ${previa.replace(/[.\s]+$/, '').replace(/^./, (c) => c.toLowerCase())}?`
                  const cambiar = (campo, valor) => setPorques(porques.map((x, j) => (j === i ? { ...x, [campo]: valor } : x)))
                  return (
                    <div key={i} className="grid grid-cols-12 items-start gap-2 rounded-lg border border-amber-500/20 bg-white/60 p-2 dark:bg-slate-900/40">
                      <span className="col-span-1 pt-2 text-center text-xs font-semibold text-amber-600 dark:text-amber-400">{i + 1}</span>
                      <div className="col-span-5">
                        <CampoAmpliable placeholder={`Pregunta (p. ej. ${sugerida})`} titulo={`${i + 1}. Pregunta`}
                          value={p.pregunta} onChange={(v) => cambiar('pregunta', v)} />
                      </div>
                      <div className="col-span-5">
                        <CampoAmpliable placeholder="Respuesta: porque…" titulo={`${i + 1}. Respuesta${p.pregunta ? ` — ${p.pregunta}` : ''}`}
                          value={p.respuesta} onChange={(v) => cambiar('respuesta', v)} />
                      </div>
                      {porques.length > 1 && (
                        <button type="button" title="Quitar este porqué" onClick={() => setPorques(porques.filter((_, j) => j !== i))}
                          className="col-span-1 pt-2 text-xs text-red-500 hover:underline">quitar</button>
                      )}
                    </div>
                  )
                })}
                <div className="flex flex-wrap gap-3">
                  {porques.every((p) => p.pregunta.trim() && p.respuesta.trim()) && (
                    <button type="button" onClick={() => setPorques([...porques, PAR_VACIO])} className="text-xs text-esynapse-500 hover:underline">+ siguiente ¿por qué?</button>
                  )}
                  {[...porques].reverse().find((p) => p.respuesta.trim()) && (
                    <button type="button" onClick={() => setCausaRaiz([...porques].reverse().find((p) => p.respuesta.trim()).respuesta)}
                      className="text-xs text-esynapse-500 hover:underline">Usar la última respuesta como causa raíz</button>
                  )}
                </div>
                <CampoAmpliable multilinea placeholder="Causa raíz identificada"
                  value={causaRaiz} onChange={setCausaRaiz} />
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
                <div className="flex flex-wrap items-center gap-3">
                  <button onClick={() => accion(() => api.sac.registrarAnalisis(detalle.id, {
                    porques: porques.filter((p) => p.pregunta.trim() || p.respuesta.trim()), causa_raiz: causaRaiz,
                    aplica_cambios_sig: cambiosSig, aplica_actualizar_riesgos: actRiesgos }))}
                    className={`${analisisSinGuardar ? 'btn-primary' : 'btn-secondary'} !py-1.5 text-xs`}>Guardar análisis</button>
                  {analisisSinGuardar && <span className="text-[11px] text-amber-600 dark:text-amber-400">Cambios sin guardar</span>}
                </div>
              </div>
            )}

            {/* Ciclos de análisis no eficaces (historial) */}
            {(detalle.ciclos_anteriores || []).length > 0 && (
              <div className="space-y-2 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3 text-xs">
                <p className="font-semibold text-violet-600 dark:text-violet-400">Ciclos anteriores (verificados como no eficaces)</p>
                {detalle.ciclos_anteriores.map((c) => (
                  <div key={c.ciclo} className="text-slate-600 dark:text-slate-300">
                    <p><strong>Ciclo {c.ciclo}</strong> · verificado el {(c.fecha || '').slice(0, 10)} por {c.verificado_por}</p>
                    {(c.porques || []).length > 0 && (
                      <ol className="list-inside list-decimal text-slate-500 dark:text-slate-400">
                        {c.porques.map(aPar).map((p, i) => <li key={i}>{p.pregunta && <strong className="text-slate-600 dark:text-slate-300">{p.pregunta} </strong>}{p.respuesta}</li>)}
                      </ol>
                    )}
                    <p>Causa raíz: {c.causa_raiz || '—'}</p>
                    <p className="text-slate-500">Evaluación de la eficacia: {c.evaluacion}</p>
                  </div>
                ))}
              </div>
            )}

            {/* 6. Análisis de causa y 7. Causa raíz (consulta) */}
            {detalle.causa_raiz && detalle.estado !== 'en_analisis' && (
              <>
                <Seccion n="6" titulo={`Análisis de causa (5 porqués)${detalle.ciclo > 1 ? ` — ciclo ${detalle.ciclo}` : ''}`}>
                  {mismoAnalisisQueElCicloAnterior(detalle, 'porques') ? (
                    <p>Se revisó y se confirma el análisis del ciclo {detalle.ciclos_anteriores.slice(-1)[0].ciclo}.</p>
                  ) : detalle.porques?.length > 0 ? (
                    <ol className="list-inside list-decimal text-slate-500 dark:text-slate-400">
                      {detalle.porques.map(aPar).map((p, i) => (
                        <li key={i}>{p.pregunta && <strong className="text-slate-600 dark:text-slate-300">{p.pregunta} </strong>}{p.respuesta}</li>
                      ))}
                    </ol>
                  ) : <p>—</p>}
                </Seccion>
                <Seccion n="7" titulo={`Causa raíz${detalle.ciclo > 1 ? ` — ciclo ${detalle.ciclo}` : ''}`}>
                  {mismoAnalisisQueElCicloAnterior(detalle, 'causa_raiz')
                    ? <p>Se confirma la causa raíz del ciclo {detalle.ciclos_anteriores.slice(-1)[0].ciclo}: {detalle.causa_raiz}</p>
                    : <p className="whitespace-pre-wrap">{detalle.causa_raiz}</p>}
                </Seccion>
              </>
            )}

            {listaAcciones('correctiva', '8. Acciones correctivas')}

            {/* Aprobación del plan: el verificador se designa aquí; el botón va al final */}
            {detalle.estado === 'en_analisis' && tienePermiso('acciones_correctivas', 'aprobar') && (
              <div className="rounded-lg border border-esynapse-600/30 p-2">
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Verificador de eficacia (se designa al aprobar el plan)</label>
                <select className="input-esynapse" value={verificador} onChange={(e) => setVerificador(e.target.value)}>
                  <option value="">— Designar —</option>
                  {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
                </select>
              </div>
            )}

            {/* Verificación de eficacia */}
            {detalle.estado === 'en_verificacion' && (tienePermiso('acciones_correctivas', 'aprobar') || (usuario && detalle.verificador === usuario.id)) && (
              <div className="space-y-2 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3">
                <p className="text-xs font-semibold text-violet-600 dark:text-violet-400">Evaluación de la eficacia</p>
                <CampoAmpliable multilinea titulo="Evaluación de la eficacia" placeholder="¿Las acciones eliminaron la causa y previenen la recurrencia? Evidencias…"
                  value={eficaciaTxt} onChange={setEficaciaTxt} />
              </div>
            )}

            {/* Secciones 9 a 11 del formato (consulta) */}
            {(detalle.ciclos_anteriores?.length > 0 || detalle.fecha_verificacion) && (
              <Seccion n="9" titulo="Evaluación de la eficacia">
                <table className="tabla-ficha w-full text-xs">
                  <thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="py-1">Evaluación</th><th className="py-1 text-right">Fecha</th><th className="py-1">Responsable</th></tr></thead>
                  <tbody>
                    {(detalle.ciclos_anteriores || []).map((c) => (
                      <tr key={`c${c.ciclo}`} className="border-t border-slate-200 dark:border-slate-800">
                        <td className="py-1">(Ciclo {c.ciclo}, no eficaz) {c.evaluacion}</td><td className="py-1 text-right">{(c.fecha || '').slice(0, 10)}</td><td className="py-1">{c.verificado_por}</td>
                      </tr>
                    ))}
                    {detalle.estado === 'cerrada_conforme' && detalle.evaluacion_eficacia && (
                      <tr className="border-t border-slate-200 dark:border-slate-800">
                        <td className="py-1">{detalle.evaluacion_eficacia}</td><td className="py-1 text-right">{detalle.fecha_verificacion ? fecha(detalle.fecha_verificacion) : ''}</td><td className="py-1">{detalle.verificado_por_nombre}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </Seccion>
            )}
            {!['registrada', 'en_analisis'].includes(detalle.estado) && (
              <Seccion n="10" titulo="Actualizaciones y cambios">
                {/* Pregunta a la izquierda y respuesta en una columna fija, alineadas */}
                <div className="grid max-w-xl grid-cols-[1fr_auto] items-center gap-x-6 gap-y-1">
                  {[['¿Aplica cambios al SIG?', detalle.aplica_cambios_sig],
                    ['¿Aplica actualizar la matriz de riesgos y oportunidades?', detalle.aplica_actualizar_riesgos]].map(([pregunta, v]) => (
                    <div key={pregunta} className="contents">
                      <strong className="text-slate-700 dark:text-slate-200">{pregunta}</strong>
                      <span className="w-10 rounded border border-slate-300 py-0.5 text-center font-semibold dark:border-slate-600">{v == null ? '—' : v ? 'Sí' : 'No'}</span>
                    </div>
                  ))}
                </div>
              </Seccion>
            )}
            {detalle.estado.startsWith('cerrada') && (
              <Seccion n="11" titulo="Conformidad" tono="verde">
                <div className="grid grid-cols-3 gap-x-4">
                  <Dato etiqueta="Resultado" valor={detalle.estado === 'cerrada_conforme' ? 'Conforme' : 'Conforme (solo corrección)'} />
                  <Dato etiqueta="Fecha de cierre" valor={detalle.fecha_cierre ? fecha(detalle.fecha_cierre) : ''} />
                  <Dato etiqueta="Responsable" valor={detalle.responsable_cierre_nombre} />
                </div>
                {detalle.hallazgo_codigo && detalle.estado === 'cerrada_conforme' && (
                  <p className="mt-1 text-slate-500 dark:text-slate-400">{(detalle.hallazgos_vinculados || []).length > 1 ? `Los hallazgos ${detalle.hallazgos_vinculados.map((h) => h.codigo).join(', ')} se cerraron automáticamente.` : `El hallazgo ${detalle.hallazgo_codigo} fue cerrado automáticamente.`}</p>
                )}
              </Seccion>
            )}

            {/* Cierre de la etapa actual: al final de la ficha */}
            {etapaFinal && (
              <BarraEtapa titulo={etapaFinal.titulo} nota={etapaFinal.nota} bloqueo={etapaFinal.bloqueo} botones={etapaFinal.botones} />
            )}

            {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          </div>
        )}
      </Modal>
    </div>
  )
}
