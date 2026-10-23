import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { SlidersHorizontal, Save, Power, Lock, FolderTree } from 'lucide-react'
import { api } from '../lib/api.js'
import { useConfig } from '../context/ConfigContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import TituloModulo from '../components/ui/TituloModulo.jsx'

export default function Configuracion() {
  const { recargarConfig, config } = useConfig()
  const { usuario } = useAuth()
  const esPropietario = Boolean(usuario?.is_superuser)
  const [marca, setMarca] = useState({ nombre_sistema: '', nombre_corto: '', subtitulo: '', color_primario: '', direccion: '', responsable_sig: '', razon_social: '', ruc: '', actividad_economica: '', aseguradora_sctr: '' })
  const [logo, setLogo] = useState(null)
  const [logoUrl, setLogoUrl] = useState(null)
  const [logoEmpresa, setLogoEmpresa] = useState(null)
  const [logoEmpresaUrl, setLogoEmpresaUrl] = useState(null)
  const [formato, setFormato] = useState({ formato_hv_codigo: '', formato_hv_elaborado: '', formato_hv_revisado: '', formato_hv_aprobado: '' })
  const [documentos, setDocumentos] = useState([])
  const [formatos, setFormatos] = useState([])
  const cargarFormatos = () => api.formatosImpresos.listar().then((d) => setFormatos(d.results ?? d)).catch(() => {})
  useEffect(() => { cargarFormatos() }, [])
  const vincularFormato = async (f, documento) => {
    setError(''); setMsg('')
    try { await api.formatosImpresos.vincular(f.id, documento ? Number(documento) : null); await cargarFormatos(); setMsg(`"${f.nombre}" actualizado.`) }
    catch (e) { setError(e.message) }
  }
  const [modulos, setModulos] = useState([])
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const cargar = async () => {
    const c = await api.config.obtener()
    setMarca({ nombre_sistema: c.nombre_sistema || '', nombre_corto: c.nombre_corto || '', subtitulo: c.subtitulo || '', color_primario: c.color_primario || '', direccion: c.direccion || '', responsable_sig: c.responsable_sig || '', razon_social: c.razon_social || '', ruc: c.ruc || '', actividad_economica: c.actividad_economica || '', aseguradora_sctr: c.aseguradora_sctr || '' })
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
      fd.append('direccion', marca.direccion)
      fd.append('responsable_sig', marca.responsable_sig)
      ;['razon_social', 'ruc', 'actividad_economica', 'aseguradora_sctr'].forEach((k) => fd.append(k, marca[k]))
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
      <div className="flex flex-wrap items-center gap-2">
        <TituloModulo seccion="Administración" titulo="Configuración del sistema" />
        {config?.version && (
          <span className="ml-auto rounded bg-slate-500/15 px-2 py-0.5 font-mono text-xs text-slate-500 dark:text-slate-400"
            title="Versión instalada (backend/VERSION)">
            v{config.version}
          </span>
        )}
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
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Dirección de la empresa (aparece en los formatos de auditoría)</label>
            <input className="input-esynapse" value={marca.direccion} onChange={(e) => setMarca({ ...marca, direccion: e.target.value })} />
          </div>
          <div className="md:col-span-2 grid gap-3 rounded-lg border border-slate-200 p-3 md:grid-cols-4 dark:border-slate-800">
            <p className="text-xs font-semibold text-slate-500 md:col-span-4">Datos del empleador (registros oficiales de SST: accidentes, incidentes, estadísticas)</p>
            {[['razon_social', 'Razón social', 'md:col-span-2'], ['ruc', 'RUC', ''], ['aseguradora_sctr', 'Aseguradora del SCTR', ''], ['actividad_economica', 'Actividad económica (CIIU)', 'md:col-span-4']].map(([k, n, c]) => (
              <div key={k} className={c}>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">{n}</label>
                <input className="input-esynapse" value={marca[k]} onChange={(e) => setMarca({ ...marca, [k]: e.target.value })} />
              </div>
            ))}
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Responsable del Sistema Integrado de Gestión</label>
            <input className="input-esynapse" value={marca.responsable_sig} onChange={(e) => setMarca({ ...marca, responsable_sig: e.target.value })} />
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

      {/* Formatos impresos: vínculo con la lista maestra (caja de control de cada PDF) */}
      <div className="card-esynapse p-5">
        <h2 className="mb-1 text-lg font-semibold">Formatos impresos</h2>
        <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
          Cada PDF que genera el sistema corresponde a un formato del SIG. Vincúlalo con su documento de la <strong>lista maestra</strong>: la caja de control del PDF tomará el código, la <strong>versión vigente</strong>, su fecha y las siglas de quien elaboró, revisó y aprobó esa versión. Al aprobar una nueva versión en Documentos, todos los PDF la imprimen automáticamente. Sin vínculo, se usan los valores de respaldo.
        </p>
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="tabla-sig w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
                <th className="px-3 py-2">Formato</th>
                <th className="px-3 py-2">Código</th>
                <th className="px-3 py-2">Documento de la lista maestra</th>
                <th className="px-3 py-2 text-center">Imprime</th>
              </tr>
            </thead>
            <tbody>
              {formatos.map((f) => {
                const c = f.control || {}
                const origen = { lista_maestra: ['Lista maestra', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'], tabla: ['Respaldo', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'], global: ['Por defecto', 'bg-slate-500/15 text-slate-500'] }[c.origen] || ['', '']
                return (
                  <tr key={f.id} className="border-t border-slate-100 dark:border-slate-800/60">
                    <td className="px-3 py-2">
                      <p className="font-medium">{f.nombre}</p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">{f.modulo}</p>
                    </td>
                    <td className="px-3 py-2 font-mono">{f.codigo_sgc}</td>
                    <td className="px-3 py-2">
                      <select className="input-esynapse !py-1 text-xs" value={f.documento || ''} onChange={(e) => vincularFormato(f, e.target.value)}>
                        <option value="">— Sin vínculo (usar respaldo) —</option>
                        {documentos.map((d) => <option key={d.id} value={d.id}>{d.codigo} — {d.titulo}</option>)}
                      </select>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-center">
                      <span className="font-mono">{c.codigo}</span> · v{c.version} · {c.fecha}
                      <span className="ml-1 text-slate-400">{c.elaborado} / {c.revisado} / {c.aprobado}</span>
                      {origen[0] && <span className={`ml-2 whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] ${origen[1]}`}>{origen[0]}</span>}
                    </td>
                  </tr>
                )
              })}
              {formatos.length === 0 && <tr><td colSpan={4} className="px-3 py-4 text-center text-slate-400">Sin formatos registrados (aplica la actualización de base de datos).</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[11px] text-slate-400">Las siglas se toman de la "sigla del cargo" de cada usuario (Usuarios). Si un firmante no la tiene, se usa el respaldo.</p>

        <h3 className="mb-1 mt-5 text-sm font-semibold">Siglas de respaldo</h3>
        <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">Se imprimen cuando un formato no está vinculado a la lista maestra o el firmante no tiene sigla.</p>
        <div className="grid gap-3 md:grid-cols-3">
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

      {/* Áreas, laboratorios y puestos: ahora en Organización y personal (núcleo) */}
      <div className="card-esynapse p-5">
        <div className="mb-1 flex items-center gap-2">
          <FolderTree className="h-5 w-5 text-esynapse-500" />
          <h2 className="text-lg font-semibold">Áreas, laboratorios y puestos</h2>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Se mantienen en <Link to="/organizacion" className="text-esynapse-500 underline">Organización y personal</Link> (menú Administración),
          junto con los trabajadores. Todos los módulos usan esas mismas listas.
        </p>
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
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">Requiere: {m.dependencias.map(nombreDe).join(', ')}</p>
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
