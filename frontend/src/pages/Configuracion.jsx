import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Building2, FileText, FolderTree, Lock, Palette, Power, Puzzle, Save } from 'lucide-react'
import { api } from '../lib/api.js'
import { useConfig } from '../context/ConfigContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import Pestanas from '../components/ui/Pestanas.jsx'

const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
const archivo = 'block w-full text-xs text-slate-500 file:mr-2 file:rounded-lg file:border-0 file:bg-slate-200 file:px-2 file:py-1 file:text-xs dark:file:bg-slate-700 dark:file:text-slate-200'

const nombreModulo = (m) => { const t = (m || '').replace(/_/g, ' '); return t.charAt(0).toUpperCase() + t.slice(1) }

function Seccion({ titulo, descripcion, children, className = '' }) {
  return (
    <section className={`card-esynapse p-5 ${className}`}>
      <h2 className="text-base font-semibold">{titulo}</h2>
      {descripcion && <p className="mb-4 mt-0.5 text-xs text-slate-500 dark:text-slate-400">{descripcion}</p>}
      {children}
    </section>
  )
}

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
  const [pestana, setPestana] = useState('empresa')
  const [modF, setModF] = useState('')
  const [buscarF, setBuscarF] = useState('')
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

  const campo = (k, n, extra = {}) => (
    <div className={extra.className || ''}>
      <label className={lbl}>{n}</label>
      <input className="input-esynapse" placeholder={extra.placeholder} value={marca[k]} onChange={(e) => setMarca({ ...marca, [k]: e.target.value })} />
    </div>
  )
  const guardarBtn = <button onClick={guardarMarca} className="btn-primary !py-1.5 text-xs"><Save className="h-3.5 w-3.5" /> Guardar cambios</button>
  const pestanas = [['empresa', 'Empresa', Building2], ...(esPropietario ? [['producto', 'Producto', Palette]] : []), ['formatos', 'Formatos impresos', FileText], ['modulos', 'Módulos', Puzzle]]

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <TituloModulo seccion="Administración" titulo="Configuración del sistema" descripcion="Datos de la empresa, formatos impresos y módulos habilitados." />
          {config?.version && (
            <span className="ml-auto rounded bg-slate-500/15 px-2 py-0.5 font-mono text-xs text-slate-500 dark:text-slate-400" title="Versión instalada">v{config.version}</span>
          )}
        </div>
        <Pestanas opciones={pestanas} valor={pestana} onChange={(k) => { setMsg(''); setError(''); setPestana(k) }} />
      </div>

      {msg && <p className="rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-400">{msg}</p>}
      {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500">{error}</p>}

      {pestana === 'empresa' && (
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Seccion titulo="Datos de la empresa" descripcion="Se imprimen en los formatos y encabezados del sistema.">
              <div className="grid gap-3">
                {campo('subtitulo', 'Nombre de la empresa')}
                {campo('direccion', 'Dirección (formatos de auditoría y SST)')}
                {campo('responsable_sig', 'Responsable del Sistema Integrado de Gestión')}
                <div>
                  <label className={lbl}>Logo de la empresa (formatos PDF)</label>
                  <div className="flex items-center gap-3">
                    {logoEmpresaUrl && <img src={logoEmpresaUrl} alt="logo empresa" className="h-12 w-12 rounded object-contain" />}
                    <input type="file" accept="image/*" onChange={(e) => setLogoEmpresa(e.target.files[0])} className={archivo} />
                  </div>
                </div>
              </div>
            </Seccion>
            <Seccion titulo="Datos del empleador" descripcion="Registros oficiales de SST: accidentes, incidentes, estadísticas, programa anual.">
              <div className="grid gap-3 md:grid-cols-2">
                {campo('razon_social', 'Razón social', { className: 'md:col-span-2' })}
                {campo('ruc', 'RUC')}
                {campo('aseguradora_sctr', 'Aseguradora del SCTR')}
                {campo('actividad_economica', 'Actividad económica (CIIU)', { className: 'md:col-span-2' })}
              </div>
            </Seccion>
          </div>
          <div className="flex items-center gap-3">
            {guardarBtn}
            <p className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400"><FolderTree className="h-3.5 w-3.5" /> Sedes, áreas, laboratorios, puestos y trabajadores se mantienen en <Link to="/organizacion" className="text-esynapse-500 underline">Organización y personal</Link>.</p>
          </div>
        </div>
      )}

      {pestana === 'producto' && esPropietario && (
        <Seccion titulo="Identidad del producto" descripcion="Nombre, sigla y logo del sistema (los define el propietario).">
          <div className="grid gap-3 md:grid-cols-2">
            {campo('nombre_sistema', 'Nombre del sistema (producto)')}
            {campo('nombre_corto', 'Nombre corto / sigla')}
            <div className="md:col-span-2">
              <label className={lbl}>Logo del producto</label>
              <div className="flex items-center gap-3">
                {logoUrl && <img src={logoUrl} alt="logo" className="h-10 w-10 rounded object-contain" />}
                <input type="file" accept="image/*" onChange={(e) => setLogo(e.target.files[0])} className={archivo} />
              </div>
            </div>
          </div>
          <div className="mt-4">{guardarBtn}</div>
        </Seccion>
      )}

      {pestana === 'formatos' && (
        <div className="space-y-4">
          <Seccion titulo="Vínculo con la lista maestra" descripcion="Cada PDF del sistema corresponde a un formato del SIG. Vinculado a su documento de la lista maestra, la caja de control imprime el código, la versión vigente, su fecha y las siglas de quien elaboró, revisó y aprobó; al aprobar una nueva versión en Documentos, el PDF la toma sola. Sin vínculo se usan los valores de respaldo.">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <select className="input-esynapse w-56 !py-1 text-xs" value={modF} onChange={(e) => setModF(e.target.value)}><option value="">Todos los módulos ({formatos.length})</option>{[...new Set(formatos.map((f) => f.modulo))].sort().map((m) => <option key={m} value={m}>{nombreModulo(m)} ({formatos.filter((f) => f.modulo === m).length})</option>)}</select>
              <input className="input-esynapse w-64 !py-1 text-xs" placeholder="Buscar formato o código" value={buscarF} onChange={(e) => setBuscarF(e.target.value)} />
              <span className="text-[11px] text-slate-500">{formatos.filter((f) => f.control?.origen === 'lista_maestra').length} de {formatos.length} vinculados a la lista maestra</span>
            </div>
            <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
              <table className="tabla-sig w-full text-xs">
                <thead><tr><th>Formato</th><th>Código</th><th>Documento de la lista maestra</th><th className="text-center">Imprime</th></tr></thead>
                <tbody>
                  {formatos.filter((f) => (!modF || f.modulo === modF) && (!buscarF || `${f.nombre} ${f.codigo_sgc}`.toLowerCase().includes(buscarF.toLowerCase()))).map((f) => {
                    const c = f.control || {}
                    const origen = { lista_maestra: ['Lista maestra', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'], tabla: ['Respaldo', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'], global: ['Por defecto', 'bg-slate-500/15 text-slate-500'] }[c.origen] || ['', '']
                    return (
                      <tr key={f.id}>
                        <td><p className="font-medium">{f.nombre}</p><p className="text-[11px] text-slate-500 dark:text-slate-400">{nombreModulo(f.modulo)}</p></td>
                        <td className="font-mono">{f.codigo_sgc}</td>
                        <td>
                          <select className="input-esynapse !py-1 text-xs" value={f.documento || ''} onChange={(e) => vincularFormato(f, e.target.value)}>
                            <option value="">— Sin vínculo (usar respaldo) —</option>
                            {documentos.map((d) => <option key={d.id} value={d.id}>{d.codigo} — {d.titulo}</option>)}
                          </select>
                        </td>
                        <td className="whitespace-nowrap text-center">
                          <span className="font-mono">{c.codigo}</span> · v{c.version} · {c.fecha}
                          <span className="ml-1 text-slate-400">{c.elaborado} / {c.revisado} / {c.aprobado}</span>
                          {origen[0] && <span className={`ml-2 whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] ${origen[1]}`}>{origen[0]}</span>}
                        </td>
                      </tr>
                    )
                  })}
                  {formatos.length === 0 && <tr><td colSpan={4} className="py-4 text-center text-slate-400">Sin formatos registrados.</td></tr>}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[11px] text-slate-400">Las siglas se toman de la sigla del puesto de cada firmante (Organización y personal). Si no la tiene, se usa el respaldo.</p>
          </Seccion>
          <Seccion titulo="Siglas de respaldo" descripcion="Se imprimen cuando un formato no está vinculado a la lista maestra o el firmante no tiene sigla.">
            <div className="grid gap-3 md:grid-cols-3">
              {[['formato_hv_elaborado', 'Elaborado', 'ASIG'], ['formato_hv_revisado', 'Revisado', 'GSIG/GT'], ['formato_hv_aprobado', 'Aprobado', 'GG']].map(([k, n, ph]) => (
                <div key={k}><label className={lbl}>Sigla {n}</label><input className="input-esynapse" value={formato[k]} placeholder={ph} onChange={(e) => setFormato({ ...formato, [k]: e.target.value })} /></div>
              ))}
            </div>
            <div className="mt-4">{guardarBtn}</div>
          </Seccion>
        </div>
      )}

      {pestana === 'modulos' && (esPropietario ? (
        <Seccion titulo="Módulos habilitados (licenciamiento)" descripcion="Activa o desactiva módulos para esta instalación. Las dependencias se respetan automáticamente.">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {modulos.map((m) => (
              <div key={m.clave} className={`flex items-center justify-between gap-2 rounded-lg border px-3 py-2 ${m.habilitado ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-slate-200 dark:border-slate-800'}`}>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{m.nombre}</p>
                  {m.dependencias?.length > 0 && <p className="text-[11px] text-slate-500 dark:text-slate-400">Requiere: {m.dependencias.map(nombreDe).join(', ')}</p>}
                </div>
                <button onClick={() => toggle(m)} className={`flex shrink-0 items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition ${m.habilitado ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-slate-200 text-slate-500 dark:bg-slate-800'}`}>
                  <Power className="h-3.5 w-3.5" /> {m.habilitado ? 'Activo' : 'Inactivo'}
                </button>
              </div>
            ))}
          </div>
          <p className="mt-3 flex items-center gap-1 text-[11px] text-slate-400"><Lock className="h-3 w-3" /> Usuarios y Configuración son módulos núcleo: siempre activos.</p>
        </Seccion>
      ) : (
        <div className="card-esynapse flex items-start gap-2 p-5 text-xs text-slate-500 dark:text-slate-400">
          <Lock className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Los módulos activos los gestiona únicamente el <strong>propietario del sistema</strong>.</span>
        </div>
      ))}
    </div>
  )
}
