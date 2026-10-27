import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowDown, ArrowUp, CalendarDays, ClipboardList, ExternalLink, FileText, GraduationCap, History, KeyRound, ListChecks, Pencil, Plus, Search, ShieldCheck, Users, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import Pestanas from '../components/ui/Pestanas.jsx'
import { Vistas } from '../components/NavModulo.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora, hoy as hoyLocal } from '../lib/fecha.js'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
const hoy = () => hoyLocal()
const ANIO = new Date().getFullYear()

// Estados (regla 10): gris programado/registro · ámbar reprogramado/pendiente · azul en proceso ·
// verde realizado/aprobado/cerrado · rojo atrasado/vencido/desaprobado/anulado.
const GRIS = 'bg-slate-500/15 text-slate-500'
const AMBAR = 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
const AZUL = 'bg-blue-500/15 text-blue-600 dark:text-blue-400'
const VERDE = 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
const ROJO = 'bg-red-500/15 text-red-600 dark:text-red-400'
const EST_ITEM = { programado: ['Programado', GRIS], reprogramado: ['Reprogramado', AMBAR], atrasado: ['Atrasado', ROJO], realizado: ['Realizado', VERDE], cancelado: ['Cancelado', GRIS] }
const EST_APROB = { aprobado: ['Aprobado por el Comité', VERDE], pendiente: ['Pendiente de aprobación', AMBAR], sin_aprobar: ['Sin aprobar', ROJO], historico: ['Histórico', GRIS] }
const EST_SESION = { en_registro: ['En registro', GRIS], cerrada: ['Cerrada', VERDE], anulada: ['Anulada', ROJO] }
const EST_EFICACIA = { pendiente: ['Eficacia pendiente', GRIS], por_vencer: ['Eficacia por vencer', AMBAR], vencida: ['Eficacia vencida', ROJO], evaluada: ['Eficacia evaluada', VERDE] }
const EST_PARTE = { en_registro: ['En registro', GRIS], aprobada: ['Aprobada', VERDE], desaprobada: ['Desaprobada', ROJO] }
const EST_IND = { completa: ['Completa', VERDE], en_proceso: ['En proceso', AZUL], sin_induccion: ['Sin inducción', ROJO], anulada: ['Anulada', GRIS] }
const CERT = { aprobacion: ['Aprobación', VERDE], participacion: ['Participación', GRIS] }
const METODO = { usuario: 'Usuario', pin: 'PIN', papel: 'Papel', carga: 'Formato original' }
// Etiqueta de norma por tipo (regla 9): SST rojo, Ambiental verde, Metrología ámbar, Calidad/SIG azul.
const COLOR_TIPO = { sst: ROJO, ambiental: VERDE, metrologia: AMBAR, calidad: AZUL, sig: AZUL, rrhh: GRIS, otros: GRIS }

const Chip = ({ par, extra }) => (par ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{par[0]}{extra}</span> : null)
function Aviso({ texto }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [texto])
  return <p ref={ref} className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p>
}
const Dato = ({ etiqueta, valor }) => <p><strong className="text-slate-700 dark:text-slate-200">{etiqueta}:</strong> {valor || '—'}</p>
const useTrabajadores = () => {
  const [t, setT] = useState([])
  useEffect(() => { api.org.trabajadores().then((x) => setT(x.filter((w) => w.estado === 'activo'))).catch(() => {}) }, [])
  return t
}

/* Credencial de la persona que firma en pantalla (regla de firma): contraseña de su usuario o PIN personal. */
function Credencial({ forma, valor, onChange }) {
  const v = valor || {}
  const pin = (k, ph) => <input type="password" inputMode="numeric" autoComplete="off" placeholder={ph} className={`${inp} !py-1 text-xs`} value={v[k] || ''} onChange={(e) => onChange({ ...v, [k]: e.target.value.replace(/\D/g, '').slice(0, 6) })} />
  if (forma === 'usuario') return <input type="password" autoComplete="off" placeholder="Contraseña de su usuario" className={`${inp} !py-1 text-xs`} value={v.clave_trabajador || ''} onChange={(e) => onChange({ ...v, clave_trabajador: e.target.value })} />
  if (forma === 'activo') return pin('pin', 'PIN')
  if (forma === 'bloqueado') return <span className="text-[11px] text-red-600">PIN bloqueado: restablézcalo (SST › EPP › Por trabajador) o use la lista en papel</span>
  return <div className="flex gap-1">{pin('pin_nuevo', 'Nuevo PIN')}{pin('pin_confirmacion', 'Confirme')}</div>
}

export default function Capacitacion() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const [pestana, setPestana] = useState('programa')
  const [cat, setCat] = useState(null)
  const [anio, setAnio] = useState(ANIO)
  const [error, setError] = useState('')
  const [irSesion, setIrSesion] = useState(null)
  const [areas, setAreas] = useState([])
  const [puestos, setPuestos] = useState([])
  useEffect(() => {
    api.capacitacion.catalogos().then(setCat).catch(() => {})
    api.org.areas().then(setAreas).catch(() => {}); api.org.puestos().then(setPuestos).catch(() => {})
  }, [])
  const abrirPdf = async (promesa) => {
    setError('')
    try { const url = URL.createObjectURL(await promesa); window.open(url, '_blank'); setTimeout(() => URL.revokeObjectURL(url), 60000) } catch (e) { setError(e.message) }
  }
  const comun = { cat, anio, setAnio, areas, puestos, confirmar, setError, abrirPdf, puedeCrear: tienePermiso('capacitacion', 'crear'), puedeEditar: tienePermiso('capacitacion', 'editar'), puedeAprobar: tienePermiso('capacitacion', 'aprobar'), puedeEliminar: tienePermiso('capacitacion', 'eliminar') }
  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <TituloModulo seccion="Talento humano" titulo="Capacitación e inducción" descripcion="Programa anual de capacitación aprobado por el Comité de SST, listas de asistencia, eficacia de las capacitaciones e inducción del personal." />
        <Pestanas opciones={[['programa', 'Programa anual', CalendarDays], ['sesiones', 'Listas de asistencia', ClipboardList], ['induccion', 'Inducción', GraduationCap], ['trabajadores', 'Por trabajador', Users], ['plantillas', 'Contenido de la inducción', ListChecks]]} valor={pestana} onChange={(k) => { setError(''); setPestana(k) }} />
      </div>
      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      {pestana === 'programa' && <Programa {...comun} registrarSesion={(item) => { setIrSesion(item); setPestana('sesiones') }} />}
      {pestana === 'sesiones' && <Sesiones {...comun} irSesion={irSesion} limpiarIr={() => setIrSesion(null)} />}
      {pestana === 'induccion' && <Inducciones {...comun} />}
      {pestana === 'trabajadores' && <PorTrabajador {...comun} />}
      {pestana === 'plantillas' && <Plantillas {...comun} />}
    </div>
  )
}

/* ============================================================================== programa anual */
const ITEM_VACIO = { tema: '', tipo: 'sst', responsable: '', externo: false, alcance: 'todos', areas: [], puestos: [], dirigido_texto: '', fecha_programada: '', horas: 1 }

