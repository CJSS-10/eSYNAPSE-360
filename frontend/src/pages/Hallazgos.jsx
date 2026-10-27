import { useCallback, useEffect, useState } from 'react'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import {
  Download, Lock, Pencil, Plus, Search, SearchX, Share2, Shuffle, Wrench,
} from 'lucide-react'
import Modal from '../components/Modal.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import SelectorProceso from '../components/SelectorProceso.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { fecha, hoy as hoyLocal } from '../lib/fecha.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import { useAbrirDesdeEnlace } from '../lib/enlaces.js'

const ES_NC = (t) => t === 'nc_mayor' || t === 'nc_menor'

const TIPOS = [
  ['nc_mayor', 'NC Mayor'], ['nc_menor', 'NC Menor'],
  ['observacion', 'Observación'], ['odm', 'Oportunidad de Mejora'],
]

const FUENTES = [
  ['auditoria_interna', 'Auditoría interna'], ['auditoria_externa', 'Auditoría externa'],
  ['inspeccion', 'Inspección'], ['queja', 'Queja'], ['seguimiento', 'Seguimiento de procesos'],
  ['indicador', 'Indicador'], ['riesgo', 'Riesgo materializado'], ['otro', 'Otro'],
]

const ESTADOS = [
  ['registrado', 'Registrado'], ['derivado', 'Derivado a riesgos y oportunidades'],
  ['en_tratamiento', 'En tratamiento'], ['cerrado', 'Cerrado'],
]

const COLOR_TIPO = {
  'NC Mayor': 'bg-red-500/15 text-red-600 dark:text-red-400',
  'NC Menor': 'bg-orange-500/15 text-orange-600 dark:text-orange-400',
  'Observación': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  'Oportunidad de Mejora': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
}

const COLOR_ESTADO = {
  'Registrado': 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
  'En análisis': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  'En tratamiento': 'bg-blue-500/15 text-blue-600 dark:text-blue-400',
  'Derivado a riesgos y oportunidades': 'bg-blue-500/15 text-blue-600 dark:text-blue-400',
  'Cerrado': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  'Reabierto': 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
}

const FORM_VACIO = {
  tipo: 'nc_menor', fuente: 'auditoria_interna', proceso: '', descripcion: '',
  requisito: '', lugar: '', fecha_deteccion: hoyLocal(),
}

