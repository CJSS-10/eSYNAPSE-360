import { useEffect, useState } from 'react'
import { SlidersHorizontal, Save, Power, Lock, FolderTree } from 'lucide-react'
import { api } from '../lib/api.js'
import { useConfig } from '../context/ConfigContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import GestionCatalogo from '../components/ui/GestionCatalogo.jsx'

export default function Configuracion() {
  const { recargarConfig } = useConfig()
  const { usuario } = useAuth()
  const esPropietario = Boolean(usuario?.is_superuser)
  const [marca, setMarca] = useState({ nombre_sistema: '', nombre_corto: '', subtitulo: '', color_primario: '' })
  const [logo, setLogo] = useState(null)
  const [logoUrl, setLogoUrl] = useState(null)
  const [logoEmpresa, setLogoEmpresa] = useState(null)
  const [logoEmpresaUrl, setLogoEmpresaUrl] = useState(null)
  const [formato, setFormato] = useState({ formato_hv_codigo: '', formato_hv_elaborado: '', formato_hv_revisado: '', formato_hv_aprobado: '' })
  const [documentos, setDocumentos] = useState([])
  const [modulos, setModulos] = useState([])
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const cargar = async () => {
    const c = await api.config.obtener()
    setMarca({ nombre_sistema: c.nombre_sistema || '', nombre_corto: c.nombre_corto || '', subtitulo: c.subtitulo || '', color_primario: c.color_primario || '' })
    setLogoUrl(c.logo_url)
    setLogoEmpresaUrl(c.logo_empresa_url)
    setFormato({ formato_hv_codigo: c.formato_hv_codigo || '', formato_hv_elaborado: c.formato_hv_elaborado || '', formato_hv_revisado: c.formato_hv_revisado || '', formato_hv_aprobado: c.formato_hv_aprobado || '' })
    try { const d = await api.documentos.listar(); setDocumentos(d.results ?? d) } catch (e) { /* documentos opcional */ }
    if (usuario?.is_superuser) {
      const m = await api.config.modulos()
      setModulos(m.modulos || [])
    }
  }
  useEffect(() => { cargar().catch((e) => setError(e.message)) }, [])

  const guardarMarca = async () => {
    setError(''); setMsg('')
    try {
      const fd = new FormData()
      if (esPropietario) {
        Object.entries(marca).forEach(([k, v]) => fd.append(k, v))
        if (logo) fd.append('logo', logo)
      } else {
        fd.append('subtitulo', marca.subtitulo)
      }
      if (logoEmpresa) fd.append('logo_empresa', logoEmpresa)
      Object.entries(formato).forEach(([k, v]) => fd.append(k, v))
      await api.config.actualizar(fd)
      setMsg('Marca actualizada. Recarga la página para verla en todo el sistema.')
      setLogo(null); setLogoEmpresa(null)
      await recargarConfig()
      await cargar()
    } catch (e) { setError(e.message) }
  }

  const toggle = async (m) => {
    setError(''); setMsg('')
    try {
      const r = await api.config.toggleModulo(m.clave, !m.habilitado)
      setModulos(r.modulos || [])
      if (r.activados_en_cascada?.length) setMsg(`También se activaron (por dependencia): ${r.activados_en_cascada.join(', ')}`)
      await recargarConfig()
    } catch (e) { setError(e.message) }
  }

  const nombreDe = (clave) => modulos.find((x) => x.clave === clave)?.nombre || clave

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <SlidersHorizontal className="h-6 w-6 text-esynapse-500" />
        <h1 className="text-2xl font-bold">Configuración del sistema</h1>
      </div>

      {msg && <p className="rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-400">{msg}</p>}
      {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500">{error}</p>}

      {/* Marca */}
      <div className="card-esynapse p-5">
        <h2 className="mb-1 text-lg font-semibold">Identidad</h2>
        <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
          {esPropietario
            ? 'Identidad del producto (nombre, sigla, logo) y nombre de la empresa cliente.'
            : 'El nombre del sistema y el logo los define el propietario. Aquí puedes ajustar el nombre de tu empresa.'}
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          {esPropietario && (
            <>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Nombre del sistema (producto)</label>
                <input className="input-esynapse" value={marca.nombre_sistema} onChange={(e) => setMarca({ ...marca, nombre_sistema: e.target.value })} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Nombre corto / sigla</label>
                <input className="input-esynapse" value={marca.nombre_corto} onChange={(e) => setMarca({ ...marca, nombre_corto: e.target.value })} />
              </div>
            </>
          )}
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Nombre de la empresa</label>
            <input className="input-esynapse" value={marca.subtitulo} onChange={(e) => setMarca({ ...marca, subtitulo: e.target.value })} />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Logo de la empresa (aparece en tus formatos PDF)</label>
            <div className="flex items-center gap-3">
              {logoEmpresaUrl && <img src={logoEmpresaUrl} alt="logo empresa" className="h-12 w-12 rounded object-contain" />}
              <input type="file" accept="image/*" onChange={(e) => setLogoEmpresa(e.target.files[0])}
                className="block w-full text-xs text-slate-500 file:mr-2 file:rounded-lg file:border-0 file:bg-slate-200 file:px-2 file:py-1 file:text-xs dark:file:bg-slate-700 dark:file:text-slate-200" />
            </div>
          </div>
          {esPropietario && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Logo del producto</label>
              <div className="flex items-center gap-3">
                {logoUrl && <img src={logoUrl} alt="logo" className="h-10 w-10 rounded object-contain" />}
                <input type="file" accept="image/*" onChange={(e) => setLogo(e.target.files[0])}
                  className="block w-full text-xs text-slate-500 file:mr-2 file:rounded-lg file:border-0 file:bg-slate-200 file:px-2 file:py-1 file:text-xs dark:file:bg-slate-700 dark:file:text-slate-200" />
              </div>
            </div>
          )}
        </div>
        <button onClick={guardarMarca} className="btn-primary mt-4 !py-1.5 text-xs"><Save className="h-3.5 w-3.5" /> Guardar</button>
      </div>

      {/* Formato de Hoja de Vida (Equipos) */}
      <div className="card-esynapse p-5">
        <h2 className="mb-1 text-lg font-semibold">Formato de Hoja de Vida (Equipos)</h2>
        <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">Vincula el formato con un documento de la lista maestra: el PDF tomará su código, su versión vigente y la fecha de aprobación. Las siglas son los roles que firman.</p>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="md:col-span-3">
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Documento del formato (lista maestra)</label>
            <select className="input-esynapse" value={formato.formato_hv_codigo} onChange={(e) => setFormato({ ...formato, formato_hv_codigo: e.target.value })}>
              <option value="">— Usar valores por defecto —</option>
              {documentos.map((d) => <option key={d.id} value={d.codigo}>{d.codigo} — {d.titulo}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Sigla Elaborado</label>
            <input className="input-esynapse" value={formato.formato_hv_elaborado} onChange={(e) => setFormato({ ...formato, formato_hv_elaborado: e.target.value })} placeholder="ASIG" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Sigla Revisado</label>
            <input className="input-esynapse" value={formato.formato_hv_revisado} onChange={(e) => setFormato({ ...formato, formato_hv_revisado: e.target.value })} placeholder="GSIG/GT" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Sigla Aprobado</label>
            <input className="input-esynapse" value={formato.formato_hv_aprobado} onChange={(e) => setFormato({ ...formato, formato_hv_aprobado: e.target.value })} placeholder="GG" />
          </div>
        </div>
        <button onClick={guardarMarca} className="btn-primary mt-4 !py-1.5 text-xs"><Save className="h-3.5 w-3.5" /> Guardar</button>
      </div>

      {/* Áreas y Laboratorios — catálogo de los desplegables de Usuarios */}
      <div className="card-esynapse p-5">
        <div className="mb-1 flex items-center gap-2">
          <FolderTree className="h-5 w-5 text-esynapse-500" />
          <h2 className="text-lg font-semibold">Áreas y Laboratorios</h2>
        </div>
        <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
          Estas listas alimentan los desplegables de la ficha de usuario. Renombra para corregir un error,
          quita las que sobran o agrega nuevas. Quitar una opción solo la oculta del desplegable; no afecta a los usuarios que ya la tengan asignada.
        </p>
        <div className="grid gap-6 md:grid-cols-2">
          <GestionCatalogo tipo="area" titulo="Áreas" singular="área" />
          <GestionCatalogo tipo="laboratorio" titulo="Laboratorios" singular="laboratorio" />
        </div>
      </div>

      {/* Módulos — SOLO el propietario del sistema (superusuario) */}
      {esPropietario ? (
      <div className="card-esynapse p-5">
        <h2 className="mb-1 text-lg font-semibold">Módulos habilitados (licenciamiento)</h2>
        <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">Activa o desactiva módulos para esta instalación. Útil para vender el sistema por partes. Las dependencias se respetan automáticamente.</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {modulos.map((m) => (
            <div key={m.clave} className={`flex items-center justify-between rounded-lg border px-3 py-2 ${m.habilitado ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-slate-200 dark:border-slate-800'}`}>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{m.nombre}</p>
                {m.dependencias?.length > 0 && (
                  <p className="text-[10px] text-slate-400">Requiere: {m.dependencias.map(nombreDe).join(', ')}</p>
                )}
              </div>
              <button onClick={() => toggle(m)}
                className={`flex shrink-0 items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                  m.habilitado ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-slate-200 text-slate-500 dark:bg-slate-800'}`}>
                <Power className="h-3.5 w-3.5" /> {m.habilitado ? 'Activo' : 'Inactivo'}
              </button>
            </div>
          ))}
        </div>
        <p className="mt-3 flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Usuarios y Configuración son módulos núcleo: siempre activos.</p>
      </div>
      ) : (
        <div className="card-esynapse flex items-start gap-2 p-5 text-xs text-slate-500 dark:text-slate-400">
          <Lock className="mt-0.5 h-4 w-4 shrink-0" />
          <span>El licenciamiento de módulos (qué módulos están activos) lo gestiona únicamente el <strong>propietario del sistema</strong>. Como administrador de sistema puedes gestionar la marca, los usuarios y los roles.</span>
        </div>
      )}
    </div>
  )
}