function Programa({ cat, anio, setAnio, areas, puestos, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeAprobar, registrarSesion }) {
  const [p, setP] = useState(undefined)
  const [form, setForm] = useState(null)
  const [aprob, setAprob] = useState(false)
  const [filtro, setFiltro] = useState('todas')
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.capacitacion.programa(anio).then(setP).catch((e) => setError(e.message)), [anio, setError])
  useEffect(() => { setP(undefined); cargar() }, [cargar])
  const run = async (prom) => { setErr(''); try { setP(await prom); return true } catch (e) { setErr(e.message); return false } }
  const editable = p && !p.historico
  const reprogramar = async (i) => {
    const f = await confirmar({ titulo: 'Reprogramar', mensaje: `${i.tema} — fecha vigente ${fecha(i.fecha_vigente)}.`, textoConfirmar: 'Siguiente', entrada: { etiqueta: 'Nueva fecha (AAAA-MM-DD)', obligatorio: true, valorInicial: i.fecha_vigente } })
    if (f === null) return
    const m = await confirmar({ titulo: 'Motivo de la reprogramación', mensaje: 'Queda como RP en el programa.', textoConfirmar: 'Reprogramar', entrada: { etiqueta: 'Motivo', obligatorio: true } })
    if (m !== null) run(api.capacitacion.accionPrograma(p.id, 'reprogramar', { id: i.id, fecha: f, motivo: m }))
  }
  const cancelar = async (i) => { const m = await confirmar({ titulo: 'Cancelar la capacitación', mensaje: i.tema, textoConfirmar: 'Cancelar capacitación', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) run(api.capacitacion.accionPrograma(p.id, 'cancelar', { id: i.id, motivo: m })) }
  const guardar = async () => {
    const { id, tema, tipo, responsable, externo, alcance, areas: ar, puestos: pu, dirigido_texto, fecha_programada, horas } = form
    if (await run(api.capacitacion.accionPrograma(p.id, 'item', { id, tema, tipo, responsable, externo, alcance, areas: ar, puestos: pu, dirigido_texto, fecha_programada, horas }))) setForm(null)
  }
  const items = (p?.items || []).filter((i) => filtro === 'todas' || (filtro === 'pendientes' ? !['realizado', 'cancelado'].includes(i.estado) : i.tipo === 'sst'))
  const ind = p?.indicadores
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select className="input-esynapse w-28" value={anio} onChange={(e) => setAnio(Number(e.target.value))}>{[...new Set([...(cat?.anios || []), ANIO, ANIO + 1])].sort().map((a) => <option key={a} value={a}>{a}</option>)}</select>
        {p && <><Chip par={EST_APROB[p.estado_aprobacion]} />{p.aprobacion?.fecha && <span className="text-xs text-slate-500">aprobado el {fecha(p.aprobacion.fecha)}</span>}
          <button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.capacitacion.programaPdf(p.id))}><FileText className="h-3.5 w-3.5" /> PDF</button>
          {editable && puedeAprobar && p.estado_aprobacion !== 'aprobado' && <button className="btn-secondary !py-1 text-xs" onClick={() => setAprob(true)}><ShieldCheck className="h-3.5 w-3.5" /> Aprobación del Comité</button>}
          {editable && puedeEditar && <button className="btn-primary ml-auto !py-1 text-xs" onClick={() => { setErr(''); setForm({ ...ITEM_VACIO, fecha_programada: `${anio}-${String(new Date().getMonth() + 1).padStart(2, '0')}-15` }) }}><Plus className="h-3.5 w-3.5" /> Capacitación</button>}</>}
      </div>
      {err && <Aviso texto={err} />}
      {p === null && (puedeCrear ? <div className="card-esynapse p-4 text-sm"><p className="mb-2 text-slate-500">No hay programa de capacitación para {anio}.</p><button className="btn-primary" onClick={() => run(api.capacitacion.crearPrograma(anio))}><Plus className="h-4 w-4" /> Crear el programa {anio}</button></div> : <p className="text-sm text-slate-400">No hay programa para {anio}.</p>)}
      {p && ind && (
        <>
          <div className="grid gap-3 md:grid-cols-5">
            {[['Programadas', ind.programadas], ['Realizadas', ind.realizadas], ['Avance del año', ind.avance == null ? '—' : `${ind.avance} %`], ['Avance a la fecha', ind.avance_a_la_fecha == null ? '—' : `${ind.avance_a_la_fecha} %`], ['Capacitaciones de SST realizadas', `${ind.sst_realizadas}`]].map(([n, v]) => (
              <div key={n} className="card-esynapse p-3"><p className="text-[11px] text-slate-500">{n}</p><p className="text-2xl font-semibold">{v}</p>{n.startsWith('Capacitaciones de SST') && <p className={`text-[11px] ${ind.sst_realizadas >= 4 ? 'text-emerald-600' : 'text-amber-600'}`}>Mínimo legal: 4 al año</p>}</div>
            ))}
          </div>
          {p.estado_aprobacion === 'pendiente' && <p className="rounded-lg bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300">El programa cambió después de su aprobación del {fecha(p.aprobacion?.fecha)}: el Comité de SST debe aprobarlo de nuevo.</p>}
          <Vistas opciones={[['todas', 'Todas'], ['pendientes', 'Pendientes'], ['sst', 'Solo SST']]} valor={filtro} onChange={setFiltro} />
          <div className="card-esynapse overflow-x-auto">
            <table className="tabla-sig min-w-[1000px]">
              <thead><tr><th>Capacitación</th><th className="text-center">Tipo</th><th>Responsable</th><th>Personal a capacitar</th><th className="text-right">Programada</th><th className="text-right">Realizada</th><th className="text-right">Horas</th><th className="text-center">Estado</th><th className="text-center">V°B°</th><th /></tr></thead>
              <tbody>
                {items.map((i) => (
                  <tr key={i.id} className={i.cancelado ? 'opacity-50' : ''}>
                    <td className="max-w-sm"><span className="line-clamp-2" title={i.tema}>{i.tema}</span>{i.reprogramaciones?.length > 0 && <span className="block text-[11px] text-amber-600">RP: {i.reprogramaciones.map((r) => `${fecha(r.de)} → ${r.a ? fecha(r.a) : 'sin fecha'} (${r.motivo})`).join(' · ')}</span>}</td>
                    <td className="text-center"><Chip par={[i.tipo_display, COLOR_TIPO[i.tipo]]} /></td>
                    <td>{i.responsable || '—'}</td>
                    <td className="max-w-[12rem] text-slate-500"><span className="line-clamp-2" title={i.dirigido}>{i.dirigido}</span></td>
                    <td className="whitespace-nowrap text-right">{fecha(i.fecha_vigente)}</td>
                    <td className="whitespace-nowrap text-right">{i.fecha_realizada ? fecha(i.fecha_realizada) : '—'}</td>
                    <td className="text-right">{Number(i.horas)}</td>
                    <td className="text-center"><Chip par={EST_ITEM[i.estado]} /></td>
                    <td className="text-center text-xs">{i.vb || '—'}</td>
                    <td className="whitespace-nowrap">{editable && !['realizado', 'cancelado'].includes(i.estado) && <span className="flex gap-1">
                      {puedeCrear && <button className="text-[11px] text-esynapse-500 underline" onClick={() => registrarSesion(i)}>Registrar asistencia</button>}
                      {puedeEditar && <><button className="p-1 text-slate-500" title="Corregir" onClick={() => { setErr(''); setForm({ ...ITEM_VACIO, ...i }) }}><Pencil className="h-3.5 w-3.5" /></button><button className="text-[11px] text-slate-500 underline" onClick={() => reprogramar(i)}>Reprogramar</button><button className="p-1 text-red-500" title="Cancelar" onClick={() => cancelar(i)}><X className="h-3.5 w-3.5" /></button></>}</span>}
                      {i.sesiones?.length > 0 && <span className="block text-[11px] text-slate-500">{i.sesiones.map((s) => s.codigo).join(', ')}</span>}</td>
                  </tr>
                ))}
                {items.length === 0 && <tr><td colSpan={10} className="py-8 text-center text-slate-400">Sin capacitaciones</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="grid gap-2 text-xs md:grid-cols-2">
            <div className="card-esynapse p-3"><p className="text-slate-500">Elaborado</p><p>{p.elaborado?.nombre ? `${p.elaborado.nombre} · ${p.elaborado.cargo || ''}` : '—'}</p></div>
            <div className="card-esynapse p-3"><p className="text-slate-500">Realizado y aprobado por (Comité de SST)</p>{(p.aprobacion?.firmas || []).length ? p.aprobacion.firmas.map((f, k) => <p key={k}>{f.nombre} · {f.cargo} <span className="text-slate-400">({METODO[f.metodo] || f.metodo})</span></p>) : '—'}</div>
          </div>
        </>
      )}
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Corregir capacitación' : 'Nueva capacitación del programa'} onCerrar={() => setForm(null)} ancho="max-w-3xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div><label className={lbl}>Capacitación</label><input className={inp} value={form.tema} onChange={(e) => setForm({ ...form, tema: e.target.value })} /></div>
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>Tipo</label><select className={inp} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{(cat?.tipos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div className="md:col-span-2"><label className={lbl}>Responsable de la capacitación</label><input className={inp} value={form.responsable} onChange={(e) => setForm({ ...form, responsable: e.target.value })} /></div>
              <label className="flex items-end gap-1 pb-2 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={form.externo} onChange={(e) => setForm({ ...form, externo: e.target.checked })} /> Externa</label>
              <div><label className={lbl}>Fecha programada</label><input type="date" className={inp} value={form.fecha_programada} onChange={(e) => setForm({ ...form, fecha_programada: e.target.value })} /></div>
              <div><label className={lbl}>Horas</label><input type="number" step="0.25" min="0" className={inp} value={form.horas} onChange={(e) => setForm({ ...form, horas: e.target.value })} /></div>
              <div className="md:col-span-2"><label className={lbl}>Personal a capacitar</label><select className={inp} value={form.alcance} onChange={(e) => setForm({ ...form, alcance: e.target.value })}>{(cat?.alcances || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
            </div>
            {form.alcance === 'areas' && <div><label className={lbl}>Áreas (incluye sus dependencias)</label><div className="grid max-h-40 gap-1 overflow-y-auto rounded border border-slate-200 p-2 text-xs md:grid-cols-3 dark:border-slate-800">{areas.map((a) => <label key={a.id} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" checked={form.areas.includes(a.id)} onChange={() => setForm({ ...form, areas: form.areas.includes(a.id) ? form.areas.filter((x) => x !== a.id) : [...form.areas, a.id] })} />{a.nombre}</label>)}</div></div>}
            {form.alcance === 'puestos' && <div><label className={lbl}>Puestos</label><div className="grid max-h-40 gap-1 overflow-y-auto rounded border border-slate-200 p-2 text-xs md:grid-cols-3 dark:border-slate-800">{puestos.map((a) => <label key={a.id} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" checked={form.puestos.includes(a.id)} onChange={() => setForm({ ...form, puestos: form.puestos.includes(a.id) ? form.puestos.filter((x) => x !== a.id) : [...form.puestos, a.id] })} />{a.nombre}</label>)}</div></div>}
            {(form.alcance === 'otros' || form.dirigido_texto) && <div><label className={lbl}>Descripción del grupo (se imprime en el programa)</label><input className={inp} value={form.dirigido_texto} onChange={(e) => setForm({ ...form, dirigido_texto: e.target.value })} /></div>}
            {p?.aprobado_en && <p className="text-[11px] text-amber-600">Agregar o corregir capacitaciones deja el programa pendiente de una nueva aprobación del Comité. Para cambiar solo la fecha use «Reprogramar».</p>}
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
      {aprob && p && <AprobacionComite programa={p} onCerrar={() => setAprob(false)} alAprobar={(r) => { setP(r); setAprob(false) }} />}
    </div>
  )
}

/* Aprobación del programa por el Comité de SST: cada titular firma con su usuario o PIN, o se adjunta el acta. */
function AprobacionComite({ programa, onCerrar, alAprobar }) {
  const [d, setD] = useState(null)
  const [modo, setModo] = useState('pantalla')
  const [f, setF] = useState({ fecha: hoy(), observaciones: '', archivo: null, password: '' })
  const [firmas, setFirmas] = useState({})
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.capacitacion.firmantes().then((x) => { setD(x); setFirmas((prev) => Object.fromEntries(x.titulares.map((t) => [t.id, prev[t.id] || { firma: true }]))) }).catch((e) => setErr(e.message)), [])
  useEffect(() => { cargar() }, [cargar])
  const firmantes = (d?.titulares || []).filter((t) => firmas[t.id]?.firma)
  const enviar = async () => {
    setErr('')
    if (firmantes.length < (d?.quorum || 1)) { setErr(`Se requiere la firma de al menos ${d?.quorum} titular(es).`); return }
    try {
      let r
      if (modo === 'papel') {
        if (!f.archivo) { setErr('Adjunte el acta firmada.'); return }
        const fd = new FormData(); fd.append('fecha', f.fecha); fd.append('observaciones', f.observaciones); fd.append('firmantes', JSON.stringify(firmantes.map((t) => t.id))); fd.append('archivo', f.archivo); fd.append('password', f.password)
        r = await api.capacitacion.aprobarProgramaPapel(programa.id, fd)
      } else {
        const lista = firmantes.map((t) => { const c = firmas[t.id] || {}; return { miembro: t.id, clave: c.clave_trabajador, pin: c.pin, pin_nuevo: c.pin_nuevo, pin_confirmacion: c.pin_confirmacion } })
        r = await api.capacitacion.accionPrograma(programa.id, 'aprobar', { fecha: f.fecha, observaciones: f.observaciones, firmas: lista })
      }
      alAprobar(r)
    } catch (e) { setErr(e.message); cargar() }
  }
  return (
    <Modal abierto titulo={`Aprobación del programa de capacitación ${programa.anio} por el Comité de SST`} onCerrar={onCerrar} ancho="max-w-4xl">
      <div className="space-y-3 text-sm">
        {d && !d.titulares.length && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600">El comité vigente no tiene titulares registrados (SST › Participación › Comité de SST).</p>}
        <div className="grid gap-3 md:grid-cols-3"><div><label className={lbl}>Fecha de aprobación</label><input type="date" className={inp} value={f.fecha} onChange={(e) => setF({ ...f, fecha: e.target.value })} /></div></div>
        <div className="flex gap-4 text-xs"><label className="flex items-center gap-1"><input type="radio" checked={modo === 'pantalla'} onChange={() => setModo('pantalla')} /> Firman en pantalla</label><label className="flex items-center gap-1"><input type="radio" checked={modo === 'papel'} onChange={() => setModo('papel')} /> Acta firmada en papel (adjunta)</label></div>
        <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
          <p className="mb-1 font-semibold">Realizado y aprobado por — Comité {d?.comite || ''} <span className="font-normal text-slate-500">(se requieren {d?.quorum || 0} de {d?.titulares.length || 0} titulares)</span></p>
          <table className="w-full"><tbody>{(d?.titulares || []).map((t) => (
            <tr key={t.id} className="border-t border-slate-100 dark:border-slate-800/60">
              <td className="w-8 py-1"><input type="checkbox" className="accent-esynapse-600" checked={Boolean(firmas[t.id]?.firma)} onChange={(e) => setFirmas({ ...firmas, [t.id]: { ...firmas[t.id], firma: e.target.checked } })} /></td>
              <td>{t.nombre}<span className="block text-[10px] text-slate-500">{t.cargo}</span></td>
              {modo === 'pantalla' && <td className="w-72">{firmas[t.id]?.firma ? <Credencial forma={t.firma} valor={firmas[t.id]} onChange={(v) => setFirmas({ ...firmas, [t.id]: { ...v, firma: true } })} /> : '—'}</td>}
            </tr>
          ))}</tbody></table>
        </div>
        {modo === 'papel' && <div className="grid gap-3 md:grid-cols-2"><div><label className={lbl}>Acta firmada (escaneada)</label><input type="file" className="text-xs" onChange={(e) => setF({ ...f, archivo: e.target.files[0] || null })} /></div><div><label className={lbl}>Su contraseña (quien registra)</label><input type="password" autoComplete="current-password" className={inp} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></div></div>}
        <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} value={f.observaciones} onChange={(v) => setF({ ...f, observaciones: v })} /></div>
        {err && <Aviso texto={err} />}
        <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={onCerrar}>Cerrar</button><button className="btn-primary" onClick={enviar}>Registrar la aprobación</button></div>
      </div>
    </Modal>
  )
}

/* ========================================================================== listas de asistencia */
const SESION_VACIA = { item: '', tipo_actividad: 'capacitacion', temas: [], otros_temas: '', tema_tratado: '', capacitador: '', externo: false, entidad: '', fecha: hoy(), hora_desde: '', hora_hasta: '', duracion_horas: '', material_entregado: '', con_evaluacion: false, observaciones: '' }
const TEMA_DE_TIPO = { sst: 'seguridad', ambiental: 'ambiental', calidad: 'calidad', sig: 'calidad', metrologia: 'metrologia' }

function Sesiones({ cat, anio, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeAprobar, puedeEliminar, irSesion, limpiarIr }) {
  const trabajadores = useTrabajadores()
  const [items, setItems] = useState([])
  const [estado, setEstado] = useState('')
  const [buscar, setBuscar] = useState('')
  const [programa, setPrograma] = useState(null)
  const [form, setForm] = useState(null)
  const [d, setD] = useState(null)
  const [agregar, setAgregar] = useState([])
  const [firmando, setFirmando] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => { const q = new URLSearchParams({ anio }); if (estado) q.set('estado', estado); if (buscar) q.set('buscar', buscar); return api.capacitacion.sesiones(`?${q}`).then(setItems).catch((e) => setError(e.message)) }, [anio, estado, buscar, setError])
  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { api.capacitacion.programa(anio).then(setPrograma).catch(() => {}) }, [anio])
  useEffect(() => {
    if (!irSesion) return
    setErr(''); setD(null)
    setForm({ ...SESION_VACIA, item: irSesion.id, tema_tratado: irSesion.tema, capacitador: irSesion.responsable, externo: irSesion.externo, duracion_horas: irSesion.horas, temas: TEMA_DE_TIPO[irSesion.tipo] ? [TEMA_DE_TIPO[irSesion.tipo]] : [] })
    limpiarIr()
  }, [irSesion, limpiarIr])
  const pendientes = (programa?.items || []).filter((i) => !['realizado', 'cancelado'].includes(i.estado))
  // Duración calculada con Desde y Hasta (el servidor aplica la misma regla al guardar)
  const minutos = (h) => { const [hh, mm] = (h || '').slice(0, 5).split(':').map(Number); return hh * 60 + mm }
  const ambasHoras = !!(form?.hora_desde && form?.hora_hasta)
  const difMin = ambasHoras ? minutos(form.hora_hasta) - minutos(form.hora_desde) : 0
  const durCalc = ambasHoras && difMin > 0 ? Math.round((difMin / 60) * 100) / 100 : null
  const horasInvalidas = ambasHoras && difMin <= 0
  const abrir = async (id) => { setErr(''); setForm(null); setFirmando(null); setAgregar([]); setD(await api.capacitacion.sesion(id)) }
  const crear = async () => {
    setErr('')
    try {
      const datos = { ...form, item: form.item || null, hora_desde: form.hora_desde || null, hora_hasta: form.hora_hasta || null, duracion_horas: durCalc ?? (form.duracion_horas || 0) }
      const r = form.id ? await api.capacitacion.editarSesion(form.id, datos) : await api.capacitacion.crearSesion(datos)
      setForm(null); setD(r); cargar()
    } catch (e) { setErr(e.message) }
  }
  const accion = async (nombre, datos) => { setErr(''); try { setD(await api.capacitacion.accionSesion(d.id, nombre, datos)); cargar(); return true } catch (e) { setErr(e.message); return false } }
  const subir = async (nombre, campos) => { setErr(''); const fd = new FormData(); Object.entries(campos).forEach(([k, v]) => v != null && fd.append(k, v)); try { setD(await api.capacitacion.subirSesion(d.id, nombre, fd)); cargar() } catch (e) { setErr(e.message) } }
  const cerrar = async () => { const c = await confirmar({ titulo: 'Cerrar la lista de asistencia', mensaje: 'Firma como responsable del registro. La lista queda de solo lectura y la capacitación del programa, realizada.', textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } }); if (c !== null) accion('cerrar', { password: c }) }
  const anular = async () => { const m = await confirmar({ titulo: 'Anular la lista', mensaje: 'Solo si se registró por error.', textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) accion('anular', { motivo: m }) }
  const [efi, setEfi] = useState(null)
  const evaluar = async () => { const c = await confirmar({ titulo: 'Evaluación de la eficacia', mensaje: `Resultado: ${efi.resultado === 'eficaz' ? 'Eficaz' : 'No eficaz'}.`, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } }); if (c !== null && await accion('eficacia', { ...efi, password: c })) setEfi(null) }
  const enLista = new Set((d?.asistentes || []).map((a) => a.trabajador))
  const abierta = d?.estado === 'en_registro'
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-60 pl-9" placeholder="Código, tema o capacitador…" value={buscar} onChange={(e) => setBuscar(e.target.value)} /></div>
        <select className="input-esynapse w-40" value={estado} onChange={(e) => setEstado(e.target.value)}><option value="">Todo estado</option>{Object.entries(EST_SESION).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select>
        <span className="text-xs text-slate-500">Año {anio}</span>
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setD(null); setForm({ ...SESION_VACIA }) }}><Plus className="h-4 w-4" /> Nueva lista de asistencia</button>}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig min-w-[900px]">
          <thead><tr><th>Código</th><th className="text-right">Fecha</th><th className="text-center">Tipo</th><th>Tema tratado</th><th>Capacitador</th><th className="text-right">Asistentes</th><th className="text-center">Estado</th><th className="text-center">Eficacia</th></tr></thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.id} className={`fila ${s.estado === 'anulada' ? 'opacity-50' : ''}`} onClick={() => abrir(s.id)}>
                <td className="whitespace-nowrap font-semibold text-esynapse-700 dark:text-esynapse-300">{s.codigo}</td><td className="whitespace-nowrap text-right">{fecha(s.fecha)}</td>
                <td className="text-center"><Chip par={[s.tipo_actividad_display, GRIS]} /></td><td className="max-w-sm"><span className="line-clamp-2">{s.tema_tratado}</span></td><td>{s.capacitador}</td>
                <td className="text-right">{s.asistentes.length}</td><td className="text-center"><Chip par={EST_SESION[s.estado]} /></td><td className="text-center">{s.estado_eficacia ? <Chip par={EST_EFICACIA[s.estado_eficacia]} /> : '—'}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-center text-slate-400">Sin listas de asistencia en {anio}</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Corregir la lista de asistencia' : 'Nueva lista de asistencia'} onCerrar={() => setForm(null)} ancho="max-w-4xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div><label className={lbl}>Capacitación del programa (opcional: charlas, simulacros o reuniones pueden ir sin programa)</label><select className={inp} value={String(form.item || '')} onChange={(e) => { const i = pendientes.find((x) => String(x.id) === e.target.value); setForm({ ...form, item: e.target.value, ...(i ? { tema_tratado: i.tema, capacitador: i.responsable, externo: i.externo, duracion_horas: i.horas, temas: TEMA_DE_TIPO[i.tipo] ? [TEMA_DE_TIPO[i.tipo]] : form.temas } : {}) }) }}><option value="">— Fuera del programa —</option>{pendientes.map((i) => <option key={i.id} value={i.id}>{fecha(i.fecha_vigente)} · {i.tema}</option>)}{form.item && !pendientes.some((i) => String(i.id) === String(form.item)) && <option value={form.item}>(capacitación actual)</option>}</select></div>
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>Tipo</label><select className={inp} value={form.tipo_actividad} onChange={(e) => setForm({ ...form, tipo_actividad: e.target.value })}>{(cat?.tipos_actividad || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
              <div><label className={lbl}>Desde</label><input type="time" className={inp} value={(form.hora_desde || '').slice(0, 5)} onChange={(e) => setForm({ ...form, hora_desde: e.target.value })} /></div>
              <div><label className={lbl}>Hasta</label><input type="time" className={inp} value={(form.hora_hasta || '').slice(0, 5)} onChange={(e) => setForm({ ...form, hora_hasta: e.target.value })} /></div>
              <div className="md:col-span-2"><label className={lbl}>Capacitador</label><input className={inp} value={form.capacitador} onChange={(e) => setForm({ ...form, capacitador: e.target.value })} /></div>
              <div><label className={lbl}>Duración (horas){durCalc !== null && <span className="ml-1 text-[10px] text-slate-400">· calculada</span>}</label><input type="number" step="0.25" min="0" className={`${inp} ${durCalc !== null ? 'opacity-80' : ''}`} readOnly={durCalc !== null} title={durCalc !== null ? 'Se calcula con las horas Desde y Hasta' : 'Indíquela o registre Desde y Hasta para calcularla'} value={durCalc !== null ? durCalc : form.duracion_horas} onChange={(e) => setForm({ ...form, duracion_horas: e.target.value })} />{horasInvalidas && <p className="mt-0.5 text-[11px] text-red-500">«Hasta» debe ser posterior a «Desde».</p>}</div>
              <label className="flex items-end gap-1 pb-2 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={form.externo} onChange={(e) => setForm({ ...form, externo: e.target.checked })} /> Externa</label>
              {form.externo && <div className="md:col-span-2"><label className={lbl}>Entidad capacitadora</label><input className={inp} value={form.entidad} onChange={(e) => setForm({ ...form, entidad: e.target.value })} /></div>}
            </div>
            <div><label className={lbl}>Temas</label><div className="flex flex-wrap gap-3 text-xs">{(cat?.temas || []).map(([k, n]) => <label key={k} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" checked={form.temas.includes(k)} onChange={() => setForm({ ...form, temas: form.temas.includes(k) ? form.temas.filter((x) => x !== k) : [...form.temas, k] })} />{n}</label>)}{form.temas.includes('otros') && <input className={`${inp} !py-1 w-48 text-xs`} placeholder="Otros temas" value={form.otros_temas} onChange={(e) => setForm({ ...form, otros_temas: e.target.value })} />}</div></div>
            <div><label className={lbl}>Tema tratado</label><CampoAmpliable multilinea rows={2} value={form.tema_tratado} onChange={(v) => setForm({ ...form, tema_tratado: v })} /></div>
            <div className="grid gap-3 md:grid-cols-2"><div><label className={lbl}>Material entregado</label><input className={inp} value={form.material_entregado} onChange={(e) => setForm({ ...form, material_entregado: e.target.value })} /></div>
              <label className="flex items-end gap-1 pb-2 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={form.con_evaluacion} onChange={(e) => setForm({ ...form, con_evaluacion: e.target.checked })} /> Con evaluación (nota de 0 a 20; aprobatoria 14)</label></div>
            <div><label className={lbl}>Observaciones / anotaciones</label><CampoAmpliable multilinea rows={2} value={form.observaciones} onChange={(v) => setForm({ ...form, observaciones: v })} /></div>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={crear}>{form.id ? 'Guardar' : 'Crear y registrar asistentes'}</button></div>
          </div>
        )}
      </Modal>

      <Modal abierto={Boolean(d) && !form} titulo={d ? `${d.codigo} — Lista de asistencia` : ''} onCerrar={() => { setD(null); setFirmando(null); setEfi(null) }} panel>
        {d && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2"><Chip par={EST_SESION[d.estado]} />{d.estado_eficacia && <Chip par={EST_EFICACIA[d.estado_eficacia]} extra={d.estado_eficacia !== 'evaluada' ? ` · vence ${fecha(d.eficacia_vence)}` : ''} />}
              <button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => abrirPdf(api.capacitacion.sesionPdf(d.id))}><FileText className="h-3.5 w-3.5" /> Lista de asistencia (PDF)</button>
              {abierta && puedeEditar && <button className="btn-secondary !py-1 text-xs" onClick={() => { setErr(''); setForm({ ...SESION_VACIA, ...d, item: d.item || '' }) }}><Pencil className="h-3.5 w-3.5" /> Corregir datos</button>}</div>
            {d.estado === 'anulada' && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600">Anulada: {d.motivo_anulacion}</p>}
            <div className="grid gap-x-6 gap-y-1 text-xs md:grid-cols-3">
              <Dato etiqueta="Tipo" valor={d.tipo_actividad_display} /><Dato etiqueta="Fecha" valor={`${fecha(d.fecha)} ${d.hora_desde ? `· ${d.hora_desde.slice(0, 5)}–${(d.hora_hasta || '').slice(0, 5)}` : ''}`} /><Dato etiqueta="Duración" valor={`${Number(d.duracion_horas)} h`} />
              <Dato etiqueta="Capacitador" valor={`${d.capacitador}${d.externo && d.entidad ? ` (${d.entidad})` : ''}`} /><Dato etiqueta="Programa" valor={d.item_tema || 'Fuera del programa'} /><Dato etiqueta="Material" valor={d.material_entregado} />
            </div>
            <p className="text-xs"><strong>Tema tratado:</strong> {d.tema_tratado}</p>
            <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
              <div className="mb-1 flex flex-wrap items-center gap-2"><p className="font-semibold">Asistentes ({d.asistentes.length})</p>
                {abierta && puedeEditar && <><select multiple className="h-16 rounded border border-slate-300 bg-transparent text-[11px] dark:border-slate-700" value={agregar.map(String)} onChange={(e) => setAgregar([...e.target.selectedOptions].map((o) => Number(o.value)))}>{trabajadores.filter((t) => !enLista.has(t.id)).map((t) => <option key={t.id} value={t.id}>{t.nombre_completo}</option>)}</select>
                  <button className="text-esynapse-500 underline" onClick={async () => { if (await accion('asistentes', { trabajadores: agregar })) setAgregar([]) }}>Agregar seleccionados</button>
                  <label className="ml-auto cursor-pointer text-esynapse-500 underline">Adjuntar lista firmada en papel<input type="file" className="hidden" onChange={(e) => e.target.files[0] && subir('lista_papel', { archivo: e.target.files[0] })} /></label></>}
                {d.lista_papel_url && <a className="text-esynapse-500 underline" href={d.lista_papel_url} target="_blank" rel="noreferrer">Ver la lista en papel</a>}</div>
              <table className="tabla-sig">
                <thead><tr><th>Apellidos y nombres</th><th>DNI/CE</th><th>Cargo</th>{d.con_evaluacion && <th className="text-right">Nota</th>}<th className="text-center">Firma</th>{d.estado === 'cerrada' && <th className="text-center">Certificado</th>}<th /></tr></thead>
                <tbody>{d.asistentes.map((a) => (
                  <tr key={a.id}>
                    <td>{a.nombre}</td><td className="whitespace-nowrap">{a.documento}</td><td>{a.cargo}</td>
                    {d.con_evaluacion && <td className="w-24 text-right">{abierta && puedeEditar ? <input type="number" min="0" max="20" step="0.5" className={`${inp} !py-1 text-right text-xs`} defaultValue={a.nota ?? ''} onBlur={(e) => e.target.value !== String(a.nota ?? '') && e.target.value !== '' && accion('nota', { id: a.id, nota: e.target.value })} /> : (a.nota ?? '—')}</td>}
                    <td className="text-center">{a.firma?.metodo ? <Chip par={[`Firmado · ${METODO[a.firma.metodo]}`, VERDE]} /> : abierta && puedeEditar ? (firmando?.id === a.id
                      ? <div className="flex items-center gap-1"><Credencial forma={a.forma_firma} valor={firmando.cred} onChange={(v) => setFirmando({ ...firmando, cred: v })} /><button className="btn-primary !py-1 text-xs" onClick={async () => { if (await accion('firmar_asistente', { id: a.id, ...firmando.cred })) setFirmando(null) }}>Firmar</button><button className="p-1 text-slate-500" onClick={() => setFirmando(null)}><X className="h-3.5 w-3.5" /></button></div>
                      : <button className="text-esynapse-500 underline" onClick={() => setFirmando({ id: a.id, cred: {} })}><KeyRound className="mr-1 inline h-3 w-3" />Firmar ({a.forma_firma === 'usuario' ? 'usuario' : 'PIN'})</button>) : <Chip par={['Sin firma', ROJO]} />}</td>
                    {d.estado === 'cerrada' && <td className="text-center"><Chip par={CERT[a.certificado]} />{a.constancia_url && <a className="ml-1 text-[11px] text-esynapse-500 underline" href={a.constancia_url} target="_blank" rel="noreferrer">constancia</a>}{d.externo && !a.constancia_url && puedeEditar && <label className="ml-1 cursor-pointer text-[11px] text-esynapse-500 underline">adjuntar constancia<input type="file" className="hidden" onChange={(e) => e.target.files[0] && subir('archivo', { asistente: a.id, archivo: e.target.files[0] })} /></label>}</td>}
                    <td>{abierta && puedeEditar && <button className="p-1 text-red-500" onClick={() => accion('quitar_asistente', { id: a.id })}><X className="h-3.5 w-3.5" /></button>}</td>
                  </tr>
                ))}{d.asistentes.length === 0 && <tr><td colSpan={7} className="py-4 text-center text-slate-400">Agregue a los asistentes</td></tr>}</tbody>
              </table>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs"><span className="font-semibold">Material y evaluaciones:</span>{d.archivos.map((x) => <a key={x.id} className="text-esynapse-500 underline" href={x.url} target="_blank" rel="noreferrer">{x.descripcion || x.tipo}</a>)}
              {puedeEditar && d.estado !== 'anulada' && <label className="cursor-pointer text-esynapse-500 underline">+ Adjuntar<input type="file" className="hidden" onChange={async (e) => { const file = e.target.files[0]; if (!file) return; const desc = await confirmar({ titulo: 'Archivo de la sesión', mensaje: file.name, textoConfirmar: 'Adjuntar', entrada: { etiqueta: 'Descripción (presentación, evaluación, manual…)', obligatorio: false, valorInicial: file.name } }); if (desc !== null) subir('archivo', { tipo: 'material', descripcion: desc, archivo: file }) }} /></label>}</div>
            {d.observaciones && <p className="text-xs"><strong>Observaciones:</strong> {d.observaciones}</p>}
            {d.estado === 'cerrada' && <p className="text-xs text-slate-500">Registró {d.firma_registro?.nombre} · {fechaHora(d.firma_registro?.fecha)}</p>}
            {d.estado === 'cerrada' && (
              <div className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
                <p className="mb-1 font-semibold">Evaluación de la eficacia <span className="font-normal text-slate-500">(dentro de los 6 meses: técnica, Gerente Técnico; general, Área SIG)</span></p>
                {d.eficacia?.resultado ? <p><Chip par={[d.eficacia.resultado === 'eficaz' ? 'Eficaz' : 'No eficaz', d.eficacia.resultado === 'eficaz' ? VERDE : ROJO]} /> {d.eficacia.comentario} <span className="text-slate-500">— {d.eficacia.firma?.nombre}, {fecha(d.eficacia.fecha)}</span></p>
                  : puedeAprobar ? (efi ? <div className="grid gap-2 md:grid-cols-4"><select className={inp} value={efi.resultado} onChange={(e) => setEfi({ ...efi, resultado: e.target.value })}><option value="eficaz">Eficaz</option><option value="no_eficaz">No eficaz</option></select><div className="md:col-span-2"><input className={inp} placeholder="Cómo se evaluó (evidencia)" value={efi.comentario} onChange={(e) => setEfi({ ...efi, comentario: e.target.value })} /></div><div className="flex gap-2"><button className="btn-secondary" onClick={() => setEfi(null)}>Cancelar</button><button className="btn-primary" onClick={evaluar}>Firmar</button></div></div>
                    : <button className="btn-secondary !py-1 text-xs" onClick={() => setEfi({ resultado: 'eficaz', comentario: '' })}>Evaluar la eficacia</button>) : <p className="text-slate-500">Pendiente.</p>}
              </div>
            )}
            {err && <Aviso texto={err} />}
            {abierta && <div className="flex justify-end gap-2">{puedeEliminar && <button className="btn-secondary text-red-600" onClick={anular}>Anular</button>}{puedeEditar && <button className="btn-primary" onClick={cerrar}>Cerrar la lista (firmar)</button>}</div>}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* =================================================================================== inducción */
function Inducciones({ cat, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeEliminar }) {
  const trabajadores = useTrabajadores()
  const [items, setItems] = useState([])
  const [nueva, setNueva] = useState(null)
  const [d, setD] = useState(null)
  const [parte, setParte] = useState('organizacional')
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.capacitacion.inducciones().then(setItems).catch((e) => setError(e.message)), [setError])
  useEffect(() => { cargar() }, [cargar])
  const abrir = async (id) => { setErr(''); setParte('organizacional'); setD(await api.capacitacion.induccion(id)) }
  const crear = async () => { setErr(''); try { const r = await api.capacitacion.crearInduccion(nueva); setNueva(null); cargar(); setParte('organizacional'); setD(r) } catch (e) { setErr(e.message) } }
  const accion = async (nombre, datos) => { setErr(''); try { setD(await api.capacitacion.accionInduccion(d.id, nombre, datos)); cargar(); return true } catch (e) { setErr(e.message); return false } }
  const anular = async () => { const m = await confirmar({ titulo: 'Anular la inducción', mensaje: 'Solo si se registró por error (sin partes firmadas).', textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null && await accion('anular', { motivo: m })) setD(null) }
  const ultima = (k) => (d?.partes || []).filter((p) => p.parte === k).sort((a, b) => b.intento - a.intento)[0]
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><p className="text-xs text-slate-500">Tres partes: organizacional (Recursos Humanos), del sistema integrado de gestión (Área SIG) y específica del cargo (responsable del área). Cada una se aprueba con 14; el trabajador inicia actividades con las tres aprobadas.</p>
        {puedeCrear && <button className="btn-primary ml-auto shrink-0" onClick={() => { setErr(''); setNueva({ trabajador: '', tipo: 'induccion', fecha_inicio: hoy(), motivo: '' }) }}><Plus className="h-4 w-4" /> Nueva inducción</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig min-w-[860px]">
          <thead><tr><th>Código</th><th>Trabajador</th><th>Puesto / área</th><th className="text-center">Tipo</th><th className="text-right">Inicio</th>{(cat?.partes || []).map(([k]) => <th key={k} className="text-center">{k === 'organizacional' ? 'Organizacional' : k === 'sig' ? 'SIG' : 'Específica'}</th>)}<th className="text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id} className="fila" onClick={() => abrir(i.id)}>
                <td className="whitespace-nowrap font-semibold text-esynapse-700 dark:text-esynapse-300">{i.codigo}</td><td>{i.nombre}</td><td className="text-slate-500">{i.puesto}<span className="block text-[11px]">{i.area}</span></td>
                <td className="text-center">{i.tipo_display}</td><td className="whitespace-nowrap text-right">{fecha(i.fecha_inicio)}</td>
                {(cat?.partes || []).map(([k]) => { const p = i.partes.filter((x) => x.parte === k).sort((a, b) => b.intento - a.intento)[0]; return <td key={k} className="text-center">{p ? <Chip par={EST_PARTE[p.estado]} extra={p.nota != null && p.estado !== 'en_registro' ? ` ${Number(p.nota)}` : ''} /> : '—'}</td> })}
                <td className="text-center"><Chip par={EST_IND[i.estado]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={9} className="py-8 text-center text-slate-400">Sin inducciones registradas</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(nueva)} titulo="Nueva inducción" onCerrar={() => setNueva(null)}>
        {nueva && <div className="space-y-3 text-sm">
          <div><label className={lbl}>Trabajador</label><select className={inp} value={nueva.trabajador} onChange={(e) => setNueva({ ...nueva, trabajador: e.target.value })}><option value="">— Elija —</option>{trabajadores.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo} · {t.puesto_nombre}</option>)}</select></div>
          <div className="grid gap-3 md:grid-cols-2"><div><label className={lbl}>Tipo</label><select className={inp} value={nueva.tipo} onChange={(e) => setNueva({ ...nueva, tipo: e.target.value })}>{(cat?.tipos_induccion || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div><div><label className={lbl}>Inicio</label><input type="date" className={inp} value={nueva.fecha_inicio} onChange={(e) => setNueva({ ...nueva, fecha_inicio: e.target.value })} /></div></div>
          {nueva.tipo === 'reinduccion' && <div><label className={lbl}>Motivo de la re-inducción</label><input className={inp} value={nueva.motivo} onChange={(e) => setNueva({ ...nueva, motivo: e.target.value })} /></div>}
          {err && <Aviso texto={err} />}
          <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setNueva(null)}>Cancelar</button><button className="btn-primary" onClick={crear}>Crear</button></div>
        </div>}
      </Modal>
      <Modal abierto={Boolean(d)} titulo={d ? `${d.codigo} — Inducción de ${d.nombre}` : ''} onCerrar={() => setD(null)} panel>
        {d && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2"><Chip par={EST_IND[d.estado]} /><span className="text-xs text-slate-500">{d.tipo_display} · {d.puesto} · {d.area}{d.motivo ? ` · ${d.motivo}` : ''}</span>
              <button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => abrirPdf(api.capacitacion.induccionPdf(d.id))}><FileText className="h-3.5 w-3.5" /> PDF</button>
              {puedeEliminar && d.partes.every((p) => p.estado === 'en_registro') && <button className="btn-secondary !py-1 text-xs text-red-600" onClick={anular}>Anular</button>}</div>
            <Vistas opciones={(cat?.partes || []).map(([k, n]) => [k, `${n.replace('Inducción ', '')}${ultima(k) ? ` · ${EST_PARTE[ultima(k).estado][0]}` : ''}`])} valor={parte} onChange={setParte} />
            {ultima(parte) && <ParteForm key={ultima(parte).id} p={ultima(parte)} ind={d} accion={accion} puedeEditar={puedeEditar} confirmar={confirmar} />}
            {err && <Aviso texto={err} />}
          </div>
        )}
      </Modal>
    </div>
  )
}

function ParteForm({ p, ind, accion, puedeEditar, confirmar }) {
  const [f, setF] = useState({ ...p, hora_inicio: (p.hora_inicio || '').slice(0, 5), hora_fin: (p.hora_fin || '').slice(0, 5) })
  const [firmar, setFirmar] = useState(null)
  const editable = p.estado === 'en_registro' && puedeEditar
  const guardar = () => accion('guardar_parte', { id: p.id, responsable: f.responsable, fecha: f.fecha, hora_inicio: f.hora_inicio, hora_fin: f.hora_fin, temas: f.temas, documentos: f.documentos, preguntas: f.preguntas, nota_directa: f.nota_directa, evaluador: f.evaluador, fecha_evaluacion: f.fecha_evaluacion, observaciones: f.observaciones, evaluacion_url: f.evaluacion_url })
  const total = (f.preguntas || []).reduce((a, q) => a + Number(q.puntos || 0), 0)
  const obtenido = (f.preguntas || []).reduce((a, q) => a + Number(q.calificacion || 0), 0)
  const nota = f.preguntas?.length ? (total ? Math.round((obtenido * 20 / total) * 10) / 10 : null) : f.nota_directa
  const firmarParte = async () => {
    if (!await guardar()) return
    const c = await confirmar({ titulo: `Firmar la ${p.parte_display.toLowerCase()}`, mensaje: `Nota: ${nota ?? '—'} (aprobatoria 14). Firma como responsable de la inducción.`, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
    if (c !== null && await accion('firmar_parte', { id: p.id, password: c, ...firmar })) setFirmar(null)
  }
  let grupo = null
  return (
    <div className="space-y-3 text-xs">
      <div className="flex flex-wrap items-center gap-2"><Chip par={EST_PARTE[p.estado]} />{p.intento > 1 && <span className="text-slate-500">Intento {p.intento}</span>}{p.estado !== 'en_registro' && <span className="text-slate-500">Nota {Number(p.nota)} · responsable {p.firma_responsable?.nombre} · colaborador firmó con {METODO[p.firma_colaborador?.metodo] || '—'} · {fechaHora(p.firma_colaborador?.fecha)}</span>}
        {p.estado === 'desaprobada' && puedeEditar && <button className="btn-primary !py-1 text-xs" onClick={() => accion('repetir_parte', { parte: p.parte })}>Repetir esta parte (nueva inducción)</button>}</div>
      <div className="grid gap-3 md:grid-cols-4">
        <div className="md:col-span-2"><label className={lbl}>Responsable de la inducción</label><input className={inp} disabled={!editable} value={f.responsable} onChange={(e) => setF({ ...f, responsable: e.target.value })} /></div>
        <div><label className={lbl}>Fecha</label><input type="date" className={inp} disabled={!editable} value={f.fecha || ''} onChange={(e) => setF({ ...f, fecha: e.target.value })} /></div>
        <div className="flex gap-1"><div><label className={lbl}>Inicio</label><input type="time" className={inp} disabled={!editable} value={f.hora_inicio} onChange={(e) => setF({ ...f, hora_inicio: e.target.value })} /></div><div><label className={lbl}>Fin</label><input type="time" className={inp} disabled={!editable} value={f.hora_fin} onChange={(e) => setF({ ...f, hora_fin: e.target.value })} /></div></div>
      </div>
      <div className="rounded-lg border border-slate-200 p-2 dark:border-slate-800">
        <div className="mb-1 flex items-center gap-2"><p className="font-semibold">Temas — la inducción incluyó</p>{editable && <button className="text-esynapse-500 underline" onClick={() => setF({ ...f, temas: f.temas.map((t) => ({ ...t, incluido: true })) })}>marcar todos</button>}</div>
        <table className="tabla-sig"><tbody>{f.temas.map((t, k) => {
          const cab = t.grupo && t.grupo !== grupo ? (grupo = t.grupo) : null
          return [cab && <tr key={`g${k}`}><td colSpan={2} className="bg-slate-100 px-1 py-0.5 font-semibold dark:bg-slate-800/60">{cab}</td></tr>,
            <tr key={k} className="border-t border-slate-100 dark:border-slate-800/60"><td className="w-6"><input type="checkbox" className="accent-esynapse-600" disabled={!editable} checked={Boolean(t.incluido)} onChange={(e) => setF({ ...f, temas: f.temas.map((x, j) => (j === k ? { ...x, incluido: e.target.checked } : x)) })} /></td><td className="py-0.5">{t.tema}{t.enlace && <a className="ml-1 inline-flex items-center gap-0.5 text-esynapse-500 underline" href={t.enlace} target="_blank" rel="noreferrer">material <ExternalLink className="h-3 w-3" /></a>}{t.descripcion && <span className="block text-[10px] text-slate-500">{t.descripcion}</span>}</td></tr>]
        })}</tbody></table>
      </div>
      {f.documentos?.length > 0 && <div className="rounded-lg border border-slate-200 p-2 dark:border-slate-800"><p className="mb-1 font-semibold">Entrega de documentos</p>{f.documentos.map((x, k) => <label key={k} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" disabled={!editable} checked={Boolean(x.entregado)} onChange={(e) => setF({ ...f, documentos: f.documentos.map((y, j) => (j === k ? { ...y, entregado: e.target.checked } : y)) })} />{x.documento}{x.version && <span className="text-slate-400">· versión {x.version}</span>}{x.enlace && <a className="inline-flex items-center gap-0.5 text-esynapse-500 underline" href={x.enlace} target="_blank" rel="noreferrer">ver <ExternalLink className="h-3 w-3" /></a>}</label>)}</div>}
      <div className="rounded-lg border border-slate-200 p-2 dark:border-slate-800">
        <p className="mb-1 font-semibold">Evaluación <span className="font-normal text-slate-500">(0 a 20; aprobatoria 14)</span></p>
        <div className="mb-2 grid gap-3 md:grid-cols-3"><div className="md:col-span-2"><label className={lbl}>Evaluador</label><input className={inp} disabled={!editable} value={f.evaluador} onChange={(e) => setF({ ...f, evaluador: e.target.value })} /></div><div><label className={lbl}>Fecha de evaluación</label><input type="date" className={inp} disabled={!editable} value={f.fecha_evaluacion || ''} onChange={(e) => setF({ ...f, fecha_evaluacion: e.target.value })} /></div></div>
        {f.preguntas?.length ? <table className="tabla-sig"><thead><tr className="text-[10px] uppercase text-slate-500"><th className="text-left">Pregunta</th><th className="w-16 text-right">Puntos</th><th className="w-24 text-right">Calificación</th></tr></thead><tbody>{f.preguntas.map((q, k) => <tr key={k} className="border-t border-slate-100 dark:border-slate-800/60"><td className="py-0.5">{editable && /definir/i.test(q.pregunta) ? <input className={`${inp} !py-1 text-xs`} value={q.pregunta} onChange={(e) => setF({ ...f, preguntas: f.preguntas.map((x, j) => (j === k ? { ...x, pregunta: e.target.value } : x)) })} /> : q.pregunta}</td><td className="text-right">{q.puntos}</td><td className="text-right">{editable ? <input type="number" min="0" max={q.puntos} step="0.5" className={`${inp} !py-1 text-right text-xs`} value={q.calificacion ?? ''} onChange={(e) => setF({ ...f, preguntas: f.preguntas.map((x, j) => (j === k ? { ...x, calificacion: e.target.value === '' ? null : Number(e.target.value) } : x)) })} /> : (q.calificacion ?? '—')}</td></tr>)}
          <tr className="border-t border-slate-200 font-semibold dark:border-slate-700"><td>Nota (sobre 20)</td><td className="text-right">{total}</td><td className="text-right">{nota ?? '—'}</td></tr></tbody></table>
          : <div className="grid gap-3 md:grid-cols-3"><div className="md:col-span-2"><label className={lbl}>Evaluación en línea</label>{f.evaluacion_url ? <a className="block truncate text-esynapse-500 underline" href={f.evaluacion_url} target="_blank" rel="noreferrer">{f.evaluacion_url}</a> : '—'}</div><div><label className={lbl}>Nota obtenida</label><input type="number" min="0" max="20" step="0.5" className={inp} disabled={!editable} value={f.nota_directa ?? ''} onChange={(e) => setF({ ...f, nota_directa: e.target.value })} /></div></div>}
      </div>
      <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} disabled={!editable} value={f.observaciones} onChange={(v) => setF({ ...f, observaciones: v })} /></div>
      {editable && (firmar ? (
        <div className="rounded-lg border-2 border-esynapse-500/50 p-3">
          <p className="mb-2 flex items-center gap-1 font-semibold"><KeyRound className="h-4 w-4" /> Firma del colaborador — {ind.nombre}</p>
          <div className="w-80"><Credencial forma={ind.forma_firma} valor={firmar} onChange={setFirmar} /></div>
          <p className="mt-1 text-[11px] text-slate-500">Luego usted firma como responsable con su contraseña.</p>
          <div className="mt-2 flex justify-end gap-2"><button className="btn-secondary" onClick={() => setFirmar(null)}>Cancelar</button><button className="btn-primary" onClick={firmarParte}>Firmar</button></div>
        </div>
      ) : <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={guardar}>Guardar</button><button className="btn-primary" onClick={() => setFirmar({})}>Firmar la parte</button></div>)}
    </div>
  )
}

/* ============================================================================== por trabajador */
function PorTrabajador({ anio, setError }) {
  const [filas, setFilas] = useState([])
  const [det, setDet] = useState(null)
  useEffect(() => { api.capacitacion.situacion(anio).then(setFilas).catch((e) => setError(e.message)) }, [anio, setError])
  const ver = async (t) => { const r = await api.capacitacion.situacion(anio, t); setDet(r[0]) }
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">Capacitaciones del programa {anio} que corresponden a cada trabajador (según el personal a capacitar), su asistencia e inducción.</p>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig min-w-[900px]">
          <thead><tr><th>Trabajador</th><th>Puesto / área</th><th className="text-center">Inducción</th><th className="text-right">Le corresponden</th><th className="text-right">Realizadas</th><th className="text-right">Asistió</th><th className="text-right">No asistió</th><th className="text-right">Horas</th></tr></thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.trabajador} className="fila" onClick={() => ver(f.trabajador)}>
                <td>{f.nombre}</td><td className="text-slate-500">{f.puesto}<span className="block text-[11px]">{f.area}</span></td><td className="text-center"><Chip par={EST_IND[f.induccion]} /></td>
                <td className="text-right">{f.aplicables}</td><td className="text-right">{f.realizadas}</td><td className="text-right">{f.asistidas}</td>
                <td className="text-right">{f.no_asistio ? <Chip par={[f.no_asistio, ROJO]} /> : 0}</td><td className="text-right">{f.horas}</td>
              </tr>
            ))}
            {filas.length === 0 && <tr><td colSpan={8} className="py-8 text-center text-slate-400">Sin trabajadores activos en Organización y personal</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(det)} titulo={det ? `${det.nombre} — capacitación ${anio}` : ''} onCerrar={() => setDet(null)} ancho="max-w-4xl">
        {det && <div className="space-y-3 text-xs">
          <p><Chip par={EST_IND[det.induccion]} /> · {det.puesto} · {det.area} · {det.horas} h de capacitación en el año</p>
          <table className="tabla-sig"><thead><tr><th>Capacitación</th><th className="text-center">Tipo</th><th className="text-right">Fecha</th><th className="text-center">Estado</th><th className="text-center">Asistió</th></tr></thead>
            <tbody>{det.detalle.map((x) => <tr key={x.id}><td>{x.tema}</td><td className="text-center">{x.tipo}</td><td className="whitespace-nowrap text-right">{fecha(x.fecha)}</td><td className="text-center"><Chip par={EST_ITEM[x.estado]} /></td><td className="text-center">{x.asistio ? <Chip par={['Sí', VERDE]} /> : x.estado === 'realizado' ? <Chip par={['No', ROJO]} /> : '—'}</td></tr>)}</tbody></table>
          {det.sesiones.length > 0 && <><p className="font-semibold">Listas de asistencia</p><table className="tabla-sig"><thead><tr><th>Código</th><th className="text-right">Fecha</th><th>Tema</th><th className="text-right">Horas</th><th className="text-right">Nota</th><th className="text-center">Certificado</th></tr></thead>
            <tbody>{det.sesiones.map((s) => <tr key={s.id}><td>{s.codigo}</td><td className="whitespace-nowrap text-right">{fecha(s.fecha)}</td><td>{s.tema}</td><td className="text-right">{s.horas}</td><td className="text-right">{s.nota ?? '—'}</td><td className="text-center"><Chip par={CERT[s.certificado]} /></td></tr>)}</tbody></table></>}
        </div>}
      </Modal>
    </div>
  )
}

/* ================================================================= contenido de la inducción */
function Plantillas({ setError, puedeEditar }) {
  const [items, setItems] = useState([])
  const [docsSig, setDocsSig] = useState([])
  const [ed, setEd] = useState(null)
  const [verHist, setVerHist] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.capacitacion.plantillas().then(setItems).catch((e) => setError(e.message)), [setError])
  useEffect(() => { cargar() }, [cargar])
  const editar = (p) => {
    setErr(''); setEd({ ...JSON.parse(JSON.stringify(p)), motivo: '' })
    if (!docsSig.length) api.capacitacion.documentosSig().then(setDocsSig).catch(() => {})
  }
  const guardar = async () => {
    setErr('')
    if (!ed.motivo.trim()) { setErr('Indique el motivo del cambio.'); return }
    try {
      await api.capacitacion.editarPlantilla(ed.id, { motivo: ed.motivo, temas: ed.temas, evaluacion_url: ed.evaluacion_url,
        documentos: ed.documentos.map((d) => ({ documento: d.documento, codigo: d.codigo, enlace: d.enlace, documento_id: d.documento_id || null })),
        preguntas: ed.preguntas.map((q) => ({ pregunta: q.pregunta, puntos: Number(q.puntos) })) })
      setEd(null); cargar()
    } catch (e) { setErr(e.message) }
  }
  const fila = (campo, k, prop, v) => setEd({ ...ed, [campo]: ed[campo].map((x, j) => (j === k ? { ...x, [prop]: v } : x)) })
  const quitar = (campo, k) => setEd({ ...ed, [campo]: ed[campo].filter((_, j) => j !== k) })
  const mover = (campo, k, d) => { const l = [...ed[campo]]; const n = k + d; if (n < 0 || n >= l.length) return; [l[k], l[n]] = [l[n], l[k]]; setEd({ ...ed, [campo]: l }) }
  const Acciones = ({ campo, k }) => (
    <div className="flex items-center justify-end gap-0.5 md:col-span-1">
      <button type="button" title="Subir" className="p-0.5 text-slate-400 hover:text-slate-600 disabled:opacity-30" disabled={k === 0} onClick={() => mover(campo, k, -1)}><ArrowUp className="h-3.5 w-3.5" /></button>
      <button type="button" title="Bajar" className="p-0.5 text-slate-400 hover:text-slate-600 disabled:opacity-30" disabled={k === ed[campo].length - 1} onClick={() => mover(campo, k, 1)}><ArrowDown className="h-3.5 w-3.5" /></button>
      <button type="button" title="Quitar" className="p-0.5 text-red-500" onClick={() => quitar(campo, k)}><X className="h-3.5 w-3.5" /></button>
    </div>
  )
  const totalPuntos = (l) => l.reduce((a, q) => a + Number(q.puntos || 0), 0)
  const ultimo = (p) => p.historial?.at(-1)
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">Configuración de cada parte de la inducción: lista de verificación de temas, documentos que se entregan (vinculados a la lista maestra o con su enlace) y preguntas de la evaluación. Cada cambio pide motivo, sube la versión y queda en el historial; se aplica a las inducciones nuevas y las ya registradas conservan el contenido con que se hicieron.</p>
      <div className="grid gap-3 md:grid-cols-3">{items.map((p) => (
        <div key={p.id} className="card-esynapse space-y-1.5 p-3 text-xs">
          <div className="flex items-center justify-between gap-2"><p className="font-semibold">{p.parte_display}</p><span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">Versión {p.version}</span></div>
          <p className="text-slate-500">{p.temas.length} temas · {p.documentos.length} documentos · {p.preguntas.length ? `${p.preguntas.length} preguntas (${totalPuntos(p.preguntas)} puntos)` : 'evaluación en línea'}</p>
          <p className="text-[11px] text-slate-400">{ultimo(p) ? `Último cambio: ${fechaHora(ultimo(p).fecha)} · ${ultimo(p).usuario}` : 'Contenido inicial del formato'}</p>
          <div className="flex gap-2">
            {puedeEditar && <button className="btn-secondary !py-1 text-xs" onClick={() => editar(p)}><Pencil className="h-3.5 w-3.5" /> Editar</button>}
            {p.historial?.length > 0 && <button className="btn-secondary !py-1 text-xs" onClick={() => setVerHist(p)}><History className="h-3.5 w-3.5" /> Historial</button>}
          </div>
        </div>
      ))}</div>
      <Modal abierto={Boolean(verHist)} titulo={verHist ? `Historial — ${verHist.parte_display}` : ''} onCerrar={() => setVerHist(null)} ancho="max-w-3xl">
        {verHist && <table className="tabla-sig w-full text-xs"><thead><tr className="text-[10px] uppercase text-slate-500"><th className="w-16 text-center">Versión</th><th className="text-right">Fecha</th><th className="text-left">Usuario</th><th className="text-left">Motivo</th><th className="text-left">Cambios</th></tr></thead>
          <tbody>{[...verHist.historial].reverse().map((h) => <tr key={h.version} className="border-t border-slate-100 dark:border-slate-800/60"><td className="text-center">{h.version}</td><td className="text-right">{fechaHora(h.fecha)}</td><td>{h.usuario}</td><td>{h.motivo}</td><td className="text-slate-500">{h.cambios}</td></tr>)}</tbody></table>}
      </Modal>
      <Modal abierto={Boolean(ed)} titulo={ed ? `Contenido — ${ed.parte_display} (versión ${ed.version})` : ''} onCerrar={() => setEd(null)} ancho="max-w-6xl">
        {ed && <div className="space-y-4 text-xs">
          <section className="space-y-1">
            <p className="font-semibold">Lista de verificación — temas <span className="font-normal text-slate-500">(se marcan al hacer la inducción)</span></p>
            <div className="hidden gap-1 px-0.5 text-[10px] uppercase text-slate-400 md:grid md:grid-cols-12"><span className="md:col-span-2">Grupo</span><span className="md:col-span-3">Tema</span><span className="md:col-span-3">Descripción</span><span className="md:col-span-2">Enlace (opcional)</span><span className="md:col-span-1">Código para el PDF</span></div>
            {ed.temas.map((t, k) => <div key={k} className="grid gap-1 md:grid-cols-12">
              <input className={`${inp} !py-1 text-xs md:col-span-2`} placeholder="Grupo" value={t.grupo || ''} onChange={(e) => fila('temas', k, 'grupo', e.target.value)} />
              <input className={`${inp} !py-1 text-xs md:col-span-3`} placeholder="Tema" value={t.tema} onChange={(e) => fila('temas', k, 'tema', e.target.value)} />
              <input className={`${inp} !py-1 text-xs md:col-span-3`} placeholder="Descripción" value={t.descripcion || ''} onChange={(e) => fila('temas', k, 'descripcion', e.target.value)} />
              <input className={`${inp} !py-1 text-xs md:col-span-2`} placeholder="https://…" value={t.enlace || ''} onChange={(e) => fila('temas', k, 'enlace', e.target.value)} />
              <input className={`${inp} !py-1 text-xs md:col-span-1`} value={t.codigo || ''} onChange={(e) => fila('temas', k, 'codigo', e.target.value)} />
              <Acciones campo="temas" k={k} />
            </div>)}
            <button className="text-esynapse-500 underline" onClick={() => setEd({ ...ed, temas: [...ed.temas, { grupo: ed.temas.at(-1)?.grupo || '', tema: '', descripcion: '', codigo: '', enlace: '' }] })}>+ Tema</button>
          </section>
          <section className="space-y-1">
            <p className="font-semibold">Documentos que se entregan</p>
            <div className="hidden gap-1 px-0.5 text-[10px] uppercase text-slate-400 md:grid md:grid-cols-12"><span className="md:col-span-4">Lista maestra de documentos</span><span className="md:col-span-4">Documento (si no está en la lista maestra)</span><span className="md:col-span-2">Enlace</span><span className="md:col-span-1">Código para el PDF</span></div>
            {ed.documentos.map((d, k) => <div key={k} className="grid gap-1 md:grid-cols-12">
              <select className={`${inp} !py-1 text-xs md:col-span-4`} value={d.documento_id || ''} onChange={(e) => { const doc = docsSig.find((x) => String(x.id) === e.target.value); setEd({ ...ed, documentos: ed.documentos.map((x, j) => (j === k ? (doc ? { documento: doc.titulo, codigo: '', enlace: '', documento_id: doc.id } : { ...x, documento_id: null }) : x)) }) }}>
                <option value="">— No vinculado —</option>{docsSig.map((x) => <option key={x.id} value={x.id}>{x.titulo}</option>)}
                {d.documento_id && !docsSig.some((x) => x.id === d.documento_id) && <option value={d.documento_id}>{d.documento}</option>}
              </select>
              {d.documento_id
                ? <p className="flex items-center gap-1 text-slate-500 md:col-span-7">Toma el nombre, el código y la versión vigente de la lista maestra{d.enlace && <a className="ml-1 inline-flex items-center gap-0.5 text-esynapse-500 underline" href={d.enlace} target="_blank" rel="noreferrer">ver <ExternalLink className="h-3 w-3" /></a>}</p>
                : <><input className={`${inp} !py-1 text-xs md:col-span-4`} placeholder="Nombre del documento" value={d.documento || ''} onChange={(e) => fila('documentos', k, 'documento', e.target.value)} />
                  <input className={`${inp} !py-1 text-xs md:col-span-2`} placeholder="https://…" value={d.enlace || ''} onChange={(e) => fila('documentos', k, 'enlace', e.target.value)} />
                  <input className={`${inp} !py-1 text-xs md:col-span-1`} value={d.codigo || ''} onChange={(e) => fila('documentos', k, 'codigo', e.target.value)} /></>}
              <Acciones campo="documentos" k={k} />
            </div>)}
            <button className="text-esynapse-500 underline" onClick={() => setEd({ ...ed, documentos: [...ed.documentos, { documento: '', codigo: '', enlace: '', documento_id: null }] })}>+ Documento</button>
          </section>
          <section className="space-y-1">
            <p className="font-semibold">Preguntas de la evaluación <span className="font-normal text-slate-500">(total {totalPuntos(ed.preguntas)} puntos; la nota se lleva a 20)</span></p>
            {ed.preguntas.map((q, k) => <div key={k} className="grid gap-1 md:grid-cols-12">
              <input className={`${inp} !py-1 text-xs md:col-span-10`} placeholder="Pregunta" value={q.pregunta} onChange={(e) => fila('preguntas', k, 'pregunta', e.target.value)} />
              <input type="number" min="0.5" step="0.5" title="Puntos" className={`${inp} !py-1 text-right text-xs md:col-span-1`} value={q.puntos} onChange={(e) => fila('preguntas', k, 'puntos', e.target.value)} />
              <Acciones campo="preguntas" k={k} />
            </div>)}
            <button className="text-esynapse-500 underline" onClick={() => setEd({ ...ed, preguntas: [...ed.preguntas, { pregunta: '', puntos: 2 }] })}>+ Pregunta</button>
          </section>
          <div className="grid gap-3 md:grid-cols-2">
            <div><label className={lbl}>Evaluación en línea (enlace, si no hay preguntas)</label><input className={inp} placeholder="https://…" value={ed.evaluacion_url || ''} onChange={(e) => setEd({ ...ed, evaluacion_url: e.target.value })} /></div>
            <div><label className={lbl}>Motivo del cambio (obligatorio)</label><input className={inp} value={ed.motivo} onChange={(e) => setEd({ ...ed, motivo: e.target.value })} /></div>
          </div>
          {err && <Aviso texto={err} />}
          <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setEd(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar versión {ed.version + 1}</button></div>
        </div>}
      </Modal>
    </div>
  )
}
