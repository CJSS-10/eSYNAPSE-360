import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import { FileText, HardHat, HeartPulse, LayoutDashboard, Lock, Siren, Target, UsersRound, Wrench, Pencil, Plus, Search, ShieldCheck, Trash2, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import CampoSugerencias from '../components/CampoSugerencias.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import { useCatalogoProcesos } from '../components/SelectorProceso.jsx'
import { Enfermedades, Estadisticas, Eventos } from './SstEventos.jsx'
import { Inspecciones, Monitoreos } from './SstInspecciones.jsx'
import { Epp, VigilanciaMedica } from './SstEpp.jsx'
import { Comite, ProgramaSsoma } from './SstComite.jsx'
import NavModulo, { Vistas } from '../components/NavModulo.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora } from '../lib/fecha.js'
import { sev } from '../lib/severidad.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'

// Navegación del módulo: grupos según el ciclo del sistema de SST (planificar, operar, vigilar la salud, eventos, participación).
const GRUPOS_SST = [
  { clave: 'inicio', nombre: 'Inicio', icono: LayoutDashboard, secciones: [{ clave: 'resumen', nombre: 'Resumen' }] },
  { clave: 'planificacion', nombre: 'Planificación', icono: Target, secciones: [{ clave: 'iperc', nombre: 'Matriz IPERC' }, { clave: 'puestos', nombre: 'Puestos' }, { clave: 'programa', nombre: 'Programa SSOMA' }] },
  { clave: 'operacion', nombre: 'Operación', icono: Wrench, secciones: [{ clave: 'ats', nombre: 'ATS' }, { clave: 'inspecciones', nombre: 'Inspecciones' }, { clave: 'epp', nombre: 'EPP' }] },
  { clave: 'salud', nombre: 'Salud ocupacional', icono: HeartPulse, secciones: [{ clave: 'vigilancia', nombre: 'Vigilancia médica' }, { clave: 'monitoreos', nombre: 'Monitoreos' }, { clave: 'enfermedades', nombre: 'Enfermedades' }] },
  { clave: 'eventos', nombre: 'Eventos', icono: Siren, secciones: [{ clave: 'eventos', nombre: 'Incidentes y accidentes' }, { clave: 'estadisticas', nombre: 'Estadísticas' }] },
  { clave: 'participacion', nombre: 'Participación', icono: UsersRound, secciones: [{ clave: 'comite', nombre: 'Comité de SST' }] },
]

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'

// Niveles de riesgo del IPERC en la escala de severidad única del sistema.
const NIVEL = {
  T: sev(1, 'Trivial'),
  TO: sev(2, 'Tolerable'),
  M: sev(3, 'Moderado'),
  IM: sev(4, 'Importante'),
  IT: sev(5, 'Intolerable'),
}
const ACCION = { T: 'No requiere acción.', TO: 'No requiere mejoras, salvo las más rentables.', M: 'Requiere reducción o controles periódicos.', IM: 'No se inicia el trabajo hasta reducir el riesgo.', IT: 'No se permite realizar el trabajo.' }
// Situación de control (regla 10): gris sin evaluar · ámbar requiere control · verde controlado · rojo trabajo detenido.
const SITUACION = {
  sin_evaluar: ['Sin evaluar', 'bg-slate-500/15 text-slate-500'],
  requiere_control: ['Requiere control', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  controlado: ['Controlado', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  trabajo_detenido: ['Trabajo detenido', 'bg-red-500/15 text-red-600 dark:text-red-400'],
}
const ESTADO_ATS = {
  borrador: ['En preparación', 'bg-slate-500/15 text-slate-500'],
  en_campo: ['En campo', 'bg-blue-500/15 text-blue-600 dark:text-blue-400'],
  recibido: ['Recibido', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  revisado: ['Revisado', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  validado: ['Validado', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  anulado: ['Anulado', 'bg-red-500/15 text-red-600 dark:text-red-400'],
}
// Niveles del análisis de trabajo seguro en la misma escala (empieza en el nivel 2).
const NIVEL_ATS = {
  tolerable: sev(2, 'Tolerable'),
  poco_significativo: sev(3, 'Poco significativo'),
  significativo: sev(4, 'Significativo'),
  intolerable: sev(5, 'Intolerable'),
}
const SITUACIONES = [['rutinaria', 'Rutinaria'], ['no_rutinaria', 'No rutinaria'], ['emergencia', 'Emergencia']]

const nivelIperc = (v) => (!v ? '' : v <= 4 ? 'T' : v <= 8 ? 'TO' : v <= 16 ? 'M' : v <= 24 ? 'IM' : 'IT')
const nivelAts = (v) => (!v ? '' : v <= 2 ? 'tolerable' : v <= 6 ? 'poco_significativo' : v <= 9 ? 'significativo' : 'intolerable')
const calc = (f, pre = '') => {
  const vals = ['personas', 'procedimientos', 'capacitacion', 'exposicion'].map((k) => Number(f[pre + k]) || 0)
  const s = Number(f[pre + 'severidad']) || 0
  if (vals.some((v) => !v) || !s) return { p: null, nr: null, n: '' }
  const p = vals.reduce((a, b) => a + b, 0)
  return { p, nr: p * s, n: nivelIperc(p * s) }
}

// Error dentro de una ventana: se desplaza a la vista para que no quede oculto arriba.
function Aviso({ texto }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [texto])
  return <p ref={ref} className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p>
}
const Chip = ({ par, extra }) => (par ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{par[0]}{extra}</span> : null)
function Seccion({ titulo, children, extra }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
      <div className="mb-1.5 flex items-center justify-between gap-2"><p className="text-xs font-semibold text-slate-500 dark:text-slate-400">{titulo}</p>{extra}</div>
      <div className="space-y-2 text-slate-600 dark:text-slate-300">{children}</div>
    </div>
  )
}

export default function Sst() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const procesos = useCatalogoProcesos()
  const [pestana, setPestana] = useState('resumen')
  const [vistaAts, setVistaAts] = useState('ats')
  const [cat, setCat] = useState(null)
  const [puestos, setPuestos] = useState([])
  const [areasOrg, setAreasOrg] = useState([])
  const [error, setError] = useState('')
  const errorRef = useRef(null)
  useEffect(() => { if (error && errorRef.current) errorRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [error])
  const cargarCat = useCallback(() => {
    api.sst.catalogos().then(setCat).catch(() => {})
    api.org.puestos().then(setPuestos).catch(() => {})
    api.org.areas().then(setAreasOrg).catch(() => {})
  }, [])
  useEffect(() => { cargarCat() }, [cargarCat])
  const abrirPdf = async (promesa) => {
    setError('')
    try { const url = URL.createObjectURL(await promesa); window.open(url, '_blank'); setTimeout(() => URL.revokeObjectURL(url), 60000) } catch (e) { setError(e.message) }
  }
  const comun = { cat, puestos, areasOrg, procesos, confirmar, setError, abrirPdf, cargarCat, puedeCrear: tienePermiso('sst', 'crear'), puedeEditar: tienePermiso('sst', 'editar'), puedeAprobar: tienePermiso('sst', 'aprobar'), puedeEliminar: tienePermiso('sst', 'eliminar') }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2"><TituloModulo seccion="Seguridad y salud" titulo="Seguridad y Salud en el Trabajo" descripcion="IPERC, análisis de trabajo seguro, incidentes, inspecciones, EPP, vigilancia médica y Comité de SST." />
          <span className="rounded bg-red-500/15 px-2 py-0.5 text-[11px] font-semibold text-red-600 dark:text-red-400">ISO 45001 · Ley 29783</span></div>
      </div>
      <NavModulo grupos={GRUPOS_SST} seccion={pestana} onCambiar={(k) => { setError(''); setPestana(k) }} />
      {error && <p ref={errorRef} className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      {pestana === 'iperc' && <Iperc {...comun} />}
      {pestana === 'ats' && <div className="space-y-3"><Vistas valor={vistaAts} onChange={setVistaAts} opciones={[['ats', 'ATS'], ['tipos', 'ATS tipo']]} />{vistaAts === 'ats' ? <Ats {...comun} /> : <AtsTipos {...comun} />}</div>}
      {pestana === 'inspecciones' && <Inspecciones {...comun} />}
      {pestana === 'monitoreos' && <Monitoreos {...comun} />}
      {pestana === 'epp' && <Epp {...comun} />}
      {pestana === 'vigilancia' && <VigilanciaMedica {...comun} />}
      {pestana === 'eventos' && <Eventos {...comun} />}
      {pestana === 'enfermedades' && <Enfermedades {...comun} />}
      {pestana === 'estadisticas' && <Estadisticas {...comun} />}
      {pestana === 'comite' && <Comite {...comun} />}
      {pestana === 'programa' && <ProgramaSsoma {...comun} />}
      {pestana === 'puestos' && <Puestos {...comun} />}
      {pestana === 'resumen' && <Resumen irA={() => setPestana('iperc')} />}
    </div>
  )
}

/* ------------------------------------------------------------ Matriz IPERC */
const FILA_VACIA = {
  area: '', unidad: '', proceso: '', subproceso: '', puestos: [], todos_los_puestos: false, puestos_texto: '', actividad: '', peligro: '', riesgo: '', consecuencia: '',
  situaciones: ['rutinaria'], controles_existentes: '', requisito_legal: '', personas: '', procedimientos: '', capacitacion: '', exposicion: '', severidad: '',
  control_eliminacion: '', control_sustitucion: '', control_ingenieria: '', control_administrativo: '', control_epp: '', responsables: [], responsable: '',
  r_personas: '', r_procedimientos: '', r_capacitacion: '', r_exposicion: '', r_severidad: '',
}
const NUMEROS = ['personas', 'procedimientos', 'capacitacion', 'exposicion', 'severidad', 'r_personas', 'r_procedimientos', 'r_capacitacion', 'r_exposicion', 'r_severidad']
const INDICES = [['personas', 'Personas expuestas (A)', '1: 1 a 3 · 2: 4 a 12 · 3: más de 12'], ['procedimientos', 'Procedimientos (B)', '1: satisfactorios · 2: parciales · 3: no existen'],
  ['capacitacion', 'Capacitación (C)', '1: entrenado · 2: parcialmente · 3: no entrenado'], ['exposicion', 'Exposición (D)', '1: anual / esporádica · 2: mensual / eventual · 3: diaria / permanente'],
  ['severidad', 'Severidad', '1: sin incapacidad / incomodidad · 2: incapacidad temporal / daño reversible · 3: incapacidad permanente / irreversible']]

function Indices({ form, setForm, pre = '', editable }) {
  const r = calc(form, pre)
  return (
    <div className="grid items-end gap-2 md:grid-cols-7">
      {INDICES.map(([k, n, ayuda]) => (
        <div key={k}><label className={lbl} title={ayuda}>{n}</label>
          <select className={inp} disabled={!editable} value={form[pre + k] ?? ''} onChange={(e) => setForm({ ...form, [pre + k]: e.target.value })}><option value="">—</option>{[1, 2, 3].map((v) => <option key={v} value={v}>{v}</option>)}</select></div>
      ))}
      <div className="text-center text-xs"><p className="text-slate-500">P = A+B+C+D</p><p className="text-lg font-bold">{r.p ?? '—'}</p></div>
      <div className="text-center text-xs"><p className="text-slate-500">NR = P × S</p><p className="text-lg font-bold">{r.nr ?? '—'}</p>{r.n && <Chip par={NIVEL[r.n]} />}</div>
    </div>
  )
}

// Estados de aprobación de una hoja de la matriz (regla 10): verde aprobada · ámbar pendiente · rojo sin aprobar.
const EST_APROB = {
  aprobada: ['Aprobada', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  pendiente: ['Pendiente de aprobación', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  sin_aprobar: ['Sin aprobar', 'bg-red-500/15 text-red-600 dark:text-red-400'],
}
const METODO_FIRMA = { usuario: 'su usuario', pin: 'PIN', papel: 'acta en papel', carga: 'formato original' }

/* La matriz IPERC la realiza y aprueba el Comité de SST. Cada titular firma en pantalla: con la contraseña de su
   usuario si lo tiene, o con su PIN si no; o se adjunta el acta firmada en papel. */
function AprobacionComite({ abierto, datos, area, onCerrar, alAprobar }) {
  const [f, setF] = useState(null)
  const [reuniones, setReuniones] = useState([])
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  useEffect(() => {
    if (!abierto || !datos) return
    setErr(''); setOk('')
    const marcadas = datos.areas.filter((x) => x.estado !== 'aprobada' || x.area === area).map((x) => x.area)
    setF({ areas: marcadas, fecha: new Date().toISOString().slice(0, 10), reunion: '', modo: 'pantalla', observaciones: '', archivo: null, password: '',
      firmas: Object.fromEntries(datos.titulares.map((t) => [t.id, { firma: true, clave: '', pin: '', pin_nuevo: '', pin_confirmacion: '' }])) })
    api.sst.reuniones().then(setReuniones).catch(() => {})
  }, [abierto]) // eslint-disable-line react-hooks/exhaustive-deps
  if (!abierto || !datos || !f) return null
  const setFirma = (id, k, v) => setF({ ...f, firmas: { ...f.firmas, [id]: { ...f.firmas[id], [k]: v } } })
  const firmantes = datos.titulares.filter((t) => f.firmas[t.id]?.firma)
  const enviar = async () => {
    setErr('')
    if (!f.areas.length) { setErr('Elija las hojas que aprueba el Comité.'); return }
    if (firmantes.length < datos.quorum) { setErr(`Se requiere la firma de al menos ${datos.quorum} titular(es) (mitad más uno).`); return }
    try {
      if (f.modo === 'papel') {
        if (!f.archivo) { setErr('Adjunte el acta firmada por los miembros.'); return }
        const fd = new FormData()
        fd.append('areas', JSON.stringify(f.areas)); fd.append('fecha', f.fecha); fd.append('observaciones', f.observaciones)
        fd.append('firmantes', JSON.stringify(firmantes.map((t) => t.id))); fd.append('archivo', f.archivo); fd.append('password', f.password)
        if (f.reunion) fd.append('reunion', f.reunion)
        await api.sst.aprobarIpercPapel(fd)
      } else {
        const firmas = firmantes.map((t) => {
          const x = f.firmas[t.id]
          return t.firma === 'usuario' ? { miembro: t.id, clave: x.clave } : t.firma === 'activo' ? { miembro: t.id, pin: x.pin } : { miembro: t.id, pin_nuevo: x.pin_nuevo, pin_confirmacion: x.pin_confirmacion }
        })
        await api.sst.aprobarIperc({ areas: f.areas, fecha: f.fecha, reunion: f.reunion || null, observaciones: f.observaciones, firmas })
      }
      setOk(`Aprobadas ${f.areas.length} hoja(s) con la firma de ${firmantes.length} titular(es).`)
      setF({ ...f, password: '', firmas: Object.fromEntries(Object.entries(f.firmas).map(([k, v]) => [k, { ...v, clave: '', pin: '', pin_nuevo: '', pin_confirmacion: '' }])) })
      alAprobar()
    } catch (e) { setErr(e.message); alAprobar() }
  }
  const pinInp = (t, k, ph) => <input type="password" inputMode="numeric" autoComplete="off" placeholder={ph} className={`${inp} !py-1 text-xs`} value={f.firmas[t.id][k]} onChange={(e) => setFirma(t.id, k, e.target.value.replace(/\D/g, '').slice(0, 6))} />
  return (
    <Modal abierto titulo="Aprobación de la matriz IPERC por el Comité de SST" onCerrar={onCerrar} ancho="max-w-5xl">
      <div className="space-y-3 text-sm">
        {!datos.titulares.length && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600">El comité vigente no tiene miembros titulares registrados: regístrelos en Participación → Comité de SST.</p>}
        <div>
          <div className="mb-1 flex items-center gap-2"><label className={lbl + ' !mb-0'}>Hojas que aprueba</label>
            <button className="text-[11px] text-esynapse-500 underline" onClick={() => setF({ ...f, areas: datos.areas.map((x) => x.area) })}>todas</button>
            <button className="text-[11px] text-esynapse-500 underline" onClick={() => setF({ ...f, areas: datos.areas.filter((x) => x.estado !== 'aprobada').map((x) => x.area) })}>solo pendientes</button></div>
          <div className="grid max-h-44 gap-1 overflow-y-auto rounded border border-slate-200 p-2 text-xs md:grid-cols-2 dark:border-slate-800">
            {datos.areas.map((x) => <label key={x.area} className="flex items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" checked={f.areas.includes(x.area)} onChange={() => setF({ ...f, areas: f.areas.includes(x.area) ? f.areas.filter((y) => y !== x.area) : [...f.areas, x.area] })} />{x.area} <Chip par={EST_APROB[x.estado]} /></label>)}
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <div><label className={lbl}>Fecha de aprobación</label><input type="date" className={inp} value={f.fecha} onChange={(e) => setF({ ...f, fecha: e.target.value })} /></div>
          <div className="md:col-span-2"><label className={lbl}>Reunión del Comité (opcional)</label><select className={inp} value={f.reunion} onChange={(e) => setF({ ...f, reunion: e.target.value })}><option value="">—</option>{reuniones.map((r) => <option key={r.id} value={r.id}>{r.codigo} · {fecha(r.fecha)} · {r.tipo_display}</option>)}</select></div>
        </div>
        <div className="flex gap-4 text-xs"><label className="flex items-center gap-1"><input type="radio" checked={f.modo === 'pantalla'} onChange={() => setF({ ...f, modo: 'pantalla' })} /> Firman en pantalla</label><label className="flex items-center gap-1"><input type="radio" checked={f.modo === 'papel'} onChange={() => setF({ ...f, modo: 'papel' })} /> Acta firmada en papel (adjunta)</label></div>
        <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
          <p className="mb-1 font-semibold">Realizado y aprobado por — Comité {datos.comite || ''} <span className="font-normal text-slate-500">(se requieren {datos.quorum} de {datos.titulares.length} titulares)</span></p>
          <table className="tabla-ficha w-full">
            <thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="px-1">Firma</th><th className="px-1">Titular</th><th className="px-1">Cargo</th>{f.modo === 'pantalla' && <th className="px-1">Credencial</th>}</tr></thead>
            <tbody>{datos.titulares.map((t) => (
              <tr key={t.id} className="border-t border-slate-100 dark:border-slate-800/60">
                <td className="px-1 py-1"><input type="checkbox" className="accent-esynapse-600" checked={f.firmas[t.id]?.firma} onChange={(e) => setFirma(t.id, 'firma', e.target.checked)} /></td>
                <td className="px-1">{t.nombre}<span className="block text-[11px] text-slate-500">{t.representacion}</span></td><td className="px-1">{t.cargo}</td>
                {f.modo === 'pantalla' && <td className="w-72 px-1">{!f.firmas[t.id]?.firma ? '—'
                  : t.firma === 'usuario' ? <input type="password" autoComplete="off" placeholder="Contraseña de su usuario" className={`${inp} !py-1 text-xs`} value={f.firmas[t.id].clave} onChange={(e) => setFirma(t.id, 'clave', e.target.value)} />
                  : t.firma === 'activo' ? pinInp(t, 'pin', 'PIN')
                  : t.firma === 'bloqueado' ? <span className="text-red-600">PIN bloqueado: restablézcalo (EPP › Por trabajador) o use el acta en papel</span>
                  : <div className="flex gap-1">{pinInp(t, 'pin_nuevo', 'Nuevo PIN')}{pinInp(t, 'pin_confirmacion', 'Confirme')}</div>}</td>}
              </tr>
            ))}</tbody>
          </table>
          {f.modo === 'pantalla' && <p className="mt-1 text-[11px] text-slate-500">Cada titular escribe su propia credencial: la contraseña de su usuario si lo tiene; si no, su PIN personal (lo crea en su primera firma).</p>}
        </div>
        {f.modo === 'papel' && <div className="grid gap-3 md:grid-cols-2">
          <div><label className={lbl}>Acta firmada (escaneada)</label><input type="file" className="text-xs" onChange={(e) => setF({ ...f, archivo: e.target.files[0] || null })} /></div>
          <div><label className={lbl}>Su contraseña (quien registra)</label><input type="password" autoComplete="current-password" className={inp} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></div>
        </div>}
        <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} value={f.observaciones} onChange={(v) => setF({ ...f, observaciones: v })} /></div>
        {err && <Aviso texto={err} />}
        {ok && <p className="rounded bg-emerald-500/10 px-3 py-2 text-xs text-emerald-600">{ok}</p>}
        <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={onCerrar}>Cerrar</button><button className="btn-primary" onClick={enviar}>Registrar la aprobación</button></div>
        {datos.historial.length > 0 && <div className="border-t border-slate-200 pt-2 text-xs dark:border-slate-800">
          <p className="mb-1 font-semibold">Aprobaciones anteriores</p>
          <ul className="space-y-1 text-slate-600 dark:text-slate-300">{datos.historial.slice(0, 8).map((h) => <li key={h.id}><span className="font-medium">{fecha(h.fecha)}</span> · {h.areas.length} hoja(s){h.reunion ? ` · ${h.reunion}` : ''} · {h.firmas.map((x) => `${x.nombre} (${METODO_FIRMA[x.metodo] || x.metodo})`).join(', ')}{h.archivo_url && <> · <a className="text-esynapse-500 underline" href={h.archivo_url} target="_blank" rel="noreferrer">acta</a></>}</li>)}</ul>
        </div>}
      </div>
    </Modal>
  )
}

function Iperc({ cat, puestos, areasOrg, procesos, confirmar, setError, abrirPdf, cargarCat, puedeCrear, puedeEditar, puedeAprobar }) {
  const [items, setItems] = useState([])
  const [area, setArea] = useState('')
  const [puesto, setPuesto] = useState('')
  const [unidad, setUnidad] = useState('')
  const [nivel, setNivel] = useState('')
  const [situacion, setSituacion] = useState('')
  const [buscar, setBuscar] = useState('')
  const [retirados, setRetirados] = useState(false)
  const [form, setForm] = useState(null)
  const [d, setD] = useState(null)
  const [err, setErr] = useState('')
  const [aprob, setAprob] = useState(null)
  const [verAprob, setVerAprob] = useState(false)
  const cargarAprob = useCallback(() => api.sst.aprobacionesIperc().then(setAprob).catch(() => {}), [])
  useEffect(() => { cargarAprob() }, [cargarAprob])
  const params = useCallback(() => {
    const p = new URLSearchParams()
    if (area) p.set('area', area); if (unidad) p.set('unidad', unidad); if (puesto) p.set('puesto', puesto); if (nivel) p.set('clasificacion', nivel)
    if (situacion) p.set('situacion', situacion); if (buscar) p.set('buscar', buscar); if (retirados) p.set('retirados', '1')
    return `?${p}`
  }, [area, unidad, puesto, nivel, situacion, buscar, retirados])
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => setItems(await ultima(api.sst.filas(params()))), [params])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])

  const abrir = async (id) => {
    setErr('')
    const f = await api.sst.fila(id)
    setD(f)
    setForm({ id: f.id, ...Object.fromEntries(Object.keys(FILA_VACIA).map((k) => [k, f[k] ?? FILA_VACIA[k]])) })
  }
  const nueva = () => { setErr(''); setD(null); setForm({ ...FILA_VACIA, area }) }
  const editable = !d || (d.estado === 'vigente' && puedeEditar)
  const guardar = async () => {
    setErr('')
    const datos = { ...form, proceso: form.proceso || null, unidad: form.unidad || null }
    NUMEROS.forEach((k) => { datos[k] = datos[k] === '' || datos[k] == null ? null : Number(datos[k]) })
    if (datos.todos_los_puestos) datos.puestos = []
    try {
      const r = form.id ? await api.sst.editarFila(form.id, datos) : await api.sst.crearFila(datos)
      await cargar(); cargarCat(); cargarAprob(); setD(r); setForm({ id: r.id, ...Object.fromEntries(Object.keys(FILA_VACIA).map((k) => [k, r[k] ?? FILA_VACIA[k]])) })
    } catch (e) { setErr(e.message) }
  }
  const retirar = async () => {
    const m = await confirmar({ titulo: 'Retirar la fila', mensaje: 'La fila queda como registro (con su historial) y sale de la matriz vigente.', textoConfirmar: 'Retirar', peligro: true, entrada: { etiqueta: 'Motivo (actividad eliminada, peligro inexistente…)', obligatorio: true, multilinea: true } })
    if (m === null) return
    setErr('')
    try { const r = await api.sst.retirarFila(d.id, m); setD(r); await cargar(); cargarAprob() } catch (e) { setErr(e.message) }
  }
  const estArea = aprob?.areas.find((x) => x.area === area)
  const pendientes = (aprob?.areas || []).filter((x) => x.estado !== 'aprobada')
  const elegirPeligro = (texto) => {
    const p = (cat?.peligros || []).find((x) => x.peligro === texto)
    setForm((f) => ({ ...f, peligro: texto, ...(p && !f.riesgo ? { riesgo: p.riesgo } : {}), ...(p && !f.consecuencia ? { consecuencia: p.consecuencia } : {}) }))
  }
  const ini = form ? calc(form) : {}
  const res = form ? calc(form, 'r_') : {}
  const noAceptable = ['IM', 'IT'].includes(ini.n)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select className="input-esynapse w-60" value={area} onChange={(e) => setArea(e.target.value)}><option value="">Todas las áreas</option>{(cat?.areas || []).map((a) => <option key={a} value={a}>{a}</option>)}</select>
        <select className="input-esynapse w-56" value={unidad} onChange={(e) => setUnidad(e.target.value)}><option value="">Toda área del organigrama</option>{areasOrg.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select>
        <select className="input-esynapse w-52" value={puesto} onChange={(e) => setPuesto(e.target.value)}><option value="">Todos los puestos</option>{puestos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select>
        <select className="input-esynapse w-36" value={nivel} onChange={(e) => setNivel(e.target.value)}><option value="">Todo nivel</option>{Object.entries(NIVEL).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select>
        <select className="input-esynapse w-40" value={situacion} onChange={(e) => setSituacion(e.target.value)}><option value="">Toda situación</option>{Object.entries(SITUACION).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select>
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-56 pl-9" placeholder="Código, peligro, riesgo…" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <label className="flex items-center gap-1 text-xs text-slate-500"><input type="checkbox" className="accent-esynapse-600" checked={retirados} onChange={(e) => setRetirados(e.target.checked)} /> Incluir retiradas</label>
        <span className="ml-auto flex gap-2">
          <button className="btn-secondary" onClick={() => abrirPdf(api.sst.matrizPdf(area))}><FileText className="h-4 w-4" /> Imprimir{area ? '' : ' todo'}</button>
          {puedeAprobar && <button className="btn-secondary" onClick={() => setVerAprob(true)}><ShieldCheck className="h-4 w-4" /> Aprobación del Comité</button>}
          {puedeCrear && <button className="btn-primary" onClick={nueva}><Plus className="h-4 w-4" /> Nueva fila</button>}
        </span>
      </div>
      {aprob && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-500">Aprobación del Comité de SST:</span>
          {area ? (estArea ? <><Chip par={EST_APROB[estArea.estado]} />{estArea.fecha && <span className="text-slate-500">última aprobación {fecha(estArea.fecha)}{estArea.estado === 'pendiente' ? ` · ${estArea.cambios} fila(s) cambiaron después` : ''}</span>}</> : null)
            : pendientes.length ? <Chip par={EST_APROB.pendiente} extra={` · ${pendientes.length} de ${aprob.areas.length} hojas`} /> : <Chip par={EST_APROB.aprobada} extra={` · las ${aprob.areas.length} hojas`} />}
        </div>
      )}
      <AprobacionComite abierto={verAprob} datos={aprob} area={area} onCerrar={() => setVerAprob(false)} alAprobar={cargarAprob} />
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Código</th><th className="px-2">Área</th><th className="px-2">Puestos</th><th className="px-2">Actividad</th><th className="px-2">Peligro</th><th className="px-2">Riesgo</th><th className="px-2 text-center">Nivel</th><th className="px-2 text-center">Residual</th><th className="px-2 text-center">Situación</th></tr></thead>
          <tbody>
            {items.map((f) => (
              <tr key={f.id} onClick={() => abrir(f.id)} className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${f.estado !== 'vigente' ? 'opacity-50' : ''}`}>
                <td className="whitespace-nowrap px-2 py-2 font-mono">{f.codigo}</td><td className="px-2">{f.area}</td>
                <td className="max-w-[10rem] truncate px-2" title={f.puestos_texto}>{f.puestos_texto || '—'}</td>
                <td className="max-w-[14rem] truncate px-2" title={f.actividad}>{f.actividad}</td>
                <td className="max-w-[12rem] truncate px-2" title={f.peligro}>{f.peligro}</td>
                <td className="max-w-[12rem] truncate px-2" title={f.riesgo}>{f.riesgo}</td>
                <td className="px-2 text-center">{f.clasificacion ? <Chip par={NIVEL[f.clasificacion]} extra={` ${f.nivel_riesgo}`} /> : '—'}</td>
                <td className="px-2 text-center">{f.r_clasificacion ? <Chip par={NIVEL[f.r_clasificacion]} extra={` ${f.r_nivel_riesgo}`} /> : '—'}</td>
                <td className="px-2 text-center">{f.estado !== 'vigente' ? <span className="text-[11px]">Retirada</span> : <Chip par={SITUACION[f.situacion_control]} />}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={9} className="py-8 text-slate-400">Sin filas para los filtros elegidos</td></tr>}
          </tbody>
        </table>
        <p className="px-2 py-1 text-[11px] text-slate-400">{items.length} fila(s)</p>
      </div>

      <Modal abierto={Boolean(form)} titulo={d ? `${d.codigo} — ${d.peligro.slice(0, 60)}` : 'Nueva fila de la matriz IPERC'} onCerrar={() => { setForm(null); setD(null) }} ancho="max-w-6xl">
        {form && (
          <div className="space-y-3 text-sm">
            {d && (
              <div className="flex flex-wrap items-center gap-2">
                {d.estado === 'vigente' ? <Chip par={SITUACION[d.situacion_control]} /> : <span className="flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Retirada: queda como registro</span>}
                {d.proceso_nombre && <span className="text-[11px] text-slate-500">Proceso: {d.proceso_nombre}</span>}
              </div>
            )}
            {err && <Aviso texto={err} />}
            <Seccion titulo="Identificación del peligro">
              <div className="grid gap-3 md:grid-cols-4">
                <div><label className={lbl}>Hoja de la matriz</label><CampoSugerencias disabled={!editable} value={form.area} opciones={cat?.areas || []} onChange={(v) => setForm({ ...form, area: v })} /></div>
                <div><label className={lbl}>Área del organigrama</label><select className={inp} disabled={!editable} value={String(form.unidad || '')} onChange={(e) => setForm({ ...form, unidad: e.target.value ? Number(e.target.value) : '' })}><option value="">— (lugar o grupo: comedor, terceros…)</option>{areasOrg.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select></div>
                <div><label className={lbl}>Proceso</label><select className={inp} disabled={!editable} value={String(form.proceso || '')} onChange={(e) => setForm({ ...form, proceso: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{procesos.filter((p) => p.is_active && !p.padre).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></div>
                <div><label className={lbl}>Subproceso</label><input className={inp} disabled={!editable} value={form.subproceso} onChange={(e) => setForm({ ...form, subproceso: e.target.value })} /></div>
              </div>
              <div><label className={lbl}>Puestos expuestos</label>
                <label className="mb-1 flex items-center gap-1.5 text-xs"><input type="checkbox" className="accent-esynapse-600" disabled={!editable} checked={form.todos_los_puestos} onChange={(e) => setForm({ ...form, todos_los_puestos: e.target.checked })} /> Todos los puestos</label>
                {!form.todos_los_puestos && <div className="grid max-h-28 gap-1 overflow-y-auto rounded border border-slate-200 p-2 text-xs md:grid-cols-4 dark:border-slate-700">
                  {puestos.map((p) => <label key={p.id} className="flex items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" disabled={!editable} checked={form.puestos.includes(p.id)} onChange={() => setForm({ ...form, puestos: form.puestos.includes(p.id) ? form.puestos.filter((x) => x !== p.id) : [...form.puestos, p.id] })} />{p.nombre}{p.tipo === 'tercero' ? ' (tercero)' : ''}</label>)}
                </div>}
                {d?.puestos_texto && <p className="mt-1 text-[11px] text-slate-400">En la matriz en Excel: {d.puestos_texto}</p>}
              </div>
              <div><label className={lbl}>Actividad / tarea</label><CampoAmpliable multilinea disabled={!editable} value={form.actividad} onChange={(v) => setForm({ ...form, actividad: v })} /></div>
              <div className="grid gap-3 md:grid-cols-3">
                <div><label className={lbl}>Peligro (tabla de peligros)</label><CampoSugerencias disabled={!editable} value={form.peligro} opciones={(cat?.peligros || []).map((p) => ({ valor: p.peligro, detalle: `${p.clase} · ${p.riesgo}` }))} onChange={elegirPeligro} /></div>
                <div><label className={lbl}>Riesgo</label><input className={inp} disabled={!editable} value={form.riesgo} onChange={(e) => setForm({ ...form, riesgo: e.target.value })} /></div>
                <div><label className={lbl}>Situación</label><div className="flex flex-wrap gap-3 pt-2 text-xs">{SITUACIONES.map(([k, n]) => <label key={k} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" disabled={!editable} checked={form.situaciones.includes(k)} onChange={() => setForm({ ...form, situaciones: form.situaciones.includes(k) ? form.situaciones.filter((x) => x !== k) : [...form.situaciones, k] })} />{n}</label>)}</div></div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div><label className={lbl}>Consecuencia del riesgo</label><CampoAmpliable multilinea disabled={!editable} value={form.consecuencia} onChange={(v) => setForm({ ...form, consecuencia: v })} /></div>
                <div><label className={lbl}>Controles existentes</label><CampoAmpliable multilinea disabled={!editable} value={form.controles_existentes} onChange={(v) => setForm({ ...form, controles_existentes: v })} /></div>
              </div>
              <div><label className={lbl}>Requisito legal asociado</label><input className={inp} disabled={!editable} value={form.requisito_legal} onChange={(e) => setForm({ ...form, requisito_legal: e.target.value })} /></div>
            </Seccion>
            <Seccion titulo="Evaluación del riesgo" extra={ini.n && <span className="text-[11px] text-slate-500">{ACCION[ini.n]}</span>}>
              <Indices form={form} setForm={setForm} editable={editable} />
            </Seccion>
            <Seccion titulo="Controles operacionales (jerarquía)" extra={noAceptable && <span className="text-[11px] font-semibold text-red-500">Riesgo no aceptable: registre controles, responsable y evaluación residual</span>}>
              <div className="grid gap-3 md:grid-cols-3">
                {[['control_eliminacion', 'Eliminación'], ['control_sustitucion', 'Sustitución'], ['control_ingenieria', 'Ingeniería'], ['control_administrativo', 'Control administrativo'], ['control_epp', 'Equipo de protección personal']].map(([k, n]) => (
                  <div key={k}><label className={lbl}>{n}</label><CampoAmpliable multilinea disabled={!editable} value={form[k]} onChange={(v) => setForm({ ...form, [k]: v })} /></div>
                ))}
                <div className="md:col-span-3"><label className={lbl}>Responsable(s) de los controles (puestos)</label>
                  <div className="grid max-h-24 gap-1 overflow-y-auto rounded border border-slate-200 p-2 text-xs md:grid-cols-4 dark:border-slate-700">
                    {puestos.filter((p) => p.tipo === 'propio').map((p) => <label key={p.id} className="flex items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" disabled={!editable} checked={form.responsables.includes(p.id)} onChange={() => setForm({ ...form, responsables: form.responsables.includes(p.id) ? form.responsables.filter((x) => x !== p.id) : [...form.responsables, p.id] })} />{p.nombre}</label>)}
                  </div>
                  {d?.responsable && <p className="mt-1 text-[11px] text-slate-400">En la matriz en Excel: {d.responsable.replace(/\n/g, ' · ')}</p>}
                </div>
              </div>
            </Seccion>
            <Seccion titulo="Evaluación del riesgo residual" extra={res.n && <span className="text-[11px] text-slate-500">{ACCION[res.n]}</span>}>
              <Indices form={form} setForm={setForm} pre="r_" editable={editable} />
            </Seccion>
            {d?.historial?.length > 0 && <Seccion titulo="Historial">{d.historial.slice().reverse().map((h, i) => <p key={i}>{(h.fecha || '').slice(0, 10)} · {h.usuario} · <strong>{h.accion}</strong>{h.campos ? `: ${h.campos}` : ''}{h.de ? ` (nivel ${h.de} → ${h.a})` : ''}{h.residual ? ` (residual ${h.residual})` : ''}{h.motivo ? `: ${h.motivo}` : ''}</p>)}</Seccion>}
            {editable && (
              <div className="flex justify-end gap-2">
                {d && <button className="btn-secondary mr-auto text-red-500" onClick={retirar}><Trash2 className="h-4 w-4" /> Retirar</button>}
                <button className="btn-secondary" onClick={() => { setForm(null); setD(null) }}>Cerrar</button>
                <button className="btn-primary" disabled={!form.area.trim() || !form.actividad.trim() || !form.peligro.trim() || !form.riesgo.trim()} onClick={guardar}>Guardar</button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ---------------------------------------------------------------------- ATS */
const ATS_VACIO = { lugar_ejecucion: 'instalaciones', formato: 'metrindust', cliente: '', ats_tipo: '', zona: '', fecha: new Date().toISOString().slice(0, 10), hora_inicio: '', hora_fin: '', tarea: '', lugar: '', orden_trabajo: '', empresa: 'METRINDUST S.A.C.', planificado: 'si', tipos_trabajo: [], tipo_otro: '', proceso: '', filas_iperc: [], ejecutantes: [], comentarios: '', equipos: [], responsable_cliente: '', ssoma_cliente: '' }
const PASO_VACIO = { etapa: '', peligros: '', riesgos: '', severidad: '', probabilidad: '', medidas: '', r_severidad: '', r_probabilidad: '' }
// Datos que se pueden transcribir mientras el ATS está en campo.
const CAMPOS_EN_CAMPO = ['ejecutantes', 'comentarios', 'equipos', 'fecha', 'hora_inicio', 'hora_fin', 'responsable_cliente', 'ssoma_cliente', 'filas_iperc']

function SelectorFilasIperc({ cat, valor, onChange, disabled }) {
  const [area, setArea] = useState('')
  const [filas, setFilas] = useState([])
  useEffect(() => { if (area) api.sst.filas(`?area=${encodeURIComponent(area)}`).then(setFilas).catch(() => {}); else setFilas([]) }, [area])
  return (
    <div>
      <select className={inp} disabled={disabled} value={area} onChange={(e) => setArea(e.target.value)}><option value="">Elegir área de la matriz…</option>{(cat?.areas || []).map((a) => <option key={a} value={a}>{a}</option>)}</select>
      {filas.length > 0 && <div className="mt-1 max-h-28 overflow-y-auto rounded border border-slate-200 p-2 text-xs dark:border-slate-700">{filas.map((f) => <label key={f.id} className="flex items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" disabled={disabled} checked={valor.includes(f.id)} onChange={() => onChange(valor.includes(f.id) ? valor.filter((x) => x !== f.id) : [...valor, f.id])} />{f.codigo} · {f.peligro.slice(0, 60)}</label>)}</div>}
      {valor.length > 0 && <p className="mt-1 text-[11px] text-slate-500">{valor.length} fila(s) seleccionada(s)</p>}
    </div>
  )
}

function Ats({ cat, procesos, confirmar, setError, abrirPdf, puedeCrear, puedeEditar }) {
  const [items, setItems] = useState([])
  const [tipos, setTipos] = useState([])
  const [estado, setEstado] = useState('')
  const [lugarF, setLugarF] = useState('')
  const [buscar, setBuscar] = useState('')
  const [d, setD] = useState(null)
  const [form, setForm] = useState(null)
  const [paso, setPaso] = useState(null)
  const [recep, setRecep] = useState(null)
  const [trabajadores, setTrabajadores] = useState([])
  useEffect(() => { api.org.trabajadores().then(setTrabajadores).catch(() => {}) }, [])
  const [err, setErr] = useState('')
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const p = new URLSearchParams(); if (estado) p.set('estado', estado); if (lugarF) p.set('lugar', lugarF); if (buscar) p.set('buscar', buscar)
    setItems(await ultima(api.sst.ats(`?${p}`)))
  }, [estado, lugarF, buscar])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  useEffect(() => { api.sst.tipos().then(setTipos).catch(() => {}) }, [])

  const abrir = async (id) => { setErr(''); setForm(null); setPaso(null); setRecep(null); setD(await api.sst.unAts(id)) }
  const enPrep = d?.estado === 'borrador' && puedeEditar
  const enCampo = d?.estado === 'en_campo' && puedeEditar
  const pasosEditables = Boolean(d?.pasos_editables) && puedeEditar
  const editarGeneral = () => setForm({ id: d.id, estado: d.estado, ...Object.fromEntries(Object.keys(ATS_VACIO).map((k) => [k, d[k] ?? ATS_VACIO[k]])), ejecutantes: (d.ejecutantes || []).map((e) => (e.trabajador && trabajadores.find((t) => t.id === e.trabajador)?.nombre_completo) || e.nombre || '') })
  const bloqueado = (k) => Boolean(form?.id) && form.estado !== 'borrador' && !CAMPOS_EN_CAMPO.includes(k)
  const guardar = async () => {
    setErr('')
    let datos = { ...form, proceso: form.proceso || null, ats_tipo: form.ats_tipo || null, hora_inicio: form.hora_inicio || null, hora_fin: form.hora_fin || null,
      ejecutantes: (form.ejecutantes || []).map((n) => n.trim()).filter(Boolean).map((nombre) => { const t = trabajadores.find((x) => x.nombre_completo === nombre); return t ? { trabajador: t.id } : { nombre } }), equipos: (form.equipos || []).map((n) => n.trim()).filter(Boolean) }
    delete datos.estado
    if (datos.lugar_ejecucion !== 'campo') datos.formato = 'metrindust'
    if (form.id) { delete datos.ats_tipo; if (form.estado !== 'borrador') datos = Object.fromEntries(Object.entries(datos).filter(([k]) => CAMPOS_EN_CAMPO.includes(k))) }
    try {
      const r = form.id ? await api.sst.editarAts(form.id, datos) : await api.sst.crearAts(datos)
      setForm(null); await cargar(); setD(await api.sst.unAts(r.id))
    } catch (e) { setErr(e.message) }
  }
  const accion = async (nombre, datos) => { setErr(''); try { const r = await api.sst.accionAts(d.id, nombre, datos); setD(r); await cargar(); return r } catch (e) { setErr(e.message); return null } }
  const guardarPaso = async () => {
    const datos = { ...paso }
    ;['severidad', 'probabilidad', 'r_severidad', 'r_probabilidad'].forEach((k) => { datos[k] = datos[k] === '' || datos[k] == null ? null : Number(datos[k]) })
    if (await accion(paso.paso_id ? 'editar_paso' : 'agregar_paso', datos)) setPaso(null)
  }
  const pedirClave = (titulo, mensaje) => confirmar({ titulo, mensaje, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
  const validar = async () => {
    const clave = await pedirClave('Validar el ATS', 'Como supervisor o prevencionista de SST, confirma que las etapas, peligros y medidas de control fueron revisados con el personal antes de iniciar la tarea. El ATS queda de solo lectura.')
    if (clave !== null) accion('validar', { password: clave })
  }
  const enviar = async () => {
    const msj = d.formato === 'cliente' ? 'En campo se llenará el formato del cliente. Al volver, se adjunta firmado.' : 'Se imprime prellenado para llenarlo y firmarlo en el lugar. La preparación queda cerrada; en campo solo se transcribe lo que cambie.'
    if (!await confirmar({ titulo: 'Enviar a campo', mensaje: msj, textoConfirmar: 'Enviar' })) return
    const r = await accion('enviar_a_campo')
    if (r && r.formato === 'metrindust') abrirPdf(api.sst.atsPdf(r.id))
  }
  const recibir = async () => {
    setErr('')
    const fd = new FormData()
    if (recep.archivo) fd.append('evidencia', recep.archivo)
    if (recep.fecha_ejecucion) fd.append('fecha_ejecucion', recep.fecha_ejecucion)
    fd.append('observaciones', recep.observaciones || '')
    try { const r = await api.sst.recibirAts(d.id, fd); setD(r); setRecep(null); await cargar() } catch (e) { setErr(e.message) }
  }
  const observar = async () => {
    const m = await confirmar({ titulo: 'Devolver con observación', mensaje: 'El ATS vuelve a «En campo» para corregir el archivo o completar la transcripción.', textoConfirmar: 'Devolver', entrada: { etiqueta: 'Qué falta corregir', obligatorio: true, multilinea: true } })
    if (m !== null) accion('observar', { motivo: m })
  }
  const revisar = async () => {
    const obs = await confirmar({ titulo: 'Revisión de SST', mensaje: 'Revise el ATS firmado adjunto y la transcripción. Si hubo un riesgo intolerable o algo fuera de lo previsto, déjelo en las observaciones.', textoConfirmar: 'Siguiente', entrada: { etiqueta: 'Observaciones de la revisión (opcional)', multilinea: true } })
    if (obs === null) return
    const clave = await pedirClave('Firmar la revisión', 'El ATS queda revisado y de solo lectura.')
    if (clave !== null) accion('revisar', { password: clave, observaciones: obs })
  }
  const anular = async () => {
    const m = await confirmar({ titulo: 'Anular el ATS', mensaje: 'Queda como registro. Si cambiaron las condiciones del trabajo, elabore un ATS nuevo.', textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true, multilinea: true } })
    if (m !== null) accion('anular', { motivo: m })
  }
  const comoTipo = async () => {
    const n = await confirmar({ titulo: 'Guardar como ATS tipo', mensaje: 'Las etapas, el tipo de trabajo, el proceso y las filas IPERC de este ATS quedan como base para preparar los próximos.', textoConfirmar: 'Guardar', entrada: { etiqueta: 'Servicio (nombre del ATS tipo)', obligatorio: true } })
    if (n === null) return
    setErr('')
    try { await api.sst.accionAts(d.id, 'guardar_como_tipo', { nombre: n }); setTipos(await api.sst.tipos()); await confirmar({ titulo: 'ATS tipo guardado', mensaje: `«${n}» ya se puede elegir al preparar un ATS.`, textoConfirmar: 'Entendido' }) } catch (e) { setErr(e.message) }
  }
  const lista = (k, max) => (
    <div className="grid gap-1 md:grid-cols-3">
      {Array.from({ length: max }).map((_, i) => <input key={i} className={inp} disabled={bloqueado(k)} placeholder={`${i + 1}`} value={(form[k] || [])[i] || ''} onChange={(e) => { const arr = [...(form[k] || [])]; while (arr.length <= i) arr.push(''); arr[i] = e.target.value; setForm({ ...form, [k]: arr }) }} />)}
    </div>
  )
  const pv = paso ? { s: Number(paso.severidad) * Number(paso.probabilidad) || null, r: Number(paso.r_severidad) * Number(paso.r_probabilidad) || null } : {}
  const tipoSel = form && !form.id && form.ats_tipo ? tipos.find((t) => t.id === Number(form.ats_tipo)) : null

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-64 pl-9" placeholder="Código, tarea, zona, cliente u OT…" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <select className="input-esynapse w-40" value={estado} onChange={(e) => setEstado(e.target.value)}><option value="">Todo estado</option>{Object.entries(ESTADO_ATS).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select>
        <select className="input-esynapse w-44" value={lugarF} onChange={(e) => setLugarF(e.target.value)}><option value="">Campo e instalaciones</option><option value="campo">En campo</option><option value="instalaciones">En instalaciones</option></select>
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setD(null); setForm({ ...ATS_VACIO }) }}><Plus className="h-4 w-4" /> Nuevo ATS</button>}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Código</th><th className="px-2 text-right">Fecha</th><th className="px-2">Dónde</th><th className="px-2">Cliente</th><th className="px-2">Zona de trabajo</th><th className="px-2">Tarea</th><th className="px-2">OT</th><th className="px-2 text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id} onClick={() => abrir(a.id)} className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="whitespace-nowrap px-2 py-2 font-mono">{a.codigo}</td><td className="whitespace-nowrap px-2 text-right">{fecha(a.fecha)}</td>
                <td className="px-2">{a.lugar_ejecucion === 'campo' ? `Campo${a.formato === 'cliente' ? ' · formato del cliente' : ''}` : 'Instalaciones'}</td>
                <td className="px-2">{a.cliente || '—'}</td><td className="px-2">{a.zona}</td>
                <td className="max-w-md truncate px-2" title={a.tarea}>{a.tarea}</td><td className="px-2">{a.orden_trabajo || '—'}</td><td className="px-2 text-center"><Chip par={ESTADO_ATS[a.estado]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin ATS registrados</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal abierto={Boolean(form)} titulo={form?.id ? (form.estado === 'borrador' ? 'Datos del ATS' : 'Transcribir datos de campo') : 'Nuevo Análisis de Trabajo Seguro'} onCerrar={() => setForm(null)} ancho="max-w-4xl">
        {form && (
          <div className="space-y-3 text-sm">
            {form.id && form.estado !== 'borrador' && <p className="rounded bg-esynapse-600/10 px-3 py-2 text-xs text-slate-600 dark:text-slate-300">El ATS está en campo: la preparación quedó cerrada. Solo se transcribe lo que cambió en el lugar (personal, equipos, horario, firmantes del cliente, comentarios).</p>}
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Dónde se realiza</label><select className={inp} disabled={Boolean(form.id)} value={form.lugar_ejecucion} onChange={(e) => setForm({ ...form, lugar_ejecucion: e.target.value, formato: e.target.value === 'campo' ? form.formato : 'metrindust' })}>{(cat?.lugares_ats || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              {form.lugar_ejecucion === 'campo' && <div><label className={lbl}>Formato que se usará</label><select className={inp} disabled={Boolean(form.id)} value={form.formato} onChange={(e) => setForm({ ...form, formato: e.target.value })}>{(cat?.formatos_ats || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>}
              {form.lugar_ejecucion === 'campo' && <div><label className={lbl}>Cliente</label><input className={inp} disabled={bloqueado('cliente')} value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })} /></div>}
            </div>
            {!form.id && form.formato === 'metrindust' && (
              <div><label className={lbl}>Preparar desde un ATS tipo (opcional)</label>
                <select className={inp} value={String(form.ats_tipo || '')} onChange={(e) => setForm({ ...form, ats_tipo: e.target.value ? Number(e.target.value) : '' })}><option value="">— Sin ATS tipo: etapas desde cero —</option>{tipos.map((t) => <option key={t.id} value={t.id}>{t.nombre} ({t.pasos.length} etapas)</option>)}</select>
                {tipoSel && <p className="mt-1 text-[11px] text-slate-500">Se copiarán {tipoSel.pasos.length} etapas, el tipo de trabajo, el proceso y {tipoSel.filas_iperc.length} fila(s) IPERC; luego se ajustan.</p>}
              </div>
            )}
            <div className="grid gap-3 md:grid-cols-4">
              <div className="md:col-span-2"><label className={lbl}>Zona de trabajo</label><input className={inp} disabled={bloqueado('zona')} value={form.zona} onChange={(e) => setForm({ ...form, zona: e.target.value })} /></div>
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} disabled={bloqueado('fecha')} value={form.fecha || ''} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
              <div className="grid grid-cols-2 gap-1"><div><label className={lbl}>Inicio</label><input type="time" className={inp} value={form.hora_inicio || ''} onChange={(e) => setForm({ ...form, hora_inicio: e.target.value })} /></div><div><label className={lbl}>Fin</label><input type="time" className={inp} value={form.hora_fin || ''} onChange={(e) => setForm({ ...form, hora_fin: e.target.value })} /></div></div>
            </div>
            <div><label className={lbl}>Tarea a realizar</label><CampoAmpliable multilinea disabled={bloqueado('tarea')} value={form.tarea} onChange={(v) => setForm({ ...form, tarea: v })} /></div>
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>Lugar de servicio</label><input className={inp} disabled={bloqueado('lugar')} value={form.lugar} onChange={(e) => setForm({ ...form, lugar: e.target.value })} /></div>
              <div><label className={lbl}>Orden de trabajo</label><input className={inp} disabled={bloqueado('orden_trabajo')} value={form.orden_trabajo} onChange={(e) => setForm({ ...form, orden_trabajo: e.target.value })} /></div>
              <div><label className={lbl}>Empresa que realiza el servicio</label><input className={inp} disabled={bloqueado('empresa')} value={form.empresa} onChange={(e) => setForm({ ...form, empresa: e.target.value })} /></div>
              <div><label className={lbl}>Planificado</label><select className={inp} disabled={bloqueado('planificado')} value={form.planificado} onChange={(e) => setForm({ ...form, planificado: e.target.value })}><option value="si">Sí</option><option value="no">No</option><option value="emergencia">Emergencia</option></select></div>
            </div>
            {!tipoSel && <div><label className={lbl}>Tipo de trabajo</label>
              <div className="flex flex-wrap gap-3 text-xs">{(cat?.tipos_trabajo || []).map(([k, n]) => <label key={k} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" disabled={bloqueado('tipos_trabajo')} checked={form.tipos_trabajo.includes(k)} onChange={() => setForm({ ...form, tipos_trabajo: form.tipos_trabajo.includes(k) ? form.tipos_trabajo.filter((x) => x !== k) : [...form.tipos_trabajo, k] })} />{n}</label>)}</div>
              {form.tipos_trabajo.includes('otro') && <input className={`${inp} mt-1`} disabled={bloqueado('tipo_otro')} placeholder="Otro tipo de trabajo" value={form.tipo_otro} onChange={(e) => setForm({ ...form, tipo_otro: e.target.value })} />}
            </div>}
            {!tipoSel && <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Proceso</label><select className={inp} disabled={bloqueado('proceso')} value={String(form.proceso || '')} onChange={(e) => setForm({ ...form, proceso: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{procesos.filter((p) => p.is_active && !p.padre).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></div>
              <div><label className={lbl}>Filas IPERC relacionadas</label><SelectorFilasIperc cat={cat} valor={form.filas_iperc} onChange={(v) => setForm({ ...form, filas_iperc: v })} /></div>
            </div>}
            <div><label className={lbl}>Personal ejecutante (hasta 9) — elija de Trabajadores; escriba el nombre solo si es personal externo</label>
              <div className="grid gap-1 md:grid-cols-3">
                {Array.from({ length: 9 }).map((_, i) => {
                  const v = (form.ejecutantes || [])[i] || ''
                  const externo = v.trim() && !trabajadores.some((t) => t.nombre_completo === v)
                  return (
                    <div key={i} className="relative">
                      <CampoSugerencias value={v} placeholder={`${i + 1}`} opciones={trabajadores.map((t) => ({ valor: t.nombre_completo, detalle: t.puesto_nombre }))} onChange={(nv) => { const arr = [...(form.ejecutantes || [])]; while (arr.length <= i) arr.push(''); arr[i] = nv; setForm({ ...form, ejecutantes: arr }) }} />
                      {externo && <span className="absolute -top-2 right-2 rounded bg-amber-500/15 px-1 text-[11px] text-amber-600">externo</span>}
                    </div>
                  )
                })}
              </div>
            </div>
            <div><label className={lbl}>Equipos, herramientas o insumos (hasta 6)</label>{lista('equipos', 6)}</div>
            <div><label className={lbl}>Comentarios / observaciones</label><CampoAmpliable multilinea value={form.comentarios} onChange={(v) => setForm({ ...form, comentarios: v })} /></div>
            <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Responsable del servicio (cliente)</label><input className={inp} value={form.responsable_cliente} onChange={(e) => setForm({ ...form, responsable_cliente: e.target.value })} /></div>
              <div><label className={lbl}>Área de SSOMA (cliente)</label><input className={inp} value={form.ssoma_cliente} onChange={(e) => setForm({ ...form, ssoma_cliente: e.target.value })} /></div>
            </div>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" disabled={!form.zona.trim() || !form.tarea.trim()} onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>

      <Modal abierto={Boolean(d) && !form} titulo={d ? `${d.codigo} — ${d.tarea.slice(0, 70)}` : ''} onCerrar={() => setD(null)} panel ancho="max-w-6xl">
        {d && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Chip par={ESTADO_ATS[d.estado]} />
              <span className="rounded bg-slate-500/10 px-1.5 py-0.5 text-[11px] text-slate-500">{d.lugar_display}{d.lugar_ejecucion === 'campo' ? ` · ${d.formato_display}` : ''}</span>
              {d.ats_tipo_nombre && <span className="text-[11px] text-slate-500">Desde el ATS tipo «{d.ats_tipo_nombre}»</span>}
              {d.estado === 'validado' && <span className="flex items-center gap-1 text-[11px] text-slate-500"><Lock className="h-3 w-3" /> Validado por {d.firma_supervisor?.nombre} ({d.firma_supervisor?.sigla}) el {fechaHora(d.firma_supervisor?.fecha)}</span>}
              {d.estado === 'revisado' && <span className="flex items-center gap-1 text-[11px] text-slate-500"><Lock className="h-3 w-3" /> Revisado por {d.firma_revision?.nombre} ({d.firma_revision?.sigla}) el {fechaHora(d.firma_revision?.fecha)}</span>}
              {d.estado === 'anulado' && <span className="text-[11px] text-red-500">Anulado: {d.motivo_anulacion}</span>}
              <span className="ml-auto flex flex-wrap gap-2">
                {d.formato === 'metrindust' && <button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.sst.atsPdf(d.id))}><FileText className="h-3.5 w-3.5" /> Imprimir</button>}
                {d.evidencia_url && <a className="btn-secondary !py-1 text-xs" href={d.evidencia_url} target="_blank" rel="noreferrer"><FileText className="h-3.5 w-3.5" /> ATS firmado</a>}
                {(enPrep || enCampo) && <button className="btn-secondary !py-1 text-xs" onClick={editarGeneral}><Pencil className="h-3.5 w-3.5" /> {enPrep ? 'Datos generales' : 'Transcribir datos de campo'}</button>}
                {puedeCrear && d.pasos.length > 0 && <button className="btn-secondary !py-1 text-xs" onClick={comoTipo}><Plus className="h-3.5 w-3.5" /> Guardar como ATS tipo</button>}
              </span>
            </div>
            {err && <Aviso texto={err} />}
            <Seccion titulo="Datos generales">
              <div className="grid gap-x-4 md:grid-cols-4">
                <p><strong>Zona:</strong> {d.zona}</p><p><strong>Fecha:</strong> {fecha(d.fecha)} {d.hora_inicio ? `· ${d.hora_inicio.slice(0, 5)}` : ''}{d.hora_fin ? ` – ${d.hora_fin.slice(0, 5)}` : ''}</p>
                <p><strong>Lugar:</strong> {d.lugar || '—'}</p><p><strong>OT:</strong> {d.orden_trabajo || '—'}</p>
              </div>
              {d.cliente && <p><strong>Cliente:</strong> {d.cliente}</p>}
              <p><strong>Tarea:</strong> {d.tarea}</p>
              <p><strong>Tipo de trabajo:</strong> {(d.tipos_trabajo || []).map((k) => (cat?.tipos_trabajo || []).find(([x]) => x === k)?.[1] || k).join(', ') || '—'}{d.tipo_otro ? ` (${d.tipo_otro})` : ''} · <strong>Planificado:</strong> {{ si: 'Sí', no: 'No', emergencia: 'Emergencia' }[d.planificado]}</p>
              <p><strong>Personal ejecutante:</strong> {(d.ejecutantes || []).map((e) => `${e.nombre}${e.trabajador ? (e.puesto ? ` (${e.puesto})` : '') : ' (externo)'}`).join(', ') || '—'}</p>
              <p><strong>Equipos:</strong> {(d.equipos || []).join(', ') || '—'}</p>
              {d.filas_iperc_info.length > 0 && <p><strong>Filas IPERC:</strong> {d.filas_iperc_info.map((f) => `${f.codigo} (${f.peligro.slice(0, 40)})`).join(' · ')}</p>}
              {d.comentarios && <p><strong>Comentarios:</strong> {d.comentarios}</p>}
            </Seccion>
            <Seccion titulo="Etapas, peligros y medidas de control" extra={pasosEditables && !paso && <button className="btn-secondary !py-0.5 text-[11px]" onClick={() => setPaso({ ...PASO_VACIO })}><Plus className="h-3.5 w-3.5" /> Etapa</button>}>
              {d.formato === 'cliente' && d.pasos.length === 0 ? <p className="text-slate-400">Se llena en el formato del cliente: las etapas están en el ATS firmado adjunto.</p> : (
                <table className="tabla-ficha w-full text-xs">
                  <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="py-1">#</th><th>Etapa</th><th>Peligros</th><th>Riesgos</th><th className="text-center">S×P</th><th>Medidas de control</th><th className="text-center">Residual</th>{pasosEditables && <th />}</tr></thead>
                  <tbody>
                    {d.pasos.map((p) => (
                      <tr key={p.id} className="border-b border-slate-100 align-top dark:border-slate-800/60">
                        <td className="py-1">{p.orden}</td><td className="max-w-[14rem]">{p.etapa}</td><td>{p.peligros || '—'}</td><td>{p.riesgos || '—'}</td>
                        <td className="text-center">{p.valor ? <Chip par={NIVEL_ATS[p.nivel]} extra={` ${p.severidad}×${p.probabilidad}=${p.valor}`} /> : '—'}</td>
                        <td className="max-w-[16rem] whitespace-pre-wrap">{p.medidas || '—'}</td>
                        <td className="text-center">{p.r_valor ? <Chip par={NIVEL_ATS[p.r_nivel]} extra={` ${p.r_valor}`} /> : '—'}</td>
                        {pasosEditables && <td className="whitespace-nowrap"><button className="p-1" title="Corregir" onClick={() => setPaso({ paso_id: p.id, ...Object.fromEntries(Object.keys(PASO_VACIO).map((k) => [k, p[k] ?? ''])) })}><Pencil className="h-3.5 w-3.5" /></button><button className="p-1 text-red-500" title="Quitar" onClick={() => accion('quitar_paso', { paso_id: p.id })}><X className="h-3.5 w-3.5" /></button></td>}
                      </tr>
                    ))}
                    {d.pasos.length === 0 && <tr><td colSpan={8} className="py-4 text-slate-400">Sin etapas registradas</td></tr>}
                  </tbody>
                </table>
              )}
              {paso && (
                <div className="space-y-2 rounded-lg border border-esynapse-600/30 bg-esynapse-600/5 p-3">
                  <div className="grid gap-2 md:grid-cols-3">
                    <div><label className={lbl}>Etapa (descripción)</label><CampoAmpliable multilinea value={paso.etapa} onChange={(v) => setPaso({ ...paso, etapa: v })} /></div>
                    <div><label className={lbl}>Peligros</label><CampoAmpliable multilinea value={paso.peligros} onChange={(v) => setPaso({ ...paso, peligros: v })} /></div>
                    <div><label className={lbl}>Riesgos</label><CampoAmpliable multilinea value={paso.riesgos} onChange={(v) => setPaso({ ...paso, riesgos: v })} /></div>
                  </div>
                  <div className="grid items-end gap-2 md:grid-cols-6">
                    {[['severidad', 'Severidad (S)'], ['probabilidad', 'Probabilidad (P)']].map(([k, n]) => <div key={k}><label className={lbl}>{n}</label><select className={inp} value={paso[k] ?? ''} onChange={(e) => setPaso({ ...paso, [k]: e.target.value })}><option value="">—</option>{[1, 2, 3, 4].map((v) => <option key={v} value={v}>{v}</option>)}</select></div>)}
                    <div className="text-center text-xs"><p className="text-slate-500">R = S×P</p>{pv.s ? <Chip par={NIVEL_ATS[nivelAts(pv.s)]} extra={` ${pv.s}`} /> : '—'}</div>
                    {[['r_severidad', 'S con medidas'], ['r_probabilidad', 'P con medidas']].map(([k, n]) => <div key={k}><label className={lbl}>{n}</label><select className={inp} value={paso[k] ?? ''} onChange={(e) => setPaso({ ...paso, [k]: e.target.value })}><option value="">—</option>{[1, 2, 3, 4].map((v) => <option key={v} value={v}>{v}</option>)}</select></div>)}
                    <div className="text-center text-xs"><p className="text-slate-500">Residual</p>{pv.r ? <Chip par={NIVEL_ATS[nivelAts(pv.r)]} extra={` ${pv.r}`} /> : '—'}</div>
                  </div>
                  <div><label className={lbl}>Medidas de control</label><CampoAmpliable multilinea value={paso.medidas} onChange={(v) => setPaso({ ...paso, medidas: v })} /></div>
                  <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setPaso(null)}>Cancelar</button><button className="btn-primary" disabled={!paso.etapa.trim()} onClick={guardarPaso}>Guardar etapa</button></div>
                </div>
              )}
            </Seccion>
            {d.lugar_ejecucion === 'campo' && (d.fecha_recepcion || recep) && (
              <Seccion titulo="Recepción del ATS de campo">
                {d.fecha_recepcion && !recep && <>
                  <div className="grid gap-x-4 md:grid-cols-3"><p><strong>Ejecutado el:</strong> {fecha(d.fecha_ejecucion)}</p><p><strong>Recibido por:</strong> {d.recibido_por_nombre}</p><p><strong>Recepción:</strong> {fechaHora(d.fecha_recepcion)}</p></div>
                  {d.observaciones_campo && <p><strong>Observaciones de campo:</strong> {d.observaciones_campo}</p>}
                  {d.observaciones_revision && <p><strong>Observaciones de la revisión:</strong> {d.observaciones_revision}</p>}
                </>}
                {recep && (
                  <div className="space-y-2">
                    <div className="grid gap-3 md:grid-cols-3">
                      <div><label className={lbl}>ATS firmado (foto o escaneo){d.evidencia_url ? ' — ya hay uno: adjunte otro solo para reemplazarlo' : ''}</label><input type="file" accept="image/*,application/pdf" className="text-xs" onChange={(e) => setRecep({ ...recep, archivo: e.target.files[0] || null })} /></div>
                      <div><label className={lbl}>Fecha de ejecución</label><input type="date" className={inp} value={recep.fecha_ejecucion} onChange={(e) => setRecep({ ...recep, fecha_ejecucion: e.target.value })} /></div>
                    </div>
                    <div><label className={lbl}>Observaciones de campo (cambios, incidentes, condiciones distintas)</label><CampoAmpliable multilinea value={recep.observaciones} onChange={(v) => setRecep({ ...recep, observaciones: v })} /></div>
                    <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setRecep(null)}>Cancelar</button><button className="btn-primary" disabled={!recep.archivo && !d.evidencia_url} onClick={recibir}>Registrar recepción</button></div>
                  </div>
                )}
              </Seccion>
            )}
            {d.lugar_ejecucion === 'instalaciones' && (
              <Seccion titulo="Firmas">
                <div className="grid gap-x-4 md:grid-cols-3">
                  <p><strong>Responsable del servicio (cliente):</strong> {d.responsable_cliente || '—'}</p>
                  <p><strong>Área de SSOMA (cliente):</strong> {d.ssoma_cliente || '—'}</p>
                  <p><strong>Supervisor / prevencionista de SST:</strong> {d.supervisor_nombre || 'pendiente'}</p>
                </div>
                <p className="text-[11px] text-slate-400">Las firmas del personal ejecutante se recogen en el formato impreso.</p>
              </Seccion>
            )}
            {d.historial?.length > 0 && <Seccion titulo="Historial">{d.historial.slice().reverse().map((h, i) => <p key={i}>{(h.fecha || '').slice(0, 16).replace('T', ' ')} · {h.usuario} · <strong>{h.accion}</strong>{h.ats_tipo ? `: desde «${h.ats_tipo}»` : ''}{h.motivo ? `: ${h.motivo}` : ''}{h.archivo ? ` (${h.archivo})` : ''}</p>)}</Seccion>}
            {enPrep && d.lugar_ejecucion === 'instalaciones' && <BarraEtapa titulo="ATS en preparación" nota="Para validar: zona, tarea, personal y cada etapa con S, P y medidas de control; las etapas significativas o intolerables requieren la evaluación con medidas." botones={[
              { texto: 'Anular', accion: anular, secundario: true },
              { texto: 'Validar con firma', accion: validar }]} />}
            {enPrep && d.lugar_ejecucion === 'campo' && <BarraEtapa titulo="ATS en preparación" nota={d.formato === 'cliente' ? 'Se usará el formato del cliente. Registre zona, tarea, fecha y personal, y envíelo a campo.' : 'Revise las etapas (desde el ATS tipo o desde cero) y envíelo a campo: se imprime prellenado para llenarlo y firmarlo en el lugar.'} botones={[
              { texto: 'Anular', accion: anular, secundario: true },
              { texto: 'Enviar a campo', accion: enviar }]} />}
            {enCampo && !recep && <BarraEtapa titulo="ATS en campo" nota="Al volver: transcriba lo que cambió en el lugar y registre la recepción con el ATS firmado adjunto." botones={[
              { texto: 'Anular', accion: anular, secundario: true },
              { texto: 'Registrar recepción', accion: () => { setErr(''); setRecep({ archivo: null, fecha_ejecucion: d.fecha || '', observaciones: d.observaciones_campo || '' }) } }]} />}
            {d.estado === 'recibido' && puedeEditar && <BarraEtapa titulo="ATS recibido" nota="SST revisa el ATS firmado y la transcripción. Si falta algo (firma, archivo ilegible, etapas sin transcribir), devuélvalo con observación." botones={[
              { texto: 'Devolver con observación', accion: observar, secundario: true },
              { texto: 'Revisar con firma', accion: revisar }]} />}
            {d.estado === 'validado' && puedeEditar && <BarraEtapa titulo="ATS validado" nota="Si cambian las condiciones del trabajo, anúlelo y elabore uno nuevo." botones={[{ texto: 'Anular', accion: anular, secundario: true }]} />}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ---------------------------------------------------------------- ATS tipo */
const TIPO_VACIO = { nombre: '', descripcion: '', tipos_trabajo: [], proceso: '', filas_iperc: [], pasos: [] }

function AtsTipos({ cat, procesos, confirmar, setError, puedeCrear, puedeEditar, puedeEliminar }) {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(async () => setItems(await api.sst.tipos()), [])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  const guardar = async () => {
    setErr('')
    const datos = { ...form, proceso: form.proceso || null, pasos: form.pasos.map((p) => Object.fromEntries(Object.entries(p).map(([k, v]) => [k, ['severidad', 'probabilidad', 'r_severidad', 'r_probabilidad'].includes(k) ? (v === '' || v == null ? null : Number(v)) : v]))) }
    try { if (form.id) await api.sst.editarTipo(form.id, datos); else await api.sst.crearTipo(datos); setForm(null); await cargar() } catch (e) { setErr(e.message) }
  }
  const desactivar = async (t) => {
    if (!await confirmar({ titulo: 'Desactivar el ATS tipo', mensaje: `«${t.nombre}» deja de ofrecerse al preparar ATS; los ATS ya preparados no cambian.`, textoConfirmar: 'Desactivar', peligro: true })) return
    try { await api.sst.desactivarTipo(t.id); await cargar() } catch (e) { setError(e.message) }
  }
  const setPasoT = (i, k, v) => setForm({ ...form, pasos: form.pasos.map((p, j) => (j === i ? { ...p, [k]: v } : p)) })
  const mover = (i, delta) => { const arr = [...form.pasos]; const j = i + delta; if (j < 0 || j >= arr.length) return; [arr[i], arr[j]] = [arr[j], arr[i]]; setForm({ ...form, pasos: arr }) }
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><p className="text-xs text-slate-500">ATS base de cada servicio que se hace en campo: sus etapas, peligros, medidas y evaluación típicas. Al preparar un ATS se copia y se ajusta.</p>
        {puedeCrear && <button className="btn-primary ml-auto shrink-0 whitespace-nowrap" onClick={() => { setErr(''); setForm({ ...TIPO_VACIO }) }}><Plus className="h-4 w-4" /> Nuevo ATS tipo</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Servicio</th><th className="px-2">Descripción</th><th className="px-2">Proceso</th><th className="px-2">Etapas</th><th className="px-2 text-right">Filas IPERC</th><th className="px-2 text-right">ATS preparados</th><th /></tr></thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id} className="border-b border-slate-100 dark:border-slate-800/60">
                <td className="px-2 py-2 font-semibold">{t.nombre}</td><td className="max-w-md truncate px-2" title={t.descripcion}>{t.descripcion || '—'}</td><td className="px-2">{t.proceso_nombre || '—'}</td>
                <td className="px-2">{t.pasos.length}</td><td className="px-2 text-right">{t.filas_iperc.length}</td><td className="px-2 text-right">{t.n_ats}</td>
                <td className="whitespace-nowrap px-2">{puedeEditar && <button className="p-1" title="Corregir" onClick={() => { setErr(''); setForm({ id: t.id, nombre: t.nombre, descripcion: t.descripcion, tipos_trabajo: t.tipos_trabajo, proceso: t.proceso || '', filas_iperc: t.filas_iperc, pasos: t.pasos.map((p) => ({ ...PASO_VACIO, ...Object.fromEntries(Object.entries(p).map(([k, v]) => [k, v ?? ''])) })) }) }}><Pencil className="h-3.5 w-3.5" /></button>}
                  {puedeEliminar && <button className="p-1 text-red-500" title="Desactivar" onClick={() => desactivar(t)}><X className="h-3.5 w-3.5" /></button>}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={7} className="py-8 text-slate-400">Sin ATS tipo. Cree uno o guarde uno desde un ATS ya preparado.</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Corregir el ATS tipo' : 'Nuevo ATS tipo'} onCerrar={() => setForm(null)} ancho="max-w-6xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Servicio / nombre</label><input className={inp} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div>
              <div className="md:col-span-2"><label className={lbl}>Descripción</label><input className={inp} value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></div>
            </div>
            <div><label className={lbl}>Tipo de trabajo</label>
              <div className="flex flex-wrap gap-3 text-xs">{(cat?.tipos_trabajo || []).filter(([k]) => k !== 'otro').map(([k, n]) => <label key={k} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" checked={form.tipos_trabajo.includes(k)} onChange={() => setForm({ ...form, tipos_trabajo: form.tipos_trabajo.includes(k) ? form.tipos_trabajo.filter((x) => x !== k) : [...form.tipos_trabajo, k] })} />{n}</label>)}</div></div>
            <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Proceso</label><select className={inp} value={String(form.proceso || '')} onChange={(e) => setForm({ ...form, proceso: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{procesos.filter((p) => p.is_active && !p.padre).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></div>
              <div><label className={lbl}>Filas IPERC relacionadas</label><SelectorFilasIperc cat={cat} valor={form.filas_iperc} onChange={(v) => setForm({ ...form, filas_iperc: v })} /></div>
            </div>
            <Seccion titulo={`Etapas (${form.pasos.length})`} extra={<button className="btn-secondary !py-0.5 text-[11px]" onClick={() => setForm({ ...form, pasos: [...form.pasos, { ...PASO_VACIO }] })}><Plus className="h-3.5 w-3.5" /> Etapa</button>}>
              {form.pasos.length === 0 && <p className="text-slate-400">Agregue las etapas del servicio.</p>}
              {form.pasos.map((p, i) => {
                const v = Number(p.severidad) * Number(p.probabilidad) || null; const rv = Number(p.r_severidad) * Number(p.r_probabilidad) || null
                return (
                  <div key={i} className="space-y-2 rounded border border-slate-200 p-2 dark:border-slate-700">
                    <div className="flex items-center gap-2"><strong>{i + 1}.</strong><input className={`${inp} flex-1`} placeholder="Etapa (descripción de la actividad)" value={p.etapa} onChange={(e) => setPasoT(i, 'etapa', e.target.value)} />
                      <button className="p-1 text-slate-400" title="Subir" onClick={() => mover(i, -1)}>↑</button><button className="p-1 text-slate-400" title="Bajar" onClick={() => mover(i, 1)}>↓</button>
                      <button className="p-1 text-red-500" title="Quitar" onClick={() => setForm({ ...form, pasos: form.pasos.filter((_, j) => j !== i) })}><X className="h-3.5 w-3.5" /></button></div>
                    <div className="grid gap-2 md:grid-cols-3">
                      <input className={inp} placeholder="Peligros" value={p.peligros} onChange={(e) => setPasoT(i, 'peligros', e.target.value)} />
                      <input className={inp} placeholder="Riesgos" value={p.riesgos} onChange={(e) => setPasoT(i, 'riesgos', e.target.value)} />
                      <input className={inp} placeholder="Medidas de control" value={p.medidas} onChange={(e) => setPasoT(i, 'medidas', e.target.value)} />
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      {[['severidad', 'S'], ['probabilidad', 'P']].map(([k, n]) => <label key={k} className="flex items-center gap-1">{n}<select className="input-esynapse w-16" value={p[k] ?? ''} onChange={(e) => setPasoT(i, k, e.target.value)}><option value="">—</option>{[1, 2, 3, 4].map((x) => <option key={x} value={x}>{x}</option>)}</select></label>)}
                      {v ? <Chip par={NIVEL_ATS[nivelAts(v)]} extra={` ${v}`} /> : null}
                      <span className="ml-3 text-slate-500">Con medidas:</span>
                      {[['r_severidad', 'S'], ['r_probabilidad', 'P']].map(([k, n]) => <label key={k} className="flex items-center gap-1">{n}<select className="input-esynapse w-16" value={p[k] ?? ''} onChange={(e) => setPasoT(i, k, e.target.value)}><option value="">—</option>{[1, 2, 3, 4].map((x) => <option key={x} value={x}>{x}</option>)}</select></label>)}
                      {rv ? <Chip par={NIVEL_ATS[nivelAts(rv)]} extra={` ${rv}`} /> : null}
                    </div>
                  </div>
                )
              })}
            </Seccion>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" disabled={!form.nombre.trim() || form.pasos.some((p) => !p.etapa.trim())} onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ------------------------------------------------------------------ Puestos */
// Los puestos vienen de Organización y personal; aquí se ve cuánto los cubre la matriz IPERC.
function Puestos({ puestos }) {
  const [cobertura, setCobertura] = useState(null)
  useEffect(() => { api.sst.porPuesto().then(setCobertura).catch(() => {}) }, [])
  const grupos = useMemo(() => [['propio', 'Personal de la empresa'], ['tercero', 'Terceros / contratistas']].map(([k, n]) => [n, puestos.filter((p) => p.tipo === k)]), [puestos])
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">Los puestos se mantienen en <Link to="/organizacion" className="text-esynapse-500 underline">Organización y personal</Link> (los usa todo el sistema). Aquí se ve en cuántas filas de la matriz IPERC figura cada uno{cobertura ? `; además, ${cobertura.todos_los_puestos} filas aplican a todos los puestos` : ''}.</p>
      <div className="grid gap-3 md:grid-cols-2">
        {grupos.map(([n, lista]) => (
          <div key={n} className="card-esynapse overflow-x-auto">
            <p className="px-3 pt-3 text-xs font-semibold text-slate-500 dark:text-slate-400">{n} ({lista.length})</p>
            <table className="tabla-sig w-full text-xs">
              <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Puesto</th><th className="px-2">Área</th><th className="px-2 text-right">Filas IPERC</th><th className="px-2 text-right">Trabajadores</th></tr></thead>
              <tbody>
                {lista.map((p) => {
                  const nf = cobertura?.por_puesto?.[String(p.id)] || 0
                  return (
                    <tr key={p.id} className="border-b border-slate-100 dark:border-slate-800/60">
                      <td className="px-2 py-1.5">{p.nombre}</td><td className="px-2">{p.area_nombre || '—'}</td>
                      <td className="px-2 text-right">{nf || <span className="text-amber-500" title="Solo le aplican las filas de «todos los puestos»">0</span>}</td><td className="px-2 text-right">{p.n_trabajadores}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ Resumen */
function Resumen() {
  const [r, setR] = useState(null)
  const [ra, setRa] = useState(null)
  useEffect(() => { api.sst.resumen().then(setR).catch(() => {}); api.sst.atsResumen().then(setRa).catch(() => {}) }, [])
  if (!r) return <p className="text-sm text-slate-400">Cargando…</p>
  const tot = (clave) => r.areas.reduce((acc, a) => { Object.entries(a[clave]).forEach(([k, v]) => { acc[k] = (acc[k] || 0) + v }); return acc }, {})
  const niveles = tot('niveles'); const sit = tot('situacion')
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-5">
        {Object.entries(SITUACION).map(([k, [n, c]]) => <div key={k} className="card-esynapse p-3"><p className="text-xs text-slate-500 dark:text-slate-400">{n}</p><p className={`text-2xl font-bold ${c.split(' ').filter((x) => x.startsWith('text-')).join(' ')}`}>{sit[k] || 0}</p></div>)}
        <div className="card-esynapse p-3"><p className="text-xs text-slate-500 dark:text-slate-400">Filas vigentes</p><p className="text-2xl font-bold">{r.total}</p></div>
      </div>
      {ra && (
        <div className="card-esynapse space-y-2 p-3 text-xs">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Análisis de Trabajo Seguro</p>
          <div className="flex flex-wrap gap-2">{Object.entries(ESTADO_ATS).map(([k, par]) => <Chip key={k} par={par} extra={` ${ra.por_estado[k] || 0}`} />)}</div>
          {ra.por_revisar > 0 && <p className="text-amber-600 dark:text-amber-400">{ra.por_revisar} ATS recibido(s) de campo pendiente(s) de revisión de SST.</p>}
          {ra.sin_recibir.length > 0 ? <p className="text-red-600 dark:text-red-400">Trabajos en campo sin ATS recibido: {ra.sin_recibir.map((a) => `${a.codigo} (${a.cliente || a.zona}, hace ${a.dias} día(s))`).join(' · ')}</p> : <p className="text-slate-400">Sin trabajos en campo pendientes de recibir.</p>}
        </div>
      )}
      {r.areas.some((a) => a.aprobacion?.estado !== 'aprobada') && <p className="rounded-lg bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300">{r.areas.filter((a) => a.aprobacion?.estado !== 'aprobada').length} hoja(s) de la matriz IPERC pendiente(s) de aprobación del Comité de SST: {r.areas.filter((a) => a.aprobacion?.estado !== 'aprobada').map((a) => a.area).join(', ')}.</p>}
      <div className="card-esynapse flex flex-wrap items-center gap-2 p-3 text-xs"><span className="text-slate-500">Nivel inicial:</span>{Object.entries(NIVEL).map(([k, par]) => <Chip key={k} par={par} extra={` ${niveles[k] || 0}`} />)}<span className="text-slate-400">· sin evaluar {niveles.sin || 0}</span></div>
      <div className="card-esynapse overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">Área</th><th className="px-2">Filas</th>{Object.keys(NIVEL).map((k) => <th key={k} className="px-2">{k}</th>)}<th className="px-2">Sin evaluar</th><th className="px-2">Requiere control</th><th className="px-2">Detenido</th><th className="px-2">Aprobación del Comité</th></tr></thead>
          <tbody>
            {r.areas.map((a) => (
              <tr key={a.area} className="border-b border-slate-100 dark:border-slate-800/60">
                <td className="px-2 py-1.5">{a.area}</td><td className="px-2">{a.total}</td>
                {Object.keys(NIVEL).map((k) => <td key={k} className="px-2">{a.niveles[k] ? <Chip par={NIVEL[k]} extra={` ${a.niveles[k]}`} /> : '—'}</td>)}
                <td className="px-2">{a.niveles.sin || '—'}</td><td className="px-2">{a.situacion.requiere_control || '—'}</td><td className="px-2">{a.situacion.trabajo_detenido || '—'}</td>
                <td className="whitespace-nowrap px-2"><Chip par={EST_APROB[a.aprobacion?.estado]} />{a.aprobacion?.fecha && <p className="text-[11px] text-slate-500 dark:text-slate-400">{fecha(a.aprobacion.fecha)}</p>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
