import { useState } from 'react'
import { Atom, Loader2 } from 'lucide-react'
import { useConfig } from '../context/ConfigContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { Dial, Senal } from '../components/ui/Decoracion.jsx'

// Pantalla de ingreso (propuesta de movimiento del 27-10-2026): panel de marca a la izquierda
// (se oculta en pantallas angostas) y formulario a la derecha. Un error sacude el formulario una vez.
const NORMAS = ['ISO 9001', 'NTP ISO/IEC 17025', 'ISO 45001', 'ISO 14001']

export default function Login() {
  const { config } = useConfig()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [intento, setIntento] = useState(0)
  const [enviando, setEnviando] = useState(false)

  const enviar = async (e) => {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await login(username, password)
    } catch (err) {
      setError(err.message || 'No se pudo iniciar sesión')
      setIntento((n) => n + 1)
    } finally {
      setEnviando(false)
    }
  }

  const logo = config.logo_url
    ? <img src={config.logo_url} alt="" className="h-7 w-7 rounded object-contain" />
    : <Atom className="h-6 w-6" />

  return (
    <div className="flex min-h-screen bg-white dark:bg-slate-950">
      {/* Panel de marca */}
      <section className="relative hidden flex-1 flex-col justify-between overflow-hidden bg-[radial-gradient(120%_90%_at_20%_10%,#1f4e9b_0%,#17396f_40%,#0d1e3b_100%)] px-14 py-12 text-white lg:flex">
        <Dial className="absolute -right-32 top-1/2 -translate-y-1/2 opacity-55" />
        <Senal className="absolute bottom-10 left-0 opacity-25" />

        <div className="mov-entra relative flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/25 bg-white/15 text-white">{logo}</div>
          <div className="leading-tight">
            <p className="text-[17px] font-bold">{config.nombre_corto || 'eSYNAPSE 360°'}</p>
            {config.subtitulo && <p className="text-[13px] text-esynapse-200">{config.subtitulo}</p>}
          </div>
        </div>

        <div className="mov-entra relative max-w-md" style={{ animationDelay: '.12s' }}>
          <h1 className="text-[40px] font-semibold leading-[1.12] tracking-tight">Sistema Integrado de Gestión</h1>
          <p className="mt-3.5 text-base leading-relaxed text-esynapse-100">
            Calidad, laboratorio, seguridad y ambiente en un solo lugar, con la trazabilidad que exige cada norma.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {NORMAS.map((n) => (
              <span key={n} className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[13px]">{n}</span>
            ))}
          </div>
        </div>

        <p className="mov-entra relative text-[13px] text-esynapse-300" style={{ animationDelay: '.2s' }}>
          {config.version ? `Versión ${config.version}` : ''}
        </p>
      </section>

      {/* Formulario */}
      <section className="flex flex-1 items-center justify-center px-6 py-12 lg:max-w-[560px]">
        <form onSubmit={enviar} className="mov-entra flex w-full max-w-sm flex-col gap-5" style={{ animationDelay: '.18s' }}>
          <div>
            <div className="mb-6 flex items-center gap-3 lg:hidden">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-esynapse-600 text-white">{logo}</div>
              <p className="font-bold">{config.nombre_corto || 'eSYNAPSE 360°'}</p>
            </div>
            <h2 className="text-[26px] font-semibold tracking-tight">Iniciar sesión</h2>
            <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400">Ingresa con tu usuario del sistema.</p>
            {config.modo_pruebas && (
              <p className="mt-3 inline-block rounded-md border border-amber-500/40 bg-amber-500/15 px-2.5 py-1 text-xs font-bold text-amber-700 dark:text-amber-300">
                Modo pruebas · copia de la base
              </p>
            )}
          </div>

          <div key={intento} className={`flex flex-col gap-4 ${intento > 0 ? 'mov-sacudir' : ''}`}>
            <label className="flex flex-col gap-1.5 text-[13px] font-medium text-slate-600 dark:text-slate-300">
              Usuario
              <input
                className={`input-esynapse h-11 text-[15px] ${error ? 'border-red-400 dark:border-red-500/60' : ''}`}
                value={username}
                onChange={(e) => { setUsername(e.target.value); setError('') }}
                autoFocus
                autoComplete="username"
                required
              />
            </label>
            <label className="flex flex-col gap-1.5 text-[13px] font-medium text-slate-600 dark:text-slate-300">
              Contraseña
              <input
                type="password"
                className={`input-esynapse h-11 text-[15px] ${error ? 'border-red-400 dark:border-red-500/60' : ''}`}
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError('') }}
                autoComplete="current-password"
                required
              />
            </label>
            {error && <p role="alert" className="text-[13px] text-red-600 dark:text-red-400">{error}</p>}
          </div>

          <button type="submit" disabled={enviando} className="btn-primary mov-pulsar h-11 w-full text-[15px]">
            {enviando && <Loader2 className="h-4 w-4 animate-spin" />}
            {enviando ? 'Verificando…' : 'Ingresar'}
          </button>
          <p className="text-center text-[13px] text-slate-500 dark:text-slate-400">¿Olvidaste tu contraseña? Pídela al administrador del sistema.</p>
        </form>
      </section>
    </div>
  )
}
