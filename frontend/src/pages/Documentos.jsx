import { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle, Archive, CheckCircle2, Download, Eye, FileText, FileUp, FolderOpen, Globe, Lock, Pencil, Plus,
  Save, Search, Send, ShieldQuestion, XCircle,
} from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfig } from '../context/ConfigContext.jsx'
import { fechaHora } from '../lib/fecha.js'

const TIPOS = [
  ['politica', 'Política'], ['manual', 'Manual'], ['reglamento', 'Reglamento'],
  ['plan', 'Plan'], ['programa', 'Programa'], ['procedimiento', 'Procedimiento'],
  ['formato', 'Formato'], ['pets', 'PETS'], ['instructivo', 'Instructivo'],
  ['registro', 'Registro'],
]

const NORMAS = [
  ['iso_9001', 'ISO 9001'],
  ['iso_14001', 'ISO 14001'],
  ['iso_45001', 'ISO 45001 / Ley 29783'],
  ['iso_17025', 'NTP ISO/IEC 17025'],
]

const COLOR_NORMA = {
  'ISO 9001': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'ISO 14001': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  'ISO 45001 / Ley 29783': 'bg-red-500/15 text-red-600 dark:text-red-400',
  'NTP ISO/IEC 17025': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
}

const CHIP_NORMA = {
  iso_9001: 'border-esynapse-500 bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  iso_14001: 'border-emerald-500 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  iso_45001: 'border-red-500 bg-red-500/15 text-red-600 dark:text-red-400',
  iso_17025: 'border-amber-500 bg-amber-500/15 text-amber-600 dark:text-amber-400',
}

const COLOR_ESTADO = {
  'En elaboración': 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
  'En revisión': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  'En aprobación': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'Vigente': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  'Obsoleto': 'bg-red-500/15 text-red-500',
  'Rechazado': 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
}

const FORM_VACIO = {
  codigo: '', titulo: '', tipo: 'procedimiento', proceso: '', objetivo: '', alcance: '',
  meses_revision: 12, anos_retencion: 5, soporte: 'digital', normas: [],
  origen: 'interno', entidad_emisora: '', edicion: '', dias_verificacion: 7, padre: '', fecha_aprobacion: '',
}

const esPdf = (url) => (url || '').split('?')[0].toLowerCase().endsWith('.pdf')

