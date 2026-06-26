import { useEffect, useState } from 'react'
import { ShieldCheck, Users, ScrollText, FlaskConical } from 'lucide-react'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function Dashboard() {
  const { usuario, tienePermiso } = useAuth()
  const [stats, setStats] = useState({ usuarios: null, roles: null, eventos: null })

  useEffect(() => {
    const cargar = async () => {
      const nuevo = {}
      try {
        if (tienePermiso('usuarios', 'leer')) {
          const u = await api.usuarios.listar()
          nuevo.usuarios = u.count ?? u.length
          const r = await api.roles.listar()
          nuevo.roles = r.count ?? r.length
        }
        if (usuario?.is_superuser) {
          const a = await api.auditoria('?accion=LOGIN')
          nuevo.eventos = a.count
        }
      } catch { /* permisos insuficientes: se omite */ }
      setStats((s) => ({ ...s, ...nuevo }))
    }
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const tarjetas = [
    { titulo: 'Usuarios activos', valor: stats.usuarios, icono: Users, color: 'text-esynapse-500' },
    { titulo: 'Roles definidos', valor: stats.roles, icono: ShieldCheck, color: 'text-emerald-500' },
    { titulo: 'Inicios de sesión', valor: stats.eventos, icono: ScrollText, color: 'text-amber-500' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Bienvenido, {usuario?.first_name || usuario?.username}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {usuario?.cargo ? `${usuario.cargo} — ` : ''}{usuario?.area || 'eSYNAPSE 360'}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tarjetas.map(({ titulo, valor, icono: Icono, color }) => (
          <div key={titulo} className="card-esynapse flex items-center gap-4 p-5">
            <div className={`rounded-xl bg-slate-100 p-3 dark:bg-slate-800 ${color}`}>
              <Icono className="h-6 w-6" />
            </div>
            <div>
              <p className="text-2xl font-bold">{valor ?? '—'}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{titulo}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="card-esynapse p-6">
        <div className="mb-2 flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-esynapse-500" />
          <h2 className="font-semibold">Fase 0 — Cimientos del sistema</h2>
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          El núcleo del SIGE está operativo: autenticación JWT, roles con permisos granulares por módulo
          y operación, y log de auditoría inmutable. Los módulos del laboratorio, SGI y cadena comercial
          se habilitarán progresivamente según el roadmap de fases (el sidebar muestra la fase de cada módulo).
        </p>
      </div>
    </div>
  )
}
