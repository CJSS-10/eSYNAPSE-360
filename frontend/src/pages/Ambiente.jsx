import { useCallback, useEffect, useMemo, useState } from 'react'
import { Droplets, FileText, Leaf, Pencil, Plus, Recycle, Search, ShieldCheck, X, Zap } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import Pestanas from '../components/ui/Pestanas.jsx'
import { Vistas } from '../components/NavModulo.jsx'
import { OpcionesProcesos, useCatalogoProcesos } from '../components/SelectorProceso.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora, hoy as hoyLocal } from '../lib/fecha.js'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
const ANIO = new Date().getFullYear()
const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']
const GRIS = 'bg-slate-500/15 text-slate-500'
const AMBAR = 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
const VERDE = 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
const ROJO = 'bg-red-500/15 text-red-600 dark:text-red-400'
const AZUL = 'bg-blue-500/15 text-blue-600 dark:text-blue-400'
const EST_APROB = { aprobada: ['Aprobada por el Comité', VERDE], pendiente: ['Pendiente de aprobación', AMBAR], sin_aprobar: ['Sin aprobar', ROJO] }
const EST_PESAJE = { en_registro: ['En registro', GRIS], cerrado: ['Cerrado', VERDE], anulado: ['Anulado', ROJO] }
const METODO = { usuario: 'Usuario', pin: 'PIN', papel: 'Papel' }
const CRIT = [['legal', 'A'], ['severidad', 'B'], ['partes', 'C'], ['escala', 'D'], ['frecuencia', 'E']]
const Chip = ({ par }) => (par ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{par[0]}</span> : null)
const Aviso = ({ texto }) => <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600 dark:text-red-400">{texto}</p>
const num = (v, d = 2) => (v === null || v === undefined || v === '' ? '—' : Number(v).toLocaleString('es-PE', { maximumFractionDigits: d }))
/** Selector de sede (catálogo de Organización y personal). */
function SelectorSede({ sedes, valor, onChange, todas = 'Todas las sedes', className = '', disabled }) {
  return <select className={`${inp} ${className}`} disabled={disabled} value={String(valor || '')} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : '')}><option value="">{todas}</option>{sedes.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}</select>
}

function Credencial({ forma, valor, onChange }) {
  const v = valor || {}
  const pin = (k, ph) => <input type="password" inputMode="numeric" autoComplete="off" placeholder={ph} className={`${inp} !py-1 text-xs`} value={v[k] || ''} onChange={(e) => onChange({ ...v, [k]: e.target.value.replace(/\D/g, '').slice(0, 6) })} />
  if (forma === 'usuario') return <input type="password" autoComplete="off" placeholder="Contraseña de su usuario" className={`${inp} !py-1 text-xs`} value={v.clave || ''} onChange={(e) => onChange({ ...v, clave: e.target.value })} />
  if (forma === 'activo') return pin('pin', 'PIN')
  if (forma === 'bloqueado') return <span className="text-[11px] text-red-600">PIN bloqueado: restablézcalo o use el acta en papel</span>
  return <div className="flex gap-1">{pin('pin_nuevo', 'Nuevo PIN')}{pin('pin_confirmacion', 'Confirme')}</div>
}

export default function Ambiente() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const [pestana, setPestana] = useState('matriz')
  const [error, setError] = useState('')
  const [sedes, setSedes] = useState([])
  useEffect(() => { api.org.sedes().then(setSedes).catch(() => {}) }, [])
  const abrirPdf = async (promesa) => {
    setError('')
    try { const url = URL.createObjectURL(await promesa); window.open(url, '_blank'); setTimeout(() => URL.revokeObjectURL(url), 60000) } catch (e) { setError(e.message) }
  }
  const comun = { sedes, confirmar, setError, abrirPdf, puedeCrear: tienePermiso('medio_ambiente', 'crear'), puedeEditar: tienePermiso('medio_ambiente', 'editar'), puedeAprobar: tienePermiso('medio_ambiente', 'aprobar'), puedeEliminar: tienePermiso('medio_ambiente', 'eliminar') }
  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <TituloModulo seccion="Seguridad, salud y ambiente" titulo="Medio ambiente" descripcion="Aspectos e impactos ambientales y su significancia, consumo de energía y agua, y gestión de residuos sólidos." />
        <Pestanas opciones={[['matriz', 'Aspectos e impactos', Leaf], ['residuos', 'Residuos sólidos', Recycle], ['consumos', 'Energía y agua', Zap]]} valor={pestana} onChange={(k) => { setError(''); setPestana(k) }} />
      </div>
      {error && <Aviso texto={error} />}
      {pestana === 'matriz' && <Matriz {...comun} />}
      {pestana === 'residuos' && <Residuos {...comun} />}
      {pestana === 'consumos' && <Consumos {...comun} />}
    </div>
  )
}

/* ================================================================================ matriz de aspectos */
const ASP_VACIO = { sede: '', alcance: 'areas', areas: [], lugar: '', proceso: '', actividad: '', aspecto: '', impacto: '', situaciones: ['N'], generacion: 'directa', clase: 'negativo', etapa_ciclo: '', controles_existentes: '', legal: 1, severidad: 1, partes: 1, escala: 1, frecuencia: 1, obligacion: '', control_operacional: '', registro_asociado: '', responsable: '', plazo: '', criterio_seguimiento: '' }