export default function Documentos() {
  const { tienePermiso } = useAuth()
  const { config } = useConfig()
  const empresa = config?.subtitulo || 'la empresa'
  const [docs, setDocs] = useState([])
  const [porVencer, setPorVencer] = useState([])
  const [porVerificar, setPorVerificar] = useState([])
  const [buscar, setBuscar] = useState('')
  const [tipo, setTipo] = useState('')
  const [modalCrear, setModalCrear] = useState(false)
  const [detalle, setDetalle] = useState(null)
  const [ficha, setFicha] = useState(null)
  const [visor, setVisor] = useState(null) // {titulo, url}
  const [form, setForm] = useState(FORM_VACIO)
  const [archivo, setArchivo] = useState(null)
  const [archivoNV, setArchivoNV] = useState(null)
  const [resumenNV, setResumenNV] = useState('')
  const [edicionNV, setEdicionNV] = useState('')
  const [comentarios, setComentarios] = useState('')
  const [obsVerif, setObsVerif] = useState('')
  const [error, setError] = useState('')
  const [retencionLibre, setRetencionLibre] = useState(false)
  const [verInactivos, setVerInactivos] = useState(false)
  const [passFirma, setPassFirma] = useState('')
  const [pdfRespaldo, setPdfRespaldo] = useState(null)
  const [archivoObs, setArchivoObs] = useState(null)
  const [archivoCorregido, setArchivoCorregido] = useState(null)
  const [verArchivados, setVerArchivados] = useState(false)
  const [confirmar, setConfirmar] = useState(null) // {tipo: 'archivar'|'eliminar', doc}
  const [editandoCodigo, setEditandoCodigo] = useState(false)
  const [nuevoCodigo, setNuevoCodigo] = useState('')
  // Edición de la ficha (con autorización por contraseña)
  const [editFicha, setEditFicha] = useState(false)
  const [fichaForm, setFichaForm] = useState(null)
  const [passFicha, setPassFicha] = useState('')
  const [errFicha, setErrFicha] = useState('')
  const [retLibreFicha, setRetLibreFicha] = useState(false)
  const [guardandoFicha, setGuardandoFicha] = useState(false)

  const cargar = useCallback(async () => {
    const params = new URLSearchParams()
    if (buscar) params.set('buscar', buscar)
    if (tipo) params.set('tipo', tipo)
    if (verInactivos) params.set('incluir_inactivos', '1')
    if (verArchivados) params.set('archivados', '1')
    const data = await api.documentos.listar(`?${params}`)
    setDocs(data.results ?? data)
  }, [buscar, tipo, verInactivos, verArchivados])

  const cargarAlertas = () => {
    api.documentos.porVencer().then(setPorVencer).catch(() => {})
    api.documentos.externosPorVerificar().then(setPorVerificar).catch(() => {})
  }

  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => { cargarAlertas() }, [])

  const abrirDetalle = async (id) => {
    setError(''); setComentarios(''); setObsVerif(''); setArchivoNV(null); setResumenNV(''); setEdicionNV(''); setPassFirma(''); setPdfRespaldo(null); setArchivoObs(null); setArchivoCorregido(null); setEditandoCodigo(false); setNuevoCodigo('')
    setDetalle(await api.documentos.detalle(id))
  }

  const refrescarDetalle = async () => {
    await cargar()
    cargarAlertas()
    if (detalle) setDetalle(await api.documentos.detalle(detalle.id))
  }

  const abrirFicha = (d) => {
    setEditFicha(false); setFichaForm(null); setPassFicha(''); setErrFicha(''); setRetLibreFicha(false)
    setFicha(d)
  }

  const cerrarFicha = () => {
    setFicha(null); setEditFicha(false); setFichaForm(null); setPassFicha(''); setErrFicha('')
  }

  const iniciarEdicionFicha = async () => {
    setErrFicha(''); setPassFicha('')
    try {
      const d = await api.documentos.detalle(ficha.id)
      setFichaForm({
        titulo: d.titulo || '',
        tipo: d.tipo || 'procedimiento',
        proceso: d.proceso || '',
        entidad_emisora: d.entidad_emisora || '',
        anos_retencion: d.anos_retencion ?? 5,
        soporte: d.soporte || 'digital',
        dias_verificacion: d.dias_verificacion ?? 7,
        padre: d.padre || '',
        normas: d.normas_aplicables || [],
        fecha_aprobacion: ficha.fecha_aprobacion || '',
      })
      setRetLibreFicha(![0, 1, 2, 3, 5, 7, 10].includes(d.anos_retencion ?? 5))
      setEditFicha(true)
    } catch (e) { setErrFicha(e.message) }
  }

  const guardarFicha = async () => {
    setErrFicha('')
    if (!passFicha) { setErrFicha('Ingresa tu contraseña para autorizar la edición.'); return }
    setGuardandoFicha(true)
    try {
      const payload = {
        titulo: fichaForm.titulo,
        tipo: fichaForm.tipo,
        proceso: fichaForm.proceso,
        entidad_emisora: fichaForm.entidad_emisora,
        anos_retencion: fichaForm.anos_retencion,
        soporte: fichaForm.soporte,
        dias_verificacion: fichaForm.dias_verificacion,
        normas_aplicables: fichaForm.normas,
        padre: fichaForm.padre || null,
        password: passFicha,
      }
      if (ficha.origen === 'externo' && fichaForm.fecha_aprobacion) payload.fecha_aprobacion = fichaForm.fecha_aprobacion
      const resp = await api.documentos.editarFicha(ficha.id, payload)
      setFicha({
        ...ficha, ...resp,
        ...(ficha.origen === 'externo' && fichaForm.fecha_aprobacion ? { fecha_aprobacion: fichaForm.fecha_aprobacion } : {}),
      })
      setEditFicha(false); setPassFicha('')
      await cargar(); cargarAlertas()
    } catch (e) { setErrFicha(e.message) } finally { setGuardandoFicha(false) }
  }

  const aprobarFirmado = async () => {
    if (pdfRespaldo) {
      const fd = new FormData()
      fd.append('password', passFirma)
      fd.append('archivo_pdf', pdfRespaldo)
      await api.documentos.aprobarConPdf(detalle.id, fd)
    } else {
      await api.documentos.aprobar(detalle.id, passFirma)
    }
  }

  const accion = async (fn) => {
    setError('')
    try { await fn(); setPassFirma(''); setArchivoObs(null); setArchivoCorregido(null); await refrescarDetalle() } catch (e) { setError(e.message) }
  }

  const crear = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => {
        if (k === 'normas') v.forEach((n) => fd.append('normas_aplicables', n))
        else if (k === 'padre' || k === 'fecha_aprobacion') { if (v) fd.append(k, v) }
        else fd.append(k, v)
      })
      fd.append('archivo', archivo)
      await api.documentos.crear(fd)
      setModalCrear(false)
      setForm(FORM_VACIO)
      setArchivo(null)
      await cargar()
      cargarAlertas()
    } catch (e2) { setError(e2.message) }
  }

  const enviarCorregido = async () => {
    // Un solo paso: si hay documento corregido cargado, lo sube y luego firma y envía a revisión.
    if (archivoCorregido) {
      const fd = new FormData()
      fd.append('archivo', archivoCorregido)
      await api.documentos.reemplazarArchivo(detalle.id, fd)
    }
    await api.documentos.enviarRevision(detalle.id, passFirma)
  }

  const subirNuevaVersion = async () => {
    const fd = new FormData()
    fd.append('archivo', archivoNV)
    fd.append('resumen_cambios', resumenNV)
    if (detalle.origen === 'externo') fd.append('edicion', edicionNV)
    await api.documentos.nuevaVersion(detalle.id, fd)
  }

  const vp = detalle?.version_en_proceso
  const obsPendientes = (vp?.observaciones || []).filter((o) => !o.resuelta)
  const obsResueltas = (vp?.observaciones || []).filter((o) => o.resuelta)
  const vv = detalle?.version_vigente
  const externo = detalle?.origen === 'externo'

  const campo = (etiqueta, clave, props = {}) => (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">{etiqueta}</label>
      <input className="input-esynapse" value={form[clave]}
        onChange={(e) => setForm({ ...form, [clave]: e.target.value })} {...props} />
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Gestión Documental</h1>
        {tienePermiso('documentos', 'crear') && (
          <button onClick={() => { setForm(FORM_VACIO); setArchivo(null); setError(''); setRetencionLibre(false); setModalCrear(true) }} className="btn-primary">
            <Plus className="h-4 w-4" /> Nuevo documento
          </button>
        )}
      </div>

      {porVencer.length > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" />
          <div>
            <p className="font-medium text-amber-600 dark:text-amber-400">
              {porVencer.length} documento(s) con revisión próxima o vencida
            </p>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              {porVencer.slice(0, 3).map((d) => `${d.codigo} (${d.fecha_proxima_revision})`).join(' · ')}
              {porVencer.length > 3 ? ` y ${porVencer.length - 3} más…` : ''}
            </p>
          </div>
        </div>
      )}

      {porVerificar.length > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-sky-500/30 bg-sky-500/10 p-4 text-sm">
          <ShieldQuestion className="mt-0.5 h-5 w-5 shrink-0 text-sky-500" />
          <div>
            <p className="font-medium text-sky-600 dark:text-sky-400">
              {porVerificar.length} documento(s) externo(s) con verificación de vigencia pendiente
            </p>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              {porVerificar.slice(0, 3).map((d) => `${d.codigo} (${d.entidad_emisora})`).join(' · ')}
              {porVerificar.length > 3 ? ` y ${porVerificar.length - 3} más…` : ''}
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input-esynapse w-64 pl-9" placeholder="Buscar código, título, proceso…"
            value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <select className="input-esynapse w-48" value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Todos los tipos</option>
          {TIPOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={verInactivos} onChange={(e) => setVerInactivos(e.target.checked)}
            className="h-4 w-4 accent-esynapse-600" />
          Incluir inactivos
        </label>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={verArchivados} onChange={(e) => setVerArchivados(e.target.checked)}
            className="h-4 w-4 accent-esynapse-600" />
          Ver archivados
        </label>
      </div>

      <div className="card-esynapse overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-center text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3">Título</th>
              <th className="px-4 py-3">Tipo</th>
              <th className="px-4 py-3">Proceso</th>
              <th className="px-4 py-3">Versión</th>
              <th className="px-4 py-3">Normas</th>
              <th className="px-4 py-3">Soporte</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Aprobado</th>
              <th className="px-4 py-3">Próx. revisión</th>
              <th className="px-4 py-3">Retención</th>
              <th className="px-4 py-3">Ver</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id} onClick={() => abrirDetalle(d.id)}
                className="cursor-pointer border-b border-slate-100 text-center align-middle transition last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 font-mono text-xs font-medium">
                  <span className="flex items-center justify-center gap-1.5">
                    {d.codigo}
                    {d.origen === 'externo' && (
                      <span title={`Externo — ${d.entidad_emisora}`}>
                        <Globe className="h-3.5 w-3.5 text-sky-500" />
                      </span>
                    )}
                  </span>
                </td>
                <td className="px-4 py-3">{d.titulo}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{d.tipo_display}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                  {d.origen === 'externo' ? d.entidad_emisora : (d.proceso || '—')}
                </td>
                <td className="px-4 py-3">{d.version_actual ? `Ver. ${d.version_actual}` : '—'}</td>
                <td className="px-4 py-3">
                  <div className="mx-auto flex max-w-[180px] flex-wrap justify-center gap-1">
                    {(d.normas_display || []).map((n) => (
                      <span key={n} className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_NORMA[n] || 'bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>
                        {n}
                      </span>
                    ))}
                    {(!d.normas_display || d.normas_display.length === 0) && <span className="text-xs text-slate-400">—</span>}
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">{d.soporte_display}</td>
                <td className="px-4 py-3">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_ESTADO[d.estado_actual] || 'bg-slate-500/15'}`}>
                    {d.estado_actual}
                  </span>
                  {d.proceso_paralelo && (
                    <span className="ml-1 rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400"
                      title={`Nueva versión en proceso: Ver. ${d.proceso_paralelo.version}`}>
                      → Ver. {d.proceso_paralelo.version} {d.proceso_paralelo.estado.toLowerCase()}
                    </span>
                  )}
                  {d.archivado && (
                    <span className="ml-1 rounded bg-slate-500/20 px-1.5 py-0.5 text-[10px] font-medium text-slate-500 dark:text-slate-400">
                      Archivado
                    </span>
                  )}
                  {!d.is_active && (
                    <span className="ml-1 rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] font-medium text-red-500">
                      Inactivo
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs">{d.fecha_aprobacion || '—'}</td>
                <td className="px-4 py-3 text-xs">{d.fecha_proxima_revision || '—'}</td>
                <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">{retencionTexto(d.anos_retencion)}</td>
                <td className="px-4 py-3">
                  <button onClick={(e) => { e.stopPropagation(); abrirFicha(d) }} title="Ver documento"
                    className="mx-auto flex h-7 w-7 items-center justify-center rounded text-esynapse-600 hover:bg-esynapse-600/10 dark:text-esynapse-300">
                    <Eye className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr><td colSpan={12} className="px-4 py-8 text-center text-slate-400">Sin documentos</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal crear */}
      <Modal abierto={modalCrear} titulo="Nuevo documento" onCerrar={() => setModalCrear(false)}>
        <form onSubmit={crear} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Origen</label>
            <div className="flex gap-2">
              {[['interno', `Interno (elaborado por ${empresa})`], ['externo', 'Externo (norma, directriz, etc.)']].map(([v, n]) => (
                <label key={v} className={`flex flex-1 cursor-pointer items-center justify-center rounded-lg border px-2 py-2 text-xs transition ${
                  form.origen === v
                    ? 'border-esynapse-500 bg-esynapse-600/15 font-medium text-esynapse-600 dark:text-esynapse-300'
                    : 'border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-300'
                }`}>
                  <input type="radio" className="hidden" checked={form.origen === v}
                    onChange={() => setForm({ ...form, origen: v })} />
                  {n}
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {campo('Código', 'codigo', { required: true, placeholder: form.origen === 'externo' ? 'EXT-001' : 'PRO-001' })}
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Tipo</label>
              <select className="input-esynapse" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
                {TIPOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
              </select>
            </div>
          </div>
          {campo('Título', 'titulo', { required: true })}
          {['formato', 'registro', 'pets', 'instructivo'].includes(form.tipo) && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Documento padre (al que pertenece)</label>
              <select className="input-esynapse" value={form.padre} onChange={(e) => setForm({ ...form, padre: e.target.value })}>
                <option value="">— Ninguno —</option>
                {docs.map((d) => <option key={d.id} value={d.id}>{d.codigo} — {d.titulo}</option>)}
              </select>
            </div>
          )}

          {form.origen === 'externo' ? (
            <div className="grid grid-cols-3 gap-3">
              {campo('Entidad emisora', 'entidad_emisora', { required: true, placeholder: 'INACAL-DA, ISO…' })}
              {campo('Edición/versión del emisor', 'edicion', { placeholder: '2017, Rev. 03…' })}
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Verificar cada</label>
                <select className="input-esynapse" value={form.dias_verificacion}
                  onChange={(e) => setForm({ ...form, dias_verificacion: Number(e.target.value) })}>
                  <option value={7}>7 días</option>
                  <option value={15}>15 días</option>
                  <option value={30}>30 días</option>
                  <option value={90}>90 días</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Fecha de aprobación (del emisor)</label>
                <input type="date" className="input-esynapse" value={form.fecha_aprobacion} onChange={(e) => setForm({ ...form, fecha_aprobacion: e.target.value })} />
              </div>
            </div>
          ) : (
            <>
              {campo('Proceso vinculado', 'proceso', { placeholder: 'Ej: Laboratorio Presión' })}
              {campo('Objetivo', 'objetivo')}
              {campo('Alcance', 'alcance')}
            </>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Normas aplicables</label>
            <div className="flex flex-wrap gap-2">
              {NORMAS.map(([clave, nombre]) => (
                <label key={clave} className={`flex cursor-pointer items-center rounded-lg border px-2.5 py-1.5 text-xs transition ${
                  form.normas.includes(clave)
                    ? CHIP_NORMA[clave]
                    : 'border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-300'
                }`}>
                  <input type="checkbox" className="hidden" checked={form.normas.includes(clave)}
                    onChange={(e) => setForm({
                      ...form,
                      normas: e.target.checked
                        ? [...form.normas, clave]
                        : form.normas.filter((n) => n !== clave),
                    })} />
                  {nombre}
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Soporte</label>
              <select className="input-esynapse" value={form.soporte}
                onChange={(e) => setForm({ ...form, soporte: e.target.value })}>
                <option value="digital">Digital</option>
                <option value="fisico">Físico</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Tiempo de retención</label>
              <select className="input-esynapse" value={[0,1,2,3,5,7,10].includes(form.anos_retencion) && !retencionLibre ? form.anos_retencion : 'otro'}
                onChange={(e) => {
                  if (e.target.value === 'otro') { setRetencionLibre(true) }
                  else { setRetencionLibre(false); setForm({ ...form, anos_retencion: Number(e.target.value) }) }
                }}>
                <option value={1}>1 año</option>
                <option value={2}>2 años</option>
                <option value={3}>3 años</option>
                <option value={5}>5 años</option>
                <option value={7}>7 años</option>
                <option value={10}>10 años</option>
                <option value={0}>Sujeto a Nueva Versión</option>
                <option value="otro">Otro…</option>
              </select>
              {retencionLibre && (
                <input type="number" min={1} max={99} className="input-esynapse mt-2" placeholder="Años de retención"
                  value={form.anos_retencion}
                  onChange={(e) => setForm({ ...form, anos_retencion: Number(e.target.value) || 1 })} />
              )}
            </div>
          </div>

          {form.origen === 'interno' && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Frecuencia de revisión</label>
              <select className="input-esynapse" value={form.meses_revision}
                onChange={(e) => setForm({ ...form, meses_revision: Number(e.target.value) })}>
                <option value={6}>Cada 6 meses</option>
                <option value={12}>Cada 1 año</option>
                <option value={24}>Cada 2 años</option>
                <option value={36}>Cada 3 años</option>
              </select>
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Archivo (PDF, DOCX, XLSX)</label>
            <input type="file" required onChange={(e) => setArchivo(e.target.files[0])}
              className="block w-full text-xs text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-esynapse-600 file:px-3 file:py-2 file:text-xs file:font-medium file:text-white hover:file:bg-esynapse-500" />
          </div>

          <p className="rounded-lg bg-esynapse-600/10 px-3 py-2 text-xs text-esynapse-600 dark:text-esynapse-300">
            {form.origen === 'externo'
              ? 'El documento externo queda Vigente de inmediato y se controla mediante verificación periódica de vigencia.'
              : 'Se creará la Ver. 00 en estado En elaboración. Luego envíala a revisión.'}
          </p>
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalCrear(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">Crear documento</button>
          </div>
        </form>
      </Modal>

      {/* Modal ficha — se abre con el ojo. Solo lectura, con opción de editar (previa contraseña). */}
      <Modal abierto={Boolean(ficha)} titulo={ficha ? `${ficha.codigo} — ${ficha.titulo}` : ''}
        onCerrar={cerrarFicha} ancho="max-w-3xl">
        {ficha && (
          <div className="space-y-4">
            <div className="mb-1 flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Datos del documento</h3>
              {!editFicha ? (
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400"><Lock className="h-3.5 w-3.5" /> Solo lectura</span>
                  {tienePermiso('documentos', 'editar') && ficha.is_active && (
                    <button onClick={iniciarEdicionFicha}
                      className="flex items-center gap-1 rounded-lg border border-esynapse-500 px-2.5 py-1 text-xs font-medium text-esynapse-600 transition hover:bg-esynapse-600/10 dark:text-esynapse-300">
                      <Pencil className="h-3.5 w-3.5" /> Editar
                    </button>
                  )}
                </div>
              ) : (
                <span className="flex items-center gap-1 text-xs font-medium text-esynapse-600 dark:text-esynapse-300"><Pencil className="h-3.5 w-3.5" /> Editando — requiere tu contraseña</span>
              )}
            </div>

            {editFicha && fichaForm ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <Dato label="Código" valor={ficha.codigo} mono />
                  <CampoEdit label="Nombre" valor={fichaForm.titulo} onChange={(v) => setFichaForm({ ...fichaForm, titulo: v })} />
                  <div>
                    <label className="mb-0.5 block text-[11px] font-medium uppercase tracking-wide text-slate-400">Tipo</label>
                    <select className="input-esynapse" value={fichaForm.tipo} onChange={(e) => setFichaForm({ ...fichaForm, tipo: e.target.value })}>
                      {TIPOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                    </select>
                  </div>
                  <Dato label="Origen" valor={ficha.origen_display} />
                  {ficha.origen === 'externo'
                    ? <CampoEdit label="Entidad emisora" valor={fichaForm.entidad_emisora} onChange={(v) => setFichaForm({ ...fichaForm, entidad_emisora: v })} />
                    : <CampoEdit label="Proceso" valor={fichaForm.proceso} onChange={(v) => setFichaForm({ ...fichaForm, proceso: v })} />}
                  <Dato label="Versión" valor={ficha.version_actual ? `Ver. ${ficha.version_actual}` : '—'} />
                  <Dato label="Situación" valor={ficha.estado_actual} />
                  {ficha.origen === 'externo' ? (
                    <div>
                      <label className="mb-0.5 block text-[11px] font-medium uppercase tracking-wide text-slate-400">Fecha de aprobación (del emisor)</label>
                      <input type="date" className="input-esynapse" value={fichaForm.fecha_aprobacion}
                        onChange={(e) => setFichaForm({ ...fichaForm, fecha_aprobacion: e.target.value })} />
                    </div>
                  ) : (
                    <Dato label="Fecha de aprobación" valor={ficha.fecha_aprobacion || '—'} />
                  )}
                  <div>
                    <label className="mb-0.5 block text-[11px] font-medium uppercase tracking-wide text-slate-400">Tiempo de retención</label>
                    <select className="input-esynapse"
                      value={[0, 1, 2, 3, 5, 7, 10].includes(fichaForm.anos_retencion) && !retLibreFicha ? fichaForm.anos_retencion : 'otro'}
                      onChange={(e) => {
                        if (e.target.value === 'otro') setRetLibreFicha(true)
                        else { setRetLibreFicha(false); setFichaForm({ ...fichaForm, anos_retencion: Number(e.target.value) }) }
                      }}>
                      <option value={1}>1 año</option>
                      <option value={2}>2 años</option>
                      <option value={3}>3 años</option>
                      <option value={5}>5 años</option>
                      <option value={7}>7 años</option>
                      <option value={10}>10 años</option>
                      <option value={0}>Sujeto a Nueva Versión</option>
                      <option value="otro">Otro…</option>
                    </select>
                    {retLibreFicha && (
                      <input type="number" min={1} max={99} className="input-esynapse mt-2" placeholder="Años de retención"
                        value={fichaForm.anos_retencion}
                        onChange={(e) => setFichaForm({ ...fichaForm, anos_retencion: Number(e.target.value) || 1 })} />
                    )}
                  </div>
                  <div>
                    <label className="mb-0.5 block text-[11px] font-medium uppercase tracking-wide text-slate-400">Soporte</label>
                    <select className="input-esynapse" value={fichaForm.soporte} onChange={(e) => setFichaForm({ ...fichaForm, soporte: e.target.value })}>
                      <option value="digital">Digital</option>
                      <option value="fisico">Físico</option>
                    </select>
                  </div>
                  <Dato label="Estado" valor={ficha.is_active ? 'Activo' : 'Inactivo'} />
                  {ficha.origen === 'externo' && (
                    <div>
                      <label className="mb-0.5 block text-[11px] font-medium uppercase tracking-wide text-slate-400">Verificación cada</label>
                      <select className="input-esynapse" value={fichaForm.dias_verificacion}
                        onChange={(e) => setFichaForm({ ...fichaForm, dias_verificacion: Number(e.target.value) })}>
                        <option value={7}>7 días</option>
                        <option value={15}>15 días</option>
                        <option value={30}>30 días</option>
                        <option value={90}>90 días</option>
                      </select>
                    </div>
                  )}
                </div>

                {['formato', 'registro', 'pets', 'instructivo'].includes(fichaForm.tipo) && (
                  <div>
                    <label className="mb-0.5 block text-[11px] font-medium uppercase tracking-wide text-slate-400">Documento padre (al que pertenece)</label>
                    <select className="input-esynapse" value={fichaForm.padre} onChange={(e) => setFichaForm({ ...fichaForm, padre: e.target.value })}>
                      <option value="">— Ninguno —</option>
                      {docs.filter((d) => d.id !== ficha.id).map((d) => <option key={d.id} value={d.id}>{d.codigo} — {d.titulo}</option>)}
                    </select>
                  </div>
                )}

                <div>
                  <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-slate-400">Normas aplicables</label>
                  <div className="flex flex-wrap gap-2">
                    {NORMAS.map(([clave, nombre]) => (
                      <label key={clave} className={`flex cursor-pointer items-center rounded-lg border px-2.5 py-1.5 text-xs transition ${
                        fichaForm.normas.includes(clave) ? CHIP_NORMA[clave] : 'border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-300'
                      }`}>
                        <input type="checkbox" className="hidden" checked={fichaForm.normas.includes(clave)}
                          onChange={(e) => setFichaForm({
                            ...fichaForm,
                            normas: e.target.checked ? [...fichaForm.normas, clave] : fichaForm.normas.filter((n) => n !== clave),
                          })} />
                        {nombre}
                      </label>
                    ))}
                  </div>
                </div>

                <input type="password" className="input-esynapse" autoComplete="current-password"
                  placeholder="Tu contraseña — autoriza y firma esta edición"
                  value={passFicha} onChange={(e) => setPassFicha(e.target.value)} />
                {errFicha && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{errFicha}</p>}
                <div className="flex justify-end gap-2">
                  <button onClick={() => { setEditFicha(false); setErrFicha('') }} className="btn-secondary">Cancelar</button>
                  <button disabled={guardandoFicha} onClick={guardarFicha} className="btn-primary">
                    <Save className="h-4 w-4" /> {guardandoFicha ? 'Guardando…' : 'Guardar cambios'}
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <Dato label="Código" valor={ficha.codigo} mono />
                  <Dato label="Nombre" valor={ficha.titulo} />
                  <Dato label="Tipo" valor={ficha.tipo_display} />
                  <Dato label="Origen" valor={ficha.origen_display} />
                  <Dato label={ficha.origen === 'externo' ? 'Entidad emisora' : 'Proceso'} valor={ficha.origen === 'externo' ? ficha.entidad_emisora : (ficha.proceso || '—')} />
                  {ficha.padre_codigo && <Dato label="Documento padre" valor={`${ficha.padre_codigo} — ${ficha.padre_titulo}`} />}
                  <Dato label="Versión" valor={ficha.version_actual ? `Ver. ${ficha.version_actual}` : '—'} />
                  <Dato label="Situación" valor={ficha.estado_actual} />
                  <Dato label="Fecha de aprobación" valor={ficha.fecha_aprobacion || '—'} />
                  <Dato label="Tiempo de retención" valor={retencionTexto(ficha.anos_retencion)} />
                  <Dato label="Soporte" valor={ficha.soporte_display} />
                  <Dato label="Estado" valor={ficha.is_active ? 'Activo' : 'Inactivo'} />
                  {ficha.origen === 'externo' && <Dato label="Verificación cada" valor={`${ficha.dias_verificacion} días`} />}
                </div>
                <div>
                  <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">Normas aplicables</p>
                  <div className="flex flex-wrap gap-1">
                    {(ficha.normas_display || []).map((n) => (
                      <span key={n} className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_NORMA[n] || 'bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>{n}</span>
                    ))}
                    {(!ficha.normas_display || ficha.normas_display.length === 0) && <span className="text-xs text-slate-400">—</span>}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 px-4 py-3 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <span className="font-medium text-slate-700 dark:text-slate-200">Creado:</span> {fechaHora(ficha.created_at)}{ficha.creado_por ? ` por ${ficha.creado_por}` : ''}
                  <span className="mx-2">·</span>
                  <span className="font-medium text-slate-700 dark:text-slate-200">Última actualización:</span> {fechaHora(ficha.updated_at)}{ficha.actualizado_por ? ` por ${ficha.actualizado_por}` : ''}
                </div>
              </>
            )}
          </div>
        )}
      </Modal>

      {/* Modal detalle */}
      <Modal abierto={Boolean(detalle)} titulo={detalle ? `${detalle.codigo} — ${detalle.titulo}` : ''}
        onCerrar={() => setDetalle(null)} ancho="max-w-2xl">
        {detalle && (
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 dark:text-slate-400">
              <p><strong className="text-slate-700 dark:text-slate-200">Origen:</strong> {detalle.origen_display}{externo ? ` — ${detalle.entidad_emisora}` : ''}</p>
              <p><strong className="text-slate-700 dark:text-slate-200">Tipo:</strong> {detalle.tipo_display}</p>
              {!externo && <p><strong className="text-slate-700 dark:text-slate-200">Proceso:</strong> {detalle.proceso || '—'}</p>}
              {!externo && <p><strong className="text-slate-700 dark:text-slate-200">Revisión:</strong> cada {detalle.meses_revision} meses</p>}
              <p><strong className="text-slate-700 dark:text-slate-200">Soporte:</strong> {detalle.soporte_display}</p>
              <p><strong className="text-slate-700 dark:text-slate-200">Retención:</strong> {retencionTexto(detalle.anos_retencion)}</p>
              {externo && (
                <p className="col-span-2">
                  <strong className="text-slate-700 dark:text-slate-200">Última verificación:</strong>{' '}
                  {detalle.ultima_verificacion ? new Date(detalle.ultima_verificacion).toLocaleString('es-PE') : 'Nunca'}
                  {' · '}cada {detalle.dias_verificacion} días
                </p>
              )}
              {detalle.normas_display?.length > 0 && (
                <p className="col-span-2"><strong className="text-slate-700 dark:text-slate-200">Normas:</strong> {detalle.normas_display.join(' · ')}</p>
              )}
            </div>

            {!detalle.is_active && tienePermiso('documentos', 'editar') && (
              <button onClick={() => accion(() => api.documentos.activar(detalle.id))} className="btn-primary !py-1.5 text-xs">
                <CheckCircle2 className="h-3.5 w-3.5" /> Reactivar documento
              </button>
            )}

            {/* Barra de progreso del flujo */}
            {!externo && vp && (
              <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-3 dark:bg-slate-800/60">
                {[
                  ['borrador', 'En elaboración'],
                  ['en_revision', 'En revisión'],
                  ['en_aprobacion', 'En aprobación'],
                  ['vigente', 'Vigente'],
                ].map(([clave, nombre], i, arr) => {
                  const orden = { borrador: 0, en_revision: 1, en_aprobacion: 2, vigente: 3 }
                  const actual = orden[vp.estado] ?? -1
                  const esActual = i === actual
                  const completado = i < actual
                  return (
                    <div key={clave} className="flex flex-1 items-center">
                      <div className="flex flex-1 flex-col items-center gap-1">
                        <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                          completado ? 'bg-emerald-500 text-white'
                          : esActual ? 'bg-esynapse-600 text-white ring-4 ring-esynapse-600/25'
                          : 'bg-slate-300 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
                        }`}>
                          {completado ? '✓' : i + 1}
                        </div>
                        <span className={`text-center text-[10px] leading-tight ${
                          esActual ? 'font-semibold text-esynapse-600 dark:text-esynapse-300'
                          : completado ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-slate-400 dark:text-slate-500'
                        }`}>
                          {esActual ? `▸ ${nombre}` : nombre}
                        </span>
                      </div>
                      {i < arr.length - 1 && (
                        <div className={`mb-4 h-0.5 flex-1 ${completado ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-700'}`} />
                      )}
                    </div>
                  )
                })}
              </div>
            )}
            {!externo && vp?.estado === 'rechazado' && (
              <p className="rounded-lg bg-violet-500/10 px-3 py-2 text-xs text-violet-600 dark:text-violet-400">
                Esta versión fue rechazada definitivamente. Crea una nueva versión para continuar.
              </p>
            )}

            {/* Flujo interno */}
            {!externo && (
              <>
                <div className="flex flex-wrap gap-2">
                  {obsPendientes.length > 0 && (
                    <div className="w-full space-y-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3">
                      <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                        ⚠ Observaciones por atender — corrige y vuelve a enviar:
                      </p>
                      {obsPendientes.map((o) => (
                        <div key={o.id} className="text-xs text-slate-600 dark:text-slate-300">
                          <span className="font-medium">{o.etapa_display}</span> por {o.autor} ({new Date(o.created_at).toLocaleDateString('es-PE')}): {o.comentarios}
                          {o.archivo_url && (
                            <a href={o.archivo_url} target="_blank" rel="noreferrer"
                              className="ml-2 inline-flex items-center gap-1 rounded bg-amber-500/20 px-2 py-0.5 font-medium text-amber-700 hover:bg-amber-500/30 dark:text-amber-300">
                              <Download className="h-3 w-3" /> Descargar archivo anotado
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  {obsResueltas.length > 0 && (
                    <div className="w-full space-y-1 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
                      <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                        ✓ Observaciones atendidas:
                      </p>
                      {obsResueltas.map((o) => (
                        <div key={o.id} className="text-xs text-slate-500 dark:text-slate-400">
                          <span className="font-medium">{o.etapa_display}</span> por {o.autor} ({new Date(o.created_at).toLocaleDateString('es-PE')}): {o.comentarios}
                          {o.archivo_url && (
                            <a href={o.archivo_url} target="_blank" rel="noreferrer"
                              className="ml-2 inline-flex items-center gap-1 rounded bg-emerald-500/15 px-2 py-0.5 font-medium text-emerald-700 hover:bg-emerald-500/25 dark:text-emerald-300">
                              <Download className="h-3 w-3" /> archivo anotado
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  {vp?.estado === 'borrador' && tienePermiso('documentos', 'editar') && (
                    <div className="w-full space-y-2">
                      {obsPendientes.length > 0 && (
                        <div className="space-y-1 rounded-lg border border-dashed border-amber-400/60 p-2 text-xs dark:border-amber-500/40">
                          <div className="flex items-center gap-2">
                            <span className="shrink-0 text-slate-500 dark:text-slate-400">Documento corregido:</span>
                            <input type="file" onChange={(e) => setArchivoCorregido(e.target.files[0])}
                              className="block w-full text-xs text-slate-500 file:mr-2 file:rounded-lg file:border-0 file:bg-slate-200 file:px-2 file:py-1 file:text-xs dark:file:bg-slate-700 dark:file:text-slate-200" />
                          </div>
                          {vp?.requiere_recarga && !archivoCorregido && (
                            <p className="text-[11px] text-amber-600 dark:text-amber-400">Adjunta el documento corregido para poder enviarlo a revisión.</p>
                          )}
                        </div>
                      )}
                      <button onClick={() => accion(enviarCorregido)} className="btn-primary !py-1.5 text-xs">
                        <Send className="h-3.5 w-3.5" /> {obsPendientes.length > 0 ? 'Firmar y enviar corregido a revisión' : 'Firmar y enviar a revisión'}
                      </button>
                    </div>
                  )}
                  {vp?.estado === 'en_revision' && tienePermiso('documentos', 'aprobar') && (
                    <>
                      <button onClick={() => accion(() => api.documentos.revisar(detalle.id, true, comentarios, passFirma))} className="btn-primary !py-1.5 text-xs">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Firmar revisión conforme
                      </button>
                      <button onClick={() => accion(() => api.documentos.revisar(detalle.id, false, comentarios, passFirma, archivoObs))} className="btn-secondary !py-1.5 text-xs">
                        <XCircle className="h-3.5 w-3.5" /> Devolver con observaciones
                      </button>
                      <button onClick={() => accion(() => api.documentos.rechazar(detalle.id, comentarios, archivoObs))} className="btn-danger !py-1.5 text-xs">
                        <XCircle className="h-3.5 w-3.5" /> Rechazar definitivamente
                      </button>
                    </>
                  )}
                  {vp?.estado === 'en_aprobacion' && tienePermiso('documentos', 'aprobar') && (
                    <>
                      <button onClick={() => accion(aprobarFirmado)} className="btn-primary !py-1.5 text-xs">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Firmar y aprobar → Vigente
                      </button>
                      <button onClick={() => accion(() => api.documentos.devolver(detalle.id, comentarios, archivoObs))} className="btn-secondary !py-1.5 text-xs">
                        <XCircle className="h-3.5 w-3.5" /> Devolver
                      </button>
                      <button onClick={() => accion(() => api.documentos.rechazar(detalle.id, comentarios, archivoObs))} className="btn-danger !py-1.5 text-xs">
                        <XCircle className="h-3.5 w-3.5" /> Rechazar definitivamente
                      </button>
                    </>
                  )}
                </div>
                {(vp?.estado === 'en_revision' || vp?.estado === 'en_aprobacion') && tienePermiso('documentos', 'aprobar') && (
                  <>
                    <input className="input-esynapse" placeholder="Comentarios (obligatorios para rechazar o devolver)"
                      value={comentarios} onChange={(e) => setComentarios(e.target.value)} />
                    <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                      <span className="shrink-0">Adjuntar archivo con anotaciones (opcional):</span>
                      <input type="file" onChange={(e) => setArchivoObs(e.target.files[0])}
                        className="block w-full text-xs text-slate-500 file:mr-2 file:rounded-lg file:border-0 file:bg-slate-200 file:px-2 file:py-1 file:text-xs dark:file:bg-slate-700 dark:file:text-slate-200" />
                    </div>
                  </>
                )}
                {((vp?.estado === 'borrador' && tienePermiso('documentos', 'editar')) ||
                  ((vp?.estado === 'en_revision' || vp?.estado === 'en_aprobacion') && tienePermiso('documentos', 'aprobar'))) && (
                  <input type="password" className="input-esynapse" autoComplete="current-password"
                    placeholder="Tu contraseña — segundo factor para firmar electrónicamente"
                    value={passFirma} onChange={(e) => setPassFirma(e.target.value)} />
                )}
                {vp?.estado === 'en_aprobacion' && tienePermiso('documentos', 'aprobar') && !(vp?.archivo || '').toLowerCase().endsWith('.pdf') && (
                  <div className="rounded-lg border border-dashed border-slate-300 p-2 text-xs dark:border-slate-700">
                    <p className="mb-1 text-slate-500 dark:text-slate-400">
                      El archivo es editable (Word/Excel). Si el servidor no tiene LibreOffice, adjunta el PDF exportado:
                    </p>
                    <input type="file" accept=".pdf" onChange={(e) => setPdfRespaldo(e.target.files[0])}
                      className="block w-full text-xs text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-200 file:px-3 file:py-1.5 file:text-xs dark:file:bg-slate-700 dark:file:text-slate-200" />
                  </div>
                )}
              </>
            )}

            {/* Verificación de vigencia (externos) */}
            {externo && tienePermiso('documentos', 'editar') && (
              <div className="space-y-2 rounded-lg border border-sky-500/30 bg-sky-500/5 p-3">
                <p className="flex items-center gap-2 text-xs font-medium text-sky-600 dark:text-sky-400">
                  <ShieldQuestion className="h-4 w-4" /> Registrar verificación de vigencia
                </p>
                <input className="input-esynapse" placeholder="Observaciones (ej: revisado portal INACAL, sin cambios)"
                  value={obsVerif} onChange={(e) => setObsVerif(e.target.value)} />
                <div className="flex gap-2">
                  <button onClick={() => accion(() => api.documentos.verificarVigencia(detalle.id, true, obsVerif))} className="btn-primary !py-1.5 text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Sigue vigente
                  </button>
                  <button onClick={() => accion(() => api.documentos.verificarVigencia(detalle.id, false, obsVerif))} className="btn-danger !py-1.5 text-xs">
                    <AlertTriangle className="h-3.5 w-3.5" /> Desactualizado
                  </button>
                </div>
                {detalle.verificaciones?.length > 0 && (
                  <div className="max-h-28 space-y-1 overflow-y-auto pt-1">
                    {detalle.verificaciones.map((vf) => (
                      <p key={vf.id} className="text-[11px] text-slate-500 dark:text-slate-400">
                        {new Date(vf.created_at).toLocaleString('es-PE')} — {vf.vigente ? '✓ vigente' : '✗ desactualizado'}
                        {vf.verificado_por ? ` — ${vf.verificado_por}` : ''}{vf.observaciones ? ` — ${vf.observaciones}` : ''}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Nueva versión / edición */}
            {((!externo && !vp && vv) || (externo && vv)) && tienePermiso('documentos', 'crear') && (
              <div className="space-y-2 rounded-lg border border-dashed border-slate-300 p-3 dark:border-slate-700">
                <p className="flex items-center gap-2 text-xs font-medium">
                  <FileUp className="h-4 w-4 text-esynapse-500" />
                  {externo
                    ? 'Registrar nueva edición del emisor (la actual pasará a Obsoleto)'
                    : `Crear nueva versión (la Ver. ${vv.version} sigue vigente hasta aprobarla)`}
                </p>
                <input type="file" onChange={(e) => setArchivoNV(e.target.files[0])}
                  className="block w-full text-xs text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-200 file:px-3 file:py-1.5 file:text-xs dark:file:bg-slate-700 dark:file:text-slate-200" />
                {externo && (
                  <input className="input-esynapse" placeholder="Edición del emisor (ej: 2024)" value={edicionNV}
                    onChange={(e) => setEdicionNV(e.target.value)} />
                )}
                <input className="input-esynapse" placeholder="Resumen de cambios" value={resumenNV} onChange={(e) => setResumenNV(e.target.value)} />
                <button disabled={!archivoNV || (externo && !edicionNV)} onClick={() => accion(subirNuevaVersion)} className="btn-primary !py-1.5 text-xs">
                  {externo ? 'Registrar edición' : 'Crear versión'}
                </button>
              </div>
            )}

            {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}

            {/* Acciones de ciclo de vida */}
            {tienePermiso('documentos', 'eliminar') && detalle.is_active && (
              <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                {!detalle.archivado ? (
                  <button onClick={() => setConfirmar({ tipo: 'archivar', doc: detalle })}
                    className="btn-secondary !py-1.5 text-xs">
                    <Archive className="h-3.5 w-3.5" /> Archivar documento
                  </button>
                ) : (
                  <button onClick={() => accion(() => api.documentos.desarchivar(detalle.id))}
                    className="btn-secondary !py-1.5 text-xs">
                    <FolderOpen className="h-3.5 w-3.5" /> Desarchivar (volver al uso activo)
                  </button>
                )}
                <button onClick={() => setConfirmar({ tipo: 'eliminar', doc: detalle })}
                  className="btn-danger !py-1.5 text-xs">
                  Eliminar (desactivar)
                </button>
                {!editandoCodigo ? (
                  <button onClick={() => { setNuevoCodigo(detalle.codigo); setEditandoCodigo(true) }}
                    className="btn-secondary !py-1.5 text-xs">
                    <Pencil className="h-3.5 w-3.5" /> Cambiar código
                  </button>
                ) : (
                  <div className="flex w-full items-center gap-2">
                    <input className="input-esynapse !py-1.5 w-48 font-mono text-xs" value={nuevoCodigo}
                      onChange={(e) => setNuevoCodigo(e.target.value)} />
                    <button onClick={() => accion(async () => {
                      await api.documentos.editar(detalle.id, { codigo: nuevoCodigo })
                      setEditandoCodigo(false)
                    })} className="btn-primary !py-1.5 text-xs">Guardar</button>
                    <button onClick={() => setEditandoCodigo(false)} className="btn-secondary !py-1.5 text-xs">Cancelar</button>
                  </div>
                )}
              </div>
            )}

            {/* Historial de versiones */}
            <div>
              <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                <FileText className="h-4 w-4" /> Historial de versiones
              </p>
              <div className="space-y-2">
                {detalle.versiones.map((v) => (
                  <div key={v.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800">
                    <div className="text-xs">
                      <p className="font-medium">
                        Ver. {v.version}{' '}
                        <span className={`ml-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${COLOR_ESTADO[v.estado_display] || 'bg-slate-500/15'}`}>
                          {v.estado_display}
                        </span>
                      </p>
                      <p className="text-slate-500 dark:text-slate-400">
                        {v.elaborado_por_nombre && `${externo ? 'Registró' : 'Elaboró'}: ${v.elaborado_por_nombre}`}
                        {v.revisado_por_nombre && ` · Revisó: ${v.revisado_por_nombre}`}
                        {v.aprobado_por_nombre && ` · Aprobó: ${v.aprobado_por_nombre}`}
                      </p>
                      {v.resumen_cambios && <p className="text-slate-500 dark:text-slate-400">Cambios: {v.resumen_cambios}</p>}
                      {v.comentarios_revision && <p className="text-amber-600 dark:text-amber-400">Obs: {v.comentarios_revision}</p>}
                      {(v.observaciones || []).length > 0 && (
                        <div className="mt-1 space-y-1">
                          {v.observaciones.map((o) => (
                            <p key={o.id} className={o.resuelta ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}>
                              ↩ {o.etapa_display} — {o.accion_display} por {o.autor} ({new Date(o.created_at).toLocaleDateString('es-PE')}): {o.comentarios}
                              {' '}<span className={`rounded px-1 py-0.5 text-[9px] font-medium ${o.resuelta ? 'bg-emerald-500/15' : 'bg-amber-500/15'}`}>{o.resuelta ? '✓ resuelta' : '⏳ pendiente'}</span>
                              {o.archivo_url && (
                                <a href={o.archivo_url} target="_blank" rel="noreferrer"
                                  className="ml-1 underline hover:text-amber-500">[archivo anotado]</a>
                              )}
                            </p>
                          ))}
                        </div>
                      )}
                      {(v.firmas || []).length > 0 && (
                        <p className="text-emerald-600 dark:text-emerald-400">
                          ✓ Firmas: {v.firmas.map((fi) => `${fi.rol_display} (${fi.firmante})`).join(' · ')}
                        </p>
                      )}
                      {(v.historial_archivos || []).length > 0 && (
                        <div className="mt-1 rounded-lg bg-slate-100 p-2 dark:bg-slate-800/60">
                          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Bitácora de archivos</p>
                          {v.historial_archivos.map((a) => (
                            <p key={a.id} className="text-[11px] text-slate-500 dark:text-slate-400">
                              <FileText className="mr-1 inline h-3 w-3" />{a.origen_display}
                              {a.autor ? ` · ${a.autor}` : ''} ({new Date(a.created_at).toLocaleDateString('es-PE')})
                              {a.archivo_url && (
                                <a href={a.archivo_url} target="_blank" rel="noreferrer"
                                  className="ml-1 text-esynapse-500 underline hover:text-esynapse-400">descargar</a>
                              )}
                            </p>
                          ))}
                        </div>
                      )}
                      {v.hash_publicado && (
                        <p className="font-mono text-[10px] text-slate-400" title={v.hash_publicado}>
                          SHA-256: {v.hash_publicado.slice(0, 16)}…
                        </p>
                      )}
                    </div>
                    <div className="flex gap-1">
                      {(v.archivo_publicado_url || (v.archivo_url && esPdf(v.archivo_url))) && (
                        <button onClick={() => setVisor({ titulo: `${detalle.codigo} Ver. ${v.version}${v.archivo_publicado_url ? ' (firmado)' : ''}`, url: v.archivo_publicado_url || v.archivo_url })}
                          title={v.archivo_publicado_url ? 'Ver PDF firmado' : 'Ver en el sistema'}
                          className="rounded p-1.5 text-slate-500 hover:bg-slate-100 hover:text-esynapse-500 dark:hover:bg-slate-800">
                          <Eye className="h-4 w-4" />
                        </button>
                      )}
                      {(v.archivo_publicado_url || v.archivo_url) && (
                        <a href={v.archivo_publicado_url || v.archivo_url} target="_blank" rel="noreferrer"
                          title={v.archivo_publicado_url ? 'Descargar PDF firmado' : 'Descargar'}
                          className="rounded p-1.5 text-slate-500 hover:bg-slate-100 hover:text-esynapse-500 dark:hover:bg-slate-800">
                          <Download className="h-4 w-4" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Confirmación de archivar/eliminar */}
      <Modal abierto={Boolean(confirmar)} titulo={confirmar?.tipo === 'archivar' ? 'Archivar documento' : 'Eliminar documento'}
        onCerrar={() => setConfirmar(null)}>
        {confirmar && (
          <div className="space-y-4 text-sm">
            {confirmar.tipo === 'archivar' ? (
              <p>
                ¿Archivar <strong>{confirmar.doc.codigo}</strong>? Se retira del uso activo pero se
                conserva consultable durante su periodo de retención ({retencionTexto(confirmar.doc.anos_retencion)}),
                con todo su historial de versiones y firmas. Es reversible.
              </p>
            ) : (
              <p>
                ¿Eliminar <strong>{confirmar.doc.codigo}</strong>? El documento se desactiva (no se borra
                físicamente — queda en "Incluir inactivos") y <strong>su código se libera</strong> para
                que puedas reutilizarlo en el documento correcto. Usa esta opción para registros creados
                por error; para retirar un documento que cumplió su ciclo, usa <strong>Archivar</strong>.
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmar(null)} className="btn-secondary">Cancelar</button>
              <button
                onClick={async () => {
                  const { tipo, doc } = confirmar
                  setConfirmar(null)
                  await accion(() => tipo === 'archivar'
                    ? api.documentos.archivar(doc.id)
                    : api.documentos.desactivar(doc.id))
                  if (tipo === 'eliminar') setDetalle(null)
                  await cargar()
                }}
                className={confirmar.tipo === 'archivar' ? 'btn-primary' : 'btn-danger'}>
                {confirmar.tipo === 'archivar' ? 'Archivar' : 'Eliminar'}
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Visor de PDF integrado */}
      <Modal abierto={Boolean(visor)} titulo={visor?.titulo || ''} onCerrar={() => setVisor(null)} ancho="max-w-5xl">
        {visor && (
          <iframe src={visor.url} title={visor.titulo} className="h-[75vh] w-full rounded-lg border border-slate-200 dark:border-slate-800" />
        )}
      </Modal>
    </div>
  )
}

function Dato({ label, valor, mono = false }) {
  return (
    <div>
      <p className="mb-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 ${mono ? 'font-mono' : ''}`}>{valor || '—'}</p>
    </div>
  )
}

function CampoEdit({ label, valor, onChange }) {
  return (
    <div>
      <label className="mb-0.5 block text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</label>
      <input className="input-esynapse" value={valor} onChange={(e) => onChange(e.target.value)} />
    </div>
  )
}

function retencionTexto(a) {
  return (a === 0 || a == null) ? 'Sujeto a Nueva Versión' : `${a} ${a === 1 ? 'año' : 'años'}`
}
// M6: edición de ficha con autorización por contraseña + auditoría (updated_by/updated_at)
