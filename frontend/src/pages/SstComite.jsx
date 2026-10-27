import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FileText, Pencil, Plus, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { Vistas as Sub } from '../components/NavModulo.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import FirmaComite from '../components/FirmaComite.jsx'
import { api } from '../lib/api.js'
import { fecha, fechaHora, hoy as hoyLocal } from '../lib/fecha.js'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
// Estados (regla 10): gris programado/pendiente · azul en proceso · ámbar en elaboración/reprogramación · verde realizado/cumplido/aprobado · rojo cancelado/vencido/no cumplido.
const GRIS = 'bg-slate-500/15 text-slate-500'
const VERDE = 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
const ROJO = 'bg-red-500/15 text-red-600 dark:text-red-400'
const AMBAR = 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
const AZUL = 'bg-blue-500/15 text-blue-600 dark:text-blue-400'
const EST_REUNION = { programada: ['Programada', GRIS], realizada: ['Realizada', VERDE], cancelada: ['Cancelada', ROJO] }
const EST_ACUERDO = { pendiente: ['Pendiente', GRIS], en_proceso: ['En proceso', AZUL], cumplido: ['Cumplido', VERDE], no_cumplido: ['No cumplido', ROJO] }
const EST_PROGRAMA = { borrador: ['En elaboración', AMBAR], aprobado: ['Aprobado', VERDE], reprogramacion: ['En reprogramación', AMBAR] }
const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']

const Chip = ({ par, extra }) => (par ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{par[0]}{extra}</span> : null)
function Aviso({ texto }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [texto])
  return <p ref={ref} className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p>
}
const useTrabajadores = () => {
  const [t, setT] = useState([])
  useEffect(() => { api.org.trabajadores().then((x) => setT(x.filter((w) => w.estado === 'activo'))).catch(() => {}) }, [])
  return t
}
const hoyIso = () => hoyLocal()

/* ================================================================================== COMITÉ */
export function Comite(props) {
  const { setError } = props
  const [vista, setVista] = useState('comite')
  const [c, setC] = useState(undefined)
  const cargar = useCallback(() => api.sst.comiteVigente().then(setC).catch((e) => setError(e.message)), [setError])
  useEffect(() => { cargar() }, [cargar])
  if (c === undefined) return null
  if (c === null) return <NuevoComite {...props} alCrear={setC} />
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Sub valor={vista} onChange={setVista} opciones={[['comite', 'Comité y miembros'], ['reuniones', 'Reuniones y actas'], ['acuerdos', 'Seguimiento de acuerdos']]} />
        <span className="text-xs text-slate-500">Periodo {c.periodo} · {fecha(c.fecha_instalacion)} al {fecha(c.fecha_fin)}</span>
        {c.alertas.length > 0 && <span className="rounded bg-amber-500/15 px-2 py-0.5 text-[11px] font-semibold text-amber-600 dark:text-amber-400">{c.alertas.length} alerta(s)</span>}
      </div>
      {vista === 'comite' && <DatosComite {...props} c={c} setC={setC} />}
      {vista === 'reuniones' && <Reuniones {...props} c={c} alCambiar={cargar} />}
      {vista === 'acuerdos' && <Acuerdos {...props} c={c} alCambiar={cargar} />}
    </div>
  )
}

function NuevoComite({ puedeCrear, alCrear }) {
  const [f, setF] = useState({ periodo: '', fecha_eleccion: '', fecha_instalacion: '', fecha_fin: '' })
  const [err, setErr] = useState('')
  const crear = async () => { setErr(''); try { alCrear(await api.sst.crearComite({ ...f, fecha_eleccion: f.fecha_eleccion || null })) } catch (e) { setErr(e.message) } }
  return (
    <div className="card-esynapse space-y-3 p-4 text-sm">
      <p className="text-slate-500">No hay un comité registrado. Registre el comité elegido (mandato de dos años).</p>
      {puedeCrear && <div className="grid gap-3 md:grid-cols-5">
        <div><label className={lbl}>Periodo</label><input className={inp} placeholder="2027-2029" value={f.periodo} onChange={(e) => setF({ ...f, periodo: e.target.value })} /></div>
        <div><label className={lbl}>Fecha de elección</label><input type="date" className={inp} value={f.fecha_eleccion} onChange={(e) => setF({ ...f, fecha_eleccion: e.target.value })} /></div>
        <div><label className={lbl}>Fecha de instalación</label><input type="date" className={inp} value={f.fecha_instalacion} onChange={(e) => setF({ ...f, fecha_instalacion: e.target.value })} /></div>
        <div><label className={lbl}>Fin del mandato</label><input type="date" className={inp} value={f.fecha_fin} onChange={(e) => setF({ ...f, fecha_fin: e.target.value })} /></div>
        <div className="flex items-end"><button className="btn-primary" onClick={crear}>Registrar</button></div>
      </div>}
      {err && <Aviso texto={err} />}
    </div>
  )
}

const DOCS = [['acta_eleccion', 'Acta del proceso de elección'], ['acta_instalacion', 'Acta de instalación'], ['constancia_t_registro', 'Constancia del T-Registro']]
const MIEMBRO = { id: null, trabajador: '', representacion: 'empleador', condicion: 'titular', cargo: 'miembro', fecha_alta: hoyIso() }

