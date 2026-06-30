import { useCallback, useEffect, useState } from 'react'
import {
  Gauge, Plus, Search, Power, Trash2, Paperclip, RotateCcw, Truck, FileText, SlidersHorizontal,
  ClipboardCheck, Check, X,
} from 'lucide-react'
import Modal from '../components/Modal.jsx'
import GestionCatalogoEquipo from '../components/ui/GestionCatalogoEquipo.jsx'
import ProgramaAnual from './ProgramaAnual.jsx'
import Trazabilidad from './Trazabilidad.jsx'
import IntervaloCalibracion from './IntervaloCalibracion.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fechaHora } from '../lib/fecha.js'

const MAGNITUDES = [
  ['masa', 'Masa'], ['temperatura', 'Temperatura'], ['electricidad', 'Electricidad'],
  ['presion', 'Presión'], ['longitud', 'Longitud'], ['grandes_volumenes', 'Grandes Volúmenes y Flujo'],
  ['analisis_quimico', 'Análisis Químico'],
]
const CLASIFICACIONES = [
  ['patron_referencia', 'Patrón de Referencia'], ['patron_verificacion', 'Patrón de Verificación'],
  ['patron_trabajo', 'Patrón de Trabajo'], ['equipamiento', 'Equipamiento Auxiliar'],
]
const ESTADOS = [['operativo', 'Operativo'], ['calibrado', 'Calibrado'], ['inoperativo', 'Inoperativo'], ['baja', 'De baja']]
// Regla 10 CLAUDE.md — colores semánticos de estado
const COLOR_ESTADO = {
  Operativo: 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  Calibrado: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  'Inoperativo / Fuera de servicio': 'bg-red-500/15 text-red-600 dark:text-red-400',
  'De baja': 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
}
const MOTIVOS = [['campo', 'Campo'], ['calibracion', 'Calibración'], ['reparacion', 'Reparación'], ['prestamo', 'Préstamo'], ['mantenimiento', 'Mantenimiento'], ['otros', 'Otros']]
const FISICOS = [['bueno', 'Bueno'], ['regular', 'Regular'], ['malo', 'Malo']]
const TIPOS_ACTIVIDAD = [['mantenimiento', 'Mantenimiento'], ['calibracion', 'Calibración'], ['comprobacion_intermedia', 'Comprobación Intermedia'], ['comprobacion_funcional', 'Comprobación Funcional'], ['caracterizacion', 'Caracterización']]

// Pestañas de la Hoja de Vida
const PESTANAS = [
  ['ficha', 'Ficha Técnica'],
  ['mantenimiento', 'Mantenimientos'],
  ['calibracion', 'Calibraciones'],
  ['verificacion', 'Verificaciones'],
  ['comprobacion_intermedia', 'Comprob. Intermedias'],
  ['caracterizacion', 'Caracterizaciones'],
  ['suceso', 'Historial'],
]
const TIPOS_REGISTRO = ['calibracion', 'mantenimiento', 'verificacion', 'comprobacion_intermedia', 'caracterizacion', 'suceso']

const FORM_VACIO = {
  codigo: '', magnitud: 'Masa', clasificacion: 'Equipamiento Auxiliar', nombre: '', marca: '', modelo: '', serie: '',
  procedencia: '', laboratorio: '', requiere_calibracion: true, intervalo_indicacion: '',
  clase_exactitud: '', resolucion: '', division_escala: '', cantidad: '', material: '', tipo_indicacion: '',
  instructivo: '', manual: '', criterio_aceptacion: '', exactitud_asignada: '', inicio_servicio: '',
  n_certificado: '', proveedor_calibracion: '', periodicidad_dias: '', fecha_ultima_calibracion: '',
  observaciones: '',
}
const REG_VACIO = { frecuencia: '', numero_documento: '', descripcion: '', fecha: '', fecha_proxima: '', observaciones: '', vb: '' }