function Matriz({ sedes, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeAprobar, puedeEliminar }) {
  const procesos = useCatalogoProcesos()
  const [items, setItems] = useState(null)
  const [res, setRes] = useState(null)
  const [cat, setCat] = useState(null)
  const [areas, setAreas] = useState([])
  const [puestos, setPuestos] = useState([])
  const [obligaciones, setObligaciones] = useState([])
  const [lugar, setLugar] = useState('')
  const [sedeF, setSedeF] = useState('')
  const [vista, setVista] = useState('todos')
  const [buscar, setBuscar] = useState('')
  const [form, setForm] = useState(null)
  const [aprob, setAprob] = useState(false)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => {
    const q = new URLSearchParams(); if (lugar) q.set('area', lugar); if (sedeF) q.set('sede', sedeF); if (buscar) q.set('buscar', buscar); if (vista === 'significativos') q.set('significativo', '1')
    api.ambiente.aspectos(`?${q}`).then(setItems).catch((e) => setError(e.message))
    api.ambiente.resumen().then(setRes).catch(() => {})
  }, [lugar, sedeF, buscar, vista, setError])
  useEffect(() => { cargar() }, [cargar])
  useEffect(() => {
    api.ambiente.catalogos().then(setCat).catch(() => {}); api.ambiente.obligaciones().then(setObligaciones).catch(() => {})
    api.org.areas().then((d) => setAreas(d.results ?? d)).catch(() => {}); api.org.puestos().then((d) => setPuestos(d.results ?? d)).catch(() => {})
  }, [])
  const lista = (items || []).filter((a) => vista !== 'positivos' || a.clase === 'positivo')
  const significativo = form && form.clase === 'negativo' && (CRIT.reduce((s, [c]) => s + Number(form[c] || 0), 0) >= 10 || Number(form.legal) === 3)
  const guardar = async () => {
    setErr('')
    const datos = { ...form, sede: form.sede || null, proceso: form.proceso || null, responsable: form.responsable || null, obligacion: form.obligacion || null, plazo: form.plazo || null }
    CRIT.forEach(([c]) => { datos[c] = form.clase === 'negativo' ? Number(form[c]) : null })
    try { form.id ? await api.ambiente.editarAspecto(form.id, datos) : await api.ambiente.crearAspecto(datos); setForm(null); cargar() } catch (e) { setErr(e.message) }
  }
  const retirar = async (a) => {
    const m = await confirmar({ titulo: 'Retirar el aspecto', mensaje: `${a.aspecto} (${a.actividad}). Queda como registro y deja la matriz pendiente de aprobación.`, textoConfirmar: 'Retirar', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } })
    if (m !== null) { try { await api.ambiente.retirarAspecto(a.id, m); cargar() } catch (e) { setError(e.message) } }
  }
  const toggle = (lst, v) => (lst.includes(v) ? lst.filter((x) => x !== v) : [...lst, v])
  const val = (c, n) => cat?.valoracion?.[c]?.[String(n)] || ''
  return (
    <div className="space-y-3">
      {res && (
        <div className="grid gap-3 md:grid-cols-6">
          {[['Aspectos vigentes', res.total], ['Significativos', res.significativos, res.significativos ? 'text-red-600' : ''], ['Por incumplimiento legal', res.por_incumplimiento], ['Positivos', res.positivos], ['Sin responsable', res.sin_responsable, res.sin_responsable ? 'text-amber-600' : ''], ['Plazos vencidos', res.vencidos, res.vencidos ? 'text-red-600' : '']].map(([n, v, c]) => (
            <div key={n} className="card-esynapse p-3"><p className="text-[11px] text-slate-500">{n}</p><p className={`text-2xl font-semibold ${c || ''}`}>{v}</p></div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        {res && <><Chip par={EST_APROB[res.aprobacion.estado]} />{res.aprobacion.fecha && <span className="text-xs text-slate-500">aprobada el {fecha(res.aprobacion.fecha)}{res.aprobacion.cambios ? ` · ${res.aprobacion.cambios} cambio(s) después` : ''}</span>}</>}
        <button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.ambiente.matrizPdf())}><FileText className="h-3.5 w-3.5" /> PDF</button>
        {puedeAprobar && res?.aprobacion.estado !== 'aprobada' && <button className="btn-secondary !py-1 text-xs" onClick={() => setAprob(true)}><ShieldCheck className="h-3.5 w-3.5" /> Aprobación del Comité</button>}
        {puedeCrear && <button className="btn-primary ml-auto !py-1 text-xs" onClick={() => { setErr(''); setForm({ ...ASP_VACIO }) }}><Plus className="h-3.5 w-3.5" /> Aspecto</button>}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {sedes.length > 1 && <SelectorSede sedes={sedes} valor={sedeF} onChange={setSedeF} className="w-48" />}
        <select className={`${inp} w-64`} value={lugar} onChange={(e) => setLugar(e.target.value)}>
          <option value="">Todos los lugares</option>
          {(cat?.alcances || []).filter(([k]) => k !== 'areas').map(([k, n]) => <option key={k} value={k}>{n}</option>)}
          <optgroup label="Áreas y laboratorios">{areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}</optgroup>
        </select>
        <div className="relative"><Search className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-slate-400" /><input className={`${inp} w-64 pl-8`} placeholder="Buscar aspecto, impacto o actividad" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <Vistas opciones={[['todos', 'Todos'], ['significativos', 'Significativos'], ['positivos', 'Positivos']]} valor={vista} onChange={setVista} />
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig min-w-[1150px]">
          <thead><tr><th>Lugar</th><th>Proceso</th><th>Actividad</th><th>Aspecto</th><th>Impacto</th><th className="text-center">Situación</th>{CRIT.map(([, l]) => <th key={l} className="text-center" title={l}>{l}</th>)}<th className="text-right">Total</th><th className="text-center">Significativo</th><th>Responsable</th><th className="text-right">Plazo</th><th /></tr></thead>
          <tbody>
            {lista.map((a) => (
              <tr key={a.id}>
                <td className="max-w-[10rem] text-slate-500"><span className="line-clamp-2" title={a.lugar_texto}>{a.lugar_texto}</span></td>
                <td className="text-slate-500">{a.proceso_nombre || 'Todos'}</td>
                <td className="max-w-[12rem]"><span className="line-clamp-2" title={a.actividad}>{a.actividad}</span></td>
                <td className="max-w-[13rem]"><span className="line-clamp-2" title={a.aspecto}>{a.aspecto}</span>{a.clase === 'positivo' && <span className="ml-1 rounded bg-emerald-500/15 px-1 text-[10px] text-emerald-600">positivo</span>}</td>
                <td className="max-w-[12rem] text-slate-500"><span className="line-clamp-2" title={a.impacto}>{a.impacto}</span></td>
                <td className="text-center text-xs">{(a.situaciones || []).join(' · ')}</td>
                {CRIT.map(([c]) => <td key={c} className={`text-center ${c === 'legal' && a[c] === 3 ? 'font-bold text-red-600' : ''}`}>{a[c] ?? '—'}</td>)}
                <td className="text-right font-semibold">{a.resultado ?? '—'}</td>
                <td className="text-center">{a.clase === 'positivo' ? '—' : <Chip par={a.significativo ? ['SI', ROJO] : ['NO', VERDE]} />}</td>
                <td className="text-slate-500">{a.responsable_nombre || (a.significativo ? <span className="text-amber-600">Falta</span> : '—')}</td>
                <td className={`whitespace-nowrap text-right ${a.plazo && a.plazo < hoyLocal() && a.significativo ? 'text-red-600' : ''}`}>{a.plazo ? fecha(a.plazo) : (a.significativo ? <span className="text-amber-600">Falta</span> : '—')}</td>
                <td className="whitespace-nowrap">{puedeEditar && <button className="p-1 text-slate-500" title="Editar" onClick={() => { setErr(''); setForm({ ...ASP_VACIO, ...a, sede: a.sede || '', proceso: a.proceso || '', responsable: a.responsable || '', obligacion: a.obligacion || '', plazo: a.plazo || '', legal: a.legal ?? 1, severidad: a.severidad ?? 1, partes: a.partes ?? 1, escala: a.escala ?? 1, frecuencia: a.frecuencia ?? 1 }) }}><Pencil className="h-3.5 w-3.5" /></button>}{puedeEliminar && <button className="p-1 text-red-500" title="Retirar" onClick={() => retirar(a)}><X className="h-3.5 w-3.5" /></button>}</td>
              </tr>
            ))}
            {items && lista.length === 0 && <tr><td colSpan={16} className="py-8 text-center text-slate-400">Sin aspectos</td></tr>}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-slate-500">Significativo: suma de A a E igual o mayor a 10, o incumplimiento legal (A = 3). Los aspectos positivos se identifican pero no se evalúan.</p>
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Editar aspecto ambiental' : 'Nuevo aspecto ambiental'} onCerrar={() => setForm(null)} ancho="max-w-5xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-4">
              {sedes.length > 0 && <div><label className={lbl}>Sede</label><SelectorSede sedes={sedes} valor={form.sede} todas="Todas las sedes" onChange={(v) => setForm({ ...form, sede: v, areas: v ? form.areas.filter((id) => (areas.find((a) => a.id === id) || {}).sede === v) : form.areas })} /></div>}
              <div><label className={lbl}>Lugar</label><select className={inp} value={form.alcance} onChange={(e) => setForm({ ...form, alcance: e.target.value })}>{(cat?.alcances || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              {form.alcance === 'otro' && <div><label className={lbl}>Describa el lugar</label><input className={inp} value={form.lugar} onChange={(e) => setForm({ ...form, lugar: e.target.value })} /></div>}
              <div><label className={lbl}>Proceso</label><select className={inp} value={form.proceso} onChange={(e) => setForm({ ...form, proceso: e.target.value })}><option value="">Todos los procesos</option><OpcionesProcesos procesos={procesos} /></select></div>
            </div>
            {form.alcance === 'areas' && <div><label className={lbl}>Áreas o laboratorios</label><div className="grid max-h-36 gap-1 overflow-y-auto rounded border border-slate-200 p-2 text-xs md:grid-cols-3 dark:border-slate-800">{areas.filter((a) => !form.sede || a.sede === form.sede).map((a) => <label key={a.id} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" checked={form.areas.includes(a.id)} onChange={() => setForm({ ...form, areas: toggle(form.areas, a.id) })} />{a.nombre}</label>)}</div></div>}
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Actividad</label><CampoAmpliable value={form.actividad} onChange={(v) => setForm({ ...form, actividad: v })} /></div>
              <div><label className={lbl}>Aspecto ambiental</label><CampoAmpliable value={form.aspecto} onChange={(v) => setForm({ ...form, aspecto: v })} /></div>
              <div><label className={lbl}>Impacto ambiental</label><CampoAmpliable value={form.impacto} onChange={(v) => setForm({ ...form, impacto: v })} /></div>
            </div>
            <div className="grid gap-3 md:grid-cols-4 text-xs">
              <div><label className={lbl}>Situación</label><div className="flex gap-3">{(cat?.situaciones || []).map(([k, n]) => <label key={k} className="flex items-center gap-1" title={n}><input type="checkbox" className="accent-esynapse-600" checked={form.situaciones.includes(k)} onChange={() => setForm({ ...form, situaciones: toggle(form.situaciones, k) })} />{n.split(' ')[0]}</label>)}</div></div>
              <div><label className={lbl}>Generación</label><select className={inp} value={form.generacion} onChange={(e) => setForm({ ...form, generacion: e.target.value })}>{(cat?.generacion || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Clase</label><select className={inp} value={form.clase} onChange={(e) => setForm({ ...form, clase: e.target.value })}>{(cat?.clases || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Etapa del ciclo de vida</label><select className={inp} value={form.etapa_ciclo} onChange={(e) => setForm({ ...form, etapa_ciclo: e.target.value })}>{(cat?.etapas || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
            </div>
            <div><label className={lbl}>Controles existentes</label><CampoAmpliable multilinea rows={2} value={form.controles_existentes} onChange={(v) => setForm({ ...form, controles_existentes: v })} /></div>
            {form.clase === 'negativo' ? (
              <div className="rounded-lg border border-slate-200 p-2 dark:border-slate-800">
                <div className="mb-2 grid gap-2 md:grid-cols-2"><div><label className={lbl}>Requisito legal asociado (Requisitos legales, ámbito ambiental)</label><select className={inp} value={form.obligacion} onChange={(e) => setForm({ ...form, obligacion: e.target.value })}><option value="">— Ninguno —</option>{obligaciones.map((o) => <option key={o.id} value={o.id}>{o.texto}</option>)}</select></div>
                  {(() => { const o = obligaciones.find((x) => String(x.id) === String(form.obligacion)); return o && o.legal_sugerido ? <p className="self-end text-[11px] text-slate-500">Según su última evaluación de cumplimiento, A = {o.legal_sugerido}. {Number(form.legal) !== o.legal_sugerido && <button className="text-esynapse-500 underline" onClick={() => setForm({ ...form, legal: o.legal_sugerido })}>Usar</button>}</p> : null })()}</div>
                <div className="grid gap-2 md:grid-cols-5">
                  {(cat?.criterios || []).map(([c, n]) => (
                    <div key={c}><label className={lbl}>{n}</label><select className={inp} value={form[c]} onChange={(e) => setForm({ ...form, [c]: Number(e.target.value) })}>{[1, 2, 3].map((v) => <option key={v} value={v}>{v} · {['Bajo', 'Medio', 'Alto'][v - 1]}</option>)}</select><p className="mt-0.5 text-[10px] leading-tight text-slate-500">{val(c, form[c])}</p></div>
                  ))}
                </div>
                <p className="mt-2 text-xs">Resultado: <strong>{CRIT.reduce((s, [c]) => s + Number(form[c] || 0), 0)}</strong> · {significativo ? <Chip par={['Significativo', ROJO]} /> : <Chip par={['No significativo', VERDE]} />}</p>
              </div>
            ) : <p className="rounded bg-emerald-500/10 p-2 text-xs text-emerald-700 dark:text-emerald-300">Aspecto positivo: se identifica para potenciar sus efectos, pero no se evalúa.</p>}
            <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Control operacional{significativo && <span className="text-red-500"> *</span>}</label><CampoAmpliable multilinea rows={2} value={form.control_operacional} onChange={(v) => setForm({ ...form, control_operacional: v })} /></div>
              <div><label className={lbl}>Registro asociado</label><CampoAmpliable multilinea rows={2} value={form.registro_asociado} onChange={(v) => setForm({ ...form, registro_asociado: v })} /></div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Responsable{significativo && <span className="text-red-500"> *</span>}</label><select className={inp} value={form.responsable} onChange={(e) => setForm({ ...form, responsable: e.target.value })}><option value="">—</option>{puestos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></div>
              <div><label className={lbl}>Plazo de implementación{significativo && <span className="text-red-500"> *</span>}</label><input type="date" className={inp} value={form.plazo} onChange={(e) => setForm({ ...form, plazo: e.target.value })} /></div>
              <div><label className={lbl}>Criterio de seguimiento</label><input className={inp} value={form.criterio_seguimiento} onChange={(e) => setForm({ ...form, criterio_seguimiento: e.target.value })} /></div>
            </div>
            {form.historial?.length > 0 && <details className="text-xs text-slate-500"><summary className="cursor-pointer">Historial ({form.historial.length})</summary>{form.historial.slice().reverse().map((h, i) => <p key={i}>{fecha(h.fecha)} · {h.usuario} · {h.accion}{h.campos ? `: ${h.campos}` : ''}</p>)}</details>}
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
      {aprob && <AprobacionComite onCerrar={() => setAprob(false)} alAprobar={() => { setAprob(false); cargar() }} />}
    </div>
  )
}

/* Aprobación de la matriz por TODOS los titulares del Comité de SST (o el acta firmada por todos). */
function AprobacionComite({ onCerrar, alAprobar }) {
  const [d, setD] = useState(null)
  const [modo, setModo] = useState('pantalla')
  const [f, setF] = useState({ fecha: hoyLocal(), observaciones: '', archivo: null, password: '' })
  const [firmas, setFirmas] = useState({})
  const [err, setErr] = useState('')
  const [enviando, setEnviando] = useState(false)
  const cargar = useCallback(() => api.ambiente.aprobaciones().then((x) => { setD(x); setFirmas((prev) => Object.fromEntries(x.titulares.map((t) => [t.id, prev[t.id] || {}]))) }).catch((e) => setErr(e.message)), [])
  useEffect(() => { cargar() }, [cargar])
  const enviar = async () => {
    setErr(''); setEnviando(true)
    try {
      if (modo === 'papel') {
        if (!f.archivo) { setErr('Adjunte el acta firmada por todos los titulares.'); return }
        const fd = new FormData(); fd.append('fecha', f.fecha); fd.append('observaciones', f.observaciones); fd.append('firmantes', JSON.stringify(d.titulares.map((t) => t.id))); fd.append('archivo', f.archivo); fd.append('password', f.password)
        await api.ambiente.aprobarPapel(fd)
      } else {
        const lista = d.titulares.map((t) => { const c = firmas[t.id] || {}; return { miembro: t.id, clave: c.clave, pin: c.pin, pin_nuevo: c.pin_nuevo, pin_confirmacion: c.pin_confirmacion } })
        await api.ambiente.aprobar({ fecha: f.fecha, observaciones: f.observaciones, firmas: lista })
      }
      alAprobar()
    } catch (e) { setErr(e.message); cargar() } finally { setEnviando(false) }
  }
  return (
    <Modal abierto titulo="Aprobación de la matriz de aspectos e impactos ambientales" onCerrar={onCerrar} ancho="max-w-4xl">
      <div className="space-y-3 text-sm">
        <p className="text-xs text-slate-500">La aprueban <strong>todos los titulares</strong> del Comité de SST{d?.comite ? ` (${d.comite})` : ''}, cada uno con la contraseña de su usuario o con su PIN; o se adjunta el acta firmada por todos.</p>
        {d && !d.titulares.length && <Aviso texto="El comité vigente no tiene titulares registrados (SST › Participación › Comité de SST)." />}
        <div className="grid gap-3 md:grid-cols-3"><div><label className={lbl}>Fecha de aprobación</label><input type="date" className={inp} value={f.fecha} onChange={(e) => setF({ ...f, fecha: e.target.value })} /></div></div>
        <div className="flex gap-4 text-xs"><label className="flex items-center gap-1"><input type="radio" checked={modo === 'pantalla'} onChange={() => setModo('pantalla')} /> Firman en pantalla</label><label className="flex items-center gap-1"><input type="radio" checked={modo === 'papel'} onChange={() => setModo('papel')} /> Acta firmada en papel</label></div>
        <table className="w-full text-xs"><tbody>{(d?.titulares || []).map((t) => (
          <tr key={t.id} className="border-t border-slate-100 dark:border-slate-800/60"><td className="py-1">{t.nombre}<span className="block text-[10px] text-slate-500">{t.cargo}</span></td>{modo === 'pantalla' && <td className="w-72"><Credencial forma={t.firma} valor={firmas[t.id]} onChange={(v) => setFirmas({ ...firmas, [t.id]: v })} /></td>}</tr>
        ))}</tbody></table>
        {modo === 'papel' && <div className="grid gap-3 md:grid-cols-2"><div><label className={lbl}>Acta firmada (escaneada)</label><input type="file" className="text-xs" onChange={(e) => setF({ ...f, archivo: e.target.files[0] || null })} /></div><div><label className={lbl}>Su contraseña (quien registra)</label><input type="password" autoComplete="current-password" className={inp} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></div></div>}
        <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} value={f.observaciones} onChange={(v) => setF({ ...f, observaciones: v })} /></div>
        {(d?.historial || []).length > 0 && <details className="text-xs text-slate-500"><summary className="cursor-pointer">Aprobaciones anteriores ({d.historial.length})</summary>{d.historial.map((h) => <p key={h.id}>{fecha(h.fecha)} · {h.aspectos} aspectos · {h.firmas.map((x) => `${x.nombre} (${METODO[x.metodo] || x.metodo})`).join(', ')}{h.archivo_url && <> · <a className="underline" href={h.archivo_url} target="_blank" rel="noreferrer">acta</a></>}</p>)}</details>}
        {err && <Aviso texto={err} />}
        <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={onCerrar}>Cerrar</button><button className="btn-primary" disabled={enviando || !d?.titulares.length} onClick={enviar}>Registrar la aprobación</button></div>
      </div>
    </Modal>
  )
}

/* ============================================================================================ residuos */
function Residuos({ sedes, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeEliminar }) {
  const [vista, setVista] = useState('pesajes')
  const [anio, setAnio] = useState(ANIO)
  const [sede, setSede] = useState('')
  const [cat, setCat] = useState(null)
  useEffect(() => { api.ambiente.catalogosResiduos().then(setCat).catch(() => {}) }, [])
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Vistas opciones={[['pesajes', 'Pesajes'], ['disposicion', 'Disposición'], ['resumen', 'Resumen anual']]} valor={vista} onChange={setVista} />
        <select className={`${inp} w-28`} value={anio} onChange={(e) => setAnio(Number(e.target.value))}>{[ANIO - 2, ANIO - 1, ANIO].map((a) => <option key={a} value={a}>{a}</option>)}</select>
        {sedes.length > 1 && <SelectorSede sedes={sedes} valor={sede} onChange={setSede} className="w-48" />}
      </div>
      {vista === 'pesajes' && <Pesajes {...{ anio, sede, sedes, cat, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeEliminar }} />}
      {vista === 'disposicion' && <Disposiciones {...{ anio, sede, sedes, cat, confirmar, setError, puedeCrear, puedeEditar, puedeEliminar }} />}
      {vista === 'resumen' && <ResumenResiduos anio={anio} sede={sede} setError={setError} />}
    </div>
  )
}

function Pesajes({ anio, sede, sedes, cat, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeEliminar }) {
  const [items, setItems] = useState([])
  const [trab, setTrab] = useState([])
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.ambiente.pesajes(`?anio=${anio}${sede ? `&sede=${sede}` : ''}`).then(setItems).catch((e) => setError(e.message)), [anio, sede, setError])
  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { api.org.trabajadores('?estado=activo').then((d) => setTrab(d.results ?? d)).catch(() => {}) }, [])
  const cats = cat?.categorias || []
  const nuevo = () => { setErr(''); setForm({ sede: sede || (sedes.length === 1 ? sedes[0].id : ''), tipo: 'ingreso', fecha: hoyLocal(), hora: '', responsable: '', observaciones: '', items: cats.flatMap((c) => (c.sugeridos.length ? c.sugeridos : ['']).map((t) => ({ categoria: c.clave, tipo: t, kg: '', litros: '', cantidad: '', observaciones: '' }))) }) }
  const editable = form && (!form.id || form.estado === 'en_registro') && puedeEditar
  const guardar = async () => {
    setErr('')
    try { const r = await api.ambiente.guardarPesaje(form.id, { sede: form.sede || null, tipo: form.tipo, fecha: form.fecha, hora: form.hora || null, responsable: form.responsable || null, observaciones: form.observaciones, items: form.items }); setForm({ ...r, items: completar(r.items) }); cargar(); return r } catch (e) { setErr(e.message); return null }
  }
  const completar = (lst) => { const r = [...lst]; cats.forEach((c) => { if (!r.some((i) => i.categoria === c.clave)) r.push({ categoria: c.clave, tipo: '', kg: '', litros: '', cantidad: '', observaciones: '' }) }); return r }
  const cerrar = async () => {
    const r = await guardar(); if (!r) return
    const c = await confirmar({ titulo: 'Cerrar el pesaje', mensaje: `Total: ${num(r.totales.total_kg)} kg${Number(r.totales.peligrosos_litros) ? ` y ${num(r.totales.peligrosos_litros)} L` : ''}. Firma como responsable del registro.`, textoConfirmar: 'Firmar y cerrar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
    if (c === null) return
    try { const x = await api.ambiente.accionPesaje(r.id, 'cerrar', { password: c }); setForm(x); cargar() } catch (e) { setErr(e.message) }
  }
  const anular = async (p) => { const m = await confirmar({ titulo: 'Anular el pesaje', mensaje: p.codigo, textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) { try { await api.ambiente.accionPesaje(p.id, 'anular', { motivo: m }); setForm(null); cargar() } catch (e) { setError(e.message) } } }
  const fila = (k, campo, v) => setForm({ ...form, items: form.items.map((x, j) => (j === k ? { ...x, [campo]: v } : x)) })
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><p className="text-xs text-slate-500">Pesaje mensual por tipo de residuo, al ingreso al almacén temporal y a la salida.</p>{puedeCrear && <button className="btn-primary ml-auto !py-1 text-xs" onClick={nuevo}><Plus className="h-3.5 w-3.5" /> Pesaje</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig">
          <thead><tr><th>N°</th><th>Sede</th><th className="text-center">Tipo</th><th className="text-right">Fecha</th><th>Responsable</th><th className="text-right">No peligrosos (kg)</th><th className="text-right">Peligrosos (kg)</th><th className="text-right">Peligrosos (L)</th><th className="text-center">Estado</th><th /></tr></thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id} className="cursor-pointer" onClick={() => { setErr(''); setForm({ ...p, hora: (p.hora || '').slice(0, 5), items: completar(p.items) }) }}>
                <td className="whitespace-nowrap font-mono text-xs">{p.codigo}</td><td className="text-xs">{p.sede_nombre || '—'}</td><td className="text-center text-xs">{p.tipo === 'ingreso' ? 'Ingreso' : 'Salida'}</td><td className="text-right">{fecha(p.fecha)}</td><td>{p.responsable_nombre || '—'}</td>
                <td className="text-right">{num(p.totales.no_peligrosos_kg)}</td><td className="text-right">{num(p.totales.peligrosos_kg)}</td><td className="text-right">{num(p.totales.peligrosos_litros)}</td>
                <td className="text-center"><Chip par={EST_PESAJE[p.estado]} /></td>
                <td onClick={(e) => e.stopPropagation()}><button className="p-1 text-slate-500" title="PDF" onClick={() => abrirPdf(api.ambiente.pesajePdf(p.id))}><FileText className="h-3.5 w-3.5" /></button></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={10} className="py-8 text-center text-slate-400">Sin pesajes en {anio}</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.codigo ? `Pesaje ${form.codigo}` : 'Nuevo pesaje de residuos'} onCerrar={() => setForm(null)} ancho="max-w-4xl">
        {form && (
          <div className="space-y-3 text-sm">
            {form.estado && form.estado !== 'en_registro' && <p className="text-xs text-slate-500"><Chip par={EST_PESAJE[form.estado]} /> {form.firma?.nombre ? `Firmado por ${form.firma.nombre} el ${fechaHora(form.firma.fecha)}` : form.motivo_anulacion}</p>}
            <div className="grid gap-3 md:grid-cols-5">
              <div><label className={lbl}>Sede</label><SelectorSede sedes={sedes} valor={form.sede} todas="—" disabled={!editable} onChange={(v) => setForm({ ...form, sede: v })} /></div>
              <div><label className={lbl}>Tipo de pesaje</label><select className={inp} disabled={!editable} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{(cat?.tipos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} disabled={!editable} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
              <div><label className={lbl}>Hora</label><input type="time" className={inp} disabled={!editable} value={form.hora || ''} onChange={(e) => setForm({ ...form, hora: e.target.value })} /></div>
              <div><label className={lbl}>Responsable del pesaje</label><select className={inp} disabled={!editable} value={form.responsable || ''} onChange={(e) => setForm({ ...form, responsable: e.target.value })}><option value="">—</option>{trab.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo}</option>)}</select></div>
            </div>
            {cats.map((c) => (
              <div key={c.clave} className="rounded-lg border border-slate-200 p-2 dark:border-slate-800">
                <p className="mb-1 text-xs font-semibold">{c.nombre} <span className="font-normal text-slate-500">({c.unidad === 'L' ? 'litros' : c.clave === 'raee' ? 'cantidad y kg' : 'kg'})</span></p>
                <table className="tabla-sig w-full text-xs"><tbody>{form.items.map((i, k) => i.categoria !== c.clave ? null : (
                  <tr key={k}>
                    <td><input className={`${inp} !py-1 text-xs`} disabled={!editable} placeholder={c.clave === 'raee' ? 'Descripción' : 'Tipo específico'} value={i.tipo || ''} onChange={(e) => fila(k, 'tipo', e.target.value)} /></td>
                    {c.clave === 'raee' && <td className="w-24"><input type="number" min="0" className={`${inp} !py-1 text-right text-xs`} disabled={!editable} placeholder="Cant." value={i.cantidad ?? ''} onChange={(e) => fila(k, 'cantidad', e.target.value)} /></td>}
                    <td className="w-28"><input type="number" min="0" step="0.01" className={`${inp} !py-1 text-right text-xs`} disabled={!editable} placeholder={c.unidad} value={(c.unidad === 'L' ? i.litros : i.kg) ?? ''} onChange={(e) => fila(k, c.unidad === 'L' ? 'litros' : 'kg', e.target.value)} /></td>
                    <td><input className={`${inp} !py-1 text-xs`} disabled={!editable} placeholder="Observaciones" value={i.observaciones || ''} onChange={(e) => fila(k, 'observaciones', e.target.value)} /></td>
                  </tr>
                ))}</tbody></table>
                {editable && <button className="mt-1 text-xs text-esynapse-500 underline" onClick={() => setForm({ ...form, items: [...form.items, { categoria: c.clave, tipo: '', kg: '', litros: '', cantidad: '', observaciones: '' }] })}>+ línea</button>}
              </div>
            ))}
            <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} disabled={!editable} value={form.observaciones || ''} onChange={(v) => setForm({ ...form, observaciones: v })} /></div>
            {err && <Aviso texto={err} />}
            <div className="flex flex-wrap justify-end gap-2">
              {form.id && <button className="btn-secondary" onClick={() => abrirPdf(api.ambiente.pesajePdf(form.id))}><FileText className="h-4 w-4" /> PDF</button>}
              {form.id && form.estado !== 'anulado' && puedeEliminar && <button className="btn-secondary text-red-600" onClick={() => anular(form)}>Anular</button>}
              {editable && <><button className="btn-secondary" onClick={guardar}>Guardar</button><button className="btn-primary" onClick={cerrar}>Firmar y cerrar</button></>}
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

const DISP_VACIA = { sede: '', fecha: '', grupo: 'no_peligroso', descripcion: '', kg: '', destino: 'reciclaje', operadora: '', registro_operadora: '', manifiesto: '', observaciones: '', certificado: null }

function Disposiciones({ anio, sede, sedes, cat, confirmar, setError, puedeCrear, puedeEditar, puedeEliminar }) {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.ambiente.disposiciones(`?anio=${anio}${sede ? `&sede=${sede}` : ''}`).then(setItems).catch((e) => setError(e.message)), [anio, sede, setError])
  useEffect(() => { cargar() }, [cargar])
  const guardar = async () => {
    setErr('')
    const fd = new FormData()
    Object.entries(form).forEach(([k, v]) => { if (['id', 'certificado_url', 'grupo_display', 'destino_display', 'sede_nombre'].includes(k)) return; if (k === 'certificado') { if (v instanceof File) fd.append(k, v) } else if (v !== null && v !== undefined) fd.append(k, v) })
    try { await api.ambiente.guardarDisposicion(form.id, fd); setForm(null); cargar() } catch (e) { setErr(e.message) }
  }
  const quitar = async (d) => { if (await confirmar({ titulo: 'Dar de baja la disposición', mensaje: `${fecha(d.fecha)} · ${num(d.kg)} kg (se conserva como registro)`, textoConfirmar: 'Dar de baja', peligro: true })) { try { await api.ambiente.quitarDisposicion(d.id); cargar() } catch (e) { setError(e.message) } } }
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><p className="text-xs text-slate-500">Entrega de residuos para disposición, reciclaje, donación o venta, con su certificado o constancia.</p>{puedeCrear && <button className="btn-primary ml-auto !py-1 text-xs" onClick={() => { setErr(''); setForm({ ...DISP_VACIA, sede: sede || (sedes.length === 1 ? sedes[0].id : ''), fecha: hoyLocal() }) }}><Plus className="h-3.5 w-3.5" /> Disposición</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig">
          <thead><tr><th className="text-right">Fecha</th><th>Sede</th><th className="text-center">Residuo</th><th>Descripción</th><th className="text-right">kg</th><th className="text-center">Destino</th><th>Operadora / receptor</th><th>Manifiesto</th><th className="text-center">Certificado</th><th /></tr></thead>
          <tbody>
            {items.map((d) => (
              <tr key={d.id}><td className="text-right">{fecha(d.fecha)}</td><td className="text-xs">{d.sede_nombre || '—'}</td><td className="text-center"><Chip par={[d.grupo_display, d.grupo === 'no_peligroso' ? AZUL : ROJO]} /></td><td>{d.descripcion || '—'}</td><td className="text-right">{num(d.kg)}</td><td className="text-center text-xs">{d.destino_display}</td><td>{d.operadora || '—'}{d.registro_operadora && <span className="block text-[10px] text-slate-500">{d.registro_operadora}</span>}</td><td>{d.manifiesto || '—'}</td><td className="text-center">{d.certificado_url ? <a className="text-esynapse-500 underline" href={d.certificado_url} target="_blank" rel="noreferrer">ver</a> : <span className="text-amber-600">Falta</span>}</td>
                <td className="whitespace-nowrap">{puedeEditar && <button className="p-1 text-slate-500" onClick={() => { setErr(''); setForm({ ...DISP_VACIA, ...d, sede: d.sede || '', certificado: null }) }}><Pencil className="h-3.5 w-3.5" /></button>}{puedeEliminar && <button className="p-1 text-red-500" onClick={() => quitar(d)}><X className="h-3.5 w-3.5" /></button>}</td></tr>
            ))}
            {items.length === 0 && <tr><td colSpan={10} className="py-8 text-center text-slate-400">Sin disposiciones en {anio}</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Editar disposición' : 'Nueva disposición de residuos'} onCerrar={() => setForm(null)} ancho="max-w-3xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-5">
              <div><label className={lbl}>Sede</label><SelectorSede sedes={sedes} valor={form.sede} todas="—" onChange={(v) => setForm({ ...form, sede: v })} /></div>
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
              <div><label className={lbl}>Residuo</label><select className={inp} value={form.grupo} onChange={(e) => setForm({ ...form, grupo: e.target.value, destino: e.target.value === 'peligroso' ? 'eors' : form.destino })}>{(cat?.grupos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Cantidad (kg)</label><input type="number" min="0" step="0.01" className={inp} value={form.kg} onChange={(e) => setForm({ ...form, kg: e.target.value })} /></div>
              <div><label className={lbl}>Destino</label><select className={inp} value={form.destino} onChange={(e) => setForm({ ...form, destino: e.target.value })}>{(cat?.destinos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
            </div>
            <div><label className={lbl}>Descripción</label><input className={inp} value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Operadora / receptor</label><input className={inp} value={form.operadora} onChange={(e) => setForm({ ...form, operadora: e.target.value })} /></div>
              <div><label className={lbl}>N° de registro de la operadora</label><input className={inp} value={form.registro_operadora} onChange={(e) => setForm({ ...form, registro_operadora: e.target.value })} /></div>
              <div><label className={lbl}>N° de manifiesto / guía</label><input className={inp} value={form.manifiesto} onChange={(e) => setForm({ ...form, manifiesto: e.target.value })} /></div>
            </div>
            <div><label className={lbl}>Certificado o constancia {form.certificado_url && <a className="ml-1 text-esynapse-500 underline" href={form.certificado_url} target="_blank" rel="noreferrer">(actual)</a>}</label><input type="file" className="text-xs" onChange={(e) => setForm({ ...form, certificado: e.target.files[0] || null })} /></div>
            <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} value={form.observaciones} onChange={(v) => setForm({ ...form, observaciones: v })} /></div>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}

function ResumenResiduos({ anio, sede, setError }) {
  const [d, setD] = useState(null)
  useEffect(() => { setD(null); api.ambiente.resumenResiduos(anio, sede).then(setD).catch((e) => setError(e.message)) }, [anio, sede, setError])
  if (!d) return <p className="text-sm text-slate-400">Cargando…</p>
  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-4">
        {[['Generado en el año', `${num(d.generado_kg)} kg`], ['Toneladas', num(d.generado_tm, 4)], ['Dispuesto', `${num(d.dispuesto_kg)} kg`], ['% dispuesto', d.porcentaje_dispuesto == null ? '—' : `${d.porcentaje_dispuesto} %`]].map(([n, v]) => <div key={n} className="card-esynapse p-3"><p className="text-[11px] text-slate-500">{n}</p><p className="text-2xl font-semibold">{v}</p></div>)}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig">
          <thead><tr><th>Mes</th><th className="text-right">No peligrosos (kg)</th><th className="text-right">Peligrosos (kg)</th><th className="text-right">Peligrosos (L)</th><th className="text-right">No peligrosos (TM)</th><th className="text-right">Peligrosos (TM)</th><th className="text-right">Dispuesto no peligroso (kg)</th><th className="text-right">Dispuesto peligroso (kg)</th></tr></thead>
          <tbody>{d.meses.map((m) => <tr key={m.mes}><td>{m.nombre}</td><td className="text-right">{num(m.generado_no_peligroso_kg)}</td><td className="text-right">{num(m.generado_peligroso_kg)}</td><td className="text-right">{num(m.generado_peligroso_litros)}</td><td className="text-right">{num(m.generado_no_peligroso_tm, 4)}</td><td className="text-right">{num(m.generado_peligroso_tm, 4)}</td><td className="text-right">{num(m.dispuesto_no_peligroso_kg)}</td><td className="text-right">{num(m.dispuesto_peligroso_kg)}</td></tr>)}</tbody>
        </table>
      </div>
      <p className="text-[11px] text-slate-500">Generado: pesajes de ingreso cerrados. Base de la declaración anual de manejo de residuos sólidos (toneladas por mes, peligrosos y no peligrosos).</p>
    </div>
  )
}

/* ============================================================================================ consumos */
const ORIGEN = { lectura: 'Lectura del medidor', recibo: 'Recibo', arrendador: 'Informado por el arrendador', estimado: 'Estimado' }
const CONS_VACIO = { suministro: '', anio: ANIO, mes: new Date().getMonth() + 1, origen: '', fecha_lectura: '', lectura_anterior: '', lectura_actual: '', cambio_medidor: false, motivo_cambio: '', consumo: '', monto: '', observaciones: '', evidencia: null }

function Consumos({ sedes, confirmar, setError, puedeCrear, puedeEditar, puedeEliminar }) {
  const [anio, setAnio] = useState(ANIO)
  const [sede, setSede] = useState('')
  const [d, setD] = useState(null)
  const [form, setForm] = useState(null)
  const [previo, setPrevio] = useState(null)
  const [err, setErr] = useState('')
  const [aviso, setAviso] = useState('')
  const cargar = useCallback(() => { api.ambiente.indicadores(anio, sede).then(setD).catch((e) => setError(e.message)) }, [anio, sede, setError])
  useEffect(() => { cargar() }, [cargar])
  const suministros = useMemo(() => sedes.flatMap((s) => (s.suministros || []).filter((x) => x.is_active).map((x) => ({ ...x, sede_nombre: s.nombre }))), [sedes])
  const sumi = form && suministros.find((x) => x.id === Number(form.suministro))
  useEffect(() => {
    if (!form?.suministro || !form.anio || !form.mes) { setPrevio(null); return }
    api.ambiente.lecturaAnterior(form.suministro, form.anio, form.mes, form.id || '').then(setPrevio).catch(() => setPrevio(null))
  }, [form?.suministro, form?.anio, form?.mes, form?.id])
  const origen = form ? (form.origen || (sumi?.modalidad === 'recibo' ? 'recibo' : 'lectura')) : 'lectura'
  const porLectura = origen === 'lectura'
  const anteriorAuto = Boolean(form) && porLectura && !form.cambio_medidor && previo?.lectura_anterior != null
  const anteriorVal = anteriorAuto ? previo.lectura_anterior : form?.lectura_anterior
  const calculado = form && porLectura && form.lectura_actual !== '' && form.lectura_actual != null && anteriorVal !== '' && anteriorVal != null ? Number(form.lectura_actual) - Number(anteriorVal) : null
  const nuevo = (extra = {}) => { setErr(''); setForm({ ...CONS_VACIO, anio, ...extra }) }
  const abrir = async (id) => { setErr(''); try { const c = await api.ambiente.consumo(id); setForm({ ...CONS_VACIO, ...Object.fromEntries(Object.entries(c).map(([k, v]) => [k, v ?? ''])), evidencia: null }) } catch (e) { setError(e.message) } }
  const guardar = async () => {
    setErr('')
    const fd = new FormData()
    const datos = { suministro: form.suministro, anio: form.anio, mes: form.mes, origen, observaciones: form.observaciones || '', monto: form.monto }
    if (porLectura) Object.assign(datos, { lectura_actual: form.lectura_actual, fecha_lectura: form.fecha_lectura, cambio_medidor: form.cambio_medidor ? 'true' : 'false', motivo_cambio: form.motivo_cambio || '', ...(anteriorAuto ? {} : { lectura_anterior: form.lectura_anterior }) })
    else datos.consumo = form.consumo
    Object.entries(datos).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== '') fd.append(k, v) })
    if (form.evidencia instanceof File) fd.append('evidencia', form.evidencia)
    try { const r = await api.ambiente.guardarConsumo(form.id, fd); setForm(null); setAviso(r.aviso ? `${r.suministro_nombre} · ${MESES[r.mes - 1]} ${r.anio}: ${r.aviso}` : ''); cargar() } catch (e) { setErr(e.message) }
  }
  const quitar = async () => { if (await confirmar({ titulo: 'Anular el registro', mensaje: `${sumi?.nombre || form.suministro_nombre || ''} · ${MESES[form.mes - 1]} ${form.anio} (se conserva como registro anulado)`, textoConfirmar: 'Anular', peligro: true })) { try { await api.ambiente.quitarConsumo(form.id); setForm(null); cargar() } catch (e) { setErr(e.message) } } }
  const hoy = new Date()
  const futuro = (m) => anio > hoy.getFullYear() || (anio === hoy.getFullYear() && m > hoy.getMonth() + 1)
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select className={`${inp} w-28`} value={anio} onChange={(e) => setAnio(Number(e.target.value))}>{[ANIO - 2, ANIO - 1, ANIO].map((a) => <option key={a} value={a}>{a}</option>)}</select>
        {sedes.length > 1 && <SelectorSede sedes={sedes} valor={sede} onChange={setSede} className="w-48" />}
        <p className="text-xs text-slate-500">Consumo de cada suministro por mes (lectura del medidor o recibo); indicadores por trabajador y frente al año anterior.</p>
        {puedeCrear && <button className="btn-primary ml-auto !py-1 text-xs" disabled={!suministros.length} onClick={() => nuevo()}><Plus className="h-3.5 w-3.5" /> Registrar consumo</button>}
      </div>
      {!suministros.length && <p className="rounded bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">No hay suministros registrados. Regístrelos en Organización y personal › Sedes (por sede o por piso, con su medidor).</p>}
      {aviso && <p className="flex items-start gap-2 rounded bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400"><span className="flex-1">{aviso}</span><button onClick={() => setAviso('')}><X className="h-3.5 w-3.5" /></button></p>}
      {d?.sin_suministro > 0 && <p className="text-[11px] text-slate-500">{d.sin_suministro} registro(s) de {anio} anteriores a las sedes, sin suministro: se suman al total de la organización.</p>}
      {d && Object.entries(d.tipos).map(([tipo, t]) => (
        <div key={tipo} className="card-esynapse p-3">
          <div className="mb-2 flex flex-wrap items-center gap-3"><p className="flex items-center gap-1 font-semibold">{tipo === 'energia' ? <Zap className="h-4 w-4 text-amber-500" /> : <Droplets className="h-4 w-4 text-blue-500" />}{t.nombre}{sede ? ` · ${sedes.find((s) => s.id === sede)?.nombre || ''}` : ' · toda la organización'}</p>
            <span className="text-xs text-slate-500">Total {anio}: <strong>{num(t.total)} {t.unidad}</strong>{Number(t.monto) ? ` · S/ ${num(t.monto)}` : ''}{t.variacion != null && <> · <span className={t.variacion > 0 ? 'text-red-600' : 'text-emerald-600'}>{t.variacion > 0 ? '+' : ''}{t.variacion} %</span> frente a los mismos meses de {anio - 1}</>}</span></div>
          <div className="overflow-x-auto">
            <table className="tabla-sig min-w-[900px] text-xs">
              <thead><tr><th>Indicador</th>{t.meses.map((m) => <th key={m.mes} className="text-right">{MESES[m.mes - 1]}</th>)}</tr></thead>
              <tbody>
                <tr><td className="font-semibold">Consumo ({t.unidad})</td>{t.meses.map((m) => <td key={m.mes} className={`text-right font-semibold ${m.estimado ? 'italic' : ''}`} title={m.estimado ? 'Incluye valores estimados' : ''}>{num(m.consumo)}{m.estimado ? '*' : ''}</td>)}</tr>
                <tr><td>Registrados</td>{t.meses.map((m) => <td key={m.mes} className={`text-right ${m.esperados && m.registrados < m.esperados && !futuro(m.mes) ? 'text-amber-600' : 'text-slate-500'}`}>{futuro(m.mes) ? '' : `${m.registrados}/${m.esperados}`}</td>)}</tr>
                <tr><td>Por trabajador</td>{t.meses.map((m) => <td key={m.mes} className="text-right">{num(m.por_trabajador)}</td>)}</tr>
                <tr><td>{anio - 1} ({t.unidad})</td>{t.meses.map((m) => <td key={m.mes} className="text-right text-slate-500">{num(m.anterior)}</td>)}</tr>
                <tr><td>Variación</td>{t.meses.map((m) => <td key={m.mes} className={`text-right ${m.variacion > 0 ? 'text-red-600' : m.variacion < 0 ? 'text-emerald-600' : ''}`}>{m.variacion == null ? '—' : `${m.variacion > 0 ? '+' : ''}${m.variacion} %`}</td>)}</tr>
              </tbody>
            </table>
          </div>
        </div>
      ))}
      {d && d.suministros.length > 0 && (
        <div className="card-esynapse p-3">
          <p className="mb-2 text-sm font-semibold">Detalle por suministro</p>
          <div className="overflow-x-auto">
            <table className="tabla-sig min-w-[1000px] text-xs">
              <thead><tr><th>Suministro</th>{MESES.map((m) => <th key={m} className="text-right">{m}</th>)}<th className="text-right">Total</th></tr></thead>
              <tbody>{d.suministros.map((x) => (
                <tr key={x.id} className={x.activo ? '' : 'opacity-50'}>
                  <td className="whitespace-nowrap">{x.tipo === 'energia' ? <Zap className="mr-1 inline h-3 w-3 text-amber-500" /> : <Droplets className="mr-1 inline h-3 w-3 text-blue-500" />}{x.sede} · {x.nivel || 'toda la sede'} <span className="text-slate-400">({x.unidad}{x.modalidad === 'recibo' ? ', recibo' : ''})</span></td>
                  {x.meses.map((m) => <td key={m.mes} className="text-right">{m.id
                    ? <button className={`underline decoration-dotted ${m.origen === 'estimado' ? 'italic text-amber-600' : 'text-esynapse-600'}`} title={ORIGEN[m.origen]} onClick={() => abrir(m.id)}>{num(m.consumo)}</button>
                    : (puedeCrear && x.activo && !futuro(m.mes) ? <button className="text-slate-300 hover:text-esynapse-600" title="Registrar" onClick={() => nuevo({ suministro: x.id, mes: m.mes })}>+</button> : '')}</td>)}
                  <td className="text-right font-semibold">{num(x.total)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Clic en un valor para verlo o corregirlo; «+» registra el mes. En cursiva, valores estimados.</p>
        </div>
      )}
      {d && !sede && d.por_sede.length > 1 && (
        <div className="card-esynapse p-3">
          <p className="mb-2 text-sm font-semibold">Total {anio} por sede</p>
          <table className="tabla-sig text-xs"><thead><tr><th>Sede</th>{Object.entries(d.tipos).map(([k, t]) => <th key={k} className="text-right">{t.nombre} ({t.unidad})</th>)}</tr></thead>
            <tbody>{d.por_sede.map((s) => <tr key={s.id}><td>{s.sede}</td>{Object.keys(d.tipos).map((k) => <td key={k} className="text-right">{num(s[k])}</td>)}</tr>)}</tbody></table>
        </div>
      )}
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Consumo registrado' : 'Registrar consumo del mes'} onCerrar={() => setForm(null)} ancho="max-w-2xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="md:col-span-2"><label className={lbl}>Suministro</label><select className={inp} disabled={Boolean(form.id)} value={String(form.suministro || '')} onChange={(e) => setForm({ ...form, suministro: e.target.value ? Number(e.target.value) : '', origen: '' })}><option value="">—</option>{sedes.map((s) => <optgroup key={s.id} label={s.nombre}>{suministros.filter((x) => x.sede === s.id).map((x) => <option key={x.id} value={x.id}>{x.tipo_display} · {x.nivel_nombre || 'toda la sede'}{x.numero ? ` (${x.numero})` : ''}</option>)}</optgroup>)}{form.id && !sumi && <option value={form.suministro}>{form.suministro_nombre}</option>}</select></div>
              <div><label className={lbl}>Año</label><input type="number" className={inp} disabled={Boolean(form.id)} value={form.anio} onChange={(e) => setForm({ ...form, anio: Number(e.target.value) })} /></div>
              <div><label className={lbl}>Mes</label><select className={inp} disabled={Boolean(form.id)} value={form.mes} onChange={(e) => setForm({ ...form, mes: Number(e.target.value) })}>{MESES.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}</select></div>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="md:col-span-2"><label className={lbl}>Origen del dato</label><select className={inp} value={origen} onChange={(e) => setForm({ ...form, origen: e.target.value })}>{Object.entries(ORIGEN).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              {porLectura && <div><label className={lbl}>Fecha de la lectura</label><input type="date" className={inp} max={hoyLocal()} value={form.fecha_lectura || ''} onChange={(e) => setForm({ ...form, fecha_lectura: e.target.value })} /></div>}
              <div><label className={lbl}>Monto (S/, opcional)</label><input type="number" min="0" step="0.01" className={inp} value={form.monto ?? ''} onChange={(e) => setForm({ ...form, monto: e.target.value })} /></div>
            </div>
            {porLectura ? (
              <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <div className="grid gap-3 md:grid-cols-3">
                  <div><label className={lbl}>Lectura anterior</label>{anteriorAuto
                    ? <p className="py-2 font-mono">{num(previo.lectura_anterior)} <span className="font-sans text-[11px] text-slate-500">({previo.mes_anterior}{previo.fecha_anterior ? `, ${fecha(previo.fecha_anterior)}` : ''})</span></p>
                    : <input type="number" min="0" step="0.01" className={inp} placeholder={form.cambio_medidor ? 'Lectura inicial del medidor nuevo' : 'Primera lectura: la del mes anterior'} value={form.lectura_anterior ?? ''} onChange={(e) => setForm({ ...form, lectura_anterior: e.target.value })} />}</div>
                  <div><label className={lbl}>Lectura actual</label><input type="number" min="0" step="0.01" className={inp} value={form.lectura_actual ?? ''} onChange={(e) => setForm({ ...form, lectura_actual: e.target.value })} /></div>
                  <div><label className={lbl}>Consumo del mes</label><p className={`py-2 font-semibold ${calculado != null && calculado < 0 ? 'text-red-600' : ''}`}>{calculado == null ? '—' : `${num(calculado)} ${sumi?.unidad || previo?.unidad || ''}`}</p></div>
                </div>
                <label className="flex items-center gap-2 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={Boolean(form.cambio_medidor)} onChange={(e) => setForm({ ...form, cambio_medidor: e.target.checked })} /> Se cambió o reinició el medidor este mes</label>
                {form.cambio_medidor && <div><label className={lbl}>Motivo del cambio</label><input className={inp} value={form.motivo_cambio || ''} onChange={(e) => setForm({ ...form, motivo_cambio: e.target.value })} /></div>}
              </div>
            ) : (
              <div className="grid gap-3 md:grid-cols-3"><div><label className={lbl}>Consumo del mes ({sumi?.unidad || ''})</label><input type="number" min="0" step="0.01" className={inp} value={form.consumo ?? ''} onChange={(e) => setForm({ ...form, consumo: e.target.value })} /></div>
                {origen === 'estimado' && <p className="self-end text-[11px] text-amber-600 md:col-span-2">Indique en observaciones cómo se estimó (equipos y horas de uso, personas, etc.).</p>}</div>
            )}
            <div><label className={lbl}>{porLectura ? 'Foto del medidor' : 'Recibo o sustento'} {form.evidencia_url && <a className="ml-1 text-esynapse-500 underline" href={form.evidencia_url} target="_blank" rel="noreferrer">(actual)</a>}</label><input type="file" accept="image/*,application/pdf" className="text-xs" onChange={(e) => setForm({ ...form, evidencia: e.target.files[0] || null })} /></div>
            <div><label className={lbl}>Observaciones</label><input className={inp} value={form.observaciones || ''} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} /></div>
            {form.aviso && <p className="rounded bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">{form.aviso}</p>}
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2">{form.id && puedeEliminar && <button className="btn-secondary mr-auto text-red-600" onClick={quitar}>Anular</button>}<button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button>{(form.id ? puedeEditar : puedeCrear) && <button className="btn-primary" disabled={!form.suministro && !form.id} onClick={guardar}>Guardar</button>}</div>
          </div>
        )}
      </Modal>
    </div>
  )
}
