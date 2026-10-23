import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { GraduationCap, Plus, Pencil, Trash2, Users, CalendarClock, Award, Layers, ClipboardList, FileText, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fechaHora } from '../lib/fecha.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'

// M12 — Competencia técnica y autorización del personal.
const FUNCIONES = [
  ['ejecutar', 'Ejecutar calibración'], ['supervisar', 'Supervisar'],
  ['informar', 'Informar resultados'], ['revisar', 'Revisar y autorizar resultados'],
  ['analizar', 'Analizar / opiniones e interpretaciones'], ['firmar', 'Firmar certificados'],
  ['operar', 'Operar equipos / manipular ítems'],
]
const IB = 'rounded p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'
const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400'
const nombrePersona = (u) => u ? (u.nombre_completo || `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username || u.email) : ''
const chipEstado = (e) => ({
  vigente: 'bg-green-500/15 text-green-600 dark:text-green-400',
  en_entrenamiento: 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
  suspendida: 'bg-red-500/15 text-red-600 dark:text-red-400',
  revocada: 'bg-slate-500/15 text-slate-500',
}[e] || 'bg-slate-500/15 text-slate-500')
const semaforo = (a) => {
  if (!a) return 'bg-slate-200 dark:bg-slate-700'
  if (a.estado === 'suspendida' || a.estado_seguimiento === 'vencido') return 'bg-red-500'
  if (a.estado === 'en_entrenamiento') return 'bg-violet-500'
  if (a.estado_seguimiento === 'por_vencer') return 'bg-amber-500'
  if (a.estado === 'vigente') return 'bg-green-500'
  return 'bg-slate-300'
}
const TABS = [
  ['matriz', 'Matriz', Layers], ['personal', 'Personal', Users],
  ['seguimiento', 'Seguimiento', CalendarClock], ['perfiles', 'Perfiles por puesto', Award],
]
const TABS_FICHA = [['entrenamiento', 'Entrenamiento'], ['supervision', 'Supervisión'], ['autorizaciones', 'Autorización'], ['seguimiento', 'Seguimiento']]

// Tabla de filas dinámicas reutilizable (soporta columnas de texto/fecha/número y de archivo).
// Conformidad de cada ítem: valores antiguos escritos a mano se leen como Conforme / No conforme.
function normalizarConformidad(v) {
  const t = String(v || '').trim().toUpperCase().replace(/\.$/, '')
  if (!t) return ''
  if (t === 'CONFORME') return 'CONFORME'
  if (t.startsWith('NO')) return 'NO CONFORME'
  return ''
}

const NOTA_MINIMA = 14

// Lo que falta para dar por superado un entrenamiento (mismas reglas que el servidor).
function faltantesEntrenamiento(r) {
  const falta = []
  const acts = (r.checklist_entrenamiento || []).filter((a) => String(a.actividad || '').trim())
  if (!acts.length || !acts.every((a) => normalizarConformidad(a.conformidad) === 'CONFORME')) falta.push('todas las actividades de entrenamiento conformes')
  if (!r.tutor_supervision) falta.push('el tutor del trabajo bajo supervisión')
  const items = (r.checklist_supervision || []).filter((x) => String(x.item || '').trim())
  if (!items.length || !items.every((x) => normalizarConformidad(x.conformidad) === 'CONFORME')) falta.push('todos los ítems de supervisión conformes')
  if (r.nota_teorica === '' || r.nota_teorica == null || Number(r.nota_teorica) < NOTA_MINIMA) falta.push(`nota teórica de ${NOTA_MINIMA} o más`)
  if (!r.control_validez || r.resultado_control !== 'satisfactorio') falta.push('un control de validez satisfactorio')
  return falta
}

// Totales de la entrevista con las fórmulas del formato (el servidor los recalcula al guardar).
function calcularPuntajes(preguntas, porPregunta) {
  const filas = (preguntas || []).map((p) => ({ est: Number(p.establecido) || 0, obt: Number(p.obtenido) || 0 }))
  if (!filas.length) return null
  const pp = porPregunta === '' || porPregunta == null ? Math.max(...filas.map((f) => f.est)) : Number(porPregunta)
  const total = Math.round(filas.reduce((s, f) => s + f.obt, 0) * 100) / 100
  const maximo = Math.round(pp * filas.length * 100) / 100
  const minimo = Math.round(maximo * 0.7 * 100) / 100
  // Sin puntajes establecidos aún no hay resultado que calcular.
  const resultado = maximo > 0 ? (total >= minimo && total <= maximo ? 'satisfactorio' : 'no_satisfactorio') : null
  return { n: filas.length, total, maximo, minimo, resultado }
}

function esGerenteTecnico(u) {
  return String(u?.cargo || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().includes('gerente tecnico')
}

function TablaFilas({ columnas, filas, onChange, nueva, onSubirArchivo }) {
  const [subiendo, setSubiendo] = useState(null)
  const set = (i, k, v) => onChange(filas.map((f, j) => (j === i ? { ...f, [k]: v } : f)))
  const subir = async (i, file) => {
    if (!file || !onSubirArchivo) return
    setSubiendo(i)
    try {
      const r = await onSubirArchivo(file)
      onChange(filas.map((f, j) => (j === i ? { ...f, adjunto: r.url, adjunto_nombre: r.nombre } : f)))
    } finally { setSubiendo(null) }
  }
  return (
    <div className="space-y-1">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-xs text-slate-500 dark:text-slate-400">
            {columnas.map((c) => <th key={c.k} className="px-1 py-0.5">{c.label}</th>)}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={i}>
              {columnas.map((c) => (
                <td key={c.k} className="px-0.5 py-0.5">
                  {c.tipo === 'file' ? (
                    <div className="flex items-center gap-1">
                      {f.adjunto && <a href={f.adjunto} target="_blank" rel="noreferrer" className="max-w-[90px] truncate text-esynapse-600 dark:text-esynapse-300" title={f.adjunto_nombre}>{f.adjunto_nombre || 'ver'}</a>}
                      <label className="cursor-pointer whitespace-nowrap rounded border border-slate-300 px-1.5 py-1 text-[11px] text-slate-500 hover:text-esynapse-600 dark:border-slate-600">
                        {subiendo === i ? '…' : (f.adjunto ? 'cambiar' : 'adjuntar')}
                        <input type="file" className="hidden" onChange={(e) => e.target.files[0] && subir(i, e.target.files[0])} />
                      </label>
                    </div>
                  ) : c.tipo === 'conformidad' ? (
                    <select className={`${inp} px-1 py-1 text-xs`} value={normalizarConformidad(f[c.k])} onChange={(e) => set(i, c.k, e.target.value)}>
                      <option value="">—</option><option value="CONFORME">Conforme</option><option value="NO CONFORME">No conforme</option>
                    </select>
                  ) : (
                    <input type={c.tipo || 'text'} className={`${inp} px-1 py-1 text-xs`} value={f[c.k] ?? ''} onChange={(e) => set(i, c.k, e.target.value)} />
                  )}
                </td>
              ))}
              <td><button onClick={() => onChange(filas.filter((_, j) => j !== i))} className="text-red-500"><X className="h-3.5 w-3.5" /></button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <button onClick={() => onChange([...filas, nueva()])} className="btn-secondary !py-1 text-xs"><Plus className="h-3.5 w-3.5" /> Agregar fila</button>
    </div>
  )
}

export default function Competencia() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const puedeEditar = tienePermiso('competencia_tecnica', 'editar')
  const puedeAprobar = tienePermiso('competencia_tecnica', 'aprobar')
  const [vista, setVista] = useState(() => localStorage.getItem('competencia_vista') || 'matriz')
  useEffect(() => { localStorage.setItem('competencia_vista', vista) }, [vista])
  const [error, setError] = useState('')
  const [pendientes, setPendientes] = useState([]); const [modalPend, setModalPend] = useState(false)
  const [misSolic, setMisSolic] = useState([]); const [modalMis, setModalMis] = useState(false); const [misDevueltas, setMisDevueltas] = useState(0)

  const [personas, setPersonas] = useState([])
  const [metodos, setMetodos] = useState([])
  const [controles, setControles] = useState([])
  const [autorizaciones, setAutorizaciones] = useState([])
  const [perfiles, setPerfiles] = useState([])
  const [porVencer, setPorVencer] = useState([])

  const [ficha, setFicha] = useState(null)
  const [tabFicha, setTabFicha] = useState('entrenamiento')
  const [entrenamientos, setEntrenamientos] = useState([])
  const [seguimientos, setSeguimientos] = useState([])

  const [modalCat, setModalCat] = useState(false)
  const [modalAut, setModalAut] = useState(false); const [formAut, setFormAut] = useState(null)
  const [modalEnt, setModalEnt] = useState(false); const [formEnt, setFormEnt] = useState(null)
  const [modalSup, setModalSup] = useState(false); const [formSup, setFormSup] = useState(null)
  const [modalSeg, setModalSeg] = useState(false); const [formSeg, setFormSeg] = useState(null)

  const cargarBase = async () => {
    try {
      const [u, m, c, a] = await Promise.all([
        api.usuarios.listar(), api.metodosCalibracion.listar(), api.controlesValidez.listar(), api.autorizaciones.listar(),
      ])
      setPersonas((u.results ?? u).filter((x) => x.is_active !== false))
      setMetodos(m.results ?? m); setControles(c.results ?? c); setAutorizaciones(a.results ?? a)
    } catch (e) { setError(e.message) }
  }
  useEffect(() => { cargarBase() }, [])
  useEffect(() => { if (vista === 'seguimiento') api.autorizaciones.seguimientos().then(setPorVencer).catch(() => {}) }, [vista])
  useEffect(() => { if (vista === 'perfiles') api.org.puestos('?tipo=propio').then(setPerfiles).catch(() => {}) }, [vista])
  const [laboratorios, setLaboratorios] = useState([])
  useEffect(() => { api.org.areas('?tipo=laboratorio').then(setLaboratorios).catch(() => {}) }, [])

  const autDe = (uid, mid) => autorizaciones.find((a) => a.usuario === uid && a.metodo === mid)
  const autsDe = (uid) => autorizaciones.filter((a) => a.usuario === uid)

  const abrirFicha = async (u) => {
    setFicha(u); setTabFicha('entrenamiento'); setError('')
    try {
      const [e, s] = await Promise.all([api.procesosEntrenamiento.listar(`?usuario=${u.id}`), api.evaluacionesSeguimiento.listar(`?usuario=${u.id}`)])
      setEntrenamientos(e.results ?? e); setSeguimientos(s.results ?? s)
    } catch (err) { setError(err.message) }
  }
  const refrescarFicha = async () => {
    await cargarBase()
    if (ficha) {
      const [e, s] = await Promise.all([api.procesosEntrenamiento.listar(`?usuario=${ficha.id}`), api.evaluacionesSeguimiento.listar(`?usuario=${ficha.id}`)])
      setEntrenamientos(e.results ?? e); setSeguimientos(s.results ?? s)
    }
  }

  const abrirPdf = async (blobPromise) => {
    setError('')
    try { const b = await blobPromise; const url = URL.createObjectURL(b); window.open(url, '_blank'); setTimeout(() => URL.revokeObjectURL(url), 60000) }
    catch (e) { setError(e.message) }
  }

  const cargarPendientes = () => { if (!puedeAprobar) return; api.solicitudesCompetencia.listar('?estado=pendiente').then((d) => setPendientes(d.results ?? d)).catch(() => {}) }
  const cargarMis = () => {
    api.solicitudesCompetencia.listar('?estado=todas&mias=1').then((d) => setMisSolic(d.results ?? d)).catch(() => {})
    api.solicitudesCompetencia.misDevueltasCount().then((d) => setMisDevueltas(d.devueltas || 0)).catch(() => {})
  }
  useEffect(() => { cargarPendientes(); cargarMis() }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  const avisoPendiente = async (resp) => {
    if (resp?.pendiente) {
      cargarPendientes()
      await confirmar({ titulo: 'Cambio pendiente de aprobación', mensaje: resp.detail || 'El cambio quedó pendiente de aprobación por un supervisor.', textoConfirmar: 'Entendido', textoCancelar: 'Cerrar' })
      return true
    }
    return false
  }
  const resolver = async (s, tipo) => {
    let obs = ''
    if (tipo === 'aprobar') { if (!await confirmar({ titulo: 'Aprobar cambio', mensaje: `¿Aprobar "${s.resumen}" de ${s.solicitante}?`, textoConfirmar: 'Aprobar' })) return }
    else {
      obs = await confirmar({
        titulo: tipo === 'devolver' ? 'Devolver para corrección' : 'Rechazar cambio',
        mensaje: `"${s.resumen}" — solicitado por ${s.solicitante}.`,
        textoConfirmar: tipo === 'devolver' ? 'Devolver' : 'Rechazar', peligro: tipo === 'rechazar',
        entrada: { etiqueta: tipo === 'devolver' ? 'Qué debe corregir' : 'Motivo del rechazo', multilinea: true, obligatorio: tipo === 'devolver' },
      })
      if (obs === null) return
    }
    try {
      if (tipo === 'aprobar') await api.solicitudesCompetencia.aprobar(s.id)
      else if (tipo === 'devolver') await api.solicitudesCompetencia.devolver(s.id, obs)
      else await api.solicitudesCompetencia.rechazar(s.id, obs)
      cargarPendientes(); await refrescarFicha()
    } catch (e) { setError(e.message) }
  }
  const reenviar = async (s) => {
    if (!await confirmar({ titulo: 'Reenviar', mensaje: `¿Reenviar "${s.resumen}" para aprobación?`, textoConfirmar: 'Reenviar' })) return
    try { await api.solicitudesCompetencia.reenviar(s.id); cargarMis(); cargarPendientes() } catch (e) { setError(e.message) }
  }

  // --- Autorización ---
  const nuevaAut = () => { setFormAut({ usuario: ficha.id, metodo: '', funciones: [], alcance_firma: '', laboratorio: '', fecha_autorizacion: '', estado: 'en_entrenamiento', frecuencia_seguimiento_meses: 12, observaciones: '', exento_entrenamiento: false, sustento_exencion: '' }); setModalAut(true) }
  const editarAut = (a) => { setFormAut({ ...a, metodo: a.metodo || '', funciones: a.funciones || [] }); setModalAut(true) }
  const toggleFuncion = (k) => setFormAut((f) => ({ ...f, funciones: f.funciones.includes(k) ? f.funciones.filter((x) => x !== k) : [...f.funciones, k] }))
  const guardarAut = async () => {
    const body = { ...formAut, metodo: formAut.metodo || null, fecha_autorizacion: formAut.fecha_autorizacion || null }
    try { const r = formAut.id ? await api.autorizaciones.editar(formAut.id, body) : await api.autorizaciones.crear(body); setModalAut(false); await avisoPendiente(r); await refrescarFicha() }
    catch (e) { setError(e.message) }
  }
  const eliminarAut = async (a) => { if (!await confirmar({ titulo: 'Eliminar autorización', mensaje: '¿Eliminar esta autorización?', textoConfirmar: 'Eliminar', peligro: true })) return; try { await api.autorizaciones.eliminar(a.id); await refrescarFicha() } catch (e) { setError(e.message) } }

  // --- Entrenamiento (sección 1) ---
  const nuevoEnt = () => { setFormEnt({ usuario: ficha.id, metodo: '', tipo: 'entrenamiento', tutor: '', checklist_entrenamiento: [], estado: 'en_proceso', checklist_supervision: [] }); setModalEnt(true) }
  const editarEnt = (r) => { setFormEnt({ ...r, metodo: r.metodo || '', tutor: r.tutor || '', checklist_entrenamiento: r.checklist_entrenamiento || [] }); setModalEnt(true) }
  const guardarEnt = async () => {
    const b = { usuario: formEnt.usuario, metodo: formEnt.metodo || null, tipo: formEnt.tipo, tutor: formEnt.tutor || null, checklist_entrenamiento: formEnt.checklist_entrenamiento || [] }
    try { const r = formEnt.id ? await api.procesosEntrenamiento.editar(formEnt.id, b) : await api.procesosEntrenamiento.crear(b); setModalEnt(false); await avisoPendiente(r); await refrescarFicha() }
    catch (e) { setError(e.message) }
  }
  const eliminarEnt = async (r) => { if (!await confirmar({ titulo: 'Eliminar', mensaje: '¿Eliminar este proceso?', textoConfirmar: 'Eliminar', peligro: true })) return; try { await api.procesosEntrenamiento.eliminar(r.id); await refrescarFicha() } catch (e) { setError(e.message) } }

  // --- Supervisión (sección 2 del mismo proceso) ---
  const editarSup = (r) => {
    setFormSup({
      id: r.id, tutor_supervision: r.tutor_supervision || '', periodo_supervision_dias: r.periodo_supervision_dias ?? '',
      fecha_inicio_supervision: r.fecha_inicio_supervision || '', checklist_supervision: r.checklist_supervision || [],
      nota_teorica: r.nota_teorica ?? '', control_validez: r.control_validez || '', resultado_control: r.resultado_control || '',
      estado: r.estado || 'en_proceso', comentarios: r.comentarios || '',
    })
    setModalSup(true)
  }
  // Guardar no cambia el estado: el entrenamiento se concluye con la barra final
  // («Dar por superado» o «No conforme»), con confirmación.
  const guardarSup = async (estado) => {
    const b = { ...formSup }
    b.tutor_supervision = b.tutor_supervision || null; b.control_validez = b.control_validez || null
    ;['periodo_supervision_dias', 'nota_teorica'].forEach((k) => { if (b[k] === '') b[k] = null })
    if (!b.fecha_inicio_supervision) b.fecha_inicio_supervision = null
    b.estado = estado || 'en_proceso'
    try { const r = await api.procesosEntrenamiento.editar(formSup.id, b); setModalSup(false); await avisoPendiente(r); await refrescarFicha() } catch (e) { setError(e.message) }
  }
  const concluirSup = async (estado) => {
    const superado = estado === 'completado'
    if (!await confirmar({ titulo: superado ? 'Dar por superado el entrenamiento' : 'Concluir como no conforme', peligro: !superado,
      textoConfirmar: superado ? 'Dar por superado' : 'No conforme',
      mensaje: superado
        ? 'El entrenamiento y el trabajo bajo supervisión quedan concluidos y de solo lectura. Con esto la persona puede ser autorizada en el método.'
        : 'El entrenamiento queda concluido como no conforme y de solo lectura. Para un nuevo intento se registra un re-entrenamiento.' })) return
    await guardarSup(estado)
  }

  // --- Seguimiento ---
  const nuevoSeg = () => { setFormSeg({ usuario: ficha.id, autorizacion: '', evaluador: '', tema: '', fecha: '', hora: '', area: '', tipo: 'entrevista', control_validez: '', preguntas: [], puntaje_minimo: '', puntaje_por_pregunta: '', resultado: '', decision: '', conclusiones: '', observaciones: '' }); setModalSeg(true) }
  const guardarSeg = async () => {
    // Solo se envían los puntajes de cada pregunta: totales y resultado los calcula el servidor.
    const preg = (formSeg.preguntas || []).map((p) => ({ n: Number(p.n) || 0, establecido: Number(p.establecido) || 0, obtenido: Number(p.obtenido) || 0 }))
    const b = {
      usuario: formSeg.usuario, autorizacion: formSeg.autorizacion || null, evaluador: formSeg.evaluador || null,
      tema: formSeg.tema, fecha: formSeg.fecha || null, hora: formSeg.hora, area: formSeg.area, tipo: formSeg.tipo,
      control_validez: formSeg.control_validez || null, preguntas: preg,
      puntaje_por_pregunta: formSeg.puntaje_por_pregunta === '' ? null : Number(formSeg.puntaje_por_pregunta),
      resultado: formSeg.resultado, decision: formSeg.decision, conclusiones: formSeg.conclusiones, observaciones: formSeg.observaciones,
    }
    try { const r = formSeg.id ? await api.evaluacionesSeguimiento.editar(formSeg.id, b) : await api.evaluacionesSeguimiento.crear(b); setModalSeg(false); await avisoPendiente(r); await refrescarFicha() }
    catch (e) { setError(e.message) }
  }
  const eliminarSeg = async (r) => { if (!await confirmar({ titulo: 'Eliminar', mensaje: '¿Eliminar este seguimiento?', textoConfirmar: 'Eliminar', peligro: true })) return; try { await api.evaluacionesSeguimiento.eliminar(r.id); await refrescarFicha() } catch (e) { setError(e.message) } }


  const nombreMetodo = (id) => { const m = metodos.find((x) => x.id === id); return m ? `${m.codigo ? m.codigo + ' · ' : ''}${m.nombre}` : '' }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <TituloModulo seccion="Laboratorio" titulo="Competencia técnica" descripcion="Autorizaciones del personal por método, entrenamiento y seguimiento de la competencia." />
        <div className="flex flex-wrap items-center gap-2">
          {puedeAprobar && (
            <button onClick={() => { cargarPendientes(); setModalPend(true) }} className="btn-secondary">Cambios pendientes
              {pendientes.length > 0 && <span className="ml-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-amber-500 px-1 text-xs font-semibold text-white">{pendientes.length}</span>}
            </button>
          )}
          {puedeEditar && (
            <button onClick={() => { cargarMis(); setModalMis(true) }} className="btn-secondary">Mis solicitudes
              {misDevueltas > 0 && <span className="ml-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-violet-500 px-1 text-xs font-semibold text-white">{misDevueltas}</span>}
            </button>
          )}
          {puedeEditar && <button onClick={() => setModalCat(true)} className="btn-secondary"><ClipboardList className="h-4 w-4" /> Catálogos</button>}
        </div>
      </div>
      {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="flex flex-wrap items-center gap-1 border-b border-slate-200 dark:border-slate-800">
        {TABS.map(([k, txt, Icon]) => (
          <button key={k} onClick={() => setVista(k)} className={`-mb-px inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition ${vista === k ? 'border-esynapse-500 text-esynapse-600 dark:text-esynapse-300' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'}`}>
            <Icon className="h-4 w-4" /> {txt}
          </button>
        ))}
      </div>

      {vista === 'matriz' && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/60">
                <th className="sticky left-0 z-10 bg-slate-50 px-3 py-2 text-left font-semibold dark:bg-slate-800/60">Personal</th>
                {metodos.map((m) => <th key={m.id} className="px-2 py-2 text-center font-medium" title={m.nombre}>{m.codigo || m.nombre}</th>)}
              </tr>
            </thead>
            <tbody>
              {personas.map((u) => (
                <tr key={u.id} className="border-t border-slate-100 dark:border-slate-800/60">
                  <td className="sticky left-0 z-10 bg-white px-3 py-1.5 font-medium dark:bg-slate-900">
                    <button onClick={() => abrirFicha(u)} className="hover:text-esynapse-600 dark:hover:text-esynapse-300">{nombrePersona(u)}</button>
                  </td>
                  {metodos.map((m) => { const a = autDe(u.id, m.id); return <td key={m.id} className="px-2 py-1.5 text-center"><span className={`inline-block h-3 w-3 rounded-full ${semaforo(a)}`} title={a ? a.estado_display : 'Sin autorización'} /></td> })}
                  {metodos.length === 0 && <td className="px-2 py-1.5 text-center text-slate-400">Agrega métodos en Catálogos</td>}
                </tr>
              ))}
              {personas.length === 0 && <tr><td className="px-3 py-4 text-center text-slate-400" colSpan={metodos.length + 1}>Sin personal.</td></tr>}
            </tbody>
          </table>
          <div className="flex flex-wrap gap-4 border-t border-slate-100 px-3 py-2 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400">
            <span><span className="mr-1 inline-block h-3 w-3 rounded-full bg-green-500 align-middle" />Vigente</span>
            <span><span className="mr-1 inline-block h-3 w-3 rounded-full bg-violet-500 align-middle" />En entrenamiento</span>
            <span><span className="mr-1 inline-block h-3 w-3 rounded-full bg-amber-500 align-middle" />Seguimiento por vencer</span>
            <span><span className="mr-1 inline-block h-3 w-3 rounded-full bg-red-500 align-middle" />Suspendida / vencida</span>
            <span><span className="mr-1 inline-block h-3 w-3 rounded-full bg-slate-300 align-middle" />Sin autorización</span>
          </div>
        </div>
      )}

      {vista === 'personal' && (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {personas.map((u) => {
            const auts = autsDe(u.id); const vig = auts.filter((a) => a.estado === 'vigente').length
            return (
              <button key={u.id} onClick={() => abrirFicha(u)} className="card-esynapse p-4 text-left transition hover:ring-2 hover:ring-esynapse-500/30">
                <p className="text-sm font-semibold">{nombrePersona(u)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{u.cargo || '—'}{u.laboratorio ? ` · ${u.laboratorio}` : ''}</p>
                <p className="mt-2 text-xs"><span className="font-semibold text-esynapse-600 dark:text-esynapse-300">{vig}</span> autorización(es) vigente(s) · {auts.length} total</p>
              </button>
            )
          })}
        </div>
      )}

      {vista === 'seguimiento' && (
        <div className="space-y-2">
          {porVencer.length === 0 && <p className="py-8 text-center text-sm text-slate-400">No hay seguimientos por vencer ni vencidos.</p>}
          {porVencer.map((a) => (
            <div key={a.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <div><p className="text-sm font-medium">{a.usuario_nombre} · {a.metodo_nombre || 'General'}</p><p className="text-xs text-slate-500 dark:text-slate-400">Próximo seguimiento: {a.fecha_proximo_seguimiento || '—'}</p></div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${a.estado_seguimiento === 'vencido' ? 'bg-red-500/15 text-red-600 dark:text-red-400' : 'bg-amber-500/15 text-amber-600 dark:text-amber-400'}`}>{a.estado_seguimiento === 'vencido' ? 'Vencido' : 'Por vencer'}</span>
            </div>
          ))}
        </div>
      )}

      {vista === 'perfiles' && (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">El perfil de cada puesto (requisitos de competencia del manual de funciones) se mantiene en <Link to="/organizacion" className="text-esynapse-500 underline">Organización y personal</Link> → Puestos. Aquí se consulta para verificar la competencia del personal.</p>
          <div className="grid gap-3 md:grid-cols-2">
            {perfiles.map((p) => (
              <div key={p.id} className="card-esynapse space-y-1 p-4">
                <div className="flex items-center justify-between"><h3 className="text-sm font-semibold">{p.nombre}{p.sigla ? <span className="ml-1 font-mono text-xs text-slate-400">{p.sigla}</span> : null}</h3><span className="text-[11px] text-slate-400">{p.tiene_perfil ? `Versión ${p.version_perfil}` : 'Sin perfil registrado'}</span></div>
                {p.educacion && <p className="text-xs"><span className="font-medium">Educación:</span> {p.educacion}</p>}
                {p.formacion && <p className="text-xs"><span className="font-medium">Formación:</span> {p.formacion}</p>}
                {p.experiencia && <p className="text-xs"><span className="font-medium">Experiencia:</span> {p.experiencia}</p>}
                {p.habilidades && <p className="text-xs"><span className="font-medium">Habilidades:</span> {p.habilidades}</p>}
                {p.responsabilidades && <p className="whitespace-pre-wrap text-xs"><span className="font-medium">Funciones:</span> {p.responsabilidades}</p>}
              </div>
            ))}
            {perfiles.length === 0 && <p className="py-6 text-center text-sm text-slate-400">Sin puestos registrados.</p>}
          </div>
        </div>
      )}

      {/* ===== FICHA ===== */}
      <Modal abierto={!!ficha} titulo={ficha ? `Competencia — ${nombrePersona(ficha)}` : ''} onCerrar={() => setFicha(null)} panel ancho="max-w-4xl">
        {ficha && (
          <div className="space-y-3">
            <div className="flex items-center gap-1 border-b border-slate-200 dark:border-slate-800">
              {TABS_FICHA.map(([k, t]) => (
                <button key={k} onClick={() => setTabFicha(k)} className={`-mb-px border-b-2 px-3 py-1.5 text-sm font-medium ${tabFicha === k ? 'border-esynapse-500 text-esynapse-600 dark:text-esynapse-300' : 'border-transparent text-slate-500'}`}>{t}</button>
              ))}
            </div>

            {(tabFicha === 'entrenamiento' || tabFicha === 'supervision') && (
              <div className="space-y-2">
                {tabFicha === 'entrenamiento' && puedeEditar && <button onClick={nuevoEnt} className="btn-primary !py-1"><Plus className="h-4 w-4" /> Nuevo proceso</button>}
                {tabFicha === 'supervision' && <p className="text-xs text-slate-400">Los procesos se crean en "Entrenamiento"; aquí registras el trabajo bajo supervisión de cada uno.</p>}
                {entrenamientos.map((r) => (
                  <div key={r.id} className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                    <div>
                      <p className="text-sm font-medium">{r.metodo_nombre || nombreMetodo(r.metodo) || 'General'} · {r.tipo_display} <span className={`ml-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${r.estado === 'completado' ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : r.estado === 'no_conforme' ? 'bg-red-500/15 text-red-600 dark:text-red-400' : 'bg-blue-500/15 text-blue-600 dark:text-blue-400'}`}>{r.estado_display}</span></p>
                      {tabFicha === 'entrenamiento'
                        ? <p className="text-xs text-slate-500 dark:text-slate-400">Tutor: {r.tutor_nombre || '—'} · {(r.checklist_entrenamiento || []).length} actividad(es)</p>
                        : <p className="text-xs text-slate-500 dark:text-slate-400">Tutor: {r.tutor_supervision_nombre || '—'} · Periodo: {r.periodo_supervision_dias ?? '—'} d · {(r.checklist_supervision || []).length} ítem(s) · {r.estado_display}</p>}
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button onClick={() => abrirPdf(api.procesosEntrenamiento.pdf(r.id))} className={IB} title="PDF del entrenamiento y supervisión"><FileText className="h-4 w-4" /></button>
                      {puedeEditar && r.estado === 'en_proceso' && <button onClick={() => (tabFicha === 'entrenamiento' ? editarEnt(r) : editarSup(r))} className={IB} title="Editar"><Pencil className="h-4 w-4" /></button>}
                      {puedeEditar && r.estado === 'en_proceso' && tabFicha === 'entrenamiento' && <button onClick={() => eliminarEnt(r)} className={`${IB} text-red-500`} title="Eliminar"><Trash2 className="h-4 w-4" /></button>}
                    </div>
                  </div>
                ))}
                {entrenamientos.length === 0 && <p className="py-4 text-center text-xs text-slate-400">Sin procesos de entrenamiento.</p>}
              </div>
            )}

            {tabFicha === 'autorizaciones' && (
              <div className="space-y-2">
                {puedeEditar && <button onClick={nuevaAut} className="btn-primary !py-1"><Plus className="h-4 w-4" /> Nueva autorización</button>}
                {autsDe(ficha.id).map((a) => (
                  <div key={a.id} className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                    <div>
                      <p className="text-sm font-medium">{a.metodo_nombre || 'General'} <span className={`ml-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${chipEstado(a.estado)}`}>{a.estado_display}</span></p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{(a.funciones_display || []).join(' · ')}</p>
                      <p className="text-[11px] text-slate-400">Próximo seguimiento: {a.fecha_proximo_seguimiento || '—'}</p>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button onClick={() => abrirPdf(api.autorizaciones.pdf(a.id))} className={IB} title="Carta de autorización (PDF)"><FileText className="h-4 w-4" /></button>
                      {puedeEditar && <button onClick={() => editarAut(a)} className={IB}><Pencil className="h-4 w-4" /></button>}
                      {puedeEditar && <button onClick={() => eliminarAut(a)} className={`${IB} text-red-500`}><Trash2 className="h-4 w-4" /></button>}
                    </div>
                  </div>
                ))}
                {autsDe(ficha.id).length === 0 && <p className="py-4 text-center text-xs text-slate-400">Sin autorizaciones.</p>}
              </div>
            )}

            {tabFicha === 'seguimiento' && (
              <div className="space-y-2">
                {puedeEditar && <button onClick={nuevoSeg} className="btn-primary !py-1"><Plus className="h-4 w-4" /> Nuevo seguimiento</button>}
                {seguimientos.map((r) => (
                  <div key={r.id} className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                    <div>
                      <p className="text-sm font-medium">{r.tipo_display} · {r.fecha || '—'}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{r.tema || ''} {r.resultado_display ? `· ${r.resultado_display}` : ''} {r.decision_display ? `· ${r.decision_display}` : ''}</p>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button onClick={() => abrirPdf(api.evaluacionesSeguimiento.pdf(r.id))} className={IB} title="PDF de la entrevista de seguimiento"><FileText className="h-4 w-4" /></button>
                      {puedeEditar && <button onClick={() => eliminarSeg(r)} className={`${IB} text-red-500`}><Trash2 className="h-4 w-4" /></button>}
                    </div>
                  </div>
                ))}
                {seguimientos.length === 0 && <p className="py-4 text-center text-xs text-slate-400">Sin seguimientos.</p>}
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* ===== MODAL AUTORIZACIÓN ===== */}
      <Modal abierto={modalAut} titulo={formAut?.id ? 'Editar autorización' : 'Nueva autorización'} onCerrar={() => setModalAut(false)} ancho="max-w-lg">
        {formAut && (
          <div className="space-y-3">
            <label className="block"><span className={lbl}>Método</span>
              <select className={inp} value={formAut.metodo} onChange={(e) => setFormAut({ ...formAut, metodo: e.target.value })}>
                <option value="">General (sin método)</option>{metodos.map((m) => <option key={m.id} value={m.id}>{m.codigo ? `${m.codigo} · ` : ''}{m.nombre}</option>)}
              </select></label>
            <div><span className={lbl}>Funciones autorizadas</span>
              <div className="grid grid-cols-2 gap-1">{FUNCIONES.map(([k, t]) => <label key={k} className="flex items-center gap-2 text-xs"><input type="checkbox" checked={formAut.funciones.includes(k)} onChange={() => toggleFuncion(k)} /> {t}</label>)}</div>
            </div>
            {formAut.funciones.includes('firmar') && (
              <div className="grid grid-cols-2 gap-3">
                <label className="block"><span className={lbl}>Alcance de firma</span><select className={inp} value={formAut.alcance_firma} onChange={(e) => setFormAut({ ...formAut, alcance_firma: e.target.value })}><option value="">—</option><option value="todos">Todos los laboratorios</option><option value="laboratorio">Un laboratorio</option></select></label>
                {formAut.alcance_firma === 'laboratorio' && <label className="block"><span className={lbl}>Laboratorio</span><select className={inp} value={formAut.laboratorio} onChange={(e) => setFormAut({ ...formAut, laboratorio: e.target.value })}><option value="">— Elegir —</option>{formAut.laboratorio && !laboratorios.some((l) => l.nombre === formAut.laboratorio) && <option value={formAut.laboratorio}>{formAut.laboratorio}</option>}{laboratorios.map((l) => <option key={l.id} value={l.nombre}>{l.nombre}</option>)}</select></label>}
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <label className="block"><span className={lbl}>Fecha de autorización</span><input type="date" className={inp} value={formAut.fecha_autorizacion || ''} onChange={(e) => setFormAut({ ...formAut, fecha_autorizacion: e.target.value })} /></label>
              <label className="block"><span className={lbl}>Estado</span><select className={inp} value={formAut.estado} onChange={(e) => setFormAut({ ...formAut, estado: e.target.value })}><option value="en_entrenamiento">En entrenamiento</option><option value="vigente">Vigente</option><option value="suspendida">Suspendida</option><option value="revocada">Revocada</option></select></label>
              <label className="block"><span className={lbl}>Frecuencia de seguimiento (meses)</span><input type="number" className={inp} value={formAut.frecuencia_seguimiento_meses} onChange={(e) => setFormAut({ ...formAut, frecuencia_seguimiento_meses: e.target.value })} /></label>
            </div>
            <label className="block"><span className={lbl}>Observaciones</span><textarea className={inp} rows={2} value={formAut.observaciones} onChange={(e) => setFormAut({ ...formAut, observaciones: e.target.value })} /></label>
            {esGerenteTecnico(ficha) && (
              <div className="space-y-2 rounded-md border border-slate-200 p-2 dark:border-slate-700">
                <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={!!formAut.exento_entrenamiento} onChange={(e) => setFormAut({ ...formAut, exento_entrenamiento: e.target.checked })} /> Eximido del entrenamiento y del trabajo bajo supervisión (Gerente Técnico)</label>
                {formAut.exento_entrenamiento && <CampoAmpliable multilinea rows={2} titulo="Sustento de la exención" placeholder="Formación académica, experiencia, conocimientos técnicos y desempeño previo (p. ej. ensayos de aptitud)" value={formAut.sustento_exencion} onChange={(v) => setFormAut({ ...formAut, sustento_exencion: v })} />}
              </div>
            )}
            {formAut.metodo && formAut.estado === 'vigente' && !formAut.exento_entrenamiento && (() => {
              const superado = entrenamientos.some((r) => String(r.metodo) === String(formAut.metodo) && r.estado === 'completado')
              return superado
                ? <p className="rounded-md bg-emerald-500/10 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-300">Tiene un entrenamiento superado en este método.</p>
                : <p className="rounded-md bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">Sin un entrenamiento superado en este método no puede quedar vigente: regístrelo «En entrenamiento» hasta concluirlo.</p>
            })()}
            <div className="flex justify-end gap-2"><button onClick={() => setModalAut(false)} className="btn-secondary">Cancelar</button><button onClick={guardarAut} className="btn-primary">Guardar</button></div>
          </div>
        )}
      </Modal>

      {/* ===== MODAL ENTRENAMIENTO (sección 1) ===== */}
      <Modal abierto={modalEnt} titulo={formEnt?.id ? 'Editar entrenamiento' : 'Nuevo entrenamiento'} onCerrar={() => setModalEnt(false)} ancho="max-w-2xl">
        {formEnt && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <label className="block"><span className={lbl}>Método</span><select className={inp} value={formEnt.metodo} onChange={(e) => setFormEnt({ ...formEnt, metodo: e.target.value })}><option value="">—</option>{metodos.map((m) => <option key={m.id} value={m.id}>{m.codigo ? `${m.codigo} · ` : ''}{m.nombre}</option>)}</select></label>
              <label className="block"><span className={lbl}>Tipo</span><select className={inp} value={formEnt.tipo} onChange={(e) => setFormEnt({ ...formEnt, tipo: e.target.value })}><option value="entrenamiento">Entrenamiento</option><option value="reentrenamiento">Re-entrenamiento</option></select></label>
              <label className="block"><span className={lbl}>Tutor</span><select className={inp} value={formEnt.tutor} onChange={(e) => setFormEnt({ ...formEnt, tutor: e.target.value })}><option value="">—</option>{personas.map((p) => <option key={p.id} value={p.id}>{nombrePersona(p)}</option>)}</select></label>
            </div>
            <div><span className={lbl}>Actividades de entrenamiento</span>
              <TablaFilas columnas={[{ k: 'actividad', label: 'Actividad' }, { k: 'documento', label: 'Documento' }, { k: 'fecha_inicio', label: 'Fecha inicio', tipo: 'date' }, { k: 'conformidad', label: 'Conformidad', tipo: 'conformidad' }, { k: 'adjunto', label: 'Documento adjunto', tipo: 'file' }]}
                filas={formEnt.checklist_entrenamiento} onChange={(f) => setFormEnt({ ...formEnt, checklist_entrenamiento: f })}
                nueva={() => ({ actividad: '', documento: '', fecha_inicio: '', conformidad: '', adjunto: '', adjunto_nombre: '' })}
                onSubirArchivo={async (file) => { const fd = new FormData(); fd.append('archivo', file); return api.procesosEntrenamiento.subirAdjunto(fd) }} />
            </div>
            <div className="flex justify-end gap-2"><button onClick={() => setModalEnt(false)} className="btn-secondary">Cancelar</button><button onClick={guardarEnt} className="btn-primary">Guardar</button></div>
          </div>
        )}
      </Modal>

      {/* ===== MODAL SUPERVISIÓN (sección 2) ===== */}
      <Modal abierto={modalSup} titulo="Trabajo bajo supervisión" onCerrar={() => setModalSup(false)} ancho="max-w-2xl">
        {formSup && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <label className="block"><span className={lbl}>Tutor de supervisión</span><select className={inp} value={formSup.tutor_supervision} onChange={(e) => setFormSup({ ...formSup, tutor_supervision: e.target.value })}><option value="">—</option>{personas.map((p) => <option key={p.id} value={p.id}>{nombrePersona(p)}</option>)}</select></label>
              <label className="block"><span className={lbl}>Periodo (días)</span><input type="number" className={inp} value={formSup.periodo_supervision_dias} onChange={(e) => setFormSup({ ...formSup, periodo_supervision_dias: e.target.value })} /></label>
              <label className="block"><span className={lbl}>Fecha de inicio</span><input type="date" className={inp} value={formSup.fecha_inicio_supervision || ''} onChange={(e) => setFormSup({ ...formSup, fecha_inicio_supervision: e.target.value })} /></label>
            </div>
            <div><span className={lbl}>El personal demuestra habilidad o conocimiento en:</span>
              <TablaFilas columnas={[{ k: 'item', label: 'Ítem' }, { k: 'conformidad', label: 'Conformidad', tipo: 'conformidad' }]}
                filas={formSup.checklist_supervision} onChange={(f) => setFormSup({ ...formSup, checklist_supervision: f })} nueva={() => ({ item: '', conformidad: '' })} />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <label className="block"><span className={lbl}>Nota teórica (0-20)</span><input type="number" step="any" className={inp} value={formSup.nota_teorica} onChange={(e) => setFormSup({ ...formSup, nota_teorica: e.target.value })} /></label>
              <label className="block"><span className={lbl}>Control de validez</span><select className={inp} value={formSup.control_validez} onChange={(e) => setFormSup({ ...formSup, control_validez: e.target.value })}><option value="">—</option>{controles.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}</select></label>
              <label className="block"><span className={lbl}>Resultado del control</span><select className={inp} value={formSup.resultado_control} onChange={(e) => setFormSup({ ...formSup, resultado_control: e.target.value })}><option value="">—</option><option value="satisfactorio">Satisfactorio</option><option value="no_satisfactorio">No satisfactorio</option></select></label>
            </div>
            <label className="block"><span className={lbl}>Comentarios</span><textarea className={inp} rows={2} value={formSup.comentarios} onChange={(e) => setFormSup({ ...formSup, comentarios: e.target.value })} /></label>
            <div className="flex justify-end gap-2"><button onClick={() => setModalSup(false)} className="btn-secondary">Cancelar</button><button onClick={() => guardarSup()} className="btn-secondary">Guardar (en proceso)</button></div>
            {(() => {
              const falta = faltantesEntrenamiento({ ...(entrenamientos.find((x) => x.id === formSup.id) || {}), ...formSup })
              return (
                <BarraEtapa titulo="Concluir el entrenamiento y el trabajo bajo supervisión"
                  nota="Cumple los requisitos para darlo por superado. Al concluir queda de solo lectura."
                  bloqueo={falta.length ? `Para darlo por superado falta: ${falta.join('; ')}. Sin entrenamiento superado no se autoriza en este método.` : ''}
                  botones={[
                    { texto: 'Dar por superado', accion: () => concluirSup('completado') },
                    { texto: 'No conforme', secundario: true, accion: () => concluirSup('no_conforme') },
                  ]} />
              )
            })()}
          </div>
        )}
      </Modal>

      {/* ===== MODAL SEGUIMIENTO ===== */}
      <Modal abierto={modalSeg} titulo="Nuevo seguimiento (entrevista)" onCerrar={() => setModalSeg(false)} ancho="max-w-3xl">
        {formSeg && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <label className="block"><span className={lbl}>Responsable (evaluador)</span><select className={inp} value={formSeg.evaluador} onChange={(e) => setFormSeg({ ...formSeg, evaluador: e.target.value })}><option value="">—</option>{personas.map((p) => <option key={p.id} value={p.id}>{nombrePersona(p)}</option>)}</select></label>
              <label className="block"><span className={lbl}>Fecha</span><input type="date" className={inp} value={formSeg.fecha || ''} onChange={(e) => setFormSeg({ ...formSeg, fecha: e.target.value })} /></label>
              <label className="block"><span className={lbl}>Hora</span><input className={inp} value={formSeg.hora} onChange={(e) => setFormSeg({ ...formSeg, hora: e.target.value })} placeholder="10:00" /></label>
              <label className="block"><span className={lbl}>Área</span><input className={inp} value={formSeg.area} onChange={(e) => setFormSeg({ ...formSeg, area: e.target.value })} /></label>
              <label className="block"><span className={lbl}>Tema</span><input className={inp} value={formSeg.tema} onChange={(e) => setFormSeg({ ...formSeg, tema: e.target.value })} /></label>
              <label className="block"><span className={lbl}>Tipo</span><select className={inp} value={formSeg.tipo} onChange={(e) => setFormSeg({ ...formSeg, tipo: e.target.value })}><option value="entrevista">Entrevista</option><option value="control_validez">Control de validez</option><option value="testificacion">Testificación</option><option value="otro">Otro</option></select></label>
              <label className="block"><span className={lbl}>Autorización relacionada</span><select className={inp} value={formSeg.autorizacion} onChange={(e) => setFormSeg({ ...formSeg, autorizacion: e.target.value })}><option value="">—</option>{autsDe(ficha?.id).map((a) => <option key={a.id} value={a.id}>{a.metodo_nombre || 'General'}</option>)}</select></label>
            </div>
            <div><span className={lbl}>Preguntas (I. Desarrollo)</span>
              <TablaFilas columnas={[{ k: 'n', label: 'N°' }, { k: 'establecido', label: 'Puntaje establecido', tipo: 'number' }, { k: 'obtenido', label: 'Puntaje obtenido', tipo: 'number' }]}
                filas={formSeg.preguntas} onChange={(f) => setFormSeg({ ...formSeg, preguntas: f })} nueva={() => ({ n: (formSeg.preguntas.length + 1), establecido: '', obtenido: '' })} />
            </div>
            {(() => {
              const c = calcularPuntajes(formSeg.preguntas, formSeg.puntaje_por_pregunta)
              const calculado = !!(c && c.resultado)
              const resultado = calculado ? c.resultado : formSeg.resultado
              const celda = (t, v) => <div className="rounded-md bg-slate-100 px-2 py-1.5 text-center dark:bg-slate-800"><p className="text-xs text-slate-500 dark:text-slate-400">{t}</p><p className="text-sm font-semibold">{v ?? '—'}</p></div>
              return (
                <>
                  <div className="grid grid-cols-5 gap-2">
                    <label className="block"><span className={lbl}>Puntaje por pregunta</span><input type="number" step="any" className={inp} value={formSeg.puntaje_por_pregunta} placeholder={c ? 'mayor establecido' : ''} onChange={(e) => setFormSeg({ ...formSeg, puntaje_por_pregunta: e.target.value })} /></label>
                    {celda('N.° preguntas', c?.n)}{celda('Total', c?.total)}{celda('Mínimo (70 %)', c?.minimo)}{celda('Máximo', c?.maximo)}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <label className="block"><span className={lbl}>Resultado {calculado && '(calculado)'}</span><select className={inp} disabled={calculado} value={resultado} onChange={(e) => setFormSeg({ ...formSeg, resultado: e.target.value })}><option value="">—</option><option value="satisfactorio">Satisfactorio</option><option value="no_satisfactorio">No satisfactorio</option></select></label>
                    <label className="block"><span className={lbl}>Decisión</span><select className={inp} value={formSeg.decision} onChange={(e) => setFormSeg({ ...formSeg, decision: e.target.value })}><option value="">—</option>{resultado !== 'no_satisfactorio' && <option value="mantener">Mantener</option>}<option value="suspender">Suspender</option>{resultado !== 'no_satisfactorio' && <option value="reautorizar">Reautorizar</option>}</select></label>
                  </div>
                </>
              )
            })()}
            <label className="block"><span className={lbl}>Conclusiones</span><textarea className={inp} rows={2} value={formSeg.conclusiones} onChange={(e) => setFormSeg({ ...formSeg, conclusiones: e.target.value })} /></label>
            <label className="block"><span className={lbl}>Observaciones y/o recomendaciones</span><textarea className={inp} rows={2} value={formSeg.observaciones} onChange={(e) => setFormSeg({ ...formSeg, observaciones: e.target.value })} /></label>
            <p className="text-[11px] text-slate-400">Total, mínimo (70 % del máximo), máximo (puntaje por pregunta × n.° de preguntas) y resultado los calcula el sistema al guardar. «Suspender» y «Reautorizar» cambian el estado de la autorización relacionada; reautorizar exige un re-entrenamiento superado después de la suspensión.</p>
            <div className="flex justify-end gap-2"><button onClick={() => setModalSeg(false)} className="btn-secondary">Cancelar</button><button onClick={guardarSeg} className="btn-primary">Guardar</button></div>
          </div>
        )}
      </Modal>

      {/* ===== MODAL CATÁLOGOS ===== */}
      <Modal abierto={modalCat} titulo="Catálogos de Competencia" onCerrar={() => setModalCat(false)} ancho="max-w-2xl">
        <CatalogoManager metodos={metodos} controles={controles} onCambio={cargarBase} />
      </Modal>

      <Modal abierto={modalPend} titulo="Cambios pendientes de aprobación" onCerrar={() => setModalPend(false)} ancho="max-w-2xl">
        {pendientes.length === 0 ? <p className="py-6 text-center text-sm text-slate-400">No hay cambios pendientes.</p> : (
          <div className="space-y-2">
            {pendientes.map((s) => (
              <div key={s.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <div><p className="text-sm font-medium">{s.resumen || `${s.operacion_display} · ${s.entidad_display}`}</p><p className="text-xs text-slate-500 dark:text-slate-400">Solicitado por {s.solicitante} · {fechaHora(s.created_at)}</p></div>
                <div className="flex shrink-0 gap-2">
                  <button onClick={() => resolver(s, 'aprobar')} className="btn-primary !py-1">Aprobar</button>
                  <button onClick={() => resolver(s, 'devolver')} className="btn-secondary !py-1">Devolver</button>
                  <button onClick={() => resolver(s, 'rechazar')} className="btn-danger !py-1">Rechazar</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>

      <Modal abierto={modalMis} titulo="Mis solicitudes de cambio" onCerrar={() => setModalMis(false)} ancho="max-w-2xl">
        {misSolic.length === 0 ? <p className="py-6 text-center text-sm text-slate-400">No has enviado cambios.</p> : (
          <div className="space-y-2">
            {misSolic.map((s) => {
              const cls = { pendiente: 'bg-amber-500/15 text-amber-600 dark:text-amber-400', aprobada: 'bg-green-500/15 text-green-600 dark:text-green-400', devuelta: 'bg-violet-500/15 text-violet-600 dark:text-violet-400', rechazada: 'bg-red-500/15 text-red-600 dark:text-red-400' }[s.estado] || 'bg-slate-500/15 text-slate-500'
              return (
                <div key={s.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <div>
                    <p className="text-sm font-medium">{s.resumen}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Enviado {fechaHora(s.created_at)}</p>
                    {s.observaciones && <p className="mt-1 text-xs text-slate-600 dark:text-slate-300"><span className="font-medium">Motivo:</span> {s.observaciones}</p>}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{s.estado_display}</span>
                    {s.estado === 'devuelta' && <button onClick={() => reenviar(s)} className="btn-primary !py-1">Reenviar</button>}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Modal>
    </div>
  )
}

function CatalogoManager({ metodos, controles, onCambio }) {
  const [nm, setNm] = useState({ nombre: '', codigo: '', magnitud: '' })
  const [nc, setNc] = useState('')
  const addMetodo = async () => { if (!nm.nombre.trim()) return; await api.metodosCalibracion.crear(nm); setNm({ nombre: '', codigo: '', magnitud: '' }); onCambio() }
  const delMetodo = async (id) => { await api.metodosCalibracion.eliminar(id); onCambio() }
  const addControl = async () => { if (!nc.trim()) return; await api.controlesValidez.crear({ nombre: nc }); setNc(''); onCambio() }
  const delControl = async (id) => { await api.controlesValidez.eliminar(id); onCambio() }
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <div>
        <h4 className="mb-2 text-sm font-semibold">Métodos / procedimientos</h4>
        <div className="mb-2 space-y-1">
          <input className={inp} placeholder="Nombre del método" value={nm.nombre} onChange={(e) => setNm({ ...nm, nombre: e.target.value })} />
          <div className="grid grid-cols-2 gap-1"><input className={inp} placeholder="Código" value={nm.codigo} onChange={(e) => setNm({ ...nm, codigo: e.target.value })} /><input className={inp} placeholder="Magnitud" value={nm.magnitud} onChange={(e) => setNm({ ...nm, magnitud: e.target.value })} /></div>
          <button onClick={addMetodo} className="btn-primary !py-1 w-full"><Plus className="h-4 w-4" /> Agregar método</button>
        </div>
        <div className="max-h-56 space-y-1 overflow-y-auto">
          {metodos.map((m) => <div key={m.id} className="flex items-center justify-between rounded border border-slate-200 px-2 py-1 text-xs dark:border-slate-700"><span>{m.codigo ? `${m.codigo} · ` : ''}{m.nombre}{m.magnitud ? ` (${m.magnitud})` : ''}</span><button onClick={() => delMetodo(m.id)} className="text-red-500"><Trash2 className="h-3.5 w-3.5" /></button></div>)}
        </div>
      </div>
      <div>
        <h4 className="mb-2 text-sm font-semibold">Controles de validez</h4>
        <div className="mb-2 flex gap-1"><input className={inp} placeholder="Nombre del control" value={nc} onChange={(e) => setNc(e.target.value)} /><button onClick={addControl} className="btn-primary !py-1"><Plus className="h-4 w-4" /></button></div>
        <div className="max-h-56 space-y-1 overflow-y-auto">
          {controles.map((c) => <div key={c.id} className="flex items-center justify-between rounded border border-slate-200 px-2 py-1 text-xs dark:border-slate-700"><span>{c.nombre}</span><button onClick={() => delControl(c.id)} className="text-red-500"><Trash2 className="h-3.5 w-3.5" /></button></div>)}
        </div>
      </div>
    </div>
  )
}
