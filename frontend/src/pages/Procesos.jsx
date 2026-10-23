import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Bell, FileText, GitBranch, History, List, Pencil, Plus,
  Power, Save, Trash2, X,
} from 'lucide-react'
import Modal from '../components/Modal.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import Badge from '../components/ui/Badge.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import { refrescarCatalogoProcesos } from '../components/SelectorProceso.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fecha, fechaHora } from '../lib/fecha.js'

// Colores de estado (regla 10): gris elaboración · ámbar revisión · azul aprobación · verde vigente · rojo obsoleta.
const TONO_FICHA = { borrador: 'gris', en_revision: 'ambar', en_aprobacion: 'azul', vigente: 'verde', obsoleta: 'rojo' }
const TONO_RESULTADO = { cumple: 'verde', en_riesgo: 'ambar', no_cumple: 'rojo' }
const PUNTO = { cumple: 'bg-emerald-500', en_riesgo: 'bg-amber-500', no_cumple: 'bg-red-500' }
const TIPOS = [['estrategico', 'Estratégico'], ['operativo', 'Operativo'], ['soporte', 'Soporte']]
const FRECUENCIAS = [['mensual', 'Mensual'], ['trimestral', 'Trimestral'], ['semestral', 'Semestral'], ['anual', 'Anual']]
const ROL_FIRMA = { elaborado: 'Elaboró', revisado: 'Revisó', aprobado: 'Aprobó' }
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'

const abrirBlob = async (promesa, setError) => {
  try {
    const url = URL.createObjectURL(await promesa)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (e) { setError(e.message) }
}

function EstadoFicha({ ficha }) {
  if (!ficha) return <Badge tono="gris">Sin ficha</Badge>
  return <Badge tono={TONO_FICHA[ficha.estado] || 'gris'}>{ficha.estado_display} · v{ficha.version}</Badge>
}

export default function Procesos() {
  const [vista, setVista] = useState('mapa')
  const [procesoId, setProcesoId] = useState(null)
  const [mapa, setMapa] = useState(null)
  const [avisos, setAvisos] = useState([])
  const [error, setError] = useState('')

  const cargar = useCallback(async () => {
    const [m, a] = await Promise.all([api.procesos.mapa(), api.procesos.avisos('?pendientes=1')])
    setMapa(m)
    setAvisos(a.results ?? a)
  }, [])
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [cargar])

  if (procesoId) {
    return <VistaProceso id={procesoId} onVolver={() => { setProcesoId(null); cargar().catch(() => {}) }} onAbrir={setProcesoId} />
  }

  return (
    <div className="space-y-4">
      <PageHeader icon={GitBranch} title="Procesos"
        subtitle="Mapa de procesos, fichas de caracterización y catálogo oficial que usan los demás módulos"
        actions={(
          <>
            <button className="btn-secondary" onClick={() => abrirBlob(api.procesos.mapaPdf(), setError)}><FileText className="h-4 w-4" /> Mapa en PDF</button>
          </>
        )} />
      <div className="flex flex-wrap gap-2">
        {[['mapa', 'Mapa de procesos', GitBranch], ['catalogo', 'Catálogo', List], ['avisos', `Fichas por revisar (${avisos.length})`, Bell]].map(([k, t, I]) => (
          <button key={k} onClick={() => setVista(k)}
            className={`${vista === k ? 'btn-primary' : 'btn-secondary'} !py-1.5 text-xs`}><I className="h-3.5 w-3.5" /> {t}</button>
        ))}
      </div>
      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      {vista === 'mapa' && <Mapa mapa={mapa} onAbrir={setProcesoId} />}
      {vista === 'catalogo' && <Catalogo onAbrir={setProcesoId} onCambio={() => cargar().catch(() => {})} />}
      {vista === 'avisos' && <ListaAvisos avisos={avisos} onAbrir={setProcesoId} onCambio={() => cargar().catch(() => {})} />}
    </div>
  )
}