function badgeCalib(eq) {
  if (!eq.requiere_calibracion) return ['No aplica', 'bg-slate-500/15 text-slate-500 dark:text-slate-400']
  if (eq.calibracion_vigente === true) return ['Vigente', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400']
  if (eq.calibracion_vigente === false) return ['Vencida', 'bg-red-500/15 text-red-600 dark:text-red-400']
  return ['Sin calibrar', 'bg-amber-500/15 text-amber-600 dark:text-amber-400']
}

// Próxima fecha = fecha + frecuencia (texto libre: "12 meses", "Anual", "6 meses", "365 días", "2 años"...)
function calcularProximaFecha(fecha, frecuencia) {
  if (!fecha || !frecuencia) return ''
  const txt = String(frecuencia).toLowerCase().trim()
  const num = parseInt((txt.match(/\d+/) || [])[0] || '0', 10)
  let dias = 0, meses = 0
  if (/quincenal/.test(txt)) dias = 15
  else if (/mensual/.test(txt)) meses = 1
  else if (/bimestral/.test(txt)) meses = 2
  else if (/trimestral/.test(txt)) meses = 3
  else if (/cuatrimestral/.test(txt)) meses = 4
  else if (/semestral/.test(txt)) meses = 6
  else if (/anual/.test(txt)) meses = 12
  else if (/bienal/.test(txt)) meses = 24
  else if (/d[ií]a/.test(txt)) dias = num
  else if (/semana/.test(txt)) dias = num * 7
  else if (/a[ñn]o/.test(txt)) meses = num * 12
  else if (/mes/.test(txt)) meses = num
  else if (num) meses = num
  if (!dias && !meses) return ''
  const d = new Date(`${fecha}T00:00:00`)
  if (Number.isNaN(d.getTime())) return ''
  d.setMonth(d.getMonth() + meses)
  d.setDate(d.getDate() + dias)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

function Campo({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>
      {children}
    </label>
  )
}

export default function Equipos() {
  const { tienePermiso } = useAuth()
  const confirmar = useConfirm()
  const [items, setItems] = useState([])
  const [buscar, setBuscar] = useState('')
  const [laboratorio, setLaboratorio] = useState('')
  const [labs, setLabs] = useState([])
  const [vista, setVista] = useState(() => localStorage.getItem('equipos_vista') || 'inventario')
  const [estado, setEstado] = useState('')
  const [soloVencidos, setSoloVencidos] = useState(false)
  const [modalCrear, setModalCrear] = useState(false)
  const [detalle, setDetalle] = useState(null)
  const [tab, setTab] = useState('ficha')
  const [form, setForm] = useState(FORM_VACIO)
  const [error, setError] = useState('')
  const [ficha, setFicha] = useState({})
  const [regForm, setRegForm] = useState(REG_VACIO)
  const [regFile, setRegFile] = useState(null)
  const [movForm, setMovForm] = useState({ motivo: 'calibracion', destino: '', solicitante: '', estado_salida: 'bueno', responsable_salida: '' })
  const [actForm, setActForm] = useState({ tipo: 'calibracion', anio: new Date().getFullYear(), frecuencia: '' })
  const [catMag, setCatMag] = useState([])
  const [catClas, setCatClas] = useState([])
  const [modalCat, setModalCat] = useState(false)
  const [modalFuera, setModalFuera] = useState(false)
  const [motivoFuera, setMotivoFuera] = useState('')
  const [pendientes, setPendientes] = useState([])
  const [modalPend, setModalPend] = useState(false)
  const [misSolic, setMisSolic] = useState([])
  const [modalMis, setModalMis] = useState(false)
  const [misDevueltas, setMisDevueltas] = useState(0)

  const cargarCatalogos = useCallback(() => {
    api.magnitudesEquipo.listar().then((d) => setCatMag(d.results ?? d)).catch(() => {})
    api.clasificacionesEquipo.listar().then((d) => setCatClas(d.results ?? d)).catch(() => {})
    api.equipos.laboratorios().then((d) => setLabs(d.results ?? d)).catch(() => {})
  }, [])
  useEffect(() => { cargarCatalogos() }, [cargarCatalogos])
  useEffect(() => { localStorage.setItem('equipos_vista', vista) }, [vista])

  const cargar = useCallback(async () => {
    const p = new URLSearchParams()
    if (buscar) p.set('buscar', buscar)
    if (laboratorio) p.set('laboratorio', laboratorio)
    if (estado) p.set('estado', estado)
    if (soloVencidos) p.set('vencidos', '1')
    const d = await api.equipos.listar(`?${p}`)
    setItems(d.results ?? d)
  }, [buscar, laboratorio, estado, soloVencidos])
  useEffect(() => { cargar().catch(() => {}) }, [cargar])

  const abrir = async (id) => {
    setError(''); setTab('ficha'); setRegForm(REG_VACIO); setRegFile(null)
    const d = await api.equipos.detalle(id)
    setDetalle(d); setFicha(d)
  }
  const refrescar = async () => { await cargar(); if (detalle) setDetalle(await api.equipos.detalle(detalle.id)) }
  const accion = async (fn) => {
    setError('')
    try {
      const r = await fn()
      if (r?.pendiente) {
        cargarPendientes()
        await confirmar({
          titulo: 'Cambio pendiente de aprobación',
          mensaje: r.detail || 'El cambio quedó registrado y pendiente de aprobación por un supervisor.',
          textoConfirmar: 'Entendido', textoCancelar: 'Cerrar',
        })
      }
      await refrescar()
    } catch (e) { setError(e.message) }
  }

  const crear = async (e) => {
    e.preventDefault(); setError('')
    if (!form.codigo.trim()) { setError('El código es obligatorio. Lo asigna el laboratorio (p. ej. M-001).'); return }
    try {
      const datos = { ...form }
      // Quita opcionales vacíos de tipo fecha/número (el backend rechaza '')
      ;['inicio_servicio', 'fecha_ultima_calibracion', 'periodicidad_dias'].forEach((k) => {
        if (!datos[k]) delete datos[k]
      })
      const resp = await api.equipos.crear(datos)
      setModalCrear(false); setForm(FORM_VACIO)
      if (resp?.pendiente) {
        cargarPendientes()
        await confirmar({
          titulo: 'Alta pendiente de aprobación',
          mensaje: resp.detail || 'El alta quedó registrada y pendiente de aprobación por un supervisor.',
          textoConfirmar: 'Entendido', textoCancelar: 'Cerrar',
        })
      } else {
        await cargar()
      }
    } catch (e2) { setError(e2.message) }
  }

  const guardarFicha = async () => {
    setError('')
    const campos = ['codigo', 'magnitud', 'clasificacion', 'nombre', 'marca', 'modelo', 'serie', 'procedencia', 'laboratorio',
      'intervalo_indicacion', 'division_escala', 'clase_exactitud', 'resolucion', 'cantidad', 'cantidad_unidades', 'material',
      'tipo_indicacion', 'instructivo', 'manual', 'criterio_aceptacion',
      'proveedor_calibracion', 'observaciones', 'requiere_calibracion']
    const datos = {}; campos.forEach((k) => { datos[k] = ficha[k] ?? '' })
    if (ficha.inicio_servicio) datos.inicio_servicio = ficha.inicio_servicio
    try {
      const resp = await api.equipos.actualizar(detalle.id, datos)
      setDetalle(null)
      if (resp?.pendiente) {
        cargarPendientes()
        await confirmar({
          titulo: 'Cambio pendiente de aprobación',
          mensaje: resp.detail || 'El cambio quedó registrado y pendiente de aprobación por un supervisor.',
          textoConfirmar: 'Entendido', textoCancelar: 'Cerrar',
        })
      } else {
        await cargar()
      }
    } catch (e) { setError(e.message) }
  }

  const agregarRegistro = (tipo) => accion(async () => {
    if (tipo !== 'suceso' && !regFile) {
      throw new Error('El documento adjunto es obligatorio para este registro.')
    }
    const fd = new FormData()
    fd.append('tipo', tipo)
    Object.entries(regForm).forEach(([k, v]) => { if (v !== '' && v != null) fd.append(k, v) })
    if (regFile) fd.append('archivo', regFile)
    const resp = await api.equipos.agregarRegistro(detalle.id, fd)
    setRegForm(REG_VACIO); setRegFile(null)
    return resp
  })

  const eliminarRegistro = async (rid) => {
    if (!await confirmar({ titulo: 'Eliminar registro', mensaje: '¿Eliminar este registro de la bitácora?', textoConfirmar: 'Eliminar', peligro: true })) return
    accion(() => api.equipos.eliminarRegistro(detalle.id, rid))
  }

  const subirImagen = (file) => accion(async () => {
    const fd = new FormData(); fd.append('imagen', file)
    const resp = await api.equipos.subirImagen(detalle.id, fd)
    if (resp?.pendiente) {
      cargarPendientes()
      await confirmar({
        titulo: 'Cambio pendiente de aprobación',
        mensaje: resp.detail || 'La imagen quedó pendiente de aprobación por un supervisor.',
        textoConfirmar: 'Entendido', textoCancelar: 'Cerrar',
      })
    }
  })

  const verFichaPdf = async () => {
    setError('')
    try {
      const blob = await api.equipos.fichaPdf(detalle.id)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  const imprimirBitacora = async (tipo, titulo) => {
    setError('')
    try {
      const blob = await api.equipos.bitacoraPdf(detalle.id, tipo, titulo)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  const imprimirInventario = async () => {
    setError('')
    try {
      const p = new URLSearchParams()
      if (buscar) p.set('buscar', buscar)
      if (laboratorio) p.set('laboratorio', laboratorio)
      if (estado) p.set('estado', estado)
      if (soloVencidos) p.set('vencidos', '1')
      const blob = await api.equipos.inventarioPdf(`?${p}`)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  const puedeEditar = tienePermiso('equipos', 'editar')
  const puedeEliminar = tienePermiso('equipos', 'eliminar')
  const puedeAprobar = tienePermiso('equipos', 'aprobar')

  const cargarPendientes = useCallback(() => {
    if (!tienePermiso('equipos', 'aprobar')) return
    api.solicitudesEquipo.listar('?estado=pendiente').then((d) => setPendientes(d.results ?? d)).catch(() => {})
  }, [tienePermiso])
  useEffect(() => { cargarPendientes() }, [cargarPendientes])

  const cargarMisSolicitudes = useCallback(() => {
    api.solicitudesEquipo.listar('?estado=todas&mias=1').then((d) => setMisSolic(d.results ?? d)).catch(() => {})
    api.solicitudesEquipo.misDevueltasCount().then((d) => setMisDevueltas(d.devueltas || 0)).catch(() => {})
  }, [])
  useEffect(() => { cargarMisSolicitudes() }, [cargarMisSolicitudes])

  const reenviarSolicitud = async (sol) => {
    if (!await confirmar({
      titulo: 'Reenviar a aprobación',
      mensaje: `¿Reenviar el cambio “${sol.resumen}” para aprobación del supervisor?`,
      textoConfirmar: 'Reenviar',
    })) return
    try {
      await api.solicitudesEquipo.reenviar(sol.id)
      cargarMisSolicitudes(); cargarPendientes()
    } catch (e) { setError(e.message) }
  }

  const resolverSolicitud = async (sol, tipo) => {
    // tipo: 'aprobar' | 'devolver' | 'rechazar'
    let obs = ''
    if (tipo === 'aprobar') {
      const ok = await confirmar({
        titulo: 'Aprobar cambio',
        mensaje: `¿Aprobar y aplicar el cambio “${sol.resumen}” solicitado por ${sol.solicitante}?`,
        textoConfirmar: 'Aprobar',
      })
      if (!ok) return
    } else {
      obs = window.prompt(
        tipo === 'devolver'
          ? 'Motivo de la devolución (indica qué se debe corregir):'
          : 'Motivo del rechazo (opcional):', '')
      if (obs === null) return  // canceló el prompt
    }
    try {
      if (tipo === 'aprobar') await api.solicitudesEquipo.aprobar(sol.id)
      else if (tipo === 'devolver') await api.solicitudesEquipo.devolver(sol.id, obs)
      else await api.solicitudesEquipo.rechazar(sol.id, obs)
      cargarPendientes(); await cargar()
    } catch (e) { setError(e.message) }
  }

  const registros = (detalle?.registros || [])
  const porTipo = (t) => registros.filter((r) => r.tipo === t)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Gauge className="h-6 w-6 text-esynapse-500" />
          <div>
            <h1 className="text-2xl font-bold">Equipos e Instrumentos</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Inventario y hoja de vida del equipamiento del laboratorio</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {puedeAprobar && (
            <button onClick={() => { cargarPendientes(); setModalPend(true) }} className="btn-secondary" title="Revisar cambios pendientes de aprobación">
              <ClipboardCheck className="h-4 w-4" /> Cambios pendientes
              {pendientes.length > 0 && (
                <span className="ml-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-amber-500 px-1 text-xs font-semibold text-white">{pendientes.length}</span>
              )}
            </button>
          )}
          {puedeEditar && (
            <button onClick={() => { cargarMisSolicitudes(); setModalMis(true) }} className="btn-secondary" title="Ver el estado de mis cambios enviados">
              <ClipboardCheck className="h-4 w-4" /> Mis solicitudes
              {misDevueltas > 0 && (
                <span className="ml-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-violet-500 px-1 text-xs font-semibold text-white">{misDevueltas}</span>
              )}
            </button>
          )}
          {puedeEditar && (
            <button onClick={() => setModalCat(true)} className="btn-secondary" title="Gestionar magnitudes y clasificaciones">
              <SlidersHorizontal className="h-4 w-4" /> Catálogos
            </button>
          )}
          {tienePermiso('equipos', 'crear') && (
            <button onClick={() => { setForm(FORM_VACIO); setError(''); setModalCrear(true) }} className="btn-primary">
              <Plus className="h-4 w-4" /> Nuevo equipo
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1 border-b border-slate-200 dark:border-slate-800">
        <button onClick={() => setVista('inventario')} className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition ${vista === 'inventario' ? 'border-esynapse-500 text-esynapse-600 dark:text-esynapse-300' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'}`}>Inventario</button>
        <button onClick={() => setVista('programa')} className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition ${vista === 'programa' ? 'border-esynapse-500 text-esynapse-600 dark:text-esynapse-300' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'}`}>Programa Anual</button>
        <button onClick={() => setVista('intervalo')} className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition ${vista === 'intervalo' ? 'border-esynapse-500 text-esynapse-600 dark:text-esynapse-300' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'}`}>Intervalo de Calibración</button>
        <button onClick={() => setVista('trazabilidad')} className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition ${vista === 'trazabilidad' ? 'border-esynapse-500 text-esynapse-600 dark:text-esynapse-300' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'}`}>Carta de Trazabilidad</button>
      </div>

      {vista === 'programa' && <ProgramaAnual puedeEditar={puedeEditar} />}

      {vista === 'trazabilidad' && <Trazabilidad puedeEditar={puedeEditar} />}

      {vista === 'intervalo' && <IntervaloCalibracion puedeEditar={puedeEditar} />}

      {vista === 'inventario' && (<>
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input-esynapse w-56 pl-9" placeholder="Buscar código, nombre, serie…" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <select className="input-esynapse w-52" value={laboratorio} onChange={(e) => setLaboratorio(e.target.value)}>
          <option value="">Todos los laboratorios</option>
          {labs.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <select className="input-esynapse w-40" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={soloVencidos} onChange={(e) => setSoloVencidos(e.target.checked)} className="h-4 w-4 accent-esynapse-600" />
          Solo calibración vencida
        </label>
        <button onClick={imprimirInventario} className="btn-secondary ml-auto" title="Generar PDF del inventario (respeta los filtros)">
          <FileText className="h-4 w-4" /> Inventario PDF
        </button>
      </div>

      {/* INVENTARIO — vista general */}
      <div className="card-esynapse overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-center text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-3 py-3">Código</th>
              <th className="px-3 py-3">Descripción</th>
              <th className="px-3 py-3">Clasificación</th>
              <th className="px-3 py-3">Marca</th>
              <th className="px-3 py-3">Modelo</th>
              <th className="px-3 py-3">N° Serie</th>
              <th className="px-3 py-3">Alcance / Valor nominal</th>
              <th className="px-3 py-3">Clase</th>
              <th className="px-3 py-3">Resolución / División de escala (d) / verificación (e)</th>
              <th className="px-3 py-3">N° Certificado</th>
              <th className="px-3 py-3">Period. (días)</th>
              <th className="px-3 py-3">Últ. calib.</th>
              <th className="px-3 py-3">Calib. requerida</th>
              <th className="px-3 py-3">Estado</th>
              <th className="px-3 py-3">Proveedor calib.</th>
              <th className="px-3 py-3">Observaciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((e) => {
              const bc = badgeCalib(e)
              return (
                <tr key={e.id} onClick={() => abrir(e.id)} className="cursor-pointer border-b border-slate-100 text-center align-middle transition last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                  <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs font-semibold text-esynapse-600 dark:text-esynapse-300">{e.codigo}</td>
                  <td className="min-w-[12rem] max-w-[18rem] whitespace-normal break-words px-3 py-2.5" title={e.nombre}>{e.nombre}</td>
                  <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{e.clasificacion_display}</td>
                  <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400">{e.marca || '—'}</td>
                  <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400">{e.modelo || '—'}</td>
                  <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{e.serie || '—'}</td>
                  <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{e.cantidad || '—'}</td>
                  <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{e.clase_exactitud || '—'}</td>
                  <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{e.resolucion || '—'}</td>
                  <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{e.n_certificado || '—'}</td>
                  <td className="px-3 py-2.5 text-center text-xs text-slate-500 dark:text-slate-400">{e.periodicidad_dias || '—'}</td>
                  <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{e.fecha_ultima_calibracion || '—'}</td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-xs">
                    <span className="text-slate-500 dark:text-slate-400">{e.fecha_proxima_calibracion || '—'}</span>
                    {bc && <span className={`ml-1.5 rounded px-1.5 py-0.5 text-[10px] font-medium ${bc[1]}`}>{bc[0]}</span>}
                  </td>
                  <td className="px-3 py-2.5"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${COLOR_ESTADO[e.estado_display] || ''}`}>{e.estado_display}</span></td>
                  <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{e.proveedor_calibracion || '—'}</td>
                  <td className="min-w-[12rem] max-w-[18rem] whitespace-normal break-words px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400" title={e.observaciones || ''}>{e.observaciones || '—'}</td>
                </tr>
              )
            })}
            {items.length === 0 && (
              <tr><td colSpan={16} className="px-4 py-10 text-center text-slate-400">No hay equipos que coincidan con el filtro.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      </>)}

      {/* ALTA DE EQUIPO — el código lo asigna el usuario */}
      <Modal abierto={modalCrear} titulo="Nuevo equipo" onCerrar={() => setModalCrear(false)} ancho="max-w-2xl">
        <form onSubmit={crear} className="space-y-3">
          {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <Campo label="Código *">
              <input className="input-esynapse font-mono" placeholder="M-001" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} required />
            </Campo>
            <Campo label="Descripción *">
              <input className="input-esynapse" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
            </Campo>
            <Campo label="Clasificación">
              <select className="input-esynapse" value={form.clasificacion} onChange={(e) => setForm({ ...form, clasificacion: e.target.value })}>
                {!catClas.some((c) => c.nombre === form.clasificacion) && form.clasificacion && <option value={form.clasificacion}>{form.clasificacion}</option>}
                {catClas.map((c) => <option key={c.id} value={c.nombre}>{c.nombre}</option>)}
              </select>
            </Campo>
            <Campo label="Marca"><input className="input-esynapse" value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })} /></Campo>
            <Campo label="Modelo"><input className="input-esynapse" value={form.modelo} onChange={(e) => setForm({ ...form, modelo: e.target.value })} /></Campo>
            <Campo label="N° de serie"><input className="input-esynapse" value={form.serie} onChange={(e) => setForm({ ...form, serie: e.target.value })} /></Campo>
            <Campo label="Alcance / Valor nominal"><input className="input-esynapse" value={form.cantidad} onChange={(e) => setForm({ ...form, cantidad: e.target.value })} /></Campo>
            <Campo label="Clase / Exactitud"><input className="input-esynapse" value={form.clase_exactitud} onChange={(e) => setForm({ ...form, clase_exactitud: e.target.value })} /></Campo>
            <Campo label="Resolución / División de escala (d) / verificación (e)"><input className="input-esynapse" value={form.resolucion} onChange={(e) => setForm({ ...form, resolucion: e.target.value })} /></Campo>
            <Campo label="N° de certificado de calibración"><input className="input-esynapse" value={form.n_certificado} onChange={(e) => setForm({ ...form, n_certificado: e.target.value })} /></Campo>
            <Campo label="Periodicidad de calibración (días)"><input type="number" min="0" className="input-esynapse" value={form.periodicidad_dias} onChange={(e) => setForm({ ...form, periodicidad_dias: e.target.value })} /></Campo>
            <Campo label="Fecha de última calibración"><input type="date" className="input-esynapse" value={form.fecha_ultima_calibracion} onChange={(e) => setForm({ ...form, fecha_ultima_calibracion: e.target.value })} /></Campo>
            <Campo label="Proveedor de calibración"><input className="input-esynapse" value={form.proveedor_calibracion} onChange={(e) => setForm({ ...form, proveedor_calibracion: e.target.value })} /></Campo>
          </div>
          <Campo label="Observaciones"><textarea className="input-esynapse h-16" value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} /></Campo>
          <p className="text-xs text-slate-400">La próxima calibración se calcula con la fecha de última calibración y la periodicidad; aparecerá en la pestaña Calibraciones de la hoja de vida.</p>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.requiere_calibracion} onChange={(e) => setForm({ ...form, requiere_calibracion: e.target.checked })} className="h-4 w-4 accent-esynapse-600" />
            Requiere calibración (el equipo influye en el resultado de las mediciones)
          </label>
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={() => setModalCrear(false)} className="btn-ghost">Cancelar</button>
            <button type="submit" className="btn-primary">Registrar equipo</button>
          </div>
        </form>
      </Modal>

      {/* GESTIÓN DE CATÁLOGOS DEL MÓDULO — magnitudes y clasificaciones */}
      <Modal abierto={modalCat} titulo="Catálogos de Equipos" onCerrar={() => setModalCat(false)} ancho="max-w-3xl">
        <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
          Estas listas alimentan los desplegables de Magnitud y Clasificación. Renombra para corregir,
          quita las que sobran o agrega nuevas. Quitar solo la oculta del desplegable; no afecta a los equipos que ya la usan.
        </p>
        <div className="grid gap-6 md:grid-cols-2">
          <GestionCatalogoEquipo
            fuente={api.magnitudesEquipo} titulo="Magnitudes" singular="magnitud" conPrefijo
            nota="El prefijo define el código del equipo (ej. M → M-001)."
            onCambio={cargarCatalogos} />
          <GestionCatalogoEquipo
            fuente={api.clasificacionesEquipo} titulo="Clasificaciones" singular="clasificación"
            nota="Toda clasificación cuyo nombre contenga «Patrón» se trata como patrón (regla de patrón vigente)."
            onCambio={cargarCatalogos} />
        </div>
        <div className="mt-5 flex justify-end">
          <button type="button" onClick={() => setModalCat(false)} className="btn-primary">Listo</button>
        </div>
      </Modal>

      {/* HOJA DE VIDA — modal con pestañas que calcan el Excel */}
      <Modal abierto={!!detalle} titulo={detalle ? detalle.nombre : ''} onCerrar={() => setDetalle(null)} ancho="max-w-5xl">
        {detalle && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${COLOR_ESTADO[detalle.estado_display] || ''}`}>{detalle.estado_display}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">{detalle.magnitud_display} · {detalle.clasificacion_display}</span>
              <div className="ml-auto flex gap-2">
                {puedeEditar && detalle.estado !== 'baja' && detalle.estado !== 'inoperativo' && (
                  <button onClick={() => { setMotivoFuera(''); setModalFuera(true) }} className="btn-ghost text-xs"><Power className="h-3.5 w-3.5" /> Fuera de servicio</button>
                )}
                {puedeEditar && (detalle.estado === 'inoperativo' || detalle.estado === 'baja') && (
                  <button onClick={async () => { if (await confirmar({ titulo: 'Reactivar equipo', mensaje: '¿Reactivar el equipo y volverlo a estado operativo?', textoConfirmar: 'Reactivar' })) accion(() => api.equipos.reactivar(detalle.id)) }} className="btn-ghost text-xs"><RotateCcw className="h-3.5 w-3.5" /> Reactivar</button>
                )}
                {puedeEliminar && detalle.estado !== 'baja' && (
                  <button onClick={async () => { if (await confirmar({ titulo: 'Dar de baja', mensaje: '¿Dar de baja el equipo? Esta acción cambia su estado a inactivo.', textoConfirmar: 'Dar de baja', peligro: true })) accion(() => api.equipos.darBaja(detalle.id)) }} className="btn-ghost text-xs text-red-500"><Trash2 className="h-3.5 w-3.5" /> Dar de baja</button>
                )}
              </div>
            </div>

            {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</p>}

            {/* Navegación por pestañas */}
            <div className="flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800">
              {PESTANAS.map(([v, n]) => (
                <button key={v} onClick={() => { setTab(v); setRegForm(REG_VACIO); setRegFile(null) }}
                  className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition ${tab === v ? 'border-esynapse-500 text-esynapse-600 dark:text-esynapse-300' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}>
                  {n}
                </button>
              ))}
            </div>

            {/* FICHA TÉCNICA */}
            {tab === 'ficha' && (
              <div className="space-y-4">
                {/* DATOS GENERALES */}
                <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
                  <div className="bg-[#1E3A5C] px-4 py-2 text-sm font-bold uppercase tracking-wide text-white">Datos Generales</div>
                  <div className="p-4">
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                    <Campo label="Nombre del equipo"><input className="input-esynapse" value={ficha.nombre || ''} onChange={(e) => setFicha({ ...ficha, nombre: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Clasificación">
                      <select className="input-esynapse" value={ficha.clasificacion || 'Equipamiento Auxiliar'} onChange={(e) => setFicha({ ...ficha, clasificacion: e.target.value })} disabled={!puedeEditar}>
                        {ficha.clasificacion && !catClas.some((c) => c.nombre === ficha.clasificacion) && <option value={ficha.clasificacion}>{ficha.clasificacion}</option>}
                        {catClas.map((c) => <option key={c.id} value={c.nombre}>{c.nombre}</option>)}
                      </select>
                    </Campo>
                    <Campo label="Magnitud">
                      <select className="input-esynapse" value={ficha.magnitud || ''} onChange={(e) => setFicha({ ...ficha, magnitud: e.target.value })} disabled={!puedeEditar}>
                        {ficha.magnitud && !catMag.some((m) => m.nombre === ficha.magnitud) && <option value={ficha.magnitud}>{ficha.magnitud}</option>}
                        {catMag.map((m) => <option key={m.id} value={m.nombre}>{m.nombre}</option>)}
                      </select>
                    </Campo>
                    <Campo label="Código"><input className="input-esynapse font-mono" value={ficha.codigo || ''} onChange={(e) => setFicha({ ...ficha, codigo: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Inicio de servicio (año)"><input type="number" min="1900" max="2100" placeholder="2024" className="input-esynapse" value={(ficha.inicio_servicio || '').split('-')[0]} onChange={(e) => { const y = e.target.value.replace(/\D/g, '').slice(0, 4); setFicha({ ...ficha, inicio_servicio: y ? `${y}-01-01` : '' }) }} disabled={!puedeEditar} /></Campo>
                    <Campo label="Estado"><input className="input-esynapse" value={ficha.estado_display || ''} disabled /></Campo>
                  </div>
                  </div>
                </div>

                {/* ESPECIFICACIONES TÉCNICAS */}
                <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
                  <div className="bg-[#1E3A5C] px-4 py-2 text-sm font-bold uppercase tracking-wide text-white">Especificaciones Técnicas</div>
                  <div className="p-4">
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                    <Campo label="Marca"><input className="input-esynapse" value={ficha.marca || ''} onChange={(e) => setFicha({ ...ficha, marca: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Modelo"><input className="input-esynapse" value={ficha.modelo || ''} onChange={(e) => setFicha({ ...ficha, modelo: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="N° de serie"><input className="input-esynapse" value={ficha.serie || ''} onChange={(e) => setFicha({ ...ficha, serie: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Procedencia"><input className="input-esynapse" value={ficha.procedencia || ''} onChange={(e) => setFicha({ ...ficha, procedencia: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Tipo de indicación"><input className="input-esynapse" value={ficha.tipo_indicacion || ''} onChange={(e) => setFicha({ ...ficha, tipo_indicacion: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Ubicación / Laboratorio"><input className="input-esynapse" value={ficha.laboratorio || ''} onChange={(e) => setFicha({ ...ficha, laboratorio: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Alcance / Valor nominal"><input className="input-esynapse" value={ficha.cantidad || ''} onChange={(e) => setFicha({ ...ficha, cantidad: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Resolución / División de escala (d) / verificación (e)"><input className="input-esynapse" value={ficha.resolucion || ''} onChange={(e) => setFicha({ ...ficha, resolucion: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Clase de exactitud"><input className="input-esynapse" value={ficha.clase_exactitud || ''} onChange={(e) => setFicha({ ...ficha, clase_exactitud: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Cantidad"><input className="input-esynapse" value={ficha.cantidad_unidades || ''} onChange={(e) => setFicha({ ...ficha, cantidad_unidades: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Material"><input className="input-esynapse" value={ficha.material || ''} onChange={(e) => setFicha({ ...ficha, material: e.target.value })} disabled={!puedeEditar} /></Campo>
                    <Campo label="Instructivo"><label className="flex items-center gap-2 py-2 text-sm"><input type="checkbox" checked={!!ficha.instructivo} onChange={(e) => setFicha({ ...ficha, instructivo: e.target.checked ? 'Sí' : '' })} className="h-4 w-4 accent-esynapse-600" disabled={!puedeEditar} /> {ficha.instructivo ? 'Sí' : 'No'}</label></Campo>
                    <Campo label="Manual"><label className="flex items-center gap-2 py-2 text-sm"><input type="checkbox" checked={!!ficha.manual} onChange={(e) => setFicha({ ...ficha, manual: e.target.checked ? 'Sí' : '' })} className="h-4 w-4 accent-esynapse-600" disabled={!puedeEditar} /> {ficha.manual ? 'Sí' : 'No'}</label></Campo>
                  </div>
                  <div className="mt-3"><Campo label="Criterio de aceptación"><textarea className="input-esynapse h-16" value={ficha.criterio_aceptacion || ''} onChange={(e) => setFicha({ ...ficha, criterio_aceptacion: e.target.value })} disabled={!puedeEditar} /></Campo></div>
                  <div className="mt-3">
                    <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Imagen del equipo</span>
                    {detalle.imagen_url ? (
                      <a href={detalle.imagen_url} target="_blank" rel="noreferrer" className="mb-2 block w-fit">
                        <img src={detalle.imagen_url} alt="Imagen del equipo" className="max-h-64 w-auto rounded-lg border border-slate-200 object-contain dark:border-slate-700" />
                      </a>
                    ) : (
                      <div className="mb-2 flex h-32 w-full max-w-xs items-center justify-center rounded-lg border border-dashed border-slate-300 text-xs text-slate-400 dark:border-slate-700">Sin imagen cargada</div>
                    )}
                    {puedeEditar && <input type="file" accept="image/*" className="text-xs" onChange={(e) => e.target.files[0] && subirImagen(e.target.files[0])} />}
                  </div>
                  </div>
                </div>

                <Campo label="Proveedor de calibración"><input className="input-esynapse" value={ficha.proveedor_calibracion || ''} onChange={(e) => setFicha({ ...ficha, proveedor_calibracion: e.target.value })} disabled={!puedeEditar} /></Campo>
                <Campo label="Observaciones"><textarea className="input-esynapse h-16" value={ficha.observaciones || ''} onChange={(e) => setFicha({ ...ficha, observaciones: e.target.value })} disabled={!puedeEditar} /></Campo>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={!!ficha.requiere_calibracion} onChange={(e) => setFicha({ ...ficha, requiere_calibracion: e.target.checked })} className="h-4 w-4 accent-esynapse-600" disabled={!puedeEditar} />
                  Requiere calibración
                </label>
                {detalle.updated_at && (
                  <p className="border-t border-slate-200 pt-3 text-xs text-slate-400 dark:border-slate-700">
                    Última modificación: {fechaHora(detalle.updated_at)}{detalle.actualizado_por ? ` — ${detalle.actualizado_por}` : ''}
                  </p>
                )}
                <div className="flex justify-end gap-2">
                  <button onClick={verFichaPdf} className="btn-secondary"><FileText className="h-4 w-4" /> Generar PDF</button>
                  {puedeEditar && <button onClick={guardarFicha} className="btn-primary">Guardar ficha técnica</button>}
                </div>
              </div>
            )}

            {/* PESTAÑAS DE BITÁCORA */}
            {TIPOS_REGISTRO.includes(tab) && (
              <RegistroTab
                tipo={tab}
                titulo={(PESTANAS.find(([v]) => v === tab) || [])[1]}
                registros={porTipo(tab)}
                regForm={regForm} setRegForm={setRegForm}
                regFile={regFile} setRegFile={setRegFile}
                onAgregar={() => agregarRegistro(tab)}
                onEliminar={eliminarRegistro}
                onImprimir={imprimirBitacora}
                puedeEditar={puedeEditar} puedeEliminar={puedeEliminar}
              />
            )}

            {/* MOVIMIENTOS (salida / entrada) */}
            {tab === 'movimiento' && (
              <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
                <div className="bg-[#1E3A5C] px-4 py-2 text-sm font-bold uppercase tracking-wide text-white">Movimientos</div>
                <div className="space-y-3 p-4">
                <Tabla cabeceras={['Motivo', 'Destino', 'Salida', 'Estado', 'Retorno', '']}>
                  {detalle.movimientos.map((m) => (
                    <tr key={m.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                      <td className="px-3 py-2">{m.motivo_display}</td>
                      <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{m.destino || '—'}</td>
                      <td className="px-3 py-2 text-xs">{m.fecha_salida ? new Date(m.fecha_salida).toLocaleDateString() : '—'}</td>
                      <td className="px-3 py-2 text-xs">{m.estado_salida_display || '—'}{m.estado_retorno_display ? ` → ${m.estado_retorno_display}` : ''}</td>
                      <td className="px-3 py-2 text-xs">{m.fecha_retorno ? new Date(m.fecha_retorno).toLocaleDateString() : <span className="text-amber-500">Fuera</span>}</td>
                      <td className="px-3 py-2 text-right">
                        {puedeEditar && !m.fecha_retorno && (
                          <button onClick={() => accion(() => api.equipos.registrarRetorno(detalle.id, { movimiento_id: m.id, estado_retorno: 'bueno', responsable_retorno: '' }))} className="btn-ghost text-xs">Registrar retorno</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </Tabla>
                {puedeEditar && (
                  <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
                    <select className="input-esynapse" value={movForm.motivo} onChange={(e) => setMovForm({ ...movForm, motivo: e.target.value })}>
                      {MOTIVOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                    </select>
                    <input className="input-esynapse" placeholder="Destino" value={movForm.destino} onChange={(e) => setMovForm({ ...movForm, destino: e.target.value })} />
                    <input className="input-esynapse" placeholder="Solicitante" value={movForm.solicitante} onChange={(e) => setMovForm({ ...movForm, solicitante: e.target.value })} />
                    <select className="input-esynapse" value={movForm.estado_salida} onChange={(e) => setMovForm({ ...movForm, estado_salida: e.target.value })}>
                      {FISICOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                    </select>
                    <button onClick={() => accion(async () => { await api.equipos.registrarMovimiento(detalle.id, movForm); setMovForm({ motivo: 'calibracion', destino: '', solicitante: '', estado_salida: 'bueno', responsable_salida: '' }) })} className="btn-primary"><Truck className="h-4 w-4" /> Salida</button>
                  </div>
                )}
                </div>
              </div>
            )}

            {/* PROGRAMA ANUAL */}
            {tab === 'programa' && (
              <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
                <div className="bg-[#1E3A5C] px-4 py-2 text-sm font-bold uppercase tracking-wide text-white">Programa</div>
                <div className="space-y-3 p-4">
                <Tabla cabeceras={['Tipo', 'Año', 'Frecuencia', 'Meses']}>
                  {detalle.actividades.map((a) => (
                    <tr key={a.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                      <td className="px-3 py-2">{a.tipo_display}</td>
                      <td className="px-3 py-2">{a.anio}</td>
                      <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{a.frecuencia || '—'}</td>
                      <td className="px-3 py-2 text-xs">{(a.meses || []).join(', ') || '—'}</td>
                    </tr>
                  ))}
                </Tabla>
                {puedeEditar && (
                  <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                    <select className="input-esynapse" value={actForm.tipo} onChange={(e) => setActForm({ ...actForm, tipo: e.target.value })}>
                      {TIPOS_ACTIVIDAD.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                    </select>
                    <input type="number" className="input-esynapse" value={actForm.anio} onChange={(e) => setActForm({ ...actForm, anio: e.target.value })} />
                    <input className="input-esynapse" placeholder="Frecuencia (ej. Anual)" value={actForm.frecuencia} onChange={(e) => setActForm({ ...actForm, frecuencia: e.target.value })} />
                    <button onClick={() => accion(async () => { await api.equipos.agregarActividad(detalle.id, actForm); setActForm({ tipo: 'calibracion', anio: new Date().getFullYear(), frecuencia: '' }) })} className="btn-primary">Agregar al programa</button>
                  </div>
                )}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* FUERA DE SERVICIO — se renderiza al final para quedar por encima del modal de detalle */}
      <Modal abierto={modalFuera} titulo="Marcar fuera de servicio" onCerrar={() => setModalFuera(false)} ancho="max-w-md">
        <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">Indica el motivo por el que el equipo queda fuera de servicio (inoperativo).</p>
        <textarea autoFocus className="input-esynapse h-24" value={motivoFuera} onChange={(e) => setMotivoFuera(e.target.value)} placeholder="Motivo…" />
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" onClick={() => setModalFuera(false)} className="btn-secondary">Cancelar</button>
          <button type="button" onClick={() => { setModalFuera(false); accion(() => api.equipos.marcarInoperativo(detalle.id, motivoFuera)) }} className="btn-danger">Marcar fuera de servicio</button>
        </div>
      </Modal>

      <Modal abierto={modalPend} titulo="Cambios pendientes de aprobación" onCerrar={() => setModalPend(false)} ancho="max-w-3xl">
        {pendientes.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-400">No hay cambios pendientes de aprobación.</p>
        ) : (
          <div className="space-y-2">
            {pendientes.map((s) => (
              <div key={s.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{s.resumen || `${s.operacion_display} · ${s.entidad_display}`}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {s.equipo_codigo ? `${s.equipo_codigo} · ` : ''}Solicitado por {s.solicitante} · {new Date(s.created_at).toLocaleString()}
                  </p>
                  {s.payload && Object.keys(s.payload).length > 0 && (
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Campos propuestos: {Object.keys(s.payload).join(', ')}</p>
                  )}
                </div>
                <div className="flex shrink-0 gap-2">
                  <button onClick={() => resolverSolicitud(s, 'aprobar')} className="btn-primary !py-1" title="Aprobar y aplicar el cambio">
                    <Check className="h-4 w-4" /> Aprobar
                  </button>
                  <button onClick={() => resolverSolicitud(s, 'devolver')} className="btn-secondary !py-1" title="Devolver al solicitante para corrección">
                    Devolver
                  </button>
                  <button onClick={() => resolverSolicitud(s, 'rechazar')} className="btn-danger !py-1" title="Rechazar y descartar el cambio">
                    <X className="h-4 w-4" /> Rechazar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>

      <Modal abierto={modalMis} titulo="Mis solicitudes de cambio" onCerrar={() => setModalMis(false)} ancho="max-w-3xl">
        {misSolic.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-400">No has enviado cambios pendientes.</p>
        ) : (
          <div className="space-y-2">
            {misSolic.map((s) => {
              const cls = {
                pendiente: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
                aprobada: 'bg-green-500/15 text-green-600 dark:text-green-400',
                devuelta: 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
                rechazada: 'bg-red-500/15 text-red-600 dark:text-red-400',
              }[s.estado] || 'bg-slate-500/15 text-slate-500'
              return (
                <div key={s.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{s.resumen || `${s.operacion_display} · ${s.entidad_display}`}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Enviado {new Date(s.created_at).toLocaleString()}{s.resuelto_at ? ` · resuelto ${new Date(s.resuelto_at).toLocaleString()}` : ''}
                    </p>
                    {s.observaciones && (
                      <p className="mt-1 text-xs text-slate-600 dark:text-slate-300"><span className="font-medium">Motivo:</span> {s.observaciones}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{s.estado_display}</span>
                    {s.estado === 'devuelta' && (
                      <button onClick={() => reenviarSolicitud(s)} className="btn-primary !py-1" title="Reenviar para aprobación">Reenviar</button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Modal>
    </div>
  )
}

function Tabla({ cabeceras, children }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
            {cabeceras.map((c, i) => <th key={i} className="px-3 py-2">{c}</th>)}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}

// Bitácora de una pestaña de la Hoja de Vida (calibración, mantenimiento, etc.)
function RegistroTab({ tipo, titulo, registros, regForm, setRegForm, regFile, setRegFile, onAgregar, onEliminar, onImprimir, puedeEditar, puedeEliminar }) {
  const esSuceso = tipo === 'suceso'
  const TERMINO_FECHA = { calibracion: 'calibración', mantenimiento: 'mantenimiento', verificacion: 'verificación', comprobacion_intermedia: 'comprobación', caracterizacion: 'caracterización' }
  const suf = TERMINO_FECHA[tipo]
  const lblFecha = suf ? `Fecha de ${suf}` : 'Fecha'
  const lblProxima = suf ? `Próxima fecha de ${suf}` : 'Próxima fecha'
  const cabeceras = esSuceso
    ? ['N°', 'Sucesos', 'Fecha suceso', 'Fecha solución', 'Observaciones', 'V°B°', '']
    : ['N°', 'Frecuencia', 'N° documento', lblFecha, lblProxima, 'Observaciones', 'V°B°', '', '']

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
      <div className="bg-[#1E3A5C] px-4 py-2 text-sm font-bold uppercase tracking-wide text-white">{titulo}</div>
      <div className="space-y-3 p-4">
      <Tabla cabeceras={cabeceras}>
        {registros.map((r, i) => (
          <tr key={r.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
            <td className="px-3 py-2 text-xs text-slate-400">{i + 1}</td>
            {esSuceso ? (
              <>
                <td className="px-3 py-2">{r.descripcion || '—'}</td>
                <td className="px-3 py-2 text-xs">{r.fecha || '—'}</td>
                <td className="px-3 py-2 text-xs">{r.fecha_proxima || '—'}</td>
                <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{r.observaciones || '—'}</td>
                <td className="px-3 py-2 text-xs">{r.vb || '—'}</td>
              </>
            ) : (
              <>
                <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{r.frecuencia || '—'}</td>
                <td className="px-3 py-2 font-mono text-xs">{r.numero_documento || '—'}</td>
                <td className="px-3 py-2 text-xs">{r.fecha || '—'}</td>
                <td className="px-3 py-2 text-xs">{r.fecha_proxima || '—'}</td>
                <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{r.observaciones || '—'}</td>
                <td className="px-3 py-2 text-xs">{r.vb || '—'}</td>
                <td className="px-3 py-2">{r.archivo_url && <a href={r.archivo_url} target="_blank" rel="noreferrer" className="text-esynapse-600 dark:text-esynapse-300"><Paperclip className="h-4 w-4" /></a>}</td>
              </>
            )}
            <td className="px-3 py-2 text-right">
              {puedeEliminar && <button onClick={() => onEliminar(r.id)} className="text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>}
            </td>
          </tr>
        ))}
        {registros.length === 0 && <tr><td colSpan={cabeceras.length} className="px-3 py-6 text-center text-xs text-slate-400">Sin registros todavía.</td></tr>}
      </Tabla>

      {puedeEditar && (
        <div className="rounded-lg border border-dashed border-slate-300 p-3 dark:border-slate-700">
          <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">Agregar registro</p>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
            {esSuceso ? (
              <>
                <Campo label="Sucesos"><input className="input-esynapse" value={regForm.descripcion} onChange={(e) => setRegForm({ ...regForm, descripcion: e.target.value })} /></Campo>
                <Campo label="Fecha del suceso"><input type="date" className="input-esynapse" value={regForm.fecha} onChange={(e) => setRegForm({ ...regForm, fecha: e.target.value })} /></Campo>
                <Campo label="Fecha de solución"><input type="date" className="input-esynapse" value={regForm.fecha_proxima} onChange={(e) => setRegForm({ ...regForm, fecha_proxima: e.target.value })} /></Campo>
              </>
            ) : (
              <>
                <Campo label="Frecuencia"><input className="input-esynapse" placeholder="Anual / 12 meses" value={regForm.frecuencia} onChange={(e) => { const fr = e.target.value; setRegForm({ ...regForm, frecuencia: fr, fecha_proxima: calcularProximaFecha(regForm.fecha, fr) || regForm.fecha_proxima }) }} /></Campo>
                <Campo label="N° de certificado / informe"><input className="input-esynapse" value={regForm.numero_documento} onChange={(e) => setRegForm({ ...regForm, numero_documento: e.target.value })} /></Campo>
                <Campo label={lblFecha}><input type="date" className="input-esynapse" value={regForm.fecha} onChange={(e) => { const fe = e.target.value; setRegForm({ ...regForm, fecha: fe, fecha_proxima: calcularProximaFecha(fe, regForm.frecuencia) || regForm.fecha_proxima }) }} /></Campo>
                <Campo label={lblProxima}><input type="date" className="input-esynapse" value={regForm.fecha_proxima} onChange={(e) => setRegForm({ ...regForm, fecha_proxima: e.target.value })} /></Campo>
              </>
            )}
            <Campo label="Observaciones"><input className="input-esynapse" value={regForm.observaciones} onChange={(e) => setRegForm({ ...regForm, observaciones: e.target.value })} /></Campo>
            <Campo label="V°B° (responsable)"><input className="input-esynapse" value={regForm.vb} onChange={(e) => setRegForm({ ...regForm, vb: e.target.value })} /></Campo>
          </div>
          <div className="mt-2 flex items-center justify-between gap-2">
            {!esSuceso ? (
              <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                <Paperclip className="h-4 w-4" />
                {regFile ? regFile.name : <span>Adjuntar documento <span className="text-red-500">(obligatorio)</span></span>}
                <input type="file" className="hidden" onChange={(e) => setRegFile(e.target.files[0] || null)} />
              </label>
            ) : <span />}
            <div className="flex items-center gap-2">
              {onImprimir && <button type="button" onClick={() => onImprimir(tipo, titulo)} className="btn-secondary"><FileText className="h-4 w-4" /> Generar PDF</button>}
              <button onClick={onAgregar} className="btn-primary"><Plus className="h-4 w-4" /> Agregar</button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  )
}
