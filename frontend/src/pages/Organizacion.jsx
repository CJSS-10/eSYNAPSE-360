import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Briefcase, Building2, History, Network, Pencil, Plus, RotateCcw, Search, UserMinus, UserPlus, Users, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import { useCatalogoProcesos } from '../components/SelectorProceso.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { useConfig } from '../context/ConfigContext.jsx'
import { fecha } from '../lib/fecha.js'
import { sev } from '../lib/severidad.js'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import Pestanas from '../components/ui/Pestanas.jsx'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
const TIPO_AREA = {
  gerencia: ['Gerencia', 'bg-blue-500/15 text-blue-600 dark:text-blue-400'],
  area: ['Área', 'bg-slate-500/15 text-slate-600 dark:text-slate-300'],
  laboratorio: ['Laboratorio', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
}
const ESTADO = { activo: ['Activo', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'], cesado: ['Cesado', 'bg-slate-500/15 text-slate-500'] }
const PERFIL = [['educacion', 'Educación'], ['formacion', 'Formación'], ['experiencia', 'Experiencia'], ['habilidades', 'Habilidades'], ['responsabilidades', 'Funciones y responsabilidades']]
const Chip = ({ par }) => (par ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{par[0]}</span> : null)

function Aviso({ texto }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [texto])
  return <p ref={ref} className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p>
}
function Historial({ items }) {
  if (!items?.length) return null
  return (
    <details className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
      <summary className="flex cursor-pointer items-center gap-1 text-slate-500"><History className="h-3.5 w-3.5" /> Historial ({items.length})</summary>
      <div className="mt-1 space-y-0.5 text-slate-600 dark:text-slate-300">{items.slice().reverse().map((h, i) => <p key={i}>{(h.fecha || '').slice(0, 16).replace('T', ' ')} · {h.usuario} · <strong>{h.accion}</strong>{h.campos ? `: ${h.campos}` : ''}{h.de ? ` (${h.de} → ${h.a})` : ''}{h.motivo ? `: ${h.motivo}` : ''}{h.usuario_sistema ? ` · ${h.usuario_sistema}` : ''}</p>)}</div>
    </details>
  )
}

/** Ordena las áreas como árbol (padre antes que hijos) con su nivel de sangría. */
function enArbol(areas) {
  const hijos = {}
  areas.forEach((a) => { (hijos[a.padre || 0] = hijos[a.padre || 0] || []).push(a) })
  const ids = new Set(areas.map((a) => a.id))
  const out = []
  const visitar = (padre, nivel) => (hijos[padre] || []).forEach((a) => { out.push({ ...a, nivel }); visitar(a.id, nivel + 1) })
  visitar(0, 0)
  areas.filter((a) => a.padre && !ids.has(a.padre)).forEach((a) => { if (!out.find((x) => x.id === a.id)) { out.push({ ...a, nivel: 0 }); visitar(a.id, 1) } })
  return out
}

export default function Organizacion() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const procesos = useCatalogoProcesos()
  const [pestana, setPestana] = useState('trabajadores')
  const [areas, setAreas] = useState([])
  const [puestos, setPuestos] = useState([])
  const [error, setError] = useState('')
  const cargarBase = useCallback(async () => {
    const [a, p] = await Promise.all([api.org.areas('?todos=1'), api.org.puestos('?todos=1')])
    setAreas(a); setPuestos(p)
  }, [])
  useEffect(() => { cargarBase().catch((e) => setError(e.message)) }, [cargarBase])
  const permisos = { puedeCrear: tienePermiso('organizacion', 'crear'), puedeEditar: tienePermiso('organizacion', 'editar'), puedeEliminar: tienePermiso('organizacion', 'eliminar') }
  const { config } = useConfig()
  const verRiesgos = tienePermiso('sst', 'leer') && (config.modulos_habilitados || []).includes('sst')
  const comun = { areas, puestos, procesos: procesos.filter((p) => p.is_active && !p.padre), confirmar, setError, cargarBase, verRiesgos, ...permisos }

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <TituloModulo seccion="Administración" titulo="Organización y personal" descripcion="Áreas, puestos y trabajadores comunes a todo el sistema. Cada módulo los usa; aquí se mantienen." />
        <Pestanas opciones={[['trabajadores', 'Trabajadores', Users], ['puestos', 'Puestos', Briefcase], ['areas', 'Áreas', Building2]]} valor={pestana} onChange={setPestana} />
      </div>
      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      {pestana === 'areas' && <Areas {...comun} />}
      {pestana === 'puestos' && <Puestos {...comun} />}
      {pestana === 'trabajadores' && <Trabajadores {...comun} />}
    </div>
  )
}