export default function Hallazgos() {
  const { tienePermiso } = useAuth()
  const [items, setItems] = useState([])
  const [buscar, setBuscar] = useState('')
  const [tipo, setTipo] = useState('')
  const [estado, setEstado] = useState('')
  const [modalCrear, setModalCrear] = useState(false)
  const [detalle, setDetalle] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [evidencia, setEvidencia] = useState(null)
  const [editandoId, setEditandoId] = useState(null)   // registro en corrección (etapa abierta)
  const [reclas, setReclas] = useState(null)            // { tipo, motivo } al reclasificar
  const [sacs, setSacs] = useState(null)                // solicitudes abiertas para sumar la NC
  const [error, setError] = useState('')

  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const params = new URLSearchParams()
    if (buscar) params.set('buscar', buscar)
    if (tipo) params.set('tipo', tipo)
    if (estado) params.set('estado', estado)
    const data = await ultima(api.hallazgos.listar(`?${params}`))
    setItems(data.results ?? data)
  }, [buscar, tipo, estado])

  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
  }, [])

  const abrirDetalle = async (id) => {
    setError(''); setReclas(null); setSacs(null)
    setDetalle(await api.hallazgos.detalle(id))
  }

  const refrescar = async () => {
    await cargar()
    if (detalle) setDetalle(await api.hallazgos.detalle(detalle.id))
    setReclas(null); setSacs(null)
  }

  const accion = async (fn) => {
    setError('')
    try { await fn(); await refrescar() } catch (e) { setError(e.message) }
  }

  const generarSac = async () => { await api.hallazgos.generarSac(detalle.id) }

  const abrirEdicion = () => {
    setForm({
      tipo: detalle.tipo, fuente: detalle.fuente, proceso: detalle.proceso, descripcion: detalle.descripcion,
      requisito: detalle.requisito || '', lugar: detalle.lugar || '', fecha_deteccion: detalle.fecha_deteccion,
    })
    setEvidencia(null); setError(''); setEditandoId(detalle.id); setModalCrear(true)
  }

  const crear = async (e) => {
    e.preventDefault()
    setError('')
    if (editandoId) {
      try {
        const { tipo: _t, ...datos } = form   // el tipo se cambia solo reclasificando
        await api.hallazgos.editar(editandoId, datos)
        setModalCrear(false); setEditandoId(null)
        await refrescar()
      } catch (e2) { setError(e2.message) }
      return
    }
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => { if (v !== '') fd.append(k, v) })
      if (evidencia) fd.append('evidencia', evidencia)
      await api.hallazgos.crear(fd)
      setModalCrear(false)
      setForm(FORM_VACIO)
      setEvidencia(null)
      await cargar()
    } catch (e2) { setError(e2.message) }
  }

  const campo = (etiqueta, clave, props = {}) => (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">{etiqueta}</label>
      <input className="input-esynapse" value={form[clave]}
        onChange={(e) => setForm({ ...form, [clave]: e.target.value })} {...props} />
    </div>
  )

  const selector = (etiqueta, clave, opciones, props = {}) => (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">{etiqueta}</label>
      <select className="input-esynapse" value={form[clave]}
        onChange={(e) => setForm({ ...form, [clave]: e.target.value })} {...props}>
        {opciones.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
      </select>
    </div>
  )

  useAbrirDesdeEnlace(abrirDetalle)   // enlace directo ?abrir=<id> (búsqueda, Mis tareas, campana)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <TituloModulo seccion="Sistema de gestión" titulo="Hallazgos" descripcion="Registro único de no conformidades, observaciones y oportunidades de mejora, vengan de donde vengan." />
        </div>
        {tienePermiso('hallazgos', 'crear') && (
          <button onClick={() => { setForm(FORM_VACIO); setEvidencia(null); setError(''); setEditandoId(null); setModalCrear(true) }} className="btn-primary">
            <Plus className="h-4 w-4" /> Registrar hallazgo
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input-esynapse w-64 pl-9" placeholder="Buscar código, descripción, proceso…"
            value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <select className="input-esynapse w-44" value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Todos los tipos</option>
          {TIPOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
        <select className="input-esynapse w-44" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
      </div>

      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3 text-center">Tipo</th>
              <th className="px-4 py-3">Fuente</th>
              <th className="px-4 py-3">Proceso</th>
              <th className="px-4 py-3 text-right">Detección</th>
              <th className="px-4 py-3">Responsable</th>
              <th className="px-4 py-3 text-center">Estado</th>
              <th className="px-4 py-3 text-center">Tratamiento</th>
            </tr>
          </thead>
          <tbody>
            {items.map((h) => (
              <tr key={h.id} onClick={() => abrirDetalle(h.id)}
                className="cursor-pointer border-b border-slate-100 transition last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="whitespace-nowrap px-4 py-3 font-mono text-xs font-medium">{h.codigo}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_TIPO[h.tipo_display] || 'bg-slate-500/15'}`}>
                    {h.tipo_display}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{h.fuente_display}</td>
                <td className="px-4 py-3">{h.proceso}</td>
                <td className="whitespace-nowrap px-4 py-3 text-xs text-right">{fecha(h.fecha_deteccion)}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{h.responsable_nombre || (h.is_active && h.estado_display !== 'Cerrado' ? <span className="whitespace-nowrap rounded bg-amber-500/15 px-1.5 py-0.5 text-[11px] font-medium text-amber-600 dark:text-amber-400">Por designar</span> : '—')}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_ESTADO[h.estado_display] || 'bg-slate-500/15'}`}>
                    {h.estado_display}
                  </span>
                  {!h.is_active && (
                    <span className="ml-1 rounded bg-red-500/15 px-1.5 py-0.5 text-[11px] font-medium text-red-500">Inactivo</span>
                  )}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-xs text-center">
                  {h.sac_codigo
                    ? <span className="font-mono">{h.sac_codigo}</span>
                    : ES_NC(h.tipo)
                      ? <span className="text-red-500">{h.estado === 'cerrado' ? '—' : 'SAC pendiente'}</span>
                      : <span className="text-slate-400">Riesgos y oport.</span>}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-400">Sin hallazgos — buena señal, o falta registrarlos</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal registrar */}
      <Modal abierto={modalCrear} titulo={editandoId ? 'Corregir registro del hallazgo' : 'Registrar hallazgo'}
        onCerrar={() => { setModalCrear(false); setEditandoId(null) }}>
        <form onSubmit={crear} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {selector('Tipo', 'tipo', TIPOS, { disabled: Boolean(editandoId), title: editandoId ? 'El tipo se cambia con «Reclasificar»' : undefined })}
            {selector('Fuente', 'fuente', FUENTES)}
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Proceso afectado</label>
            <SelectorProceso required value={form.proceso} onChange={(v) => setForm({ ...form, proceso: v })} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Descripción del hallazgo</label>
            <textarea className="input-esynapse" rows={3} required value={form.descripcion}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
              placeholder="Qué se detectó, dónde, cuándo y evidencia objetiva" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            {campo('Requisito incumplido', 'requisito', { placeholder: 'ISO 17025 7.8.2' })}
            {campo('Lugar', 'lugar', { placeholder: 'Lab. Presión, 2° piso' })}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {campo('Fecha de detección', 'fecha_deteccion', { type: 'date', required: true })}
            <p className="self-end pb-2 text-[11px] text-slate-500">El responsable del tratamiento se designa al evaluar la solicitud de acción correctiva (o en Riesgos y oportunidades).</p>
          </div>
          {!editandoId && (
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Evidencia (opcional)</label>
            <input type="file" onChange={(e) => setEvidencia(e.target.files[0])}
              className="block w-full text-xs text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-esynapse-600 file:px-3 file:py-2 file:text-xs file:font-medium file:text-white hover:file:bg-esynapse-500" />
          </div>
          )}
          {!editandoId && (ES_NC(form.tipo) ? (
            <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">
              Toda No Conformidad se trata en una Solicitud de Acción Correctiva: después de registrarla, genérela o súmela a una solicitud abierta del mismo problema.
            </p>
          ) : (
            <p className="rounded-lg bg-blue-500/10 px-3 py-2 text-xs text-blue-600 dark:text-blue-400">
              Las observaciones y oportunidades de mejora no se tratan aquí: quedan derivadas a Riesgos y Oportunidades.
            </p>
          ))}
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalCrear(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">{editandoId ? 'Guardar corrección' : 'Registrar'}</button>
          </div>
        </form>
      </Modal>

      {/* Modal detalle */}
      <Modal abierto={Boolean(detalle) && !modalCrear} titulo={detalle ? `${detalle.codigo} — ${detalle.tipo_display}` : ''}
        onCerrar={() => setDetalle(null)} panel ancho="max-w-2xl">
        {detalle && (
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 dark:text-slate-400">
              <p><strong className="text-slate-700 dark:text-slate-200">Estado:</strong>{' '}
                <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_ESTADO[detalle.estado_display]}`}>{detalle.estado_display}</span>
              </p>
              <p><strong className="text-slate-700 dark:text-slate-200">Fuente:</strong> {detalle.fuente_display}</p>
              <p><strong className="text-slate-700 dark:text-slate-200">Proceso:</strong> {detalle.proceso}</p>
              <p><strong className="text-slate-700 dark:text-slate-200">Detección:</strong> {fecha(detalle.fecha_deteccion)}{detalle.lugar ? ` — ${detalle.lugar}` : ''}</p>
              {detalle.auditoria_codigo && <p><strong className="text-slate-700 dark:text-slate-200">Auditoría:</strong> {detalle.auditoria_codigo}</p>}
              {detalle.requisito && <p><strong className="text-slate-700 dark:text-slate-200">Requisito:</strong> {detalle.requisito}</p>}
              <p><strong className="text-slate-700 dark:text-slate-200">Responsable:</strong> {detalle.responsable_nombre || (detalle.tratamiento === 'riesgos_oportunidades' ? 'Por designar (en Riesgos y oportunidades)' : 'Por designar (al evaluar la solicitud de acción correctiva)')}</p>
              <p><strong className="text-slate-700 dark:text-slate-200">Registró:</strong> {detalle.registrado_por || '—'}</p>
            </div>

            {/* Tratamiento según el procedimiento: NC → solicitud de acción correctiva;
                observación / oportunidad de mejora → Riesgos y Oportunidades. */}
            {ES_NC(detalle.tipo) ? (
              <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-xs">
                {detalle.sac ? (
                  <p className="text-slate-600 dark:text-slate-300">
                    <Wrench className="mr-1 inline h-3.5 w-3.5 text-red-500" />
                    <strong className="text-red-600 dark:text-red-400">Se trata en:</strong>{' '}
                    <span className="font-mono font-medium">{detalle.sac.codigo}</span>
                    <span className="ml-1 text-slate-400">[{detalle.sac.estado_display}]</span>
                    {!detalle.sac.es_origen && <span className="ml-1 text-slate-500">· sumada como nueva ocurrencia</span>}
                    <span className="ml-2 text-slate-500 dark:text-slate-400">— se gestiona en Acciones Correctivas; al cerrarse la solicitud, este hallazgo se cierra.</span>
                  </p>
                ) : detalle.motivo_no_derivar ? (
                  <p className="text-slate-600 dark:text-slate-300">{detalle.motivo_no_derivar}</p>
                ) : detalle.puede_generar_sac ? (
                  <p className="text-slate-600 dark:text-slate-300">
                    Pendiente de derivar: esta No Conformidad se trata en una Solicitud de Acción Correctiva (al final de la ficha).
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="rounded-lg border border-blue-500/30 bg-blue-500/5 p-3 text-xs text-slate-600 dark:text-slate-300">
                <Share2 className="mr-1 inline h-3.5 w-3.5 text-blue-500" />
                <strong className="text-blue-600 dark:text-blue-400">Derivado a Riesgos y Oportunidades.</strong>{' '}
                Las observaciones y oportunidades de mejora se tratan según el procedimiento de identificación de riesgos y oportunidades; quedarán conectadas cuando ese módulo esté disponible.
              </div>
            )}

            {/* Registro: se corrige mientras su etapa esté abierta; el tipo, solo reclasificando con motivo */}
            {(detalle.etapas_abiertas || []).includes('registro') ? (
              tienePermiso('hallazgos', 'editar') && (
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-2">
                    <button onClick={abrirEdicion} className="btn-secondary !py-1.5 text-xs"><Pencil className="h-3.5 w-3.5" /> Corregir registro</button>
                  </div>
                </div>
              )
            ) : detalle.registro_cerrado_motivo && (
              <p className="flex items-start gap-1.5 text-[11px] text-slate-400"><Lock className="mt-0.5 h-3 w-3 shrink-0" /> Solo lectura: {detalle.registro_cerrado_motivo}</p>
            )}

            {(detalle.reclasificaciones || []).length > 0 && (
              <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 p-3 text-xs">
                <p className="mb-1 font-semibold text-violet-600 dark:text-violet-400">Reclasificaciones</p>
                {detalle.reclasificaciones.map((r, i) => (
                  <p key={i} className="text-slate-600 dark:text-slate-300">
                    {fecha(r.fecha)} · {r.de} → {r.a} ({r.codigo_anterior}) · {r.usuario}: {r.motivo}
                  </p>
                ))}
              </div>
            )}

            <div className="rounded-lg bg-slate-100 p-3 text-xs dark:bg-slate-800">
              <p className="mb-1 font-semibold text-slate-700 dark:text-slate-200">Descripción</p>
              <p className="text-slate-600 dark:text-slate-300">{detalle.descripcion}</p>
            </div>

            {detalle.analisis && (
              <div className="rounded-lg bg-amber-500/10 p-3 text-xs">
                <p className="mb-1 font-semibold text-amber-600 dark:text-amber-400">Análisis (registro anterior)</p>
                <p className="text-slate-600 dark:text-slate-300">{detalle.analisis}</p>
              </div>
            )}
            {detalle.correccion && (
              <div className="rounded-lg bg-esynapse-600/10 p-3 text-xs">
                <p className="mb-1 font-semibold text-esynapse-600 dark:text-esynapse-300">Corrección inmediata (registro anterior)</p>
                <p className="text-slate-600 dark:text-slate-300">{detalle.correccion}</p>
              </div>
            )}
            {detalle.comentarios_cierre && (
              <div className="rounded-lg bg-emerald-500/10 p-3 text-xs">
                <p className="mb-1 font-semibold text-emerald-600 dark:text-emerald-400">
                  Cierre {detalle.cerrado_por_nombre ? `— verificado por ${detalle.cerrado_por_nombre}` : ''}
                </p>
                <p className="whitespace-pre-line text-slate-600 dark:text-slate-300">{detalle.comentarios_cierre}</p>
              </div>
            )}

            {detalle.evidencia_url && (
              <a href={detalle.evidencia_url} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-2 text-xs text-esynapse-500 hover:underline">
                <Download className="h-3.5 w-3.5" /> Descargar evidencia
              </a>
            )}

            {/* Al final: reclasificación y derivación de la No Conformidad (cierra el registro) */}
            {(detalle.etapas_abiertas || []).includes('registro') && tienePermiso('hallazgos', 'editar') && reclas && (
              <div className="grid grid-cols-3 gap-2 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
                <select className="input-esynapse text-xs" value={reclas.tipo} onChange={(e) => setReclas({ ...reclas, tipo: e.target.value })}>
                  <option value="">— Nuevo tipo —</option>
                  {TIPOS.filter(([v]) => v !== detalle.tipo).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                </select>
                <input className="input-esynapse col-span-2 text-xs" placeholder="Motivo de la reclasificación (obligatorio)"
                  value={reclas.motivo} onChange={(e) => setReclas({ ...reclas, motivo: e.target.value })} />
                <button disabled={!reclas.tipo || !reclas.motivo.trim()}
                  onClick={() => accion(() => api.hallazgos.reclasificar(detalle.id, reclas.tipo, reclas.motivo))}
                  className="btn-primary col-span-3 !py-1.5 text-xs">Confirmar reclasificación</button>
              </div>
            )}
            {ES_NC(detalle.tipo) && !detalle.sac && detalle.puede_generar_sac && sacs && (
              <div className="max-h-56 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-700">
                <p className="text-[11px] font-semibold text-slate-500">Solicitudes abiertas</p>
                {sacs.length === 0 && <p className="text-slate-400">No hay solicitudes abiertas.</p>}
                {sacs.map((s) => (
                  <div key={s.id} className="flex items-start justify-between gap-2 border-b border-slate-100 pb-1 last:border-0 dark:border-slate-800">
                    <div>
                      <span className="font-mono font-medium">{s.codigo}</span>
                      <span className="ml-1 text-slate-400">[{s.estado_display}]</span>
                      {s.similar && <span className="ml-1 rounded bg-amber-500/15 px-1 text-[11px] text-amber-600 dark:text-amber-400">posible mismo problema</span>}
                      <p className="text-slate-500 dark:text-slate-400">{s.requisito ? `${s.requisito} · ` : ''}{s.descripcion}</p>
                    </div>
                    <button onClick={() => accion(() => api.hallazgos.vincularSac(detalle.id, s.id))} className="btn-secondary shrink-0 !px-2 !py-1 text-[11px]">Sumar</button>
                  </div>
                ))}
              </div>
            )}
            {(() => {
              const registroAbierto = (detalle.etapas_abiertas || []).includes('registro') && tienePermiso('hallazgos', 'editar')
              const botonReclas = registroAbierto ? [{ texto: reclas ? 'Cancelar reclasificación' : 'Reclasificar', secundario: true, accion: () => setReclas(reclas ? null : { tipo: '', motivo: '' }) }] : []
              if (ES_NC(detalle.tipo) && !detalle.sac && detalle.puede_generar_sac) {
                return (
                  <BarraEtapa titulo="Cerrar el registro: derivar la No Conformidad"
                    nota="Se trata en una Solicitud de Acción Correctiva. Si ya hay una abierta por el mismo problema, súmela como nueva ocurrencia. Después, el registro queda de solo lectura."
                    botones={[
                      ...(tienePermiso('hallazgos', 'crear') ? [{ texto: 'Generar SAC nueva', accion: () => accion(generarSac) }] : []),
                      ...(tienePermiso('hallazgos', 'editar') ? [{ texto: sacs ? 'Ocultar solicitudes abiertas' : 'Sumar a SAC abierta', secundario: true,
                        accion: async () => { if (sacs) { setSacs(null); return } setError(''); try { setSacs(await api.hallazgos.sacAbiertas(detalle.id)) } catch (e) { setError(e.message) } } }] : []),
                      ...botonReclas,
                    ]} />
                )
              }
              return botonReclas.length > 0 && (
                <div className="flex justify-end">
                  <button onClick={botonReclas[0].accion} className="btn-secondary !py-1.5 text-xs"><Shuffle className="h-3.5 w-3.5" /> {botonReclas[0].texto}</button>
                </div>
              )
            })()}

            {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          </div>
        )}
      </Modal>
    </div>
  )
}
