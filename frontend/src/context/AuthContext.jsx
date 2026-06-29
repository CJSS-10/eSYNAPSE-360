import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../lib/api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(true)

  const cargarUsuario = useCallback(async () => {
    if (!api.haySesion()) { setUsuario(null); setCargando(false); return }
    try {
      const me = await api.me()
      setUsuario(me)
    } catch {
      api.logout()
      setUsuario(null)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { cargarUsuario() }, [cargarUsuario])

  useEffect(() => {
    const fn = () => { api.logout(); setUsuario(null) }
    window.addEventListener('esynapse:sesion-expirada', fn)
    return () => window.removeEventListener('esynapse:sesion-expirada', fn)
  }, [])

  const login = async (username, password) => {
    await api.login(username, password)
    await cargarUsuario()
  }

  const logout = () => {
    api.logout()
    setUsuario(null)
  }

  /** Permiso granular: tienePermiso('usuarios', 'crear') */
  const tienePermiso = (modulo, operacion) => {
    if (!usuario) return false
    if (usuario.is_superuser) return true
    return (usuario.permisos?.[modulo] || []).includes(operacion)
  }

  return (
    <AuthContext.Provider value={{ usuario, cargando, login, logout, tienePermiso, recargar: cargarUsuario }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
