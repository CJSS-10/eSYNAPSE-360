import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FileText, KeyRound, Pencil, Plus, Search, Trash2, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { Vistas as Sub } from '../components/NavModulo.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import { api } from '../lib/api.js'
import { fecha, fechaHora, hoy as hoyLocal } from '../lib/fecha.js'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
// Estados (regla 10): gris registro · verde firmada/vigente · ámbar por vencer · rojo vencido/falta/anulada.
const ESTADO = {
  en_registro: ['En registro', 'bg-slate-500/15 text-slate-500'],
  firmada: ['Firmada', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  anulada: ['Anulada', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  registrado: ['Registrado', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  anulado: ['Anulado', 'bg-red-500/15 text-red-600 dark:text-red-400'],
}
const SIT = {
  vigente: ['Vigente', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  por_vencer: ['Por renovar', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  vencido: ['Vencido', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  falta: ['Falta entregar', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  segun_tarea: ['Según la tarea', 'bg-slate-500/15 text-slate-500'],
  sin_examen: ['Sin examen', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  sin_proximo: ['Sin próximo examen', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
}
const APT = {
  apto: ['Apto', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  apto_restricciones: ['Apto con restricciones', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  no_apto: ['No apto', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  observado: ['Observado', 'bg-violet-500/15 text-violet-600 dark:text-violet-400'],
}
// Firma presencial: quien tiene usuario firma con su contraseña; quien no, con su PIN personal.
const METODO = { pin: 'PIN', usuario: 'Usuario', papel: 'Papel' }
const credencial = (estado, f) => (estado === 'usuario' ? { clave_trabajador: f.claveT } : estado === 'activo' ? { pin: f.pin } : { pin_nuevo: f.pinNuevo, pin_confirmacion: f.pinConf })
const PIN = { usuario: ['Firma con su usuario', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'], sin_pin: ['Sin PIN', 'bg-slate-500/15 text-slate-500'], activo: ['PIN activo', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'], bloqueado: ['PIN bloqueado', 'bg-red-500/15 text-red-600 dark:text-red-400'] }

const Chip = ({ par, extra }) => (par ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{par[0]}{extra}</span> : null)
function Aviso({ texto }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [texto])
  return <p ref={ref} className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p>
}
const pedirClave = (confirmar, titulo, mensaje) => confirmar({ titulo, mensaje, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
const useTrabajadores = () => {
  const [t, setT] = useState([])
  useEffect(() => { api.org.trabajadores().then((x) => setT(x.filter((w) => w.estado === 'activo'))).catch(() => {}) }, [])
  return t
}

/* ========================================================================================= EPP */
export function Epp(props) {
  const [vista, setVista] = useState('entregas')
  const [resumen, setResumen] = useState(null)
  const cargarResumen = useCallback(() => api.sst.resumenEpp().then(setResumen).catch(() => {}), [])
  useEffect(() => { cargarResumen() }, [cargarResumen])
  const [trab, setTrab] = useState('')
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Sub valor={vista} onChange={setVista} opciones={[['entregas', 'Entregas'], ['trabajador', 'Por trabajador'], ['matriz', 'Matriz por puesto'], ['catalogo', 'Catálogo']]} />
        {resumen && (
          <div className="flex flex-wrap gap-1.5 text-[11px]">
            {resumen.faltan.length > 0 && <span className="rounded bg-red-500/15 px-2 py-0.5 font-semibold text-red-600 dark:text-red-400">{resumen.faltan.length} EPP obligatorio(s) sin entregar</span>}
            {resumen.por_renovar.filter((x) => x.estado === 'vencido').length > 0 && <span className="rounded bg-red-500/15 px-2 py-0.5 font-semibold text-red-600 dark:text-red-400">{resumen.por_renovar.filter((x) => x.estado === 'vencido').length} vencido(s)</span>}
            {resumen.por_renovar.filter((x) => x.estado === 'por_vencer').length > 0 && <span className="rounded bg-amber-500/15 px-2 py-0.5 font-semibold text-amber-600 dark:text-amber-400">{resumen.por_renovar.filter((x) => x.estado === 'por_vencer').length} por renovar</span>}
            {resumen.sin_devolver.length > 0 && <span className="rounded bg-red-500/15 px-2 py-0.5 font-semibold text-red-600 dark:text-red-400">{resumen.sin_devolver.length} EPP de cesados sin devolver</span>}
            {resumen.pin_bloqueados.length > 0 && <span className="rounded bg-red-500/15 px-2 py-0.5 font-semibold text-red-600 dark:text-red-400">{resumen.pin_bloqueados.length} PIN bloqueado(s)</span>}
          </div>
        )}
      </div>
      {vista === 'entregas' && <Entregas {...props} alCambiar={cargarResumen} verTrabajador={(id) => { setTrab(String(id)); setVista('trabajador') }} />}
      {vista === 'trabajador' && <PorTrabajador {...props} trab={trab} setTrab={setTrab} resumen={resumen} alCambiar={cargarResumen} />}
      {vista === 'matriz' && <MatrizEpp {...props} />}
      {vista === 'catalogo' && <CatalogoEpp {...props} />}
    </div>
  )
}

const NUEVA = { trabajador: '', fecha: hoyLocal(), tipo: 'dotacion', motivo: '', observaciones: '', items: [] }

function Entregas({ confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeEliminar, alCambiar, verTrabajador }) {
  const [items, setItems] = useState([])
  const [filtro, setFiltro] = useState({ estado: '', anio: String(new Date().getFullYear()), buscar: '' })
  const [cat, setCat] = useState(null)
  const [catalogo, setCatalogo] = useState([])
  const trabajadores = useTrabajadores()
  const [form, setForm] = useState(null)
  const [firma, setFirma] = useState(null)
  const [err, setErr] = useState('')
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => { const p = new URLSearchParams(Object.entries(filtro).filter(([, v]) => v)); setItems(await ultima(api.sst.entregasEpp(`?${p}`))) }, [filtro])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  useEffect(() => { api.sst.catalogosEpp().then(setCat).catch(() => {}); api.sst.eppCatalogo().then(setCatalogo).catch(() => {}) }, [])
  const editable = (!form?.id && puedeCrear) || (form?.estado === 'en_registro' && puedeEditar)

  const sugerir = async (campo = false) => {
    if (!form.trabajador) { setErr('Elija primero al trabajador.'); return }
    setErr('')
    try {
      const s = await api.sst.sugerirEpp(form.trabajador, campo)
      const ya = new Set(form.items.map((i) => i.epp))
      setForm({ ...form, items: [...form.items, ...s.filter((x) => !ya.has(x.epp)).map((x) => ({ epp: x.epp, cantidad: 1, talla: '', observaciones: '' }))] })
      if (!s.length) setErr('Según la matriz no le falta ni le toca renovar ningún EPP.')
    } catch (e) { setErr(e.message) }
  }
  const guardar = async () => {
    setErr('')
    const datos = { ...form, items: form.items.filter((i) => i.epp) }
    try { const r = form.id ? await api.sst.editarEntregaEpp(form.id, datos) : await api.sst.crearEntregaEpp(datos); setForm({ ...r, items: r.items.map((i) => ({ epp: i.epp, cantidad: i.cantidad, talla: i.talla, observaciones: i.observaciones })), _det: r }); cargar(); alCambiar(); return r } catch (e) { setErr(e.message); return null }
  }
  const abrir = async (id) => { setErr(''); const r = await api.sst.entregaEpp(id); setForm({ ...r, items: r.items.map((i) => ({ epp: i.epp, cantidad: i.cantidad, talla: i.talla, observaciones: i.observaciones })), _det: r }) }
  const prepararFirma = async () => {
    const r = await guardar(); if (!r) return
    const est = await api.sst.estadoEpp(r.trabajador)
    setFirma({ modo: 'pin', estadoPin: est.estado_pin, password: '', claveT: '', pin: '', pinNuevo: '', pinConf: '', archivo: null, err: '' })
  }
  const firmar = async () => {
    const f = firma
    try {
      let r
      if (f.modo === 'papel') {
        if (!f.archivo) { setFirma({ ...f, err: 'Adjunte el cargo firmado.' }); return }
        const fd = new FormData(); fd.append('archivo', f.archivo); fd.append('password', f.password)
        r = await api.sst.subirEntregaEpp(form.id, 'firmar_papel', fd)
      } else {
        r = await api.sst.accionEntregaEpp(form.id, 'firmar', { password: f.password, ...credencial(f.estadoPin, f) })
      }
      setFirma(null); setForm({ ...form, ...r, _det: r }); cargar(); alCambiar()
    } catch (e) { setFirma({ ...f, err: e.message, pin: '' }) }
  }
  const anular = async () => { const m = await confirmar({ titulo: 'Anular la entrega', mensaje: 'Solo si se registró por error.', textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) { try { const r = await api.sst.accionEntregaEpp(form.id, 'anular', { motivo: m }); setForm({ ...form, ...r, _det: r }); cargar() } catch (e) { setErr(e.message) } } }
  const devolver = async () => {
    const dev = (form._det.items || []).filter((i) => i.vigente)
    if (!dev.length) { setErr('No hay EPP en poder del trabajador en esta entrega.'); return }
    const estado = await confirmar({ titulo: 'Devolución de EPP', mensaje: `Se registran como devueltos: ${dev.map((i) => i.epp_nombre).join(', ')}.`, textoConfirmar: 'Registrar', entrada: { etiqueta: 'Estado (escriba «reutilizable» o «descartado»)', obligatorio: true, valorInicial: 'reutilizable' } })
    if (estado === null) return
    const e = estado.trim().toLowerCase().startsWith('desc') ? 'descartado' : 'reutilizable'
    try { const r = await api.sst.accionEntregaEpp(form.id, 'devolver', { items: dev.map((i) => ({ id: i.id, estado_devolucion: e })) }); setForm({ ...form, ...r, _det: r }); cargar(); alCambiar() } catch (x) { setErr(x.message) }
  }
  const nombreEpp = (id) => catalogo.find((c) => c.id === Number(id))?.nombre || ''
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-56 pl-9" placeholder="Código o trabajador…" value={filtro.buscar} onChange={(e) => setFiltro({ ...filtro, buscar: e.target.value })} /></div>
        <select className="input-esynapse w-44" value={filtro.estado} onChange={(e) => setFiltro({ ...filtro, estado: e.target.value })}><option value="">Todo estado</option>{['en_registro', 'firmada', 'anulada'].map((k) => <option key={k} value={k}>{ESTADO[k][0]}</option>)}</select>
        <input className="input-esynapse w-24" type="number" value={filtro.anio} onChange={(e) => setFiltro({ ...filtro, anio: e.target.value })} />
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setForm({ ...NUEVA, items: [] }) }}><Plus className="h-4 w-4" /> Nueva entrega</button>}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">N° registro</th><th className="px-2 text-right">Fecha</th><th className="px-2">Trabajador</th><th className="px-2">Puesto / área</th><th className="px-2 text-center">Tipo</th><th className="px-2">EPP</th><th className="px-2 text-center">Firma</th><th className="px-2 text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id} onClick={() => abrir(e.id)} className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${e.estado === 'anulada' ? 'opacity-50' : ''}`}>
                <td className="px-2 py-1.5 font-mono">{e.codigo}</td><td className="px-2 text-right">{fecha(e.fecha)}</td><td className="px-2">{e.trabajador_nombre}</td><td className="px-2">{e.puesto}<span className="block text-[11px] text-slate-500">{e.area}</span></td>
                <td className="px-2 text-center">{e.tipo_display}{e.motivo && <span className="block text-[11px] text-slate-500">{e.motivo_display}</span>}</td>
                <td className="max-w-[18rem] px-2">{e.items.map((i) => i.epp_nombre).join(', ')}</td>
                <td className="px-2 text-center">{METODO[e.firma_trabajador?.metodo] || '—'}</td><td className="px-2 text-center"><Chip par={ESTADO[e.estado]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin entregas registradas</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal abierto={Boolean(form)} titulo={form?.id ? `${form.codigo} — Entrega de EPP` : 'Nueva entrega de EPP'} onCerrar={() => { setForm(null); setFirma(null) }} ancho="max-w-4xl">
        {form && (
          <div className="space-y-3 text-sm">
            {form.id && <div className="flex flex-wrap items-center gap-2"><Chip par={ESTADO[form.estado]} />{form.firma_trabajador?.metodo && <span className="text-xs text-slate-500">Recibido por {form.firma_trabajador.nombre} ({(METODO[form.firma_trabajador.metodo] || '').toLowerCase()}) · entregado por {form.firma_responsable?.nombre} · {fechaHora(form.firma_responsable?.fecha)}</span>}
              <button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => abrirPdf(api.sst.entregaEppPdf(form.id))}><FileText className="h-3.5 w-3.5" /> PDF</button>
              <button className="btn-secondary !py-1 text-xs" onClick={() => verTrabajador(form.trabajador)}>Ver al trabajador</button></div>}
            {form.estado === 'anulada' && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600">Anulada: {form.motivo_anulacion}</p>}
            <div className="grid gap-3 md:grid-cols-4">
              <div className="md:col-span-2"><label className={lbl}>Trabajador</label><select className={inp} disabled={Boolean(form.id)} value={String(form.trabajador || '')} onChange={(e) => setForm({ ...form, trabajador: e.target.value })}><option value="">— Elija —</option>{trabajadores.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo} · {t.puesto_nombre}</option>)}</select></div>
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} disabled={!editable} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
              <div><label className={lbl}>Tipo</label><select className={inp} disabled={!editable} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{(cat?.tipos_entrega || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
            </div>
            {form.tipo === 'reposicion' && <div className="w-64"><label className={lbl}>Motivo de la reposición</label><select className={inp} disabled={!editable} value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })}><option value="">— Elija —</option>{(cat?.motivos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>}
            <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
              <div className="mb-1 flex flex-wrap items-center gap-2"><p className="font-semibold">EPP entregados</p>
                {editable && <><button className="text-esynapse-500 underline" onClick={() => sugerir(false)}>Traer los que faltan o tocan renovar (matriz)</button><button className="text-esynapse-500 underline" onClick={() => sugerir(true)}>+ los de servicio en campo</button></>}</div>
              <table className="tabla-ficha w-full">
                <thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="px-1">EPP</th><th className="px-1 text-right">Cantidad</th><th className="px-1">Talla</th><th className="px-1">Observaciones</th>{!editable && <th className="px-1 text-right">Renovar el</th>}{!editable && <th className="px-1 text-center">Situación</th>}<th /></tr></thead>
                <tbody>
                  {(editable ? form.items : form._det.items).map((it, i) => (
                    <tr key={i} className="border-t border-slate-100 dark:border-slate-800/60">
                      <td className="px-1 py-1">{editable ? <select className={`${inp} !py-1 text-xs`} value={String(it.epp || '')} onChange={(e) => setForm({ ...form, items: form.items.map((x, j) => (j === i ? { ...x, epp: Number(e.target.value) } : x)) })}><option value="">—</option>{catalogo.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}</select> : it.epp_nombre || nombreEpp(it.epp)}</td>
                      <td className="w-20 px-1 text-right">{editable ? <input type="number" min="1" className={`${inp} !py-1 text-xs`} value={it.cantidad} onChange={(e) => setForm({ ...form, items: form.items.map((x, j) => (j === i ? { ...x, cantidad: e.target.value } : x)) })} /> : it.cantidad}</td>
                      <td className="w-20 px-1">{editable ? <input className={`${inp} !py-1 text-xs`} value={it.talla} onChange={(e) => setForm({ ...form, items: form.items.map((x, j) => (j === i ? { ...x, talla: e.target.value } : x)) })} /> : it.talla}</td>
                      <td className="px-1">{editable ? <input className={`${inp} !py-1 text-xs`} value={it.observaciones} onChange={(e) => setForm({ ...form, items: form.items.map((x, j) => (j === i ? { ...x, observaciones: e.target.value } : x)) })} /> : it.observaciones}</td>
                      {!editable && <td className="px-1 text-right">{fecha(it.renovar_el) || '—'}</td>}
                      {!editable && <td className="px-1 text-center">{it.devuelto ? `Devuelto ${fecha(it.fecha_devolucion)}` : it.reemplazado_por ? 'Reemplazado' : it.vigente ? <Chip par={SIT[it.estado_renovacion || 'vigente']} /> : '—'}</td>}
                      <td>{editable && <button className="p-1 text-red-500" onClick={() => setForm({ ...form, items: form.items.filter((_, j) => j !== i) })}><X className="h-3.5 w-3.5" /></button>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {editable && <button className="mt-1 text-[11px] text-esynapse-500 underline" onClick={() => setForm({ ...form, items: [...form.items, { epp: '', cantidad: 1, talla: '', observaciones: '' }] })}>+ Agregar EPP</button>}
            </div>
            <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} disabled={!editable} value={form.observaciones} onChange={(v) => setForm({ ...form, observaciones: v })} /></div>
            {form.cargo_papel_url && <a className="text-xs text-esynapse-500 underline" href={form.cargo_papel_url} target="_blank" rel="noreferrer">Ver el cargo firmado en papel</a>}
            {err && <Aviso texto={err} />}
            {firma && (
              <div className="rounded-lg border-2 border-esynapse-500/50 p-3 text-xs">
                <p className="mb-2 flex items-center gap-1 font-semibold"><KeyRound className="h-4 w-4" /> Firma de la entrega</p>
                <div className="mb-2 flex gap-3"><label className="flex items-center gap-1"><input type="radio" checked={firma.modo === 'pin'} onChange={() => setFirma({ ...firma, modo: 'pin', err: '' })} /> El trabajador firma en pantalla ({firma.estadoPin === 'usuario' ? 'contraseña de su usuario' : 'PIN'})</label><label className="flex items-center gap-1"><input type="radio" checked={firma.modo === 'papel'} onChange={() => setFirma({ ...firma, modo: 'papel', err: '' })} /> Cargo firmado en papel (adjunto)</label></div>
                <div className="grid gap-3 md:grid-cols-3">
                  {firma.modo === 'pin' && ['sin_pin', 'bloqueado'].includes(firma.estadoPin) && <>
                    <div><label className={lbl}>Nuevo PIN del trabajador (4 a 6 dígitos)</label><input type="password" inputMode="numeric" autoComplete="off" className={inp} value={firma.pinNuevo} onChange={(e) => setFirma({ ...firma, pinNuevo: e.target.value.replace(/\D/g, '').slice(0, 6) })} /></div>
                    <div><label className={lbl}>Confirme el PIN</label><input type="password" inputMode="numeric" autoComplete="off" className={inp} value={firma.pinConf} onChange={(e) => setFirma({ ...firma, pinConf: e.target.value.replace(/\D/g, '').slice(0, 6) })} /></div>
                  </>}
                  {firma.modo === 'pin' && firma.estadoPin === 'usuario' && <div><label className={lbl}>Contraseña del trabajador (su usuario)</label><input type="password" autoComplete="off" className={inp} value={firma.claveT} onChange={(e) => setFirma({ ...firma, claveT: e.target.value })} /></div>}
                  {firma.modo === 'pin' && firma.estadoPin === 'activo' && <div><label className={lbl}>PIN del trabajador</label><input type="password" inputMode="numeric" autoComplete="off" className={inp} value={firma.pin} onChange={(e) => setFirma({ ...firma, pin: e.target.value.replace(/\D/g, '').slice(0, 6) })} /></div>}
                  {firma.modo === 'papel' && <div className="md:col-span-2"><label className={lbl}>Cargo firmado (escaneado)</label><input type="file" className="text-xs" onChange={(e) => setFirma({ ...firma, archivo: e.target.files[0] || null })} /></div>}
                  <div><label className={lbl}>Su contraseña (responsable de la entrega)</label><input type="password" autoComplete="current-password" className={inp} value={firma.password} onChange={(e) => setFirma({ ...firma, password: e.target.value })} /></div>
                </div>
                {firma.modo === 'pin' && firma.estadoPin === 'bloqueado' && <p className="mt-2 text-red-600">El PIN del trabajador está bloqueado: restablézcalo en «Por trabajador» o use el cargo en papel.</p>}
                {firma.modo === 'pin' && firma.estadoPin === 'sin_pin' && <p className="mt-2 text-slate-500">Primera entrega: el trabajador crea su PIN, que usará en las siguientes. Se guarda cifrado; nadie más lo conoce.</p>}
                {firma.err && <p className="mt-2 rounded bg-red-500/10 px-2 py-1 text-red-600">{firma.err}</p>}
                <div className="mt-2 flex justify-end gap-2"><button className="btn-secondary" onClick={() => setFirma(null)}>Cancelar</button><button className="btn-primary" onClick={firmar}>Firmar</button></div>
              </div>
            )}
            <div className="flex flex-wrap justify-end gap-2">
              {form.id && form.estado === 'en_registro' && puedeEliminar && <button className="btn-secondary text-red-600" onClick={anular}>Anular</button>}
              {form.id && form.estado === 'firmada' && puedeEditar && <button className="btn-secondary" onClick={devolver}>Registrar devolución</button>}
              {editable && puedeEditar && <button className="btn-secondary" onClick={guardar}>Guardar</button>}
              {editable && puedeEditar && !firma && <button className="btn-primary" onClick={prepararFirma}>Firmar la entrega</button>}
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

function PorTrabajador({ trab, setTrab, abrirPdf, confirmar, setError, puedeAprobar, resumen, alCambiar }) {
  const trabajadores = useTrabajadores()
  const [d, setD] = useState(null)
  const cargar = useCallback(() => { if (trab) api.sst.estadoEpp(trab).then(setD).catch((e) => setError(e.message)); else setD(null) }, [trab, setError])
  useEffect(() => { cargar() }, [cargar])
  const restablecer = async () => { if (await confirmar({ titulo: 'Restablecer el PIN', mensaje: `${d.nombre} creará un PIN nuevo en su próxima entrega.`, textoConfirmar: 'Restablecer' })) { await api.sst.restablecerPin(d.trabajador); cargar(); alCambiar() } }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select className="input-esynapse w-96" value={trab} onChange={(e) => setTrab(e.target.value)}><option value="">— Elija un trabajador —</option>{trabajadores.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo} · {t.puesto_nombre}</option>)}</select>
        {d && <><Chip par={PIN[d.estado_pin]} />{puedeAprobar && ['activo', 'bloqueado'].includes(d.estado_pin) && <button className="text-xs text-esynapse-500 underline" onClick={restablecer}>Restablecer PIN</button>}<button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => abrirPdf(api.sst.tarjetaEppPdf(d.trabajador))}><FileText className="h-3.5 w-3.5" /> Registro de entregas (PDF)</button></>}
      </div>
      {d && (
        <div className="card-esynapse overflow-x-auto">
          <p className="px-3 pt-2 text-xs text-slate-500">{d.puesto} · {d.area}. Los EPP requeridos salen de la matriz por puesto (y laboratorio).</p>
          <table className="tabla-ficha w-full text-xs">
            <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">EPP</th><th className="px-2 text-center">Tipo</th><th className="px-2 text-center">Matriz</th><th className="px-2 text-right">Última entrega</th><th className="px-2 text-right">Renovar el</th><th className="px-2 text-center">Situación</th></tr></thead>
            <tbody>
              {d.filas.map((f) => (
                <tr key={f.epp} className="border-b border-slate-100 dark:border-slate-800/60"><td className="px-2 py-1.5">{f.nombre}</td><td className="px-2 text-center">{f.tipo}</td><td className="px-2 text-center">{f.nivel === 'obligatorio' ? 'Obligatorio' : f.nivel === 'segun_tarea' ? 'Según la tarea' : '—'}</td>
                  <td className="px-2 text-right">{f.entregado ? `${fecha(f.entregado)} · ${f.entrega}` : '—'}</td><td className="px-2 text-right">{fecha(f.renovar_el) || '—'}</td><td className="px-2 text-center"><Chip par={SIT[f.estado]} /></td></tr>
              ))}
              {d.filas.length === 0 && <tr><td colSpan={6} className="py-6 text-slate-400">Su puesto no tiene EPP en la matriz.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {!d && resumen && (resumen.faltan.length > 0 || resumen.sin_devolver.length > 0 || resumen.pin_bloqueados.length > 0) && (
        <div className="grid gap-3 text-xs md:grid-cols-3">
          <div className="card-esynapse p-3"><p className="mb-1 font-semibold">EPP obligatorios sin entregar</p>{[...new Set(resumen.faltan.map((x) => x.nombre))].map((n) => <button key={n} className="block text-left text-esynapse-500 underline" onClick={() => setTrab(String(resumen.faltan.find((x) => x.nombre === n).trabajador))}>{n} ({resumen.faltan.filter((x) => x.nombre === n).length})</button>)}{!resumen.faltan.length && '—'}</div>
          <div className="card-esynapse p-3"><p className="mb-1 font-semibold">Cesados con EPP sin devolver</p>{resumen.sin_devolver.map((x, i) => <p key={i}>{x.nombre}: {x.epp}</p>)}{!resumen.sin_devolver.length && '—'}</div>
          <div className="card-esynapse p-3"><p className="mb-1 font-semibold">PIN bloqueados</p>{resumen.pin_bloqueados.map((x) => <button key={x.trabajador} className="block text-esynapse-500 underline" onClick={() => setTrab(String(x.trabajador))}>{x.nombre}</button>)}{!resumen.pin_bloqueados.length && '—'}</div>
        </div>
      )}
    </div>
  )
}

function MatrizEpp({ areasOrg, puestos, confirmar, setError, abrirPdf, puedeEditar, puedeCrear, puedeEliminar }) {
  const [perfiles, setPerfiles] = useState([])
  const [catalogo, setCatalogo] = useState([])
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => { api.sst.matrizEpp().then(setPerfiles).catch((e) => setError(e.message)); api.sst.eppCatalogo().then(setCatalogo).catch(() => {}) }, [setError])
  useEffect(() => { cargar() }, [cargar])
  const usados = useMemo(() => catalogo.filter((c) => perfiles.some((p) => p.requisitos.some((r) => r.epp === c.id))), [catalogo, perfiles])
  const marca = (p, c) => ({ obligatorio: 'x', segun_tarea: 'x*' }[p.requisitos.find((r) => r.epp === c.id)?.nivel] || '')
  const guardar = async () => {
    setErr('')
    const datos = { nombre: form.nombre, grupo: form.grupo, puestos: form.puestos, area: form.area || null, en_campo: form.en_campo }
    try {
      const p = form.id ? await api.sst.editarPerfilEpp(form.id, datos) : await api.sst.crearPerfilEpp({ ...datos, orden: perfiles.length + 1 })
      await api.sst.requisitosEpp(p.id, Object.entries(form.req).filter(([, v]) => v).map(([epp, nivel]) => ({ epp: Number(epp), nivel })))
      setForm(null); cargar()
    } catch (e) { setErr(e.message) }
  }
  const quitar = async (p) => { if (await confirmar({ titulo: 'Quitar de la matriz', mensaje: p.nombre, textoConfirmar: 'Quitar', peligro: true })) { await api.sst.desactivarPerfilEpp(p.id); cargar() } }
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs"><span className="text-slate-500">x: obligatorio · x*: según la tarea. Un perfil aplica a sus puestos (y al laboratorio, si lo indica); los de servicio en campo se agregan al entregar para campo.</span>
        <div className="ml-auto flex gap-2"><button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.sst.matrizEppPdf())}><FileText className="h-3.5 w-3.5" /> PDF</button>{puedeCrear && <button className="btn-primary !py-1 text-xs" onClick={() => { setErr(''); setForm({ nombre: '', grupo: '', puestos: [], area: '', en_campo: false, req: {} }) }}><Plus className="h-3.5 w-3.5" /> Agregar perfil</button>}</div></div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-ficha w-full text-[11px]">
          <thead><tr className="border-b border-slate-200 text-[11px] text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Área</th><th className="px-2">Puesto / perfil</th><th className="px-2">Puestos del organigrama</th>{usados.map((c) => <th key={c.id} className="max-w-[4.5rem] px-1 font-medium">{c.nombre}</th>)}<th /></tr></thead>
          <tbody>
            {perfiles.map((p) => (
              <tr key={p.id} className="border-b border-slate-100 dark:border-slate-800/60">
                <td className="px-2 py-1">{p.grupo}</td><td className="max-w-[16rem] px-2">{p.nombre}{p.en_campo && <span className="block text-[11px] text-blue-600">Servicio en campo</span>}</td>
                <td className="max-w-[14rem] px-2 text-[11px]">{p.puestos_nombres.join(', ') || (p.en_campo ? '—' : <span className="text-amber-600">Sin puesto asignado</span>)}{p.area_nombre && <span className="block text-slate-500">{p.area_nombre}</span>}</td>
                {usados.map((c) => <td key={c.id} className="px-1 font-semibold">{marca(p, c)}</td>)}
                <td className="whitespace-nowrap px-1">{puedeEditar && <button className="p-1 text-slate-500" onClick={() => { setErr(''); setForm({ ...p, area: p.area || '', req: Object.fromEntries(p.requisitos.map((r) => [r.epp, r.nivel])) }) }}><Pencil className="h-3.5 w-3.5" /></button>}{puedeEliminar && <button className="p-1 text-red-500" onClick={() => quitar(p)}><Trash2 className="h-3.5 w-3.5" /></button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? form.nombre : 'Perfil de la matriz de EPP'} onCerrar={() => setForm(null)} ancho="max-w-4xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Área de la matriz</label><input className={inp} value={form.grupo} onChange={(e) => setForm({ ...form, grupo: e.target.value })} /></div>
              <div className="md:col-span-2"><label className={lbl}>Puesto / perfil (como figura en la matriz)</label><input className={inp} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div>
            </div>
            <div><label className={lbl}>Puestos del organigrama a los que aplica</label><div className="grid max-h-36 gap-1 overflow-y-auto rounded border border-slate-200 p-2 text-xs md:grid-cols-3 dark:border-slate-800">{puestos.filter((p) => p.is_active !== false).map((p) => <label key={p.id} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" checked={form.puestos.includes(p.id)} onChange={() => setForm({ ...form, puestos: form.puestos.includes(p.id) ? form.puestos.filter((x) => x !== p.id) : [...form.puestos, p.id] })} />{p.nombre}</label>)}</div></div>
            <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Solo en el área o laboratorio (opcional)</label><select className={inp} value={String(form.area || '')} onChange={(e) => setForm({ ...form, area: e.target.value })}><option value="">— (todas)</option>{areasOrg.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select></div>
              <label className="flex items-center gap-1.5 pt-6 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={form.en_campo} onChange={(e) => setForm({ ...form, en_campo: e.target.checked })} /> Servicio en campo (se agrega al entregar para campo)</label>
            </div>
            <div><label className={lbl}>EPP</label><div className="grid gap-1 text-xs md:grid-cols-3">{catalogo.map((c) => <label key={c.id} className="flex items-center gap-1"><select className="rounded border border-slate-300 bg-transparent px-1 py-0.5 text-[11px] dark:border-slate-700" value={form.req[c.id] || ''} onChange={(e) => setForm({ ...form, req: { ...form.req, [c.id]: e.target.value } })}><option value="">—</option><option value="obligatorio">x</option><option value="segun_tarea">x*</option></select>{c.nombre}</label>)}</div></div>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}

function CatalogoEpp({ setError, puedeCrear, puedeEditar, puedeEliminar, confirmar }) {
  const [items, setItems] = useState([])
  const [cat, setCat] = useState(null)
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.eppCatalogo().then(setItems).catch((e) => setError(e.message)), [setError])
  useEffect(() => { cargar(); api.sst.catalogosEpp().then(setCat).catch(() => {}) }, [cargar])
  const guardar = async () => { setErr(''); const datos = { ...form, vida_util_meses: form.vida_util_meses === '' ? null : Number(form.vida_util_meses) }; try { form.id ? await api.sst.editarEpp(form.id, datos) : await api.sst.crearEpp(datos); setForm(null); cargar() } catch (e) { setErr(e.message) } }
  const quitar = async (c) => { if (await confirmar({ titulo: 'Desactivar EPP', mensaje: c.nombre, textoConfirmar: 'Desactivar', peligro: true })) { await api.sst.desactivarEpp(c.id); cargar() } }
  return (
    <div className="space-y-2">
      <div className="flex items-center"><p className="text-xs text-slate-500">La vida útil referencial calcula la fecha de renovación de cada EPP entregado. Sin vida útil no se alerta la renovación.</p>{puedeCrear && <button className="btn-primary ml-auto !py-1 text-xs" onClick={() => { setErr(''); setForm({ nombre: '', tipo: 'manos', clasificacion: 'especifico', marca_modelo: '', certificacion: '', vida_util_meses: '', descartable: false }) }}><Plus className="h-3.5 w-3.5" /> Agregar EPP</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">EPP</th><th className="px-2 text-center">Tipo</th><th className="px-2 text-center">Clasificación</th><th className="px-2">Marca / modelo</th><th className="px-2">Certificación</th><th className="px-2 text-right">Vida útil</th><th className="px-2 text-center">Descartable</th><th /></tr></thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id} className="border-b border-slate-100 dark:border-slate-800/60"><td className="px-2 py-1.5">{c.nombre}</td><td className="px-2 text-center">{c.tipo_display}</td><td className="px-2 text-center">{c.clasificacion_display}</td><td className="px-2">{c.marca_modelo || '—'}</td><td className="px-2">{c.certificacion || '—'}</td>
                <td className="px-2 text-right">{c.vida_util_meses ? `${c.vida_util_meses} meses` : <span className="text-amber-600">Sin definir</span>}</td><td className="px-2 text-center">{c.descartable ? 'Sí' : 'No'}</td>
                <td className="whitespace-nowrap px-1">{puedeEditar && <button className="p-1 text-slate-500" onClick={() => { setErr(''); setForm({ ...c, vida_util_meses: c.vida_util_meses ?? '' }) }}><Pencil className="h-3.5 w-3.5" /></button>}{puedeEliminar && <button className="p-1 text-red-500" onClick={() => quitar(c)}><Trash2 className="h-3.5 w-3.5" /></button>}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? form.nombre : 'Agregar EPP al catálogo'} onCerrar={() => setForm(null)} ancho="max-w-2xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>EPP</label><input className={inp} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div>
              <div><label className={lbl}>Tipo de protección</label><select className={inp} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{(cat?.tipos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Clasificación</label><select className={inp} value={form.clasificacion} onChange={(e) => setForm({ ...form, clasificacion: e.target.value })}>{(cat?.clasificaciones || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Marca / modelo</label><input className={inp} value={form.marca_modelo} onChange={(e) => setForm({ ...form, marca_modelo: e.target.value })} /></div>
              <div><label className={lbl}>Certificación</label><input className={inp} value={form.certificacion} onChange={(e) => setForm({ ...form, certificacion: e.target.value })} /></div>
              <div><label className={lbl}>Vida útil referencial (meses)</label><input type="number" className={inp} value={form.vida_util_meses} onChange={(e) => setForm({ ...form, vida_util_meses: e.target.value })} /></div>
            </div>
            <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={form.descartable} onChange={(e) => setForm({ ...form, descartable: e.target.checked })} /> Descartable (no se devuelve al cesar)</label>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ============================================================================ Vigilancia médica */
export function VigilanciaMedica(props) {
  const [vista, setVista] = useState('trabajadores')
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">Solo aptitud y restricciones, sin diagnóstico: los resultados clínicos los custodia el médico ocupacional.</p>
      <Sub valor={vista} onChange={setVista} opciones={[['trabajadores', 'Por trabajador'], ['evaluaciones', 'Evaluaciones médicas']]} />
      {vista === 'trabajadores' && <Vigilancia {...props} />}
      {vista === 'evaluaciones' && <Evaluaciones {...props} />}
    </div>
  )
}

const hoy = () => hoyLocal()

function Anexo4({ setError, puedeEditar }) {
  const [d, setD] = useState(null)
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.anexo4().then(setD).catch((e) => setError(e.message)), [setError])
  useEffect(() => { cargar() }, [cargar])
  const registrar = async () => {
    setErr('')
    if (!form.archivo) { setErr('Adjunte el informe presentado.'); return }
    const fd = new FormData(); fd.append('anio', form.anio); fd.append('fecha_presentacion', form.fecha); fd.append('observaciones', form.observaciones); fd.append('archivo', form.archivo)
    if (form.reemplazar) { fd.append('reemplazar', '1'); fd.append('motivo', form.motivo) }
    try { setD(await api.sst.registrarAnexo4(fd)); setForm(null) } catch (e) { setErr(e.message) }
  }
  if (!d) return null
  const p = d.pendiente
  return (
    <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-semibold">Informe anual de actividades de vigilancia médica (Anexo 4)</p>
        {p ? <Chip par={SIT[p.estado === 'vencido' ? 'vencido' : 'por_vencer']} extra={` · informe ${p.anio} · plazo ${fecha(p.limite)}`} /> : <Chip par={['Al día', SIT.vigente[1]]} />}
        {d.informes.map((i) => <span key={i.anio} title={i.observaciones}><a className="text-esynapse-500 underline" href={i.archivo_url} target="_blank" rel="noreferrer">{i.anio} (presentado {fecha(i.fecha_presentacion)})</a>{puedeEditar && !form && <button className="ml-1 text-[11px] text-slate-500 underline" onClick={() => { setErr(''); setForm({ anio: i.anio, fecha: hoy(), observaciones: '', archivo: null, reemplazar: true, motivo: '' }) }}>reemplazar</button>}</span>)}
        {puedeEditar && !form && <button className="ml-auto text-esynapse-500 underline" onClick={() => { setErr(''); setForm({ anio: p?.anio || new Date().getFullYear() - 1, fecha: hoy(), observaciones: '', archivo: null, reemplazar: false, motivo: '' }) }}>Registrar presentación</button>}
      </div>
      <p className="mt-1 text-slate-500">Lo presenta el médico ocupacional o el centro médico a la autoridad de salud hasta el 31 de marzo, con lo del año anterior; aquí queda el cargo.</p>
      {form && (
        <div className="mt-2 grid gap-2 md:grid-cols-5">
          <div><label className={lbl}>Año que informa</label><input type="number" className={inp} disabled={form.reemplazar} value={form.anio} onChange={(e) => setForm({ ...form, anio: e.target.value })} /></div>
          <div><label className={lbl}>Fecha de presentación</label><input type="date" className={inp} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
          <div><label className={lbl}>Informe o cargo (archivo)</label><input type="file" className="text-xs" onChange={(e) => setForm({ ...form, archivo: e.target.files[0] || null })} /></div>
          <div><label className={lbl}>{form.reemplazar ? 'Motivo del reemplazo' : 'Observaciones'}</label><input className={inp} value={form.reemplazar ? form.motivo : form.observaciones} onChange={(e) => setForm(form.reemplazar ? { ...form, motivo: e.target.value } : { ...form, observaciones: e.target.value })} /></div>
          <div className="flex items-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={registrar}>Registrar</button></div>
          {err && <div className="md:col-span-5"><Aviso texto={err} /></div>}
        </div>
      )}
    </div>
  )
}

function Vigilancia({ setError, puedeEditar }) {
  const [filas, setFilas] = useState([])
  useEffect(() => { api.sst.vigilancia().then(setFilas).catch((e) => setError(e.message)) }, [setError])
  const cuenta = (k) => filas.filter((f) => f.estado === k).length
  return (
    <div className="space-y-2">
      <Anexo4 setError={setError} puedeEditar={puedeEditar} />
      <div className="flex flex-wrap gap-2 text-[11px]">{['sin_examen', 'sin_proximo', 'vencido', 'por_vencer'].map((k) => cuenta(k) > 0 && <Chip key={k} par={SIT[k]} extra={`: ${cuenta(k)}`} />)}<span className="text-slate-500">Próximo examen: anual para el personal operativo y cada dos años para el administrativo.</span></div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Trabajador</th><th className="px-2">Puesto / área</th><th className="px-2">Personal</th><th className="px-2 text-right">Último examen</th><th className="px-2 text-center">Aptitud</th><th className="px-2">Restricciones</th><th className="px-2 text-right">Próximo examen</th><th className="px-2 text-center">Situación</th></tr></thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.trabajador} className="border-b border-slate-100 dark:border-slate-800/60"><td className="px-2 py-1.5">{f.nombre}</td><td className="px-2">{f.puesto}<span className="block text-[11px] text-slate-500">{f.area}</span></td><td className="px-2">{f.personal === 'operativo' ? 'Operativo' : 'Administrativo'}</td>
                <td className="px-2 text-right">{f.ultimo ? `${fecha(f.ultimo)} · ${f.tipo}` : '—'}</td><td className="px-2 text-center">{f.aptitud ? <Chip par={APT[f.aptitud]} /> : '—'}</td><td className="max-w-[16rem] px-2">{f.restricciones || '—'}</td><td className="px-2 text-right">{fecha(f.proximo) || '—'}</td><td className="px-2 text-center"><Chip par={SIT[f.estado]} /></td></tr>
            ))}
            {filas.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin trabajadores activos en Organización y personal</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const EMO_VACIA = { tipo: 'periodico', fecha: hoyLocal(), centro_medico: '', medico: '', cmp: '', observaciones: '', medidas: [], trabajadores: [] }

function Evaluaciones({ confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeEliminar }) {
  const [items, setItems] = useState([])
  const [cat, setCat] = useState(null)
  const trabajadores = useTrabajadores()
  const [form, setForm] = useState(null)
  const [agregar, setAgregar] = useState([])
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.emos().then(setItems).catch((e) => setError(e.message)), [setError])
  useEffect(() => { cargar(); api.sst.catalogosEpp().then(setCat).catch(() => {}) }, [cargar])
  const editable = (!form?.id && puedeCrear) || (form?.estado === 'en_registro' && puedeEditar)
  const mostrar = (r) => setForm({ ...EMO_VACIA, ...r })
  const guardar = async () => {
    setErr('')
    try { const r = form.id ? await api.sst.editarEmo(form.id, { tipo: form.tipo, fecha: form.fecha, centro_medico: form.centro_medico, medico: form.medico, cmp: form.cmp, observaciones: form.observaciones, medidas: form.medidas }) : await api.sst.crearEmo(form); mostrar(r); cargar(); return r } catch (e) { setErr(e.message); return null }
  }
  const accion = async (nombre, datos) => { setErr(''); try { mostrar(await api.sst.accionEmo(form.id, nombre, datos)); cargar() } catch (e) { setErr(e.message) } }
  const firmar = async () => { if (!await guardar()) return; const c = await pedirClave(confirmar, 'Registrar la evaluación', 'Firma como responsable del registro. Queda de solo lectura.'); if (c !== null) accion('firmar', { password: c }) }
  const anular = async () => { const m = await confirmar({ titulo: 'Anular la evaluación', mensaje: 'Solo si se registró por error.', textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) accion('anular', { motivo: m }) }
  const subir = async (r, file) => { setErr(''); const fd = new FormData(); fd.append('id', r.id); fd.append('archivo', file); try { mostrar(await api.sst.subirEmo(form.id, fd)) } catch (e) { setErr(e.message) } }
  const [entrega, setEntrega] = useState(null)
  const entregar = async () => {
    const f = entrega
    try {
      let r
      if (f.modo === 'papel') {
        if (!f.archivo) { setEntrega({ ...f, err: 'Adjunte el cargo firmado.' }); return }
        const fd = new FormData(); fd.append('id', f.res.id); fd.append('archivo', f.archivo); fd.append('password', f.password)
        r = await api.sst.subirAccionEmo(form.id, 'entregar_resultados_papel', fd)
      } else {
        const pin = credencial(f.res.estado_pin, f)
        r = await api.sst.accionEmo(form.id, 'entregar_resultados', { id: f.res.id, password: f.password, entregado_por: f.entregadoPor, ...pin })
      }
      setEntrega(null); mostrar(r); cargar()
    } catch (e) { setEntrega({ ...f, err: e.message, pin: '' }) }
  }
  const enEval = new Set((form?.resultados || []).map((r) => r.trabajador))
  return (
    <div className="space-y-2">
      <div className="flex justify-end">{puedeCrear && <button className="btn-primary" onClick={() => { setErr(''); setForm({ ...EMO_VACIA }) }}><Plus className="h-4 w-4" /> Nueva evaluación</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">N° registro</th><th className="px-2 text-right">Fecha</th><th className="px-2 text-center">Tipo</th><th className="px-2">Centro médico</th><th className="px-2 text-right">Evaluados</th><th className="px-2 text-right">Aptos</th><th className="px-2 text-right">Con restricciones / no aptos</th><th className="px-2 text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id} onClick={() => { setErr(''); mostrar(e) }} className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${e.estado === 'anulado' ? 'opacity-50' : ''}`}>
                <td className="px-2 py-1.5 font-mono">{e.codigo}</td><td className="px-2 text-right">{fecha(e.fecha)}</td><td className="px-2 text-center">{e.tipo_display}</td><td className="px-2">{e.centro_medico || '—'}</td><td className="px-2 text-right">{e.totales.evaluados}</td><td className="px-2 text-right">{e.totales.apto}</td><td className="px-2 text-right">{e.totales.apto_restricciones + e.totales.no_apto}</td><td className="px-2 text-center"><Chip par={ESTADO[e.estado]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin evaluaciones registradas</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? `${form.codigo} — Evaluación médica ocupacional` : 'Nueva evaluación médica ocupacional'} onCerrar={() => { setForm(null); setEntrega(null) }} ancho="max-w-6xl">
        {form && (
          <div className="space-y-3 text-sm">
            {form.id && <div className="flex items-center gap-2"><Chip par={ESTADO[form.estado]} />{form.firma_registro?.nombre && <span className="text-xs text-slate-500">Registrado por {form.firma_registro.nombre} · {fechaHora(form.firma_registro.fecha)}</span>}<button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => abrirPdf(api.sst.emoPdf(form.id))}><FileText className="h-3.5 w-3.5" /> PDF</button></div>}
            <div className="grid gap-3 md:grid-cols-5">
              <div><label className={lbl}>Tipo de examen</label><select className={inp} disabled={!editable} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{(cat?.tipos_emo || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} disabled={!editable} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
              <div><label className={lbl}>Centro médico / IPRESS</label><input className={inp} disabled={!editable} value={form.centro_medico} onChange={(e) => setForm({ ...form, centro_medico: e.target.value })} /></div>
              <div><label className={lbl}>Médico ocupacional</label><input className={inp} disabled={!editable} value={form.medico} onChange={(e) => setForm({ ...form, medico: e.target.value })} /></div>
              <div><label className={lbl}>CMP</label><input className={inp} disabled={!editable} value={form.cmp} onChange={(e) => setForm({ ...form, cmp: e.target.value })} /></div>
            </div>
            {!form.id && <div><label className={lbl}>Trabajadores evaluados</label><div className="grid max-h-48 gap-1 overflow-y-auto rounded border border-slate-200 p-2 text-xs md:grid-cols-3 dark:border-slate-800">{trabajadores.map((t) => <label key={t.id} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" checked={form.trabajadores.includes(t.id)} onChange={() => setForm({ ...form, trabajadores: form.trabajadores.includes(t.id) ? form.trabajadores.filter((x) => x !== t.id) : [...form.trabajadores, t.id] })} />{t.nombre_completo}</label>)}</div></div>}
            {form.id && (
              <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
                <div className="mb-1 flex flex-wrap items-center gap-2"><p className="font-semibold">Resultados ({form.totales?.evaluados || 0})</p>
                  {editable && <><select multiple className="h-16 rounded border border-slate-300 bg-transparent text-[11px] dark:border-slate-700" value={agregar.map(String)} onChange={(e) => setAgregar([...e.target.selectedOptions].map((o) => Number(o.value)))}>{trabajadores.filter((t) => !enEval.has(t.id)).map((t) => <option key={t.id} value={t.id}>{t.nombre_completo}</option>)}</select><button className="text-esynapse-500 underline" onClick={async () => { await accion('agregar', { trabajadores: agregar }); setAgregar([]) }}>Agregar seleccionados</button></>}</div>
                <table className="tabla-ficha w-full">
                  <thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="px-1">Trabajador</th><th className="px-1">Puesto / área</th><th className="px-1 text-center">Aptitud</th><th className="px-1">Restricciones / recomendaciones (sin diagnóstico)</th><th className="px-1 text-right">Próximo examen</th><th className="px-1 text-center">Certificado</th>{form.estado === 'registrado' && <th className="px-1 text-center">Entrega de resultados</th>}<th /></tr></thead>
                  <tbody>
                    {form.resultados.map((r) => (
                      <tr key={r.id} className="border-t border-slate-100 dark:border-slate-800/60">
                        <td className="px-1 py-1">{r.trabajador_nombre}<span className="block text-[11px] text-slate-500">{r.documento}</span></td><td className="px-1 text-[11px]">{r.puesto}<span className="block text-slate-500">{r.area}</span></td>
                        <td className="px-1 text-center">{editable ? <select className={`${inp} !py-1 text-xs`} value={r.aptitud} onChange={(e) => accion('resultado', { id: r.id, aptitud: e.target.value })}><option value="">—</option>{(cat?.aptitudes || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select> : <Chip par={APT[r.aptitud]} />}</td>
                        <td className="px-1">{editable ? <input className={`${inp} !py-1 text-xs`} defaultValue={r.restricciones} onBlur={(e) => e.target.value !== r.restricciones && accion('resultado', { id: r.id, restricciones: e.target.value })} /> : r.restricciones || '—'}</td>
                        <td className="w-36 px-1 text-right">{editable ? <input type="date" className={`${inp} !py-1 text-xs`} value={r.fecha_proximo || ''} onChange={(e) => accion('resultado', { id: r.id, fecha_proximo: e.target.value })} /> : fecha(r.fecha_proximo) || '—'}</td>
                        <td className="px-1 text-center">{r.certificado_url ? <a className="text-esynapse-500 underline" href={r.certificado_url} target="_blank" rel="noreferrer">ver</a> : editable ? <label className="cursor-pointer text-esynapse-500 underline">adjuntar<input type="file" className="hidden" onChange={(e) => e.target.files[0] && subir(r, e.target.files[0])} /></label> : '—'}</td>
                        {form.estado === 'registrado' && <td className="px-1 text-center">{r.entrega_resultados?.metodo
                          ? <span className="text-[11px]"><Chip par={['Entregado', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400']} /> {METODO[r.entrega_resultados.metodo]} · {fechaHora(r.entrega_resultados.fecha)}{r.cargo_resultados_url && <> · <a className="text-esynapse-500 underline" href={r.cargo_resultados_url} target="_blank" rel="noreferrer">cargo</a></>}</span>
                          : puedeEditar ? <button className="text-esynapse-500 underline" onClick={() => setEntrega({ res: r, modo: 'pin', password: '', pin: '', pinNuevo: '', pinConf: '', entregadoPor: form.medico || '', archivo: null, err: '' })}>Registrar entrega</button> : <Chip par={['Pendiente', 'bg-amber-500/15 text-amber-600 dark:text-amber-400']} />}</td>}
                        <td>{editable && <button className="p-1 text-red-500" onClick={() => accion('quitar', { id: r.id })}><X className="h-3.5 w-3.5" /></button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {entrega && (
              <div className="rounded-lg border-2 border-esynapse-500/50 p-3 text-xs">
                <p className="mb-2 flex items-center gap-1 font-semibold"><KeyRound className="h-4 w-4" /> Cargo de entrega de resultados — {entrega.res.trabajador_nombre}</p>
                <p className="mb-2 text-slate-500">El trabajador declara haber recibido de forma personal y confidencial el resultado de su evaluación médica.</p>
                <div className="mb-2 flex gap-3"><label className="flex items-center gap-1"><input type="radio" checked={entrega.modo === 'pin'} onChange={() => setEntrega({ ...entrega, modo: 'pin', err: '' })} /> El trabajador firma en pantalla ({entrega.res.estado_pin === 'usuario' ? 'contraseña de su usuario' : 'PIN'})</label><label className="flex items-center gap-1"><input type="radio" checked={entrega.modo === 'papel'} onChange={() => setEntrega({ ...entrega, modo: 'papel', err: '' })} /> Cargo firmado en papel (adjunto)</label></div>
                <div className="grid gap-3 md:grid-cols-4">
                  {entrega.modo === 'pin' && ['sin_pin', 'bloqueado'].includes(entrega.res.estado_pin) && <>
                    <div><label className={lbl}>Nuevo PIN del trabajador (4 a 6 dígitos)</label><input type="password" inputMode="numeric" autoComplete="off" className={inp} value={entrega.pinNuevo} onChange={(e) => setEntrega({ ...entrega, pinNuevo: e.target.value.replace(/\D/g, '').slice(0, 6) })} /></div>
                    <div><label className={lbl}>Confirme el PIN</label><input type="password" inputMode="numeric" autoComplete="off" className={inp} value={entrega.pinConf} onChange={(e) => setEntrega({ ...entrega, pinConf: e.target.value.replace(/\D/g, '').slice(0, 6) })} /></div>
                  </>}
                  {entrega.modo === 'pin' && entrega.res.estado_pin === 'usuario' && <div><label className={lbl}>Contraseña del trabajador (su usuario)</label><input type="password" autoComplete="off" className={inp} value={entrega.claveT || ''} onChange={(e) => setEntrega({ ...entrega, claveT: e.target.value })} /></div>}
                  {entrega.modo === 'pin' && entrega.res.estado_pin === 'activo' && <div><label className={lbl}>PIN del trabajador</label><input type="password" inputMode="numeric" autoComplete="off" className={inp} value={entrega.pin} onChange={(e) => setEntrega({ ...entrega, pin: e.target.value.replace(/\D/g, '').slice(0, 6) })} /></div>}
                  {entrega.modo === 'pin' && <div><label className={lbl}>Entregado por (médico o centro)</label><input className={inp} value={entrega.entregadoPor} onChange={(e) => setEntrega({ ...entrega, entregadoPor: e.target.value })} /></div>}
                  {entrega.modo === 'papel' && <div className="md:col-span-2"><label className={lbl}>Cargo firmado (escaneado)</label><input type="file" className="text-xs" onChange={(e) => setEntrega({ ...entrega, archivo: e.target.files[0] || null })} /></div>}
                  <div><label className={lbl}>Su contraseña (quien registra)</label><input type="password" autoComplete="current-password" className={inp} value={entrega.password} onChange={(e) => setEntrega({ ...entrega, password: e.target.value })} /></div>
                </div>
                {entrega.modo === 'pin' && entrega.res.estado_pin === 'bloqueado' && <p className="mt-2 text-red-600">El PIN del trabajador está bloqueado: restablézcalo en EPP › Por trabajador o use el cargo en papel.</p>}
                {entrega.modo === 'pin' && entrega.res.estado_pin === 'sin_pin' && <p className="mt-2 text-slate-500">El trabajador aún no tiene PIN: lo crea ahora y es el mismo que usa en la entrega de EPP.</p>}
                {entrega.err && <p className="mt-2 rounded bg-red-500/10 px-2 py-1 text-red-600">{entrega.err}</p>}
                <div className="mt-2 flex justify-end gap-2"><button className="btn-secondary" onClick={() => setEntrega(null)}>Cancelar</button><button className="btn-primary" onClick={entregar}>Firmar el cargo</button></div>
              </div>
            )}
            <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
              <p className="mb-1 font-semibold">Medidas correctivas</p>
              {(form.medidas || []).map((m, i) => (
                <div key={i} className="mb-1 grid gap-1 md:grid-cols-12">
                  <input className={`${inp} !py-1 text-xs md:col-span-6`} disabled={!editable} placeholder="Descripción" value={m.descripcion} onChange={(e) => setForm({ ...form, medidas: form.medidas.map((x, j) => (j === i ? { ...x, descripcion: e.target.value } : x)) })} />
                  <input className={`${inp} !py-1 text-xs md:col-span-2`} disabled={!editable} placeholder="Responsable" value={m.responsable} onChange={(e) => setForm({ ...form, medidas: form.medidas.map((x, j) => (j === i ? { ...x, responsable: e.target.value } : x)) })} />
                  <input type="date" className={`${inp} !py-1 text-xs md:col-span-2`} disabled={!editable} value={m.fecha} onChange={(e) => setForm({ ...form, medidas: form.medidas.map((x, j) => (j === i ? { ...x, fecha: e.target.value } : x)) })} />
                  <select className={`${inp} !py-1 text-xs md:col-span-1`} disabled={!editable} value={m.estado} onChange={(e) => setForm({ ...form, medidas: form.medidas.map((x, j) => (j === i ? { ...x, estado: e.target.value } : x)) })}><option value="pendiente">Pendiente</option><option value="en ejecución">En ejecución</option><option value="realizada">Realizada</option></select>
                  {editable && <button className="p-1 text-red-500" onClick={() => setForm({ ...form, medidas: form.medidas.filter((_, j) => j !== i) })}><X className="h-3.5 w-3.5" /></button>}
                </div>
              ))}
              {editable && <button className="text-[11px] text-esynapse-500 underline" onClick={() => setForm({ ...form, medidas: [...(form.medidas || []), { descripcion: '', responsable: '', fecha: '', estado: 'pendiente' }] })}>+ Agregar medida</button>}
            </div>
            <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} disabled={!editable} value={form.observaciones} onChange={(v) => setForm({ ...form, observaciones: v })} /></div>
            {err && <Aviso texto={err} />}
            {editable && puedeEditar && <div className="flex justify-end gap-2">{form.id && puedeEliminar && <button className="btn-secondary text-red-600" onClick={anular}>Anular</button>}<button className="btn-secondary" onClick={guardar}>{form.id ? 'Guardar' : 'Crear evaluación'}</button>{form.id && <button className="btn-primary" onClick={firmar}>Firmar el registro</button>}</div>}
          </div>
        )}
      </Modal>
    </div>
  )
}