function DatosComite({ c, setC, confirmar, puedeEditar }) {
  const trabajadores = useTrabajadores()
  const [datos, setDatos] = useState(null)
  const [m, setM] = useState(null)
  const [err, setErr] = useState('')
  const [verBajas, setVerBajas] = useState(false)
  const run = async (p) => { setErr(''); try { setC(await p); return true } catch (e) { setErr(e.message); return false } }
  const subir = (campo, file) => { const fd = new FormData(); fd.append('campo', campo); fd.append('archivo', file); run(api.sst.subirComite(c.id, fd)) }
  const baja = async (x) => {
    const motivo = await confirmar({ titulo: `Baja de ${x.nombre}`, mensaje: 'El miembro deja el comité; su historial se conserva. Si corresponde, registre al suplente como titular.', textoConfirmar: 'Registrar baja', peligro: true, entrada: { etiqueta: 'Motivo (renuncia, cese, reemplazo…)', obligatorio: true } })
    if (motivo !== null) run(api.sst.accionComite(c.id, 'baja_miembro', { id: x.id, motivo }))
  }
  const vigentes = c.miembros.filter((x) => !x.fecha_baja)
  const grupos = [['empleador', 'Representantes del empleador'], ['trabajadores', 'Representantes de los trabajadores']]
  return (
    <div className="space-y-3">
      {c.alertas.length > 0 && <ul className="space-y-1 rounded-lg bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300">{c.alertas.map((a) => <li key={a}>• {a}</li>)}</ul>}
      <div className="card-esynapse grid gap-3 p-3 text-xs md:grid-cols-4">
        {datos ? <>
          <div><label className={lbl}>Fecha de elección</label><input type="date" className={inp} value={datos.fecha_eleccion || ''} onChange={(e) => setDatos({ ...datos, fecha_eleccion: e.target.value })} /></div>
          <div><label className={lbl}>Fecha de instalación</label><input type="date" className={inp} value={datos.fecha_instalacion || ''} onChange={(e) => setDatos({ ...datos, fecha_instalacion: e.target.value })} /></div>
          <div><label className={lbl}>Fin del mandato</label><input type="date" className={inp} value={datos.fecha_fin || ''} onChange={(e) => setDatos({ ...datos, fecha_fin: e.target.value })} /></div>
          <div><label className={lbl}>Registro en el T-Registro</label><input type="date" className={inp} value={datos.fecha_t_registro || ''} onChange={(e) => setDatos({ ...datos, fecha_t_registro: e.target.value })} /></div>
          <div className="md:col-span-3"><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} value={datos.observaciones} onChange={(v) => setDatos({ ...datos, observaciones: v })} /></div>
          <div className="flex items-end gap-2"><button className="btn-secondary" onClick={() => setDatos(null)}>Cancelar</button><button className="btn-primary" onClick={async () => { const { fecha_eleccion, fecha_instalacion, fecha_fin, fecha_t_registro, observaciones } = datos; if (await run(api.sst.editarComite(c.id, { fecha_eleccion: fecha_eleccion || null, fecha_instalacion, fecha_fin, fecha_t_registro: fecha_t_registro || null, observaciones }))) setDatos(null) }}>Guardar</button></div>
        </> : <>
          <div><p className="text-slate-500">Elección</p><p>{fecha(c.fecha_eleccion) || '—'}</p></div>
          <div><p className="text-slate-500">Instalación · fin del mandato</p><p>{fecha(c.fecha_instalacion)} · {fecha(c.fecha_fin)}</p></div>
          <div><p className="text-slate-500">T-Registro</p><p>{fecha(c.fecha_t_registro) || <Chip par={['Sin registrar', ROJO]} />}</p></div>
          <div className="flex items-start justify-end">{puedeEditar && <button className="btn-secondary !py-1 text-xs" onClick={() => setDatos({ ...c })}><Pencil className="h-3.5 w-3.5" /> Editar datos</button>}</div>
          {c.observaciones && <p className="whitespace-pre-line text-slate-500 md:col-span-4">{c.observaciones}</p>}
          <div className="flex flex-wrap gap-4 md:col-span-4">{DOCS.map(([k, n]) => (
            <span key={k}>{n}: {c.archivos[k] ? <a className="text-esynapse-500 underline" href={c.archivos[k]} target="_blank" rel="noreferrer">ver</a> : <span className="text-slate-400">sin adjuntar</span>}
              {puedeEditar && <label className="ml-1 cursor-pointer text-esynapse-500 underline">{c.archivos[k] ? 'reemplazar' : 'adjuntar'}<input type="file" className="hidden" onChange={(e) => e.target.files[0] && subir(k, e.target.files[0])} /></label>}</span>
          ))}</div>
        </>}
      </div>
      <div className="grid gap-3 2xl:grid-cols-2">
        {grupos.map(([rep, titulo]) => (
          <div key={rep} className="card-esynapse overflow-x-auto">
            <p className="px-3 pt-2 text-xs font-semibold">{titulo}</p>
            <table className="tabla-ficha w-full text-xs">
              <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">Miembro</th><th className="px-2">Puesto</th><th className="px-2 text-center">Condición</th><th className="px-2">Cargo</th><th className="px-2 text-right">Desde</th><th /></tr></thead>
              <tbody>
                {vigentes.filter((x) => x.representacion === rep).map((x) => (
                  <tr key={x.id} className="border-b border-slate-100 dark:border-slate-800/60"><td className="px-2 py-1.5">{x.nombre}<span className="block text-[11px] text-slate-500">DNI {x.documento || '—'}</span></td><td className="px-2">{x.puesto}</td><td className="px-2 text-center">{x.condicion_display}</td><td className="px-2">{x.cargo !== 'miembro' ? <Chip par={[x.cargo_display, AZUL]} /> : x.cargo_display}</td><td className="whitespace-nowrap px-2 text-right">{fecha(x.fecha_alta)}</td>
                    <td className="whitespace-nowrap px-2">{puedeEditar && <><button className="p-1 text-slate-500" title="Corregir" onClick={() => { setErr(''); setM({ ...MIEMBRO, ...x }) }}><Pencil className="h-3.5 w-3.5" /></button><button className="p-1 text-red-500" title="Baja" onClick={() => baja(x)}><X className="h-3.5 w-3.5" /></button></>}</td></tr>
                ))}
                {!vigentes.some((x) => x.representacion === rep) && <tr><td colSpan={6} className="py-4 text-slate-400">Sin miembros registrados</td></tr>}
              </tbody>
            </table>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {puedeEditar && !m && <button className="btn-primary" onClick={() => { setErr(''); setM({ ...MIEMBRO }) }}><Plus className="h-4 w-4" /> Agregar miembro</button>}
        {c.miembros.some((x) => x.fecha_baja) && <button className="text-esynapse-500 underline" onClick={() => setVerBajas(!verBajas)}>{verBajas ? 'Ocultar' : 'Ver'} las bajas</button>}
        <span className="text-slate-500">Los miembros se eligen entre los trabajadores de Organización y personal. Comité paritario; presidente y secretario entre los titulares.</span>
      </div>
      {verBajas && <ul className="text-xs text-slate-500">{c.miembros.filter((x) => x.fecha_baja).map((x) => <li key={x.id}>{x.nombre} ({x.representacion_display}, {x.cargo_display}) — baja el {fecha(x.fecha_baja)}: {x.motivo_baja}</li>)}</ul>}
      {m && (
        <div className="card-esynapse grid gap-3 p-3 text-xs md:grid-cols-6">
          <div className="md:col-span-2"><label className={lbl}>Trabajador</label><select className={inp} disabled={Boolean(m.id)} value={String(m.trabajador || '')} onChange={(e) => setM({ ...m, trabajador: e.target.value })}><option value="">— Elija —</option>{trabajadores.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo} · {t.puesto_nombre}</option>)}</select></div>
          <div><label className={lbl}>Representa a</label><select className={inp} value={m.representacion} onChange={(e) => setM({ ...m, representacion: e.target.value })}><option value="empleador">Empleador</option><option value="trabajadores">Trabajadores</option></select></div>
          <div><label className={lbl}>Condición</label><select className={inp} value={m.condicion} onChange={(e) => setM({ ...m, condicion: e.target.value })}><option value="titular">Titular</option><option value="suplente">Suplente</option></select></div>
          <div><label className={lbl}>Cargo</label><select className={inp} value={m.cargo} onChange={(e) => setM({ ...m, cargo: e.target.value })}><option value="miembro">Miembro</option><option value="presidente">Presidente</option><option value="secretario">Secretario</option></select></div>
          <div><label className={lbl}>Desde</label><input type="date" className={inp} value={m.fecha_alta || ''} onChange={(e) => setM({ ...m, fecha_alta: e.target.value })} /></div>
          {err && <div className="md:col-span-6"><Aviso texto={err} /></div>}
          <div className="flex justify-end gap-2 md:col-span-6"><button className="btn-secondary" onClick={() => setM(null)}>Cancelar</button><button className="btn-primary" onClick={async () => { if (await run(api.sst.accionComite(c.id, 'miembro', m))) setM(null) }}>Guardar</button></div>
        </div>
      )}
      {err && !m && <Aviso texto={err} />}
    </div>
  )
}

