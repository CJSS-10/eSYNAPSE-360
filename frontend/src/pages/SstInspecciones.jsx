import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, CheckCheck, FileText, Pencil, Plus, Search, Trash2, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { Vistas as Sub } from '../components/NavModulo.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import { api } from '../lib/api.js'
import { fecha, fechaHora } from '../lib/fecha.js'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']
// Estados (regla 10): gris registro · azul en proceso · verde cerrado · rojo anulado/vencido.
const ESTADO = {
  en_registro: ['En registro', 'bg-slate-500/15 text-slate-500'],
  con_acciones: ['Con acciones pendientes', 'bg-blue-500/15 text-blue-600 dark:text-blue-400'],
  cerrada: ['Cerrada', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  anulada: ['Anulada', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  registrado: ['Registrado', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  anulado: ['Anulado', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  pendiente: ['Pendiente', 'bg-slate-500/15 text-slate-500'],
  en_proceso: ['En proceso', 'bg-blue-500/15 text-blue-600 dark:text-blue-400'],
  ejecutada: ['Ejecutada', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  no_aplica: ['No aplica', 'bg-slate-500/15 text-slate-500'],
}
const VENC = { vencido: ['Vencido', 'bg-red-500/15 text-red-600 dark:text-red-400'], por_vencer: ['Por vencer', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'], vigente: ['Vigente', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'] }
// Programa: verde realizado · azul en plazo · gris programado · rojo atrasado.
const SITUACION = { realizado: 'bg-emerald-500/25 text-emerald-700 dark:text-emerald-300', en_plazo: 'bg-blue-500/20 text-blue-700 dark:text-blue-300', programado: 'bg-slate-500/15 text-slate-500', atrasado: 'bg-red-500/20 text-red-600 dark:text-red-400', no_programado: '', antes_del_sistema: 'text-slate-300 dark:text-slate-600' }
const MALO = { c_nc_na: 'NC', si_no_na: 'NO', optimo_mal_na: 'MAL', bueno_mal: 'M' }

const Chip = ({ par, extra }) => (par ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{par[0]}{extra}</span> : null)
function Aviso({ texto }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [texto])
  return <p ref={ref} className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p>
}
const pedirClave = (confirmar, titulo, mensaje) => confirmar({ titulo, mensaje, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
const nombreUsuario = (u) => u.nombre_completo || [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username
// Respuesta «mala»: la de la escala, o la buena si el criterio es invertido («Requiere cambio»).
const esMala = (v, escala, invertido, valores) => (v ? (invertido ? v === valores[0]?.[0] : v === MALO[escala]) : false)

/* =================================================================================== Inspecciones */
export function Inspecciones(props) {
  const [vista, setVista] = useState('lista')
  const [resumen, setResumen] = useState(null)
  const cargarResumen = useCallback(() => api.sst.resumenInspecciones().then(setResumen).catch(() => {}), [])
  useEffect(() => { cargarResumen() }, [cargarResumen])
  const venc = resumen?.vencimientos || []
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Sub valor={vista} onChange={setVista} opciones={[['lista', 'Inspecciones'], ['programa', 'Programa'], ['elementos', 'Elementos de seguridad'], ['plantillas', 'Plantillas']]} />
        {resumen && (
          <div className="flex flex-wrap gap-1.5 text-[11px]">
            {venc.filter((v) => v.estado === 'vencido').length > 0 && <button onClick={() => setVista('elementos')} className="rounded bg-red-500/15 px-2 py-0.5 font-semibold text-red-600 dark:text-red-400">{venc.filter((v) => v.estado === 'vencido').length} vencimiento(s)</button>}
            {venc.filter((v) => v.estado === 'por_vencer').length > 0 && <button onClick={() => setVista('elementos')} className="rounded bg-amber-500/15 px-2 py-0.5 font-semibold text-amber-600 dark:text-amber-400">{venc.filter((v) => v.estado === 'por_vencer').length} por vencer (30 días)</button>}
            {resumen.acciones_pendientes.filter((a) => a.vencida).length > 0 && <span className="rounded bg-red-500/15 px-2 py-0.5 font-semibold text-red-600 dark:text-red-400">{resumen.acciones_pendientes.filter((a) => a.vencida).length} acción(es) vencida(s)</span>}
            {resumen.inspecciones_atrasadas.length > 0 && <button onClick={() => setVista('programa')} className="rounded bg-red-500/15 px-2 py-0.5 font-semibold text-red-600 dark:text-red-400">{resumen.inspecciones_atrasadas.length} inspección(es) atrasada(s)</button>}
          </div>
        )}
      </div>
      {vista === 'lista' && <ListaInspecciones {...props} alCambiar={cargarResumen} />}
      {vista === 'programa' && <ProgramaInspecciones {...props} />}
      {vista === 'elementos' && <Elementos {...props} vencimientos={venc} alCambiar={cargarResumen} />}
      {vista === 'plantillas' && <Plantillas {...props} />}
    </div>
  )
}

const NUEVA = { plantilla: '', fecha: new Date().toISOString().slice(0, 10), hora: '', tipo_inspeccion: 'planeada', tipo_detalle: '', area: '', lugar: '', responsable_area: '', objetivo: '', elemento: '', conductor: '', km: '', trabajadores: [] }

function ListaInspecciones({ areasOrg, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeEliminar, alCambiar }) {
  const [items, setItems] = useState([])
  const [filtro, setFiltro] = useState({ plantilla: '', estado: '', anio: String(new Date().getFullYear()), buscar: '' })
  const [plantillas, setPlantillas] = useState([])
  const [elementos, setElementos] = useState([])
  const [trabajadores, setTrabajadores] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [nueva, setNueva] = useState(null)
  const [d, setD] = useState(null)
  const [reg, setReg] = useState({})
  const [resp, setResp] = useState({})
  const [fila, setFila] = useState(null)
  const [err, setErr] = useState('')
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const p = new URLSearchParams(Object.entries(filtro).filter(([, v]) => v))
    setItems(await ultima(api.sst.inspecciones(`?${p}`)))
  }, [filtro])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  useEffect(() => {
    api.sst.plantillas().then(setPlantillas).catch(() => {})
    api.sst.elementos().then(setElementos).catch(() => {})
    api.org.trabajadores().then((t) => setTrabajadores(t.filter((x) => x.estado === 'activo'))).catch(() => {})
    api.usuarios.listar().then((u) => setUsuarios((u.results ?? u).filter((x) => x.is_active !== false))).catch(() => {})
  }, [])

  const pl = plantillas.find((p) => String(p.id) === String(nueva?.plantilla))
  // conservar: al guardar solo los datos del registro no se pierden las respuestas aún sin guardar.
  const mostrar = (x, conservar = false) => {
    setD(x)
    setReg({ fecha: x.fecha, hora: x.hora ? x.hora.slice(0, 5) : '', tipo_inspeccion: x.tipo_inspeccion, tipo_detalle: x.tipo_detalle, area: x.area || '', lugar: x.lugar, responsable_area: x.responsable_area || '', objetivo: x.objetivo, n_trabajadores: x.n_trabajadores ?? '', conclusiones: x.conclusiones, km: x.km ?? '' })
    if (!conservar) setResp({})
  }
  const abrir = async (id) => { setErr(''); mostrar(await api.sst.inspeccion(id)) }
  const accion = async (nombre, datos) => { setErr(''); try { const r = await api.sst.accionInspeccion(d.id, nombre, datos); mostrar(r); await cargar(); alCambiar(); return r } catch (e) { setErr(e.message); return null } }

  const crear = async () => {
    setErr('')
    const datos = { ...nueva }
    ;['area', 'responsable_area', 'elemento', 'conductor', 'km'].forEach((k) => { if (datos[k] === '') datos[k] = null })
    if (!datos.hora) datos.hora = null
    try { const r = await api.sst.crearInspeccion(datos); setNueva(null); await cargar(); alCambiar(); mostrar(r) } catch (e) { setErr(e.message) }
  }
  const guardarRegistro = async () => {
    setErr('')
    const datos = { ...reg }
    ;['area', 'responsable_area', 'n_trabajadores', 'km'].forEach((k) => { if (datos[k] === '') datos[k] = null })
    if (!datos.hora) datos.hora = null
    try { mostrar(await api.sst.editarInspeccion(d.id, datos), true); return true } catch (e) { setErr(e.message); return false }
  }
  // Respuestas en edición (sin guardar): id → cambios.
  const valorItem = (it) => ({ ...it, ...(resp[it.id] || {}), resultados: { ...it.resultados, ...(resp[it.id]?.resultados || {}) } })
  const cambiar = (it, campo, valor) => setResp((r) => ({ ...r, [it.id]: { ...(r[it.id] || {}), [campo]: valor } }))
  const responder = (it, clave, v) => setResp((r) => ({ ...r, [it.id]: { ...(r[it.id] || {}), resultados: { ...(r[it.id]?.resultados || {}), [clave]: v } } }))
  const pendientesGuardar = Object.keys(resp).length
  const guardarRespuestas = async () => {
    if (!pendientesGuardar) return true
    const items = Object.entries(resp).map(([id, c]) => ({ id: Number(id), ...c, ...(c.resultados ? { resultados: { ...d.items.find((i) => i.id === Number(id)).resultados, ...c.resultados } } : {}) }))
    return Boolean(await accion('responder', { items }))
  }
  const todoBueno = () => {
    const est = d.estructura
    const n = (est.criterios || []).length
    const bueno = d.valores_escala[0][0]
    const nuevo = { ...resp }
    d.items.forEach((it) => {
      const v = valorItem(it)
      const res = {}
      if (n) {
        est.criterios.forEach((c, k) => { if (!v.resultados[String(k)]) res[String(k)] = c.invertido ? MALO[est.escala] : bueno })
      } else if (!v.resultados.r) res.r = bueno
      if (Object.keys(res).length) nuevo[it.id] = { ...(nuevo[it.id] || {}), resultados: { ...(nuevo[it.id]?.resultados || {}), ...res } }
    })
    setResp(nuevo)
  }
  const firmar = async () => {
    // Se revisa antes de pedir la contraseña (el servidor vuelve a validarlo al firmar).
    const n = (est.criterios || []).length
    const vacias = d.items.map(valorItem).filter((it) => (n ? est.criterios.some((_, k) => !it.resultados[String(k)]) : !it.resultados.r))
    if (vacias.length) { setErr(`Faltan respuestas en ${vacias.length} fila(s). Use «No aplica» cuando corresponda.`); return }
    const sinAccion = nc.filter((it) => !(it.accion || '').trim() || !it.responsable_accion || !it.plazo_accion)
    if (sinAccion.length) { setErr(`Registre la acción inmediata, el responsable y el plazo de cada «no conforme» (${sinAccion.length} pendiente(s)).`); return }
    if (pendientesGuardar && !await guardarRespuestas()) return
    const c = await pedirClave(confirmar, 'Firmar la inspección', 'Como responsable del registro. Las respuestas y los datos quedan de solo lectura; los «no conforme» pasan a seguimiento de sus acciones.')
    if (c !== null) accion('firmar', { password: c })
  }
  const anular = async () => { const m = await confirmar({ titulo: 'Anular la inspección', mensaje: 'Solo si se registró por error. Queda como registro.', textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true, multilinea: true } }); if (m !== null) accion('anular', { motivo: m }) }
  const completar = async (it) => {
    const s = await confirmar({ titulo: 'Completar la acción', mensaje: `${it.texto}: ${it.accion}`, textoConfirmar: 'Registrar', entrada: { etiqueta: 'Qué se hizo', obligatorio: true, multilinea: true } })
    if (s === null) return
    const fd = new FormData(); fd.append('item_id', it.id); fd.append('seguimiento', s)
    setErr('')
    try { mostrar(await api.sst.subirInspeccion(d.id, 'completar_accion', fd)); await cargar(); alCambiar() } catch (e) { setErr(e.message) }
  }
  const [hz, setHz] = useState(null)
  const hallazgo = async () => {
    if (!await confirmar({ titulo: 'Registrar hallazgo', mensaje: `«${hz.item.texto}» se registra como ${hz.tipo === 'nc_mayor' ? 'NC mayor' : 'NC menor'} con su solicitud de acción correctiva (seguimiento y eficacia en Acciones correctivas). Úselo solo para lo relevante.`, textoConfirmar: 'Registrar' })) return
    if (await accion('registrar_hallazgo', { item_id: hz.item.id, tipo_nc: hz.tipo })) setHz(null)
  }
  const agregarFila = async () => {
    const r = await accion('agregar_fila', fila)
    if (r) setFila(null)
  }
  const quitarFila = async (it) => { if (await confirmar({ titulo: 'Quitar la fila', mensaje: it.texto, textoConfirmar: 'Quitar', peligro: true })) accion('quitar_fila', { item_id: it.id }) }

  const est = d?.estructura || {}
  const enReg = d?.estado === 'en_registro' && puedeEditar
  const vehiculo = ['vehiculo', 'moto'].includes(est.tipo_elemento)
  const elegibles = (tipo) => elementos.filter((e) => e.tipo === tipo)
  const nc = d ? d.items.map(valorItem).filter((it) => (est.criterios?.length ? est.criterios.some((c, k) => esMala(it.resultados[String(k)], est.escala, c.invertido, d.valores_escala)) : esMala(it.resultados.r, est.escala, false, d.valores_escala))) : []

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-56 pl-9" placeholder="Código, inspección, lugar…" value={filtro.buscar} onChange={(e) => setFiltro({ ...filtro, buscar: e.target.value })} /></div>
        <select className="input-esynapse w-64" value={filtro.plantilla} onChange={(e) => setFiltro({ ...filtro, plantilla: e.target.value })}><option value="">Toda inspección</option>{plantillas.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select>
        <select className="input-esynapse w-48" value={filtro.estado} onChange={(e) => setFiltro({ ...filtro, estado: e.target.value })}><option value="">Todo estado</option>{['en_registro', 'con_acciones', 'cerrada', 'anulada'].map((k) => <option key={k} value={k}>{ESTADO[k][0]}</option>)}</select>
        <input className="input-esynapse w-24" type="number" value={filtro.anio} onChange={(e) => setFiltro({ ...filtro, anio: e.target.value })} />
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setD(null); setNueva({ ...NUEVA }) }}><Plus className="h-4 w-4" /> Nueva inspección</button>}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Código</th><th className="px-2 text-right">Fecha</th><th className="px-2">Inspección</th><th className="px-2">Área / lugar</th><th className="px-2">Inspector</th><th className="px-2 text-right">Filas</th><th className="px-2 text-right">No conformes</th><th className="px-2 text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((x) => (
              <tr key={x.id} onClick={() => abrir(x.id)} className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${x.estado === 'anulada' ? 'opacity-50' : ''}`}>
                <td className="whitespace-nowrap px-2 py-2 font-mono">{x.codigo}</td><td className="whitespace-nowrap px-2 text-right">{fecha(x.fecha)}</td>
                <td className="px-2">{x.plantilla_nombre}{x.elemento_codigo && <span className="block text-[11px] text-slate-500">{x.elemento_codigo}</span>}</td>
                <td className="px-2">{[x.area_nombre, x.lugar].filter(Boolean).join(' · ') || '—'}</td><td className="px-2">{x.inspector_nombre || '—'}</td>
                <td className="px-2 text-right">{x.resumen.items}</td>
                <td className="px-2 text-right">{x.resumen.no_conformes ? <span className="font-semibold text-red-600 dark:text-red-400">{x.resumen.no_conformes}</span> : '0'}{x.resumen.acciones_vencidas > 0 && <span className="block text-[11px] font-semibold text-red-600">{x.resumen.acciones_vencidas} acción(es) vencida(s)</span>}</td>
                <td className="px-2 text-center"><Chip par={ESTADO[x.estado]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin inspecciones registradas</td></tr>}
          </tbody>
        </table>
      </div>

      {/* --- Nueva inspección */}
      <Modal abierto={Boolean(nueva)} titulo="Nueva inspección" onCerrar={() => setNueva(null)} ancho="max-w-3xl">
        {nueva && (
          <div className="space-y-3 text-sm">
            <div><label className={lbl}>Inspección (plantilla)</label><select className={inp} value={nueva.plantilla} onChange={(e) => { const p = plantillas.find((x) => String(x.id) === e.target.value); setNueva({ ...nueva, plantilla: e.target.value, objetivo: p?.objetivo || '', elemento: '' }) }}><option value="">— Elija —</option>{plantillas.map((p) => <option key={p.id} value={p.id}>{p.nombre} · {p.frecuencia_display}</option>)}</select></div>
            {pl && <p className="rounded bg-slate-500/10 px-3 py-2 text-xs text-slate-600 dark:text-slate-300">{pl.familia === 'elementos' && pl.tipo_elemento ? `Se traen los ${pl.tipo_elemento_display?.toLowerCase()}s activos del inventario (del área elegida, si tiene). Luego puede quitar o agregar filas.` : pl.familia === 'elementos' ? 'Las filas se agregan en la inspección (p. ej. cada tipo de herramienta con su cantidad).' : pl.familia === 'contenido' ? 'Se traen los productos del elemento (o el contenido mínimo de la plantilla).' : pl.familia === 'trabajadores' ? 'Se traen los trabajadores activos del área elegida; luego puede agregar o quitar.' : 'Se traen todas las preguntas de la plantilla.'}</p>}
            {pl && (pl.familia === 'contenido' || ['vehiculo', 'moto'].includes(pl.tipo_elemento)) && (
              <div className="grid gap-3 md:grid-cols-3">
                <div className="md:col-span-2"><label className={lbl}>{pl.tipo_elemento_display} inspeccionado</label><select className={inp} value={nueva.elemento} onChange={(e) => setNueva({ ...nueva, elemento: e.target.value })}><option value="">— Elija —</option>{elegibles(pl.tipo_elemento).map((e) => <option key={e.id} value={e.id}>{e.codigo} {e.ubicacion ? `· ${e.ubicacion}` : ''} {e.marca ? `· ${e.marca}` : ''}</option>)}</select>{elegibles(pl.tipo_elemento).length === 0 && <p className="mt-1 text-[11px] text-amber-600">No hay elementos de este tipo: regístrelos en «Elementos de seguridad».</p>}</div>
                {['vehiculo', 'moto'].includes(pl.tipo_elemento) && <div><label className={lbl}>Kilometraje</label><input type="number" className={inp} value={nueva.km} onChange={(e) => setNueva({ ...nueva, km: e.target.value })} /></div>}
              </div>
            )}
            {pl && ['vehiculo', 'moto'].includes(pl.tipo_elemento) && <div><label className={lbl}>Conductor</label><select className={inp} value={nueva.conductor} onChange={(e) => setNueva({ ...nueva, conductor: e.target.value })}><option value="">—</option>{trabajadores.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo}</option>)}</select></div>}
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} value={nueva.fecha} onChange={(e) => setNueva({ ...nueva, fecha: e.target.value })} /></div>
              <div><label className={lbl}>Hora</label><input type="time" className={inp} value={nueva.hora} onChange={(e) => setNueva({ ...nueva, hora: e.target.value })} /></div>
              <div><label className={lbl}>Tipo</label><select className={inp} value={nueva.tipo_inspeccion} onChange={(e) => setNueva({ ...nueva, tipo_inspeccion: e.target.value })}><option value="planeada">Planeada</option><option value="no_planeada">No planeada</option><option value="otro">Otro</option></select></div>
              {nueva.tipo_inspeccion === 'otro' && <div><label className={lbl}>Detalle</label><input className={inp} value={nueva.tipo_detalle} onChange={(e) => setNueva({ ...nueva, tipo_detalle: e.target.value })} /></div>}
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Área inspeccionada</label><select className={inp} value={nueva.area} onChange={(e) => setNueva({ ...nueva, area: e.target.value })}><option value="">—</option>{areasOrg.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select></div>
              <div><label className={lbl}>Lugar / sede (detalle)</label><input className={inp} value={nueva.lugar} onChange={(e) => setNueva({ ...nueva, lugar: e.target.value })} /></div>
              <div><label className={lbl}>Responsable del área</label><select className={inp} value={nueva.responsable_area} onChange={(e) => setNueva({ ...nueva, responsable_area: e.target.value })}><option value="">—</option>{trabajadores.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo}</option>)}</select></div>
            </div>
            <div><label className={lbl}>Objetivo</label><input className={inp} value={nueva.objetivo} onChange={(e) => setNueva({ ...nueva, objetivo: e.target.value })} /></div>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setNueva(null)}>Cancelar</button><button className="btn-primary" disabled={!nueva.plantilla} onClick={crear}>Crear inspección</button></div>
          </div>
        )}
      </Modal>

      {/* --- Detalle */}
      <Modal abierto={Boolean(d)} titulo={d ? `${d.codigo} — ${est.nombre || d.plantilla_nombre}` : ''} onCerrar={() => setD(null)} panel ancho="max-w-7xl">
        {d && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              {['en_registro', 'con_acciones', 'cerrada'].map((k, i) => <span key={k} className={`rounded-full px-2.5 py-0.5 text-[11px] ${d.estado === k ? 'bg-esynapse-600 text-white' : 'bg-slate-500/10 text-slate-500'}`}>{i + 1}. {ESTADO[k][0]}</span>)}
              {d.estado === 'anulada' && <Chip par={ESTADO.anulada} />}
              <button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => abrirPdf(api.sst.inspeccionPdf(d.id))}><FileText className="h-3.5 w-3.5" /> PDF</button>
            </div>
            {d.estado === 'anulada' && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600">Anulada: {d.motivo_anulacion}</p>}

            <div className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
              <p className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Datos de la inspección</p>
              <div className="grid gap-2 md:grid-cols-6">
                <div><label className={lbl}>Fecha</label><input type="date" className={inp} disabled={!enReg} value={reg.fecha} onChange={(e) => setReg({ ...reg, fecha: e.target.value })} /></div>
                <div><label className={lbl}>Hora</label><input type="time" className={inp} disabled={!enReg} value={reg.hora} onChange={(e) => setReg({ ...reg, hora: e.target.value })} /></div>
                <div><label className={lbl}>Tipo</label><select className={inp} disabled={!enReg} value={reg.tipo_inspeccion} onChange={(e) => setReg({ ...reg, tipo_inspeccion: e.target.value })}><option value="planeada">Planeada</option><option value="no_planeada">No planeada</option><option value="otro">Otro</option></select></div>
                <div><label className={lbl}>Área</label><select className={inp} disabled={!enReg} value={reg.area} onChange={(e) => setReg({ ...reg, area: e.target.value })}><option value="">—</option>{areasOrg.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select></div>
                <div><label className={lbl}>Lugar / sede</label><input className={inp} disabled={!enReg} value={reg.lugar} onChange={(e) => setReg({ ...reg, lugar: e.target.value })} /></div>
                <div><label className={lbl}>{vehiculo ? 'Kilometraje' : 'N° trabajadores'}</label>{vehiculo ? <input type="number" className={inp} disabled={!enReg} value={reg.km} onChange={(e) => setReg({ ...reg, km: e.target.value })} /> : <input type="number" className={inp} disabled={!enReg} value={reg.n_trabajadores} onChange={(e) => setReg({ ...reg, n_trabajadores: e.target.value })} />}</div>
              </div>
              <div className="mt-2 grid gap-2 md:grid-cols-3">
                <div><label className={lbl}>Responsable del área</label><select className={inp} disabled={!enReg} value={reg.responsable_area} onChange={(e) => setReg({ ...reg, responsable_area: e.target.value })}><option value="">—</option>{trabajadores.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo}</option>)}</select></div>
                <div className="md:col-span-2"><label className={lbl}>Objetivo</label><input className={inp} disabled={!enReg} value={reg.objetivo} onChange={(e) => setReg({ ...reg, objetivo: e.target.value })} /></div>
              </div>
              {d.elemento_codigo && <p className="mt-2 text-slate-500">Elemento: <b>{d.elemento_codigo}</b>{d.conductor_nombre && <> · Conductor: <b>{d.conductor_nombre}</b></>}</p>}
              <p className="mt-1 text-slate-500">Responsable de la inspección: <b>{d.inspector_nombre || '—'}</b>{d.firma_registro?.nombre && <> · Registro firmado por <b>{d.firma_registro.nombre}</b> el {fechaHora(d.firma_registro.fecha)}</>}</p>
            </div>

            <div className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Registro ({d.items.length} filas · {nc.length} no conforme{nc.length === 1 ? '' : 's'})</p>
                {enReg && <button className="btn-secondary !py-1 text-xs" onClick={todoBueno} title="Completa las respuestas vacías con la respuesta favorable"><CheckCheck className="h-3.5 w-3.5" /> Completar lo vacío como conforme</button>}
                {enReg && est.familia !== 'preguntas' && <button className="btn-secondary !py-1 text-xs" onClick={() => setFila({})}><Plus className="h-3.5 w-3.5" /> Agregar fila</button>}
                {enReg && pendientesGuardar > 0 && <span className="ml-auto text-amber-600">{pendientesGuardar} fila(s) sin guardar</span>}
              </div>
              {fila && (
                <div className="mb-2 flex flex-wrap items-end gap-2 rounded bg-slate-500/5 p-2">
                  {est.familia === 'elementos' && est.tipo_elemento && <div className="w-72"><label className={lbl}>Elemento del inventario</label><select className={inp} value={fila.elemento || ''} onChange={(e) => setFila({ elemento: e.target.value })}><option value="">—</option>{elegibles(est.tipo_elemento).filter((e) => !d.items.some((i) => i.elemento === e.id)).map((e) => <option key={e.id} value={e.id}>{e.codigo} · {e.ubicacion}</option>)}</select></div>}
                  {est.familia === 'elementos' && !est.tipo_elemento && (est.columnas_datos || []).map((c) => <div key={c} className="w-56"><label className={lbl}>{c}</label><input className={inp} value={fila.datos?.[c] || ''} onChange={(e) => setFila({ datos: { ...(fila.datos || {}), [c]: e.target.value } })} /></div>)}
                  {est.familia === 'trabajadores' && <div className="w-72"><label className={lbl}>Trabajador</label><select className={inp} value={fila.trabajador || ''} onChange={(e) => setFila({ trabajador: e.target.value })}><option value="">—</option>{trabajadores.filter((t) => !d.items.some((i) => i.trabajador === t.id)).map((t) => <option key={t.id} value={t.id}>{t.nombre_completo}</option>)}</select></div>}
                  {est.familia === 'contenido' && <><div className="w-64"><label className={lbl}>Producto</label><input className={inp} value={fila.texto || ''} onChange={(e) => setFila({ ...fila, texto: e.target.value })} /></div><div className="w-24"><label className={lbl}>Cantidad</label><input className={inp} value={fila.datos?.Cantidad || ''} onChange={(e) => setFila({ ...fila, datos: { ...(fila.datos || {}), Cantidad: e.target.value } })} /></div><div className="w-24"><label className={lbl}>Unidad</label><input className={inp} value={fila.datos?.Unidad || ''} onChange={(e) => setFila({ ...fila, datos: { ...(fila.datos || {}), Unidad: e.target.value } })} /></div></>}
                  <button className="btn-primary !py-1 text-xs" onClick={agregarFila}>Agregar</button><button className="btn-secondary !py-1 text-xs" onClick={() => setFila(null)}>Cancelar</button>
                </div>
              )}
              {(est.familia === 'elementos' || est.familia === 'trabajadores') && <MatrizInspeccion d={d} est={est} valorItem={valorItem} responder={responder} cambiar={cambiar} editable={enReg} quitar={quitarFila} />}
              {est.familia === 'contenido' && <ContenidoInspeccion d={d} est={est} valorItem={valorItem} responder={responder} cambiar={cambiar} editable={enReg} quitar={quitarFila} />}
              {est.familia === 'preguntas' && <PreguntasInspeccion d={d} est={est} valorItem={valorItem} responder={responder} cambiar={cambiar} editable={enReg} />}
              {est.nota && <p className="mt-2 text-[11px] italic text-slate-500">{est.nota}</p>}
            </div>

            {nc.length > 0 && (
              <div className="rounded-lg border border-red-300/60 p-3 text-xs dark:border-red-500/30">
                <p className="mb-2 text-xs font-semibold text-red-600 dark:text-red-400">Acciones inmediatas de los «no conforme»</p>
                <table className="tabla-ficha w-full">
                  <thead><tr className="text-xs text-slate-500 dark:text-slate-400"><th className="px-1 py-1">N°</th><th className="px-1">Ítem</th><th className="px-1">Acción inmediata</th><th className="px-1">Responsable</th><th className="px-1 text-right">Plazo</th><th className="px-1">Seguimiento</th><th className="px-1" /></tr></thead>
                  <tbody>
                    {nc.map((it) => (
                      <tr key={it.id} className="border-t border-slate-100 dark:border-slate-800/60">
                        <td className="px-1 py-1">{it.orden}</td><td className="max-w-[16rem] px-1">{it.texto}</td>
                        <td className="px-1">{enReg ? <input className={`${inp} !py-1 text-xs`} value={it.accion || ''} onChange={(e) => cambiar(it, 'accion', e.target.value)} /> : it.accion}</td>
                        <td className="px-1">{enReg ? <select className={`${inp} !py-1 text-xs`} value={it.responsable_accion || ''} onChange={(e) => cambiar(it, 'responsable_accion', e.target.value ? Number(e.target.value) : null)}><option value="">—</option>{usuarios.map((u) => <option key={u.id} value={u.id}>{nombreUsuario(u)}</option>)}</select> : it.responsable_accion_nombre}</td>
                        <td className="px-1 text-right">{enReg ? <input type="date" className={`${inp} !py-1 text-xs`} value={it.plazo_accion || ''} onChange={(e) => cambiar(it, 'plazo_accion', e.target.value || null)} /> : <span className={it.accion_vencida ? 'font-semibold text-red-600' : ''}>{fecha(it.plazo_accion)}</span>}</td>
                        <td className="px-1">{it.accion_completada ? <span className="text-emerald-600">✓ {fecha(it.fecha_accion_completada)} {it.seguimiento_accion}</span> : d.estado === 'con_acciones' && puedeEditar ? <button className="text-esynapse-500 underline" onClick={() => completar(it)}>Completar</button> : '—'}</td>
                        <td className="whitespace-nowrap px-1">{it.hallazgo_codigo ? <span className="font-mono text-[11px]">{it.hallazgo_codigo}</span>
                          : ['con_acciones', 'cerrada'].includes(d.estado) && puedeEditar && (hz?.item.id === it.id
                            ? <span className="flex items-center gap-1"><select className="rounded border border-slate-300 bg-transparent px-1 py-0.5 text-[11px] dark:border-slate-700" value={hz.tipo} onChange={(e) => setHz({ ...hz, tipo: e.target.value })}><option value="nc_menor">NC menor</option><option value="nc_mayor">NC mayor</option></select><button className="text-[11px] font-semibold text-esynapse-500" onClick={hallazgo}>Registrar</button><button onClick={() => setHz(null)}><X className="h-3 w-3" /></button></span>
                            : <button className="text-[11px] text-esynapse-500 underline" onClick={() => setHz({ item: it, tipo: 'nc_menor' })}>Registrar hallazgo</button>)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div><label className={lbl}>Conclusiones / observaciones / recomendaciones</label><CampoAmpliable multilinea rows={2} disabled={!enReg} value={reg.conclusiones} onChange={(v) => setReg({ ...reg, conclusiones: v })} /></div>
            {err && <Aviso texto={err} />}
            {enReg && (
              <div className="flex flex-wrap justify-end gap-2">
                {puedeEliminar && <button className="btn-secondary text-red-600" onClick={anular}>Anular</button>}
                <button className="btn-secondary" onClick={async () => { if (await guardarRegistro()) await guardarRespuestas() }}>Guardar</button>
                <button className="btn-primary" onClick={async () => { if (await guardarRegistro()) firmar() }}>Firmar el registro</button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

function Respuesta({ valor, valores, onChange, disabled, mala, invertido }) {
  // Selector compacto; rojo si la respuesta es no conforme.
  return (
    <select disabled={disabled} value={valor || ''} onChange={(e) => onChange(e.target.value)}
      className={`rounded border px-0.5 py-0.5 text-[11px] ${mala ? 'border-red-400 bg-red-500/15 text-red-700 dark:text-red-300' : 'border-slate-300 bg-transparent dark:border-slate-700'}`}>
      <option value="">·</option>
      {valores.map(([k, n]) => <option key={k} value={k}>{invertido && n === '✔' ? '✔ Sí' : invertido && n === 'X' ? 'X No' : n}</option>)}
    </select>
  )
}

function MatrizInspeccion({ d, est, valorItem, responder, cambiar, editable, quitar }) {
  const crit = est.criterios || []
  const grupos = useMemo(() => {
    const g = []
    crit.forEach((c) => { const n = c.grupo || ''; if (!g.length || g[g.length - 1].n !== n) g.push({ n, span: 1 }); else g[g.length - 1].span += 1 })
    return g
  }, [crit])
  const conGrupos = crit.some((c) => c.grupo)
  const trab = est.familia === 'trabajadores'
  const cols = trab ? ['Trabajador'] : (est.columnas_datos?.length ? est.columnas_datos : Object.keys(d.items[0]?.datos || { Elemento: '' }))
  return (
    <div className="overflow-x-auto">
      <table className="tabla-ficha w-full text-[11px]">
        <thead className="text-[11px] text-slate-500">
          {conGrupos && <tr><th colSpan={1 + cols.length} />{grupos.map((g, i) => <th key={i} colSpan={g.span} className="border-x border-slate-200 px-1 dark:border-slate-800">{g.n}</th>)}<th /></tr>}
          <tr className="border-b border-slate-200 dark:border-slate-800"><th className="px-1 py-1">N°</th>{cols.map((c) => <th key={c} className="px-1">{c}</th>)}{crit.map((c, k) => <th key={k} className="max-w-[6rem] px-1 font-medium" title={c.nombre}>{c.nombre.length > 40 ? `${k + 1})` : c.nombre}{c.invertido && ' *'}</th>)}<th className="px-1">Observaciones</th>{editable && <th />}</tr>
        </thead>
        <tbody>
          {d.items.map((it0) => {
            const it = valorItem(it0)
            return (
              <tr key={it.id} className="border-b border-slate-100 dark:border-slate-800/60">
                <td className="px-1 py-1">{it.orden}</td>
                {trab ? <td className="whitespace-nowrap px-1">{it.trabajador_nombre || it.texto}</td> : cols.map((c) => <td key={c} className="px-1">{it.datos?.[c] ?? ''}</td>)}
                {crit.map((c, k) => <td key={k} className="px-0.5"><Respuesta valor={it.resultados[String(k)]} valores={d.valores_escala} disabled={!editable} invertido={c.invertido} mala={esMala(it.resultados[String(k)], est.escala, c.invertido, d.valores_escala)} onChange={(v) => responder(it, String(k), v)} /></td>)}
                <td className="px-1"><input disabled={!editable} className={`${inp} !py-0.5 text-[11px]`} value={it.observacion || ''} onChange={(e) => cambiar(it, 'observacion', e.target.value)} /></td>
                {editable && <td><button className="p-1 text-red-500" title="Quitar la fila" onClick={() => quitar(it0)}><X className="h-3.5 w-3.5" /></button></td>}
              </tr>
            )
          })}
          {d.items.length === 0 && <tr><td colSpan={3 + cols.length + crit.length} className="py-4 text-slate-400">Sin filas: agregue {trab ? 'trabajadores' : 'elementos'}.</td></tr>}
        </tbody>
      </table>
      {crit.some((c) => c.nombre.length > 40) && <ol className="mt-2 list-decimal pl-5 text-[11px] text-slate-500">{crit.map((c, k) => <li key={k}>{c.nombre}</li>)}</ol>}
      {crit.some((c) => c.invertido) && <p className="mt-1 text-[11px] text-slate-500">* En «Requiere cambio», ✔ Sí significa que el EPP debe cambiarse (no conforme).</p>}
    </div>
  )
}

function ContenidoInspeccion({ d, est, valorItem, responder, cambiar, editable, quitar }) {
  return (
    <table className="tabla-ficha w-full text-[11px]">
      <thead><tr className="border-b border-slate-200 text-[11px] text-slate-500 dark:border-slate-800"><th className="px-1 py-1">N°</th><th className="px-1">Producto</th><th className="px-1 text-right">Cantidad</th><th className="px-1">Unidad</th><th className="px-1 text-right">Vencimiento</th><th className="px-1 text-center">Resultado</th><th className="px-1">Observaciones</th>{editable && <th />}</tr></thead>
      <tbody>
        {d.items.map((it0) => {
          const it = valorItem(it0)
          const datos = { ...it0.datos, ...(it.datos || {}) }
          return (
            <tr key={it.id} className="border-b border-slate-100 dark:border-slate-800/60">
              <td className="px-1 py-1">{it.orden}</td><td className="px-1">{it.texto}</td><td className="px-1 text-right">{datos.Cantidad}</td><td className="px-1">{datos.Unidad}</td>
              <td className="px-1 text-right"><input type="date" disabled={!editable} className={`${inp} !py-0.5 text-[11px]`} value={(datos.Vencimiento || '').slice(0, 10)} onChange={(e) => cambiar(it, 'datos', { ...datos, Vencimiento: e.target.value })} /></td>
              <td className="px-1 text-center"><Respuesta valor={it.resultados.r} valores={d.valores_escala} disabled={!editable} mala={esMala(it.resultados.r, est.escala, false, d.valores_escala)} onChange={(v) => responder(it, 'r', v)} /></td>
              <td className="px-1"><input disabled={!editable} className={`${inp} !py-0.5 text-[11px]`} value={it.observacion || ''} onChange={(e) => cambiar(it, 'observacion', e.target.value)} /></td>
              {editable && <td><button className="p-1 text-red-500" title="Quitar" onClick={() => quitar(it0)}><X className="h-3.5 w-3.5" /></button></td>}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function PreguntasInspeccion({ d, est, valorItem, responder, cambiar, editable }) {
  let seccion = null
  return (
    <table className="w-full text-[11px]">
      <tbody>
        {d.items.map((it0) => {
          const it = valorItem(it0)
          const cab = it.seccion !== seccion
          seccion = it.seccion
          const mala = esMala(it.resultados.r, est.escala, false, d.valores_escala)
          return [
            cab && <tr key={`s${it.id}`} className="bg-slate-500/10"><td colSpan={2 + d.valores_escala.length} className="px-2 py-1 text-[11px] font-semibold">{it.seccion}</td></tr>,
            <tr key={it.id} className={`border-b border-slate-100 dark:border-slate-800/60 ${mala ? 'bg-red-500/5' : ''}`}>
              <td className="px-2 py-1">{it.texto}</td>
              {d.valores_escala.map(([k, n]) => <td key={k} className="w-16 px-1"><label className="flex items-center justify-center gap-1"><input type="radio" className="accent-esynapse-600" disabled={!editable} checked={it.resultados.r === k} onChange={() => responder(it, 'r', k)} />{n}</label></td>)}
              <td className="w-64 px-1"><input disabled={!editable} className={`${inp} !py-0.5 text-[11px]`} placeholder="Observaciones" value={it.observacion || ''} onChange={(e) => cambiar(it, 'observacion', e.target.value)} /></td>
            </tr>,
          ]
        })}
      </tbody>
    </table>
  )
}

function ProgramaInspecciones({ setError }) {
  const [anio, setAnio] = useState(new Date().getFullYear())
  const [datos, setDatos] = useState(null)
  useEffect(() => { api.sst.programaInspecciones(anio).then(setDatos).catch((e) => setError(e.message)) }, [anio, setError])
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <input type="number" className="input-esynapse w-24" value={anio} onChange={(e) => setAnio(e.target.value)} />
        <span className={`rounded px-2 py-0.5 ${SITUACION.realizado}`}>Realizada</span><span className={`rounded px-2 py-0.5 ${SITUACION.en_plazo}`}>En plazo</span><span className={`rounded px-2 py-0.5 ${SITUACION.programado}`}>Programada</span><span className={`rounded px-2 py-0.5 ${SITUACION.atrasado}`}>Atrasada</span>
        <span className="text-slate-500">Según la frecuencia de cada plantilla (se cambia en «Plantillas»). Los meses anteriores al uso del sistema no se alertan.</span>
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">Inspección</th><th className="px-2">Frecuencia</th>{MESES.map((m) => <th key={m} className="px-1">{m}</th>)}</tr></thead>
          <tbody>
            {(datos?.filas || []).map((f) => (
              <tr key={f.plantilla} className="border-b border-slate-100 dark:border-slate-800/60">
                <td className="px-2 py-1.5">{f.nombre}</td><td className="px-2">{f.frecuencia}</td>
                {f.meses.map((m) => <td key={m.mes} className="px-0.5"><span title={m.inspecciones.map((i) => i.codigo).join(', ')} className={`block rounded py-1 text-[11px] ${SITUACION[m.situacion]}`}>{m.inspecciones.length || (m.esperado ? '•' : '')}</span></td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- Elementos de seguridad */
const ELEM_VACIO = { tipo: 'extintor', codigo: '', ubicacion: '', piso: '', area: '', subtipo: '', marca: '', capacidad: '', fecha_fabricacion: '', fecha_vencimiento: '', fecha_prueba_hidrostatica: '', fecha_revision_tecnica: '', placa: '', combustible: '', contenido: [], observaciones: '' }

function Elementos({ areasOrg, confirmar, setError, puedeCrear, puedeEditar, puedeEliminar, vencimientos, alCambiar }) {
  const [tipo, setTipo] = useState('')
  const [items, setItems] = useState([])
  const [cat, setCat] = useState(null)
  const [plantillas, setPlantillas] = useState([])
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.elementos(tipo ? `?tipo=${tipo}` : '').then(setItems).catch((e) => setError(e.message)), [tipo, setError])
  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { api.sst.catalogosInspeccion().then(setCat).catch(() => {}); api.sst.plantillas().then(setPlantillas).catch(() => {}) }, [])
  const guardar = async () => {
    setErr('')
    const datos = { ...form }
    ;['fecha_fabricacion', 'fecha_vencimiento', 'fecha_prueba_hidrostatica', 'fecha_revision_tecnica', 'area'].forEach((k) => { if (!datos[k]) datos[k] = null })
    try { form.id ? await api.sst.editarElemento(form.id, datos) : await api.sst.crearElemento(datos); setForm(null); cargar(); alCambiar() } catch (e) { setErr(e.message) }
  }
  const baja = async (e) => { const m = await confirmar({ titulo: `Dar de baja ${e.tipo_display} ${e.codigo}`, mensaje: 'Deja de inspeccionarse; queda en el historial.', textoConfirmar: 'Dar de baja', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) { try { await api.sst.bajaElemento(e.id, m); cargar(); alCambiar() } catch (x) { setError(x.message) } } }
  const t = form?.tipo
  const conContenido = ['botiquin', 'kit_antiderrame'].includes(t)
  const veh = ['vehiculo', 'moto'].includes(t)
  const cargarBase = () => { const p = plantillas.find((x) => x.familia === 'contenido' && x.tipo_elemento === t); if (p) setForm({ ...form, contenido: p.contenido_base.map((c) => ({ ...c })) }) }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select className="input-esynapse w-56" value={tipo} onChange={(e) => setTipo(e.target.value)}><option value="">Todos los tipos</option>{(cat?.tipos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select>
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setForm({ ...ELEM_VACIO, tipo: tipo || 'extintor' }) }}><Plus className="h-4 w-4" /> Registrar elemento</button>}
      </div>
      {vencimientos.length > 0 && (
        <div className="rounded-lg border border-amber-300/60 p-2 text-xs dark:border-amber-500/30">
          <p className="mb-1 flex items-center gap-1 font-semibold text-amber-700 dark:text-amber-400"><AlertTriangle className="h-3.5 w-3.5" /> Vencimientos</p>
          <div className="flex flex-wrap gap-2">{vencimientos.map((v, i) => <span key={i} className="rounded bg-slate-500/5 px-2 py-0.5">{v.nombre} · {v.concepto}: {fecha(v.fecha)} <Chip par={VENC[v.estado]} /></span>)}</div>
        </div>
      )}
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2 text-center">Tipo</th><th className="px-2">Código</th><th className="px-2">Ubicación</th><th className="px-2">Piso</th><th className="px-2">Detalle</th><th className="px-2">Vencimientos</th><th className="px-2 text-right">Última inspección</th><th className="px-2" /></tr></thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id} className="border-b border-slate-100 dark:border-slate-800/60">
                <td className="px-2 py-1.5 text-center">{e.tipo_display}</td><td className="px-2 font-mono">{e.codigo}</td><td className="px-2">{e.ubicacion || '—'}</td><td className="px-2">{e.piso || '—'}</td>
                <td className="px-2">{[e.subtipo, e.marca, e.capacidad, e.combustible].filter(Boolean).join(' · ') || (e.contenido?.length ? `${e.contenido.length} productos` : '—')}</td>
                <td className="px-2">{e.vencimientos.map((v, i) => <span key={i} className="block whitespace-nowrap">{v.concepto}: {fecha(v.fecha)} {v.estado !== 'vigente' && <Chip par={VENC[v.estado]} />}</span>)}{!e.vencimientos.length && '—'}</td>
                <td className="px-2 text-right">{e.ultima_inspeccion ? `${e.ultima_inspeccion.codigo} · ${fecha(e.ultima_inspeccion.fecha)}` : '—'}</td>
                <td className="whitespace-nowrap px-2">{puedeEditar && <button className="p-1 text-slate-500" title="Editar" onClick={() => { setErr(''); setForm({ ...ELEM_VACIO, ...Object.fromEntries(Object.entries(e).map(([k, v]) => [k, v ?? ''])) }) }}><Pencil className="h-3.5 w-3.5" /></button>}{puedeEliminar && <button className="p-1 text-red-500" title="Dar de baja" onClick={() => baja(e)}><Trash2 className="h-3.5 w-3.5" /></button>}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin elementos registrados</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? `${form.tipo_display} ${form.codigo}` : 'Registrar elemento de seguridad'} onCerrar={() => setForm(null)} ancho="max-w-3xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>Tipo</label><select className={inp} disabled={Boolean(form.id)} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{(cat?.tipos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>{veh ? 'Placa' : 'Código / N°'}</label><input className={inp} value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value, ...(veh ? { placa: e.target.value } : {}) })} /></div>
              {!veh && <div><label className={lbl}>Ubicación</label><input className={inp} value={form.ubicacion} onChange={(e) => setForm({ ...form, ubicacion: e.target.value })} /></div>}
              {!veh && <div><label className={lbl}>Piso</label><input className={inp} value={form.piso} onChange={(e) => setForm({ ...form, piso: e.target.value })} /></div>}
              {veh && <div><label className={lbl}>Marca / modelo</label><input className={inp} value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })} /></div>}
              {veh && <div><label className={lbl}>Combustible</label><input className={inp} value={form.combustible} onChange={(e) => setForm({ ...form, combustible: e.target.value })} /></div>}
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              {!veh && <div><label className={lbl}>Área</label><select className={inp} value={String(form.area || '')} onChange={(e) => setForm({ ...form, area: e.target.value })}><option value="">—</option>{areasOrg.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select></div>}
              {['extintor', 'escalera'].includes(t) && <div><label className={lbl}>{t === 'extintor' ? 'Tipo de extintor (agente)' : 'Tipo de escalera'}</label><input className={inp} value={form.subtipo} onChange={(e) => setForm({ ...form, subtipo: e.target.value })} /></div>}
              {t === 'extintor' && <div><label className={lbl}>Capacidad</label><input className={inp} value={form.capacidad} onChange={(e) => setForm({ ...form, capacidad: e.target.value })} /></div>}
              {t === 'extintor' && <div><label className={lbl}>Fecha de fabricación</label><input type="date" className={inp} value={form.fecha_fabricacion} onChange={(e) => setForm({ ...form, fecha_fabricacion: e.target.value })} /></div>}
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {(t === 'extintor' || veh) && <div><label className={lbl}>{veh ? 'SOAT vence' : 'Vencimiento (recarga)'}</label><input type="date" className={inp} value={form.fecha_vencimiento} onChange={(e) => setForm({ ...form, fecha_vencimiento: e.target.value })} /></div>}
              {t === 'extintor' && <div><label className={lbl}>Próxima prueba hidrostática</label><input type="date" className={inp} value={form.fecha_prueba_hidrostatica} onChange={(e) => setForm({ ...form, fecha_prueba_hidrostatica: e.target.value })} /></div>}
              {veh && <div><label className={lbl}>Revisión técnica vence</label><input type="date" className={inp} value={form.fecha_revision_tecnica} onChange={(e) => setForm({ ...form, fecha_revision_tecnica: e.target.value })} /></div>}
            </div>
            {conContenido && (
              <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
                <div className="mb-1 flex items-center gap-2"><p className="font-semibold">Contenido mínimo</p><button className="text-esynapse-500 underline" onClick={cargarBase}>Traer el de la plantilla</button></div>
                {(form.contenido || []).map((c, i) => (
                  <div key={i} className="mb-1 flex gap-1">
                    <input className={`${inp} flex-1 !py-1 text-xs`} placeholder="Producto" value={c.producto} onChange={(e) => setForm({ ...form, contenido: form.contenido.map((x, j) => (j === i ? { ...x, producto: e.target.value } : x)) })} />
                    <input className={`${inp} w-20 !py-1 text-xs`} placeholder="Cant." value={c.cantidad} onChange={(e) => setForm({ ...form, contenido: form.contenido.map((x, j) => (j === i ? { ...x, cantidad: e.target.value } : x)) })} />
                    <input className={`${inp} w-24 !py-1 text-xs`} placeholder="Unidad" value={c.unidad} onChange={(e) => setForm({ ...form, contenido: form.contenido.map((x, j) => (j === i ? { ...x, unidad: e.target.value } : x)) })} />
                    <input type="date" className={`${inp} w-36 !py-1 text-xs`} title="Vencimiento" value={c.vencimiento || ''} onChange={(e) => setForm({ ...form, contenido: form.contenido.map((x, j) => (j === i ? { ...x, vencimiento: e.target.value } : x)) })} />
                    <button className="p-1 text-red-500" onClick={() => setForm({ ...form, contenido: form.contenido.filter((_, j) => j !== i) })}><X className="h-3.5 w-3.5" /></button>
                  </div>
                ))}
                <button className="text-[11px] text-esynapse-500 underline" onClick={() => setForm({ ...form, contenido: [...(form.contenido || []), { producto: '', cantidad: '', unidad: '', vencimiento: '' }] })}>+ Agregar producto</button>
              </div>
            )}
            <div><label className={lbl}>Observaciones</label><input className={inp} value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} /></div>
            {form.historial?.length > 0 && <p className="text-[11px] text-slate-500">Historial: {form.historial.slice(-3).map((h) => `${fechaHora(h.fecha)} ${h.usuario}: ${h.accion}`).join(' · ')}</p>}
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ----------------------------------------------------------------------------------- Plantillas */
const PL_VACIA = { nombre: '', codigo_formato: '', familia: 'elementos', tipo_elemento: '', escala: 'c_nc_na', criterios: [], columnas_datos: [], secciones: [], contenido_base: [], frecuencia: 'mensual', objetivo: '', nota: '', version_formato: '00', fecha_formato: '', elaborado: 'ASIG', revisado: 'GSIG', aprobado: 'GG' }

function Plantillas({ confirmar, setError, puedeCrear, puedeEditar, puedeEliminar }) {
  const [items, setItems] = useState([])
  const [cat, setCat] = useState(null)
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.plantillas().then(setItems).catch((e) => setError(e.message)), [setError])
  useEffect(() => { cargar(); api.sst.catalogosInspeccion().then(setCat).catch(() => {}) }, [cargar])
  const guardar = async () => {
    setErr('')
    const datos = { ...form, fecha_formato: form.fecha_formato || null, columnas_datos: typeof form.columnas_datos === 'string' ? form.columnas_datos.split(',').map((x) => x.trim()).filter(Boolean) : form.columnas_datos }
    try { form.id ? await api.sst.editarPlantilla(form.id, datos) : await api.sst.crearPlantilla(datos); setForm(null); cargar() } catch (e) { setErr(e.message) }
  }
  const desactivar = async (p) => { if (await confirmar({ titulo: 'Desactivar plantilla', mensaje: `${p.nombre}: deja de ofrecerse para nuevas inspecciones. Las ya hechas se conservan.`, textoConfirmar: 'Desactivar', peligro: true })) { await api.sst.desactivarPlantilla(p.id); cargar() } }
  const set = (k, v) => setForm({ ...form, [k]: v })
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><p className="text-xs text-slate-500">Cada plantilla es un formato de inspección. Cambiarla no altera las inspecciones ya hechas: cada una guarda la estructura con la que se inspeccionó.</p>{puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setForm({ ...PL_VACIA }) }}><Plus className="h-4 w-4" /> Nueva plantilla</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Inspección</th><th className="px-2">Tipo de lista</th><th className="px-2 text-right">Elementos</th><th className="px-2">Escala</th><th className="px-2">Frecuencia</th><th className="px-2">Contenido</th><th className="px-2 text-right">Inspecciones</th><th className="px-2" /></tr></thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id} className="border-b border-slate-100 dark:border-slate-800/60">
                <td className="px-2 py-1.5">{p.nombre}</td><td className="px-2">{p.familia_display}</td><td className="px-2 text-right">{p.tipo_elemento_display || '—'}</td><td className="px-2">{p.escala_display}</td><td className="px-2">{p.frecuencia_display}</td>
                <td className="px-2">{p.familia === 'preguntas' ? `${p.secciones.reduce((a, s) => a + s.preguntas.length, 0)} preguntas` : p.familia === 'contenido' ? `${p.contenido_base.length} productos` : `${p.criterios.length} criterios`}</td>
                <td className="px-2 text-right">{p.total_inspecciones}</td>
                <td className="whitespace-nowrap px-2">{puedeEditar && <button className="p-1 text-slate-500" title="Editar" onClick={() => { setErr(''); setForm({ ...PL_VACIA, ...p, fecha_formato: p.fecha_formato || '' }) }}><Pencil className="h-3.5 w-3.5" /></button>}{puedeEliminar && <button className="p-1 text-red-500" title="Desactivar" onClick={() => desactivar(p)}><Trash2 className="h-3.5 w-3.5" /></button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? form.nombre : 'Nueva plantilla de inspección'} onCerrar={() => setForm(null)} ancho="max-w-5xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="md:col-span-2"><label className={lbl}>Nombre</label><input className={inp} value={form.nombre} onChange={(e) => set('nombre', e.target.value)} /></div>
              <div><label className={lbl}>Tipo de lista</label><select className={inp} disabled={Boolean(form.id)} value={form.familia} onChange={(e) => set('familia', e.target.value)}>{(cat?.familias || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Elementos que inspecciona</label><select className={inp} value={form.tipo_elemento} onChange={(e) => set('tipo_elemento', e.target.value)}><option value="">— (filas libres / ninguno)</option>{(cat?.tipos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <p className="-mt-2 text-[11px] text-slate-500 md:col-span-4"><span className="font-medium">Tipo de lista:</span> {(cat?.familias || []).find(([k]) => k === form.familia)?.[2]}{form.id ? ' No se cambia en una plantilla ya creada.' : ''}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>Escala de respuesta</label><select className={inp} value={form.escala} onChange={(e) => set('escala', e.target.value)}>{(cat?.escalas || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Frecuencia</label><select className={inp} value={form.frecuencia} onChange={(e) => set('frecuencia', e.target.value)}>{(cat?.frecuencias || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div className="md:col-span-2"><label className={lbl}>Objetivo</label><input className={inp} value={form.objetivo} onChange={(e) => set('objetivo', e.target.value)} /></div>
            </div>
            {['elementos', 'trabajadores'].includes(form.familia) && (
              <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
                <p className="mb-1 font-semibold">Criterios (columnas)</p>
                {form.criterios.map((c, i) => (
                  <div key={i} className="mb-1 flex items-center gap-1">
                    {form.familia === 'trabajadores' && <input className={`${inp} w-48 !py-1 text-xs`} placeholder="Grupo (p. ej. Casco)" value={c.grupo} onChange={(e) => set('criterios', form.criterios.map((x, j) => (j === i ? { ...x, grupo: e.target.value } : x)))} />}
                    <input className={`${inp} flex-1 !py-1 text-xs`} placeholder="Criterio" value={c.nombre} onChange={(e) => set('criterios', form.criterios.map((x, j) => (j === i ? { ...x, nombre: e.target.value } : x)))} />
                    <label className="flex items-center gap-1 whitespace-nowrap" title="La respuesta favorable es la no conforme (p. ej. «Requiere cambio»)"><input type="checkbox" className="accent-esynapse-600" checked={c.invertido} onChange={(e) => set('criterios', form.criterios.map((x, j) => (j === i ? { ...x, invertido: e.target.checked } : x)))} />Invertido</label>
                    <button className="p-1 text-red-500" onClick={() => set('criterios', form.criterios.filter((_, j) => j !== i))}><X className="h-3.5 w-3.5" /></button>
                  </div>
                ))}
                <button className="text-[11px] text-esynapse-500 underline" onClick={() => set('criterios', [...form.criterios, { grupo: '', nombre: '', invertido: false }])}>+ Agregar criterio</button>
                {form.familia === 'elementos' && !form.tipo_elemento && <div className="mt-2"><label className={lbl}>Columnas que describen cada fila (separadas por coma)</label><input className={inp} value={Array.isArray(form.columnas_datos) ? form.columnas_datos.join(', ') : form.columnas_datos} onChange={(e) => set('columnas_datos', e.target.value)} /></div>}
              </div>
            )}
            {form.familia === 'preguntas' && (
              <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
                <p className="mb-1 font-semibold">Secciones y preguntas (una pregunta por línea)</p>
                {form.secciones.map((s, i) => (
                  <div key={i} className="mb-2 rounded bg-slate-500/5 p-2">
                    <div className="flex gap-1"><input className={`${inp} flex-1 !py-1 text-xs font-semibold`} placeholder="Título de la sección" value={s.titulo} onChange={(e) => set('secciones', form.secciones.map((x, j) => (j === i ? { ...x, titulo: e.target.value } : x)))} /><button className="p-1 text-red-500" onClick={() => set('secciones', form.secciones.filter((_, j) => j !== i))}><X className="h-3.5 w-3.5" /></button></div>
                    <textarea className={`${inp} mt-1 text-xs`} rows={Math.min(8, Math.max(2, s.preguntas.length))} value={s.preguntas.join('\n')} onChange={(e) => set('secciones', form.secciones.map((x, j) => (j === i ? { ...x, preguntas: e.target.value.split('\n') } : x)))} />
                  </div>
                ))}
                <button className="text-[11px] text-esynapse-500 underline" onClick={() => set('secciones', [...form.secciones, { titulo: '', preguntas: [] }])}>+ Agregar sección</button>
              </div>
            )}
            {form.familia === 'contenido' && (
              <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
                <p className="mb-1 font-semibold">Contenido mínimo por defecto</p>
                {form.contenido_base.map((c, i) => (
                  <div key={i} className="mb-1 flex gap-1">
                    <input className={`${inp} flex-1 !py-1 text-xs`} value={c.producto} onChange={(e) => set('contenido_base', form.contenido_base.map((x, j) => (j === i ? { ...x, producto: e.target.value } : x)))} />
                    <input className={`${inp} w-20 !py-1 text-xs`} value={c.cantidad} onChange={(e) => set('contenido_base', form.contenido_base.map((x, j) => (j === i ? { ...x, cantidad: e.target.value } : x)))} />
                    <input className={`${inp} w-24 !py-1 text-xs`} value={c.unidad} onChange={(e) => set('contenido_base', form.contenido_base.map((x, j) => (j === i ? { ...x, unidad: e.target.value } : x)))} />
                    <button className="p-1 text-red-500" onClick={() => set('contenido_base', form.contenido_base.filter((_, j) => j !== i))}><X className="h-3.5 w-3.5" /></button>
                  </div>
                ))}
                <button className="text-[11px] text-esynapse-500 underline" onClick={() => set('contenido_base', [...form.contenido_base, { producto: '', cantidad: 1, unidad: 'Und.', vencimiento: '' }])}>+ Agregar producto</button>
              </div>
            )}
            <div><label className={lbl}>Nota al pie del formato</label><input className={inp} value={form.nota} onChange={(e) => set('nota', e.target.value)} /></div>
            <div className="grid gap-3 md:grid-cols-6">
              <div className="md:col-span-2"><label className={lbl}>Código del formato impreso</label><input className={inp} value={form.codigo_formato} onChange={(e) => set('codigo_formato', e.target.value)} /></div>
              <div><label className={lbl}>Versión</label><input className={inp} value={form.version_formato} onChange={(e) => set('version_formato', e.target.value)} /></div>
              <div><label className={lbl}>Elaborado</label><input className={inp} value={form.elaborado} onChange={(e) => set('elaborado', e.target.value)} /></div>
              <div><label className={lbl}>Revisado</label><input className={inp} value={form.revisado} onChange={(e) => set('revisado', e.target.value)} /></div>
              <div><label className={lbl}>Aprobado</label><input className={inp} value={form.aprobado} onChange={(e) => set('aprobado', e.target.value)} /></div>
            </div>
            <p className="text-[11px] text-slate-500">La versión, fecha y siglas son de respaldo: si el formato está vinculado a la lista maestra (Configuración → Formatos impresos), el PDF toma los de la versión vigente.</p>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ==================================================================================== Monitoreos */
export function Monitoreos(props) {
  const [vista, setVista] = useState('programa')
  return (
    <div className="space-y-3">
      <Sub valor={vista} onChange={setVista} opciones={[['programa', 'Programa anual'], ['registros', 'Registros de monitoreo'], ['recomendaciones', 'Seguimiento de recomendaciones']]} />
      {vista === 'programa' && <ProgramaMonitoreos {...props} />}
      {vista === 'registros' && <RegistrosMonitoreo {...props} />}
      {vista === 'recomendaciones' && <Recomendaciones {...props} />}
    </div>
  )
}

const PROG_VACIO = { agente: 'fisico', detalle: '', fecha_programada: '', frecuencia: 'anual', meses: [], comentarios: '' }

function ProgramaMonitoreos({ cat: _c, confirmar, setError, abrirPdf, puedeEditar, puedeCrear }) {
  const [anio, setAnio] = useState(new Date().getFullYear())
  const [p, setP] = useState(undefined)
  const [cat, setCat] = useState(null)
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.programaMonitoreos(anio).then(setP).catch((e) => setError(e.message)), [anio, setError])
  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { api.sst.catalogosInspeccion().then(setCat).catch(() => {}) }, [])
  const crear = async () => { try { await api.sst.crearProgramaMonitoreos(Number(anio)); cargar() } catch (e) { setError(e.message) } }
  const guardar = async () => {
    setErr('')
    try { setP(await api.sst.itemProgramaMonitoreos(p.id, { ...form, fecha_programada: form.fecha_programada || null })); setForm(null) } catch (e) { setErr(e.message) }
  }
  const quitar = async (it) => { const m = await confirmar({ titulo: 'Retirar del programa', mensaje: it.nombre, textoConfirmar: 'Retirar', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) { try { setP(await api.sst.quitarItemMonitoreos(p.id, { id: it.id, motivo: m })) } catch (e) { setError(e.message) } } }
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <input type="number" className="input-esynapse w-24" value={anio} onChange={(e) => setAnio(e.target.value)} />
        {p && <span className="text-slate-500">Actualizado el {fecha(p.fecha_actualizacion)}</span>}
        <span className="rounded bg-slate-500/15 px-2 py-0.5">X Programado</span><span className="rounded bg-emerald-500/25 px-2 py-0.5 text-emerald-700 dark:text-emerald-300">X Ejecutado</span>
        <div className="ml-auto flex gap-2">
          {p && <button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.sst.programaMonitoreosPdf(p.id))}><FileText className="h-3.5 w-3.5" /> PDF</button>}
          {p && puedeEditar && <button className="btn-primary !py-1 text-xs" onClick={() => { setErr(''); setForm({ ...PROG_VACIO }) }}><Plus className="h-3.5 w-3.5" /> Agregar monitoreo</button>}
        </div>
      </div>
      {p === null && <div className="card-esynapse p-6 text-center text-sm text-slate-500">No hay programa de monitoreos para {anio}. {puedeCrear && <button className="btn-primary ml-2" onClick={crear}>Crear el programa {anio}</button>}</div>}
      {p && (
        <div className="card-esynapse overflow-x-auto">
          <table className="tabla-ficha w-full text-xs">
            <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">Ítem</th><th className="px-2">Agente</th><th className="px-2 text-right">Fecha programada / frecuencia</th>{MESES.map((m) => <th key={m} className="px-1">{m}</th>)}<th className="px-2">Comentarios</th><th /></tr></thead>
            <tbody>
              {p.items.map((it, i) => (
                <tr key={it.id} className="border-b border-slate-100 dark:border-slate-800/60">
                  <td className="px-2 py-1.5">{i + 1}</td><td className="px-2">{it.nombre}</td><td className="px-2 text-right">{fecha(it.fecha_programada)} / {it.frecuencia_display}</td>
                  {MESES.map((_, k) => { const m = k + 1; const ej = it.meses_ejecutados.includes(m); return <td key={m} className="px-0.5"><span className={`block rounded py-0.5 ${ej ? 'bg-emerald-500/25 text-emerald-700 dark:text-emerald-300' : it.meses.includes(m) ? 'bg-slate-500/15' : ''}`}>{ej || it.meses.includes(m) ? 'X' : ''}</span></td> })}
                  <td className="max-w-[18rem] px-2">{it.comentarios}</td>
                  <td className="whitespace-nowrap px-1">{puedeEditar && <><button className="p-1 text-slate-500" onClick={() => { setErr(''); setForm({ ...PROG_VACIO, ...it, fecha_programada: it.fecha_programada || '' }) }}><Pencil className="h-3.5 w-3.5" /></button><button className="p-1 text-red-500" onClick={() => quitar(it)}><Trash2 className="h-3.5 w-3.5" /></button></>}</td>
                </tr>
              ))}
              {p.items.length === 0 && <tr><td colSpan={16} className="py-6 text-slate-400">Sin monitoreos programados</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Monitoreo programado' : 'Agregar monitoreo al programa'} onCerrar={() => setForm(null)} ancho="max-w-2xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Agente</label><select className={inp} value={form.agente} onChange={(e) => setForm({ ...form, agente: e.target.value })}>{(cat?.agentes || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Detalle (p. ej. iluminación, ruido)</label><input className={inp} value={form.detalle} onChange={(e) => setForm({ ...form, detalle: e.target.value })} /></div>
              <div><label className={lbl}>Frecuencia</label><select className={inp} value={form.frecuencia} onChange={(e) => setForm({ ...form, frecuencia: e.target.value })}>{(cat?.frecuencias || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Fecha programada</label><input type="date" className={inp} value={form.fecha_programada} onChange={(e) => setForm({ ...form, fecha_programada: e.target.value })} /></div>
              <div className="md:col-span-2"><label className={lbl}>Meses programados</label><div className="flex flex-wrap gap-1">{MESES.map((m, k) => <label key={m} className="flex items-center gap-0.5 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={form.meses.includes(k + 1)} onChange={() => setForm({ ...form, meses: form.meses.includes(k + 1) ? form.meses.filter((x) => x !== k + 1) : [...form.meses, k + 1] })} />{m}</label>)}</div></div>
            </div>
            <div><label className={lbl}>Comentarios / observaciones (motivo de una reprogramación)</label><CampoAmpliable multilinea rows={2} value={form.comentarios} onChange={(v) => setForm({ ...form, comentarios: v })} /></div>
            <p className="text-[11px] text-slate-500">Un cambio de fecha o meses queda en el historial del programa como reprogramación. Lo ejecutado se marca solo al registrar el monitoreo.</p>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}

const MON_VACIO = { area_monitoreada: '', fecha: new Date().toISOString().slice(0, 10), frecuencia: 'anual', programados: [], tipo_riesgo: '', n_expuestos: '', organizacion: '', resultados: [], causas_desviacion: '', conclusiones: '' }

function RegistrosMonitoreo({ confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeEliminar }) {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(null)
  const [prog, setProg] = useState([])
  const [cat, setCat] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.monitoreos().then(setItems).catch((e) => setError(e.message)), [setError])
  useEffect(() => { cargar(); api.sst.catalogosInspeccion().then(setCat).catch(() => {}) }, [cargar])
  useEffect(() => {
    const anio = Number((form?.fecha || '').slice(0, 4)) || new Date().getFullYear()
    if (form) api.sst.programaMonitoreos(anio).then((p) => setProg(p?.items || [])).catch(() => setProg([]))
  }, [form?.fecha]) // eslint-disable-line react-hooks/exhaustive-deps
  const editable = !form?.id || form.estado === 'en_registro'
  const guardar = async () => {
    setErr('')
    const datos = { ...form, n_expuestos: form.n_expuestos === '' ? null : Number(form.n_expuestos) }
    try { const r = form.id ? await api.sst.editarMonitoreo(form.id, datos) : await api.sst.crearMonitoreo(datos); setForm({ ...MON_VACIO, ...r, n_expuestos: r.n_expuestos ?? '' }); cargar(); return r } catch (e) { setErr(e.message); return null }
  }
  const accion = async (nombre, datos) => { setErr(''); try { const r = await api.sst.accionMonitoreo(form.id, nombre, datos); setForm({ ...MON_VACIO, ...r, n_expuestos: r.n_expuestos ?? '' }); cargar() } catch (e) { setErr(e.message) } }
  const firmar = async () => { if (!await guardar()) return; const c = await pedirClave(confirmar, 'Registrar el monitoreo', 'Firma como responsable del registro. El monitoreo queda de solo lectura y marca como ejecutados sus monitoreos del programa.'); if (c !== null) accion('firmar', { password: c }) }
  const anular = async () => { const m = await confirmar({ titulo: 'Anular el monitoreo', mensaje: 'Solo si se registró por error.', textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) accion('anular', { motivo: m }) }
  const subir = async (file) => { setErr(''); const fd = new FormData(); fd.append('archivo', file); try { const r = await api.sst.subirMonitoreo(form.id, fd); setForm({ ...form, informe_url: r.informe_url }) } catch (e) { setErr(e.message) } }
  const setRes = (i, k, v) => setForm({ ...form, resultados: form.resultados.map((r, j) => (j === i ? { ...r, [k]: v } : r)) })
  return (
    <div className="space-y-2">
      <div className="flex justify-end">{puedeCrear && <button className="btn-primary" onClick={() => { setErr(''); setForm({ ...MON_VACIO }) }}><Plus className="h-4 w-4" /> Registrar monitoreo</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">N° registro</th><th className="px-2 text-right">Fecha</th><th className="px-2">Área monitoreada</th><th className="px-2">Agentes</th><th className="px-2">Organización</th><th className="px-2 text-center">Resultado</th><th className="px-2">Recomendaciones</th><th className="px-2 text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id} onClick={() => { setErr(''); setForm({ ...MON_VACIO, ...m, n_expuestos: m.n_expuestos ?? '' }) }} className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${m.estado === 'anulado' ? 'opacity-50' : ''}`}>
                <td className="px-2 py-1.5 font-mono">{m.codigo}</td><td className="px-2 text-right">{fecha(m.fecha)}</td><td className="px-2">{m.area_monitoreada}</td><td className="px-2">{m.resultados.map((r) => r.agente).join(', ')}</td><td className="px-2">{m.organizacion || '—'}</td>
                <td className="px-2 text-center">{m.con_desviaciones ? <Chip par={['Con desviaciones', 'bg-red-500/15 text-red-600 dark:text-red-400']} /> : m.resultados.length ? <Chip par={['Dentro del LMP', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400']} /> : '—'}</td>
                <td className="px-2">{m.total_recomendaciones}</td><td className="px-2 text-center"><Chip par={ESTADO[m.estado]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin monitoreos registrados</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? `${form.codigo} — Monitoreo de agentes ocupacionales` : 'Registrar monitoreo de agentes ocupacionales'} onCerrar={() => setForm(null)} ancho="max-w-5xl">
        {form && (
          <div className="space-y-3 text-sm">
            {form.id && <div className="flex items-center gap-2"><Chip par={ESTADO[form.estado]} />{form.firma_registro?.nombre && <span className="text-xs text-slate-500">Registrado por {form.firma_registro.nombre} · {fecha(form.firma_registro.fecha)}</span>}<button className="btn-secondary ml-auto !py-1 text-xs" onClick={() => abrirPdf(api.sst.monitoreoPdf(form.id))}><FileText className="h-3.5 w-3.5" /> PDF</button></div>}
            <div className="grid gap-3 md:grid-cols-4">
              <div className="md:col-span-2"><label className={lbl}>Área monitoreada</label><input className={inp} disabled={!editable} value={form.area_monitoreada} onChange={(e) => setForm({ ...form, area_monitoreada: e.target.value })} /></div>
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} disabled={!editable} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
              <div><label className={lbl}>Frecuencia</label><select className={inp} disabled={!editable} value={form.frecuencia} onChange={(e) => setForm({ ...form, frecuencia: e.target.value })}>{(cat?.frecuencias || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
            </div>
            <div><label className={lbl}>Monitoreos del programa que cubre</label><div className="flex flex-wrap gap-2 text-xs">{prog.map((p) => <label key={p.id} className="flex items-center gap-1"><input type="checkbox" className="accent-esynapse-600" disabled={!editable} checked={form.programados.includes(p.id)} onChange={() => setForm({ ...form, programados: form.programados.includes(p.id) ? form.programados.filter((x) => x !== p.id) : [...form.programados, p.id] })} />{p.nombre}</label>)}{prog.length === 0 && <span className="text-slate-400">Sin programa para ese año.</span>}</div></div>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="md:col-span-2"><label className={lbl}>Tipo de riesgo monitoreado</label><input className={inp} disabled={!editable} value={form.tipo_riesgo} onChange={(e) => setForm({ ...form, tipo_riesgo: e.target.value })} /></div>
              <div><label className={lbl}>N° trabajadores expuestos</label><input type="number" className={inp} disabled={!editable} value={form.n_expuestos} onChange={(e) => setForm({ ...form, n_expuestos: e.target.value })} /></div>
              <div><label className={lbl}>Organización que monitorea</label><input className={inp} disabled={!editable} value={form.organizacion} onChange={(e) => setForm({ ...form, organizacion: e.target.value })} /></div>
            </div>
            <div className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
              <p className="mb-1 font-semibold">Resultados frente a los límites máximos permisibles</p>
              {form.resultados.map((r, i) => (
                <div key={i} className="mb-1 grid gap-1 md:grid-cols-12">
                  <input className={`${inp} !py-1 text-xs md:col-span-2`} disabled={!editable} placeholder="Agente" value={r.agente} onChange={(e) => setRes(i, 'agente', e.target.value)} />
                  <input className={`${inp} !py-1 text-xs md:col-span-5`} disabled={!editable} placeholder="Resultado" value={r.resultado} onChange={(e) => setRes(i, 'resultado', e.target.value)} />
                  <input className={`${inp} !py-1 text-xs md:col-span-1`} disabled={!editable} placeholder="Valor" value={r.valor} onChange={(e) => setRes(i, 'valor', e.target.value)} />
                  <input className={`${inp} !py-1 text-xs md:col-span-2`} disabled={!editable} placeholder="LMP" value={r.lmp} onChange={(e) => setRes(i, 'lmp', e.target.value)} />
                  <select className={`${inp} !py-1 text-xs md:col-span-1 ${r.dentro_lmp === false ? 'text-red-600' : ''}`} disabled={!editable} value={r.dentro_lmp === true ? 'si' : r.dentro_lmp === false ? 'no' : ''} onChange={(e) => setRes(i, 'dentro_lmp', e.target.value === 'si' ? true : e.target.value === 'no' ? false : null)}><option value="">¿Dentro?</option><option value="si">Dentro</option><option value="no">Fuera</option></select>
                  {editable && <button className="p-1 text-red-500" onClick={() => setForm({ ...form, resultados: form.resultados.filter((_, j) => j !== i) })}><X className="h-3.5 w-3.5" /></button>}
                </div>
              ))}
              {editable && <button className="text-[11px] text-esynapse-500 underline" onClick={() => setForm({ ...form, resultados: [...form.resultados, { agente: '', resultado: '', valor: '', lmp: '', dentro_lmp: null }] })}>+ Agregar resultado</button>}
            </div>
            <div><label className={lbl}>Causas ante desviaciones</label><CampoAmpliable multilinea rows={2} disabled={!editable} value={form.causas_desviacion} onChange={(v) => setForm({ ...form, causas_desviacion: v })} /></div>
            <div><label className={lbl}>Conclusiones y recomendaciones (medidas para corregir las desviaciones)</label><CampoAmpliable multilinea rows={3} disabled={!editable} value={form.conclusiones} onChange={(v) => setForm({ ...form, conclusiones: v })} /></div>
            {form.id && <div className="text-xs">Informe con resultados: {form.informe_url ? <a className="text-esynapse-500 underline" href={form.informe_url} target="_blank" rel="noreferrer">ver informe</a> : <span className="text-slate-400">sin adjuntar</span>}{editable && puedeEditar && <label className="ml-2 cursor-pointer text-esynapse-500 underline">adjuntar<input type="file" className="hidden" onChange={(e) => e.target.files[0] && subir(e.target.files[0])} /></label>}</div>}
            {form.id && form.estado === 'registrado' && <p className="text-[11px] text-slate-500">Las recomendaciones de este monitoreo se registran en «Seguimiento de recomendaciones».</p>}
            {err && <Aviso texto={err} />}
            {editable && puedeEditar && (
              <div className="flex justify-end gap-2">
                {form.id && puedeEliminar && <button className="btn-secondary text-red-600" onClick={anular}>Anular</button>}
                <button className="btn-secondary" onClick={guardar}>Guardar</button>
                {form.id && <button className="btn-primary" onClick={firmar}>Firmar el registro</button>}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

const REC_VACIA = { agente: '', orden: 1, actividad: '', fecha_programada: '', programacion: '', meses: [], responsable: '', estado: 'pendiente', fecha_ejecucion: '', observaciones: '', monitoreo: '' }

function Recomendaciones({ confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeEliminar }) {
  const [anio, setAnio] = useState(new Date().getFullYear())
  const [items, setItems] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [monitoreos, setMonitoreos] = useState([])
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(() => api.sst.recomendaciones(`?anio=${anio}`).then(setItems).catch((e) => setError(e.message)), [anio, setError])
  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { api.usuarios.listar().then((u) => setUsuarios(u.results ?? u)).catch(() => {}); api.sst.monitoreos().then(setMonitoreos).catch(() => {}) }, [])
  const grupos = useMemo(() => { const g = []; items.forEach((r) => { let x = g.find((y) => y.agente === r.agente); if (!x) { x = { agente: r.agente, items: [] }; g.push(x) } x.items.push(r) }); g.forEach((x) => x.items.sort((a, b) => a.orden - b.orden)); return g }, [items])
  const guardar = async () => {
    setErr('')
    const datos = { ...form, anio: Number(anio), fecha_programada: form.fecha_programada || null, fecha_ejecucion: form.fecha_ejecucion || null, responsable: form.responsable || null, monitoreo: form.monitoreo || null }
    try { form.id ? await api.sst.editarRecomendacion(form.id, datos) : await api.sst.crearRecomendacion(datos); setForm(null); cargar() } catch (e) { setErr(e.message) }
  }
  const retirar = async (r) => { if (await confirmar({ titulo: 'Retirar del programa', mensaje: r.actividad, textoConfirmar: 'Retirar', peligro: true })) { await api.sst.retirarRecomendacion(r.id); cargar() } }
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <input type="number" className="input-esynapse w-24" value={anio} onChange={(e) => setAnio(e.target.value)} />
        <div className="ml-auto flex gap-2">
          <button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.sst.recomendacionesPdf(anio))}><FileText className="h-3.5 w-3.5" /> PDF</button>
          {puedeCrear && <button className="btn-primary !py-1 text-xs" onClick={() => { setErr(''); setForm({ ...REC_VACIA }) }}><Plus className="h-3.5 w-3.5" /> Agregar actividad</button>}
        </div>
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-ficha w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">Ítem</th><th className="px-2">Actividad</th><th className="px-2 text-right">Fecha / frecuencia</th><th className="px-2">Responsable</th><th className="px-2 text-center">Estado</th><th className="px-2">Observaciones</th><th /></tr></thead>
          <tbody>
            {grupos.map((g) => [
              <tr key={g.agente} className="bg-slate-500/10"><td colSpan={7} className="px-2 py-1 font-semibold">{g.agente}</td></tr>,
              ...g.items.map((r) => (
                <tr key={r.id} className="border-b border-slate-100 dark:border-slate-800/60">
                  <td className="px-2 py-1.5">{r.orden}</td><td className="max-w-[28rem] px-2">{r.actividad}</td>
                  <td className="whitespace-nowrap px-2 text-right">{r.fecha_programada ? <span className={r.vencida ? 'font-semibold text-red-600' : ''}>{fecha(r.fecha_programada)}</span> : r.programacion}</td>
                  <td className="px-2">{r.responsable_nombre || '—'}</td><td className="px-2 text-center"><Chip par={ESTADO[r.estado]} />{r.vencida && <span className="block text-[11px] font-semibold text-red-600">Vencida</span>}</td>
                  <td className="max-w-[18rem] px-2">{r.observaciones}</td>
                  <td className="whitespace-nowrap px-1">{puedeEditar && <button className="p-1 text-slate-500" onClick={() => { setErr(''); setForm({ ...REC_VACIA, ...Object.fromEntries(Object.entries(r).map(([k, v]) => [k, v ?? ''])) }) }}><Pencil className="h-3.5 w-3.5" /></button>}{puedeEliminar && <button className="p-1 text-red-500" onClick={() => retirar(r)}><Trash2 className="h-3.5 w-3.5" /></button>}</td>
                </tr>
              )),
            ])}
            {items.length === 0 && <tr><td colSpan={7} className="py-8 text-slate-400">Sin actividades para {anio}</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Actividad de seguimiento' : 'Agregar actividad al seguimiento de recomendaciones'} onCerrar={() => setForm(null)} ancho="max-w-3xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="md:col-span-2"><label className={lbl}>Agente (agrupa las actividades)</label><input className={inp} list="agentes-rec" value={form.agente} onChange={(e) => setForm({ ...form, agente: e.target.value })} /><datalist id="agentes-rec">{[...new Set(items.map((r) => r.agente))].map((a) => <option key={a} value={a} />)}</datalist></div>
              <div><label className={lbl}>Ítem</label><input type="number" className={inp} value={form.orden} onChange={(e) => setForm({ ...form, orden: e.target.value })} /></div>
              <div><label className={lbl}>Monitoreo que la origina</label><select className={inp} value={String(form.monitoreo || '')} onChange={(e) => setForm({ ...form, monitoreo: e.target.value })}><option value="">—</option>{monitoreos.map((m) => <option key={m.id} value={m.id}>{m.codigo}</option>)}</select></div>
            </div>
            <div><label className={lbl}>Actividad</label><CampoAmpliable multilinea rows={2} value={form.actividad} onChange={(v) => setForm({ ...form, actividad: v })} /></div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Fecha programada</label><input type="date" className={inp} value={form.fecha_programada} onChange={(e) => setForm({ ...form, fecha_programada: e.target.value })} /></div>
              <div><label className={lbl}>O frecuencia / programación</label><input className={inp} placeholder="Mensual, En evaluación…" value={form.programacion} onChange={(e) => setForm({ ...form, programacion: e.target.value })} /></div>
              <div><label className={lbl}>Responsable</label><select className={inp} value={String(form.responsable || '')} onChange={(e) => setForm({ ...form, responsable: e.target.value })}><option value="">—</option>{usuarios.map((u) => <option key={u.id} value={u.id}>{nombreUsuario(u)}</option>)}</select></div>
            </div>
            <div><label className={lbl}>Meses programados ({anio})</label><div className="flex flex-wrap gap-1">{MESES.map((m, k) => <label key={m} className="flex items-center gap-0.5 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={(form.meses || []).includes(k + 1)} onChange={() => setForm({ ...form, meses: (form.meses || []).includes(k + 1) ? form.meses.filter((x) => x !== k + 1) : [...(form.meses || []), k + 1] })} />{m}</label>)}</div></div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Estado</label><select className={inp} value={form.estado} onChange={(e) => setForm({ ...form, estado: e.target.value })}>{['pendiente', 'en_proceso', 'ejecutada', 'no_aplica'].map((k) => <option key={k} value={k}>{ESTADO[k][0]}</option>)}</select></div>
              {form.estado === 'ejecutada' && <div><label className={lbl}>Fecha de ejecución</label><input type="date" className={inp} value={form.fecha_ejecucion} onChange={(e) => setForm({ ...form, fecha_ejecucion: e.target.value })} /></div>}
            </div>
            <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} value={form.observaciones} onChange={(v) => setForm({ ...form, observaciones: v })} /></div>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}
