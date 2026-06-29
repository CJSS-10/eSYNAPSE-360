import { useCallback, useEffect, useState } from 'react'
import {
  CheckCircle2, Download, Plus, RotateCcw, Search, SearchX, Send, Wrench,
} from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'

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
  ['registrado', 'Registrado'], ['en_analisis', 'En análisis'],
  ['en_tratamiento', 'En tratamiento'], ['cerrado', 'Cerrado'], ['reabierto', 'Reabierto'],
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
  'En tratamiento': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'Cerrado': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  'Reabierto': 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
}

const FORM_VACIO = {
  tipo: 'nc_menor', fuente: 'auditoria_interna', proceso: '', descripcion: '',
  requisito: '', lugar: '', fecha_deteccion: new Date().toISOString().slice(0, 10),
  responsable: '',
}

export default function Hallazgos() {
  const { tienePermiso } = useAuth()
  const [items, setItems] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [buscar, setBuscar] = useState('')
  const [tipo, setTipo] = useState('')
  const [estado, setEstado] = useState('')
  const [modalCrear, setModalCrear] = useState(false)
  const [detalle, setDetalle] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [evidencia, setEvidencia] = useState(null)
  const [texto, setTexto] = useState('')      // análisis / corrección / comentarios según estado
  const [error, setError] = useState('')

  const cargar = useCallback(async () => {
    const params = new URLSearchParams()
    if (buscar) params.set('buscar', buscar)
    if (tipo) params.set('tipo', tipo)
    if (estado) params.set('estado', estado)
    const data = await api.hallazgos.listar(`?${params}`)
    setItems(data.results ?? data)
  }, [buscar, tipo, estado])

  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
    api.usuarios.listar().then((d) => setUsuarios(d.results ?? d)).catch(() => {})
  }, [])

  const abrirDetalle = async (id) => {
    setError(''); setTexto('')
    setDetalle(await api.hallazgos.detalle(id))
  }

  const refrescar = async () => {
    await cargar()
    if (detalle) setDetalle(await api.hallazgos.detalle(detalle.id))
    setTexto('')
  }

  const accion = async (fn) => {
    setError('')
    try { await fn(); await refrescar() } catch (e) { setError(e.message) }
  }

  const generarSac = async () => { await api.hallazgos.generarSac(detalle.id) }

  const crear = async (e) => {
    e.preventDefault()
    setError('')
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SearchX className="h-6 w-6 text-esynapse-500" />
          <h1 className="text-2xl font-bold">Hallazgos</h1>
        </div>
        {tienePermiso('hallazgos', 'crear') && (
          <button onClick={() => { setForm(FORM_VACIO); setEvidencia(null); setError(''); setModalCrear(true) }} className="btn-primary">
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
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3">Tipo</th>
              <th className="px-4 py-3">Fuente</th>
              <th className="px-4 py-3">Proceso</th>
              <th className="px-4 py-3">Detección</th>
              <th className="px-4 py-3">Responsable</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">AC</th>
            </tr>
          </thead>
          <tbody>
            {items.map((h) => (
              <tr key={h.id} onClick={() => abrirDetalle(h.id)}
                className="cursor-pointer border-b border-slate-100 transition last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 font-mono text-xs font-medium">{h.codigo}</td>
                <td className="px-4 py-3">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_TIPO[h.tipo_display] || 'bg-slate-500/15'}`}>
                    {h.tipo_display}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{h.fuente_display}</td>
                <td className="px-4 py-3">{h.proceso}</td>
                <td className="px-4 py-3 text-xs">{h.fecha_deteccion}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{h.responsable_nombre || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_ESTADO[h.estado_display] || 'bg-slate-500/15'}`}>
                    {h.estado_display}
                  </span>
                  {!h.is_active && (
                    <span className="ml-1 rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] font-medium text-red-500">Inactivo</span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs">{h.requiere_ac ? '⚠ Sí' : '—'}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-400">Sin hallazgos — buena señal, o falta registrarlos</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal registrar */}
      <Modal abierto={modalCrear} titulo="Registrar hallazgo" onCerrar={() => setModalCrear(false)}>
        <form onSubmit={crear} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {selector('Tipo', 'tipo', TIPOS)}
            {selector('Fuente', 'fuente', FUENTES)}
          </div>
          {campo('Proceso afectado', 'proceso', { required: true, placeholder: 'Ej: Laboratorio Presión' })}
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
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Responsable del tratamiento</label>
              <select className="input-esynapse" value={form.responsable}
                onChange={(e) => setForm({ ...form, responsable: e.target.value })}>
                <option value="">— Por asignar —</option>
                {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Evidencia (opcional)</label>
            <input type="file" onChange={(e) => setEvidencia(e.target.files[0])}
              className="block w-full text-xs text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-esynapse-600 file:px-3 file:py-2 file:text-xs file:font-medium file:text-white hover:file:bg-esynapse-500" />
          </div>
          {form.tipo === 'nc_mayor' && (
            <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">
              Las NC Mayores requieren Acción Correctiva obligatoria (se vinculará en el módulo M9).
            </p>
          )}
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalCrear(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">Registrar</button>
          </div>
        </form>
      </Modal>

      {/* Modal detalle */}
      <Modal abierto={Boolean(detalle)} titulo={detalle ? `${detalle.codigo} — ${detalle.tipo_display}` : ''}
        onCerrar={() => setDetalle(null)} ancho="max-w-2xl">
        {detalle && (
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 dark:text-slate-400">
              <p><strong className="text-slate-700 dark:text-slate-200">Estado:</strong>{' '}
                <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_ESTADO[detalle.estado_display]}`}>{detalle.estado_display}</span>
              </p>
              <p><strong className="text-slate-700 dark:text-slate-200">Fuente:</strong> {detalle.fuente_display}</p>
              <p><strong className="text-slate-700 dark:text-slate-200">Proceso:</strong> {detalle.proceso}</p>
              <p><strong className="text-slate-700 dark:text-slate-200">Detección:</strong> {detalle.fecha_deteccion}{detalle.lugar ? ` — ${detalle.lugar}` : ''}</p>
              {detalle.requisito && <p><strong className="text-slate-700 dark:text-slate-200">Requisito:</strong> {detalle.requisito}</p>}
              <p><strong className="text-slate-700 dark:text-slate-200">Responsable:</strong> {detalle.responsable_nombre || 'Por asignar'}</p>
              <p><strong className="text-slate-700 dark:text-slate-200">Registró:</strong> {detalle.registrado_por || '—'}</p>
              {detalle.requiere_ac && !detalle.sac && (
                <p className="col-span-2 text-red-500"><strong>⚠ Requiere Acción Correctiva</strong></p>
              )}
            </div>

            {/* Derivación a Acciones Correctivas (M9) — solo NC */}
            {(detalle.sac || detalle.puede_generar_sac) && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-xs">
                {detalle.sac ? (
                  <p className="text-slate-600 dark:text-slate-300">
                    <Wrench className="mr-1 inline h-3.5 w-3.5 text-red-500" />
                    <strong className="text-red-600 dark:text-red-400">Acción Correctiva:</strong>{' '}
                    <span className="font-mono font-medium">{detalle.sac.codigo}</span>
                    <span className="ml-1 text-slate-400">[{detalle.sac.estado_display}]</span>
                    <span className="ml-2 text-slate-500 dark:text-slate-400">— gestiónala en el módulo Acciones Correctivas.</span>
                  </p>
                ) : (
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-slate-600 dark:text-slate-300">Esta No Conformidad debe tratarse con una Solicitud de Acción Correctiva.</span>
                    {tienePermiso('hallazgos', 'crear') && (
                      <button onClick={() => accion(generarSac)} className="btn-primary shrink-0 !py-1.5 text-xs">
                        <Wrench className="h-3.5 w-3.5" /> Generar SAC
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="rounded-lg bg-slate-100 p-3 text-xs dark:bg-slate-800">
              <p className="mb-1 font-semibold text-slate-700 dark:text-slate-200">Descripción</p>
              <p className="text-slate-600 dark:text-slate-300">{detalle.descripcion}</p>
            </div>

            {detalle.analisis && (
              <div className="rounded-lg bg-amber-500/10 p-3 text-xs">
                <p className="mb-1 font-semibold text-amber-600 dark:text-amber-400">Análisis</p>
                <p className="text-slate-600 dark:text-slate-300">{detalle.analisis}</p>
              </div>
            )}
            {detalle.correccion && (
              <div className="rounded-lg bg-esynapse-600/10 p-3 text-xs">
                <p className="mb-1 font-semibold text-esynapse-600 dark:text-esynapse-300">Corrección inmediata</p>
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

            {/* Etapas de tratamiento: SOLO Observación y OdM se tratan aquí.
                Las NC (Mayor/Menor) se tratan en su Acción Correctiva (M9). */}
            {!['nc_mayor', 'nc_menor'].includes(detalle.tipo) && (
            <div className="space-y-2">
              {(detalle.estado === 'registrado' || detalle.estado === 'reabierto') && tienePermiso('hallazgos', 'editar') && (
                <>
                  <textarea className="input-esynapse" rows={2} placeholder="Análisis del hallazgo (opcional en este paso)"
                    value={texto} onChange={(e) => setTexto(e.target.value)} />
                  <button onClick={() => accion(() => api.hallazgos.iniciarAnalisis(detalle.id, texto))} className="btn-primary !py-1.5 text-xs">
                    <Send className="h-3.5 w-3.5" /> Iniciar análisis
                  </button>
                </>
              )}
              {detalle.estado === 'en_analisis' && tienePermiso('hallazgos', 'editar') && (
                <>
                  <textarea className="input-esynapse" rows={2} placeholder="Corrección inmediata aplicada"
                    value={texto} onChange={(e) => setTexto(e.target.value)} />
                  <button onClick={() => accion(() => api.hallazgos.registrarTratamiento(detalle.id, { correccion: texto }))} className="btn-primary !py-1.5 text-xs">
                    <Wrench className="h-3.5 w-3.5" /> Registrar tratamiento
                  </button>
                </>
              )}
              {detalle.estado === 'en_tratamiento' && tienePermiso('hallazgos', 'aprobar') && (
                <>
                  <textarea className="input-esynapse" rows={2} placeholder="Comentarios de verificación del cierre (obligatorio)"
                    value={texto} onChange={(e) => setTexto(e.target.value)} />
                  <button onClick={() => accion(() => api.hallazgos.cerrar(detalle.id, texto))} className="btn-primary !py-1.5 text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Verificar y cerrar
                  </button>
                </>
              )}
              {detalle.estado === 'cerrado' && tienePermiso('hallazgos', 'aprobar') && (
                <>
                  <textarea className="input-esynapse" rows={2} placeholder="Justificación de la reapertura (obligatorio)"
                    value={texto} onChange={(e) => setTexto(e.target.value)} />
                  <button onClick={() => accion(() => api.hallazgos.reabrir(detalle.id, texto))} className="btn-secondary !py-1.5 text-xs">
                    <RotateCcw className="h-3.5 w-3.5" /> Reabrir hallazgo
                  </button>
                </>
              )}
            </div>
            )}

            {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          </div>
        )}
      </Modal>
    </div>
  )
}
