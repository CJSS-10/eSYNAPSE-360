import { useCallback, useEffect, useState } from 'react'
import {
  ClipboardList, Plus, Search, CheckCircle2, XCircle, Users, FileText, AlertTriangle,
} from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'

const NORMAS = [
  ['iso_9001', 'ISO 9001'], ['iso_14001', 'ISO 14001'],
  ['iso_45001', 'ISO 45001 / Ley 29783'], ['iso_17025', 'NTP ISO/IEC 17025'],
]
const CHIP_NORMA = {
  iso_9001: 'border-esynapse-500 bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  iso_14001: 'border-emerald-500 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  iso_45001: 'border-red-500 bg-red-500/15 text-red-600 dark:text-red-400',
  iso_17025: 'border-amber-500 bg-amber-500/15 text-amber-600 dark:text-amber-400',
}
const COLOR_NORMA = {
  'ISO 9001': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'ISO 14001': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  'ISO 45001 / Ley 29783': 'bg-red-500/15 text-red-600 dark:text-red-400',
  'NTP ISO/IEC 17025': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
}
const MODALIDADES = [['presencial', 'Presencial'], ['remota', 'Remota'], ['hibrido', 'Híbrido']]
const ESTADOS = [
  ['programada', 'Programada'], ['planificada', 'Planificada'], ['en_ejecucion', 'En ejecución'],
  ['en_informe', 'En informe'], ['cerrada', 'Cerrada'],
]
const COLOR_ESTADO = {
  'Programada': 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
  'Planificada': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  'En ejecución': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'En informe': 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
  'Cerrada': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
}
const PASOS = ['programada', 'planificada', 'en_ejecucion', 'en_informe', 'cerrada']
const NOMBRE_PASO = ['Programada', 'Planificada', 'Ejecución', 'Informe', 'Cerrada']
const ROLES = [['lider', 'Auditor líder'], ['auditor', 'Auditor'], ['experto', 'Experto técnico'], ['observador', 'Observador']]
const TIPOS_HALLAZGO = [['nc_mayor', 'NC Mayor'], ['nc_menor', 'NC Menor'], ['observacion', 'Observación'], ['odm', 'Oportunidad de Mejora']]
const RESULTADOS = [['pendiente', '—'], ['cumple', 'Cumple'], ['no_cumple', 'No cumple'], ['na', 'N/A'], ['observa', 'Observa']]
const COLOR_RESULTADO = {
  cumple: 'text-emerald-600 dark:text-emerald-400',
  no_cumple: 'text-red-600 dark:text-red-400',
  observa: 'text-amber-600 dark:text-amber-400',
  na: 'text-slate-400',
  pendiente: 'text-slate-400',
}

const FORM_VACIO = { programa: '', tipo: 'programada', normas: [], areas_procesos: '', modalidad: 'presencial', mes_programado: '' }

