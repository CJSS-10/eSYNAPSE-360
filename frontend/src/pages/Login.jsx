import { useState } from 'react'
import { Atom, Loader2 } from 'lucide-react'
import { useConfig } from '../context/ConfigContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login() {
  const { config } = useConfig()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const enviar = async (e) => {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await login(username, password)
    } catch (err) {
      setError(err.message || 'No se pudo iniciar sesión')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-100 via-slate-100 to-esynapse-100/40 p-4 dark:from-slate-950 dark:via-slate-950 dark:to-esynapse-950/60">
      <div className="card-esynapse w-full max-w-sm p-8">
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="rounded-2xl bg-esynapse-600/15 p-3">
            {config.logo_url
              ? <img src={config.logo_url} alt="logo" className="h-8 w-8 rounded object-contain" />
              : <Atom className="h-8 w-8 text-esynapse-500" />}
          </div>
          <h1 className="text-xl font-bold tracking-wide">{config.nombre_sistema || 'eSYNAPSE 360'}</h1>
          <p className="text-center text-xs text-slate-500 dark:text-slate-400">
            {config.subtitulo || 'Sistema Integrado de Gestión'}
          </p>
        </div>

        <form onSubmit={enviar} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Usuario</label>
            <input
              className="input-esynapse"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Contraseña</label>
            <input
              type="password"
              className="input-esynapse"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          {error && (
            <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>
          )}
          <button type="submit" disabled={enviando} className="btn-primary w-full">
            {enviando && <Loader2 className="h-4 w-4 animate-spin" />}
            Iniciar sesión
          </button>
        </form>
      </div>
    </div>
  )
}
