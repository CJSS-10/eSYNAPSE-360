import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Camera, CheckCircle2, FileText, Info, Plus, Search, SearchX } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import EncabezadoModulo from '../components/ui/EncabezadoModulo.jsx'
import Pestanas from '../components/ui/Pestanas.jsx'
import Badge, { NormaBadge } from '../components/ui/Badge.jsx'
import { Vistas } from '../components/NavModulo.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora } from '../lib/fecha.js'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
// Estados (regla 10): sin evaluar y no aplica gris · parcial ámbar · cumple verde · no cumple rojo.
const TONO_ESTADO = { sin_evaluar: 'gris', cumple: 'verde', parcial: 'ambar', no_cumple: 'rojo', no_aplica: 'gris' }
const NOMBRE_ESTADO = { sin_evaluar: 'Sin evaluar', cumple: 'Cumple', parcial: 'Parcial', no_cumple: 'No cumple', no_aplica: 'No aplica' }
// Evidencia automática: conforme verde · alerta rojo · informativo gris.
const EVID = {
  conforme: { tono: 'verde', Icono: CheckCircle2, color: 'text-emerald-500', nombre: 'Conforme' },
  alerta: { tono: 'rojo', Icono: AlertTriangle, color: 'text-red-500', nombre: 'Alerta' },
  informativo: { tono: 'gris', Icono: Info, color: 'text-slate-400', nombre: 'Informativo' },
}
const PESTANAS = [['tablero', 'Tablero'], ['iso_9001', 'ISO 9001'], ['iso_14001', 'ISO 14001'],
  ['iso_45001', 'ISO 45001'], ['iso_17025', 'NTP ISO/IEC 17025'], ['otros', 'Otros requisitos']]
const NOMBRE_NORMA = { iso_9001: 'ISO 9001', iso_14001: 'ISO 14001', iso_45001: 'ISO 45001 / Ley 29783', iso_17025: 'NTP ISO/IEC 17025' }
const abrirPdf = async (promesa, setError) => {
  setError('')
  try { const url = URL.createObjectURL(await promesa); window.open(url, '_blank'); setTimeout(() => URL.revokeObjectURL(url), 60000) } catch (e) { setError(e.message) }
}
// Estado de una fila para el SIG completo (sede vacía) o para una sede: cada una con su propia evaluación.
const estadoVista = (f, sede) => {
  const ev = f.evaluacion
  if (!ev) return 'sin_evaluar'
  return sede ? (ev.sedes?.[sede]?.estado || 'sin_evaluar') : ev.estado
}
const pct = (v, vacio = '—') => (v == null ? vacio : `${v} %`)

function MsgError({ texto }) {
  const ref = useRef(null)
  useEffect(() => { if (texto) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }, [texto])
  return texto ? <p ref={ref} className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p> : null
}