/* ------------------------------------------------------------------ Áreas */
const AREA_VACIA = { nombre: '', tipo: 'area', padre: '', proceso: '', sede: '', piso: '', responsable: '', descripcion: '', orden: 0 }

function Areas({ areas, puestos, procesos, confirmar, setError, cargarBase, puedeCrear, puedeEditar, puedeEliminar }) {
  const [form, setForm] = useState(null)
  const [verInactivas, setVerInactivas] = useState(false)
  const [err, setErr] = useState('')
  const arbol = useMemo(() => enArbol(areas.filter((a) => verInactivas || a.is_active)), [areas, verInactivas])
  const guardar = async () => {
    setErr('')
    const datos = { ...form, padre: form.padre || null, proceso: form.proceso || null, responsable: form.responsable || null }
    try { if (form.id) await api.org.editarArea(form.id, datos); else await api.org.crearArea(datos); setForm(null); await cargarBase() } catch (e) { setErr(e.message) }
  }
  const desactivar = async (a) => {
    if (!await confirmar({ titulo: 'Desactivar el área', mensaje: `«${a.nombre}» deja de ofrecerse en el sistema; los registros que ya la usan la conservan.`, textoConfirmar: 'Desactivar', peligro: true })) return
    try { await api.org.desactivarArea(a.id); await cargarBase() } catch (e) { setError(e.message) }
  }
  const reactivar = async (a) => { try { await api.org.reactivar('areas', a.id); await cargarBase() } catch (e) { setError(e.message) } }
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-1 text-xs text-slate-500"><input type="checkbox" className="accent-esynapse-600" checked={verInactivas} onChange={(e) => setVerInactivas(e.target.checked)} /> Mostrar desactivadas</label>
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setForm({ ...AREA_VACIA }) }}><Plus className="h-4 w-4" /> Nueva área</button>}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Área</th><th className="px-2 text-center">Tipo</th><th className="px-2">Proceso principal</th><th className="px-2">Sede · piso</th><th className="px-2">Responsable</th><th className="px-2">Puestos</th><th className="px-2 text-right">Trabajadores</th><th /></tr></thead>
          <tbody>
            {arbol.map((a) => (
              <tr key={a.id} className={`border-b border-slate-100 dark:border-slate-800/60 ${a.is_active ? '' : 'opacity-50'}`}>
                <td className="px-2 py-1.5"><span style={{ paddingLeft: `${a.nivel * 1.25}rem` }} className={a.nivel ? '' : 'font-semibold'}>{a.nivel ? '↳ ' : ''}{a.nombre}</span></td>
                <td className="px-2 text-center"><Chip par={TIPO_AREA[a.tipo]} /></td><td className="px-2">{a.proceso_nombre || '—'}</td>
                <td className="px-2">{[a.sede, a.piso ? `piso ${a.piso}` : ''].filter(Boolean).join(' · ') || '—'}</td>
                <td className="px-2">{a.responsable_nombre || '—'}</td><td className="px-2">{a.n_puestos}</td><td className="px-2 text-right">{a.n_trabajadores}</td>
                <td className="whitespace-nowrap px-2">
                  {puedeEditar && a.is_active && <button className="p-1" title="Corregir" onClick={() => { setErr(''); setForm({ ...Object.fromEntries(Object.keys(AREA_VACIA).map((k) => [k, a[k] ?? AREA_VACIA[k]])), id: a.id, historial: a.historial }) }}><Pencil className="h-3.5 w-3.5" /></button>}
                  {puedeEliminar && a.is_active && <button className="p-1 text-red-500" title="Desactivar" onClick={() => desactivar(a)}><X className="h-3.5 w-3.5" /></button>}
                  {puedeEditar && !a.is_active && <button className="p-1" title="Reactivar" onClick={() => reactivar(a)}><RotateCcw className="h-3.5 w-3.5" /></button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Corregir el área' : 'Nueva área'} onCerrar={() => setForm(null)} ancho="max-w-2xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="md:col-span-2"><label className={lbl}>Nombre</label><input className={inp} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div>
              <div><label className={lbl}>Tipo</label><select className={inp} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{Object.entries(TIPO_AREA).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select></div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Depende de</label><select className={inp} value={String(form.padre || '')} onChange={(e) => setForm({ ...form, padre: e.target.value ? Number(e.target.value) : '' })}><option value="">— (nivel superior)</option>{enArbol(areas.filter((a) => a.is_active && a.id !== form.id)).map((a) => <option key={a.id} value={a.id}>{'· '.repeat(a.nivel)}{a.nombre}</option>)}</select></div>
              <div><label className={lbl}>Proceso principal</label><select className={inp} value={String(form.proceso || '')} onChange={(e) => setForm({ ...form, proceso: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{procesos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Sede</label><input className={inp} placeholder="Operativa / Administrativa" value={form.sede} onChange={(e) => setForm({ ...form, sede: e.target.value })} /></div>
              <div><label className={lbl}>Piso</label><input className={inp} value={form.piso} onChange={(e) => setForm({ ...form, piso: e.target.value })} /></div>
              <div><label className={lbl}>Puesto responsable</label><select className={inp} value={String(form.responsable || '')} onChange={(e) => setForm({ ...form, responsable: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{puestos.filter((p) => p.is_active && p.tipo === 'propio').map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></div>
            </div>
            <div><label className={lbl}>Descripción</label><input className={inp} value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></div>
            <Historial items={form.historial} />
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" disabled={!form.nombre.trim()} onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ----------------------------------------------------------------- Puestos */
const PUESTO_VACIO = { nombre: '', sigla: '', area: '', reporta_a: '', tipo: 'propio', proceso: '', educacion: '', formacion: '', experiencia: '', habilidades: '', responsabilidades: '' }

function Puestos({ areas, puestos, procesos, confirmar, setError, cargarBase, puedeCrear, puedeEditar, puedeEliminar }) {
  const [form, setForm] = useState(null)
  const [area, setArea] = useState('')
  const [verInactivos, setVerInactivos] = useState(false)
  const [err, setErr] = useState('')
  const lista = puestos.filter((p) => (verInactivos || p.is_active) && (!area || String(p.area) === area))
  const guardar = async () => {
    setErr('')
    const datos = { ...form, area: form.area || null, reporta_a: form.reporta_a || null, proceso: form.proceso || null }
    delete datos.historial; delete datos.version_perfil
    try { if (form.id) await api.org.editarPuesto(form.id, datos); else await api.org.crearPuesto(datos); setForm(null); await cargarBase() } catch (e) { setErr(e.message) }
  }
  const desactivar = async (p) => {
    if (!await confirmar({ titulo: 'Desactivar el puesto', mensaje: `«${p.nombre}» deja de ofrecerse; los registros que ya lo usan lo conservan.`, textoConfirmar: 'Desactivar', peligro: true })) return
    try { await api.org.desactivarPuesto(p.id); await cargarBase() } catch (e) { setError(e.message) }
  }
  const reactivar = async (p) => { try { await api.org.reactivar('puestos', p.id); await cargarBase() } catch (e) { setError(e.message) } }
  const abrir = (p) => { setErr(''); setForm({ ...Object.fromEntries(Object.keys(PUESTO_VACIO).map((k) => [k, p[k] ?? PUESTO_VACIO[k]])), id: p.id, historial: p.historial, version_perfil: p.version_perfil }) }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select className="input-esynapse w-64" value={area} onChange={(e) => setArea(e.target.value)}><option value="">Todas las áreas</option>{enArbol(areas.filter((a) => a.is_active)).map((a) => <option key={a.id} value={a.id}>{'· '.repeat(a.nivel)}{a.nombre}</option>)}</select>
        <label className="flex items-center gap-1 text-xs text-slate-500"><input type="checkbox" className="accent-esynapse-600" checked={verInactivos} onChange={(e) => setVerInactivos(e.target.checked)} /> Mostrar desactivados</label>
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setForm({ ...PUESTO_VACIO, area: area ? Number(area) : '' }) }}><Plus className="h-4 w-4" /> Nuevo puesto</button>}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Puesto</th><th className="px-2">Sigla</th><th className="px-2">Área</th><th className="px-2">Reporta a</th><th className="px-2 text-center">Tipo</th><th className="px-2 text-center">Perfil</th><th className="px-2 text-right">Trabajadores</th><th /></tr></thead>
          <tbody>
            {lista.map((p) => (
              <tr key={p.id} onClick={() => abrir(p)} className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${p.is_active ? '' : 'opacity-50'}`}>
                <td className="px-2 py-1.5 font-semibold">{p.nombre}</td><td className="px-2 font-mono">{p.sigla || '—'}</td><td className="px-2">{p.area_nombre || '—'}</td>
                <td className="px-2">{p.reporta_a_nombre || '—'}</td><td className="px-2 text-center">{p.tipo === 'tercero' ? 'Tercero' : 'Propio'}</td>
                <td className="px-2 text-center">{p.tiene_perfil ? `Versión ${p.version_perfil}` : <span className="text-amber-500">Sin perfil</span>}</td><td className="px-2 text-right">{p.n_trabajadores}</td>
                <td className="whitespace-nowrap px-2" onClick={(e) => e.stopPropagation()}>
                  {puedeEliminar && p.is_active && <button className="p-1 text-red-500" title="Desactivar" onClick={() => desactivar(p)}><X className="h-3.5 w-3.5" /></button>}
                  {puedeEditar && !p.is_active && <button className="p-1" title="Reactivar" onClick={() => reactivar(p)}><RotateCcw className="h-3.5 w-3.5" /></button>}
                </td>
              </tr>
            ))}
            {lista.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin puestos</td></tr>}
          </tbody>
        </table>
        <p className="px-2 py-1 text-[11px] text-slate-400">{lista.length} puesto(s)</p>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? `Puesto: ${form.nombre}` : 'Nuevo puesto'} onCerrar={() => setForm(null)} ancho="max-w-3xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="md:col-span-2"><label className={lbl}>Puesto</label><input className={inp} disabled={!puedeEditar} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div>
              <div><label className={lbl} title="Tal como se imprime en las firmas de los formatos">Sigla (firmas)</label><input className={inp} disabled={!puedeEditar} maxLength={12} placeholder="GSIG, ASIG…" value={form.sigla} onChange={(e) => setForm({ ...form, sigla: e.target.value.toUpperCase() })} /></div>
              <div><label className={lbl}>Tipo</label><select className={inp} disabled={!puedeEditar} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}><option value="propio">Personal de la empresa</option><option value="tercero">Tercero / contratista</option></select></div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Área</label><select className={inp} disabled={!puedeEditar} value={String(form.area || '')} onChange={(e) => setForm({ ...form, area: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{enArbol(areas.filter((a) => a.is_active)).map((a) => <option key={a.id} value={a.id}>{'· '.repeat(a.nivel)}{a.nombre}</option>)}</select></div>
              <div><label className={lbl}>Reporta a</label><select className={inp} disabled={!puedeEditar} value={String(form.reporta_a || '')} onChange={(e) => setForm({ ...form, reporta_a: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{puestos.filter((p) => p.is_active && p.id !== form.id && p.tipo === 'propio').map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></div>
              <div><label className={lbl}>Proceso</label><select className={inp} disabled={!puedeEditar} value={String(form.proceso || '')} onChange={(e) => setForm({ ...form, proceso: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{procesos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
              <p className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Perfil del puesto {form.version_perfil ? `(versión ${form.version_perfil})` : ''} — lo consulta Competencia técnica</p>
              <div className="grid gap-3 md:grid-cols-2">{PERFIL.map(([k, n]) => <div key={k} className={k === 'responsabilidades' ? 'md:col-span-2' : ''}><label className={lbl}>{n}</label><CampoAmpliable multilinea disabled={!puedeEditar} value={form[k]} onChange={(v) => setForm({ ...form, [k]: v })} /></div>)}</div>
            </div>
            <Historial items={form.historial} />
            {err && <Aviso texto={err} />}
            {puedeEditar && <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" disabled={!form.nombre.trim()} onClick={guardar}>Guardar</button></div>}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ------------------------------------------------------------ Trabajadores */
const TRAB_VACIO = { nombres: '', apellidos: '', documento: '', puesto: '', area: '', empresa: '', correo: '', telefono: '', fecha_ingreso: '' }

const NIVEL_IPERC = {
  T: sev(1, 'Trivial'), TO: sev(2, 'Tolerable'), M: sev(3, 'Moderado'), IM: sev(4, 'Importante'), IT: sev(5, 'Intolerable'),
}

/** Riesgos de la matriz IPERC a los que está expuesto el trabajador (según su puesto y su área). */
function RiesgosTrabajador({ id }) {
  const [r, setR] = useState(null)
  const [ver, setVer] = useState(false)
  useEffect(() => { api.sst.porTrabajador(id).then(setR).catch(() => setR({ error: true })) }, [id])
  if (!r) return <p className="text-[11px] text-slate-400">Cargando riesgos del puesto…</p>
  if (r.error) return null
  const cuenta = {}
  r.filas.forEach((f) => { const k = f.r_clasificacion || f.clasificacion || 'sin'; cuenta[k] = (cuenta[k] || 0) + 1 })
  const orden = { IT: 0, IM: 1, M: 2, TO: 3, T: 4, sin: 5 }
  const filas = [...r.filas].sort((a, b) => orden[a.r_clasificacion || a.clasificacion || 'sin'] - orden[b.r_clasificacion || b.clasificacion || 'sin'])
  return (
    <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded bg-red-500/15 px-1.5 py-0.5 text-[11px] font-semibold text-red-600 dark:text-red-400">ISO 45001</span>
        <strong>Riesgos a los que está expuesto (matriz IPERC):</strong> {r.filas.length} fila(s)
        {Object.entries(NIVEL_IPERC).map(([k, par]) => cuenta[k] ? <Chip key={k} par={[`${par[0]} ${cuenta[k]}`, par[1]]} /> : null)}
        {r.filas.length > 0 && <button className="ml-auto text-[11px] text-esynapse-500 underline" onClick={() => setVer(!ver)}>{ver ? 'Ocultar' : 'Ver detalle'}</button>}
      </div>
      <p className="mt-1 text-[11px] text-slate-500">Nivel residual (con controles) cuando está evaluado. Incluye las filas de su puesto en su área y las que aplican a todos los puestos.</p>
      {ver && (
        <table className="tabla-ficha mt-2 w-full text-[11px]">
          <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="py-1">Código</th><th>Peligro</th><th>Riesgo</th><th className="text-center">Nivel</th><th>EPP</th></tr></thead>
          <tbody>{filas.map((f) => { const n = f.r_clasificacion || f.clasificacion; return <tr key={f.id} className="border-b border-slate-100 dark:border-slate-800/60"><td className="py-1 font-mono">{f.codigo}</td><td>{f.peligro}</td><td>{f.riesgo}</td><td className="text-center">{n ? <Chip par={NIVEL_IPERC[n]} /> : '—'}</td><td className="max-w-[12rem] truncate" title={f.control_epp}>{f.control_epp || '—'}</td></tr> })}</tbody>
        </table>
      )}
    </div>
  )
}

function Trabajadores({ areas, puestos, confirmar, setError, cargarBase, puedeCrear, puedeEditar, verRiesgos }) {
  const [items, setItems] = useState([])
  const [buscar, setBuscar] = useState('')
  const [area, setArea] = useState('')
  const [cesados, setCesados] = useState(false)
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const p = new URLSearchParams(); if (buscar) p.set('buscar', buscar); if (area) p.set('area', area); if (cesados) p.set('cesados', '1')
    setItems(await ultima(api.org.trabajadores(`?${p}`)))
  }, [buscar, area, cesados])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  const puestoSel = form ? puestos.find((p) => p.id === Number(form.puesto)) : null
  const guardar = async () => {
    setErr('')
    const datos = { ...form, area: form.area || null, fecha_ingreso: form.fecha_ingreso || null }
    delete datos.historial; delete datos.estado; delete datos.usuario_username
    try { if (form.id) await api.org.editarTrabajador(form.id, datos); else await api.org.crearTrabajador(datos); setForm(null); await cargar(); await cargarBase() } catch (e) { setErr(e.message) }
  }
  const cesar = async () => {
    const f = await confirmar({ titulo: 'Registrar el cese', mensaje: `${form.nombres} ${form.apellidos} deja de figurar como activo.${form.usuario_username ? ` Su usuario del sistema (${form.usuario_username}) se desactiva.` : ''}`, textoConfirmar: 'Siguiente', entrada: { etiqueta: 'Fecha de cese (AAAA-MM-DD)', obligatorio: true, valorInicial: new Date().toISOString().slice(0, 10) } })
    if (f === null) return
    const m = await confirmar({ titulo: 'Motivo del cese', mensaje: 'Queda en el historial del trabajador.', textoConfirmar: 'Registrar', peligro: true, entrada: { etiqueta: 'Motivo (renuncia, término de contrato…)', obligatorio: true } })
    if (m === null) return
    setErr('')
    try { await api.org.accionTrabajador(form.id, 'cesar', { fecha: f, motivo: m }); setForm(null); await cargar(); await cargarBase() } catch (e) { setErr(e.message) }
  }
  const reingresar = async () => {
    const f = await confirmar({ titulo: 'Reingreso', mensaje: 'El trabajador vuelve a figurar como activo. Su usuario del sistema, si lo tenía, se reactiva desde Usuarios.', textoConfirmar: 'Registrar', entrada: { etiqueta: 'Fecha de reingreso (AAAA-MM-DD)', obligatorio: true, valorInicial: new Date().toISOString().slice(0, 10) } })
    if (f === null) return
    try { await api.org.accionTrabajador(form.id, 'reingresar', { fecha: f }); setForm(null); await cargar() } catch (e) { setErr(e.message) }
  }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-64 pl-9" placeholder="Nombre, documento o puesto…" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <select className="input-esynapse w-64" value={area} onChange={(e) => setArea(e.target.value)}><option value="">Todas las áreas</option>{enArbol(areas.filter((a) => a.is_active)).map((a) => <option key={a.id} value={a.id}>{'· '.repeat(a.nivel)}{a.nombre}</option>)}</select>
        <label className="flex items-center gap-1 text-xs text-slate-500"><input type="checkbox" className="accent-esynapse-600" checked={cesados} onChange={(e) => setCesados(e.target.checked)} /> Incluir cesados</label>
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setForm({ ...TRAB_VACIO }) }}><UserPlus className="h-4 w-4" /> Nuevo trabajador</button>}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Trabajador</th><th className="px-2">Puesto</th><th className="px-2">Área</th><th className="px-2 text-right">Ingreso</th><th className="px-2">Usuario del sistema</th><th className="px-2 text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id} onClick={() => { setErr(''); setForm({ ...Object.fromEntries(Object.keys(TRAB_VACIO).map((k) => [k, t[k] ?? TRAB_VACIO[k]])), id: t.id, estado: t.estado, historial: t.historial, usuario_username: t.usuario_username }) }}
                className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${t.estado === 'cesado' ? 'opacity-60' : ''}`}>
                <td className="px-2 py-1.5 font-semibold">{t.nombre_completo}{t.empresa ? <span className="ml-1 font-normal text-slate-400">({t.empresa})</span> : null}</td>
                <td className="px-2">{t.puesto_nombre}{t.puesto_sigla ? <span className="ml-1 font-mono text-slate-400">{t.puesto_sigla}</span> : null}</td>
                <td className="px-2">{t.area_nombre || '—'}</td><td className="whitespace-nowrap px-2 text-right">{t.fecha_ingreso ? fecha(t.fecha_ingreso) : '—'}</td>
                <td className="px-2">{t.usuario_username || '—'}</td><td className="px-2 text-center"><Chip par={ESTADO[t.estado]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={6} className="py-8 text-slate-400">Sin trabajadores registrados</td></tr>}
          </tbody>
        </table>
        <p className="px-2 py-1 text-[11px] text-slate-400">{items.length} trabajador(es)</p>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? `${form.nombres} ${form.apellidos}` : 'Nuevo trabajador'} onCerrar={() => setForm(null)} ancho="max-w-2xl">
        {form && (
          <div className="space-y-3 text-sm">
            {form.estado === 'cesado' && <p className="rounded bg-slate-500/10 px-3 py-2 text-xs text-slate-500">Trabajador cesado: queda como registro.</p>}
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Nombres</label><input className={inp} disabled={!puedeEditar} value={form.nombres} onChange={(e) => setForm({ ...form, nombres: e.target.value })} /></div>
              <div><label className={lbl}>Apellidos</label><input className={inp} disabled={!puedeEditar} value={form.apellidos} onChange={(e) => setForm({ ...form, apellidos: e.target.value })} /></div>
              <div><label className={lbl}>Documento de identidad</label><input className={inp} disabled={!puedeEditar} value={form.documento || ''} onChange={(e) => setForm({ ...form, documento: e.target.value })} /></div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Puesto</label><select className={inp} disabled={!puedeEditar} value={String(form.puesto || '')} onChange={(e) => setForm({ ...form, puesto: e.target.value ? Number(e.target.value) : '' })}><option value="">— Elegir —</option>{[['propio', 'Personal de la empresa'], ['tercero', 'Terceros']].map(([k, n]) => <optgroup key={k} label={n}>{puestos.filter((p) => p.is_active && p.tipo === k).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</optgroup>)}</select></div>
              <div><label className={lbl}>Área {puestoSel?.area_nombre ? `(vacía = la del puesto: ${puestoSel.area_nombre})` : ''}</label><select className={inp} disabled={!puedeEditar} value={String(form.area || '')} onChange={(e) => setForm({ ...form, area: e.target.value ? Number(e.target.value) : '' })}><option value="">— La del puesto —</option>{enArbol(areas.filter((a) => a.is_active)).map((a) => <option key={a.id} value={a.id}>{'· '.repeat(a.nivel)}{a.nombre}</option>)}</select></div>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              {puestoSel?.tipo === 'tercero' && <div><label className={lbl}>Empresa</label><input className={inp} disabled={!puedeEditar} value={form.empresa} onChange={(e) => setForm({ ...form, empresa: e.target.value })} /></div>}
              <div><label className={lbl}>Fecha de ingreso</label><input type="date" className={inp} disabled={!puedeEditar} value={form.fecha_ingreso || ''} onChange={(e) => setForm({ ...form, fecha_ingreso: e.target.value })} /></div>
              <div><label className={lbl}>Correo</label><input className={inp} disabled={!puedeEditar} value={form.correo} onChange={(e) => setForm({ ...form, correo: e.target.value })} /></div>
              <div><label className={lbl}>Teléfono</label><input className={inp} disabled={!puedeEditar} value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} /></div>
            </div>
            {form.id && verRiesgos && <RiesgosTrabajador id={form.id} />}
            <p className="text-[11px] text-slate-500">Usuario del sistema: {form.usuario_username || 'ninguno'} — se vincula desde Usuarios. El usuario toma el cargo, la sigla y el área de este puesto para sus firmas.</p>
            <Historial items={form.historial} />
            {err && <Aviso texto={err} />}
            {puedeEditar && (
              <div className="flex justify-end gap-2">
                {form.id && form.estado === 'activo' && <button className="btn-secondary mr-auto text-red-500" onClick={cesar}><UserMinus className="h-4 w-4" /> Registrar cese</button>}
                {form.id && form.estado === 'cesado' && <button className="btn-secondary mr-auto" onClick={reingresar}><RotateCcw className="h-4 w-4" /> Reingreso</button>}
                <button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button>
                <button className="btn-primary" disabled={!form.nombres.trim() || !form.apellidos.trim() || !form.puesto} onClick={guardar}>Guardar</button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
