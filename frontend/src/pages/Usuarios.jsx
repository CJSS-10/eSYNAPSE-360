import { useCallback, useEffect, useState } from 'react'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import { ImagePlus, KeyRound, Pencil, Plus, RotateCcw, Search, UserX } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import Avatar from '../components/ui/Avatar.jsx'
import CampoSugerencias from '../components/CampoSugerencias.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import TituloModulo from '../components/ui/TituloModulo.jsx'

const FORM_VACIO = {
  username: '', first_name: '', last_name: '', email: '',
  area: '', laboratorio: '', cargo: '', sigla_cargo: '', telefono: '', roles: [], foto: null, trabajador: '',
}

export default function Usuarios() {
  const { tienePermiso } = useAuth()
  const [usuarios, setUsuarios] = useState([])
  const [roles, setRoles] = useState([])
  const [buscar, setBuscar] = useState('')
  const [verInactivos, setVerInactivos] = useState(false)
  const [modal, setModal] = useState(null) // null | 'crear' | usuario a editar
  const [form, setForm] = useState(FORM_VACIO)
  const [error, setError] = useState('')
  const [passwordTemporal, setPasswordTemporal] = useState(null)
  const [confirmar, setConfirmar] = useState(null)
  const [fotoPreview, setFotoPreview] = useState(null)

  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const params = new URLSearchParams()
    if (verInactivos) params.set('incluir_inactivos', '1')
    if (buscar) params.set('buscar', buscar)
    const data = await ultima(api.usuarios.listar(`?${params}`))
    setUsuarios(data.results ?? data)
  }, [buscar, verInactivos])

  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
    api.roles.listar().then((d) => setRoles(d.results ?? d)).catch(() => {})
  }, [])
  // Organización y personal: el usuario se vincula a su trabajador y toma cargo, sigla y área del puesto.
  const [trabajadores, setTrabajadores] = useState([])
  const [areasOrg, setAreasOrg] = useState([])
  const [puestosOrg, setPuestosOrg] = useState([])
  useEffect(() => {
    if (!modal) return
    api.org.trabajadores().then(setTrabajadores).catch(() => {})
    api.org.areas().then(setAreasOrg).catch(() => {})
    api.org.puestos().then(setPuestosOrg).catch(() => {})
  }, [modal])
  const trabSel = trabajadores.find((t) => t.id === Number(form.trabajador))
  const trabDisponibles = trabajadores.filter((t) => !t.usuario || (modal && modal !== 'crear' && t.usuario === modal.id))

  const abrirCrear = () => { setForm(FORM_VACIO); setFotoPreview(null); setError(''); setModal('crear') }
  const abrirEditar = (u) => {
    setForm({
      username: u.username, first_name: u.first_name, last_name: u.last_name,
      email: u.email, area: u.area, laboratorio: u.laboratorio, cargo: u.cargo, sigla_cargo: u.sigla_cargo || '',
      telefono: u.telefono, roles: (u.roles || []).map((r) => r.id), foto: null, trabajador: u.trabajador_info?.id || '',
    })
    setFotoPreview(u.foto_url || null)
    setError('')
    setModal(u)
  }

  const guardar = async (e) => {
    e.preventDefault()
    setError('')
    try {
      if (modal === 'crear') {
        const creado = await api.usuarios.crear({ ...form, trabajador: form.trabajador || null })
        if (creado.password_temporal) setPasswordTemporal({ usuario: creado.username, clave: creado.password_temporal })
      } else {
        const { roles: rolesIds, username, foto, ...resto } = form
        const datos = { ...resto, trabajador: resto.trabajador || null }
        if (foto) {
          const fd = new FormData()
          Object.entries(datos).forEach(([k, v]) => fd.append(k, v ?? ''))
          fd.append('foto', foto)
          await api.usuarios.editarMultipart(modal.id, fd)
        } else {
          await api.usuarios.editar(modal.id, datos)
        }
        await api.usuarios.asignarRoles(modal.id, rolesIds)
      }
      setModal(null)
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  const desactivar = async (u) => {
    try {
      await api.usuarios.desactivar(u.id)
      setConfirmar(null)
      await cargar()
    } catch (err) {
      setError(err.message)
      setConfirmar(null)
    }
  }

  const activar = async (u) => {
    await api.usuarios.activar(u.id)
    await cargar()
  }

  const campo = (etiqueta, clave, props = {}) => (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">{etiqueta}</label>
      <input
        className="input-esynapse"
        value={form[clave]}
        onChange={(e) => setForm({ ...form, [clave]: e.target.value })}
        {...props}
      />
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <TituloModulo seccion="Administración" titulo="Usuarios" descripcion="Cuentas de acceso al sistema, sus roles y su vínculo con el personal." />
        {tienePermiso('usuarios', 'crear') && (
          <button onClick={abrirCrear} className="btn-primary">
            <Plus className="h-4 w-4" /> Nuevo usuario
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            className="input-esynapse w-64 pl-9"
            placeholder="Buscar por nombre, email, cargo…"
            value={buscar}
            onChange={(e) => setBuscar(e.target.value)}
          />
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input
            type="checkbox"
            checked={verInactivos}
            onChange={(e) => setVerInactivos(e.target.checked)}
            className="h-4 w-4 accent-esynapse-600"
          />
          Incluir inactivos
        </label>
      </div>

      {error && !modal && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}

      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-4 py-3">Usuario</th>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Área / Lab</th>
              <th className="px-4 py-3">Cargo</th>
              <th className="px-4 py-3">Roles</th>
              <th className="px-4 py-3 text-center">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <Avatar src={u.foto_url} nombre={u.nombre_completo || u.username} className="h-8 w-8 text-[11px]" />
                    <span className="font-medium">{u.username}</span>
                  </div>
                </td>
                <td className="px-4 py-3">{u.nombre_completo}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                  {u.area}{u.laboratorio ? ` / ${u.laboratorio}` : ''}
                </td>
                <td className="px-4 py-3">{u.cargo}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {(u.roles || []).map((r) => (
                      <span key={r.id} className="rounded bg-esynapse-600/15 px-1.5 py-0.5 text-[11px] font-medium text-esynapse-600 dark:text-esynapse-300">
                        {r.nombre}
                      </span>
                    ))}
                    {u.is_superuser && (
                      <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[11px] font-medium text-amber-600 dark:text-amber-400">
                        Superusuario
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${
                    u.is_active
                      ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                      : 'bg-red-500/15 text-red-500'
                  }`}>
                    {u.is_active ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-1">
                    {tienePermiso('usuarios', 'editar') && (
                      <button onClick={() => abrirEditar(u)} title="Editar"
                        className="rounded p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">
                        <Pencil className="h-4 w-4" />
                      </button>
                    )}
                    {tienePermiso('usuarios', 'eliminar') && u.is_active && !u.is_superuser && (
                      <button onClick={() => setConfirmar(u)} title="Desactivar"
                        className="rounded p-1.5 text-slate-500 hover:bg-red-500/10 hover:text-red-500">
                        <UserX className="h-4 w-4" />
                      </button>
                    )}
                    {tienePermiso('usuarios', 'editar') && !u.is_active && (
                      <button onClick={() => activar(u)} title="Reactivar"
                        className="rounded p-1.5 text-slate-500 hover:bg-emerald-500/10 hover:text-emerald-500">
                        <RotateCcw className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {usuarios.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-400">Sin resultados</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal crear / editar */}
      <Modal
        abierto={Boolean(modal)}
        titulo={modal === 'crear' ? 'Nuevo usuario' : `Editar: ${modal?.username || ''}`}
        onCerrar={() => setModal(null)}
      >
        <form onSubmit={guardar} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {campo('Usuario', 'username', { required: true, disabled: modal !== 'crear' })}
            {campo('Email', 'email', { type: 'email', required: true })}
            {campo('Nombres', 'first_name')}
            {campo('Apellidos', 'last_name')}
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Trabajador (Organización y personal)</label>
              <select className="input-esynapse" value={String(form.trabajador || '')} onChange={(e) => setForm({ ...form, trabajador: e.target.value ? Number(e.target.value) : '' })}>
                <option value="">— Sin trabajador (cuenta externa o de sistema) —</option>
                {trabDisponibles.map((t) => <option key={t.id} value={t.id}>{t.nombre_completo} · {t.puesto_nombre}</option>)}
              </select>
            </div>
            {trabSel ? (
              <p className="col-span-2 rounded bg-esynapse-600/10 px-3 py-2 text-xs text-slate-600 dark:text-slate-300">
                Cargo y firma: <strong>{trabSel.puesto_nombre}</strong>{trabSel.puesto_sigla ? ` (${trabSel.puesto_sigla})` : ''} · Área: <strong>{trabSel.area_nombre || '—'}</strong>. Se toman del puesto; para cambiarlos, edite el trabajador o el puesto en Organización y personal.
              </p>
            ) : (
              <>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Área</label>
                  <select className="input-esynapse" required value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })}>
                    <option value="">— Selecciona —</option>
                    {form.area && !areasOrg.some((a) => a.nombre === form.area) && <option value={form.area}>{form.area}</option>}
                    {areasOrg.filter((a) => a.tipo !== 'laboratorio').map((a) => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Laboratorio</label>
                  <select className="input-esynapse" value={form.laboratorio} onChange={(e) => setForm({ ...form, laboratorio: e.target.value })}>
                    <option value="">—</option>
                    {form.laboratorio && !areasOrg.some((a) => a.nombre === form.laboratorio) && <option value={form.laboratorio}>{form.laboratorio}</option>}
                    {areasOrg.filter((a) => a.tipo === 'laboratorio').map((a) => <option key={a.id} value={a.nombre}>{a.nombre}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Cargo</label>
                  <CampoSugerencias value={form.cargo} opciones={puestosOrg.map((p) => p.nombre)} onChange={(v) => { const p = puestosOrg.find((x) => x.nombre === v); setForm({ ...form, cargo: v, sigla_cargo: p?.sigla || form.sigla_cargo }) }} />
                </div>
                {campo('Sigla del cargo (firma de formatos, ej. ASIG)', 'sigla_cargo', { maxLength: 12 })}
              </>
            )}
            {campo('Teléfono', 'telefono')}
          </div>
          {modal !== 'crear' && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Foto de perfil</label>
              <div className="flex items-center gap-3">
                <Avatar src={fotoPreview} nombre={form.first_name || form.username} className="h-14 w-14 text-base" />
                <label className="btn-secondary cursor-pointer">
                  <ImagePlus className="h-4 w-4" /> Subir foto
                  <input type="file" accept="image/*" className="hidden"
                    onChange={(e) => {
                      const f = e.target.files[0]
                      if (f) { setForm({ ...form, foto: f }); setFotoPreview(URL.createObjectURL(f)) }
                    }} />
                </label>
              </div>
            </div>
          )}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Roles</label>
            <div className="flex flex-wrap gap-2">
              {roles.map((r) => (
                <label key={r.id} className={`flex cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition ${
                  form.roles.includes(r.id)
                    ? 'border-esynapse-500 bg-esynapse-600/10 text-esynapse-600 dark:text-esynapse-300'
                    : 'border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-300'
                }`}>
                  <input
                    type="checkbox"
                    className="hidden"
                    checked={form.roles.includes(r.id)}
                    onChange={(e) => setForm({
                      ...form,
                      roles: e.target.checked
                        ? [...form.roles, r.id]
                        : form.roles.filter((id) => id !== r.id),
                    })}
                  />
                  {r.nombre}
                </label>
              ))}
              {roles.length === 0 && <p className="text-xs text-slate-400">No hay roles — créalos primero</p>}
            </div>
          </div>
          {modal === 'crear' && (
            <p className="rounded-lg bg-esynapse-600/10 px-3 py-2 text-xs text-esynapse-600 dark:text-esynapse-300">
              El sistema generará una contraseña temporal que se mostrará una sola vez.
            </p>
          )}
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModal(null)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">Guardar</button>
          </div>
        </form>
      </Modal>

      {/* Modal password temporal */}
      <Modal
        abierto={Boolean(passwordTemporal)}
        titulo="Usuario creado"
        onCerrar={() => setPasswordTemporal(null)}
      >
        <div className="space-y-3 text-sm">
          <p>
            Contraseña temporal de <strong>{passwordTemporal?.usuario}</strong> — cópiala ahora,
            no volverá a mostrarse:
          </p>
          <div className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 font-mono text-base dark:bg-slate-800">
            <KeyRound className="h-4 w-4 text-amber-500" />
            {passwordTemporal?.clave}
          </div>
          <div className="flex justify-end">
            <button onClick={() => setPasswordTemporal(null)} className="btn-primary">Entendido</button>
          </div>
        </div>
      </Modal>

      {/* Confirmación de desactivación */}
      <Modal abierto={Boolean(confirmar)} titulo="Desactivar usuario" onCerrar={() => setConfirmar(null)}>
        <div className="space-y-4 text-sm">
          <p>
            ¿Desactivar a <strong>{confirmar?.nombre_completo}</strong>? Sus sesiones se invalidarán
            de inmediato y no podrá iniciar sesión. Sus registros históricos se conservan.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setConfirmar(null)} className="btn-secondary">Cancelar</button>
            <button onClick={() => desactivar(confirmar)} className="btn-danger">Desactivar</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