const REUNION = { tipo: 'ordinaria', fecha: hoyIso(), hora: '', lugar: '', invitados: '', agenda: [''], asistentes: [], desarrollo: '', proxima_reunion: '', acuerdos: [] }

function Reuniones({ c, confirmar, abrirPdf, setError, puedeCrear, puedeEditar, puedeEliminar, alCambiar }) {
  const trabajadores = useTrabajadores()
  const [anio, setAnio] = useState(String(new Date().getFullYear()))
  const [items, setItems] = useState([])
  const [form, setForm] = useState(null)
  const [acuerdo, setAcuerdo] = useState(null)
  const [acta, setActa] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.reuniones(`?comite=${c.id}&anio=${anio}`).then(setItems).catch((e) => setError(e.message)), [c.id, anio, setError])
  useEffect(() => { cargar() }, [cargar])
  const vigentes = c.miembros.filter((x) => !x.fecha_baja)
  const editable = !form?.id || form.estado === 'programada'
  const mostrar = (r) => { setForm({ ...REUNION, ...r, hora: (r.hora || '').slice(0, 5), proxima_reunion: r.proxima_reunion || '', agenda: r.agenda?.length ? r.agenda : [''] }) }
  const guardar = async () => {
    setErr('')
    const d = { comite: c.id, tipo: form.tipo, fecha: form.fecha, hora: form.hora || null, lugar: form.lugar, invitados: form.invitados, agenda: form.agenda, asistentes: form.asistentes, desarrollo: form.desarrollo, proxima_reunion: form.proxima_reunion || null }
    try { const r = form.id ? await api.sst.editarReunion(form.id, d) : await api.sst.crearReunion(d); mostrar(r); cargar(); return r } catch (e) { setErr(e.message); return null }
  }
  const accion = async (nombre, datos) => { setErr(''); try { mostrar(await api.sst.accionReunion(form.id, nombre, datos)); cargar(); alCambiar() } catch (e) { setErr(e.message) } }
  const cerrar = async () => {
    if (!await guardar()) return
    if (!acta) { setErr('Adjunte el acta firmada por los asistentes.'); return }
    const fd = new FormData(); fd.append('acta', acta)
    try { mostrar(await api.sst.cerrarReunion(form.id, fd)); setActa(null); cargar(); alCambiar() } catch (e) { setErr(e.message) }
  }
  const cancelar = async () => { const m = await confirmar({ titulo: 'Cancelar la reunión', mensaje: 'Queda registrada como no realizada.', textoConfirmar: 'Cancelar reunión', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) accion('cancelar', { motivo: m }) }
  const q = useMemo(() => {
    if (!form) return null
    const tit = vigentes.filter((x) => x.condicion === 'titular')
    const pres = tit.filter((x) => form.asistentes.includes(x.id)).length
    const req = tit.length ? Math.floor(tit.length / 2) + 1 : 0
    return { tit: tit.length, pres, req, ok: tit.length > 0 && pres >= req }
  }, [form, vigentes])
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2"><input className="input-esynapse w-24" type="number" value={anio} onChange={(e) => setAnio(e.target.value)} />
        <span className="text-[11px] text-slate-500">Reunión ordinaria mensual. Se programa, se imprime el acta, se firma y se adjunta para cerrarla.</span>
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setActa(null); setForm({ ...REUNION, asistentes: [] }) }}><Plus className="h-4 w-4" /> Nueva reunión</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">N° acta</th><th className="px-2 text-right">Fecha</th><th className="px-2 text-center">Tipo</th><th className="px-2">Agenda</th><th className="px-2 text-center">Quórum</th><th className="px-2 text-right">Acuerdos</th><th className="px-2 text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.id} onClick={() => { setErr(''); setActa(null); mostrar(r) }} className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${r.estado === 'cancelada' ? 'opacity-50' : ''}`}>
                <td className="px-2 py-1.5 font-mono">{r.codigo}</td><td className="px-2 text-right">{fecha(r.fecha)}</td><td className="px-2 text-center">{r.tipo_display}</td><td className="max-w-[20rem] px-2">{(r.agenda || []).join(' · ') || '—'}</td>
                <td className="px-2 text-center">{r.quorum.presentes}/{r.quorum.titulares}</td><td className="px-2 text-right">{r.acuerdos.length}</td><td className="px-2 text-center"><Chip par={EST_REUNION[r.estado]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={7} className="py-8 text-slate-400">Sin reuniones en {anio}</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? `Acta ${form.codigo} — Reunión del Comité de SST` : 'Nueva reunión del Comité de SST'} onCerrar={() => { setForm(null); setAcuerdo(null) }} ancho="max-w-5xl">
        {form && (
          <div className="space-y-3 text-sm">
            {form.id && <div className="flex flex-wrap items-center gap-2"><Chip par={EST_REUNION[form.estado]} />
              {form.acta_url && <a className="text-xs text-esynapse-500 underline" href={form.acta_url} target="_blank" rel="noreferrer">Ver el acta firmada</a>}
              {form.estado === 'cancelada' && <span className="text-xs text-red-600">Cancelada: {form.motivo_cancelacion}</span>}
              <button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => abrirPdf(api.sst.actaPdf(form.id))}><FileText className="h-3.5 w-3.5" /> Acta para imprimir</button></div>}
            <div className="grid gap-3 md:grid-cols-6">
              <div><label className={lbl}>Tipo</label><select className={inp} disabled={!editable} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}><option value="ordinaria">Ordinaria</option><option value="extraordinaria">Extraordinaria</option><option value="instalacion">Instalación</option></select></div>
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} disabled={!editable} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
              <div><label className={lbl}>Hora</label><input type="time" className={inp} disabled={!editable} value={form.hora} onChange={(e) => setForm({ ...form, hora: e.target.value })} /></div>
              <div className="md:col-span-3"><label className={lbl}>Lugar</label><input className={inp} disabled={!editable} value={form.lugar} onChange={(e) => setForm({ ...form, lugar: e.target.value })} /></div>
            </div>
            <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
              <div className="mb-1 flex flex-wrap items-center gap-2"><p className="font-semibold">Asistentes</p>{q && <Chip par={q.ok ? ['Hay quórum', VERDE] : ['Sin quórum', ROJO]} extra={` · ${q.pres} de ${q.tit} titulares (se requieren ${q.req})`} />}</div>
              <div className="grid gap-1 md:grid-cols-3">{vigentes.map((x) => <label key={x.id} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" disabled={!editable} checked={form.asistentes.includes(x.id)} onChange={() => setForm({ ...form, asistentes: form.asistentes.includes(x.id) ? form.asistentes.filter((y) => y !== x.id) : [...form.asistentes, x.id] })} />{x.nombre} <span className="text-[11px] text-slate-500">({x.representacion_display}, {x.condicion_display.toLowerCase()})</span></label>)}</div>
              {vigentes.length === 0 && <p className="text-slate-400">Registre primero los miembros del comité.</p>}
              <div className="mt-2"><label className={lbl}>Invitados</label><input className={inp} disabled={!editable} value={form.invitados} onChange={(e) => setForm({ ...form, invitados: e.target.value })} /></div>
            </div>
            <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
              <p className="mb-1 font-semibold">Agenda</p>
              {form.agenda.map((a, i) => <div key={i} className="mb-1 flex gap-1"><span className="w-5 pt-1.5 text-slate-500">{i + 1}.</span><input className={`${inp} !py-1 text-xs`} disabled={!editable} value={a} onChange={(e) => setForm({ ...form, agenda: form.agenda.map((x, j) => (j === i ? e.target.value : x)) })} />{editable && form.agenda.length > 1 && <button className="p-1 text-red-500" onClick={() => setForm({ ...form, agenda: form.agenda.filter((_, j) => j !== i) })}><X className="h-3.5 w-3.5" /></button>}</div>)}
              {editable && <button className="text-[11px] text-esynapse-500 underline" onClick={() => setForm({ ...form, agenda: [...form.agenda, ''] })}>+ Agregar punto</button>}
            </div>
            <div><label className={lbl}>Desarrollo de la reunión</label><CampoAmpliable multilinea rows={4} disabled={!editable} value={form.desarrollo} onChange={(v) => setForm({ ...form, desarrollo: v })} /></div>
            {form.id && (
              <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
                <p className="mb-1 font-semibold">Acuerdos</p>
                <table className="tabla-ficha w-full">
                  <thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="px-1">N°</th><th className="px-1">Acuerdo</th><th className="px-1">Responsable</th><th className="px-1 text-right">Plazo</th><th className="px-1 text-center">Estado</th><th /></tr></thead>
                  <tbody>{form.acuerdos.map((a) => (
                    <tr key={a.id} className="border-t border-slate-100 dark:border-slate-800/60"><td className="px-1 py-1">{a.orden}</td><td className="px-1">{a.descripcion}</td><td className="px-1">{a.responsable_nombre || '—'}</td><td className="px-1 text-right">{fecha(a.plazo) || '—'}</td><td className="px-1 text-center"><Chip par={EST_ACUERDO[a.estado]} /></td>
                      <td className="whitespace-nowrap">{editable && puedeEditar && <><button className="p-1 text-slate-500" onClick={() => setAcuerdo({ id: a.id, descripcion: a.descripcion, responsable: a.responsable || '', plazo: a.plazo || '' })}><Pencil className="h-3.5 w-3.5" /></button><button className="p-1 text-red-500" onClick={() => accion('quitar_acuerdo', { id: a.id })}><X className="h-3.5 w-3.5" /></button></>}</td></tr>
                  ))}{form.acuerdos.length === 0 && <tr><td colSpan={6} className="py-2 text-slate-400">Sin acuerdos</td></tr>}</tbody>
                </table>
                {acuerdo && <div className="mt-2 grid gap-2 md:grid-cols-12">
                  <input className={`${inp} !py-1 text-xs md:col-span-6`} placeholder="Acuerdo" value={acuerdo.descripcion} onChange={(e) => setAcuerdo({ ...acuerdo, descripcion: e.target.value })} />
                  <select className={`${inp} !py-1 text-xs md:col-span-3`} value={String(acuerdo.responsable || '')} onChange={(e) => setAcuerdo({ ...acuerdo, responsable: e.target.value })}><option value="">— Responsable —</option>{trabajadores.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo}</option>)}</select>
                  <input type="date" className={`${inp} !py-1 text-xs md:col-span-2`} value={acuerdo.plazo} onChange={(e) => setAcuerdo({ ...acuerdo, plazo: e.target.value })} />
                  <button className="btn-primary !py-1 text-xs md:col-span-1" onClick={async () => { await accion('acuerdo', acuerdo); setAcuerdo(null) }}>OK</button>
                </div>}
                {editable && puedeEditar && !acuerdo && <button className="mt-1 text-[11px] text-esynapse-500 underline" onClick={() => setAcuerdo({ descripcion: '', responsable: '', plazo: '' })}>+ Agregar acuerdo</button>}
              </div>
            )}
            <div className="w-56"><label className={lbl}>Próxima reunión</label><input type="date" className={inp} disabled={!editable} value={form.proxima_reunion} onChange={(e) => setForm({ ...form, proxima_reunion: e.target.value })} /></div>
            {form.id && editable && puedeEditar && <div className="rounded-lg border-2 border-esynapse-500/40 p-2 text-xs"><p className="mb-1 font-semibold">Cerrar con el acta firmada</p><p className="mb-1 text-slate-500">Imprima el acta, recoja las firmas de los asistentes y adjunte el escaneo. Al cerrar, la reunión y sus acuerdos quedan de solo lectura.</p><input type="file" className="text-xs" onChange={(e) => setActa(e.target.files[0] || null)} /></div>}
            {err && <Aviso texto={err} />}
            {editable && puedeEditar && <div className="flex flex-wrap justify-end gap-2">
              {form.id && puedeEliminar && <button className="btn-secondary text-red-600" onClick={cancelar}>Cancelar reunión</button>}
              <button className="btn-secondary" onClick={guardar}>{form.id ? 'Guardar' : 'Programar reunión'}</button>
              {form.id && <button className="btn-primary" onClick={cerrar}>Cerrar con el acta firmada</button>}
            </div>}
          </div>
        )}
      </Modal>
    </div>
  )
}

function Acuerdos({ c, setError, puedeEditar, alCambiar }) {
  const [solo, setSolo] = useState(true)
  const [items, setItems] = useState([])
  const [seg, setSeg] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.acuerdos(`?comite=${c.id}${solo ? '&abiertos=1' : ''}`).then(setItems).catch((e) => setError(e.message)), [c.id, solo, setError])
  useEffect(() => { cargar() }, [cargar])
  const registrar = async () => { setErr(''); try { await api.sst.seguimientoAcuerdo(seg.id, seg); setSeg(null); cargar(); alCambiar() } catch (e) { setErr(e.message) } }
  return (
    <div className="space-y-2">
      <label className="flex items-center gap-1 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={solo} onChange={() => setSolo(!solo)} /> Solo pendientes y en proceso</label>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Acta</th><th className="px-2">Acuerdo</th><th className="px-2">Responsable</th><th className="px-2 text-right">Plazo</th><th className="px-2">Último seguimiento</th><th className="px-2 text-center">Estado</th><th /></tr></thead>
          <tbody>
            {items.map((a) => {
              const u = (a.seguimiento || []).at(-1)
              return (
                <tr key={a.id} className="border-b border-slate-100 dark:border-slate-800/60"><td className="px-2 py-1.5 font-mono">{a.reunion_codigo}<span className="block text-[11px] text-slate-500">{fecha(a.reunion_fecha)}</span></td><td className="max-w-[22rem] px-2">{a.descripcion}</td><td className="px-2">{a.responsable_nombre || '—'}</td>
                  <td className="px-2 text-right">{fecha(a.plazo) || '—'}{a.vencido && <span className="ml-1"><Chip par={['Vencido', ROJO]} /></span>}</td>
                  <td className="max-w-[18rem] px-2">{u ? <>{u.comentario}<span className="block text-[11px] text-slate-500">{u.usuario} · {fechaHora(u.fecha)}</span></> : '—'}</td>
                  <td className="px-2 text-center"><Chip par={EST_ACUERDO[a.estado]} /></td>
                  <td className="px-2">{puedeEditar && <button className="text-esynapse-500 underline" onClick={() => { setErr(''); setSeg({ id: a.id, descripcion: a.descripcion, estado: a.estado, comentario: '', fecha_cumplimiento: hoyIso() }) }}>Seguimiento</button>}</td></tr>
              )
            })}
            {items.length === 0 && <tr><td colSpan={7} className="py-8 text-slate-400">Sin acuerdos {solo ? 'abiertos' : ''}</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(seg)} titulo="Seguimiento del acuerdo" onCerrar={() => setSeg(null)}>
        {seg && <div className="space-y-3 text-sm">
          <p className="text-xs text-slate-500">{seg.descripcion}</p>
          <div className="grid gap-3 md:grid-cols-2">
            <div><label className={lbl}>Estado</label><select className={inp} value={seg.estado} onChange={(e) => setSeg({ ...seg, estado: e.target.value })}>{Object.entries(EST_ACUERDO).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select></div>
            {seg.estado === 'cumplido' && <div><label className={lbl}>Fecha de cumplimiento</label><input type="date" className={inp} value={seg.fecha_cumplimiento} onChange={(e) => setSeg({ ...seg, fecha_cumplimiento: e.target.value })} /></div>}
          </div>
          <div><label className={lbl}>Avance o evidencia</label><CampoAmpliable multilinea rows={3} value={seg.comentario} onChange={(v) => setSeg({ ...seg, comentario: v })} /></div>
          {err && <Aviso texto={err} />}
          <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setSeg(null)}>Cancelar</button><button className="btn-primary" onClick={registrar}>Registrar</button></div>
        </div>}
      </Modal>
    </div>
  )
}

/* ======================================================================== PROGRAMA SSOMA */
const ACT = { id: null, objetivo: '', descripcion: '', responsable: '', meta: '100%', indicador: 'N° de actividades ejecutadas / N° de actividades programadas × 100', meses: [] }

export function ProgramaSsoma({ puestos, confirmar, abrirPdf, setError, puedeCrear, puedeEditar, puedeAprobar }) {
  const [anio, setAnio] = useState(new Date().getFullYear())
  const [p, setP] = useState(undefined)
  const [act, setAct] = useState(null)
  const [obj, setObj] = useState(null)
  const [aprob, setAprob] = useState(false)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.programaSsoma(anio).then(setP).catch((e) => setError(e.message)), [anio, setError])
  useEffect(() => { setP(undefined); cargar() }, [cargar])
  const run = async (prom) => { setErr(''); try { setP(await prom); return true } catch (e) { setErr(e.message); return false } }
  const hoy = new Date()
  const futuro = (m) => anio > hoy.getFullYear() || (anio === hoy.getFullYear() && m > hoy.getMonth() + 1)
  const editable = p && p.estado !== 'aprobado'
  const celda = async (a, m) => {
    if (editable) {
      if (!puedeEditar) return
      const meses = a.meses.includes(m) ? a.meses.filter((x) => x !== m) : [...a.meses, m]
      run(api.sst.accionProgramaSsoma(p.id, 'actividad', { id: a.id, meses }))
      return
    }
    if (!puedeEditar || !a.meses.includes(m)) return
    if (futuro(m)) { setErr('No se registra la ejecución de un mes futuro.'); return }
    if (a.meses_ejecutados.includes(m)) {
      if (await confirmar({ titulo: 'Anular la ejecución', mensaje: `${a.descripcion} — ${MESES[m - 1]}. Evidencia registrada: ${a.evidencias[String(m)] || '—'}`, textoConfirmar: 'Anular', peligro: true })) run(api.sst.accionProgramaSsoma(p.id, 'ejecutar', { actividad: a.id, mes: m, ejecutado: false }))
      return
    }
    const ev = await confirmar({ titulo: `Ejecutado en ${MESES[m - 1]}`, mensaje: a.descripcion, textoConfirmar: 'Registrar', entrada: { etiqueta: 'Evidencia (registro, acta, informe… p. ej. INS-003-2026)', obligatorio: true } })
    if (ev !== null) run(api.sst.accionProgramaSsoma(p.id, 'ejecutar', { actividad: a.id, mes: m, ejecutado: true, evidencia: ev }))
  }
  // La aprobación la firman todos los titulares del Comité de SST (o el acta en papel firmada por todos).
  const aprobar = () => { setErr(''); setAprob(true) }
  const reprogramar = async () => { const m = await confirmar({ titulo: 'Reprogramar', mensaje: 'Abre una nueva versión del programa para cambiar lo programado; se guarda lo anterior en el historial. Luego se aprueba de nuevo.', textoConfirmar: 'Reprogramar', entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) run(api.sst.accionProgramaSsoma(p.id, 'reprogramar', { motivo: m })) }
  const quitar = async (a) => { const m = await confirmar({ titulo: 'Retirar la actividad', mensaje: a.descripcion, textoConfirmar: 'Retirar', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) run(api.sst.accionProgramaSsoma(p.id, 'quitar_actividad', { id: a.id, motivo: m })) }
  const ind = (oid) => p.indicadores.find((i) => i.objetivo === oid)
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <input type="number" className="input-esynapse w-24" value={anio} onChange={(e) => setAnio(Number(e.target.value))} />
        {p && <><Chip par={EST_PROGRAMA[p.estado]} /><span className="text-xs text-slate-500">Versión {p.version} · actualizado {fecha(p.fecha_actualizacion) || '—'}</span>
          <button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.sst.programaSsomaPdf(p.id))}><FileText className="h-3.5 w-3.5" /> PDF</button>
          {p.estado === 'aprobado' && puedeAprobar && <button className="btn-secondary !py-1 text-xs" onClick={reprogramar}>Reprogramar</button>}
          {editable && puedeAprobar && <button className="btn-primary !py-1 text-xs" onClick={aprobar}>Aprobar</button>}</>}
        <span className="ml-auto text-[11px] text-slate-500">{p?.estado === 'aprobado' ? 'Clic en un mes programado (P) para registrar su ejecución con evidencia.' : p ? 'Clic en las celdas para programar los meses.' : ''}</span>
      </div>
      {err && <Aviso texto={err} />}
      {p === null && (puedeCrear ? <div className="card-esynapse p-4 text-sm"><p className="mb-2 text-slate-500">No hay programa para {anio}.</p><button className="btn-primary" onClick={() => run(api.sst.crearProgramaSsoma({ anio, recursos: 'Recurso humano y económico' }))}><Plus className="h-4 w-4" /> Crear el programa {anio}</button></div> : <p className="text-sm text-slate-400">No hay programa para {anio}.</p>)}
      {p && (
        <>
          <div className="grid gap-2 md:grid-cols-3">{p.objetivos.map((o) => { const i = ind(o.id); return (
            <div key={o.id} className="card-esynapse p-2 text-xs"><p className="font-semibold">{o.codigo}</p><p className="text-slate-500">{o.descripcion}</p>
              <p className="mt-1">Avance a la fecha: {i?.avance == null ? '—' : <Chip par={[`${i.avance}%`, i.avance >= 90 ? VERDE : i.avance >= 70 ? AMBAR : ROJO]} extra={` · ${i.ejecutadas}/${i.programadas}`} />}</p></div>
          ) })}</div>
          <div className="card-esynapse overflow-x-auto">
            <table className="tabla-ficha w-full text-xs">
              <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">N°</th><th className="px-2">Actividad</th><th className="px-2">Responsable</th>{MESES.map((m) => <th key={m} className="w-9 px-0.5">{m}</th>)}<th className="px-2 text-center">Avance</th><th /></tr></thead>
              <tbody>
                {p.objetivos.map((o) => [
                  <tr key={`o${o.id}`} className="bg-slate-50 dark:bg-slate-800/40"><td colSpan={17} className="px-2 py-1 font-semibold">{o.codigo} {o.descripcion}{editable && puedeEditar && <button className="ml-2 p-0.5 text-slate-500" onClick={() => setObj({ id: o.id, codigo: o.codigo, descripcion: o.descripcion })}><Pencil className="inline h-3 w-3" /></button>}</td></tr>,
                  ...p.actividades.filter((a) => a.objetivo === o.id).map((a) => (
                    <tr key={a.id} className="border-b border-slate-100 dark:border-slate-800/60">
                      <td className="px-2 py-1">{a.orden}</td><td className="max-w-[22rem] px-2">{a.descripcion}</td><td className="px-2">{a.responsable_nombre || '—'}</td>
                      {MESES.map((_, k) => { const m = k + 1; const pr = a.meses.includes(m); const ej = a.meses_ejecutados.includes(m); const atr = pr && !ej && !futuro(m) && p.estado === 'aprobado'
                        return <td key={m} title={ej ? `Evidencia: ${a.evidencias[String(m)] || '—'}` : ''} onClick={() => celda(a, m)} className={`border-l border-slate-100 px-0.5 py-1 font-semibold dark:border-slate-800/60 ${puedeEditar && (editable || pr) ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800' : ''} ${ej ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300' : atr ? 'bg-red-500/10 text-red-600' : pr ? 'text-slate-600 dark:text-slate-300' : 'text-slate-300 dark:text-slate-700'}`}>{ej ? 'E' : pr ? 'P' : '·'}</td> })}
                      <td className="px-2 text-center">{a.avance}%</td>
                      <td className="whitespace-nowrap px-1">{editable && puedeEditar && <><button className="p-1 text-slate-500" onClick={() => setAct({ ...ACT, ...a, responsable: a.responsable || '' })}><Pencil className="h-3.5 w-3.5" /></button><button className="p-1 text-red-500" onClick={() => quitar(a)}><X className="h-3.5 w-3.5" /></button></>}</td>
                    </tr>
                  )),
                ])}
                {p.objetivos.length === 0 && <tr><td colSpan={17} className="py-6 text-slate-400">Registre los objetivos y sus actividades</td></tr>}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-slate-500">P programado · <span className="font-semibold text-emerald-600">E ejecutado</span> · <span className="text-red-600">rojo: programado y no ejecutado</span></p>
          {editable && puedeEditar && !act && !obj && <div className="flex gap-2"><button className="btn-secondary" onClick={() => setObj({ codigo: '', descripcion: '' })}><Plus className="h-4 w-4" /> Objetivo</button>{p.objetivos.length > 0 && <button className="btn-secondary" onClick={() => setAct({ ...ACT, objetivo: p.objetivos[0].id })}><Plus className="h-4 w-4" /> Actividad</button>}</div>}
          {obj && <div className="card-esynapse grid gap-3 p-3 text-xs md:grid-cols-6">
            <div><label className={lbl}>Código</label><input className={inp} placeholder="OSST3" value={obj.codigo} onChange={(e) => setObj({ ...obj, codigo: e.target.value })} /></div>
            <div className="md:col-span-4"><label className={lbl}>Objetivo</label><input className={inp} value={obj.descripcion} onChange={(e) => setObj({ ...obj, descripcion: e.target.value })} /></div>
            <div className="flex items-end gap-2"><button className="btn-secondary" onClick={() => setObj(null)}>Cancelar</button><button className="btn-primary" onClick={async () => { if (await run(api.sst.accionProgramaSsoma(p.id, 'objetivo', obj))) setObj(null) }}>Guardar</button></div>
          </div>}
          {act && <div className="card-esynapse grid gap-3 p-3 text-xs md:grid-cols-6">
            <div className="md:col-span-2"><label className={lbl}>Objetivo</label><select className={inp} value={String(act.objetivo)} onChange={(e) => setAct({ ...act, objetivo: Number(e.target.value) })}>{p.objetivos.map((o) => <option key={o.id} value={o.id}>{o.codigo}</option>)}</select></div>
            <div className="md:col-span-4"><label className={lbl}>Actividad</label><input className={inp} value={act.descripcion} onChange={(e) => setAct({ ...act, descripcion: e.target.value })} /></div>
            <div className="md:col-span-2"><label className={lbl}>Responsable (puesto)</label><select className={inp} value={String(act.responsable || '')} onChange={(e) => setAct({ ...act, responsable: e.target.value })}><option value="">— Elija —</option>{puestos.map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}</select></div>
            <div className="md:col-span-3"><label className={lbl}>Indicador</label><input className={inp} value={act.indicador} onChange={(e) => setAct({ ...act, indicador: e.target.value })} /></div>
            <div><label className={lbl}>Meta</label><input className={inp} value={act.meta} onChange={(e) => setAct({ ...act, meta: e.target.value })} /></div>
            <div className="md:col-span-6"><label className={lbl}>Meses programados</label><div className="flex flex-wrap gap-1">{MESES.map((m, k) => <label key={m} className="flex items-center gap-0.5"><input type="checkbox" className="accent-esynapse-600" checked={act.meses.includes(k + 1)} onChange={() => setAct({ ...act, meses: act.meses.includes(k + 1) ? act.meses.filter((x) => x !== k + 1) : [...act.meses, k + 1] })} />{m}</label>)}</div></div>
            <div className="flex justify-end gap-2 md:col-span-6"><button className="btn-secondary" onClick={() => setAct(null)}>Cancelar</button><button className="btn-primary" onClick={async () => { const { id, objetivo, descripcion, responsable, meta, indicador, meses } = act; if (await run(api.sst.accionProgramaSsoma(p.id, 'actividad', { id, objetivo, descripcion, responsable: responsable || null, meta, indicador, meses }))) setAct(null) }}>Guardar</button></div>
          </div>}
          <div className="grid gap-2 text-xs md:grid-cols-3">
            <div className="card-esynapse p-2"><p className="text-slate-500">Elaborado</p><p>{p.elaborado?.nombre ? `${p.elaborado.nombre} · ${p.elaborado.cargo || ''}` : '—'}</p></div>
            <div className="card-esynapse p-2"><p className="text-slate-500">Revisado</p><p>{p.revisado?.nombre ? `${p.revisado.nombre} · ${p.revisado.cargo || ''}` : '—'}</p></div>
            <div className="card-esynapse p-2"><p className="text-slate-500">Aprobado</p>{(p.aprobado || []).length ? p.aprobado.map((a, i) => <p key={i}>{a.nombre} · {a.cargo} · {fecha(a.fecha)}</p>) : '—'}</div>
          </div>
        </>
      )}
      {aprob && p && <FirmaComite titulo={`Aprobación del Programa SSOMA ${p.anio} (versión ${p.version}) por el Comité de SST`} cargar={api.sst.firmantesSsoma}
        enviar={(datos) => api.sst.accionProgramaSsoma(p.id, 'aprobar', datos)} enviarPapel={(fd) => api.sst.aprobarSsomaPapel(p.id, fd)}
        onCerrar={() => setAprob(false)} alAprobar={(r) => { setP(r); setAprob(false) }} />}
    </div>
  )
}
