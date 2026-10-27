import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import { AlertTriangle, BarChart3, Check, FileText, Layers, Lightbulb, Lock, Pencil, Plus, Search, ShieldCheck, Trash2, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import { useCatalogoProcesos } from '../components/SelectorProceso.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora, hoy as hoyLocal } from '../lib/fecha.js'
import { sev } from '../lib/severidad.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import Pestanas from '../components/ui/Pestanas.jsx'
import { useAbrirDesdeEnlace } from '../lib/enlaces.js'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
const hoy = () => hoyLocal()

// Colores de nivel (escala de la matriz) y de situación (regla 10).
// Escala de severidad única del sistema: [nombre, etiqueta, celda del mapa de calor].
const NIVEL = {
  critico: sev(5, 'Crítico'),
  importante: sev(4, 'Importante'),
  moderado: sev(3, 'Moderado'),
  tolerado: sev(2, 'Tolerado'),
  no_significativo: sev(1, 'No significativo'),
}
const nivelDe = (v) => (!v ? '' : v >= 20 ? 'critico' : v >= 15 ? 'importante' : v >= 8 ? 'moderado' : v >= 4 ? 'tolerado' : 'no_significativo')
const SITUACION = {
  borrador: ['En registro', 'bg-slate-500/15 text-slate-500'],
  sin_tratamiento: ['Sin tratamiento', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  en_tratamiento: ['En tratamiento', 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300'],
  por_verificar: ['Por verificar eficacia', 'bg-violet-500/15 text-violet-600 dark:text-violet-400'],
  eficaz: ['Eficaz', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  no_eficaz: ['No eficaz', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  sin_cambio: ['Sin cambio', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  asumido: ['Asumido', 'bg-slate-500/15 text-slate-500'],
  aceptado: ['Aceptado', 'bg-slate-500/15 text-slate-500'],
  descartado: ['Descartado', 'bg-slate-500/15 text-slate-500'],
  en_cartera: ['En cartera', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  retirado: ['Retirado', 'bg-slate-500/15 text-slate-400'],
}
const REQUIERE = { si: 'Sí', no: 'No', en_cartera: 'En cartera' }
const DECISION = {
  en_evaluacion: ['En evaluación', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  se_implementa: ['Se implementa', 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300'],
  no_se_implementa: ['No se implementa', 'bg-slate-500/15 text-slate-500'],
}
const EF_MEJORA = {
  pendiente: ['Pendiente', 'bg-slate-500/15 text-slate-500'],
  lograda: ['Lograda', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  parcial: ['Parcial', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  no_lograda: ['No lograda', 'bg-red-500/15 text-red-600 dark:text-red-400'],
}
const ESTADO_ACCION = {
  pendiente: 'bg-slate-500/15 text-slate-500', en_proceso: 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  ejecutado: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400', no_aplica: 'bg-slate-500/10 text-slate-400',
}
const FUENTE_HALLAZGO_RYO = { auditoria_interna: 'auditoria_interna', auditoria_externa: 'evaluacion_de_organismo_externo', queja: 'queja_o_reclamo_del_cliente', revision_direccion: 'revision_por_la_direccion', indicador: 'analisis_de_datos_e_indicadores' }
const FUENTE_HALLAZGO_OM = { auditoria_interna: 'auditoria_interna', auditoria_externa: 'evaluacion_de_organismo_externo', queja: 'queja', revision_direccion: 'revision_por_la_direccion', indicador: 'analisis_de_datos' }
const CAMPOS_ID = ['proceso', 'contexto', 'categoria', 'fuente', 'fecha_identificacion', 'actividad', 'descripcion', 'causa', 'efecto', 'controles_existentes', 'probabilidad', 'impacto']

function Chip({ par, texto }) {
  if (!par) return <span className="text-slate-400">—</span>
  return <span className={`inline-block whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{texto || par[0]}</span>
}
function ChipNivel({ nivel, valor }) {
  if (!nivel) return <span className="text-slate-400">—</span>
  return <span className={`inline-block whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${NIVEL[nivel][1]}`}>{valor ? `${valor} · ` : ''}{NIVEL[nivel][0]}</span>
}
function Seccion({ titulo, tono, children, extra }) {
  const tonos = { ambar: 'border-amber-500/30 bg-amber-500/5', azul: 'border-esynapse-600/30 bg-esynapse-600/5', violeta: 'border-violet-500/30 bg-violet-500/5' }
  return (
    <div className={`rounded-lg border p-3 text-xs ${tonos[tono] || 'border-slate-200 dark:border-slate-800'}`}>
      <div className="mb-1.5 flex items-center justify-between gap-2"><p className="text-xs font-semibold text-slate-500 dark:text-slate-400">{titulo}</p>{extra}</div>
      <div className="space-y-2 text-slate-600 dark:text-slate-300">{children}</div>
    </div>
  )
}
function Dato({ etiqueta, valor }) {
  return <p><strong className="text-slate-700 dark:text-slate-200">{etiqueta}:</strong> <span className="whitespace-pre-wrap">{valor || '—'}</span></p>
}
const Escala = ({ valor, onChange, disabled }) => (
  <select className={inp} value={valor ?? ''} disabled={disabled} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
    <option value="">—</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
  </select>
)

export default function Riesgos() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const procesos = useCatalogoProcesos()
  const [pestana, setPestana] = useState('matriz')
  const [irRyo, setIrRyo] = useState(null)
  // Enlace directo ?abrir=<id> (búsqueda global): abre el riesgo u oportunidad en la matriz
  useAbrirDesdeEnlace((id) => { setPestana('matriz'); setIrRyo(id) })
  const [cat, setCat] = useState(null)
  const [usuarios, setUsuarios] = useState([])
  const [contexto, setContexto] = useState([])
  const [derivados, setDerivados] = useState([])
  const [revisiones, setRevisiones] = useState({ ryo: [], om: [] })
  const [error, setError] = useState('')
  const errorRef = useRef(null)
  useEffect(() => { if (error && errorRef.current) errorRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [error])

  const puedeCrear = tienePermiso('riesgos', 'crear')
  const puedeEditar = tienePermiso('riesgos', 'editar')
  const puedeAprobar = tienePermiso('riesgos', 'aprobar')

  const cargarComunes = useCallback(async () => {
    const [ctx, der, r1, r2] = await Promise.all([api.contextoRiesgos.listar(), api.riesgos.hallazgosDerivados(),
      api.revisionesRiesgos.listar('ryo'), api.revisionesRiesgos.listar('om')])
    setContexto(ctx.results ?? ctx); setDerivados(der); setRevisiones({ ryo: r1.results ?? r1, om: r2.results ?? r2 })
  }, [])
  useEffect(() => {
    api.riesgos.catalogos().then(setCat).catch(() => {})
    api.usuarios.listar().then((r) => setUsuarios(r.results ?? r)).catch(() => {})
    cargarComunes().catch(() => {})
  }, [cargarComunes])

  const abrirPdf = async (promesa) => {
    setError('')
    try { const url = URL.createObjectURL(await promesa); window.open(url, '_blank'); setTimeout(() => URL.revokeObjectURL(url), 60000) } catch (e) { setError(e.message) }
  }
  const firmar = (titulo, mensaje) => confirmar({ titulo, mensaje, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
  const registrarRevision = async (matriz, tipo) => {
    const obs = await confirmar({ titulo: tipo === 'supervision' ? 'Supervisión de la matriz' : 'Actualización de la matriz', mensaje: tipo === 'supervision' ? 'Control independiente del correcto llenado (Gerente Técnico). No lo firma quien actualizó la matriz.' : 'Registra la fecha y el responsable de la actualización que se imprimen en el formato.', textoConfirmar: 'Continuar', entrada: { etiqueta: 'Observaciones (opcional)', multilinea: true } })
    if (obs === null) return
    const clave = await firmar('Firmar', 'Confirme con su contraseña.')
    if (clave === null) return
    setError('')
    try { await api.revisionesRiesgos.registrar(tipo, { matriz, observaciones: obs, password: clave }); await cargarComunes() } catch (e) { setError(e.message) }
  }

  const comun = { cat, usuarios, procesos, contexto, confirmar, firmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeAprobar, cargarComunes }
  const matrizActual = pestana === 'mejoras' ? 'om' : 'ryo'
  const ult = (tipo) => revisiones[matrizActual].find((r) => r.tipo === tipo)

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <TituloModulo seccion="Estratégico" titulo="Riesgos y oportunidades" descripcion="Matriz de riesgos y oportunidades por proceso, su tratamiento y la eficacia de las acciones." />
        <Pestanas opciones={[['matriz', 'Matriz', Layers], ['mejoras', 'Oportunidades de mejora', Lightbulb], ['contexto', 'Contexto', Search], ['indicadores', 'Indicadores', BarChart3]]} valor={pestana} onChange={setPestana} />
      </div>

      {['matriz', 'mejoras'].includes(pestana) && (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-800">
          <span><strong>Actualización:</strong> {ult('actualizacion') ? `${fecha(ult('actualizacion').fecha)} · ${ult('actualizacion').responsable_nombre}` : '—'}</span>
          {matrizActual === 'ryo' && <span><strong>Supervisión:</strong> {ult('supervision') ? `${fecha(ult('supervision').fecha)} · ${ult('supervision').responsable_nombre}` : '—'}</span>}
          <span className="ml-auto flex gap-2">
            {puedeEditar && <button className="btn-secondary !py-1 text-xs" onClick={() => registrarRevision(matrizActual, 'actualizacion')}>Registrar actualización</button>}
            {matrizActual === 'ryo' && puedeAprobar && <button className="btn-secondary !py-1 text-xs" onClick={() => registrarRevision('ryo', 'supervision')}><ShieldCheck className="h-3.5 w-3.5" /> Supervisión</button>}
          </span>
        </div>
      )}
      {error && <p ref={errorRef} className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {pestana === 'matriz' && <Matriz {...comun} derivados={derivados} abrirId={irRyo} onAbierto={() => setIrRyo(null)} />}
      {pestana === 'mejoras' && <Mejoras {...comun} derivados={derivados} />}
      {pestana === 'contexto' && <Contexto {...comun} />}
      {pestana === 'indicadores' && <Indicadores cat={cat} />}
    </div>
  )
}

/* ------------------------------------------------------------------ Matriz */
function Matriz({ cat, usuarios, procesos, contexto, confirmar, firmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeAprobar, derivados, cargarComunes, abrirId, onAbierto }) {
  const [items, setItems] = useState([])
  const [f, setF] = useState({ tipo: '', proceso: '', categoria: '', nivel: '', situacion: '', buscar: '' })
  const [d, setD] = useState(null)
  const [nuevo, setNuevo] = useState(null)
  const [errLocal, setErrLocal] = useState('')

  const params = useCallback(() => { const p = new URLSearchParams(); Object.entries(f).forEach(([k, v]) => v && p.set(k, v)); return `?${p}` }, [f])
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => setItems(await ultima(api.riesgos.listar(params()))), [params])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  const abrir = async (id) => { setErrLocal(''); setD(await api.riesgos.detalle(id)) }
  useEffect(() => { if (abrirId) { abrir(abrirId).catch(() => {}); onAbierto() } }, [abrirId])  // eslint-disable-line react-hooks/exhaustive-deps

  const crear = async (e) => {
    e.preventDefault(); setErrLocal('')
    try { const r = await api.riesgos.crear({ ...nuevo, proceso: nuevo.proceso || null }); setNuevo(null); await cargar(); await cargarComunes(); await abrir(r.id) } catch (e2) { setErrLocal(e2.message) }
  }
  const desdeHallazgo = (h) => setNuevo({ tipo: 'riesgo', proceso: h.proceso_id ? String(h.proceso_id) : '', fuente: FUENTE_HALLAZGO_RYO[h.fuente] || 'actividad_del_proceso', descripcion: h.descripcion, hallazgo: h.id, fecha_identificacion: hoy() })
  const nombreSituacion = (s) => SITUACION[s]?.[0] || s

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-56 pl-9" placeholder="Código o descripción…" value={f.buscar} onChange={(e) => setF({ ...f, buscar: e.target.value })} /></div>
        <select className="input-esynapse w-36" value={f.tipo} onChange={(e) => setF({ ...f, tipo: e.target.value })}><option value="">Riesgos y oportunidades</option><option value="riesgo">Riesgos</option><option value="oportunidad">Oportunidades</option></select>
        <select className="input-esynapse w-52" value={f.proceso} onChange={(e) => setF({ ...f, proceso: e.target.value })}><option value="">Todos los procesos</option>{procesos.map((p) => <option key={p.id} value={p.id}>{p.padre ? `↳ ${p.nombre}` : p.nombre}</option>)}</select>
        <select className="input-esynapse w-48" value={f.categoria} onChange={(e) => setF({ ...f, categoria: e.target.value })}><option value="">Todas las categorías</option>{(cat?.categorias || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select>
        <select className="input-esynapse w-40" value={f.nivel} onChange={(e) => setF({ ...f, nivel: e.target.value })}><option value="">Todos los niveles</option>{Object.entries(NIVEL).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select>
        <select className="input-esynapse w-44" value={f.situacion} onChange={(e) => setF({ ...f, situacion: e.target.value })}><option value="">Toda situación</option>{Object.entries(SITUACION).filter(([k]) => k !== 'retirado').map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select>
        <span className="ml-auto flex gap-2">
          <button className="btn-secondary" onClick={() => abrirPdf(api.riesgos.matrizPdf(params()))}><FileText className="h-4 w-4" /> Imprimir matriz</button>
          {puedeCrear && <button className="btn-primary" onClick={() => { setErrLocal(''); setNuevo({ tipo: 'riesgo', proceso: '', categoria: '', fuente: '', descripcion: '', fecha_identificacion: hoy() }) }}><Plus className="h-4 w-4" /> Nuevo</button>}
        </span>
      </div>
      {derivados.length > 0 && puedeCrear && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs">
          <p className="mb-1 font-semibold">Observaciones y oportunidades de mejora derivadas desde Hallazgos, por registrar ({derivados.length})</p>
          {derivados.slice(0, 5).map((h) => (
            <div key={h.id} className="flex items-center gap-2 py-0.5"><span className="font-mono">{h.codigo}</span><span className="truncate">{h.descripcion}</span>
              <button className="btn-secondary ml-auto !py-0.5 text-[11px]" onClick={() => desdeHallazgo(h)}>Registrar como riesgo</button></div>
          ))}
          <p className="text-slate-500">Las oportunidades de mejora se registran desde la pestaña «Oportunidades de mejora».</p>
        </div>
      )}

      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
            <th className="px-2 py-2">Código</th><th className="px-2">Proceso</th><th className="px-2">Categoría</th><th className="px-2">Descripción</th>
            <th className="px-2 text-center">P×I / V×B</th><th className="px-2 text-center">¿Requiere acción?</th><th className="px-2">Estrategia</th><th className="px-2 text-right">Acciones</th><th className="px-2 text-center">Residual</th><th className="px-2 text-center">Situación</th>
          </tr></thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.id} onClick={() => abrir(r.id)} className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className={`whitespace-nowrap px-2 py-2 font-mono font-semibold ${r.tipo === 'riesgo' ? 'text-red-600' : 'text-sky-700 dark:text-sky-400'}`}>{r.codigo}</td>
                <td className="px-2">{r.proceso_nombre || '—'}</td>
                <td className="px-2">{r.categoria_display || '—'}</td>
                <td className="max-w-xs truncate px-2" title={r.descripcion}>{r.descripcion}</td>
                <td className="px-2 text-center"><ChipNivel nivel={r.nivel} valor={r.valor} /></td>
                <td className="px-2 text-center">{REQUIERE[r.requiere_accion] || '—'}</td>
                <td className="px-2">{r.estrategia_display || '—'}</td>
                <td className="px-2 text-right">{r.n_acciones || '—'}{r.vencidas > 0 && <span className="ml-1 whitespace-nowrap rounded bg-red-500/15 px-1 text-[11px] font-semibold text-red-600">{r.vencidas} vencida(s)</span>}</td>
                <td className="px-2 text-center"><ChipNivel nivel={r.nivel_residual} valor={r.valor_residual} /></td>
                <td className="px-2 text-center"><Chip par={SITUACION[r.estado === 'borrador' ? 'borrador' : r.situacion]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={10} className="py-8 text-slate-400">Sin registros</td></tr>}
          </tbody>
        </table>
        <p className="px-2 py-1 text-[11px] text-slate-400">{items.length} registro(s)</p>
      </div>

      <Modal abierto={Boolean(nuevo)} titulo="Nuevo riesgo u oportunidad" onCerrar={() => setNuevo(null)} ancho="max-w-2xl">
        {nuevo && (
          <form onSubmit={crear} className="space-y-3 text-sm">
            <div className="grid grid-cols-3 gap-3">
              <div><label className={lbl}>Tipo</label><select className={inp} value={nuevo.tipo} onChange={(e) => setNuevo({ ...nuevo, tipo: e.target.value })}><option value="riesgo">Riesgo</option><option value="oportunidad">Oportunidad</option></select></div>
              <div className="col-span-2"><label className={lbl}>Proceso</label><select className={inp} required value={nuevo.proceso} onChange={(e) => setNuevo({ ...nuevo, proceso: e.target.value })}><option value="">— Elige el proceso —</option>{procesos.map((p) => <option key={p.id} value={p.id}>{p.padre ? `   ${p.nombre}` : p.nombre}</option>)}</select></div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div><label className={lbl}>Categoría</label><select className={inp} value={nuevo.categoria} onChange={(e) => setNuevo({ ...nuevo, categoria: e.target.value })}><option value="">—</option>{(cat?.categorias || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Fuente / origen</label><select className={inp} value={nuevo.fuente} onChange={(e) => setNuevo({ ...nuevo, fuente: e.target.value })}><option value="">—</option>{(cat?.fuentes || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Fecha de identificación</label><input type="date" max={hoy()} className={inp} value={nuevo.fecha_identificacion} onChange={(e) => setNuevo({ ...nuevo, fecha_identificacion: e.target.value })} /></div>
            </div>
            <div><label className={lbl}>{nuevo.tipo === 'riesgo' ? 'Descripción del riesgo (qué puede suceder)' : 'Descripción de la oportunidad (acción a aprovechar)'}</label><CampoAmpliable multilinea rows={3} value={nuevo.descripcion} onChange={(v) => setNuevo({ ...nuevo, descripcion: v })} /></div>
            <p className="text-[11px] text-slate-500">Se crea en registro: completa la causa, el efecto, la valoración y el tratamiento en la ficha y luego «Registrar en la matriz».</p>
            {errLocal && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{errLocal}</p>}
            <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setNuevo(null)}>Cancelar</button><button className="btn-primary" disabled={!nuevo.descripcion.trim()}>Crear</button></div>
          </form>
        )}
      </Modal>

      <Modal abierto={Boolean(d)} titulo={d ? `${d.codigo} — ${d.descripcion.slice(0, 80)}` : ''} onCerrar={() => setD(null)} panel ancho="max-w-5xl">
        {d && <DetalleRiesgo d={d} setD={setD} recargar={cargar} {...{ cat, usuarios, procesos, contexto, confirmar, firmar, abrirPdf, puedeEditar, puedeAprobar, nombreSituacion, cargarComunes }} />}
      </Modal>
    </div>
  )
}

function DetalleRiesgo({ d, setD, recargar, cat, usuarios, procesos, contexto, confirmar, firmar, puedeEditar, puedeAprobar, cargarComunes }) {
  const [form, setForm] = useState({})
  const [trat, setTrat] = useState({})
  const [accF, setAccF] = useState(null)
  const [seg, setSeg] = useState(null)
  const [ver, setVer] = useState(null)
  const [error, setError] = useState('')
  const errRef = useRef(null)
  useEffect(() => { if (error && errRef.current) errRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [error])
  useEffect(() => {
    setForm(Object.fromEntries(CAMPOS_ID.map((k) => [k, d[k] ?? (k === 'contexto' ? [] : '')])))
    setTrat({ estrategia: d.estrategia || '', justificacion_aceptacion: d.justificacion_aceptacion || '' })
    setAccF(null); setSeg(null); setVer(null)
  }, [d])

  const borrador = d.estado === 'borrador'
  const idAbierta = d.etapas_abiertas.includes('identificacion') && puedeEditar
  const tratAbierto = d.etapas_abiertas.includes('tratamiento') && puedeEditar
  // Firmada la aceptación, la estrategia y su decisión quedan fijas (se cambian revalorando).
  const estrategiaEditable = tratAbierto && !d.firma_aceptacion?.nombre
  const esRiesgo = d.tipo === 'riesgo'
  const valorForm = form.probabilidad && form.impacto ? form.probabilidad * form.impacto : null
  const cambiosId = idAbierta && CAMPOS_ID.some((k) => JSON.stringify(k === 'contexto' ? [...(form[k] || [])].sort() : form[k] ?? '') !== JSON.stringify(k === 'contexto' ? [...(d[k] || [])].sort() : d[k] ?? ''))
  const cambiosTrat = tratAbierto && (trat.estrategia !== (d.estrategia || '') || trat.justificacion_aceptacion !== (d.justificacion_aceptacion || ''))
  const estrategias = (cat?.estrategias || []).filter(([k]) => (esRiesgo ? k !== 'incrementar' : k === 'incrementar'))
  const acciones = d.acciones
  const todasEjecutadas = acciones.length > 0 && acciones.every((a) => ['ejecutado', 'no_aplica'].includes(a.estado)) && acciones.some((a) => a.estado === 'ejecutado')
  const usuariosOpc = [['', '— Usuario —'], ...usuarios.map((u) => [String(u.id), u.nombre_completo])]

  const accion = async (fn) => {
    setError('')
    try { const r = await fn(); const n = r && r.id ? r : await api.riesgos.detalle(d.id); setD(n); await recargar() } catch (e) { setError(e.message) }
  }
  const guardarId = () => accion(() => api.riesgos.editar(d.id, { ...form, proceso: form.proceso || null, categoria: form.categoria || '', fuente: form.fuente || '' }))
  const guardarTrat = () => accion(() => api.riesgos.editar(d.id, trat))
  const conMotivo = (titulo, nombre, etiqueta, extra = {}) => async () => {
    const motivo = await confirmar({ titulo, mensaje: 'Queda en el historial del registro.', textoConfirmar: 'Continuar', entrada: { etiqueta, obligatorio: true, multilinea: true } })
    if (motivo !== null) accion(() => api.riesgos.accion(d.id, nombre, { motivo, ...extra }))
  }
  const revalorar = async () => {
    const p = await confirmar({ titulo: 'Revalorar', mensaje: esRiesgo ? 'Nueva probabilidad (1 a 5).' : 'Nueva viabilidad (1 a 5).', textoConfirmar: 'Siguiente', entrada: { etiqueta: esRiesgo ? 'Probabilidad' : 'Viabilidad', obligatorio: true, valorInicial: String(d.probabilidad || '') } })
    if (p === null) return
    const i = await confirmar({ titulo: 'Revalorar', mensaje: esRiesgo ? 'Nuevo impacto (1 a 5).' : 'Nuevo beneficio (1 a 5).', textoConfirmar: 'Siguiente', entrada: { etiqueta: esRiesgo ? 'Impacto' : 'Beneficio', obligatorio: true, valorInicial: String(d.impacto || '') } })
    if (i === null) return
    const motivo = await confirmar({ titulo: 'Revalorar', mensaje: `Nueva valoración ${p}×${i}. Si ya había una verificación, ese ciclo pasa al historial.`, textoConfirmar: 'Revalorar', entrada: { etiqueta: 'Motivo (revisión anual, cambio de contexto, materialización…)', obligatorio: true, multilinea: true } })
    if (motivo !== null) accion(() => api.riesgos.accion(d.id, 'revalorar', { probabilidad: p, impacto: i, motivo }))
  }
  const materializar = async () => {
    const desc = await confirmar({ titulo: 'Riesgo materializado', mensaje: 'Se registra un hallazgo (riesgo materializado) para su acción correctiva.', textoConfirmar: 'Registrar', peligro: true, entrada: { etiqueta: 'Cómo se materializó', obligatorio: true, multilinea: true } })
    if (desc !== null) accion(() => api.riesgos.accion(d.id, 'materializar', { descripcion: desc, fecha: hoy() }))
  }
  const aceptarGG = async () => {
    const clave = await firmar('Aceptar el riesgo', `Como Gerente General acepta ${d.codigo} (${NIVEL[d.nivel]?.[0]}). Decisión: ${d.justificacion_aceptacion}`)
    if (clave !== null) accion(() => api.riesgos.accion(d.id, 'aceptar_riesgo', { password: clave }))
  }
  const decidirCartera = (decision) => conMotivo(decision === 'abordar' ? 'Abordar la oportunidad' : 'Descartar la oportunidad', 'decidir_cartera', 'Motivo de la decisión', { decision })()
  const guardarAccion = async () => {
    const original = accF.id ? (d.acciones || []).find((x) => x.id === accF.id) : null
    let motivo
    // Mover el plazo de una acción que ya está en la matriz pide motivo (queda en el historial).
    if (original && d.estado !== 'borrador' && (original.fecha_maxima || '') !== (accF.fecha_maxima || '')) {
      motivo = await confirmar({ titulo: 'Cambio del plazo máximo', mensaje: `De ${fecha(original.fecha_maxima) || '—'} a ${fecha(accF.fecha_maxima) || '—'}. Queda en el historial del registro.`, textoConfirmar: 'Guardar', entrada: { etiqueta: 'Motivo del cambio', obligatorio: true, multilinea: true } })
      if (motivo === null) return
    }
    accion(() => api.riesgos.accion(d.id, accF.id ? 'editar_accion' : 'agregar_accion', { ...accF, accion_id: accF.id, responsable: accF.responsable || null, ...(motivo ? { motivo } : {}) }))
  }
  const quitarAccion = async (a) => { if (await confirmar({ titulo: 'Quitar acción', mensaje: `¿Quitar «${a.actividad}»?`, textoConfirmar: 'Quitar', peligro: true })) accion(() => api.riesgos.accion(d.id, 'quitar_accion', { accion_id: a.id })) }
  const guardarSeg = () => accion(() => { const fd = new FormData(); Object.entries(seg).forEach(([k, v]) => { if (v) fd.append(k, v) }); return api.riesgos.subir(d.id, 'seguimiento_accion', fd) })
  const incumplimiento = async (a) => { if (await confirmar({ titulo: 'Registrar incumplimiento', mensaje: `La acción no se ejecutó dentro de su plazo (${fecha(a.fecha_maxima)}). Se registra un hallazgo para su acción correctiva.`, textoConfirmar: 'Registrar', peligro: true })) accion(() => api.riesgos.accion(d.id, 'registrar_incumplimiento', { accion_id: a.id })) }
  const verificar = () => accion(() => api.riesgos.accion(d.id, 'verificar', ver))
  const anular = async () => { if (await confirmar({ titulo: 'Anular', mensaje: `¿Anular ${d.codigo}? Solo para un registro creado por error.`, textoConfirmar: 'Anular', peligro: true })) { try { await api.riesgos.anular(d.id); setD(null); await recargar() } catch (e) { setError(e.message) } } }

  const ctxPorTipo = useMemo(() => (cat?.tipos_contexto || []).map(([k, n]) => [n, contexto.filter((e) => e.tipo === k)]), [cat, contexto])
  const sel = (etq, val, on, ops, dis) => <div><label className={lbl}>{etq}</label><select className={inp} value={val ?? ''} disabled={dis} onChange={on}><option value="">—</option>{ops.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
  const area = (etq, k, dis) => <div><label className={lbl}>{etq}</label><CampoAmpliable multilinea rows={2} titulo={etq} disabled={dis} value={form[k] || ''} onChange={(v) => setForm({ ...form, [k]: v })} /></div>

  const barra = borrador ? (puedeEditar && { titulo: 'Registrar en la matriz', nota: 'Exige identificación, valoración y, si requiere acción, el tratamiento. Luego solo se corrige por revaloración.', bloqueo: cambiosId || cambiosTrat ? 'Guarde primero los cambios.' : '', botones: [{ texto: 'Anular', accion: anular, secundario: true }, { texto: 'Registrar en la matriz', accion: () => accion(() => api.riesgos.accion(d.id, 'registrar')) }] })
    : d.estado === 'vigente' ? (puedeEditar && { titulo: 'Registro en la matriz', nota: 'Revalore en la revisión anual o ante un cambio; retire si deja de aplicar.', botones: [
      { texto: 'Retirar', accion: conMotivo('Retirar el registro', 'retirar', 'Por qué deja de aplicar'), secundario: true },
      ...(esRiesgo ? [{ texto: 'Riesgo materializado', accion: materializar, secundario: true }] : []),
      { texto: 'Revalorar', accion: revalorar }] }) : null

  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-[11px] font-semibold ${esRiesgo ? 'bg-red-500/10 text-red-600' : 'bg-sky-500/10 text-sky-700 dark:text-sky-400'}`}>{d.tipo_display}</span>
        <ChipNivel nivel={d.nivel} valor={d.valor} />
        <span className="text-xs">¿Requiere acción? <strong>{REQUIERE[d.requiere_accion] || '—'}</strong></span>
        {!idAbierta && <span className="flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Identificación de solo lectura</span>}
        <span className="ml-auto"><Chip par={SITUACION[d.estado === 'vigente' ? d.situacion : d.estado]} /></span>
      </div>
      {error && <p ref={errRef} className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}

      <Seccion titulo="1. Identificación y análisis" tono={idAbierta ? 'ambar' : ''} extra={idAbierta && <button disabled={!cambiosId} onClick={guardarId} className="btn-primary !py-1 text-xs disabled:opacity-40">Guardar</button>}>
        {idAbierta ? (<>
          <div className="grid gap-3 md:grid-cols-4">
            <div className="md:col-span-2"><label className={lbl}>Proceso</label><select className={inp} value={form.proceso ?? ''} onChange={(e) => setForm({ ...form, proceso: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{procesos.map((p) => <option key={p.id} value={p.id}>{p.padre ? `   ${p.nombre}` : p.nombre}</option>)}</select></div>
            {sel('Categoría', form.categoria, (e) => setForm({ ...form, categoria: e.target.value }), cat?.categorias || [])}
            <div><label className={lbl}>Fecha de identificación</label><input type="date" max={hoy()} className={inp} value={form.fecha_identificacion || ''} onChange={(e) => setForm({ ...form, fecha_identificacion: e.target.value })} /></div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {sel('Fuente / origen de la identificación', form.fuente, (e) => setForm({ ...form, fuente: e.target.value }), cat?.fuentes || [])}
            {area('Actividad / etapa', 'actividad')}
          </div>
          {area(esRiesgo ? 'Descripción del riesgo' : 'Descripción de la oportunidad', 'descripcion')}
          <div className="grid gap-3 md:grid-cols-3">
            {area(esRiesgo ? 'Causa (por qué y cómo puede suceder)' : 'Causa / factor que la hace posible', 'causa')}
            {area(esRiesgo ? 'Efecto / consecuencia' : 'Beneficio esperado', 'efecto')}
            {area('Controles existentes', 'controles_existentes')}
          </div>
          <div>
            <label className={lbl}>Contexto y partes interesadas que lo originan</label>
            <div className="grid max-h-40 gap-x-4 overflow-y-auto rounded border border-slate-200 p-2 md:grid-cols-2 dark:border-slate-700">
              {ctxPorTipo.map(([n, els]) => els.length > 0 && (
                <div key={n} className="mb-1"><p className="text-xs font-semibold text-slate-500 dark:text-slate-400">{n}</p>
                  {els.map((e) => <label key={e.id} className="flex cursor-pointer items-start gap-1.5"><input type="checkbox" className="mt-0.5 accent-esynapse-600" checked={(form.contexto || []).includes(e.id)} onChange={() => setForm({ ...form, contexto: (form.contexto || []).includes(e.id) ? form.contexto.filter((x) => x !== e.id) : [...(form.contexto || []), e.id] })} /><span><strong>{e.codigo}</strong> {e.descripcion}</span></label>)}
                </div>
              ))}
            </div>
          </div>
          <div className="grid items-end gap-3 md:grid-cols-4">
            <div><label className={lbl}>{esRiesgo ? 'Probabilidad (1–5)' : 'Viabilidad (1–5)'}</label><Escala valor={form.probabilidad} onChange={(v) => setForm({ ...form, probabilidad: v })} /></div>
            <div><label className={lbl}>{esRiesgo ? 'Impacto (1–5)' : 'Beneficio (1–5)'}</label><Escala valor={form.impacto} onChange={(v) => setForm({ ...form, impacto: v })} /></div>
            <div className="md:col-span-2 pb-2">Nivel: <ChipNivel nivel={nivelDe(valorForm)} valor={valorForm} /></div>
          </div>
        </>) : (<>
          <div className="grid gap-x-4 md:grid-cols-3">
            <Dato etiqueta="Proceso" valor={d.proceso_nombre} /><Dato etiqueta="Categoría" valor={d.categoria_display} /><Dato etiqueta="Fecha" valor={fecha(d.fecha_identificacion)} />
            <Dato etiqueta="Fuente" valor={d.fuente_display} />{d.hallazgo_codigo && <Dato etiqueta="Hallazgo de origen" valor={d.hallazgo_codigo} />}
          </div>
          <Dato etiqueta="Actividad / etapa" valor={d.actividad} />
          <Dato etiqueta="Descripción" valor={d.descripcion} />
          <div className="grid gap-x-4 md:grid-cols-3"><Dato etiqueta="Causa" valor={d.causa} /><Dato etiqueta={esRiesgo ? 'Efecto' : 'Beneficio esperado'} valor={d.efecto} /><Dato etiqueta="Controles existentes" valor={d.controles_existentes} /></div>
          <Dato etiqueta="Contexto" valor={d.contexto_info.map((e) => `${e.codigo}: ${e.descripcion}`).join(' · ')} />
          <p><strong className="text-slate-700 dark:text-slate-200">Valoración inicial:</strong> {d.probabilidad ?? '—'} × {d.impacto ?? '—'} = <ChipNivel nivel={d.nivel} valor={d.valor} /></p>
        </>)}
      </Seccion>

      <Seccion titulo="2. Tratamiento" tono={tratAbierto ? 'azul' : ''} extra={estrategiaEditable && <button disabled={!cambiosTrat} onClick={guardarTrat} className="btn-primary !py-1 text-xs disabled:opacity-40">Guardar</button>}>
        {d.requiere_accion === 'en_cartera' && (
          <div className="rounded bg-amber-500/10 px-2 py-1.5">Oportunidad en cartera (moderada): la Alta Dirección decide si se aborda. {d.decision_cartera ? <strong>{d.decision_cartera === 'abordar' ? 'Se aborda' : 'Se descarta'}: {d.motivo_cartera}</strong> : (puedeAprobar && d.valor_residual == null && <span className="ml-2 inline-flex gap-1"><button className="btn-secondary !py-0.5 text-[11px]" onClick={() => decidirCartera('abordar')}>Abordar</button><button className="btn-secondary !py-0.5 text-[11px]" onClick={() => decidirCartera('descartar')}>Descartar</button></span>)}</div>
        )}
        {estrategiaEditable ? (
          <div className="grid gap-3 md:grid-cols-3">
            {sel('Estrategia', trat.estrategia, (e) => setTrat({ ...trat, estrategia: e.target.value }), estrategias)}
            {trat.estrategia === 'aceptar' && <div className="md:col-span-2"><label className={lbl}>Decisión documentada de aceptar el riesgo</label><CampoAmpliable multilinea value={trat.justificacion_aceptacion} onChange={(v) => setTrat({ ...trat, justificacion_aceptacion: v })} /></div>}
          </div>
        ) : <div className="grid gap-x-4 md:grid-cols-2"><Dato etiqueta="Estrategia" valor={d.estrategia_display} />{d.justificacion_aceptacion && <Dato etiqueta="Decisión de aceptar" valor={d.justificacion_aceptacion} />}</div>}
        {d.estrategia === 'aceptar' && ['importante', 'critico'].includes(d.nivel) && (
          <p className="rounded bg-slate-500/10 px-2 py-1.5">{d.firma_aceptacion?.nombre ? <><Check className="mr-1 inline h-3.5 w-3.5 text-emerald-600" />Aceptado por {d.firma_aceptacion.nombre} ({d.firma_aceptacion.sigla}) el {fechaHora(d.firma_aceptacion.fecha)}</> : <>Riesgo {NIVEL[d.nivel][0].toLowerCase()}: su aceptación la firma el Gerente General. {puedeAprobar && tratAbierto && !cambiosTrat && <button className="btn-primary ml-2 !py-0.5 text-[11px]" onClick={aceptarGG}>Firmar aceptación</button>}</>}</p>
        )}
        <table className="tabla-ficha w-full text-xs">
          <thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="py-1">Acción</th><th>Implementación documental</th><th>Responsable</th><th className="text-right">Fecha máx.</th><th>Recursos</th><th className="text-center">Estado</th><th /></tr></thead>
          <tbody>
            {acciones.map((a) => (
              <tr key={a.id} className="border-t border-slate-100 align-top dark:border-slate-800">
                <td className="py-1.5">{a.actividad}{a.observaciones && <p className="text-[11px] text-slate-500">{a.observaciones}{a.evidencia_url && <a className="ml-1 underline" href={a.evidencia_url} target="_blank" rel="noreferrer">evidencia</a>}</p>}</td>
                <td>{a.implementacion_documental || '—'}</td><td>{a.responsable_nombre || '—'}</td>
                <td className="text-right" className={a.vencida ? 'font-semibold text-red-600' : ''}>{fecha(a.fecha_maxima) || '—'}</td><td>{a.recursos || '—'}</td>
                <td className="text-center"><span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${ESTADO_ACCION[a.estado]}`}>{a.estado_display}</span>{a.fecha_ejecucion && <p className="text-[11px]">{fecha(a.fecha_ejecucion)}</p>}{a.hallazgo_codigo && <p className="text-[11px] text-red-600">{a.hallazgo_codigo}</p>}</td>
                <td className="whitespace-nowrap">
                  {tratAbierto && a.estado !== 'ejecutado' && <button title="Corregir" className="p-1" onClick={() => setAccF({ id: a.id, actividad: a.actividad, implementacion_documental: a.implementacion_documental, responsable: a.responsable || '', responsable_texto: a.responsable_texto, fecha_inicio: a.fecha_inicio || '', fecha_maxima: a.fecha_maxima || '', recursos: a.recursos })}><Pencil className="h-3.5 w-3.5" /></button>}
                  {borrador && puedeEditar && <button title="Quitar" className="p-1 text-red-500" onClick={() => quitarAccion(a)}><X className="h-3.5 w-3.5" /></button>}
                  {d.estado === 'vigente' && d.valor_residual == null && puedeEditar && !['ejecutado', 'no_aplica'].includes(a.estado) && <button className="btn-secondary !py-0.5 text-[11px]" onClick={() => setSeg({ accion_id: a.id, estado: 'ejecutado', fecha_ejecucion: hoy(), observaciones: '', evidencia: null })}>Seguimiento</button>}
                  {puedeEditar && !a.hallazgo_codigo && (a.vencida || (a.estado === 'ejecutado' && a.fecha_maxima && a.fecha_ejecucion > a.fecha_maxima)) && <button className="btn-secondary ml-1 !py-0.5 text-[11px] text-red-600" onClick={() => incumplimiento(a)}>Incumplimiento</button>}
                </td>
              </tr>
            ))}
            {acciones.length === 0 && <tr><td colSpan={7} className="py-2 text-slate-400">Sin acciones.</td></tr>}
          </tbody>
        </table>
        {tratAbierto && !accF && <button className="btn-secondary !py-1 text-xs" onClick={() => setAccF({ actividad: '', implementacion_documental: '', responsable: '', responsable_texto: '', fecha_inicio: hoy(), fecha_maxima: '', recursos: '' })}><Plus className="h-3.5 w-3.5" /> Agregar acción</button>}
        {accF && (
          <div className="space-y-2 rounded border border-slate-200 p-2 dark:border-slate-700">
            <div className="grid gap-2 md:grid-cols-2">
              <div><label className={lbl}>Acción o actividad</label><CampoAmpliable multilinea value={accF.actividad} onChange={(v) => setAccF({ ...accF, actividad: v })} /></div>
              <div><label className={lbl}>Implementación documental propuesta</label><CampoAmpliable multilinea value={accF.implementacion_documental} onChange={(v) => setAccF({ ...accF, implementacion_documental: v })} /></div>
            </div>
            <div className="grid gap-2 md:grid-cols-5">
              <div><label className={lbl}>Responsable</label><select className={inp} value={String(accF.responsable || '')} onChange={(e) => setAccF({ ...accF, responsable: e.target.value ? Number(e.target.value) : '' })}>{usuariosOpc.map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></div>
              <div><label className={lbl}>o cargo / nombre</label><input className={inp} value={accF.responsable_texto} onChange={(e) => setAccF({ ...accF, responsable_texto: e.target.value })} /></div>
              <div><label className={lbl}>Fecha de inicio</label><input type="date" className={inp} value={accF.fecha_inicio || ''} onChange={(e) => setAccF({ ...accF, fecha_inicio: e.target.value })} /></div>
              <div><label className={lbl}>Fecha máxima</label><input type="date" className={inp} value={accF.fecha_maxima || ''} onChange={(e) => setAccF({ ...accF, fecha_maxima: e.target.value })} /></div>
              <div><label className={lbl}>Recursos</label><input className={inp} value={accF.recursos} onChange={(e) => setAccF({ ...accF, recursos: e.target.value })} /></div>
            </div>
            <div className="flex justify-end gap-2"><button className="btn-secondary !py-1 text-xs" onClick={() => setAccF(null)}>Cancelar</button><button className="btn-primary !py-1 text-xs" disabled={!accF.actividad.trim()} onClick={guardarAccion}>Guardar acción</button></div>
          </div>
        )}
        {seg && (
          <div className="space-y-2 rounded border border-esynapse-600/30 p-2">
            <div className="grid gap-2 md:grid-cols-3">
              <div><label className={lbl}>Nuevo estado</label><select className={inp} value={seg.estado} onChange={(e) => setSeg({ ...seg, estado: e.target.value })}><option value="en_proceso">En proceso</option><option value="ejecutado">Ejecutado</option><option value="no_aplica">No aplica</option></select></div>
              {seg.estado === 'ejecutado' && <div><label className={lbl}>Fecha de ejecución</label><input type="date" max={hoy()} className={inp} value={seg.fecha_ejecucion} onChange={(e) => setSeg({ ...seg, fecha_ejecucion: e.target.value })} /></div>}
            </div>
            <CampoAmpliable multilinea placeholder="Evidencia / observaciones" value={seg.observaciones} onChange={(v) => setSeg({ ...seg, observaciones: v })} />
            <div className="flex flex-wrap items-center gap-2">
              <label className="btn-secondary !py-1 cursor-pointer text-xs">Adjuntar evidencia<input type="file" className="hidden" onChange={(e) => setSeg({ ...seg, evidencia: e.target.files[0] || null })} /></label>
              {seg.evidencia && <span className="text-[11px]">{seg.evidencia.name}</span>}
              <button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => setSeg(null)}>Cancelar</button><button className="btn-primary !py-1 text-xs" onClick={guardarSeg}>Registrar</button>
            </div>
          </div>
        )}
      </Seccion>

      {d.estado !== 'borrador' && (acciones.length > 0 || d.valor_residual != null) && (
        <Seccion titulo="3. Verificación de la eficacia (valoración residual)" tono={todasEjecutadas && d.valor_residual == null ? 'violeta' : ''}>
          {d.valor_residual != null ? (<>
            <div className="grid gap-x-4 md:grid-cols-3">
              <p><strong>Residual:</strong> {d.residual_probabilidad} × {d.residual_impacto} = <ChipNivel nivel={d.nivel_residual} valor={d.valor_residual} /></p>
              <Dato etiqueta="Fecha de verificación" valor={fecha(d.fecha_verificacion)} />
              <p><strong>Eficacia:</strong> <Chip par={SITUACION[d.eficacia]} /></p>
            </div>
            <Dato etiqueta="Evidencia" valor={d.evidencia_verificacion} />
            {['no_eficaz', 'sin_cambio'].includes(d.eficacia) && puedeEditar && <button className="btn-primary !py-1 text-xs" onClick={conMotivo('Nuevo tratamiento', 'nuevo_tratamiento', 'Motivo y enfoque del nuevo tratamiento')}>Iniciar nuevo tratamiento</button>}
          </>) : todasEjecutadas ? (puedeEditar && (ver ? (
            <div className="space-y-2">
              <div className="grid gap-2 md:grid-cols-3">
                <div><label className={lbl}>{esRiesgo ? 'Probabilidad residual' : 'Viabilidad residual'}</label><Escala valor={ver.residual_probabilidad} onChange={(v) => setVer({ ...ver, residual_probabilidad: v })} /></div>
                <div><label className={lbl}>{esRiesgo ? 'Impacto residual' : 'Beneficio residual'}</label><Escala valor={ver.residual_impacto} onChange={(v) => setVer({ ...ver, residual_impacto: v })} /></div>
                <div><label className={lbl}>Fecha de verificación</label><input type="date" max={hoy()} className={inp} value={ver.fecha_verificacion} onChange={(e) => setVer({ ...ver, fecha_verificacion: e.target.value })} /></div>
              </div>
              <CampoAmpliable multilinea placeholder="Evidencia: con qué se comprobó la eficacia" value={ver.evidencia} onChange={(v) => setVer({ ...ver, evidencia: v })} />
              <p className="text-[11px] text-slate-500">Se verifica tras tres meses de operación de la acción (o un ciclo completo del control).</p>
              <div className="flex justify-end gap-2"><button className="btn-secondary !py-1 text-xs" onClick={() => setVer(null)}>Cancelar</button><button className="btn-primary !py-1 text-xs" onClick={verificar}>Registrar verificación</button></div>
            </div>
          ) : <button className="btn-primary !py-1 text-xs" onClick={() => setVer({ residual_probabilidad: null, residual_impacto: null, fecha_verificacion: hoy(), evidencia: '' })}>Registrar verificación</button>))
            : <p className="text-slate-400">Se habilita cuando todas las acciones estén ejecutadas.</p>}
        </Seccion>
      )}

      {d.historial.length > 0 && (
        <Seccion titulo="Historial">
          {d.historial.slice().reverse().map((h, i) => <p key={i}>{fecha(h.fecha)} · {h.usuario} · <strong>{h.accion}</strong>{h.de ? ` ${h.de} → ${h.a}` : ''}{h.eficacia ? ` (${h.eficacia})` : ''}{h.hallazgo ? ` · ${h.hallazgo}` : ''}{h.motivo || h.descripcion ? `: ${h.motivo || h.descripcion}` : ''}</p>)}
        </Seccion>
      )}
      {barra && <BarraEtapa titulo={barra.titulo} nota={barra.nota} bloqueo={barra.bloqueo} botones={barra.botones} />}
    </div>
  )
}

/* ------------------------------------------------- Oportunidades de mejora */
function Mejoras({ cat, usuarios, procesos, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, derivados, cargarComunes }) {
  const [items, setItems] = useState([])
  const [buscar, setBuscar] = useState('')
  const [decision, setDecision] = useState('')
  const [d, setD] = useState(null)
  const [nuevo, setNuevo] = useState(null)
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const params = useCallback(() => { const p = new URLSearchParams(); if (buscar) p.set('buscar', buscar); if (decision) p.set('decision', decision); return `?${p}` }, [buscar, decision])
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => { const r = await ultima(api.mejoras.listar(params())); setItems(r.results ?? r) }, [params])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  const usuariosOpc = [['', '— Usuario —'], ...usuarios.map((u) => [String(u.id), u.nombre_completo])]

  const crear = async (e) => {
    e.preventDefault(); setErr('')
    try { const o = await api.mejoras.crear({ ...nuevo, proceso: nuevo.proceso || null }); setNuevo(null); await cargar(); await cargarComunes(); setD(o) } catch (e2) { setErr(e2.message) }
  }
  const accion = async (fn) => { setErr(''); try { const o = await fn(); setD(o); setForm(null); await cargar() } catch (e) { setErr(e.message) } }
  const desdeHallazgo = (h) => setNuevo({ proceso: h.proceso_id ? String(h.proceso_id) : '', fuente: FUENTE_HALLAZGO_OM[h.fuente] || 'actividad_del_proceso', detectado_por: '', descripcion: h.descripcion, situacion: `Hallazgo ${h.codigo} (${h.tipo}, ${h.fuente_display}).`, hallazgo: h.id, fecha_identificacion: hoy() })
  const ident = d && d.decision === 'en_evaluacion' && puedeEditar

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-64 pl-9" placeholder="Código o descripción…" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <select className="input-esynapse w-48" value={decision} onChange={(e) => setDecision(e.target.value)}><option value="">Toda decisión</option>{Object.entries(DECISION).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select>
        <span className="ml-auto flex gap-2">
          <button className="btn-secondary" onClick={() => abrirPdf(api.mejoras.matrizPdf(params()))}><FileText className="h-4 w-4" /> Imprimir matriz</button>
          {puedeCrear && <button className="btn-primary" onClick={() => { setErr(''); setNuevo({ proceso: '', fuente: '', detectado_por: '', descripcion: '', situacion: '', fecha_identificacion: hoy() }) }}><Plus className="h-4 w-4" /> Nueva oportunidad de mejora</button>}
        </span>
      </div>
      {derivados.length > 0 && puedeCrear && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs">
          <p className="mb-1 font-semibold">Derivadas desde Hallazgos, por registrar ({derivados.length})</p>
          {derivados.slice(0, 8).map((h) => <div key={h.id} className="flex items-center gap-2 py-0.5"><span className="font-mono">{h.codigo}</span><span className="truncate">{h.descripcion}</span><button className="btn-secondary ml-auto !py-0.5 text-[11px]" onClick={() => desdeHallazgo(h)}>Registrar como oportunidad de mejora</button></div>)}
        </div>
      )}
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-ficha w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
            <th className="px-2 py-2">Código</th><th className="px-2">Proceso</th><th className="px-2">Fuente</th><th className="px-2">Detectado por</th><th className="px-2 text-right">Fecha</th><th className="px-2">Descripción</th><th className="px-2 text-center">Decisión</th><th className="px-2">Responsable</th><th className="px-2 text-right">Fecha máx.</th><th className="px-2 text-center">Estado</th><th className="px-2">Eficacia</th>
          </tr></thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.id} onClick={() => { setErr(''); setForm(null); setD(o) }} className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="whitespace-nowrap px-2 py-2 font-mono font-semibold text-emerald-700 dark:text-emerald-400">{o.codigo}</td>
                <td className="px-2">{o.proceso_nombre || '—'}</td><td className="px-2">{o.fuente_display}</td><td className="px-2">{o.detectado_por || '—'}</td><td className="whitespace-nowrap px-2 text-right">{fecha(o.fecha_identificacion)}</td>
                <td className="max-w-sm truncate px-2" title={o.descripcion}>{o.descripcion}</td>
                <td className="px-2 text-center"><Chip par={DECISION[o.decision]} />{o.evaluacion_vencida && <span className="ml-1 text-[11px] font-semibold text-red-600">+1 año</span>}</td>
                <td className="px-2">{o.responsable_nombre || '—'}</td><td className="text-right" className={`whitespace-nowrap px-2 ${o.accion_vencida ? 'font-semibold text-red-600' : ''}`}>{fecha(o.fecha_maxima) || '—'}</td>
                <td className="px-2 text-center">{o.decision === 'se_implementa' ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${ESTADO_ACCION[o.estado_accion]}`}>{o.estado_accion_display}</span> : '—'}</td>
                <td className="px-2">{o.decision === 'se_implementa' ? <Chip par={EF_MEJORA[o.eficacia]} /> : '—'}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={11} className="py-8 text-slate-400">Sin oportunidades de mejora</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal abierto={Boolean(nuevo)} titulo="Nueva oportunidad de mejora" onCerrar={() => setNuevo(null)} ancho="max-w-2xl">
        {nuevo && (
          <form onSubmit={crear} className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-3">
              <div><label className={lbl}>Proceso</label><select className={inp} required value={nuevo.proceso} onChange={(e) => setNuevo({ ...nuevo, proceso: e.target.value })}><option value="">— Elige el proceso —</option>{procesos.map((p) => <option key={p.id} value={p.id}>{p.padre ? `   ${p.nombre}` : p.nombre}</option>)}</select></div>
              <div><label className={lbl}>Fuente / origen</label><select className={inp} required value={nuevo.fuente} onChange={(e) => setNuevo({ ...nuevo, fuente: e.target.value })}><option value="">—</option>{(cat?.fuentes_mejora || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Detectado por</label><input className={inp} value={nuevo.detectado_por} onChange={(e) => setNuevo({ ...nuevo, detectado_por: e.target.value })} placeholder="Nombre (área)" /></div>
              <div><label className={lbl}>Fecha de identificación</label><input type="date" max={hoy()} className={inp} value={nuevo.fecha_identificacion} onChange={(e) => setNuevo({ ...nuevo, fecha_identificacion: e.target.value })} /></div>
            </div>
            <div><label className={lbl}>Descripción de la oportunidad de mejora</label><CampoAmpliable multilinea rows={3} value={nuevo.descripcion} onChange={(v) => setNuevo({ ...nuevo, descripcion: v })} /></div>
            <div><label className={lbl}>Situación que la motiva</label><CampoAmpliable multilinea rows={2} value={nuevo.situacion} onChange={(v) => setNuevo({ ...nuevo, situacion: v })} /></div>
            {err && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{err}</p>}
            <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setNuevo(null)}>Cancelar</button><button className="btn-primary" disabled={!nuevo.descripcion.trim()}>Registrar</button></div>
          </form>
        )}
      </Modal>

      <Modal abierto={Boolean(d)} titulo={d ? `${d.codigo} — ${d.descripcion.slice(0, 80)}` : ''} onCerrar={() => setD(null)} panel ancho="max-w-4xl">
        {d && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2"><Chip par={DECISION[d.decision]} />{d.decision === 'se_implementa' && <Chip par={EF_MEJORA[d.eficacia]} texto={`Eficacia: ${EF_MEJORA[d.eficacia][0]}`} />}{d.evaluacion_vencida && <span className="text-xs font-semibold text-red-600">En evaluación más de un año: resolver en la revisión por la dirección.</span>}</div>
            {err && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{err}</p>}
            <Seccion titulo="1. Identificación y análisis">
              <div className="grid gap-x-4 md:grid-cols-3"><Dato etiqueta="Proceso" valor={d.proceso_nombre} /><Dato etiqueta="Fuente" valor={d.fuente_display} /><Dato etiqueta="Detectado por" valor={d.detectado_por} /><Dato etiqueta="Fecha" valor={fecha(d.fecha_identificacion)} />{d.hallazgo_codigo && <Dato etiqueta="Hallazgo" valor={d.hallazgo_codigo} />}</div>
              <Dato etiqueta="Descripción" valor={d.descripcion} /><Dato etiqueta="Situación que la motiva" valor={d.situacion} />
              {ident && <button className="btn-secondary !py-1 text-xs" onClick={async () => { const t = await confirmar({ titulo: 'Corregir la descripción', mensaje: '', textoConfirmar: 'Guardar', entrada: { etiqueta: 'Descripción', obligatorio: true, multilinea: true, valorInicial: d.descripcion } }); if (t !== null) accion(() => api.mejoras.editar(d.id, { descripcion: t })) }}><Pencil className="h-3.5 w-3.5" /> Corregir descripción</button>}
            </Seccion>
            <Seccion titulo="2. Selección" tono={ident ? 'ambar' : ''}>
              {d.decision !== 'en_evaluacion' ? <><Dato etiqueta="Decisión" valor={`${d.decision_display} (${fecha(d.fecha_decision) || '—'})`} /><Dato etiqueta="Justificación" valor={d.justificacion} /></>
                : ident && (form?.tipo === 'decidir' ? (
                  <div className="space-y-2">
                    <div className="flex gap-3">{[['se_implementa', 'Se implementa'], ['no_se_implementa', 'No se implementa']].map(([k, n]) => <label key={k} className="flex items-center gap-1.5"><input type="radio" checked={form.decision === k} onChange={() => setForm({ ...form, decision: k })} /> {n}</label>)}</div>
                    <CampoAmpliable multilinea placeholder="Justificación de la decisión" value={form.justificacion} onChange={(v) => setForm({ ...form, justificacion: v })} />
                    {form.decision === 'se_implementa' && <div className="grid gap-2 md:grid-cols-4">
                      <div className="md:col-span-4"><CampoAmpliable multilinea placeholder="Acción o actividad" value={form.accion} onChange={(v) => setForm({ ...form, accion: v })} /></div>
                      <div><label className={lbl}>Responsable</label><select className={inp} value={String(form.responsable || '')} onChange={(e) => setForm({ ...form, responsable: e.target.value ? Number(e.target.value) : '' })}>{usuariosOpc.map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></div>
                      <div><label className={lbl}>o cargo / nombre</label><input className={inp} value={form.responsable_texto} onChange={(e) => setForm({ ...form, responsable_texto: e.target.value })} /></div>
                      <div><label className={lbl}>Fecha máxima</label><input type="date" min={hoy()} className={inp} value={form.fecha_maxima} onChange={(e) => setForm({ ...form, fecha_maxima: e.target.value })} /></div>
                    </div>}
                    <div className="flex justify-end gap-2"><button className="btn-secondary !py-1 text-xs" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary !py-1 text-xs" disabled={!form.decision} onClick={() => accion(() => api.mejoras.accion(d.id, 'decidir', { ...form, responsable: form.responsable || null }))}>Registrar decisión</button></div>
                  </div>
                ) : <button className="btn-primary !py-1 text-xs" onClick={() => setForm({ tipo: 'decidir', decision: '', justificacion: '', accion: '', responsable: '', responsable_texto: '', fecha_maxima: '' })}>Registrar decisión</button>)}
            </Seccion>
            {d.decision === 'se_implementa' && (
              <Seccion titulo="3. Implementación y seguimiento" tono={d.eficacia === 'pendiente' ? 'azul' : ''}>
                <div className="grid gap-x-4 md:grid-cols-3"><Dato etiqueta="Responsable" valor={d.responsable_nombre} /><Dato etiqueta="Fecha máxima" valor={fecha(d.fecha_maxima)} /><p><strong>Estado:</strong> <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${ESTADO_ACCION[d.estado_accion]}`}>{d.estado_accion_display}</span>{d.fecha_ejecucion ? ` · ${fecha(d.fecha_ejecucion)}` : ''}</p></div>
                <Dato etiqueta="Acción" valor={d.accion} />
                {d.evidencia && <p><strong>Evidencia:</strong> {d.evidencia}{d.evidencia_url && <a href={d.evidencia_url} target="_blank" rel="noreferrer" className="ml-1 underline">archivo</a>}</p>}
                {d.fecha_verificacion && <Dato etiqueta="Fecha de verificación" valor={fecha(d.fecha_verificacion)} />}
                {puedeEditar && d.eficacia === 'pendiente' && d.estado_accion !== 'ejecutado' && (form?.tipo === 'seg' ? (
                  <div className="space-y-2 rounded border border-slate-200 p-2 dark:border-slate-700">
                    <div className="grid gap-2 md:grid-cols-3"><div><label className={lbl}>Estado</label><select className={inp} value={form.estado} onChange={(e) => setForm({ ...form, estado: e.target.value })}><option value="en_proceso">En proceso</option><option value="ejecutado">Ejecutado</option></select></div>
                      {form.estado === 'ejecutado' && <div><label className={lbl}>Fecha de ejecución</label><input type="date" max={hoy()} className={inp} value={form.fecha_ejecucion} onChange={(e) => setForm({ ...form, fecha_ejecucion: e.target.value })} /></div>}</div>
                    <CampoAmpliable multilinea placeholder="Evidencia / observaciones" value={form.evidencia} onChange={(v) => setForm({ ...form, evidencia: v })} />
                    <div className="flex flex-wrap items-center gap-2"><label className="btn-secondary !py-1 cursor-pointer text-xs">Adjuntar archivo<input type="file" className="hidden" onChange={(e) => setForm({ ...form, archivo: e.target.files[0] || null })} /></label>{form.archivo && <span className="text-[11px]">{form.archivo.name}</span>}
                      <button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary !py-1 text-xs" onClick={() => accion(() => { const fd = new FormData(); ['estado', 'fecha_ejecucion', 'evidencia', 'archivo'].forEach((k) => form[k] && fd.append(k, form[k])); return api.mejoras.subir(d.id, 'seguimiento', fd) })}>Registrar</button></div>
                  </div>
                ) : <button className="btn-primary !py-1 text-xs" onClick={() => setForm({ tipo: 'seg', estado: 'ejecutado', fecha_ejecucion: hoy(), evidencia: '', archivo: null })}>Registrar seguimiento</button>)}
                {puedeEditar && d.eficacia === 'pendiente' && d.estado_accion === 'ejecutado' && (form?.tipo === 'ef' ? (
                  <div className="space-y-2 rounded border border-violet-500/30 p-2">
                    <div className="flex gap-3">{[['lograda', 'Lograda'], ['parcial', 'Parcial'], ['no_lograda', 'No lograda']].map(([k, n]) => <label key={k} className="flex items-center gap-1.5"><input type="radio" checked={form.eficacia === k} onChange={() => setForm({ ...form, eficacia: k })} /> {n}</label>)}</div>
                    <div className="grid gap-2 md:grid-cols-3"><div><label className={lbl}>Fecha de verificación</label><input type="date" max={hoy()} className={inp} value={form.fecha_verificacion} onChange={(e) => setForm({ ...form, fecha_verificacion: e.target.value })} /></div></div>
                    <CampoAmpliable multilinea placeholder="Beneficio obtenido contra el esperado (y qué faltó, si es parcial o no lograda)" value={form.evidencia} onChange={(v) => setForm({ ...form, evidencia: v })} />
                    <div className="flex justify-end gap-2"><button className="btn-secondary !py-1 text-xs" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary !py-1 text-xs" disabled={!form.eficacia} onClick={() => accion(() => api.mejoras.accion(d.id, 'evaluar_eficacia', form))}>Registrar eficacia</button></div>
                  </div>
                ) : <button className="btn-primary !py-1 text-xs" onClick={() => setForm({ tipo: 'ef', eficacia: '', fecha_verificacion: hoy(), evidencia: d.evidencia || '' })}>Evaluar eficacia</button>)}
              </Seccion>
            )}
            {d.historial.length > 0 && <Seccion titulo="Historial">{d.historial.slice().reverse().map((h, i) => <p key={i}>{fecha(h.fecha)} · {h.usuario} · <strong>{h.accion}</strong>{h.motivo ? `: ${h.motivo}` : ''}</p>)}</Seccion>}
            {ident && <div className="flex justify-end"><button className="btn-secondary !py-1 text-xs text-red-500" onClick={async () => { if (await confirmar({ titulo: 'Anular', mensaje: `¿Anular ${d.codigo}? Solo si se registró por error.`, textoConfirmar: 'Anular', peligro: true })) { try { await api.mejoras.anular(d.id); setD(null); await cargar() } catch (e) { setErr(e.message) } } }}><Trash2 className="h-3.5 w-3.5" /> Anular</button></div>}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ---------------------------------------------------------------- Contexto */
function Contexto({ cat, contexto, puedeEditar, puedeCrear, confirmar, setError, cargarComunes }) {
  const [form, setForm] = useState(null)
  const guardar = async () => {
    setError('')
    try { form.id ? await api.contextoRiesgos.editar(form.id, { descripcion: form.descripcion, requisitos: form.requisitos }) : await api.contextoRiesgos.crear(form); setForm(null); await cargarComunes() } catch (e) { setError(e.message) }
  }
  const retirar = async (e) => {
    if (!await confirmar({ titulo: 'Dejar de considerar', mensaje: `${e.codigo} deja de estar vigente (no se borra; los riesgos que lo citan lo conservan).`, textoConfirmar: 'Continuar', peligro: true })) return
    try { await api.contextoRiesgos.retirar(e.id); await cargarComunes() } catch (err) { setError(err.message) }
  }
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between"><p className="text-xs text-slate-500">Análisis del contexto (FODA) y partes interesadas: se revisa como mínimo una vez al año y ante cambios significativos.</p>
        {puedeCrear && <button className="btn-primary" onClick={() => setForm({ tipo: 'fortaleza', descripcion: '', requisitos: '' })}><Plus className="h-4 w-4" /> Nuevo elemento</button>}</div>
      {form && (
        <div className="card-esynapse space-y-2 p-3 text-sm">
          <div className="grid gap-2 md:grid-cols-4">
            <div><label className={lbl}>Tipo</label><select className={inp} disabled={Boolean(form.id)} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{(cat?.tipos_contexto || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
            <div className="md:col-span-3"><label className={lbl}>Descripción</label><input className={inp} value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></div>
          </div>
          {form.tipo === 'parte_interesada' && <div><label className={lbl}>Necesidades y expectativas</label><CampoAmpliable multilinea value={form.requisitos} onChange={(v) => setForm({ ...form, requisitos: v })} /></div>}
          <div className="flex justify-end gap-2"><button className="btn-secondary !py-1 text-xs" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary !py-1 text-xs" disabled={!form.descripcion.trim()} onClick={guardar}>Guardar</button></div>
        </div>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        {(cat?.tipos_contexto || []).map(([k, n]) => (
          <div key={k} className="card-esynapse p-3">
            <p className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">{n === 'Oportunidad' ? 'Oportunidades (externas)' : n === 'Parte interesada' ? 'Partes interesadas' : `${n}s`}</p>
            {contexto.filter((e) => e.tipo === k).map((e) => (
              <div key={e.id} className="flex items-start gap-2 border-t border-slate-100 py-1.5 text-xs dark:border-slate-800">
                <span className="w-9 shrink-0 font-mono font-semibold">{e.codigo}</span><span className="flex-1">{e.descripcion}{e.requisitos && <span className="block text-slate-500">{e.requisitos}</span>}</span>
                <span className="text-[11px] text-slate-500 dark:text-slate-400">{e.n_riesgos} R/O</span>
                {puedeEditar && <><button className="p-0.5" title="Corregir" onClick={() => setForm({ id: e.id, tipo: e.tipo, descripcion: e.descripcion, requisitos: e.requisitos })}><Pencil className="h-3.5 w-3.5" /></button><button className="p-0.5 text-red-500" title="Dejar de considerar" onClick={() => retirar(e)}><X className="h-3.5 w-3.5" /></button></>}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------- Indicadores */
function Indicadores() {
  const [ind, setInd] = useState(null)
  const [sel, setSel] = useState(null)
  useEffect(() => { api.riesgos.indicadores().then(setInd).catch(() => {}) }, [])
  if (!ind) return <p className="text-sm text-slate-400">Cargando…</p>
  const a = ind.alertas
  const Mapa = ({ titulo, m, cods, ejes, clave }) => (
    <div className="card-esynapse p-3">
      <p className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">{titulo}</p>
      <div className="flex gap-2">
        <div className="flex w-5 items-center justify-center text-[11px] text-slate-500 [writing-mode:vertical-rl] rotate-180">{ejes[1]}</div>
        <div className="flex-1">
          <table className="w-full table-fixed text-xs">
            <tbody>
              {m.map((fila, i) => (
                <tr key={i}><td className="w-6 text-[11px] text-slate-500">{5 - i}</td>
                  {fila.map((n, j) => {
                    const v = (5 - i) * (j + 1)
                    const lista = cods?.[i]?.[j] || []
                    const marcada = sel && sel.clave === clave && sel.i === i && sel.j === j
                    // Cada casilla muestra su valor (fila × columna), como la matriz de valoración del
                    // procedimiento; la marca de la esquina, cuántos registros caen en ella (clic: cuáles).
                    return (
                      <td key={j} onClick={() => setSel(n ? { clave, i, j, v, lista } : null)}
                        className={`relative h-11 border border-white dark:border-slate-900 ${NIVEL[nivelDe(v)][2]} ${n ? 'cursor-pointer' : ''} ${marcada ? 'ring-2 ring-inset ring-slate-900 dark:ring-white' : ''}`}
                        title={`${5 - i} × ${j + 1} = ${v} (${NIVEL[nivelDe(v)][0]})${n ? ` · ${lista.join(', ')}` : ''}`}>
                        <span className="text-base font-bold">{v}</span>
                        {n > 0 && <span className="absolute right-1 top-0.5 rounded-full bg-slate-900/80 px-1.5 text-[11px] font-bold text-white">{n}</span>}
                      </td>
                    )
                  })}
                </tr>
              ))}
              <tr><td />{[1, 2, 3, 4, 5].map((n) => <td key={n} className="text-[11px] text-slate-500">{n}</td>)}</tr>
            </tbody>
          </table>
          <p className="text-center text-[11px] text-slate-500">{ejes[0]}</p>
          {sel && sel.clave === clave && (
            <p className="mt-2 rounded bg-slate-100 px-2 py-1.5 text-[11px] dark:bg-slate-800/60"><strong>Valor {sel.v} ({NIVEL[nivelDe(sel.v)][0]}):</strong> {sel.lista.join(', ')}</p>
          )}
        </div>
      </div>
    </div>
  )
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        {[['Eficacia de las acciones', ind.eficacia_acciones.porcentaje != null ? `${ind.eficacia_acciones.porcentaje} %` : '—', `${ind.eficacia_acciones.eficaces} de ${ind.eficacia_acciones.implementadas} · meta ≥ 80 %`, ind.eficacia_acciones.porcentaje != null && ind.eficacia_acciones.porcentaje < 80],
          ['Acciones vencidas', a.acciones_vencidas, 'sin ejecutar pasada su fecha máxima', a.acciones_vencidas > 0],
          ['Requieren acción sin tratamiento', a.sin_tratamiento, `${a.sin_valoracion} sin valoración`, a.sin_tratamiento > 0],
          ['Por verificar / en cartera', `${a.por_verificar} / ${a.en_cartera_sin_decision}`, 'eficacia pendiente · oportunidades sin decisión', false]].map(([t, v, s, mal]) => (
          <div key={t} className="card-esynapse p-3"><p className="text-xs text-slate-500 dark:text-slate-400">{t}</p><p className={`text-2xl font-bold ${mal ? 'text-red-600' : ''}`}>{v}</p><p className="text-[11px] text-slate-500">{s}</p></div>
        ))}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Mapa clave="r" titulo="Mapa de calor — riesgos" m={ind.mapa_riesgos} cods={ind.mapa_riesgos_codigos} ejes={['Probabilidad', 'Impacto']} />
        <Mapa clave="o" titulo="Mapa de calor — oportunidades" m={ind.mapa_oportunidades} cods={ind.mapa_oportunidades_codigos} ejes={['Viabilidad', 'Beneficio']} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <div className="card-esynapse overflow-x-auto p-3"><p className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Matriz de riesgos y oportunidades</p>
          <table className="w-full text-xs"><thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="py-1">Indicador</th><th>Riesgos</th><th>Oportunidades</th><th>Total</th></tr></thead>
            <tbody>{ind.riesgos_oportunidades.map((f) => <tr key={f.indicador} className="border-t border-slate-100 dark:border-slate-800"><td className="py-1">{f.indicador}</td><td>{f.riesgos}</td><td>{f.oportunidades}</td><td className="font-semibold">{f.total}</td></tr>)}
              <tr><td colSpan={4} className="pt-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Distribución por valoración inicial</td></tr>
              {ind.distribucion.map((f) => <tr key={f.nivel} className="border-t border-slate-100 dark:border-slate-800"><td className="py-1"><ChipNivel nivel={f.nivel} /></td><td>{f.riesgos}</td><td>{f.oportunidades}</td><td className="font-semibold">{f.total}</td></tr>)}
            </tbody></table></div>
        <div className="card-esynapse overflow-x-auto p-3"><p className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Oportunidades de mejora</p>
          <table className="w-full text-xs"><thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="py-1">Indicador</th><th>Cantidad</th><th>% del total</th></tr></thead>
            <tbody>{ind.mejoras.map((f) => <tr key={f.indicador} className="border-t border-slate-100 dark:border-slate-800"><td className="py-1">{f.indicador}</td><td>{f.cantidad}</td><td>{f.porcentaje != null ? `${f.porcentaje} %` : '—'}</td></tr>)}
              <tr><td colSpan={3} className="pt-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Origen de la detección</td></tr>
              {ind.mejoras_por_origen.map((f) => <tr key={f.fuente} className="border-t border-slate-100 dark:border-slate-800"><td className="py-1">{f.nombre}</td><td>{f.cantidad}</td><td /></tr>)}
            </tbody></table>
          {(a.mejoras_en_evaluacion_vencidas > 0 || a.mejoras_accion_vencida > 0) && <p className="mt-2 text-xs text-red-600">{a.mejoras_en_evaluacion_vencidas} en evaluación más de un año · {a.mejoras_accion_vencida} con acción vencida</p>}
        </div>
      </div>
    </div>
  )
}