// ---------------------------------------------------------------- mapa
function Mapa({ mapa, onAbrir }) {
  if (!mapa) return <p className="text-sm muted">Cargando el mapa…</p>
  return (
    <div className="card-esynapse card-pad">
      <div className="grid grid-cols-[44px_minmax(0,1fr)_44px] gap-3">
        <div className="flex items-center justify-center rounded-2xl bg-lime-500/80 p-2 text-white"><span className="rotate-180 text-center text-xs font-semibold [writing-mode:vertical-rl]">Cliente · <span className="font-normal">requisitos y partes interesadas</span></span></div>
        <div className="space-y-3">
          {mapa.bandas.map((b) => (
            <div key={b.tipo} className="rounded-xl border border-dashed border-slate-400/70 p-3 dark:border-slate-600">
              <p className="mb-2 inline-block rounded bg-red-700 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white">
                {{ estrategico: 'Procesos estratégicos', operativo: 'Procesos principales', soporte: 'Procesos de soporte' }[b.tipo]}
              </p>
              {b.procesos.length === 0 && <p className="text-xs muted">Sin procesos en el catálogo.</p>}
              <div className={`grid gap-2 ${b.tipo === 'soporte' ? 'grid-cols-2 md:grid-cols-3 xl:grid-cols-6' : 'grid-cols-1 md:grid-cols-[repeat(auto-fit,minmax(200px,1fr))]'}`}>
                {b.procesos.map((p) => <TarjetaProceso key={p.id} p={p} onAbrir={onAbrir} ancha={Boolean(p.subprocesos.length || p.detalle_mapa)} />)}
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-center rounded-2xl bg-lime-500/80 p-2 text-white"><span className="rotate-180 text-center text-xs font-semibold [writing-mode:vertical-rl]">Cliente · <span className="font-normal">satisfacción y resultados del SIG</span></span></div>
      </div>
      <p className="mt-3 flex flex-wrap items-center gap-3 text-[11px] muted">
        Indicadores del último periodo:
        {[['cumple', 'cumple'], ['en_riesgo', 'en riesgo'], ['no_cumple', 'no cumple']].map(([k, t]) => (
          <span key={k} className="inline-flex items-center gap-1"><span className={`h-2 w-2 rounded-full ${PUNTO[k]}`} />{t}</span>
        ))}
      </p>
    </div>
  )
}

function TarjetaProceso({ p, onAbrir, ancha }) {
  const v = p.vinculados || {}
  const ficha = p.ficha_en_curso || (p.ficha_vigente ? { ...p.ficha_vigente, estado: 'vigente', estado_display: 'Vigente' } : null)
  return (
    <div className={`rounded-lg border border-slate-200 bg-white p-2.5 text-center dark:border-slate-700 dark:bg-slate-900 ${ancha ? 'md:col-span-2' : ''}`}>
      <button type="button" onClick={() => onAbrir(p.id)} className="w-full text-sm font-semibold hover:text-esynapse-600">
        {p.nombre} {p.semaforo && <span className={`ml-1 inline-block h-2 w-2 rounded-full ${PUNTO[p.semaforo]}`} />}
      </button>
      <p className="text-[11px] muted">{p.responsable_cargo || 'Sin responsable'}</p>
      {p.detalle_mapa && <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{p.detalle_mapa}</p>}
      <div className="mt-1.5 flex flex-wrap justify-center gap-1">
        {!p.subprocesos.length && <EstadoFicha ficha={ficha} />}
        {v.nc_abiertas > 0 && <Badge tono="rojo">{v.nc_abiertas} NC</Badge>}
        {p.avisos_pendientes > 0 && <Badge tono="ambar">Ficha por revisar</Badge>}
      </div>
      {p.subprocesos.length > 0 && (
        <div className="mt-2 flex flex-wrap justify-center gap-1">
          {p.subprocesos.map((s) => (
            <button key={s.id} type="button" onClick={() => onAbrir(s.id)}
              className={`rounded-md px-2 py-0.5 text-[11px] ring-1 ring-inset ${s.avisos_pendientes ? 'bg-amber-500/15 text-amber-700 ring-amber-500/30 dark:text-amber-300' : 'bg-esynapse-500/10 text-esynapse-700 ring-esynapse-500/25 hover:bg-esynapse-500/20 dark:text-esynapse-300'}`}>
              {s.nombre}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- catálogo
const PROC_VACIO = { nombre: '', tipo: 'soporte', padre: '', responsable_cargo: '', responsable: '', detalle_mapa: '', orden: 0 }

function Catalogo({ onAbrir, onCambio }) {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const [items, setItems] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(PROC_VACIO)
  const [error, setError] = useState('')
  const cargar = useCallback(async () => {
    const d = await api.procesos.listar('?todos=1')
    setItems(d.results ?? d)
  }, [])
  useEffect(() => {
    cargar().catch((e) => setError(e.message))
    api.usuarios.listar().then((d) => setUsuarios(d.results ?? d)).catch(() => {})
  }, [cargar])

  const raiz = items.filter((p) => !p.padre)
  const ordenados = raiz.flatMap((p) => [p, ...items.filter((s) => s.padre === p.id)])
  const abrir = (p) => {
    setError('')
    setForm(p ? { nombre: p.nombre, tipo: p.tipo, padre: p.padre || '', responsable_cargo: p.responsable_cargo, responsable: p.responsable || '', detalle_mapa: p.detalle_mapa, orden: p.orden } : PROC_VACIO)
    setModal(p ? p.id : 'nuevo')
  }
  const guardar = async (e) => {
    e.preventDefault()
    setError('')
    const datos = { ...form, padre: form.padre || null, responsable: form.responsable || null, orden: Number(form.orden) || 0 }
    try {
      if (modal === 'nuevo') await api.procesos.crear(datos)
      else await api.procesos.editar(modal, datos)
      setModal(null)
      refrescarCatalogoProcesos()
      await cargar()
      onCambio()
    } catch (err) { setError(err.message) }
  }
  const activar = async (p) => {
    setError('')
    try {
      if (p.is_active) {
        if (!await confirmar({ titulo: 'Desactivar proceso', mensaje: `«${p.nombre}» sale del mapa y de las listas. Su historial se conserva.`, peligro: true, textoConfirmar: 'Desactivar' })) return
        await api.procesos.desactivar(p.id)
      } else {
        await api.procesos.reactivar(p.id)
      }
      refrescarCatalogoProcesos()
      await cargar()
      onCambio()
    } catch (err) { setError(err.message) }
  }
  const puedeEditar = tienePermiso('procesos', 'editar')

  return (
    <div className="card-esynapse overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
        <p className="text-sm muted">El catálogo oficial: lo usan Documentos, Hallazgos, Acciones correctivas, Quejas y Auditorías.</p>
        {tienePermiso('procesos', 'crear') && <button className="btn-primary !py-1.5 text-xs" onClick={() => abrir(null)}><Plus className="h-3.5 w-3.5" /> Nuevo proceso</button>}
      </div>
      {error && <p className="m-3 rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="overflow-x-auto">
        <table className="tabla-sig">
          <thead className="bg-slate-50 text-xs text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
            <tr><th className="px-4 py-2">Proceso</th><th className="px-4 py-2 text-center">Tipo</th><th className="px-4 py-2">Cargo responsable</th><th className="px-4 py-2 text-center">Recibe avisos</th><th className="px-4 py-2 text-center">Ficha</th><th className="px-4 py-2 text-center">Estado</th><th className="px-4 py-2" /></tr>
          </thead>
          <tbody>
            {ordenados.map((p) => (
              <tr key={p.id} className={`border-t border-slate-100 dark:border-slate-800 ${p.is_active ? '' : 'opacity-50'}`}>
                <td className="px-4 py-2">
                  <button className="font-medium hover:text-esynapse-600" onClick={() => onAbrir(p.id)}>{p.padre ? '↳ ' : ''}{p.nombre}</button>
                </td>
                <td className="px-4 py-2 text-center">{p.tipo_display}</td>
                <td className="px-4 py-2">{p.responsable_cargo || '—'}</td>
                <td className="px-4 py-2 text-center">{p.responsable_nombre || '—'}</td>
                <td className="px-4 py-2 text-center"><EstadoFicha ficha={p.ficha_en_curso || (p.ficha_vigente && { ...p.ficha_vigente, estado: 'vigente', estado_display: 'Vigente' })} /></td>
                <td className="px-4 py-2 text-center"><Badge tono={p.is_active ? 'verde' : 'gris'}>{p.is_active ? 'Activo' : 'Inactivo'}</Badge></td>
                <td className="whitespace-nowrap px-4 py-2">
                  {puedeEditar && <button title="Editar" className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => abrir(p)}><Pencil className="h-4 w-4" /></button>}
                  {puedeEditar && <button title={p.is_active ? 'Desactivar' : 'Reactivar'} className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => activar(p)}><Power className="h-4 w-4" /></button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal abierto={Boolean(modal)} titulo={modal === 'nuevo' ? 'Nuevo proceso' : 'Editar proceso'} onCerrar={() => setModal(null)}>
        <form onSubmit={guardar} className="space-y-3">
          {error && <p className="rounded-lg bg-red-500/10 p-2 text-xs text-red-600 dark:text-red-400">{error}</p>}
          <div><label className={lbl}>Nombre</label><input className="input-esynapse" required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={lbl}>Tipo</label>
              <select className="input-esynapse" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{TIPOS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></div>
            <div><label className={lbl}>Subproceso de</label>
              <select className="input-esynapse" value={form.padre} onChange={(e) => setForm({ ...form, padre: e.target.value })}>
                <option value="">— Es un proceso del mapa —</option>
                {raiz.filter((p) => p.is_active && p.id !== modal).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
              </select></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={lbl}>Cargo responsable</label><input className="input-esynapse" value={form.responsable_cargo} onChange={(e) => setForm({ ...form, responsable_cargo: e.target.value })} /></div>
            <div><label className={lbl}>Usuario que recibe los avisos</label>
              <select className="input-esynapse" value={form.responsable} onChange={(e) => setForm({ ...form, responsable: e.target.value })}>
                <option value="">— Nadie asignado —</option>
                {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
              </select></div>
          </div>
          <div><label className={lbl}>Detalle en el mapa (opcional; etapas separadas con →)</label><input className="input-esynapse" value={form.detalle_mapa} onChange={(e) => setForm({ ...form, detalle_mapa: e.target.value })} /></div>
          <div className="w-32"><label className={lbl}>Orden</label><input type="number" className="input-esynapse" value={form.orden} onChange={(e) => setForm({ ...form, orden: e.target.value })} /></div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={() => setModal(null)}>Cancelar</button>
            <button className="btn-primary"><Save className="h-4 w-4" /> Guardar</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

// ---------------------------------------------------------------- avisos
function ListaAvisos({ avisos, onAbrir, onCambio }) {
  const confirmar = useConfirm()
  const [error, setError] = useState('')
  const descartar = async (a) => {
    const motivo = await confirmar({ titulo: 'La ficha no requiere cambios', mensaje: a.motivo, textoConfirmar: 'Cerrar aviso', entrada: { etiqueta: 'Por qué no requiere cambios', obligatorio: true, multilinea: true } })
    if (motivo === null) return
    try { await api.procesos.descartarAviso(a.id, motivo); onCambio() } catch (e) { setError(e.message) }
  }
  return (
    <div className="card-esynapse card-pad space-y-2">
      {error && <p className="rounded-lg bg-red-500/10 p-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
      {avisos.length === 0 && <p className="text-sm muted">No hay fichas por revisar. Cuando se aprueba un documento vinculado a un proceso, su responsable recibe aquí el aviso.</p>}
      {avisos.map((a) => (
        <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
          <div>
            <button className="font-semibold hover:text-esynapse-600" onClick={() => onAbrir(a.proceso)}>{a.proceso_nombre}</button>
            <p className="text-xs text-slate-600 dark:text-slate-300">{a.motivo}</p>
            <p className="text-[11px] muted">{a.origen_display} · {fechaHora(a.created_at)}{a.registrado_por ? ` · ${a.registrado_por}` : ''}</p>
          </div>
          <div className="flex gap-2">
            <button className="btn-secondary !py-1 text-xs" onClick={() => descartar(a)}>No requiere cambios</button>
            <button className="btn-primary !py-1 text-xs" onClick={() => onAbrir(a.proceso)}>Revisar ficha <ArrowRight className="h-3.5 w-3.5" /></button>
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------- proceso y su ficha
function VistaProceso({ id, onVolver, onAbrir }) {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const [proceso, setProceso] = useState(null)
  const [catalogo, setCatalogo] = useState([])
  const [versiones, setVersiones] = useState([])
  const [ficha, setFicha] = useState(null)
  const [vinc, setVinc] = useState(null)
  const [avisos, setAvisos] = useState([])
  const [docsMaestra, setDocsMaestra] = useState([])
  const [edit, setEdit] = useState(null)
  const [sucio, setSucio] = useState(false)
  const [error, setError] = useState('')
  const [modalResultado, setModalResultado] = useState(null)
  const [verHistorial, setVerHistorial] = useState(false)

  const cargar = useCallback(async (fichaId) => {
    const [p, cat, fs, v, av] = await Promise.all([
      api.procesos.listar(`${id}/`), api.procesos.listar('?todos=1'), api.procesos.fichas(`?proceso=${id}`),
      api.procesos.vinculados(id), api.procesos.avisos(`?proceso=${id}`),
    ])
    setProceso(p)
    setCatalogo(cat.results ?? cat)
    const lista = fs.results ?? fs
    setVersiones(lista)
    setVinc(v)
    setAvisos(av.results ?? av)
    const elegida = fichaId || lista.find((f) => ['borrador', 'en_revision', 'en_aprobacion'].includes(f.estado))?.id
      || lista.find((f) => f.estado === 'vigente')?.id || lista[0]?.id
    if (elegida) {
      const f = await api.procesos.ficha(elegida)
      setFicha(f)
      setEdit(null)
      setSucio(false)
    } else {
      setFicha(null)
    }
  }, [id])
  useEffect(() => { setError(''); cargar().catch((e) => setError(e.message)) }, [cargar])
  useEffect(() => { api.documentos.listar('?page_size=500').then((d) => setDocsMaestra(d.results ?? d)).catch(() => {}) }, [])

  const puedeEditar = tienePermiso('procesos', 'editar')
  const puedeAprobar = tienePermiso('procesos', 'aprobar')
  const editable = ficha?.estado === 'borrador' && puedeEditar

  const empezarEdicion = () => {
    setEdit({
      objetivo: ficha.objetivo, responsable: ficha.responsable, alcance: ficha.alcance, motivo_cambio: ficha.motivo_cambio,
      recurso_humano: ficha.recurso_humano, recurso_economico: ficha.recurso_economico, recurso_tecnologico: ficha.recurso_tecnologico,
      actividades: ficha.actividades.map((a) => ({ ...a })),
      documentos: ficha.documentos.map((d) => ({ ...d })),
      registros: ficha.registros.map((r) => ({ ...r })),
      indicadores: ficha.indicadores.map((i) => ({ ...i })),
    })
    setSucio(false)
  }
  const cambiar = (cambios) => { setEdit({ ...edit, ...cambios }); setSucio(true) }
  const guardar = async () => {
    setError('')
    const limpiar = (lista, campos) => lista.map((x) => Object.fromEntries(Object.entries(x).filter(([k]) => campos.includes(k))))
    const datos = {
      ...edit,
      actividades: limpiar(edit.actividades, ['id', 'seccion', 'proveedores', 'proveedor_otro', 'entrada', 'actividad', 'control', 'clientes', 'cliente_otro', 'salida']),
      documentos: limpiar(edit.documentos, ['id', 'documento', 'descripcion']).map((d) => ({ ...d, documento: d.documento || null })),
      registros: limpiar(edit.registros, ['id', 'descripcion']),
      indicadores: limpiar(edit.indicadores, ['id', 'nombre', 'calculo', 'meta', 'frecuencia', 'responsable']),
    }
    try {
      const f = await api.procesos.editarFicha(ficha.id, datos)
      setFicha(f)
      setEdit(null)
      setSucio(false)
    } catch (e) { setError(e.message) }
  }
  const pedirClave = (titulo, mensaje) => confirmar({ titulo, mensaje, textoConfirmar: 'Firmar', entrada: { etiqueta: 'Su contraseña (firma)', tipo: 'password', obligatorio: true } })
  const accion = async (fn) => {
    setError('')
    try { await fn(); await cargar(ficha?.id) } catch (e) { setError(e.message) }
  }
  const enviar = async () => {
    if (sucio) { setError('Guarde los cambios antes de enviar la ficha a revisión.'); return }
    const clave = await pedirClave('Enviar a revisión', 'Firma como quien elabora la ficha. Desde ahora su contenido queda de solo lectura.')
    if (clave !== null) accion(() => api.procesos.enviar(ficha.id, clave))
  }
  const revisar = async () => {
    const clave = await pedirClave('Revisión conforme', 'Firma como quien revisa. La ficha pasa a aprobación.')
    if (clave !== null) accion(() => api.procesos.revisar(ficha.id, clave))
  }
  const aprobar = async () => {
    const clave = await pedirClave('Aprobar la ficha', 'Firma como quien aprueba. Esta versión queda vigente y la anterior pasa a obsoleta.')
    if (clave !== null) accion(() => api.procesos.aprobar(ficha.id, clave))
  }
  const devolver = async () => {
    const c = await confirmar({ titulo: 'Devolver con observaciones', mensaje: 'La ficha vuelve a elaboración y se anulan las firmas de esta ronda.', textoConfirmar: 'Devolver', peligro: true, entrada: { etiqueta: 'Observaciones', obligatorio: true, multilinea: true } })
    if (c !== null) accion(() => api.procesos.devolver(ficha.id, c))
  }
  const nuevaVersion = async () => {
    const motivo = await confirmar({ titulo: 'Nueva versión de la ficha', mensaje: 'Se copia la ficha vigente en una versión en elaboración. La vigente sigue rigiendo hasta que se apruebe la nueva.', textoConfirmar: 'Crear versión', entrada: { etiqueta: 'Motivo del cambio', obligatorio: true, multilinea: true } })
    if (motivo === null) return
    setError('')
    try { const f = await api.procesos.nuevaVersion(ficha.id, motivo); await cargar(f.id) } catch (e) { setError(e.message) }
  }
  const crearFicha = async () => {
    setError('')
    try { const f = await api.procesos.crearFicha({ proceso: id, responsable: proceso.responsable_cargo }); await cargar(f.id) } catch (e) { setError(e.message) }
  }
  const registrarAviso = async () => {
    const motivo = await confirmar({ titulo: 'Registrar aviso', mensaje: 'Algo cambió en el proceso y su ficha puede estar desactualizada (por ejemplo, empezó a usarse un módulo nuevo).', textoConfirmar: 'Registrar', entrada: { etiqueta: 'Qué cambió', obligatorio: true, multilinea: true } })
    if (motivo !== null) accion(() => api.procesos.crearAviso({ proceso: id, motivo }))
  }
  const descartarAviso = async (a) => {
    const motivo = await confirmar({ titulo: 'La ficha no requiere cambios', mensaje: a.motivo, textoConfirmar: 'Cerrar aviso', entrada: { etiqueta: 'Por qué no requiere cambios', obligatorio: true, multilinea: true } })
    if (motivo !== null) accion(() => api.procesos.descartarAviso(a.id, motivo))
  }

  if (!proceso) return <div className="space-y-3"><button className="btn-secondary" onClick={onVolver}><ArrowLeft className="h-4 w-4" /> Procesos</button>{error ? <p className="text-sm text-red-600">{error}</p> : <p className="text-sm muted">Cargando…</p>}</div>

  const pendientes = avisos.filter((a) => !a.atendido)
  const datos = edit || ficha
  const subprocesos = catalogo.filter((p) => p.padre === proceso.id && p.is_active)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button className="mb-1 inline-flex items-center gap-1 text-xs muted hover:text-esynapse-600" onClick={onVolver}><ArrowLeft className="h-3.5 w-3.5" /> Mapa de procesos</button>
          <h1 className="page-title">{proceso.nombre}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            <Badge tono="gris">{proceso.tipo_display}</Badge>
            {proceso.padre_nombre && <Badge tono="gris">Subproceso de {proceso.padre_nombre}</Badge>}
            {ficha && <EstadoFicha ficha={ficha} />}
            {proceso.responsable_cargo && <span className="text-xs muted">Responsable: {proceso.responsable_cargo}</span>}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {versiones.length > 1 && (
            <select className="input-esynapse !w-auto !py-1.5 text-xs" value={ficha?.id || ''} onChange={(e) => cargar(Number(e.target.value)).catch((err) => setError(err.message))}>
              {versiones.map((v) => <option key={v.id} value={v.id}>Versión {v.version} — {v.estado_display}</option>)}
            </select>
          )}
          {ficha && <button className="btn-secondary !py-1.5 text-xs" onClick={() => setVerHistorial(true)}><History className="h-3.5 w-3.5" /> Historial</button>}
          {ficha && <button className="btn-secondary !py-1.5 text-xs" onClick={() => abrirBlob(api.procesos.fichaPdf(ficha.id), setError)}><FileText className="h-3.5 w-3.5" /> Ficha en PDF</button>}
        </div>
      </div>
      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {pendientes.length > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
          <p className="mb-1 flex items-center gap-1.5 font-semibold text-amber-700 dark:text-amber-300"><AlertTriangle className="h-4 w-4" /> Ficha por revisar</p>
          {pendientes.map((a) => (
            <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-1 text-xs">
              <span>{a.motivo} <span className="muted">({fecha(a.created_at)})</span></span>
              {puedeEditar && <button className="btn-secondary !py-0.5 text-[11px]" onClick={() => descartarAviso(a)}>No requiere cambios</button>}
            </div>
          ))}
          <p className="mt-1 text-[11px] muted">Se atienden al aprobar la siguiente versión de la ficha.</p>
        </div>
      )}

      {subprocesos.length > 0 && (
        <div className="card-esynapse card-pad">
          <p className="mb-2 text-xs font-semibold muted">Subprocesos</p>
          <div className="flex flex-wrap gap-2">
            {subprocesos.map((s) => (
              <button key={s.id} className="btn-secondary !py-1 text-xs" onClick={() => onAbrir(s.id)}>
                {s.nombre} {s.ficha_en_curso ? `· ${s.ficha_en_curso.estado_display}` : s.ficha_vigente ? `· vigente v${s.ficha_vigente.version}` : ''}
              </button>
            ))}
          </div>
        </div>
      )}

      {!ficha && (
        <div className="card-esynapse card-pad text-sm">
          <p className="muted">Este proceso aún no tiene ficha de caracterización.</p>
          {tienePermiso('procesos', 'crear') && <button className="btn-primary mt-3" onClick={crearFicha}><Plus className="h-4 w-4" /> Crear ficha</button>}
        </div>
      )}

      {ficha && (
        <>
          {ficha.motivo_cambio && <p className="text-xs muted"><strong>Motivo de la versión {ficha.version}:</strong> {ficha.motivo_cambio}</p>}
          {ficha.devoluciones?.length > 0 && ficha.estado === 'borrador' && (
            <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 p-3 text-xs">
              <p className="mb-1 font-semibold text-violet-700 dark:text-violet-300">Observaciones de la última devolución</p>
              <p>{ficha.devoluciones[ficha.devoluciones.length - 1].comentarios}</p>
              <p className="muted">{ficha.devoluciones[ficha.devoluciones.length - 1].usuario} · {ficha.devoluciones[ficha.devoluciones.length - 1].etapa}</p>
            </div>
          )}
          {editable && !edit && (
            <div className="flex justify-end"><button className="btn-secondary !py-1.5 text-xs" onClick={empezarEdicion}><Pencil className="h-3.5 w-3.5" /> Editar la ficha</button></div>
          )}

          <div className="card-esynapse card-pad space-y-4">
            <Bloque titulo="Datos del proceso">
              <div className="grid gap-3 md:grid-cols-3">
                <Campo etiqueta="Responsable" valor={datos.responsable} editar={edit && ((v) => cambiar({ responsable: v }))} />
                <Campo etiqueta="Objetivo" valor={datos.objetivo} editar={edit && ((v) => cambiar({ objetivo: v }))} multilinea clase="md:col-span-2" />
                <Campo etiqueta="Alcance" valor={datos.alcance} editar={edit && ((v) => cambiar({ alcance: v }))} multilinea clase="md:col-span-3" />
                {edit && ficha.version !== '01' && <Campo etiqueta="Motivo de esta versión" valor={datos.motivo_cambio} editar={(v) => cambiar({ motivo_cambio: v })} multilinea clase="md:col-span-3" />}
              </div>
            </Bloque>

            <Bloque titulo={`Descripción del proceso · ${datos.actividades.length} actividades`}>
              {edit
                ? <EditorActividades filas={edit.actividades} catalogo={catalogo} onChange={(v) => cambiar({ actividades: v })} />
                : <TablaActividades filas={ficha.actividades} catalogo={catalogo} onAbrir={onAbrir} />}
            </Bloque>

            <div className="grid gap-4 lg:grid-cols-3">
              <Bloque titulo="Documentos asociados">
                {edit
                  ? <EditorDocumentos filas={edit.documentos} docs={docsMaestra} onChange={(v) => cambiar({ documentos: v })} />
                  : <ul className="space-y-1 text-sm">{ficha.documentos.map((d) => (
                    <li key={d.id}>{d.documento ? <span><span className="text-esynapse-600 dark:text-esynapse-300">{d.documento_titulo}</span> <span className="text-[11px] muted">(lista maestra)</span></span> : <span>{d.descripcion} <span className="text-[11px] text-amber-600">sin vincular</span></span>}</li>
                  ))}</ul>}
              </Bloque>
              <Bloque titulo="Registros">
                {edit
                  ? <EditorLista filas={edit.registros} campo="descripcion" placeholder="Registro que genera el proceso" onChange={(v) => cambiar({ registros: v })} />
                  : <ul className="space-y-1 text-sm">{ficha.registros.map((r) => <li key={r.id}>{r.descripcion}</li>)}</ul>}
              </Bloque>
              <Bloque titulo="Recursos">
                <div className="space-y-2">
                  <Campo etiqueta="Humano" valor={datos.recurso_humano} editar={edit && ((v) => cambiar({ recurso_humano: v }))} multilinea />
                  <Campo etiqueta="Económico" valor={datos.recurso_economico} editar={edit && ((v) => cambiar({ recurso_economico: v }))} multilinea />
                  <Campo etiqueta="Tecnológico" valor={datos.recurso_tecnologico} editar={edit && ((v) => cambiar({ recurso_tecnologico: v }))} multilinea />
                </div>
              </Bloque>
            </div>

            <Bloque titulo="Seguimiento y medición del proceso">
              {edit
                ? <EditorIndicadores filas={edit.indicadores} onChange={(v) => cambiar({ indicadores: v })} />
                : (
                  <div className="overflow-x-auto">
                    <table className="tabla-ficha w-full text-sm">
                      <thead className="text-xs text-slate-500 dark:text-slate-400"><tr><th className="py-1">Indicador</th><th className="py-1">Forma de cálculo</th><th className="py-1 text-right">Meta</th><th className="py-1">Frecuencia</th><th className="py-1">Responsable</th><th className="py-1 text-center">Último resultado</th><th /></tr></thead>
                      <tbody>
                        {ficha.indicadores.map((i) => (
                          <tr key={i.id} className="border-t border-slate-100 dark:border-slate-800">
                            <td className="py-1.5 font-medium">{i.nombre}</td><td className="py-1.5 text-xs">{i.calculo}</td><td className="py-1.5 text-right">{i.meta}</td>
                            <td className="py-1.5">{i.frecuencia_display}</td><td className="py-1.5">{i.responsable}</td>
                            <td className="py-1.5 text-center">{i.ultimo_resultado
                              ? <span className="inline-flex flex-col items-center"><Badge tono={TONO_RESULTADO[i.ultimo_resultado.estado]}>{i.ultimo_resultado.valor} · {i.ultimo_resultado.estado_display}</Badge><span className="text-[11px] muted">{i.ultimo_resultado.periodo.slice(0, 7)}</span></span>
                              : <span className="text-xs muted">Sin registrar</span>}</td>
                            <td className="py-1.5">{puedeEditar && <button className="btn-secondary !py-0.5 text-[11px]" onClick={() => setModalResultado(i)}>Registrar</button>}</td>
                          </tr>
                        ))}
                        {ficha.indicadores.length === 0 && <tr><td colSpan={7} className="py-2 text-xs muted">Sin indicadores.</td></tr>}
                      </tbody>
                    </table>
                  </div>
                )}
            </Bloque>

            {edit && (
              <div className="sticky bottom-2 flex items-center justify-end gap-2 rounded-lg border border-slate-200 bg-white/95 p-2 dark:border-slate-700 dark:bg-slate-900/95">
                {sucio && <span className="mr-auto text-xs text-amber-600 dark:text-amber-400">Hay cambios sin guardar</span>}
                <button className="btn-secondary" onClick={() => { setEdit(null); setSucio(false) }}><X className="h-4 w-4" /> Descartar</button>
                <button className="btn-primary" onClick={guardar}><Save className="h-4 w-4" /> Guardar cambios</button>
              </div>
            )}
          </div>

          {vinc && <Vinculados v={vinc} />}

          {ficha.estado === 'borrador' && puedeEditar && !edit && (
            <BarraEtapa titulo="Elaboración" nota="Al enviar firma como quien elabora; la ficha pasa a revisión del Gerente SIG."
              botones={[{ texto: 'Enviar a revisión', accion: enviar }]} />
          )}
          {ficha.estado === 'en_revision' && puedeAprobar && (
            <BarraEtapa titulo="Revisión" nota="Revisa alguien distinto de quien elaboró. Conforme: firma y pasa a aprobación."
              botones={[{ texto: 'Devolver', accion: devolver, secundario: true }, { texto: 'Revisión conforme', accion: revisar }]} />
          )}
          {ficha.estado === 'en_aprobacion' && puedeAprobar && (
            <BarraEtapa titulo="Aprobación" nota="Aprueba alguien distinto de quien revisó. La versión queda vigente."
              botones={[{ texto: 'Devolver', accion: devolver, secundario: true }, { texto: 'Aprobar', accion: aprobar }]} />
          )}
          {ficha.estado === 'vigente' && tienePermiso('procesos', 'crear') && !versiones.some((v) => ['borrador', 'en_revision', 'en_aprobacion'].includes(v.estado)) && (
            <BarraEtapa titulo="Ficha vigente: solo lectura" nota="Para cambiarla se crea una nueva versión con su motivo; pasa por revisión y aprobación."
              botones={[{ texto: 'Nueva versión', accion: nuevaVersion }]} />
          )}
          {puedeEditar && <div className="text-right"><button className="text-xs muted hover:text-esynapse-600" onClick={registrarAviso}><Bell className="mr-1 inline h-3.5 w-3.5" />Registrar que algo cambió en el proceso</button></div>}
        </>
      )}

      {modalResultado && <ModalResultado indicador={modalResultado} procesoId={id} onCerrar={() => setModalResultado(null)} onGuardado={() => { setModalResultado(null); cargar(ficha?.id).catch(() => {}) }} />}
      <Modal abierto={verHistorial} titulo={`Historial de la ficha de ${proceso.nombre}`} onCerrar={() => setVerHistorial(false)} ancho="max-w-2xl">
        {ficha && <Historial ficha={ficha} versiones={versiones} onElegir={(vid) => { setVerHistorial(false); cargar(vid).catch(() => {}) }} />}
      </Modal>
    </div>
  )
}

function Bloque({ titulo, children }) {
  return (
    <div>
      <p className="mb-2 rounded bg-[#2F5496] px-2 py-1 text-center text-[11px] font-semibold uppercase tracking-wide text-white">{titulo}</p>
      {children}
    </div>
  )
}

function Campo({ etiqueta, valor, editar, multilinea, clase = '' }) {
  return (
    <div className={clase}>
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{etiqueta}</p>
      {editar
        ? (multilinea
          ? <textarea className="input-esynapse" rows={2} value={valor || ''} onChange={(e) => editar(e.target.value)} />
          : <input className="input-esynapse" value={valor || ''} onChange={(e) => editar(e.target.value)} />)
        : <p className="whitespace-pre-line text-sm">{valor || '—'}</p>}
    </div>
  )
}

function nombresDe(ids, catalogo) {
  return (ids || []).map((pid) => catalogo.find((p) => p.id === pid)).filter(Boolean)
}

function TablaActividades({ filas, catalogo, onAbrir }) {
  const parte = (ids, otro) => (
    <>
      {nombresDe(ids, catalogo).map((p) => <button key={p.id} className="block w-full text-esynapse-600 hover:underline dark:text-esynapse-300" onClick={() => onAbrir(p.id)}>{p.nombre}</button>)}
      {otro && <span className="block">{otro}</span>}
    </>
  )
  return (
    <div className="overflow-x-auto">
      <table className="w-full table-fixed text-xs">
        <colgroup><col className="w-[12%]" /><col className="w-[16%]" /><col className="w-[18%]" /><col className="w-[24%]" /><col className="w-[12%]" /><col className="w-[18%]" /></colgroup>
        <thead className="bg-slate-50 text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
          <tr><th className="px-2 py-1.5">Proveedor</th><th className="px-2 py-1.5">Entrada</th><th className="px-2 py-1.5">Actividad</th><th className="px-2 py-1.5">Medida de control</th><th className="px-2 py-1.5">Cliente</th><th className="px-2 py-1.5">Salida</th></tr>
        </thead>
        <tbody>
          {filas.map((a) => [
            a.seccion && <tr key={`s${a.id}`}><td colSpan={6} className="bg-[#B4C6E7] px-2 py-1 font-semibold uppercase text-slate-800">{a.seccion}</td></tr>,
            <tr key={a.id} className="border-t border-slate-100 align-middle dark:border-slate-800">
              <td className="px-2 py-1.5">{parte(a.proveedores, a.proveedor_otro)}</td>
              <td className="whitespace-pre-line px-2 py-1.5">{a.entrada}</td>
              <td className="whitespace-pre-line px-2 py-1.5 font-medium">{a.actividad}</td>
              <td className="whitespace-pre-line px-2 py-1.5">{a.control}</td>
              <td className="px-2 py-1.5">{parte(a.clientes, a.cliente_otro)}</td>
              <td className="whitespace-pre-line px-2 py-1.5">{a.salida}</td>
            </tr>,
          ])}
        </tbody>
      </table>
    </div>
  )
}

function SelectorProcesos({ valor, catalogo, onChange }) {
  const elegidos = nombresDe(valor, catalogo)
  const raiz = catalogo.filter((p) => !p.padre && p.is_active)
  return (
    <div>
      <div className="mb-1 flex flex-wrap gap-1">
        {elegidos.map((p) => (
          <span key={p.id} className="inline-flex items-center gap-1 rounded bg-esynapse-500/12 px-1.5 py-0.5 text-[11px] text-esynapse-700 dark:text-esynapse-300">
            {p.nombre}<button type="button" onClick={() => onChange(valor.filter((x) => x !== p.id))}><X className="h-3 w-3" /></button>
          </span>
        ))}
      </div>
      <select className="input-esynapse !py-1 text-xs" value="" onChange={(e) => { const v = Number(e.target.value); if (v && !valor.includes(v)) onChange([...valor, v]) }}>
        <option value="">+ proceso…</option>
        {raiz.flatMap((p) => [
          <option key={p.id} value={p.id}>{p.nombre}</option>,
          ...catalogo.filter((s) => s.padre === p.id && s.is_active).map((s) => <option key={s.id} value={s.id}>{'   '}{s.nombre}</option>),
        ])}
      </select>
    </div>
  )
}

const mover = (lista, i, d) => {
  const j = i + d
  if (j < 0 || j >= lista.length) return lista
  const n = [...lista];
  [n[i], n[j]] = [n[j], n[i]]
  return n
}

function BotonesFila({ lista, i, onChange }) {
  return (
    <div className="flex gap-1">
      <button type="button" title="Subir" className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => onChange(mover(lista, i, -1))}><ArrowUp className="h-3.5 w-3.5" /></button>
      <button type="button" title="Bajar" className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => onChange(mover(lista, i, 1))}><ArrowDown className="h-3.5 w-3.5" /></button>
      <button type="button" title="Quitar" className="rounded p-1 text-red-500 hover:bg-red-500/10" onClick={() => onChange(lista.filter((_, k) => k !== i))}><Trash2 className="h-3.5 w-3.5" /></button>
    </div>
  )
}

function EditorActividades({ filas, catalogo, onChange }) {
  const set = (i, cambios) => onChange(filas.map((f, k) => (k === i ? { ...f, ...cambios } : f)))
  const area = (i, campo, ph) => <textarea className="input-esynapse !py-1 text-xs" rows={3} placeholder={ph} value={filas[i][campo] || ''} onChange={(e) => set(i, { [campo]: e.target.value })} />
  return (
    <div className="space-y-2">
      {filas.map((a, i) => (
        <div key={a.id || `n${i}`} className="rounded-lg border border-slate-200 p-2 dark:border-slate-700">
          <div className="mb-2 flex items-center justify-between gap-2">
            <input className="input-esynapse !py-1 text-xs" placeholder="Subtítulo de sección (opcional)" value={a.seccion || ''} onChange={(e) => set(i, { seccion: e.target.value })} />
            <span className="text-[11px] muted">#{i + 1}</span>
            <BotonesFila lista={filas} i={i} onChange={onChange} />
          </div>
          <div className="grid gap-2 md:grid-cols-6">
            <div><p className="text-[11px] muted">Proveedor</p><SelectorProcesos valor={a.proveedores || []} catalogo={catalogo} onChange={(v) => set(i, { proveedores: v })} />
              <input className="input-esynapse mt-1 !py-1 text-xs" placeholder="Otro: Cliente…" value={a.proveedor_otro || ''} onChange={(e) => set(i, { proveedor_otro: e.target.value })} /></div>
            <div><p className="text-[11px] muted">Entrada</p>{area(i, 'entrada')}</div>
            <div><p className="text-[11px] muted">Actividad *</p>{area(i, 'actividad')}</div>
            <div className="md:col-span-1"><p className="text-[11px] muted">Medida de control</p>{area(i, 'control')}</div>
            <div><p className="text-[11px] muted">Cliente</p><SelectorProcesos valor={a.clientes || []} catalogo={catalogo} onChange={(v) => set(i, { clientes: v })} />
              <input className="input-esynapse mt-1 !py-1 text-xs" placeholder="Otro: Cliente…" value={a.cliente_otro || ''} onChange={(e) => set(i, { cliente_otro: e.target.value })} /></div>
            <div><p className="text-[11px] muted">Salida</p>{area(i, 'salida')}</div>
          </div>
        </div>
      ))}
      <button type="button" className="btn-secondary !py-1 text-xs" onClick={() => onChange([...filas, { actividad: '', proveedores: [], clientes: [] }])}><Plus className="h-3.5 w-3.5" /> Agregar actividad</button>
    </div>
  )
}

function EditorDocumentos({ filas, docs, onChange }) {
  const set = (i, cambios) => onChange(filas.map((f, k) => (k === i ? { ...f, ...cambios } : f)))
  return (
    <div className="space-y-2">
      {filas.map((d, i) => (
        <div key={d.id || `n${i}`} className="space-y-1 rounded border border-slate-200 p-1.5 dark:border-slate-700">
          <div className="flex items-center gap-1">
            <select className="input-esynapse !py-1 text-xs" value={d.documento || ''} onChange={(e) => set(i, { documento: e.target.value ? Number(e.target.value) : null })}>
              <option value="">— Descrito (no está en la lista maestra) —</option>
              {docs.map((x) => <option key={x.id} value={x.id}>{x.codigo} — {x.titulo}</option>)}
            </select>
            <BotonesFila lista={filas} i={i} onChange={onChange} />
          </div>
          {!d.documento && <input className="input-esynapse !py-1 text-xs" placeholder="Nombre del documento" value={d.descripcion || ''} onChange={(e) => set(i, { descripcion: e.target.value })} />}
        </div>
      ))}
      <button type="button" className="btn-secondary !py-1 text-xs" onClick={() => onChange([...filas, { documento: null, descripcion: '' }])}><Plus className="h-3.5 w-3.5" /> Agregar documento</button>
    </div>
  )
}

function EditorLista({ filas, campo, placeholder, onChange }) {
  return (
    <div className="space-y-1.5">
      {filas.map((r, i) => (
        <div key={r.id || `n${i}`} className="flex items-center gap-1">
          <input className="input-esynapse !py-1 text-xs" placeholder={placeholder} value={r[campo] || ''} onChange={(e) => onChange(filas.map((f, k) => (k === i ? { ...f, [campo]: e.target.value } : f)))} />
          <BotonesFila lista={filas} i={i} onChange={onChange} />
        </div>
      ))}
      <button type="button" className="btn-secondary !py-1 text-xs" onClick={() => onChange([...filas, { [campo]: '' }])}><Plus className="h-3.5 w-3.5" /> Agregar</button>
    </div>
  )
}

function EditorIndicadores({ filas, onChange }) {
  const set = (i, cambios) => onChange(filas.map((f, k) => (k === i ? { ...f, ...cambios } : f)))
  return (
    <div className="space-y-2">
      {filas.map((x, i) => (
        <div key={x.id || `n${i}`} className="grid items-start gap-2 rounded border border-slate-200 p-2 md:grid-cols-[2fr_3fr_1fr_1fr_1.5fr_auto] dark:border-slate-700">
          <input className="input-esynapse !py-1 text-xs" placeholder="Nombre del indicador" value={x.nombre || ''} onChange={(e) => set(i, { nombre: e.target.value })} />
          <textarea className="input-esynapse !py-1 text-xs" rows={2} placeholder="Forma de cálculo" value={x.calculo || ''} onChange={(e) => set(i, { calculo: e.target.value })} />
          <input className="input-esynapse !py-1 text-xs" placeholder="Meta" value={x.meta || ''} onChange={(e) => set(i, { meta: e.target.value })} />
          <select className="input-esynapse !py-1 text-xs" value={x.frecuencia || 'mensual'} onChange={(e) => set(i, { frecuencia: e.target.value })}>{FRECUENCIAS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select>
          <input className="input-esynapse !py-1 text-xs" placeholder="Responsable" value={x.responsable || ''} onChange={(e) => set(i, { responsable: e.target.value })} />
          <BotonesFila lista={filas} i={i} onChange={onChange} />
        </div>
      ))}
      <button type="button" className="btn-secondary !py-1 text-xs" onClick={() => onChange([...filas, { nombre: '', frecuencia: 'mensual' }])}><Plus className="h-3.5 w-3.5" /> Agregar indicador</button>
    </div>
  )
}

function Vinculados({ v }) {
  const tarjeta = (titulo, valor, extra) => (
    <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
      <p className="text-[11px] muted">{titulo}</p>
      <p className="text-xl font-semibold">{valor} {extra && <span className="text-xs font-normal muted">{extra}</span>}</p>
    </div>
  )
  return (
    <div className="card-esynapse card-pad">
      <p className="mb-2 text-xs font-semibold muted">Vinculado a este proceso (se actualiza solo)</p>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        {tarjeta('Documentos', v.documentos.length, 'asignados en Documentos')}
        {tarjeta('No conformidades', v.nc_abiertas, 'abiertas')}
        {tarjeta('Acciones correctivas', v.sac_en_curso, 'en curso')}
        {tarjeta('Quejas', v.quejas_abiertas, `abiertas de ${v.quejas_total}`)}
        {tarjeta('Auditorías', v.auditorias_anio, 'este año')}
      </div>
      {v.documentos.length > 0 && <p className="mt-2 text-xs muted">{v.documentos.map((d) => `${d.codigo} ${d.titulo}`).join(' · ')}</p>}
      {v.hallazgos_abiertos.length > 0 && <p className="mt-1 text-xs muted">Hallazgos abiertos: {v.hallazgos_abiertos.map((h) => `${h.codigo} (${h.estado.toLowerCase()})`).join(', ')}</p>}
    </div>
  )
}

function ModalResultado({ indicador, procesoId, onCerrar, onGuardado }) {
  const hoy = new Date()
  const mesPasado = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)
  const [form, setForm] = useState({ periodo: `${mesPasado.getFullYear()}-${String(mesPasado.getMonth() + 1).padStart(2, '0')}`, valor: '', estado: '', comentario: '' })
  const [error, setError] = useState('')
  const guardar = async (e) => {
    e.preventDefault()
    if (!form.valor.trim() || !form.estado) { setError('Indique el resultado y si cumple la meta.'); return }
    try {
      await api.procesos.crearResultado({ proceso: procesoId, indicador: indicador.nombre, periodo: `${form.periodo}-01`, valor: form.valor, estado: form.estado, comentario: form.comentario })
      onGuardado()
    } catch (err) { setError(err.message) }
  }
  return (
    <Modal abierto titulo={`Resultado: ${indicador.nombre}`} onCerrar={onCerrar}>
      <form onSubmit={guardar} className="space-y-3">
        <p className="text-xs muted">Meta: {indicador.meta || '—'} · {indicador.frecuencia_display}</p>
        {error && <p className="rounded bg-red-500/10 p-2 text-xs text-red-600 dark:text-red-400">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div><label className={lbl}>Periodo</label><input type="month" className="input-esynapse" value={form.periodo} onChange={(e) => setForm({ ...form, periodo: e.target.value })} /></div>
          <div><label className={lbl}>Resultado</label><input className="input-esynapse" placeholder="87 %" value={form.valor} onChange={(e) => { setError(''); setForm({ ...form, valor: e.target.value }) }} /></div>
        </div>
        <div><label className={lbl}>Frente a la meta</label>
          <select className="input-esynapse" value={form.estado} onChange={(e) => { setError(''); setForm({ ...form, estado: e.target.value }) }}>
            <option value="">— Elige —</option><option value="cumple">Cumple</option><option value="en_riesgo">En riesgo</option><option value="no_cumple">No cumple</option>
          </select></div>
        <div><label className={lbl}>Comentario</label><textarea className="input-esynapse" rows={2} value={form.comentario} onChange={(e) => setForm({ ...form, comentario: e.target.value })} /></div>
        <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onCerrar}>Cancelar</button><button className="btn-primary"><Save className="h-4 w-4" /> Guardar</button></div>
      </form>
    </Modal>
  )
}

function Historial({ ficha, versiones, onElegir }) {
  const firmas = useMemo(() => ficha.firmas || [], [ficha])
  return (
    <div className="space-y-4 text-sm">
      <div>
        <p className="mb-1 text-xs font-semibold muted">Firmas de la versión {ficha.version}</p>
        {firmas.length === 0 && <p className="text-xs muted">Aún sin firmas.</p>}
        {firmas.map((f) => (
          <p key={f.rol} className="text-xs"><strong>{ROL_FIRMA[f.rol]}:</strong> {f.nombre}{f.sigla ? ` (${f.sigla})` : ''} · {fechaHora(f.fecha)}</p>
        ))}
        {ficha.hash_contenido && <p className="mt-1 break-all text-[11px] muted">Huella del contenido aprobado: {ficha.hash_contenido}</p>}
      </div>
      {ficha.devoluciones?.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold muted">Devoluciones</p>
          {ficha.devoluciones.map((d, i) => <p key={i} className="text-xs">{fechaHora(d.fecha)} · {d.usuario} ({d.etapa}): {d.comentarios}</p>)}
        </div>
      )}
      <div>
        <p className="mb-1 text-xs font-semibold muted">Versiones</p>
        <table className="tabla-ficha w-full text-xs">
          <thead className="text-slate-500"><tr><th className="py-1">Versión</th><th className="py-1 text-center">Estado</th><th className="py-1">Motivo</th><th className="py-1 text-right">Aprobada</th></tr></thead>
          <tbody>
            {versiones.map((v) => (
              <tr key={v.id} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50" onClick={() => onElegir(v.id)}>
                <td className="py-1.5 font-medium">{v.version}</td>
                <td className="py-1.5 text-center"><Badge tono={TONO_FICHA[v.estado]}>{v.estado_display}</Badge></td>
                <td className="py-1.5">{v.motivo_cambio || '—'}</td>
                <td className="py-1.5 text-right">{v.fecha_aprobacion ? fecha(v.fecha_aprobacion) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