function Evidencia({ e, compacta }) {
  const v = EVID[e.nivel] || EVID.informativo
  return (
    <div className="flex items-start gap-2 text-xs">
      <v.Icono className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${v.color}`} />
      <div className="min-w-0">
        {!compacta && <span className="font-medium text-slate-700 dark:text-slate-200">{e.titulo}: </span>}
        <span className="text-slate-600 dark:text-slate-300">{e.texto}</span>
        {e.ruta && <Link to={e.ruta} className="ml-1 text-esynapse-500 hover:underline">ver</Link>}
      </div>
    </div>
  )
}

export default function Cumplimiento() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const [tab, setTab] = useState('tablero')
  const [op, setOp] = useState(null)
  const [error, setError] = useState('')
  const [recarga, setRecarga] = useState(0)

  useEffect(() => { api.cumplimiento.opciones().then(setOp).catch((e) => setError(e.message)) }, [])

  const guardarCorte = async () => {
    const obs = await confirmar({ titulo: 'Guardar corte', textoConfirmar: 'Guardar corte', mensaje: 'Se guarda el grado de cumplimiento actual de cada norma para ver su evolución.', entrada: { etiqueta: 'Observaciones (opcional)', multilinea: true } })
    if (obs === null || obs === undefined) return
    try { await api.cumplimiento.corte({ observaciones: obs }); setRecarga((n) => n + 1); setTab('tablero') } catch (e) { setError(e.message) }
  }

  return (
    <div className="space-y-4">
      <EncabezadoModulo seccion="Sistema de gestión" titulo="Cumplimiento"
        descripcion="¿Cumplimos cada requisito de las normas, cómo y dónde está la evidencia? Evaluación por requisito con la evidencia viva de los módulos."
        acciones={<>
          <button onClick={() => abrirPdf(api.cumplimiento.pdf('todas', ''), setError)} className="btn-secondary"><FileText className="h-4 w-4" /> Matriz completa (PDF)</button>
          {tienePermiso('cumplimiento', 'aprobar') && <button onClick={guardarCorte} className="btn-secondary"><Camera className="h-4 w-4" /> Guardar corte</button>}
        </>}>
        <Pestanas opciones={PESTANAS} valor={tab} onChange={setTab} />
      </EncabezadoModulo>
      <MsgError texto={error} />
      {tab === 'tablero' && <Tablero key={recarga} onNorma={setTab} />}
      {tab !== 'tablero' && op && <Matriz key={`${tab}-${recarga}`} norma={tab} op={op} tienePermiso={tienePermiso} confirmar={confirmar} />}
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ tablero
function Tablero({ onNorma }) {
  const [d, setD] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api.cumplimiento.tablero().then(setD).catch((e) => setError(e.message)) }, [])
  if (error) return <MsgError texto={error} />
  if (!d) return <p className="text-sm text-slate-500">Calculando el cumplimiento…</p>
  const alertas = d.evidencias.filter((e) => e.nivel === 'alerta').length
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {d.normas.map((n) => (
          <button key={n.norma} onClick={() => onNorma(n.norma)} className="card-esynapse space-y-2 p-4 text-left transition hover:ring-1 hover:ring-esynapse-500/40">
            <NormaBadge nombre={n.nombre} />
            <p className={n.porcentaje == null ? 'py-1.5 text-lg text-slate-400' : 'text-3xl font-semibold text-slate-900 dark:text-white'}>{pct(n.porcentaje, 'Sin evaluar')}</p>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
              <div className="h-full bg-esynapse-500" style={{ width: `${n.cobertura || 0}%` }} />
            </div>
            <p className="text-xs text-slate-500">Cobertura {pct(n.cobertura)} · {n.evaluados + n.no_aplica} de {n.total} requisitos</p>
            <div className="flex flex-wrap gap-1 text-[11px]">
              <Badge tono="verde">{n.cumple} cumplen</Badge>
              <Badge tono="ambar">{n.parcial} parcial</Badge>
              <Badge tono="rojo">{n.no_cumple} no cumplen</Badge>
              {n.en_riesgo > 0 && <Badge tono="rojo">{n.en_riesgo} en riesgo</Badge>}
            </div>
          </button>
        ))}
      </div>
      <p className="text-[11px] text-slate-500">Grado de cumplimiento: cumple = 100, parcial = 50, no cumple = 0; no aplica se excluye. Cobertura: requisitos evaluados o justificados como no aplicables.</p>

      {d.sedes?.length > 0 && (
        <section className="card-esynapse overflow-hidden">
          <p className="border-b border-slate-200 px-4 py-3 text-sm font-semibold dark:border-slate-800">Cumplimiento por sede</p>
          <table className="tabla-sig">
            <thead><tr><th>Norma</th><th>SIG completo</th>{d.sedes.map((x) => <th key={x.id}>{x.nombre}</th>)}</tr></thead>
            <tbody>{d.normas.map((n) => (
              <tr key={n.norma}><td className="whitespace-nowrap"><NormaBadge nombre={n.nombre} /></td>
                <td className="text-right font-semibold">{pct(n.porcentaje)}</td>
                {d.sedes.map((x) => <td key={x.id} className="text-right">{pct(x.normas.find((m) => m.norma === n.norma)?.porcentaje)}</td>)}</tr>))}</tbody>
          </table>
          <p className="px-4 py-2 text-[11px] text-slate-500">El SIG completo y cada sede tienen su propia evaluación; el porcentaje de una sede solo considera los requisitos evaluados en ella.</p>
        </section>
      )}

      <section className="card-esynapse overflow-hidden">
        <p className="border-b border-slate-200 px-4 py-3 text-sm font-semibold dark:border-slate-800">Requieren atención ({d.atencion.length})</p>
        {d.atencion.length ? (
          <table className="tabla-sig">
            <thead><tr><th>Norma</th><th>Requisito</th><th>Estado</th><th>Motivo</th><th>Hallazgo</th></tr></thead>
            <tbody>{d.atencion.map((a, i) => (
              <tr key={i} className="fila" onClick={() => onNorma(a.norma_clave)}>
                <td className="whitespace-nowrap"><NormaBadge nombre={a.norma} /></td>
                <td><span className="font-medium">{a.codigo}</span> <span className="text-slate-500">{a.titulo.split('\n')[0].slice(0, 90)}</span></td>
                <td className="text-center whitespace-nowrap"><Badge tono={TONO_ESTADO[a.estado_clave] || 'gris'}>{a.estado}</Badge>{a.en_riesgo && <Badge tono="rojo" className="ml-1">En riesgo</Badge>}</td>
                <td className="text-xs text-slate-500">{[a.sedes, a.motivo].filter(Boolean).join(' · ') || '—'}</td>
                <td className="text-center whitespace-nowrap">{a.hallazgo_codigo || '—'}</td>
              </tr>))}</tbody>
          </table>
        ) : <p className="px-4 py-6 text-sm text-slate-500">Ningún requisito en riesgo, parcial o incumplido.</p>}
      </section>

      <section className="card-esynapse space-y-2 p-4">
        <p className="text-sm font-semibold">Evidencia del sistema {alertas > 0 && <Badge tono="rojo" className="ml-1">{alertas} en alerta</Badge>}</p>
        <div className="grid gap-2 md:grid-cols-2">{d.evidencias.map((e) => <Evidencia key={e.clave} e={e} />)}</div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card-esynapse overflow-hidden">
          <p className="border-b border-slate-200 px-4 py-3 text-sm font-semibold dark:border-slate-800">Por proceso</p>
          {d.procesos.length ? (
            <table className="tabla-sig">
              <thead><tr><th>Proceso</th><th>Cumplimiento</th><th>Evaluados</th><th>En riesgo</th></tr></thead>
              <tbody>{d.procesos.map((p) => (
                <tr key={p.proceso}><td>{p.proceso}</td><td className="text-right">{pct(p.porcentaje)}</td><td className="text-right">{p.evaluados}</td><td className="text-right">{p.en_riesgo}</td></tr>))}</tbody>
            </table>
          ) : <p className="px-4 py-6 text-sm text-slate-500">Asigne el proceso responsable al evaluar los requisitos.</p>}
        </section>
        <section className="card-esynapse overflow-hidden">
          <p className="border-b border-slate-200 px-4 py-3 text-sm font-semibold dark:border-slate-800">Evolución (cortes)</p>
          {d.cortes.length ? (
            <table className="tabla-sig">
              <thead><tr><th>Fecha</th>{Object.keys(NOMBRE_NORMA).map((k) => <th key={k}>{NOMBRE_NORMA[k].split(' /')[0]}</th>)}</tr></thead>
              <tbody>{d.cortes.map((c) => (
                <tr key={c.id} title={c.observaciones || ''}><td className="text-right whitespace-nowrap">{fecha(c.fecha)}</td>
                  {Object.keys(NOMBRE_NORMA).map((k) => <td key={k} className="text-right">{pct(c.resultados[k]?.porcentaje)}</td>)}</tr>))}</tbody>
            </table>
          ) : <p className="px-4 py-6 text-sm text-slate-500">Sin cortes. Use «Guardar corte» para registrar el estado actual.</p>}
        </section>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ matriz
function Matriz({ norma, op, tienePermiso, confirmar }) {
  const [d, setD] = useState(null)
  const [error, setError] = useState('')
  const [filtro, setFiltro] = useState('todos')
  const [buscar, setBuscar] = useState('')
  const [sel, setSel] = useState(null)
  const [nuevo, setNuevo] = useState(false)
  const [aviso, setAviso] = useState('')
  const [sede, setSede] = useState('')
  const cargar = useCallback(() => api.cumplimiento.matriz(norma).then(setD).catch((e) => setError(e.message)), [norma])
  useEffect(() => { cargar() }, [cargar])

  const filas = useMemo(() => {
    if (!d) return []
    const b = buscar.trim().toLowerCase()
    const pasa = (f) => {
      const est = estadoVista(f, sede)
      if (filtro === 'en_riesgo' ? !f.en_riesgo : filtro !== 'todos' && est !== filtro) return false
      return !b || `${f.codigo} ${f.titulo} ${f.referencia || ''}`.toLowerCase().includes(b)
    }
    const salida = []
    let seccion = null
    for (const f of d.filas) {
      if (f.tipo === 'seccion') { seccion = f; continue }
      if (!pasa(f)) continue
      if (seccion) { salida.push(seccion); seccion = null }
      salida.push(f)
    }
    return salida
  }, [d, filtro, buscar, sede])

  const r = sede ? d?.resumen_sedes?.[sede] : d?.resumen
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative"><Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <input className={`${inp} !w-64 pl-8`} placeholder="Buscar numeral o texto" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <Vistas valor={filtro} onChange={setFiltro} opciones={[['todos', 'Todos'], ['sin_evaluar', 'Sin evaluar'], ['cumple', 'Cumple'], ['parcial', 'Parcial'], ['no_cumple', 'No cumple'], ['no_aplica', 'No aplica'], ['en_riesgo', 'En riesgo']]} />
        {r && <span className="ml-auto text-xs text-slate-500">Cumplimiento <strong className="text-slate-800 dark:text-slate-100">{pct(r.porcentaje)}</strong> · cobertura {pct(r.cobertura)} · {r.en_riesgo} en riesgo</span>}
        {norma !== 'otros' && <button onClick={() => abrirPdf(api.cumplimiento.pdf(norma, sede), setError)} className="btn-secondary !py-1.5 text-xs"><FileText className="h-3.5 w-3.5" /> PDF</button>}
        {norma === 'otros' && tienePermiso('cumplimiento', 'crear') && <button onClick={() => setNuevo(true)} className="btn-primary"><Plus className="h-4 w-4" /> Registrar requisito</button>}
      </div>
      {op.sedes.length > 0 && norma !== 'otros' && (
        <div className="flex items-center gap-2 text-xs text-slate-500">Vista:
          <Vistas valor={sede} onChange={setSede} opciones={[['', 'SIG completo'], ...op.sedes.map((x) => [String(x.id), x.nombre])]} />
        </div>
      )}
      {norma === 'otros' && <p className="text-xs text-slate-500">Requisitos de otras fuentes que no se vinculan a una norma: organismo de acreditación, entidad certificadora, clientes u otros. Los que se vinculan a una norma aparecen al final de su matriz.</p>}
      <MsgError texto={error} />
      {aviso && <p className="rounded-lg bg-emerald-500/10 px-3 py-2 text-xs text-emerald-600">{aviso}</p>}
      {!d ? <p className="text-sm text-slate-500">Cargando…</p> : (
        <div className="card-esynapse overflow-x-auto">
          <table className="tabla-sig">
            <thead><tr><th className="w-20">Numeral</th><th>Requisito</th><th>Proceso</th><th>Estado</th><th>Evidencia del sistema</th><th>Evaluado</th></tr></thead>
            <tbody>
              {filas.length === 0 && <tr><td colSpan={6} className="py-6 text-center text-slate-500">{norma === 'otros' ? 'Sin requisitos registrados.' : 'Ningún requisito con este filtro.'}</td></tr>}
              {filas.map((f, i) => f.tipo === 'seccion' ? (
                <tr key={`s${i}`} className="bg-slate-50 dark:bg-slate-800/40"><td colSpan={6} className="!py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{f.codigo} {f.titulo}</td></tr>
              ) : (
                <tr key={f.clave} className="fila" onClick={() => setSel(f)}>
                  <td className="whitespace-nowrap font-medium">{f.codigo}</td>
                  <td className="max-w-xl"><p className="line-clamp-2 text-slate-700 dark:text-slate-200">{f.titulo}</p>{f.referencia && <p className="text-[11px] text-slate-400">{f.referencia}</p>}</td>
                  <td className="text-xs">{f.evaluacion?.proceso_nombre || '—'}</td>
                  <td className="text-center whitespace-nowrap">
                    <Badge tono={TONO_ESTADO[estadoVista(f, sede)]}>{NOMBRE_ESTADO[estadoVista(f, sede)]}</Badge>
                    {!sede && Object.values(f.evaluacion?.sedes || {}).filter((x) => x.estado !== 'sin_evaluar').map((x) => (
                      <p key={x.sede_codigo + x.sede_nombre} className="mt-0.5 text-[10px] text-slate-500">{x.sede_codigo || x.sede_nombre}: {x.estado_display}</p>))}
                    {f.en_riesgo && <Badge tono="rojo" className="ml-1">En riesgo</Badge>}
                    {f.evaluacion?.hallazgo_codigo && <p className="mt-0.5 text-[10px] text-slate-400">{f.evaluacion.hallazgo_codigo}</p>}
                  </td>
                  <td className="text-center">
                    {f.evidencias.length ? <span className="inline-flex gap-1">{f.evidencias.map((e) => { const v = EVID[e.nivel] || EVID.informativo; return <span key={e.clave} title={`${e.titulo}: ${e.texto}`}><v.Icono className={`h-4 w-4 ${v.color}`} /></span> })}</span> : <span className="text-slate-300">—</span>}
                  </td>
                  <td className="text-right whitespace-nowrap text-xs">{fecha(f.evaluacion?.fecha_evaluacion) || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal abierto={Boolean(sel)} titulo={sel ? `${NOMBRE_NORMA[norma] || 'Otro requisito'} · ${sel.codigo}` : ''} onCerrar={() => setSel(null)} panel>
        {sel && <Evaluar fila={sel} op={op} tienePermiso={tienePermiso} confirmar={confirmar} onGuardado={async (msg) => { await cargar(); setSel(null); setAviso(msg || '') }} />}
      </Modal>
      <Modal abierto={nuevo} titulo="Registrar otro requisito" onCerrar={() => setNuevo(false)} ancho="max-w-2xl">
        <NuevoRequisito op={op} onListo={async () => { setNuevo(false); await cargar() }} />
      </Modal>
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ evaluar
function Evaluar({ fila, op, tienePermiso, confirmar, onGuardado }) {
  const ev = fila.evaluacion || {}
  const [f, setF] = useState({
    estado: ev.estado && ev.estado !== 'sin_evaluar' ? ev.estado : '', justificacion: ev.justificacion || '',
    proceso: ev.proceso || '', como_se_cumple: ev.como_se_cumple || '', evidencia: ev.evidencia || '',
    documentos: (ev.documentos || []).map((x) => x.id), reflejar: true,
    sedes: Object.fromEntries(op.sedes.map((x) => [x.id, { estado: ev.sedes?.[x.id]?.estado && ev.sedes[x.id].estado !== 'sin_evaluar' ? ev.sedes[x.id].estado : '', observacion: ev.sedes?.[x.id]?.observacion || '' }])),
  })
  const [buscaDoc, setBuscaDoc] = useState('')
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const puedeEditar = tienePermiso('cumplimiento', 'editar')
  const set = (k) => (v) => setF((x) => ({ ...x, [k]: v }))
  const docsSel = op.documentos.filter((x) => f.documentos.includes(x.id))
  const docsBusca = buscaDoc.trim().length >= 2 ? op.documentos.filter((x) => !f.documentos.includes(x.id) && `${x.codigo} ${x.titulo}`.toLowerCase().includes(buscaDoc.toLowerCase())).slice(0, 8) : []
  const id = fila.requisito ? { requisito: fila.requisito } : { adicional: fila.adicional }

  const guardar = async () => {
    setError(''); setAviso('')
    try {
      const sedes = Object.entries(f.sedes).map(([sede, x]) => ({ sede: Number(sede), estado: x.estado || 'sin_evaluar', observacion: x.observacion }))
      const r = await api.cumplimiento.evaluar({ ...id, ...f, sedes, proceso: f.proceso || null })
      await onGuardado(`Evaluación de ${fila.codigo} guardada${r.reflejada_en?.length ? `; registrada también en ${r.reflejada_en.join(' y ')}` : ''}.`)
    } catch (e) { setError(e.message) }
  }
  const [brecha, setBrecha] = useState(null)
  const registrarHallazgo = async () => {
    setError('')
    try {
      const r = await api.cumplimiento.hallazgo({ ...id, ...brecha, sede: brecha.sede || null })
      await onGuardado(`Se registró el hallazgo ${r.codigo}; su tratamiento sigue en Hallazgos.`)
    } catch (e) { setError(e.message) }
  }
  const darDeBaja = async () => {
    const motivo = await confirmar({ titulo: 'Dar de baja el requisito', textoConfirmar: 'Dar de baja', peligro: true, mensaje: 'El requisito deja de evaluarse; queda en el sistema con su historial.', entrada: { etiqueta: 'Motivo', obligatorio: true, multilinea: true } })
    if (motivo === null || motivo === undefined) return
    try { await api.cumplimiento.bajaOtro(fila.adicional, { motivo }); await onGuardado('Requisito dado de baja.') } catch (e) { setError(e.message) }
  }
  const hallazgoAbierto = ev.hallazgo && ev.hallazgo_estado !== 'Cerrado'

  return (
    <div className="space-y-4 text-sm">
      <div className="space-y-1">
        {fila.referencia && <p className="text-xs text-slate-500">{fila.referencia}</p>}
        <p className="whitespace-pre-wrap text-slate-700 dark:text-slate-200">{fila.titulo}</p>
        {fila.equivalentes?.length > 0 && <p className="text-xs text-slate-500">Cláusula común con: {fila.equivalentes.join(', ')}.</p>}
      </div>

      {fila.evidencias.length > 0 && (
        <div className="space-y-1.5 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
          <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">Evidencia del sistema</p>
          {fila.evidencias.map((e) => <Evidencia key={e.clave} e={e} />)}
          {fila.en_riesgo && <p className="text-xs text-red-500">En riesgo: la evidencia está en alerta o la evaluación tiene más de 12 meses.</p>}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        <div><label className={lbl}>Estado (SIG completo)</label>
          <select disabled={!puedeEditar} className={inp} value={f.estado} onChange={(e) => set('estado')(e.target.value)}>
            <option value="">— Seleccionar —</option>{op.estados.filter(([k]) => k !== 'sin_evaluar').map(([k, n]) => <option key={k} value={k}>{n}</option>)}
          </select></div>
        <div><label className={lbl}>Proceso responsable</label>
          <select disabled={!puedeEditar} className={inp} value={f.proceso} onChange={(e) => set('proceso')(e.target.value)}>
            <option value="">—</option>{op.procesos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select></div>
        {f.estado === 'no_aplica' && <div className="md:col-span-2"><label className={lbl}>Justificación de no aplica</label><CampoAmpliable multilinea disabled={!puedeEditar} value={f.justificacion} onChange={set('justificacion')} titulo="Justificación" /></div>}
        <div className="md:col-span-2"><label className={lbl}>Cómo se cumple</label><CampoAmpliable multilinea rows={3} disabled={!puedeEditar} value={f.como_se_cumple} onChange={set('como_se_cumple')} titulo="Cómo se cumple" placeholder="Procedimiento, práctica o control que asegura el requisito" /></div>
        <div className="md:col-span-2"><label className={lbl}>Evidencia</label><CampoAmpliable multilinea disabled={!puedeEditar} value={f.evidencia} onChange={set('evidencia')} titulo="Evidencia" placeholder="Registros, ubicación, fechas" /></div>
        <div className="md:col-span-2 space-y-1.5"><label className={lbl}>Documentos de la lista maestra que lo sustentan</label>
          <div className="flex flex-wrap gap-1">{docsSel.map((x) => (
            <span key={x.id} className="badge badge-gris">{x.codigo}{puedeEditar && <button type="button" className="ml-1 text-slate-400 hover:text-red-500" onClick={() => set('documentos')(f.documentos.filter((y) => y !== x.id))}>×</button>}</span>))}
            {!docsSel.length && <span className="text-xs text-slate-400">Ninguno</span>}</div>
          {puedeEditar && <><input className={inp} placeholder="Buscar documento por código o título" value={buscaDoc} onChange={(e) => setBuscaDoc(e.target.value)} />
            {docsBusca.length > 0 && <div className="rounded-lg border border-slate-200 dark:border-slate-700">{docsBusca.map((x) => (
              <button key={x.id} type="button" className="block w-full px-3 py-1.5 text-left text-xs hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => { set('documentos')([...f.documentos, x.id]); setBuscaDoc('') }}><strong>{x.codigo}</strong> {x.titulo}</button>))}</div>}</>}
        </div>
        {op.sedes.length > 0 && (
          <div className="space-y-2 rounded-lg border border-slate-200 p-3 md:col-span-2 dark:border-slate-800">
            <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">Evaluación por sede <span className="font-normal text-slate-400">(cada sede con su propia calificación, independiente del SIG completo)</span></p>
            {op.sedes.map((x) => {
              const v = f.sedes[x.id] || { estado: '', observacion: '' }
              const setSede = (campo) => (e) => setF((y) => ({ ...y, sedes: { ...y.sedes, [x.id]: { ...v, [campo]: e.target.value } } }))
              return (
                <div key={x.id} className="grid items-center gap-2 md:grid-cols-[10rem_11rem_1fr]">
                  <span className="text-xs font-medium">{x.nombre}</span>
                  <select disabled={!puedeEditar} className={`${inp} !py-1 text-xs`} value={v.estado} onChange={setSede('estado')}>
                    <option value="">Sin evaluar</option>{op.estados.filter(([k]) => k !== 'sin_evaluar').map(([k, n]) => <option key={k} value={k}>{n}</option>)}
                  </select>
                  <input disabled={!puedeEditar || !v.estado} className={`${inp} !py-1 text-xs`} placeholder={v.estado ? 'Cómo se cumple o evidencia en la sede (obligatorio)' : 'Elija primero el estado de la sede'} value={v.observacion} onChange={setSede('observacion')} />
                </div>
              )
            })}
          </div>
        )}
        {fila.equivalentes?.length > 0 && puedeEditar && (
          <label className="flex items-center gap-2 text-xs md:col-span-2"><input type="checkbox" checked={f.reflejar} onChange={(e) => set('reflejar')(e.target.checked)} /> Registrar la misma evaluación en {fila.equivalentes.join(' y ')}</label>
        )}
      </div>

      <MsgError texto={error} />
      {aviso && <p className="rounded-lg bg-emerald-500/10 px-3 py-2 text-xs text-emerald-600">{aviso}</p>}
      <div className="flex flex-wrap items-center gap-2">
        {puedeEditar && <button onClick={guardar} className="btn-primary">Guardar evaluación</button>}
        {(['parcial', 'no_cumple'].includes(ev.estado) || Object.values(ev.sedes || {}).some((x) => ['parcial', 'no_cumple'].includes(x.estado))) && !hallazgoAbierto && !brecha && tienePermiso('cumplimiento', 'crear') &&
          <button onClick={() => setBrecha({ tipo: 'nc_menor', descripcion: '' })} className="btn-secondary"><SearchX className="h-4 w-4" /> Registrar brecha como hallazgo</button>}
        {fila.adicional && tienePermiso('cumplimiento', 'eliminar') && <button onClick={darDeBaja} className="btn-secondary text-red-500">Dar de baja</button>}
        {ev.hallazgo_codigo && <span className="text-xs text-slate-500">Hallazgo {ev.hallazgo_codigo} · {ev.hallazgo_estado} · <Link to="/hallazgos" className="text-esynapse-500 hover:underline">ver en Hallazgos</Link></span>}
        {ev.fecha_evaluacion && <span className="ml-auto text-xs text-slate-500">Última evaluación: {fecha(ev.fecha_evaluacion)} · {ev.evaluado_por}{ev.vencida ? ' (más de 12 meses)' : ''}</span>}
      </div>

      {brecha && (
        <div className="space-y-2 rounded-lg border border-dashed border-red-500/40 p-3">
          <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">Registrar la brecha como hallazgo</p>
          <div className="grid gap-2 md:grid-cols-4">
            <div><label className={lbl}>Tipo</label><select className={inp} value={brecha.tipo} onChange={(e) => setBrecha({ ...brecha, tipo: e.target.value })}>{op.tipos_hallazgo.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
            {op.sedes.length > 0 && <div><label className={lbl}>Sede (opcional)</label><select className={inp} value={brecha.sede || ''} onChange={(e) => setBrecha({ ...brecha, sede: e.target.value })}><option value="">SIG completo</option>{op.sedes.map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}</select></div>}
            <div className="md:col-span-2"><label className={lbl}>Descripción de la brecha</label><CampoAmpliable multilinea value={brecha.descripcion} onChange={(v) => setBrecha({ ...brecha, descripcion: v })} titulo="Descripción de la brecha" placeholder="Qué falta para cumplir el requisito" /></div>
          </div>
          <div className="flex gap-2"><button onClick={registrarHallazgo} className="btn-primary !py-1.5 text-xs">Registrar hallazgo</button><button onClick={() => setBrecha(null)} className="btn-secondary !py-1.5 text-xs">Cancelar</button></div>
        </div>
      )}

      {ev.historial?.length > 0 && (
        <details className="text-xs text-slate-500"><summary className="cursor-pointer">Historial</summary>
          <ul className="mt-1 space-y-0.5">{[...ev.historial].reverse().map((h, i) => (
            <li key={i}>{fechaHora(h.fecha)} · {h.usuario} · {h.accion}{h.de ? `: ${h.de} → ${h.a}` : ''}{h.reflejada_desde ? ` (reflejada desde ${h.reflejada_desde})` : ''}{h.hallazgo ? ` ${h.hallazgo}` : ''}</li>))}</ul>
        </details>
      )}
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ otros requisitos
function NuevoRequisito({ op, onListo }) {
  const [f, setF] = useState({ fuente: 'acreditacion', referencia: '', codigo: '', texto: '', norma: '' })
  const [error, setError] = useState('')
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const enviar = async (e) => {
    e.preventDefault(); setError('')
    try { await api.cumplimiento.crearOtro(f); await onListo() } catch (err) { setError(err.message) }
  }
  return (
    <form onSubmit={enviar} className="space-y-3 text-sm">
      <div className="grid gap-3 md:grid-cols-2">
        <div><label className={lbl}>Fuente</label><select className={inp} value={f.fuente} onChange={set('fuente')}>{op.fuentes.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
        <div><label className={lbl}>Norma relacionada</label><select className={inp} value={f.norma} onChange={set('norma')}><option value="">Ninguna (pestaña «Otros requisitos»)</option>{op.normas.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
        <div><label className={lbl}>Documento de referencia</label><input required className={inp} value={f.referencia} onChange={set('referencia')} placeholder="Directriz, política o contrato" /></div>
        <div><label className={lbl}>Código o numeral</label><input className={inp} value={f.codigo} onChange={set('codigo')} /></div>
        <div className="md:col-span-2"><label className={lbl}>Requisito</label><textarea required rows={4} className={inp} value={f.texto} onChange={set('texto')} /></div>
      </div>
      <MsgError texto={error} />
      <div className="flex justify-end"><button type="submit" className="btn-primary">Registrar</button></div>
    </form>
  )
}
