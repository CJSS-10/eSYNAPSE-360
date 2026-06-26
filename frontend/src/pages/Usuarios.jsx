import { useCallback, useEffect, useState } from 'react'
import { KeyRound, Pencil, Plus, RotateCcw, Search, UserX } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'

const FORM_VACIO = {
  username: '', first_name: '', last_name: '', email: '',
  area: '', laboratorio: '', cargo: '', telefono: '', roles: [],
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

  const cargar = useCallback(async () => {
    const params = new URLSearchParams()
    if (verInactivos) params.set('incluir_inactivos', '1')
    if (buscar) params.set('buscar', buscar)
    const data = await api.usuarios.listar(`?${params}`)
    setUsuarios(data.results ?? data)
  }, [buscar, verInactivos])

  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
    api.roles.listar().then((d) => setRoles(d.results ?? d)).catch(() => {})
  }, [])

  const abrirCrear = () => { setForm(FORM_VACIO); setError(''); setModal('crear') }
  const abrirEditar = (u) => {
    setForm({
      username: u.username, first_name: u.first_name, last_name: u.last_name,
      email: u.email, area: u.area, laboratorio: u.laboratorio, cargo: u.cargo,
      telefono: u.telefono, roles: (u.roles || []).map((r) => r.id),
    })
    setError('')
    setModal(u)
  }

  const guardar = async (e) => {
    e.preventDefault()
    setError('')
    try {
      if (modal === 'crear') {
        const creado = await api.usuarios.crear(form)
        if (creado.password_temporal) setPasswordTemporal({ usuario: creado.username, clave: creado.password_temporal })
      } else {
        const { roles: rolesIds, username, ...datos } = form
        await api.usuarios.editar(modal.id, datos)
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
        <h1 className="text-2xl font-bold">Usuarios</h1>
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
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-4 py-3">Usuario</th>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Área / Lab</th>
              <th className="px-4 py-3">Cargo</th>
              <th className="px-4 py-3">Roles</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                <td className="px-4 py-3 font-medium">{u.username}</td>
                <td className="px-4 py-3">{u.nombre_completo}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                  {u.area}{u.laboratorio ? ` / ${u.laboratorio}` : ''}
                </td>
                <td className="px-4 py-3">{u.cargo}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {(u.roles || []).map((r) => (
                      <span key={r.id} className="rounded bg-esynapse-600/15 px-1.5 py-0.5 text-[10px] font-medium text-esynapse-600 dark:text-esynapse-300">
                        {r.nombre}
                      </span>
                    ))}
                    {u.is_superuser && (
                      <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                        Superusuario
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                    u.is_active
                      ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                      : 'bg-red-500/15 text-red-500'
                  }`}>
                    {u.is_active ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td className="px-4 py-3">
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
            {campo('Área', 'area', { required: true })}
            {campo('Laboratorio', 'laboratorio')}
            {campo('Cargo', 'cargo', { required: true })}
            {campo('Teléfono', 'telefono')}
          </div>
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
