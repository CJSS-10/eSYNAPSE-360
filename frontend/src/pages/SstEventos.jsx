import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, FileText, Lock, Plus, Search, X } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import CampoAmpliable from '../components/CampoAmpliable.jsx'
import CampoSugerencias from '../components/CampoSugerencias.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import { api } from '../lib/api.js'
import { fecha, fechaHora, hoy as hoyLocal } from '../lib/fecha.js'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import BarraPasos from '../components/BarraPasos.jsx'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
// Estados (regla 10): gris registro · ámbar análisis/revisión · azul ejecución · verde cerrado · rojo anulado.
const ESTADO = {
  reportado: ['Reportado', 'bg-slate-500/15 text-slate-500'],
  en_investigacion: ['En investigación', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  en_revision: ['En revisión', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'],
  en_acciones: ['En acciones correctivas', 'bg-blue-500/15 text-blue-600 dark:text-blue-400'],
  cerrado: ['Cerrado', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  anulado: ['Anulado', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  registrada: ['Registrada', 'bg-slate-500/15 text-slate-500'],
  cerrada: ['Cerrada', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'],
  anulada: ['Anulada', 'bg-red-500/15 text-red-600 dark:text-red-400'],
}
const TIPO = {
  accidente: ['Accidente', 'bg-red-500/15 text-red-600 dark:text-red-400'],
  incidente_peligroso: ['Incidente peligroso', 'bg-orange-500/15 text-orange-600 dark:text-orange-400'],
  incidente: ['Incidente', 'bg-yellow-400/25 text-yellow-700 dark:text-yellow-300'],
  emergencia: ['Emergencia', 'bg-violet-500/15 text-violet-600 dark:text-violet-400'],
}
const PASOS = ['reportado', 'en_investigacion', 'en_revision', 'en_acciones', 'cerrado']

const Chip = ({ par, extra }) => (par ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${par[1]}`}>{par[0]}{extra}</span> : null)
function Seccion({ titulo, children, extra, bloqueada }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
      <div className="mb-1.5 flex items-center justify-between gap-2"><p className="flex items-center gap-1 text-xs font-semibold text-slate-500 dark:text-slate-400">{bloqueada && <Lock className="h-3 w-3" />}{titulo}</p>{extra}</div>
      <div className="space-y-2 text-slate-600 dark:text-slate-300">{children}</div>
    </div>
  )
}
function Aviso({ texto }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [texto])
  return <p ref={ref} className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">{texto}</p>
}
function Casillas({ opciones, valor, onChange, disabled, cols = 'md:grid-cols-3' }) {
  const otros = (valor || []).filter((v) => String(v).startsWith('Otro:'))
  const otroTxt = otros[0] ? otros[0].slice(5).trim() : ''
  return (
    <div className={`grid gap-1 ${cols}`}>
      {opciones.map((o) => <label key={o} className="flex items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" disabled={disabled} checked={(valor || []).includes(o)} onChange={() => onChange((valor || []).includes(o) ? valor.filter((x) => x !== o) : [...(valor || []), o])} />{o}</label>)}
      <input className={`${inp} !py-1 text-xs`} disabled={disabled} placeholder="Otro (especificar)" value={otroTxt} onChange={(e) => onChange([...(valor || []).filter((x) => !String(x).startsWith('Otro:')), ...(e.target.value.trim() ? [`Otro: ${e.target.value}`] : [])])} />
    </div>
  )
}
/** Personas: trabajador de Organización y personal o, si es externa, nombre escrito. */
function Personas({ valor, onChange, trabajadores, disabled, roles }) {
  const lista = valor || []
  const set = (i, campo, v) => onChange(lista.map((p, j) => (j === i ? { ...p, [campo]: v } : p)))
  return (
    <div className="space-y-1">
      {lista.map((p, i) => (
        <div key={i} className="flex items-center gap-1">
          <div className="flex-1"><CampoSugerencias disabled={disabled} value={p.nombre} opciones={trabajadores.map((t) => ({ valor: t.nombre_completo, detalle: t.puesto_nombre }))}
            onChange={(v) => { const t = trabajadores.find((x) => x.nombre_completo === v); onChange(lista.map((x, j) => (j === i ? { ...x, nombre: v, trabajador: t ? t.id : null } : x))) }} /></div>
          {!lista[i].trabajador && <input className={`${inp} w-36`} disabled={disabled} placeholder="Cargo" value={p.cargo || ''} onChange={(e) => set(i, 'cargo', e.target.value)} />}
          {roles && <select className={`${inp} w-36`} disabled={disabled} value={p.rol || 'miembro'} onChange={(e) => set(i, 'rol', e.target.value)}>{roles.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select>}
          {!disabled && <button className="p-1 text-red-500" title="Quitar" onClick={() => onChange(lista.filter((_, j) => j !== i))}><X className="h-3.5 w-3.5" /></button>}
        </div>
      ))}
      {!disabled && <button className="text-[11px] text-esynapse-500 underline" onClick={() => onChange([...lista, { nombre: '', trabajador: null }])}>+ Agregar</button>}
    </div>
  )
}
const ROLES = [['lider', 'Lidera (Comité SST)'], ['jefe', 'Jefe inmediato'], ['especialista', 'Especialista'], ['miembro', 'Miembro']]
const pedirClave = (confirmar, titulo, mensaje) => confirmar({ titulo, mensaje, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })

/* ------------------------------------------------------------------------------------ Eventos */
const REPORTE_VACIO = { tipo: 'accidente', fecha_hora: '', lugar: '', unidad: '', proceso: '', en_campo: false, cliente: '', actividad: '', descripcion: '', acciones_inmediatas: '', primeros_auxilios: '', potencialmente_afectados: '', pobladores_afectados: '', tipos_emergencia: [], tipos_ambiental: [], testigos: [] }
const INVESTIGACION = ['gravedad', 'grado_incapacidad', 'tipos_accidente', 'metodo_analisis', 'actos_subestandar', 'condiciones_subestandar', 'detalle_actos_condiciones', 'factores_trabajo', 'detalle_factores_trabajo', 'factores_personales', 'detalle_factores_personales', 'que_sucedio', 'porques', 'causas_inmediatas', 'causas_basicas', 'conclusiones', 'filas_iperc', 'requiere_actualizar_iperc']
const AFECTADO_VACIO = { trabajador: null, nombre: '', edad: '', sexo: '', antiguedad: '', turno: 'D', tipo_contrato: '', experiencia_puesto: '', horas_trabajadas: '', sctr: null, partes_cuerpo: [], tipos_lesion: [], dias_descanso: '', empresa: '' }
const localISO = (d) => { const x = new Date(d); x.setMinutes(x.getMinutes() - x.getTimezoneOffset()); return x.toISOString().slice(0, 16) }

export function Eventos({ areasOrg, procesos, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeAprobar, puedeEliminar }) {
  const [items, setItems] = useState([])
  const [cat, setCat] = useState(null)
  const [trabajadores, setTrabajadores] = useState([])
  const [filtro, setFiltro] = useState({ tipo: '', estado: '', anio: String(new Date().getFullYear()), buscar: '' })
  const [form, setForm] = useState(null)
  const [d, setD] = useState(null)
  const [inv, setInv] = useState(null)
  const [equipo, setEquipo] = useState([])
  const [afect, setAfect] = useState(null)
  const [err, setErr] = useState('')
  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const p = new URLSearchParams(Object.entries(filtro).filter(([, v]) => v))
    setItems(await ultima(api.sst.eventos(`?${p}`)))
  }, [filtro])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  useEffect(() => { api.sst.catalogosEventos().then(setCat).catch(() => {}); api.org.trabajadores().then(setTrabajadores).catch(() => {}) }, [])

  const mostrar = (e) => { setD(e); setInv(Object.fromEntries(INVESTIGACION.map((k) => [k, e[k] ?? '']))); setEquipo(e.equipo_investigador || []); setAfect(null) }
  const abrir = async (id) => { setErr(''); setForm(null); mostrar(await api.sst.evento(id)) }
  const accion = async (nombre, datos) => { setErr(''); try { const r = await api.sst.accionEvento(d.id, nombre, datos); mostrar(r); await cargar(); return r } catch (e) { setErr(e.message); return null } }
  const guardarReporte = async () => {
    setErr('')
    const datos = { ...form, unidad: form.unidad || null, proceso: form.proceso || null, fecha_hora: form.fecha_hora ? new Date(form.fecha_hora).toISOString() : null,
      potencialmente_afectados: form.potencialmente_afectados === '' ? null : Number(form.potencialmente_afectados), pobladores_afectados: form.pobladores_afectados === '' ? null : Number(form.pobladores_afectados) }
    try {
      const r = form.id ? await api.sst.editarEvento(form.id, (({ tipo, ...x }) => x)(datos)) : await api.sst.crearEvento(datos)
      setForm(null); await cargar(); mostrar(await api.sst.evento(r.id))
    } catch (e) { setErr(e.message) }
  }
  const guardarInvestigacion = async () => {
    setErr('')
    try { mostrar(await api.sst.editarEvento(d.id, { ...inv, filas_iperc: inv.filas_iperc || [] })) } catch (e) { setErr(e.message) }
  }
  const guardarAfectado = async () => {
    const datos = { ...afect }
    ;['edad', 'dias_descanso', 'horas_trabajadas'].forEach((k) => { datos[k] = datos[k] === '' || datos[k] == null ? null : Number(datos[k]) })
    if (await accion('afectado', datos)) setAfect(null)
  }
  const subir = async (nombre, campos, archivoCampo, archivo) => {
    setErr('')
    const fd = new FormData(); Object.entries(campos).forEach(([k, v]) => fd.append(k, v)); if (archivo) fd.append(archivoCampo, archivo)
    try { mostrar(await api.sst.subirEvento(d.id, nombre, fd)); await cargar() } catch (e) { setErr(e.message) }
  }
  const agregarArchivo = async (file) => {
    const desc = await confirmar({ titulo: 'Evidencia', mensaje: file.name, textoConfirmar: 'Adjuntar', entrada: { etiqueta: 'Qué es (foto del lugar, croquis, declaración del testigo…)', obligatorio: true } })
    if (desc !== null) subir('archivo', { descripcion: desc }, 'archivo', file)
  }
  const notificar = async (file) => {
    const f = await confirmar({ titulo: 'Notificación al Ministerio de Trabajo', mensaje: 'Fecha en que se notificó (accidente mortal o incidente peligroso: dentro de las 24 horas).', textoConfirmar: 'Registrar', entrada: { etiqueta: 'Fecha (AAAA-MM-DD)', obligatorio: true, valorInicial: hoyLocal() } })
    if (f !== null) subir('notificar_mtpe', { fecha: f }, 'constancia', file)
  }
  const iniciar = async () => {
    if (!equipo.filter((p) => p.nombre.trim()).length) { setErr('Conforme el equipo investigador (abajo) antes de iniciar.'); return }
    if (!await confirmar({ titulo: 'Iniciar la investigación', mensaje: 'El reporte queda cerrado (solo lectura). Las personas afectadas se pueden seguir completando durante la investigación.', textoConfirmar: 'Iniciar' })) return
    accion('iniciar_investigacion', { equipo_investigador: equipo.filter((p) => p.nombre.trim()) })
  }
  const concluir = async () => { const c = await pedirClave(confirmar, 'Concluir la investigación', 'Firma el informe como elaborado. Pasa a revisión; la investigación queda de solo lectura.'); if (c !== null) accion('concluir', { password: c }) }
  const devolver = async () => { const m = await confirmar({ titulo: 'Devolver el informe', mensaje: 'Vuelve a investigación para completar o corregir.', textoConfirmar: 'Devolver', entrada: { etiqueta: 'Qué falta', obligatorio: true, multilinea: true } }); if (m !== null) accion('devolver', { motivo: m }) }
  const aprobar = async () => { const c = await pedirClave(confirmar, 'Revisar el informe', 'Firma la revisión. Se registra el hallazgo y su solicitud de acción correctiva: las acciones y su eficacia se siguen en Acciones correctivas.'); if (c !== null) accion('aprobar_informe', { password: c }) }
  const cerrar = async () => {
    let iperc = false
    if (d.requiere_actualizar_iperc) { if (!await confirmar({ titulo: 'Matriz IPERC', mensaje: 'La investigación pidió actualizar la matriz IPERC. ¿Se actualizó?', textoConfirmar: 'Sí, se actualizó' })) return; iperc = true }
    const c = await pedirClave(confirmar, 'Cerrar el evento', 'Las acciones correctivas están implementadas y su eficacia verificada.')
    if (c !== null) accion('cerrar', { password: c, iperc_actualizado: iperc })
  }
  const anular = async () => { const m = await confirmar({ titulo: 'Anular el reporte', mensaje: 'Solo si se registró por error. Queda como registro.', textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true, multilinea: true } }); if (m !== null) accion('anular', { motivo: m }) }
  const descanso = async (a) => { const v = await confirmar({ titulo: 'Descanso médico', mensaje: `${a.nombre}: actualizar los días de descanso médico (queda en el historial).`, textoConfirmar: 'Actualizar', entrada: { etiqueta: 'Días', obligatorio: true, valorInicial: String(a.dias_descanso ?? '') } }); if (v !== null) accion('actualizar_descanso', { id: a.id, dias_descanso: v }) }

  const enRep = d?.estado === 'reportado' && puedeEditar
  const enInv = d?.estado === 'en_investigacion' && puedeEditar
  const afectEditable = (d?.estado === 'reportado' || d?.estado === 'en_investigacion') && puedeEditar
  const vivo = d && !['cerrado', 'anulado'].includes(d.estado)
  const esAcc = (d?.tipo || form?.tipo) === 'accidente'

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input-esynapse w-56 pl-9" placeholder="Código, lugar, persona…" value={filtro.buscar} onChange={(e) => setFiltro({ ...filtro, buscar: e.target.value })} /></div>
        <select className="input-esynapse w-44" value={filtro.tipo} onChange={(e) => setFiltro({ ...filtro, tipo: e.target.value })}><option value="">Todo tipo</option>{Object.entries(TIPO).map(([k, [n]]) => <option key={k} value={k}>{n}</option>)}</select>
        <select className="input-esynapse w-44" value={filtro.estado} onChange={(e) => setFiltro({ ...filtro, estado: e.target.value })}><option value="">Todo estado</option>{PASOS.concat('anulado').map((k) => <option key={k} value={k}>{ESTADO[k][0]}</option>)}</select>
        <input className="input-esynapse w-24" type="number" value={filtro.anio} onChange={(e) => setFiltro({ ...filtro, anio: e.target.value })} />
        {puedeCrear && <button className="btn-primary ml-auto" onClick={() => { setErr(''); setD(null); setForm({ ...REPORTE_VACIO, fecha_hora: localISO(new Date()) }) }}><Plus className="h-4 w-4" /> Reportar evento</button>}
      </div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Código</th><th className="px-2 text-right">Fecha y hora</th><th className="px-2 text-center">Tipo</th><th className="px-2">Lugar</th><th className="px-2">Área</th><th className="px-2 text-right">Afectados</th><th className="px-2 text-center">Estado</th><th className="px-2">Alertas</th></tr></thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id} onClick={() => abrir(e.id)} className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40 ${e.estado === 'anulado' ? 'opacity-50' : ''}`}>
                <td className="whitespace-nowrap px-2 py-2 font-mono">{e.codigo}</td><td className="whitespace-nowrap px-2 text-right">{fechaHora(e.fecha_hora)}</td>
                <td className="px-2 text-center"><Chip par={TIPO[e.tipo]} />{e.gravedad && <p className="text-[11px] text-slate-500">{e.gravedad_display}</p>}</td>
                <td className="max-w-[14rem] truncate px-2" title={e.lugar}>{e.lugar}</td><td className="px-2">{e.unidad_nombre || '—'}</td>
                <td className="px-2 text-right">{e.afectados_nombres.join(', ') || '—'}</td><td className="px-2 text-center"><Chip par={ESTADO[e.estado]} /></td>
                <td className="px-2">{e.pendiente_mtpe && <span className="block text-[11px] font-semibold text-red-600">Notificar al MTPE</span>}{e.reporte_tardio && <span className="block text-[11px] text-amber-600">Reporte tardío</span>}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="py-8 text-slate-400">Sin eventos registrados</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Corregir el reporte' : 'Reportar incidente, accidente o emergencia'} onCerrar={() => setForm(null)} ancho="max-w-4xl">
        {form && (
          <div className="space-y-3 text-sm">
            {!form.id && <p className="rounded bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">Reporte dentro de las 24 horas de ocurrido. El Comité SST comunica de inmediato al Gerente General. Accidente mortal o incidente peligroso: notificar al Ministerio de Trabajo.</p>}
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>Tipo</label><select className={inp} disabled={Boolean(form.id)} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{(cat?.tipos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className={lbl}>Fecha y hora de ocurrencia</label><input type="datetime-local" className={inp} value={form.fecha_hora} onChange={(e) => setForm({ ...form, fecha_hora: e.target.value })} /></div>
              <div className="md:col-span-2"><label className={lbl}>Lugar exacto</label><input className={inp} value={form.lugar} onChange={(e) => setForm({ ...form, lugar: e.target.value })} /></div>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>Área</label><select className={inp} value={String(form.unidad || '')} onChange={(e) => setForm({ ...form, unidad: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{areasOrg.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select></div>
              <div><label className={lbl}>Proceso</label><select className={inp} value={String(form.proceso || '')} onChange={(e) => setForm({ ...form, proceso: e.target.value ? Number(e.target.value) : '' })}><option value="">— (el del área)</option>{procesos.filter((p) => p.is_active && !p.padre).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></div>
              <div><label className={lbl}>Actividad que se ejecutaba</label><input className={inp} value={form.actividad} onChange={(e) => setForm({ ...form, actividad: e.target.value })} /></div>
              <div><label className="flex items-center gap-1.5 pt-6 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={form.en_campo} onChange={(e) => setForm({ ...form, en_campo: e.target.checked })} /> En instalaciones del cliente</label>{form.en_campo && <input className={`${inp} mt-1`} placeholder="Cliente" value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })} />}</div>
            </div>
            <div><label className={lbl}>Descripción de los hechos (solo hechos comprobables)</label><CampoAmpliable multilinea rows={3} value={form.descripcion} onChange={(v) => setForm({ ...form, descripcion: v })} /></div>
            <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Acciones inmediatas</label><CampoAmpliable multilinea value={form.acciones_inmediatas} onChange={(v) => setForm({ ...form, acciones_inmediatas: v })} /></div>
              <div><label className={lbl}>Atención de primeros auxilios</label><CampoAmpliable multilinea value={form.primeros_auxilios} onChange={(v) => setForm({ ...form, primeros_auxilios: v })} /></div>
            </div>
            {form.tipo === 'incidente_peligroso' && <div className="grid gap-3 md:grid-cols-2">
              <div><label className={lbl}>Trabajadores potencialmente afectados</label><input type="number" className={inp} value={form.potencialmente_afectados ?? ''} onChange={(e) => setForm({ ...form, potencialmente_afectados: e.target.value })} /></div>
              <div><label className={lbl}>Pobladores potencialmente afectados</label><input type="number" className={inp} value={form.pobladores_afectados ?? ''} onChange={(e) => setForm({ ...form, pobladores_afectados: e.target.value })} /></div>
            </div>}
            {form.tipo === 'emergencia' && <>
              <div><label className={lbl}>Tipo de emergencia</label><Casillas opciones={cat?.tipos_emergencia || []} valor={form.tipos_emergencia} onChange={(v) => setForm({ ...form, tipos_emergencia: v })} /></div>
              <div><label className={lbl}>Tipo de accidente ambiental</label><Casillas opciones={cat?.tipos_ambiental || []} valor={form.tipos_ambiental} onChange={(v) => setForm({ ...form, tipos_ambiental: v })} /></div>
            </>}
            <div><label className={lbl}>Testigos</label><Personas valor={form.testigos} onChange={(v) => setForm({ ...form, testigos: v })} trabajadores={trabajadores} /></div>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" disabled={!form.lugar.trim() || !form.descripcion.trim() || !form.fecha_hora} onClick={guardarReporte}>{form.id ? 'Guardar' : 'Registrar reporte'}</button></div>
          </div>
        )}
      </Modal>

      <Modal abierto={Boolean(d) && !form} titulo={d ? `${d.codigo} — ${d.tipo_display}${d.gravedad ? ` (${d.gravedad_display.toLowerCase()})` : ''}` : ''} onCerrar={() => setD(null)} panel ancho="max-w-6xl">
        {d && inv && (
          <div className="space-y-3 text-sm">
            <BarraPasos pasos={PASOS.map((p) => ESTADO[p][0])} actual={Math.max(0, PASOS.indexOf(d.estado))} cerrado={d.estado === 'cerrado'} />
            <div className="flex flex-wrap items-center gap-1">
              {d.estado === 'anulado' && <Chip par={ESTADO.anulado} extra={`: ${d.motivo_anulacion}`} />}
              <span className="ml-auto flex gap-2">
                {d.tipo !== 'emergencia' && <button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.sst.registroPdf(d.id))}><FileText className="h-3.5 w-3.5" /> Registro</button>}
                <button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.sst.informePdf(d.id))}><FileText className="h-3.5 w-3.5" /> Informe de investigación</button>
              </span>
            </div>
            {d.reporte_tardio && <p className="flex items-center gap-1 text-[11px] text-amber-600"><AlertTriangle className="h-3.5 w-3.5" /> Reportado después de las 24 horas ({fechaHora(d.fecha_reporte)}).</p>}
            {d.requiere_notificacion_mtpe && (
              <p className={`flex flex-wrap items-center gap-2 rounded px-3 py-2 text-xs ${d.notificacion_mtpe ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' : 'bg-red-500/10 text-red-600'}`}>
                {d.notificacion_mtpe ? `Notificado al Ministerio de Trabajo el ${fecha(d.notificacion_mtpe)}.` : 'Accidente mortal o incidente peligroso: notificar al Ministerio de Trabajo dentro de las 24 horas.'}
                {d.constancia_url && <a className="underline" href={d.constancia_url} target="_blank" rel="noreferrer">constancia</a>}
                {vivo && puedeEditar && <label className="btn-secondary !py-0.5 cursor-pointer text-[11px]">{d.notificacion_mtpe ? 'Corregir' : 'Registrar notificación'}<input type="file" className="hidden" onChange={(e) => notificar(e.target.files[0] || null)} /></label>}
                {vivo && puedeEditar && !d.notificacion_mtpe && <button className="text-[11px] underline" onClick={() => notificar(null)}>sin constancia</button>}
              </p>
            )}
            {err && <Aviso texto={err} />}
            <Seccion titulo="Reporte" bloqueada={!enRep} extra={enRep && <button className="btn-secondary !py-0.5 text-[11px]" onClick={() => setForm({ id: d.id, ...Object.fromEntries(Object.keys(REPORTE_VACIO).map((k) => [k, d[k] ?? REPORTE_VACIO[k]])), fecha_hora: localISO(d.fecha_hora) })}>Corregir</button>}>
              <div className="grid gap-x-4 md:grid-cols-4"><p><strong>Fecha:</strong> {fechaHora(d.fecha_hora)}</p><p><strong>Área:</strong> {d.unidad_nombre || '—'}</p><p className="md:col-span-2"><strong>Lugar:</strong> {d.lugar}{d.en_campo ? ` (cliente: ${d.cliente || '—'})` : ''}</p></div>
              {d.actividad && <p><strong>Actividad:</strong> {d.actividad}</p>}
              <p className="whitespace-pre-wrap"><strong>Hechos:</strong> {d.descripcion}</p>
              {d.acciones_inmediatas && <p className="whitespace-pre-wrap"><strong>Acciones inmediatas:</strong> {d.acciones_inmediatas}</p>}
              {d.testigos?.length > 0 && <p><strong>Testigos:</strong> {d.testigos.map((t) => `${t.nombre}${t.cargo ? ` (${t.cargo})` : ''}`).join(', ')}</p>}
              <p className="text-[11px] text-slate-400">Reportado por {d.reportado_por_nombre || '—'} el {fechaHora(d.fecha_reporte)}</p>
            </Seccion>
            <Seccion titulo={`Personas afectadas (${d.afectados.length})`} extra={afectEditable && !afect && <button className="btn-secondary !py-0.5 text-[11px]" onClick={() => setAfect({ ...AFECTADO_VACIO })}><Plus className="h-3.5 w-3.5" /> Persona</button>}>
              {d.afectados.length === 0 && <p className="text-slate-400">Sin personas afectadas registradas.</p>}
              {d.afectados.map((a) => (
                <div key={a.id} className="flex flex-wrap items-center gap-2 border-b border-slate-100 py-1 dark:border-slate-800/60">
                  <strong>{a.nombre}</strong><span className="text-slate-500">{[a.puesto, a.area, a.empresa].filter(Boolean).join(' · ')}</span>
                  <span>{[a.edad ? `${a.edad} años` : '', a.sexo].filter(Boolean).join(' · ')}</span>
                  {a.partes_cuerpo.length > 0 && <span>Lesión: {a.partes_cuerpo.join(', ')}{a.tipos_lesion.length ? ` (${a.tipos_lesion.join(', ')})` : ''}</span>}
                  <span>Descanso: {a.dias_descanso ?? 0} día(s)</span>
                  <span className="ml-auto flex gap-1">
                    {afectEditable && <button className="text-[11px] underline" onClick={() => setAfect({ ...AFECTADO_VACIO, ...Object.fromEntries(Object.entries(a).map(([k, v]) => [k, v ?? ''])) })}>Corregir</button>}
                    {afectEditable && <button className="text-[11px] text-red-500 underline" onClick={() => accion('quitar_afectado', { id: a.id })}>Quitar</button>}
                    {!afectEditable && vivo && puedeEditar && <button className="text-[11px] underline" onClick={() => descanso(a)}>Actualizar descanso médico</button>}
                  </span>
                </div>
              ))}
              {afect && (
                <div className="space-y-2 rounded-lg border border-esynapse-600/30 bg-esynapse-600/5 p-3">
                  <div className="grid gap-2 md:grid-cols-4">
                    <div className="md:col-span-2"><label className={lbl}>Trabajador (o nombre si es externo)</label><CampoSugerencias value={afect.nombre} opciones={trabajadores.map((t) => ({ valor: t.nombre_completo, detalle: t.puesto_nombre }))} onChange={(v) => { const t = trabajadores.find((x) => x.nombre_completo === v); setAfect({ ...afect, nombre: v, trabajador: t ? t.id : null }) }} /></div>
                    {!afect.trabajador && <div><label className={lbl}>Empresa</label><input className={inp} value={afect.empresa} onChange={(e) => setAfect({ ...afect, empresa: e.target.value })} /></div>}
                    <div className="grid grid-cols-2 gap-1"><div><label className={lbl}>Edad</label><input type="number" className={inp} value={afect.edad} onChange={(e) => setAfect({ ...afect, edad: e.target.value })} /></div><div><label className={lbl}>Sexo</label><select className={inp} value={afect.sexo} onChange={(e) => setAfect({ ...afect, sexo: e.target.value })}><option value="">—</option><option value="F">F</option><option value="M">M</option></select></div></div>
                  </div>
                  <div className="grid gap-2 md:grid-cols-6">
                    <div><label className={lbl}>Antigüedad</label><input className={inp} value={afect.antiguedad} onChange={(e) => setAfect({ ...afect, antiguedad: e.target.value })} /></div>
                    <div><label className={lbl}>Experiencia en el puesto</label><input className={inp} value={afect.experiencia_puesto} onChange={(e) => setAfect({ ...afect, experiencia_puesto: e.target.value })} /></div>
                    <div><label className={lbl}>Tipo de contrato</label><input className={inp} value={afect.tipo_contrato} onChange={(e) => setAfect({ ...afect, tipo_contrato: e.target.value })} /></div>
                    <div><label className={lbl}>Turno</label><select className={inp} value={afect.turno} onChange={(e) => setAfect({ ...afect, turno: e.target.value })}><option value="D">Día</option><option value="T">Tarde</option><option value="N">Noche</option></select></div>
                    <div><label className={lbl}>Horas trabajadas antes</label><input type="number" step="0.5" className={inp} value={afect.horas_trabajadas} onChange={(e) => setAfect({ ...afect, horas_trabajadas: e.target.value })} /></div>
                    <div><label className={lbl}>Días de descanso médico</label><input type="number" className={inp} value={afect.dias_descanso} onChange={(e) => setAfect({ ...afect, dias_descanso: e.target.value })} /></div>
                  </div>
                  <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={afect.sctr === true} onChange={(e) => setAfect({ ...afect, sctr: e.target.checked })} /> Con SCTR</label>
                  <div><label className={lbl}>Parte del cuerpo lesionada</label><Casillas opciones={cat?.partes_cuerpo || []} valor={afect.partes_cuerpo} onChange={(v) => setAfect({ ...afect, partes_cuerpo: v })} cols="md:grid-cols-6" /></div>
                  <div><label className={lbl}>Tipo de lesión</label><Casillas opciones={cat?.tipos_lesion || []} valor={afect.tipos_lesion} onChange={(v) => setAfect({ ...afect, tipos_lesion: v })} cols="md:grid-cols-5" /></div>
                  <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setAfect(null)}>Cancelar</button><button className="btn-primary" disabled={!afect.nombre.trim()} onClick={guardarAfectado}>Guardar persona</button></div>
                </div>
              )}
            </Seccion>
            {d.estado === 'reportado' && puedeEditar && (
              <Seccion titulo="Equipo investigador (lo conforma el Comité SST)"><Personas valor={equipo} onChange={setEquipo} trabajadores={trabajadores} roles={ROLES} /><p className="text-[11px] text-slate-400">El trabajador involucrado y los testigos no forman parte del equipo.</p></Seccion>
            )}
            {d.estado !== 'reportado' && d.estado !== 'anulado' && (
              <Seccion titulo="Investigación" bloqueada={!enInv} extra={enInv && <button className="btn-primary !py-1 text-xs" onClick={guardarInvestigacion}>Guardar investigación</button>}>
                <p><strong>Equipo investigador:</strong> {(d.equipo_investigador || []).map((m) => `${m.nombre} (${(ROLES.find((r) => r[0] === m.rol) || ['', m.rol])[1]})`).join(', ')} · <strong>Inicio:</strong> {fecha(d.fecha_inicio_investigacion)}</p>
                {esAcc && <div className="grid gap-3 md:grid-cols-3">
                  <div><label className={lbl}>Gravedad</label><select className={inp} disabled={!enInv} value={inv.gravedad} onChange={(e) => setInv({ ...inv, gravedad: e.target.value })}><option value="">—</option>{(cat?.gravedades || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
                  {inv.gravedad === 'incapacitante' && <div><label className={lbl}>Grado</label><select className={inp} disabled={!enInv} value={inv.grado_incapacidad} onChange={(e) => setInv({ ...inv, grado_incapacidad: e.target.value })}><option value="">—</option>{(cat?.grados || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>}
                </div>}
                {esAcc && <div><label className={lbl}>Tipo de accidente</label><Casillas disabled={!enInv} opciones={cat?.tipos_accidente || []} valor={inv.tipos_accidente} onChange={(v) => setInv({ ...inv, tipos_accidente: v })} cols="md:grid-cols-5" /></div>}
                <div className="grid gap-3 md:grid-cols-2">
                  <div><label className={lbl}>Actos subestándar</label><Casillas disabled={!enInv} opciones={cat?.actos || []} valor={inv.actos_subestandar} onChange={(v) => setInv({ ...inv, actos_subestandar: v })} cols="md:grid-cols-2" /></div>
                  <div><label className={lbl}>Condiciones subestándar</label><Casillas disabled={!enInv} opciones={cat?.condiciones || []} valor={inv.condiciones_subestandar} onChange={(v) => setInv({ ...inv, condiciones_subestandar: v })} cols="md:grid-cols-2" /></div>
                </div>
                <div><label className={lbl}>Actos o condiciones subestándar existentes</label><CampoAmpliable multilinea disabled={!enInv} value={inv.detalle_actos_condiciones} onChange={(v) => setInv({ ...inv, detalle_actos_condiciones: v })} /></div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div><label className={lbl}>Factores de trabajo</label><Casillas disabled={!enInv} opciones={cat?.factores_trabajo || []} valor={inv.factores_trabajo} onChange={(v) => setInv({ ...inv, factores_trabajo: v })} cols="md:grid-cols-2" /><CampoAmpliable multilinea disabled={!enInv} placeholder="Explicación" value={inv.detalle_factores_trabajo} onChange={(v) => setInv({ ...inv, detalle_factores_trabajo: v })} /></div>
                  <div><label className={lbl}>Factores personales</label><Casillas disabled={!enInv} opciones={cat?.factores_personales || []} valor={inv.factores_personales} onChange={(v) => setInv({ ...inv, factores_personales: v })} cols="md:grid-cols-2" /><CampoAmpliable multilinea disabled={!enInv} placeholder="Explicación" value={inv.detalle_factores_personales} onChange={(v) => setInv({ ...inv, detalle_factores_personales: v })} /></div>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <div><label className={lbl}>Metodología</label><select className={inp} disabled={!enInv} value={inv.metodo_analisis} onChange={(e) => setInv({ ...inv, metodo_analisis: e.target.value })}>{(cat?.metodos || []).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
                  <div className="md:col-span-2"><label className={lbl}>¿Qué sucedió?</label><input className={inp} disabled={!enInv} value={inv.que_sucedio} onChange={(e) => setInv({ ...inv, que_sucedio: e.target.value })} /></div>
                </div>
                <div className="space-y-1">{(inv.porques || []).concat(enInv && (inv.porques || []).length < 7 ? [''] : []).map((pq, i) => <div key={i} className="flex items-center gap-2"><span className="w-16 text-right text-[11px] font-semibold">¿Por qué? {i + 1}</span><input className={`${inp} flex-1`} disabled={!enInv} value={pq} onChange={(e) => { const arr = [...(inv.porques || [])]; arr[i] = e.target.value; setInv({ ...inv, porques: arr }) }} /></div>)}</div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div><label className={lbl}>Causas inmediatas</label><CampoAmpliable multilinea disabled={!enInv} value={inv.causas_inmediatas} onChange={(v) => setInv({ ...inv, causas_inmediatas: v })} /></div>
                  <div><label className={lbl}>Causas básicas (raíz)</label><CampoAmpliable multilinea disabled={!enInv} value={inv.causas_basicas} onChange={(v) => setInv({ ...inv, causas_basicas: v })} /></div>
                </div>
                <div><label className={lbl}>Conclusiones</label><CampoAmpliable multilinea disabled={!enInv} value={inv.conclusiones} onChange={(v) => setInv({ ...inv, conclusiones: v })} /></div>
                <label className="flex items-center gap-1.5"><input type="checkbox" className="accent-esynapse-600" disabled={!enInv} checked={Boolean(inv.requiere_actualizar_iperc)} onChange={(e) => setInv({ ...inv, requiere_actualizar_iperc: e.target.checked })} /> Requiere actualizar la matriz IPERC</label>
                {d.firma_elaborado?.nombre && <p className="text-[11px] text-slate-500">Elaborado por {d.firma_elaborado.nombre} ({d.firma_elaborado.sigla}) el {fechaHora(d.firma_elaborado.fecha)}{d.firma_revisado?.nombre ? ` · Revisado por ${d.firma_revisado.nombre} (${d.firma_revisado.sigla}) el ${fechaHora(d.firma_revisado.fecha)}` : ''}</p>}
              </Seccion>
            )}
            {d.acciones && (
              <Seccion titulo="Acciones correctivas" extra={<Link to="/acciones-correctivas" className="text-[11px] text-esynapse-500 underline">Ir a Acciones correctivas</Link>}>
                <p>Hallazgo <strong>{d.acciones.hallazgo}</strong> · Solicitud <strong>{d.acciones.sac}</strong> ({d.acciones.sac_estado_display})</p>
                {d.acciones.acciones.length === 0 && <p className="text-slate-400">Las acciones se registran en la solicitud de acción correctiva.</p>}
                {d.acciones.acciones.map((a, i) => <p key={i}>• {a.descripcion} — {a.responsable} · {fecha(a.fecha)} · <strong>{a.estado}</strong></p>)}
              </Seccion>
            )}
            <Seccion titulo={`Evidencias (${d.archivos.length})`} extra={vivo && puedeEditar && <label className="btn-secondary !py-0.5 cursor-pointer text-[11px]"><Plus className="inline h-3.5 w-3.5" /> Adjuntar<input type="file" className="hidden" onChange={(e) => e.target.files[0] && agregarArchivo(e.target.files[0])} /></label>}>
              {d.archivos.length === 0 && <p className="text-slate-400">Fotografías, croquis, declaraciones firmadas, descanso médico…</p>}
              {d.archivos.map((a) => <p key={a.id}><a className="underline" href={a.url} target="_blank" rel="noreferrer">{a.descripcion}</a> · {fecha(a.fecha)}</p>)}
            </Seccion>
            {d.historial?.length > 0 && <Seccion titulo="Historial">{d.historial.slice().reverse().map((h, i) => <p key={i}>{(h.fecha || '').slice(0, 16).replace('T', ' ')} · {h.usuario} · <strong>{h.accion}</strong>{h.motivo ? `: ${h.motivo}` : ''}{h.tardio ? ` (${h.tardio})` : ''}</p>)}</Seccion>}
            {d.estado === 'reportado' && puedeEditar && <BarraEtapa titulo="Reporte registrado" nota="Registre a las personas afectadas, conforme el equipo investigador e inicie la investigación." botones={[...(puedeEliminar ? [{ texto: 'Anular', accion: anular, secundario: true }] : []), { texto: 'Iniciar investigación', accion: iniciar }]} />}
            {d.estado === 'en_investigacion' && puedeEditar && <BarraEtapa titulo="En investigación" nota="Guarde el análisis y concluya: se exige gravedad (accidentes), porqués, causas inmediatas y básicas y conclusiones." botones={[...(puedeEliminar ? [{ texto: 'Anular', accion: anular, secundario: true }] : []), { texto: 'Concluir con firma', accion: concluir }]} />}
            {d.estado === 'en_revision' && puedeAprobar && <BarraEtapa titulo="Informe en revisión" nota="Al revisarlo se registran el hallazgo y la solicitud de acción correctiva." botones={[{ texto: 'Devolver', accion: devolver, secundario: true }, { texto: 'Revisar con firma', accion: aprobar }]} />}
            {d.estado === 'en_acciones' && puedeAprobar && <BarraEtapa titulo="En acciones correctivas" nota={['cerrada_conforme', 'cerrada_sin_ac'].includes(d.acciones?.sac_estado) ? 'La solicitud de acción correctiva está cerrada: puede cerrar el evento.' : `Se cierra cuando la solicitud ${d.acciones?.sac || ''} esté cerrada (acciones implementadas y eficacia verificada).`} botones={[{ texto: 'Cerrar con firma', accion: cerrar }]} />}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ------------------------------------------------------------------------------- Enfermedades */
const ENF_VACIA = { fecha: hoyLocal(), nombre: '', trabajadores_afectados: 1, unidad: '', agente: 'fisico', agente_detalle: '', causas: '', trabajadores_expuestos: '', cancer_profesional: false }

export function Enfermedades({ areasOrg, confirmar, setError, abrirPdf, puedeCrear, puedeEditar, puedeAprobar, puedeEliminar }) {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(null)
  const [d, setD] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(async () => setItems(await api.sst.enfermedades()), [])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  const guardar = async () => {
    setErr('')
    const datos = { ...form, unidad: form.unidad || null, trabajadores_expuestos: form.trabajadores_expuestos === '' ? null : Number(form.trabajadores_expuestos) }
    try { const r = form.id ? await api.sst.editarEnfermedad(form.id, datos) : await api.sst.crearEnfermedad(datos); setForm(null); await cargar(); setD(r) } catch (e) { setErr(e.message) }
  }
  const accion = async (nombre, datos) => { setErr(''); try { const r = await api.sst.accionEnfermedad(d.id, nombre, datos); setD(r); await cargar() } catch (e) { setErr(e.message) } }
  const registrar = async () => { const c = await pedirClave(confirmar, 'Firmar el registro', 'Se registran el hallazgo y la solicitud de acción correctiva. El registro queda de solo lectura.'); if (c !== null) accion('registrar_acciones', { password: c }) }
  const anular = async () => { const m = await confirmar({ titulo: 'Anular el registro', mensaje: 'Solo si se registró por error.', textoConfirmar: 'Anular', peligro: true, entrada: { etiqueta: 'Motivo', obligatorio: true } }); if (m !== null) accion('anular', { motivo: m }) }
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2"><p className="text-xs text-slate-500">Registro sin datos personales de salud: el diagnóstico individual se conserva en la historia clínica ocupacional (médico ocupacional).</p>
        {puedeCrear && <button className="btn-primary ml-auto shrink-0" onClick={() => { setErr(''); setForm({ ...ENF_VACIA }) }}><Plus className="h-4 w-4" /> Registrar</button>}</div>
      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><th className="px-2 py-2">Código</th><th className="px-2 text-right">Fecha</th><th className="px-2">Enfermedad</th><th className="px-2">Área</th><th className="px-2 text-right">Afectados</th><th className="px-2">Agente</th><th className="px-2 text-center">Estado</th></tr></thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.id} onClick={() => { setErr(''); setD(o) }} className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="px-2 py-2 font-mono">{o.codigo}</td><td className="px-2 text-right">{fecha(o.fecha)}</td><td className="px-2">{o.nombre}</td><td className="px-2">{o.unidad_nombre || '—'}</td>
                <td className="px-2 text-right">{o.trabajadores_afectados}</td><td className="px-2">{o.agente_display}</td><td className="px-2 text-center"><Chip par={ESTADO[o.estado]} /></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={7} className="py-8 text-slate-400">Sin enfermedades ocupacionales registradas</td></tr>}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(form)} titulo={form?.id ? 'Corregir el registro' : 'Registrar enfermedad ocupacional'} onCerrar={() => setForm(null)} ancho="max-w-3xl">
        {form && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="md:col-span-2"><label className={lbl}>Nombre de la enfermedad ocupacional</label><input className={inp} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div>
              <div><label className={lbl}>Fecha</label><input type="date" className={inp} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <div><label className={lbl}>Área</label><select className={inp} value={String(form.unidad || '')} onChange={(e) => setForm({ ...form, unidad: e.target.value ? Number(e.target.value) : '' })}><option value="">—</option>{areasOrg.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select></div>
              <div><label className={lbl}>N° de trabajadores afectados</label><input type="number" min="1" className={inp} value={form.trabajadores_afectados} onChange={(e) => setForm({ ...form, trabajadores_afectados: e.target.value })} /></div>
              <div><label className={lbl}>N° de expuestos al agente</label><input type="number" className={inp} value={form.trabajadores_expuestos ?? ''} onChange={(e) => setForm({ ...form, trabajadores_expuestos: e.target.value })} /></div>
              <div><label className="flex items-center gap-1.5 pt-6 text-xs"><input type="checkbox" className="accent-esynapse-600" checked={form.cancer_profesional} onChange={(e) => setForm({ ...form, cancer_profesional: e.target.checked })} /> Cáncer profesional</label></div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className={lbl}>Agente / factor de riesgo</label><select className={inp} value={form.agente} onChange={(e) => setForm({ ...form, agente: e.target.value })}>{[['fisico', 'Físico'], ['quimico', 'Químico'], ['biologico', 'Biológico'], ['ergonomico', 'Ergonómico'], ['psicosocial', 'Psicosocial']].map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div className="md:col-span-2"><label className={lbl}>Detalle del agente</label><input className={inp} value={form.agente_detalle} onChange={(e) => setForm({ ...form, agente_detalle: e.target.value })} /></div>
            </div>
            <div><label className={lbl}>Causas que generan la enfermedad</label><CampoAmpliable multilinea rows={3} value={form.causas} onChange={(v) => setForm({ ...form, causas: v })} /></div>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setForm(null)}>Cancelar</button><button className="btn-primary" disabled={!form.nombre.trim() || !form.causas.trim()} onClick={guardar}>Guardar</button></div>
          </div>
        )}
      </Modal>
      <Modal abierto={Boolean(d) && !form} titulo={d ? `${d.codigo} — ${d.nombre}` : ''} onCerrar={() => setD(null)} ancho="max-w-3xl">
        {d && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2"><Chip par={ESTADO[d.estado]} />{d.motivo_anulacion && <span className="text-[11px] text-red-500">{d.motivo_anulacion}</span>}
              <span className="ml-auto flex gap-2"><button className="btn-secondary !py-1 text-xs" onClick={() => abrirPdf(api.sst.enfermedadPdf(d.id))}><FileText className="h-3.5 w-3.5" /> Registro</button>
                {d.estado === 'registrada' && puedeEditar && <button className="btn-secondary !py-1 text-xs" onClick={() => setForm({ ...ENF_VACIA, ...Object.fromEntries(Object.keys(ENF_VACIA).map((k) => [k, d[k] ?? ENF_VACIA[k]])), id: d.id })}>Corregir</button>}</span></div>
            {err && <Aviso texto={err} />}
            <Seccion titulo="Registro">
              <div className="grid gap-x-4 md:grid-cols-3"><p><strong>Fecha:</strong> {fecha(d.fecha)}</p><p><strong>Área:</strong> {d.unidad_nombre || '—'}</p><p><strong>Veces en el área:</strong> {d.veces_en_area}</p></div>
              <p><strong>Afectados:</strong> {d.trabajadores_afectados} · <strong>Expuestos:</strong> {d.trabajadores_expuestos ?? '—'} · <strong>Agente:</strong> {d.agente_display}{d.agente_detalle ? ` (${d.agente_detalle})` : ''}{d.cancer_profesional ? ' · Cáncer profesional' : ''}</p>
              <p className="whitespace-pre-wrap"><strong>Causas:</strong> {d.causas}</p>
            </Seccion>
            {d.acciones && <Seccion titulo="Acciones correctivas" extra={<Link to="/acciones-correctivas" className="text-[11px] text-esynapse-500 underline">Ir a Acciones correctivas</Link>}><p>Hallazgo <strong>{d.acciones.hallazgo}</strong> · Solicitud <strong>{d.acciones.sac}</strong> ({d.acciones.sac_estado_display})</p>{d.acciones.acciones.map((a, i) => <p key={i}>• {a.descripcion} — {a.responsable} · {fecha(a.fecha)} · <strong>{a.estado}</strong></p>)}</Seccion>}
            {d.estado === 'registrada' && (puedeAprobar || puedeEliminar) && <BarraEtapa titulo="Registro" nota="Al firmar se registran el hallazgo y la solicitud de acción correctiva." botones={[...(puedeEliminar ? [{ texto: 'Anular', accion: anular, secundario: true }] : []), ...(puedeAprobar ? [{ texto: 'Firmar y registrar acciones', accion: registrar }] : [])]} />}
            {d.estado === 'en_acciones' && puedeAprobar && <BarraEtapa titulo="En acciones correctivas" nota="Se cierra cuando la solicitud de acción correctiva esté cerrada." botones={[{ texto: 'Cerrar', accion: () => accion('cerrar') }]} />}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ------------------------------------------------------------------------------- Estadísticas */
export function Estadisticas({ confirmar, setError, abrirPdf, puedeEditar }) {
  const [anio, setAnio] = useState(new Date().getFullYear())
  const [r, setR] = useState(null)
  const [mes, setMes] = useState(null)
  const [inf, setInf] = useState(null)
  const [err, setErr] = useState('')
  const cargar = useCallback(async () => setR(await api.sst.estadisticas(anio)), [anio])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar, setError])
  const guardarMes = async () => {
    setErr('')
    const datos = { anio, ...Object.fromEntries(Object.entries(mes).map(([k, v]) => [k, ['observaciones'].includes(k) ? v : Number(v) || 0])) }
    try { await api.sst.datosMes(datos); setMes(null); await cargar() } catch (e) { setErr(e.message) }
  }
  const guardarInforme = async () => {
    const c = await pedirClave(confirmar, 'Firmar el análisis', 'Queda como responsable del registro de estadísticas.')
    if (c === null) return
    setErr('')
    try { await api.sst.informeEstadisticas({ ...inf, anio, password: c }); setInf(null); await cargar() } catch (e) { setErr(e.message) }
  }
  if (!r) return <p className="text-sm text-slate-400">Cargando…</p>
  const filas = [['Trabajadores', 'trabajadores'], ['Horas-hombre', 'horas_hombre'], ['Accidentes mortales', 'mortales'], ['Accidentes leves', 'leves'], ['Accidentes incapacitantes', 'incapacitantes'], ['Días perdidos', 'dias_perdidos'], ['Índice de frecuencia', 'indice_frecuencia'], ['Índice de gravedad', 'indice_gravedad'], ['Índice de accidentabilidad', 'indice_accidentabilidad'], ['Incidentes', 'incidentes'], ['Incidentes peligrosos', 'incidentes_peligrosos'], ['Enfermedades ocupacionales', 'enfermedades'], ['Trabajadores con descanso médico', 'trabajadores_dm']]
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <input type="number" className="input-esynapse w-24" value={anio} onChange={(e) => setAnio(Number(e.target.value))} />
        <span className="text-xs text-slate-500">Índices según la R.M. 050-2013-TR (por millón de horas-hombre). Horas-hombre propuestas: trabajadores activos × días laborables × 8 (editables por mes).</span>
        <span className="ml-auto flex gap-2">
          <button className="btn-secondary" onClick={() => abrirPdf(api.sst.datosEstadisticasPdf(anio))}><FileText className="h-4 w-4" /> Datos del año</button>
          <button className="btn-secondary" onClick={() => abrirPdf(api.sst.estadisticasPdf(anio))}><FileText className="h-4 w-4" /> Registro de estadísticas</button>
        </span>
      </div>
      {r.pendientes_mtpe.length > 0 && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600">Pendientes de notificar al Ministerio de Trabajo: {r.pendientes_mtpe.join(', ')}</p>}
      <div className="card-esynapse overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"><th className="px-2 py-2">Indicador</th>{r.meses.map((m) => <th key={m.mes} className="px-1">{m.nombre.slice(0, 3)}</th>)}</tr></thead>
          <tbody>
            {filas.map(([n, k]) => (
              <tr key={k} className="border-b border-slate-100 dark:border-slate-800/60">
                <td className="whitespace-nowrap px-2 py-1 font-semibold">{n}</td>
                {r.meses.map((m) => <td key={m.mes} className={`px-1 ${m.futuro ? 'text-slate-300 dark:text-slate-600' : ''} ${k === 'horas_hombre' && !m.propuesto ? 'font-semibold text-esynapse-500' : ''}`}>{m.futuro ? '' : (m[k] ?? '—')}</td>)}
              </tr>
            ))}
            {puedeEditar && <tr><td className="px-2 py-1 text-[11px] text-slate-500 dark:text-slate-400">Ajustar datos del mes</td>{r.meses.map((m) => <td key={m.mes} className="px-1">{!m.futuro && <button className="text-[11px] text-esynapse-500 underline" onClick={() => { setErr(''); setMes({ mes: m.mes, trabajadores: m.trabajadores, dias_laborables: m.dias_laborables, horas_hombre: m.horas_hombre, trabajadores_dm: m.trabajadores_dm, dias_dm_calendario: m.dias_dm_calendario, dias_dm_laborales: m.dias_dm_laborales, observaciones: '' }) }}>editar</button>}</td>)}</tr>}
          </tbody>
        </table>
      </div>
      <Seccion titulo="Análisis del registro de estadísticas (resultados, causas de desviaciones, conclusiones)" extra={puedeEditar && <button className="btn-secondary !py-0.5 text-[11px]" onClick={() => { setErr(''); setInf({ periodo: '', resultados: '', causas_desviaciones: '', conclusiones: '' }) }}><Plus className="h-3.5 w-3.5" /> Nuevo análisis</button>}>
        {r.informes.length === 0 && <p className="text-slate-400">Sin análisis registrados para {anio}.</p>}
        {r.informes.map((i) => <div key={i.id} className="flex flex-wrap items-center gap-2 border-b border-slate-100 py-1 dark:border-slate-800/60"><strong>{i.periodo}</strong><span className="text-slate-500">{i.firma?.nombre} · {fechaHora(i.firma?.fecha)}</span><button className="ml-auto text-[11px] underline" onClick={() => abrirPdf(api.sst.estadisticasPdf(anio, i.id))}>Imprimir con este análisis</button></div>)}
      </Seccion>
      <Modal abierto={Boolean(mes)} titulo={mes ? `Datos de ${r.meses[mes.mes - 1].nombre} ${anio}` : ''} onCerrar={() => setMes(null)} ancho="max-w-xl">
        {mes && (
          <div className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-3">{[['trabajadores', 'Trabajadores'], ['dias_laborables', 'Días laborables'], ['horas_hombre', 'Horas-hombre']].map(([k, n]) => <div key={k}><label className={lbl}>{n}</label><input type="number" className={inp} value={mes[k]} onChange={(e) => setMes({ ...mes, [k]: e.target.value, ...(k !== 'horas_hombre' ? { horas_hombre: (Number(k === 'trabajadores' ? e.target.value : mes.trabajadores) || 0) * (Number(k === 'dias_laborables' ? e.target.value : mes.dias_laborables) || 0) * 8 } : {}) })} /></div>)}</div>
            <div className="grid gap-3 md:grid-cols-3">{[['trabajadores_dm', 'Trabajadores con descanso médico'], ['dias_dm_calendario', 'Días DM (calendario)'], ['dias_dm_laborales', 'Días DM (laborables)']].map(([k, n]) => <div key={k}><label className={lbl}>{n}</label><input type="number" className={inp} value={mes[k]} onChange={(e) => setMes({ ...mes, [k]: e.target.value })} /></div>)}</div>
            <div><label className={lbl}>Observaciones (horas extra, ausencias…)</label><input className={inp} value={mes.observaciones} onChange={(e) => setMes({ ...mes, observaciones: e.target.value })} /></div>
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setMes(null)}>Cancelar</button><button className="btn-primary" onClick={guardarMes}>Guardar</button></div>
          </div>
        )}
      </Modal>
      <Modal abierto={Boolean(inf)} titulo="Análisis del registro de estadísticas" onCerrar={() => setInf(null)} ancho="max-w-3xl">
        {inf && (
          <div className="space-y-3 text-sm">
            <div><label className={lbl}>Periodo analizado</label><input className={inp} placeholder={`Enero – Junio ${anio}`} value={inf.periodo} onChange={(e) => setInf({ ...inf, periodo: e.target.value })} /></div>
            {[['resultados', 'Resultados estadísticos (comparados con los objetivos de SST)'], ['causas_desviaciones', 'Análisis de las causas de las desviaciones'], ['conclusiones', 'Conclusiones y recomendaciones']].map(([k, n]) => <div key={k}><label className={lbl}>{n}</label><CampoAmpliable multilinea rows={3} value={inf[k]} onChange={(v) => setInf({ ...inf, [k]: v })} /></div>)}
            {err && <Aviso texto={err} />}
            <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={() => setInf(null)}>Cancelar</button><button className="btn-primary" disabled={!inf.periodo.trim() || !inf.resultados.trim()} onClick={guardarInforme}>Firmar y guardar</button></div>
          </div>
        )}
      </Modal>
    </div>
  )
}
