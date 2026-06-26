import { useEffect, useState } from 'react'
import { LayoutGrid, List, Pencil, Plus, ShieldCheck, Trash2 } from 'lucide-react'
import Modal from '../components/Modal.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function Roles() {
  const { tienePermiso, usuario } = useAuth()
  const [vista, setVista] = useState(localStorage.getItem('esynapse_vista_roles') || 'tarjetas')
  const cambiarVista = (v) => { setVista(v); localStorage.setItem('esynapse_vista_roles', v) }
  const [roles, setRoles] = useState([])
  const [catalogo, setCatalogo] = useState({ modulos: [], operaciones: [] })
  const [modal, setModal] = useState(null) // null | 'crear' | rol a editar
  const [nombre, setNombre] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [matriz, setMatriz] = useState({}) // {modulo: Set(operaciones)}
  const [error, setError] = useState('')
  const [confirmar, setConfirmar] = useState(null)
  const [esAdminRol, setEsAdminRol] = useState(false)

  const cargar = () => api.roles.listar().then((d) => setRoles(d.results ?? d)).catch(() => {})

  useEffect(() => {
    cargar()
    api.catalogo().then(setCatalogo).catch(() => {})
  }, [])

  const abrirCrear = () => {
    setNombre(''); setDescripcion(''); setMatriz({}); setEsAdminRol(false); setError(''); setModal('crear')
  }

  const abrirEditar = (rol) => {
    setNombre(rol.nombre)
    setDescripcion(rol.descripcion || '')
    const m = {}
    for (const p of rol.permisos || []) {
      if (!p.permitido) continue
      m[p.modulo] = m[p.modulo] || new Set()
      m[p.modulo].add(p.operacion)
    }
    setMatriz(m)
    setEsAdminRol(Boolean(rol.es_admin_sistema))
    setError('')
    setModal(rol)
  }

  const alternar = (modulo, operacion) => {
    setMatriz((prev) => {
      const m = { ...prev }
      const ops = new Set(m[modulo] || [])
      if (ops.has(operacion)) ops.delete(operacion)
      else ops.add(operacion)
      if (ops.size === 0) delete m[modulo]
      else m[modulo] = ops
      return m
    })
  }

  const alternarFila = (modulo) => {
    setMatriz((prev) => {
      const m = { ...prev }
      const todas = catalogo.operaciones.map((o) => o.clave)
      const ops = new Set(m[modulo] || [])
      if (ops.size === todas.length) delete m[modulo]
      else m[modulo] = new Set(todas)
      return m
    })
  }

  const guardar = async (e) => {
    e.preventDefault()
    setError('')
    const permisos = Object.entries(matriz).flatMap(([modulo, ops]) =>
      [...ops].map((operacion) => ({ modulo, operacion, permitido: true })),
    )
    try {
      if (modal === 'crear') {
        await api.roles.crear({ nombre, descripcion, es_admin_sistema: esAdminRol, permisos })
      } else {
        await api.roles.editar(modal.id, { nombre, descripcion, es_admin_sistema: esAdminRol, permisos })
      }
      setModal(null)
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  const desactivar = async (rol) => {
    try {
      await api.roles.desactivar(rol.id)
      setConfirmar(null)
      await cargar()
    } catch (err) {
      setError(err.message)
      setConfirmar(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Roles y permisos</h1>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-slate-300 p-0.5 dark:border-slate-700">
            <button onClick={() => cambiarVista('tarjetas')} title="Vista de tarjetas"
              className={`rounded p-1.5 ${vista === 'tarjetas' ? 'bg-esynapse-600 text-white' : 'text-slate-500'}`}>
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button onClick={() => cambiarVista('lista')} title="Vista de lista"
              className={`rounded p-1.5 ${vista === 'lista' ? 'bg-esynapse-600 text-white' : 'text-slate-500'}`}>
              <List className="h-4 w-4" />
            </button>
          </div>
          {tienePermiso('usuarios', 'crear') && (
            <button onClick={abrirCrear} className="btn-primary">
              <Plus className="h-4 w-4" /> Nuevo rol
            </button>
          )}
        </div>
      </div>

      {error && !modal && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}

      {vista === 'tarjetas' && (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {roles.map((rol) => (
          <div key={rol.id} className="card-esynapse flex flex-col p-5">
            <div className="mb-2 flex items-start justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-esynapse-500" />
                <h2 className="font-semibold">{rol.nombre}</h2>
              </div>
              {rol.es_admin_sistema && (
                <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                  Sistema
                </span>
              )}
            </div>
            <p className="mb-3 flex-1 text-xs text-slate-500 dark:text-slate-400">
              {rol.descripcion || 'Sin descripción'}
            </p>
            <div className="mb-3 flex gap-4 text-xs text-slate-500 dark:text-slate-400">
              <span><strong className="text-slate-700 dark:text-slate-200">{(rol.permisos || []).length}</strong> permisos</span>
              <span><strong className="text-slate-700 dark:text-slate-200">{rol.total_usuarios}</strong> usuarios</span>
            </div>
            {(!rol.es_admin_sistema || usuario?.is_superuser) && (
              <div className="flex gap-2">
                {tienePermiso('usuarios', 'editar') && (
                  <button onClick={() => abrirEditar(rol)} className="btn-secondary flex-1 !py-1.5 text-xs">
                    <Pencil className="h-3.5 w-3.5" /> Editar
                  </button>
                )}
                {tienePermiso('usuarios', 'eliminar') && (
                  <button onClick={() => setConfirmar(rol)}
                    className="rounded-lg border border-slate-300 p-1.5 text-slate-500 transition hover:border-red-400 hover:text-red-500 dark:border-slate-700">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
        {roles.length === 0 && (
          <p className="col-span-full py-8 text-center text-sm text-slate-400">
            No hay roles definidos todavía
          </p>
        )}
      </div>
      )}

      {vista === 'lista' && (
        <div className="card-esynapse overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <th className="px-4 py-3">Rol</th>
                <th className="px-4 py-3">Descripción</th>
                <th className="px-4 py-3 text-center">Permisos</th>
                <th className="px-4 py-3 text-center">Usuarios</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((rol) => (
                <tr key={rol.id} className="border-b border-slate-100 transition last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 shrink-0 text-esynapse-500" />
                      <span className="font-medium">{rol.nombre}</span>
                      {rol.es_admin_sistema && (
                        <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">Sistema</span>
                      )}
                    </div>
                  </td>
                  <td className="max-w-md truncate px-4 py-3 text-slate-500 dark:text-slate-400">{rol.descripcion || 'Sin descripción'}</td>
                  <td className="px-4 py-3 text-center">{(rol.permisos || []).length}</td>
                  <td className="px-4 py-3 text-center">{rol.total_usuarios}</td>
                  <td className="px-4 py-3">
                    {(!rol.es_admin_sistema || usuario?.is_superuser) && (
                      <div className="flex justify-end gap-1">
                        {tienePermiso('usuarios', 'editar') && (
                          <button onClick={() => abrirEditar(rol)} title="Editar"
                            className="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-100 hover:text-esynapse-500 dark:hover:bg-slate-800">
                            <Pencil className="h-4 w-4" />
                          </button>
                        )}
                        {tienePermiso('usuarios', 'eliminar') && (
                          <button onClick={() => setConfirmar(rol)} title="Eliminar"
                            className="rounded-lg p-1.5 text-slate-500 transition hover:bg-red-500/10 hover:text-red-500">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {roles.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-400">No hay roles definidos todavía</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal crear/editar con matriz de permisos */}
      <Modal
        abierto={Boolean(modal)}
        titulo={modal === 'crear' ? 'Nuevo rol' : `Editar rol: ${modal?.nombre || ''}`}
        onCerrar={() => setModal(null)}
        ancho="max-w-3xl"
      >
        <form onSubmit={guardar} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Nombre del rol</label>
              <input className="input-esynapse" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Descripción</label>
              <input className="input-esynapse" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
            </div>
          </div>

          {usuario?.is_superuser && (
            <label className="flex items-start gap-2 rounded-lg border border-amber-400/40 bg-amber-500/5 p-3 text-xs">
              <input type="checkbox" className="mt-0.5 h-4 w-4 accent-esynapse-600" checked={esAdminRol} onChange={(e) => setEsAdminRol(e.target.checked)} />
              <span className="text-slate-600 dark:text-slate-300">
                <strong>Administrador de Sistema</strong> — acceso a gestión de usuarios, roles y configuración de marca.
                <span className="block text-[11px] text-slate-400">Solo el propietario puede otorgar este nivel. No incluye el licenciamiento de módulos.</span>
              </span>
            </label>
          )}

          <div>
            <p className="mb-2 text-xs font-medium text-slate-600 dark:text-slate-300">
              Matriz de permisos — clic en el módulo selecciona/deselecciona toda la fila
            </p>
            <div className="max-h-80 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-800">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-100 dark:bg-slate-800">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Módulo</th>
                    {catalogo.operaciones.map((op) => (
                      <th key={op.clave} className="px-2 py-2 text-center font-medium">{op.nombre}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {catalogo.modulos.map((mod) => (
                    <tr key={mod.clave} className="border-t border-slate-100 dark:border-slate-800/60">
                      <td
                        className="cursor-pointer px-3 py-1.5 hover:text-esynapse-500"
                        onClick={() => alternarFila(mod.clave)}
                        title="Seleccionar/deseleccionar fila"
                      >
                        {mod.nombre}
                      </td>
                      {catalogo.operaciones.map((op) => (
                        <td key={op.clave} className="px-2 py-1.5 text-center">
                          <input
                            type="checkbox"
                            className="h-3.5 w-3.5 accent-esynapse-600"
                            checked={matriz[mod.clave]?.has(op.clave) || false}
                            onChange={() => alternar(mod.clave, op.clave)}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModal(null)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary">Guardar rol</button>
          </div>
        </form>
      </Modal>

      {/* Confirmación */}
      <Modal abierto={Boolean(confirmar)} titulo="Desactivar rol" onCerrar={() => setConfirmar(null)}>
        <div className="space-y-4 text-sm">
          <p>
            ¿Desactivar el rol <strong>{confirmar?.nombre}</strong>? Los usuarios que lo tienen
            perderán esos permisos de inmediato.
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
