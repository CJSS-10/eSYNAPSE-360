import { useCallback, useEffect, useRef, useState } from 'react'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import { BarChart3, ClipboardCheck, FileText, Lock, Pencil, Plus, Scale, Search, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import CampoSugerencias from '../components/CampoSugerencias.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import { useCatalogoProcesos } from '../components/SelectorProceso.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora, hoy as hoyLocal } from '../lib/fecha.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import Pestanas from '../components/ui/Pestanas.jsx'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
const hoy = () => hoyLocal()

// Etiquetas de norma (regla 9): SST rojo · Medio Ambiente verde · acreditación ámbar; los demás, neutros.
const COLOR_AMBITO = {
  sst: 'bg-red-500/15 text-red-600 dark:text-red-400',
  ma: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  acreditacion: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  sociolaboral: 'bg-slate-500/15 text-slate-600 dark:text-slate-300',
  otros: 'bg-slate-500/15 text-slate-600 dark:text-slate-300',
}
const RESULTADO = {
  pendiente: ['Pendiente', 'bg-slate-500/15 text-slate-500'],
  cumple: ['Cumple', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  no_cumple: ['No cumple', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  no_aplica: ['No aplica', 'bg-slate-500/10 text-slate-400'],
}
const CALIF = { bueno: ['Bueno', 'text-emerald-600 dark:text-emerald-400'], regular: ['Regular', 'text-amber-500'], malo: ['Malo', 'text-red-600'] }

const Chip = ({ par }) => (par ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{par[0]}</span> : null)
function Seccion({ titulo, children, extra, tono }) {
  return (
    <div className={`rounded-lg border p-3 text-xs ${tono === 'azul' ? 'border-esynapse-600/30 bg-esynapse-600/5' : 'border-slate-200 dark:border-slate-800'}`}>
      <div className="mb-1.5 flex items-center justify-between gap-2"><p className="text-xs font-semibold text-slate-500 dark:text-slate-400">{titulo}</p>{extra}</div>
      <div className="space-y-2 text-slate-600 dark:text-slate-300">{children}</div>
    </div>
  )
}
const Dato = ({ etiqueta, valor }) => <p><strong className="text-slate-700 dark:text-slate-200">{etiqueta}:</strong> <span className="whitespace-pre-wrap">{valor || '—'}</span></p>

export default function Legal() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const procesos = useCatalogoProcesos()
  const [pestana, setPestana] = useState('requisitos')
  const [ambito, setAmbito] = useState('sst')
  const [cat, setCat] = useState(null)
  const [error, setError] = useState('')
  const errorRef = useRef(null)
  useEffect(() => { if (error && errorRef.current) errorRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [error])
  const cargarCat = useCallback(() => api.legal.catalogos().then(setCat).catch(() => {}), [])
  useEffect(() => { cargarCat() }, [cargarCat])

  const abrirPdf = async (promesa) => {
    setError('')
    try { const url = URL.createObjectURL(await promesa); window.open(url, '_blank'); setTimeout(() => URL.revokeObjectURL(url), 60000) } catch (e) { setError(e.message) }
  }
  const comun = { ambito, cat, procesos, confirmar, setError, abrirPdf, cargarCat, puedeCrear: tienePermiso('legal', 'crear'), puedeEditar: tienePermiso('legal', 'editar'), puedeAprobar: tienePermiso('legal', 'aprobar'), puedeEliminar: tienePermiso('legal', 'eliminar'), puedeCambios: tienePermiso('cambios', 'crear') }

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <TituloModulo seccion="Estratégico" titulo="Requisitos legales y otros requisitos" descripcion="Normas aplicables, sus obligaciones y la evaluación periódica de su cumplimiento." />
        <Pestanas opciones={[['requisitos', 'Lista de requisitos', FileText], ['obligaciones', 'Obligaciones', Search], ['evaluaciones', 'Evaluaciones', ClipboardCheck], ['indicadores', 'Indicadores', BarChart3]]} valor={pestana} onChange={setPestana} />
      </div>
      {pestana !== 'indicadores' && (
        <div className="flex flex-wrap gap-1.5">
          {(cat?.ambitos || []).map(([k, n]) => (
            <button key={k} onClick={() => setAmbito(k)} className={`rounded-full px-3 py-1 text-xs font-semibold ${ambito === k ? `${COLOR_AMBITO[k]} ring-2 ring-current` : 'bg-slate-100 text-slate-500 dark:bg-slate-800'}`}>{n}</button>
          ))}
        </div>
      )}
      {error && <p ref={errorRef} className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      {pestana === 'requisitos' && <Requisitos {...comun} />}
      {pestana === 'obligaciones' && <Obligaciones {...comun} />}
      {pestana === 'evaluaciones' && <Evaluaciones {...comun} />}
      {pestana === 'indicadores' && <Indicadores irA={(amb) => { setAmbito(amb); setPestana('evaluaciones') }} />}
    </div>
  )
}

/* -------------------------------------------------------------- Requisitos */
const REQ_VACIO = { tema: '', tipo: '', codigo: '', nombre: '', fecha_aprobacion: '', observaciones: '', aplicabilidad: '', procesos: [] }

function Requisitos({ ambito, cat, procesos, confirmar, setError, abrirPdf, cargarCat, puedeCrear, puedeEditar, puedeEliminar, puedeCambios }) {
  const [items, setItems] = useState([])
  const [buscar, setBuscar] = useState('')
  const [tema, setTema] = useState('')
  const [estado, setEstado] = useState('')
  const [d, setD] = useState(null)
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const params = useCallback(() => { const p = new URLSearchParams({ ambito }); if (buscar) p.set('buscar', buscar); if (tema) p.set('tema', tema); if (estado) p.set('estado', estado); return `?${p}` }, [ambito, buscar, tema, estado])
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => setItems(await ultima(api.legal.requisitos(params()))), [params])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  useEffect(() => { setTema('') }, [ambito])
  const temas = (cat?.temas || {})[ambito] || []

  const abrir = async (id) => { setErr(''); setForm(null); setD(await api.legal.requisito(id)) }
  const guardar = async () => {
    setErr('')
    try {
      const datos = { ...form, ambito }
      const r = form.id ? await api.legal.editarRequisito(form.id, datos) : await api.legal.crearRequisito(datos)
      setForm(null); await cargar(); await cargarCat(); setD(await api.legal.requisito(r.id))
    } catch (e) { setErr(e.message) }
  }
  const accion = async (fn) => { setErr(''); try { const r = await fn(); await cargar(); if (r?.id) setD(r); else setD(await api.legal.requisito(d.id)) } catch (e) { setErr(e.message) } }
  const pedir = async (titulo, mensaje, etiqueta) => confirmar({ titulo, mensaje, textoConfirmar: 'Registrar', entrada: { etiqueta, obligatorio: true, multilinea: true } })
  const modificatoria = async () => { const t = await pedir('Cambio normativo', 'Se agrega a la revisión de la norma con la fecha de hoy y queda en el historial.', 'Norma modificatoria (tipo, número y qué cambia)'); if (t !== null) accion(() => api.legal.accionRequisito(d.id, 'registrar_modificacion', { descripcion: t, fecha: hoy() })) }
  const derogar = async () => { const t = await pedir('Derogar la norma', 'La norma queda como registro y sus obligaciones salen de las próximas evaluaciones.', 'Norma que la deroga o motivo'); if (t !== null) accion(() => api.legal.accionRequisito(d.id, 'derogar', { motivo: t, fecha: hoy() })) }
  const comunicar = async () => {
    const dest = await confirmar({ titulo: 'Comunicar el requisito', mensaje: 'Medio: correo formal. Indique a quién se comunicó.', textoConfirmar: 'Siguiente', entrada: { etiqueta: 'Destinatarios (áreas o personas)', obligatorio: true } })
    if (dest === null) return
    const res = await pedir('Comunicar el requisito', 'Qué se comunicó: obligaciones, impactos y acciones requeridas.', 'Resumen')
    if (res !== null) accion(() => api.legal.accionRequisito(d.id, 'comunicar', { medio: 'correo', destinatarios: dest, resumen: res, fecha: hoy() }))
  }
  const solicitarCambio = async () => {
    if (!await confirmar({ titulo: 'Solicitud de cambio', mensaje: 'Se registra una solicitud de cambio (origen externo: requisitos legales) para adecuarse a esta norma. La completas en Cambios.', textoConfirmar: 'Registrar' })) return
    setErr('')
    try { const r = await api.legal.accionRequisito(d.id, 'solicitar_cambio'); setD(await api.legal.requisito(d.id)); setErr(''); await confirmar({ titulo: 'Solicitud registrada', mensaje: `Se registró ${r.cambio_codigo} en Cambios.`, textoConfirmar: 'Entendido' }) } catch (e) { setErr(e.message) }
  }
  const anular = async () => {
    if (!await confirmar({ titulo: 'Anular la norma', mensaje: 'Solo para una norma registrada por error y sin obligaciones. Si dejó de regir, derógala.', textoConfirmar: 'Anular', peligro: true })) return
    setErr('')
    try { await api.legal.anularRequisito(d.id); setD(null); await cargar(); await cargarCat() } catch (e) { setErr(e.message) }
  }
  const vigente = d?.estado === 'vigente'

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-64 pl-9" placeholder="Código, nombre o modificatoria…" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <select className="input-esynapse w-60" value={tema} onChange={(e) => setTema(e.target.value)}><option value="">Todos los temas</option>{temas.map((t) => <option key={t} value={t}>{t}</option>)}</select>
        <select className="input-esynapse w-36" value={estado} onChange={(e) => setEstado(e.target.value)}><option value="">Todo estado</option><option value="vigente">Vigentes</option><option value="derogada">Derogadas</option></select>
        <span className="ml-auto flex gap-2">
          <button className="btn-secondary" onClick={() => abrirPdf(api.legal.listaPdf(ambito))}><FileText className="h-4 w-4" /> Imprimir lista</button>
          {puedeCrear && <button className="btn-primary" onClick={() => { setErr(''); setD(null); setForm({ ...REQ_VACIO }) }}><Plus className="h-4 w-4" /> Nueva norma</button>}
        </span>
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Ítem</th><th className="px-2">Tema</th><th className="px-2 text-center">Tipo</th><th className="px-2">Código</th><th className="px-2">Nombre del documento</th><th className="px-2 text-right">Fecha de aprobación</th><th className="px-2 text-right">Obligaciones</th><th className="px-2 text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.id} onClick={() => abrir(r.id)} className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${r.estado === 'derogada' ? 'opacity-60' : ''}`}>
                <td className="px-2 py-2">{r.orden}</td><td className="px-2">{r.tema || '—'}</td><td className="px-2 text-center">{r.tipo}</td><td className="whitespace-nowrap px-2 font-mono">{r.codigo || '—'}</td>
                <td className="max-w-sm truncate px-2" title={r.nombre}>{r.nombre}</td><td className="whitespace-nowrap px-2 text-right">{r.fecha_aprobacion || '—'}</td>
                <td className="px-2 text-right">{r.n_obligaciones || '—'}</td>
                <td className="px-2 text-center"><Chip par={r.estado === 'vigente' ? ['Vigente', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'] : ['Derogada', 'bg-slate-500/15 text-slate-500']} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin normas en este ámbito</td></tr>}
          </tbody>
        </table>
        <p className="px-2 py-1 text-[11px] text-slate-400">{items.length} norma(s)</p>
      </div>

      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Corregir la norma' : 'Nueva norma'} onCerrar={() => setForm(null)} ancho="max-w-3xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Tema</label><CampoSugerencias value={form.tema} opciones={temas} onChange={(v) => setForm({ ...form, tema: v })} /></div>
              <div><label className={lbl}>Tipo</label><input className={inp} placeholder="Ley, Decreto Supremo, Directriz…" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} /></div>
              <div><label className={lbl}>Código / número</label><input className={inp} value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} /></div>
            </div>
            <div><label className={lbl}>Nombre del documento</label><CampoAmpliable multilinea value={form.nombre} onChange={(v) => setForm({ ...form, nombre: v })} /></div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Fecha de aprobación</label><input className={inp} placeholder="AAAA-MM-DD" value={form.fecha_aprobacion} onChange={(e) => setForm({ ...form, fecha_aprobacion: e.target.value })} /></div>
              <div className="md:col-span-2"><label className={lbl}>Observaciones (General, Referencial, Aplicable…)</label><input className={inp} value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} /></div>
            </div>
            <div><label className={lbl}>Aplicabilidad y consecuencias del incumplimiento</label><CampoAmpliable multilinea value={form.aplicabilidad} onChange={(v) => setForm({ ...form, aplicabilidad: v })} /></div>
            <div><label className={lbl}>Procesos involucrados</label>
              <div className="grid max-h-32 gap-1 overflow-y-auto rounded border border-slate-200 p-2 text-xs md:grid-cols-3 dark:border-slate-700">
                {procesos.filter((p) => p.is_active).map((p) => <label key={p.id} className="flex items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" checked={form.procesos.includes(p.id)} onChange={() => setForm({ ...form, procesos: form.procesos.includes(p.id) ? form.procesos.filter((x) => x !== p.id) : [...form.procesos, p.id] })} />{p.padre ? `↳ ${p.nombre}` : p.nombre}</label>)}
              </div></div>
            {err && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{err}</p>}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" disabled={!form.nombre.trim()} onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>

      <Modal abierto={Boolean(d) && !form} titulo={d ? `${d.denominacion || d.tipo} — ${d.nombre.slice(0, 70)}` : ''} onCerrar={() => setD(null)} panel ancho="max-w-5xl">
        {d && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded px-2 py-0.5 text-[11px] font-semibold ${COLOR_AMBITO[d.ambito]}`}>{d.ambito_display}</span>
              <Chip par={vigente ? ['Vigente', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'] : ['Derogada', 'bg-slate-500/15 text-slate-500']} />
              {!vigente && <span className="flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Queda como registro</span>}
              {vigente && puedeEditar && <button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => setForm({ id: d.id, ...Object.fromEntries(Object.keys(REQ_VACIO).map((k) => [k, d[k] ?? REQ_VACIO[k]])) })}><Pencil className="h-3.5 w-3.5" /> Corregir</button>}
            </div>
            {err && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{err}</p>}
            <Seccion titulo="Norma">
              <div className="grid gap-x-4 md:grid-cols-4"><Dato etiqueta="Ítem" valor={d.orden} /><Dato etiqueta="Tema" valor={d.tema} /><Dato etiqueta="Tipo" valor={d.tipo} /><Dato etiqueta="Código" valor={d.codigo} /></div>
              <Dato etiqueta="Nombre" valor={d.nombre} />
              <div className="grid gap-x-4 md:grid-cols-3"><Dato etiqueta="Fecha de aprobación" valor={d.fecha_aprobacion} /><Dato etiqueta="Observaciones" valor={d.observaciones} />{d.fecha_derogacion && <Dato etiqueta="Derogada el" valor={fecha(d.fecha_derogacion)} />}</div>
              <Dato etiqueta="Revisión / modificatorias" valor={d.modificatorias} />
              <Dato etiqueta="Aplicabilidad y consecuencias" valor={d.aplicabilidad} />
              <Dato etiqueta="Procesos involucrados" valor={d.procesos_nombres.join(', ')} />
            </Seccion>
            <Seccion titulo={`Obligaciones (${d.obligaciones.length})`}>
              {d.obligaciones.length === 0 && <p className="text-slate-400">Sin artículos a cumplir registrados: agréguelos en la pestaña Obligaciones.</p>}
              {d.obligaciones.map((o) => <p key={o.id} className={o.estado !== 'vigente' ? 'opacity-50' : ''}><strong>{o.articulo || '—'}</strong> · {o.extracto.slice(0, 180)}{o.extracto.length > 180 ? '…' : ''} {o.ultimo_resultado && <Chip par={RESULTADO[o.ultimo_resultado.resultado]} />}</p>)}
            </Seccion>
            <Seccion titulo="Comunicación">
              {d.comunicaciones.length === 0 && <p className="text-slate-400">Sin comunicaciones registradas.</p>}
              {d.comunicaciones.map((c) => <p key={c.id}>{fecha(c.fecha)} · {c.medio_display} · {c.destinatarios}: {c.resumen}</p>)}
            </Seccion>
            {d.historial.length > 0 && <Seccion titulo="Historial">{d.historial.slice().reverse().map((h, i) => <p key={i}>{fecha(h.fecha)} · {h.usuario} · <strong>{h.accion}</strong>{h.descripcion ? `: ${h.descripcion}` : ''}{h.motivo ? `: ${h.motivo}` : ''}{h.cambio ? ` (${h.cambio})` : ''}</p>)}</Seccion>}
            {vigente && puedeEditar && <BarraEtapa titulo="Norma vigente" nota="Registre los cambios normativos, comuníquela a las áreas o abra una solicitud de cambio para adecuarse." botones={[
              ...(puedeEliminar && d.obligaciones.length === 0 ? [{ texto: 'Anular', accion: anular, secundario: true }] : []),
              { texto: 'Derogar', accion: derogar, secundario: true },
              { texto: 'Comunicar', accion: comunicar, secundario: true },
              ...(puedeCambios ? [{ texto: 'Solicitud de cambio', accion: solicitarCambio, secundario: true }] : []),
              { texto: 'Registrar modificatoria', accion: modificatoria }]} />}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ------------------------------------------------------------ Obligaciones */
const OBL_VACIA = { tema: '', requisito: '', documento_legal: '', articulo: '', extracto: '', evidencia_documento: '', proceso_sede: 'Todas', responsable: '', periodicidad: 'Anual', observaciones: '' }

function Obligaciones({ ambito, cat, confirmar, setError, cargarCat, puedeCrear, puedeEditar }) {
  const [items, setItems] = useState([])
  const [reqs, setReqs] = useState([])
  const [buscar, setBuscar] = useState('')
  const [tema, setTema] = useState('')
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const params = useCallback(() => { const p = new URLSearchParams({ ambito }); if (buscar) p.set('buscar', buscar); if (tema) p.set('tema', tema); return `?${p}` }, [ambito, buscar, tema])
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => setItems(await ultima(api.legal.obligaciones(params()))), [params])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  useEffect(() => { setTema(''); api.legal.requisitos(`?ambito=${ambito}&estado=vigente`).then(setReqs).catch(() => {}) }, [ambito])
  const temas = (cat?.temas_obligaciones || {})[ambito] || []
  const guardar = async () => {
    setErr('')
    try {
      const datos = { ...form, ambito, requisito: form.requisito || null }
      if (form.id) await api.legal.editarObligacion(form.id, datos); else await api.legal.crearObligacion(datos)
      setForm(null); await cargar(); await cargarCat()
    } catch (e) { setErr(e.message) }
  }
  const baja = async (o) => {
    const m = await confirmar({ titulo: 'Dar de baja la obligación', mensaje: 'Queda como registro y sale de las próximas evaluaciones.', textoConfirmar: 'Dar de baja', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true, multilinea: true } })
    if (m === null) return
    try { await api.legal.bajaObligacion(o.id, m); await cargar() } catch (e) { setError(e.message) }
  }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-64 pl-9" placeholder="Norma, artículo o extracto…" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <select className="input-esynapse w-64" value={tema} onChange={(e) => setTema(e.target.value)}><option value="">Todos los temas</option>{temas.map((t) => <option key={t} value={t}>{t}</option>)}</select>
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setForm({ ...OBL_VACIA }) }}><Plus className="h-4 w-4" /> Nueva obligación</button>}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-ficha w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">Documento / registro</th><th className="px-2">Documento legal</th><th className="px-2">Artículo</th><th className="px-2">Extracto</th><th className="px-2">Responsable</th><th className="px-2">Periodicidad</th><th className="px-2 text-center">Último resultado</th><th /></tr></thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.id} className={`border-b border-slate-100 align-top dark:border-slate-800/60 ${o.estado !== 'vigente' ? 'opacity-50' : ''}`}>
                <td className="max-w-[12rem] px-2 py-2">{o.evidencia_documento || '—'}</td>
                <td className="max-w-[12rem] px-2" title={o.documento_legal}>{(o.documento_legal || o.documento || '—').split('\n')[0]}</td>
                <td className="px-2">{o.articulo || '—'}</td>
                <td className="max-w-md px-2"><span className="line-clamp-3" title={o.extracto}>{o.extracto}</span></td>
                <td className="px-2">{o.responsable || '—'}</td><td className="px-2">{o.periodicidad || '—'}</td>
                <td className="px-2 text-center">{o.estado !== 'vigente' ? <span className="text-[11px]">Baja</span> : o.ultimo_resultado ? <><Chip par={RESULTADO[o.ultimo_resultado.resultado]} /><p className="text-[11px] text-slate-500 dark:text-slate-400">{o.ultimo_resultado.periodo}</p></> : '—'}</td>
                <td className="whitespace-nowrap px-2">{puedeEditar && o.estado === 'vigente' && <><button className="p-1" title="Corregir" onClick={() => setForm({ id: o.id, ...Object.fromEntries(Object.keys(OBL_VACIA).map((k) => [k, o[k] ?? ''])) })}><Pencil className="h-3.5 w-3.5" /></button><button className="p-1 text-red-500" title="Dar de baja" onClick={() => baja(o)}><X className="h-3.5 w-3.5" /></button></>}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin obligaciones en este ámbito</td></tr>}
          </tbody>
        </table>
        <p className="px-2 py-1 text-[11px] text-slate-400">{items.length} obligación(es)</p>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Corregir la obligación' : 'Nueva obligación'} onCerrar={() => setForm(null)} ancho="max-w-3xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Tema</label><CampoSugerencias value={form.tema} opciones={temas} onChange={(v) => setForm({ ...form, tema: v })} /></div>
              <div><label className={lbl}>Norma de la lista</label><select className={inp} value={String(form.requisito || '')} onChange={(e) => setForm({ ...form, requisito: e.target.value ? Number(e.target.value) : '' })}><option value="">— Sin vincular (texto) —</option>{reqs.map((r) => <option key={r.id} value={r.id}>{r.denominacion} — {r.nombre.slice(0, 60)}</option>)}</select></div>
            </div>
            {!form.requisito && <div><label className={lbl}>Documento legal asociado (texto)</label><input className={inp} value={form.documento_legal} onChange={(e) => setForm({ ...form, documento_legal: e.target.value })} /></div>}
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>N° de artículo</label><input className={inp} value={form.articulo} onChange={(e) => setForm({ ...form, articulo: e.target.value })} /></div>
              <div><label className={lbl}>Proceso / sede</label><input className={inp} value={form.proceso_sede} onChange={(e) => setForm({ ...form, proceso_sede: e.target.value })} /></div>
              <div><label className={lbl}>Responsable</label><input className={inp} value={form.responsable} onChange={(e) => setForm({ ...form, responsable: e.target.value })} /></div>
              <div><label className={lbl}>Periodicidad</label><CampoSugerencias value={form.periodicidad} opciones={['Anual', 'Semestral', 'Mensual', 'Cada vez que ocurra', 'Según lo programado', 'Única vez']} onChange={(v) => setForm({ ...form, periodicidad: v })} /></div>
            </div>
            <div><label className={lbl}>Extracto del artículo a cumplir</label><CampoAmpliable multilinea rows={3} value={form.extracto} onChange={(v) => setForm({ ...form, extracto: v })} /></div>
            <div><label className={lbl}>Documento / registro que evidencia el cumplimiento</label><CampoAmpliable multilinea value={form.evidencia_documento} onChange={(v) => setForm({ ...form, evidencia_documento: v })} /></div>
            {err && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{err}</p>}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" disabled={!form.extracto.trim()} onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ------------------------------------------------------------ Evaluaciones */
function Evaluaciones({ ambito, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeAprobar, puedeEliminar }) {
  const [evs, setEvs] = useState([])
  const [sel, setSel] = useState(null)
  const [res, setRes] = useState([])
  const [filtro, setFiltro] = useState('')
  const [buscar, setBuscar] = useState('')
  const [edit, setEdit] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(async () => {
    const lista = await api.legal.evaluaciones(`?ambito=${ambito}`)
    setEvs(lista)
    setSel((s) => lista.find((e) => e.id === s?.id) || lista.find((e) => e.estado === 'en_curso') || lista[0] || null)
  }, [ambito])
  useEffect(() => { setSel(null); cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  const ultima = useUltimaRespuesta()
  const cargarRes = useCallback(async () => {
    if (!sel) { setRes([]); return }
    const p = new URLSearchParams(); if (filtro) p.set('resultado', filtro); if (buscar) p.set('buscar', buscar)
    setRes(await ultima(api.legal.resultados(sel.id, `?${p}`)))
  }, [sel, filtro, buscar])
  useEffect(() => { cargarRes().catch((e) => setErr(e.message)) }, [cargarRes])

  const nueva = async () => {
    const mes = new Date().getMonth() + 1
    const periodo = await confirmar({ titulo: 'Nueva evaluación semestral', mensaje: 'Se cargan todas las obligaciones vigentes del ámbito como pendientes.', textoConfirmar: 'Crear', entrada: { etiqueta: `Periodo (${new Date().getFullYear()})`, obligatorio: true, valorInicial: mes <= 6 ? 'Semestre 1' : 'Semestre 2' } })
    if (periodo === null) return
    setErr('')
    try { const e = await api.legal.crearEvaluacion({ ambito, anio: new Date().getFullYear(), periodo }); await cargar(); setSel(e) } catch (e) { setErr(e.message) }
  }
  const guardar = async (r, resultado) => {
    setErr('')
    const fd = new FormData()
    fd.append('resultado_id', r.id); fd.append('resultado', resultado); fd.append('observaciones', edit?.id === r.id ? edit.observaciones : r.observaciones || '')
    if (edit?.id === r.id && edit.evidencia) fd.append('evidencia', edit.evidencia)
    try { await api.legal.evaluar(sel.id, fd); setEdit(null); await cargarRes(); await cargar() } catch (e) { setErr(e.message) }
  }
  const cerrar = async () => {
    const clave = await confirmar({ titulo: 'Cerrar la evaluación', mensaje: `Cierra ${sel.anio} · ${sel.periodo}. Cada incumplimiento se registra como hallazgo para su acción correctiva. Los resultados quedan de solo lectura.`, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
    if (clave === null) return
    setErr('')
    try { await api.legal.cerrarEvaluacion(sel.id, clave); await cargar(); await cargarRes() } catch (e) { setErr(e.message) }
  }
  const anular = async () => { if (!await confirmar({ titulo: 'Anular la evaluación', mensaje: 'Solo una evaluación abierta por error, sin resultados.', textoConfirmar: 'Anular', peligro: true })) return; try { await api.legal.anularEvaluacion(sel.id); setSel(null); await cargar() } catch (e) { setErr(e.message) } }
  const abierta = sel?.estado === 'en_curso'
  const r0 = sel?.resumen

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {evs.map((e) => (
          <button key={e.id} onClick={() => setSel(e)} className={`rounded-lg border px-3 py-1.5 text-xs ${sel?.id === e.id ? 'border-esynapse-600 bg-esynapse-600/10 font-semibold' : 'border-slate-200 dark:border-slate-700'}`}>
            {e.anio} · {e.periodo} <span className={e.estado === 'en_curso' ? 'text-esynapse-500' : 'text-emerald-600'}>({e.estado_display.toLowerCase()}{e.historica ? ', Excel' : ''})</span>
          </button>
        ))}
        {evs.length === 0 && <span className="text-sm text-slate-400">Sin evaluaciones en este ámbito.</span>}
        <span className="ml-auto flex gap-2">
          {sel && <button className="btn-secondary" onClick={() => abrirPdf(api.legal.matrizPdf(ambito, sel.anio))}><FileText className="h-4 w-4" /> Imprimir matriz {sel.anio}</button>}
          {puedeCrear && !evs.some((e) => e.estado === 'en_curso') && <button className="btn-primary" onClick={nueva}><Plus className="h-4 w-4" /> Nueva evaluación</button>}
        </span>
      </div>
      {err && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{err}</p>}
      {sel && (
        <>
          <div className="grid gap-3 md:grid-cols-5">
            {[['Cumple', r0.cumple, 'text-emerald-600'], ['No cumple', r0.no_cumple, 'text-red-600'], ['No aplica', r0.no_aplica, 'text-slate-500'], ['Pendientes', r0.pendiente, r0.pendiente ? 'text-esynapse-500' : 'text-slate-500'],
              ['Cumplimiento', r0.porcentaje != null ? `${r0.porcentaje} %` : '—', CALIF[r0.calificacion]?.[1] || '']].map(([t, v, c]) => (
              <div key={t} className="card-esynapse p-3"><p className="text-xs text-slate-500 dark:text-slate-400">{t}</p><p className={`text-2xl font-bold ${c}`}>{v}</p>{t === 'Cumplimiento' && r0.calificacion && <p className="text-[11px] text-slate-500">{CALIF[r0.calificacion][0]}</p>}</div>
            ))}
          </div>
          {!abierta && <p className="flex items-center gap-1 text-xs text-slate-500"><Lock className="h-3.5 w-3.5" /> Cerrada{sel.firma?.nombre ? ` por ${sel.firma.nombre} (${sel.firma.sigla}) el ${fechaHora(sel.firma.fecha)}` : sel.historica ? ' (cargada de la matriz en Excel)' : ''}: solo lectura.</p>}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-64 pl-9" placeholder="Norma, artículo o extracto…" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
            <select className="input-esynapse w-44" value={filtro} onChange={(e) => setFiltro(e.target.value)}><option value="">Todos los resultados</option>{Object.entries(RESULTADO).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select>
          </div>
          <div className="card-esynapse overflow-x-auto">
            <table className="tabla-ficha w-full text-xs">
              <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">Tema</th><th className="px-2">Documento legal / artículo</th><th className="px-2">Extracto</th><th className="px-2">Evidencia esperada</th><th className="px-2 text-center">Resultado</th><th className="px-2">Observaciones</th>{abierta && puedeEditar && <th className="px-2 text-center">Evaluar</th>}</tr></thead>
              <tbody>
                {res.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 align-top dark:border-slate-800/60">
                    <td className="px-2 py-2">{r.obligacion_info.tema || '—'}</td>
                    <td className="max-w-[12rem] px-2">{(r.obligacion_info.documento || '').split('\n')[0]}<p className="font-semibold">{r.obligacion_info.articulo}</p></td>
                    <td className="max-w-md px-2"><span className="line-clamp-3" title={r.obligacion_info.extracto}>{r.obligacion_info.extracto}</span></td>
                    <td className="max-w-[12rem] px-2">{r.obligacion_info.evidencia_documento || '—'}</td>
                    <td className="px-2 text-center"><Chip par={RESULTADO[r.resultado]} />{r.hallazgo_codigo && <p className="text-[11px] text-red-600">{r.hallazgo_codigo}</p>}</td>
                    <td className="max-w-xs px-2">
                      {edit?.id === r.id ? (
                        <div className="space-y-1"><CampoAmpliable multilinea value={edit.observaciones} onChange={(v) => setEdit({ ...edit, observaciones: v })} />
                          <label className="btn-secondary !py-0.5 cursor-pointer text-[11px]">Evidencia<input type="file" className="hidden" onChange={(e) => setEdit({ ...edit, evidencia: e.target.files[0] || null })} /></label>{edit.evidencia && <span className="ml-1 text-[11px]">{edit.evidencia.name}</span>}</div>
                      ) : <>{r.observaciones || '—'}{r.evidencia_url && <a className="ml-1 underline" href={r.evidencia_url} target="_blank" rel="noreferrer">evidencia</a>}</>}
                    </td>
                    {abierta && puedeEditar && (
                      <td className="whitespace-nowrap px-2 text-center">
                        {edit?.id === r.id ? (
                          <div className="flex flex-col gap-1">{[['cumple', 'Cumple'], ['no_cumple', 'No cumple'], ['no_aplica', 'No aplica']].map(([k, n]) => <button key={k} className="btn-secondary !py-0.5 text-[11px]" onClick={() => guardar(r, k)}>{n}</button>)}<button className="text-[11px] text-slate-400" onClick={() => setEdit(null)}>Cancelar</button></div>
                        ) : (
                          <span className="flex gap-1"><button className="btn-secondary !py-0.5 text-[11px]" onClick={() => guardar(r, 'cumple')}>Cumple</button><button className="btn-secondary !py-0.5 text-[11px]" onClick={() => setEdit({ id: r.id, observaciones: r.observaciones || '', evidencia: null })}>Otro…</button></span>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
                {res.length === 0 && <tr><td colSpan={7} className="py-6 text-slate-400">Sin resultados</td></tr>}
              </tbody>
            </table>
          </div>
          {abierta && (puedeAprobar || puedeEditar) && <BarraEtapa titulo="Cerrar la evaluación" nota={r0.pendiente ? `Faltan ${r0.pendiente} obligación(es) por evaluar.` : 'Todas evaluadas: el cierre se firma y registra los incumplimientos como hallazgos.'} botones={[
            ...(r0.cumple + r0.no_cumple + r0.no_aplica === 0 && puedeEliminar ? [{ texto: 'Anular', accion: anular, secundario: true }] : []),
            ...(puedeAprobar ? [{ texto: 'Cerrar con firma', accion: cerrar }] : [])]} />}
        </>
      )}
    </div>
  )
}

/* ------------------------------------------------------------- Indicadores */
function Indicadores({ irA }) {
  const [ind, setInd] = useState(null)
  useEffect(() => { api.legal.indicadores().then(setInd).catch(() => {}) }, [])
  if (!ind) return <p className="text-sm text-slate-400">Cargando…</p>
  const g = ind.cumplimiento_global
  return (
    <div className="space-y-4">
      <div className="card-esynapse flex flex-wrap items-center gap-6 p-4">
        <div><p className="text-xs text-slate-500 dark:text-slate-400">Cumplimiento de requisitos legales (última evaluación de cada ámbito)</p>
          <p className={`text-3xl font-bold ${CALIF[g.calificacion]?.[1] || ''}`}>{g.porcentaje != null ? `${g.porcentaje} %` : '—'}</p>
          <p className="text-xs text-slate-500">{g.cumplidos} de {g.evaluados} obligaciones evaluadas · meta {g.meta} % · semestral</p></div>
        <p className="text-xs text-slate-500">Escala: Bueno &gt; 80 % · Regular 70–80 % · Malo &lt; 70 %</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {ind.ambitos.map((a) => (
          <div key={a.ambito} className="card-esynapse space-y-2 p-3 text-xs">
            <div className="flex items-center justify-between"><span className={`rounded px-2 py-0.5 text-[11px] font-semibold ${COLOR_AMBITO[a.ambito]}`}>{a.nombre}</span>
              {a.evaluacion_vencida && <span className="rounded bg-red-500/15 px-1.5 py-0.5 text-[11px] font-semibold text-red-600">evaluación vencida</span>}</div>
            <p>{a.requisitos} normas vigentes{a.derogados ? ` (${a.derogados} derogadas)` : ''} · {a.obligaciones} obligaciones</p>
            {a.ultima ? <p>Última: <strong>{a.ultima.periodo}</strong> — <span className={`font-bold ${CALIF[a.ultima.calificacion]?.[1] || ''}`}>{a.ultima.porcentaje != null ? `${a.ultima.porcentaje} %` : '—'}</span> ({a.ultima.no_cumple} incumplimiento(s))</p> : <p className="text-slate-400">Sin evaluaciones cerradas.</p>}
            {a.en_curso && <p>En curso: {a.en_curso.periodo} · avance {a.en_curso.avance ?? 0} %</p>}
            {a.tendencia.length > 1 && <div className="flex items-end gap-1 pt-1">{a.tendencia.map((t) => <div key={t.periodo} className="flex-1 text-center" title={`${t.periodo}: ${t.porcentaje} %`}><div className="mx-auto w-6 rounded-t bg-esynapse-600/60" style={{ height: `${Math.max(4, (t.porcentaje || 0) * 0.5)}px` }} /><p className="truncate text-[11px] text-slate-500 dark:text-slate-400">{t.periodo.replace(/ · /, ' ')}</p></div>)}</div>}
            <button className="text-[11px] text-esynapse-500 underline" onClick={() => irA(a.ambito)}>Ver evaluaciones</button>
          </div>
        ))}
      </div>
    </div>
  )
}