export default function Auditorias() {
  const { tienePermiso } = useAuth()
  const [items, setItems] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [programas, setProgramas] = useState([])
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('')
  const [modalCrear, setModalCrear] = useState(false)
  const [modalPrograma, setModalPrograma] = useState(false)
  const [anioNuevo, setAnioNuevo] = useState(new Date().getFullYear())
  const [detalle, setDetalle] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [error, setError] = useState('')
  // edición de datos generales
  const [gen, setGen] = useState({})
  const [equipoForm, setEquipoForm] = useState({ usuario: '', nombre_externo: '', rol: 'auditor', cargo: '' })
  const [hallForm, setHallForm] = useState({ tipo: 'nc_menor', proceso: '', requisito: '', descripcion: '' })
  const [informe, setInforme] = useState({ fortalezas: '', debilidades: '', conclusiones: '' })
  const [listaAbierta, setListaAbierta] = useState(null)
  const [actaForm, setActaForm] = useState({ tipo: 'apertura', contenido: '' })

  const cargar = useCallback(async () => {
    const p = new URLSearchParams()
    if (buscar) p.set('buscar', buscar)
    if (estado) p.set('estado', estado)
    const d = await api.auditorias.listar(`?${p}`)
    setItems(d.results ?? d)
  }, [buscar, estado])

  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
    api.usuarios.listar().then((d) => setUsuarios(d.results ?? d)).catch(() => {})
    api.programasAuditoria.listar().then((d) => setProgramas(d.results ?? d)).catch(() => {})
  }, [])

  const abrir = async (id) => {
    setError('')
    const d = await api.auditorias.detalle(id)
    setDetalle(d)
    setGen({
      objetivo: d.objetivo || '', alcance: d.alcance || '', criterios: d.criterios || '',
      documentos_referencia: d.documentos_referencia || '', auditor_lider: d.auditor_lider || '',
      modalidad: d.modalidad || 'presencial',
    })
    setInforme({ fortalezas: d.fortalezas || '', debilidades: d.debilidades || '', conclusiones: d.conclusiones || '' })
    setEquipoForm({ usuario: '', nombre_externo: '', rol: 'auditor', cargo: '' })
    setHallForm({ tipo: 'nc_menor', proceso: '', requisito: '', descripcion: '' })
    setActaForm({ tipo: 'apertura', contenido: '' })
    setListaAbierta(null)
  }

  const refrescar = async () => { await cargar(); if (detalle) setDetalle(await api.auditorias.detalle(detalle.id)) }
  const accion = async (fn) => { setError(''); try { await fn(); await refrescar() } catch (e) { setError(e.message) } }

  const crearPrograma = async () => {
    setError('')
    try {
      await api.programasAuditoria.crear({ anio: Number(anioNuevo) })
      setModalPrograma(false)
      setProgramas((await api.programasAuditoria.listar()).results ?? [])
    } catch (e) { setError(e.message) }
  }

  const crear = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const datos = { ...form, normas_aplicables: form.normas }
      delete datos.normas
      if (!datos.programa) delete datos.programa
      if (!datos.mes_programado) delete datos.mes_programado
      await api.auditorias.crear(datos)
      setModalCrear(false); setForm(FORM_VACIO); await cargar()
    } catch (e2) { setError(e2.message) }
  }

  const guardarGenerales = async () => {
    const datos = { ...gen }
    if (!datos.auditor_lider) datos.auditor_lider = null
    await api.auditorias.actualizar(detalle.id, datos)
  }

  const paso = (d) => PASOS.indexOf(d?.estado)
  const puedeEditar = tienePermiso('auditorias', 'editar')
  const puedeAprobar = tienePermiso('auditorias', 'aprobar')
  const cerrada = detalle?.estado === 'cerrada'

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-6 w-6 text-esynapse-500" />
          <h1 className="text-2xl font-bold">Auditorías Internas</h1>
        </div>
        <div className="flex gap-2">
          {tienePermiso('auditorias', 'crear') && (
            <button onClick={() => { setAnioNuevo(new Date().getFullYear()); setError(''); setModalPrograma(true) }} className="btn-secondary">
              <Plus className="h-4 w-4" /> Programa anual
            </button>
          )}
          {tienePermiso('auditorias', 'crear') && (
            <button onClick={() => { setForm(FORM_VACIO); setError(''); setModalCrear(true) }} className="btn-primary">
              <Plus className="h-4 w-4" /> Nueva auditoría
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input-esynapse w-64 pl-9" placeholder="Buscar código, área, objetivo…"
            value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <select className="input-esynapse w-52" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
      </div>

      <div className="card-esynapse overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3">Normas</th>
              <th className="px-4 py-3">Áreas / procesos</th>
              <th className="px-4 py-3">Modalidad</th>
              <th className="px-4 py-3">Líder</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Hallazgos</th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id} onClick={() => abrir(a.id)}
                className="cursor-pointer border-b border-slate-100 transition last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 font-mono text-xs font-medium">{a.codigo}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {(a.normas_display || []).map((n) => (
                      <span key={n} className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_NORMA[n] || 'bg-slate-200 text-slate-600'}`}>{n}</span>
                    ))}
                  </div>
                </td>
                <td className="max-w-xs truncate px-4 py-3" title={a.areas_procesos}>{a.areas_procesos || '—'}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{a.modalidad_display}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{a.auditor_lider_nombre || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_ESTADO[a.estado_display] || 'bg-slate-500/15'}`}>{a.estado_display}</span>
                </td>
                <td className="px-4 py-3 text-xs">{a.hallazgos_count > 0 ? a.hallazgos_count : '—'}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-400">Sin auditorías</td></tr>}
          </tbody>
        </table>
      </div>

      {/* Crear programa anual */}
      <Modal abierto={modalPrograma} titulo="Nuevo programa anual de auditorías" onCerrar={() => setModalPrograma(false)} ancho="max-w-md">
        <div className="space-y-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">El programa anual agrupa las auditorías del año.</p>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Año</label>
            <input type="number" className="input-esynapse" value={anioNuevo} onChange={(e) => setAnioNuevo(e.target.value)} />
          </div>
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button onClick={() => setModalPrograma(false)} className="btn-secondary">Cancelar</button>
            <button onClick={crearPrograma} className="btn-primary">Crear programa</button>
          </div>
        </div>
      </Modal>

      {/* Crear auditoría */}
      <Modal abierto={modalCrear} titulo="Nueva auditoría interna" onCerrar={() => setModalCrear(false)}>
        <form onSubmit={crear} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Programa anual</label>
              <select className="input-esynapse" value={form.programa} onChange={(e) => setForm({ ...form, programa: e.target.value })}>
                <option value="">— Sin programa —</option>
                {programas.map((p) => <option key={p.id} value={p.id}>{p.anio}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Tipo</label>
              <select className="input-esynapse" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
                <option value="programada">Programada</option>
                <option value="extraordinaria">Extraordinaria</option>
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Normas / criterios</label>
            <div className="flex flex-wrap gap-2">
              {NORMAS.map(([clave, nombre]) => (
                <label key={clave} className={`cursor-pointer rounded-lg border px-2.5 py-1.5 text-xs transition ${
                  form.normas.includes(clave) ? CHIP_NORMA[clave] : 'border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-300'}`}>
                  <input type="checkbox" className="hidden" checked={form.normas.includes(clave)}
                    onChange={(e) => setForm({ ...form, normas: e.target.checked ? [...form.normas, clave] : form.normas.filter((n) => n !== clave) })} />
                  {nombre}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Áreas / procesos a auditar</label>
            <textarea className="input-esynapse" rows={2} value={form.areas_procesos} onChange={(e) => setForm({ ...form, areas_procesos: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Modalidad</label>
              <select className="input-esynapse" value={form.modalidad} onChange={(e) => setForm({ ...form, modalidad: e.target.value })}>
                {MODALIDADES.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Mes programado</label>
              <input type="number" min="1" max="12" className="input-esynapse" value={form.mes_programado} onChange={(e) => setForm({ ...form, mes_programado: e.target.value })} />
            </div>
          </div>
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalCrear(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">Crear auditoría</button>
          </div>
        </form>
      </Modal>

      {/* Detalle */}
      <Modal abierto={Boolean(detalle)} titulo={detalle ? `${detalle.codigo} — Auditoría interna` : ''} onCerrar={() => setDetalle(null)} ancho="max-w-4xl">
        {detalle && (
          <div className="space-y-4 text-sm">
            {/* Stepper */}
            <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-3 dark:bg-slate-800/60">
              {NOMBRE_PASO.map((nombre, i) => {
                const actual = paso(detalle)
                const esActual = i === actual
                const completado = i < actual
                return (
                  <div key={nombre} className="flex flex-1 items-center">
                    <div className="flex flex-1 flex-col items-center gap-1">
                      <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                        completado ? 'bg-emerald-500 text-white' : esActual ? 'bg-esynapse-600 text-white ring-4 ring-esynapse-600/25' : 'bg-slate-300 text-slate-600 dark:bg-slate-700 dark:text-slate-400'}`}>
                        {completado ? '✓' : i + 1}
                      </div>
                      <span className={`text-center text-[10px] leading-tight ${esActual ? 'font-semibold text-esynapse-600 dark:text-esynapse-300' : completado ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'}`}>{nombre}</span>
                    </div>
                    {i < 4 && <div className={`mb-4 h-0.5 flex-1 ${completado ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-700'}`} />}
                  </div>
                )
              })}
            </div>

            <div className="flex flex-wrap gap-1">
              {(detalle.normas_display || []).map((n) => (
                <span key={n} className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_NORMA[n] || 'bg-slate-200'}`}>{n}</span>
              ))}
            </div>

            {/* Datos generales / planificación */}
            <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Plan de auditoría</p>
              <textarea className="input-esynapse" rows={2} placeholder="Objetivo" disabled={cerrada || !puedeEditar}
                value={gen.objetivo} onChange={(e) => setGen({ ...gen, objetivo: e.target.value })} />
              <textarea className="input-esynapse" rows={2} placeholder="Alcance" disabled={cerrada || !puedeEditar}
                value={gen.alcance} onChange={(e) => setGen({ ...gen, alcance: e.target.value })} />
              <div className="grid grid-cols-2 gap-2">
                <input className="input-esynapse" placeholder="Criterios" disabled={cerrada || !puedeEditar}
                  value={gen.criterios} onChange={(e) => setGen({ ...gen, criterios: e.target.value })} />
                <select className="input-esynapse" disabled={cerrada || !puedeEditar} value={gen.auditor_lider}
                  onChange={(e) => setGen({ ...gen, auditor_lider: e.target.value })}>
                  <option value="">— Auditor líder —</option>
                  {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
                </select>
              </div>
              {!cerrada && puedeEditar && (
                <div className="flex gap-2">
                  <button onClick={() => accion(guardarGenerales)} className="btn-secondary !py-1.5 text-xs">Guardar datos</button>
                  {detalle.estado === 'programada' && (
                    <button onClick={() => accion(async () => { await guardarGenerales(); await api.auditorias.planificar(detalle.id) })} className="btn-primary !py-1.5 text-xs">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Planificar
                    </button>
                  )}
                  {detalle.estado === 'planificada' && (
                    <button onClick={() => accion(() => api.auditorias.iniciar(detalle.id))} className="btn-primary !py-1.5 text-xs">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Iniciar ejecución
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Equipo auditor */}
            <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
              <p className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"><Users className="h-3.5 w-3.5" /> Equipo auditor</p>
              {(detalle.equipo || []).map((m) => (
                <div key={m.id} className="flex items-center justify-between text-xs">
                  <span><strong>{m.rol_display}:</strong> {m.nombre} {m.cargo && `· ${m.cargo}`}</span>
                  {!cerrada && puedeEditar && (
                    <button onClick={() => accion(() => api.auditorias.quitarIntegrante(detalle.id, m.id))} className="text-red-500 hover:underline">quitar</button>
                  )}
                </div>
              ))}
              {(detalle.equipo || []).length === 0 && <p className="text-xs text-slate-400">Sin integrantes aún.</p>}
              {!cerrada && puedeEditar && (
                <div className="grid grid-cols-12 items-end gap-2">
                  <select className="input-esynapse col-span-3 !py-1.5 text-xs" value={equipoForm.rol} onChange={(e) => setEquipoForm({ ...equipoForm, rol: e.target.value })}>
                    {ROLES.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                  </select>
                  <select className="input-esynapse col-span-4 !py-1.5 text-xs" value={equipoForm.usuario} onChange={(e) => setEquipoForm({ ...equipoForm, usuario: e.target.value, nombre_externo: '' })}>
                    <option value="">— Interno —</option>
                    {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
                  </select>
                  <input className="input-esynapse col-span-3 !py-1.5 text-xs" placeholder="o externo" value={equipoForm.nombre_externo}
                    onChange={(e) => setEquipoForm({ ...equipoForm, nombre_externo: e.target.value, usuario: '' })} />
                  <button disabled={!equipoForm.usuario && !equipoForm.nombre_externo}
                    onClick={() => accion(async () => { const d = { ...equipoForm }; if (!d.usuario) delete d.usuario; await api.auditorias.agregarIntegrante(detalle.id, d); setEquipoForm({ usuario: '', nombre_externo: '', rol: 'auditor', cargo: '' }) })}
                    className="btn-secondary col-span-2 !px-2 !py-1.5 text-xs"><Plus className="h-3.5 w-3.5" /></button>
                </div>
              )}
            </div>

            {/* Listas de verificación */}
            {['en_ejecucion', 'en_informe', 'cerrada'].includes(detalle.estado) && (
              <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Listas de verificación</p>
                {(detalle.normas_aplicables || []).map((clave) => {
                  const lista = (detalle.listas || []).find((l) => l.norma === clave)
                  const nombre = NORMAS.find((n) => n[0] === clave)?.[1] || clave
                  return (
                    <div key={clave} className="rounded-lg border border-slate-100 dark:border-slate-800/60">
                      <div className="flex items-center justify-between px-2 py-1.5">
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${CHIP_NORMA[clave]}`}>{nombre}</span>
                        {lista ? (
                          <button onClick={() => setListaAbierta(listaAbierta === clave ? null : clave)} className="text-xs text-esynapse-500 hover:underline">
                            {listaAbierta === clave ? 'ocultar' : `ver (${lista.avance})`}
                          </button>
                        ) : (!cerrada && puedeEditar && (
                          <button onClick={() => accion(() => api.auditorias.generarLista(detalle.id, clave))} className="text-xs text-esynapse-500 hover:underline">generar lista</button>
                        ))}
                      </div>
                      {lista && listaAbierta === clave && (
                        <div className="max-h-72 space-y-0.5 overflow-y-auto border-t border-slate-100 p-2 dark:border-slate-800/60">
                          {lista.items.map((it) => it.es_seccion ? (
                            <p key={it.id} className="pt-1 text-[11px] font-semibold text-slate-600 dark:text-slate-300">{it.codigo} {it.titulo}</p>
                          ) : (
                            <div key={it.id} className="grid grid-cols-12 items-center gap-1 text-[11px]">
                              <span className="col-span-6 text-slate-600 dark:text-slate-400">{it.codigo} {it.titulo}</span>
                              <select disabled={cerrada || !puedeEditar} value={it.resultado}
                                onChange={(e) => accion(() => api.auditorias.evaluarItem(detalle.id, { item_id: it.id, resultado: e.target.value }))}
                                className={`input-esynapse col-span-2 !py-0.5 text-[11px] font-medium ${COLOR_RESULTADO[it.resultado]}`}>
                                {RESULTADOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                              </select>
                              <input disabled={cerrada || !puedeEditar} defaultValue={it.observacion} placeholder="observación"
                                onBlur={(e) => { if (e.target.value !== it.observacion) accion(() => api.auditorias.evaluarItem(detalle.id, { item_id: it.id, resultado: it.resultado, observacion: e.target.value })) }}
                                className="input-esynapse col-span-4 !py-0.5 text-[11px]" />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {/* Hallazgos */}
            {['en_ejecucion', 'en_informe', 'cerrada'].includes(detalle.estado) && (
              <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <p className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"><AlertTriangle className="h-3.5 w-3.5" /> Hallazgos (se registran en M8)</p>
                {(detalle.hallazgos || []).map((h) => (
                  <div key={h.id} className="rounded-lg border border-slate-100 px-2 py-1.5 text-xs dark:border-slate-800/60">
                    <span className="font-mono font-medium">{h.codigo}</span> · <span className="font-medium">{h.tipo_display}</span>
                    {h.requiere_ac && <span className="ml-1 rounded bg-red-500/15 px-1 py-0.5 text-[9px] text-red-600 dark:text-red-400">requiere AC</span>}
                    <span className="ml-1 text-slate-400">[{h.estado}]</span>
                    <p className="text-slate-500 dark:text-slate-400">{h.descripcion} {h.requisito && `· ${h.requisito}`}</p>
                  </div>
                ))}
                {(detalle.hallazgos || []).length === 0 && <p className="text-xs text-slate-400">Sin hallazgos.</p>}
                {['en_ejecucion', 'en_informe'].includes(detalle.estado) && tienePermiso('auditorias', 'crear') && (
                  <div className="grid grid-cols-12 items-end gap-2">
                    <select className="input-esynapse col-span-3 !py-1.5 text-xs" value={hallForm.tipo} onChange={(e) => setHallForm({ ...hallForm, tipo: e.target.value })}>
                      {TIPOS_HALLAZGO.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                    </select>
                    <input className="input-esynapse col-span-3 !py-1.5 text-xs" placeholder="Requisito (ej. 17025 6.4)" value={hallForm.requisito} onChange={(e) => setHallForm({ ...hallForm, requisito: e.target.value })} />
                    <input className="input-esynapse col-span-4 !py-1.5 text-xs" placeholder="Descripción del hallazgo" value={hallForm.descripcion} onChange={(e) => setHallForm({ ...hallForm, descripcion: e.target.value })} />
                    <button disabled={!hallForm.descripcion}
                      onClick={() => accion(async () => { await api.auditorias.registrarHallazgo(detalle.id, hallForm); setHallForm({ tipo: 'nc_menor', proceso: '', requisito: '', descripcion: '' }) })}
                      className="btn-secondary col-span-2 !px-2 !py-1.5 text-xs"><Plus className="h-3.5 w-3.5" /></button>
                  </div>
                )}
              </div>
            )}

            {/* Actas */}
            {['en_ejecucion', 'en_informe', 'cerrada'].includes(detalle.estado) && (
              <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Actas (apertura / cierre)</p>
                {(detalle.actas || []).map((ac) => (
                  <p key={ac.id} className="text-xs text-slate-500 dark:text-slate-400"><strong>{ac.tipo_display}:</strong> {ac.contenido}</p>
                ))}
                {!cerrada && puedeEditar && (
                  <div className="grid grid-cols-12 items-end gap-2">
                    <select className="input-esynapse col-span-3 !py-1.5 text-xs" value={actaForm.tipo} onChange={(e) => setActaForm({ ...actaForm, tipo: e.target.value })}>
                      <option value="apertura">Apertura</option><option value="cierre">Cierre</option>
                    </select>
                    <input className="input-esynapse col-span-7 !py-1.5 text-xs" placeholder="Contenido del acta" value={actaForm.contenido} onChange={(e) => setActaForm({ ...actaForm, contenido: e.target.value })} />
                    <button disabled={!actaForm.contenido}
                      onClick={() => accion(async () => { await api.auditorias.registrarActa(detalle.id, actaForm); setActaForm({ tipo: 'apertura', contenido: '' }) })}
                      className="btn-secondary col-span-2 !px-2 !py-1.5 text-xs">Guardar</button>
                  </div>
                )}
              </div>
            )}

            {/* Informe + cierre */}
            {['en_ejecucion', 'en_informe', 'cerrada'].includes(detalle.estado) && (
              <div className="space-y-2 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3">
                <p className="flex items-center gap-1 text-xs font-semibold text-violet-600 dark:text-violet-400"><FileText className="h-3.5 w-3.5" /> Informe de auditoría</p>
                <textarea className="input-esynapse" rows={2} placeholder="Fortalezas" disabled={cerrada} value={informe.fortalezas} onChange={(e) => setInforme({ ...informe, fortalezas: e.target.value })} />
                <textarea className="input-esynapse" rows={2} placeholder="Debilidades" disabled={cerrada} value={informe.debilidades} onChange={(e) => setInforme({ ...informe, debilidades: e.target.value })} />
                <textarea className="input-esynapse" rows={2} placeholder="Conclusiones" disabled={cerrada} value={informe.conclusiones} onChange={(e) => setInforme({ ...informe, conclusiones: e.target.value })} />
                {detalle.estado === 'en_ejecucion' && puedeEditar && (
                  <button onClick={() => accion(() => api.auditorias.generarInforme(detalle.id, informe))} className="btn-primary !py-1.5 text-xs">
                    <FileText className="h-3.5 w-3.5" /> Generar informe
                  </button>
                )}
                {detalle.estado === 'en_informe' && puedeAprobar && (
                  <button onClick={() => accion(() => api.auditorias.cerrar(detalle.id, { conclusiones: informe.conclusiones }))} className="btn-primary !py-1.5 text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Cerrar auditoría
                  </button>
                )}
                {cerrada && <p className="text-xs text-emerald-600 dark:text-emerald-400">✓ Auditoría cerrada. Las NC se tratan en Acciones Correctivas (M9).</p>}
              </div>
            )}

            {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          </div>
        )}
      </Modal>
    </div>
  )
}
