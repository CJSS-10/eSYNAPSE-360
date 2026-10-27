import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, CornerDownLeft, Loader2, Search } from 'lucide-react'
import { api } from '../lib/api.js'
import { GRUPOS_MODULOS } from '../lib/modulos.js'
import { rutaRegistro } from '../lib/enlaces.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfig } from '../context/ConfigContext.jsx'

/**
 * Búsqueda global (Ctrl + K): por código o texto en los registros que el usuario puede leer
 * (servicio /buscar/) y por nombre de módulo. Elegir un registro abre directamente su ficha.
 * Teclado: ↑ ↓ para moverse, Enter para abrir, Esc para cerrar.
 */
const sinTildes = (s) => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

export default function BuscadorGlobal() {
  const [abierto, setAbierto] = useState(false)
  const [q, setQ] = useState('')
  const [resultados, setResultados] = useState([])
  const [buscando, setBuscando] = useState(false)
  const [activo, setActivo] = useState(0)
  const navigate = useNavigate()
  const { usuario, tienePermiso } = useAuth()
  const { config } = useConfig()
  const inputRef = useRef(null)
  const listaRef = useRef(null)
  const turno = useRef(0)

  // Atajo Ctrl + K (⌘ + K en Mac) desde cualquier pantalla
  useEffect(() => {
    const tecla = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setAbierto((a) => !a) }
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  }, [])

  useEffect(() => {
    if (abierto) { setQ(''); setResultados([]); setActivo(0); setTimeout(() => inputRef.current?.focus(), 0) }
  }, [abierto])

  // Consulta al servidor con una pausa breve; una respuesta vieja no pisa a una nueva
  useEffect(() => {
    const texto = q.trim()
    if (texto.length < 2) { setResultados([]); setBuscando(false); return undefined }
    setBuscando(true)
    const mio = ++turno.current
    const t = setTimeout(() => {
      api.buscar(texto)
        .then((d) => { if (mio === turno.current) { setResultados(d.resultados || []); setActivo(0) } })
        .catch(() => { if (mio === turno.current) setResultados([]) })
        .finally(() => { if (mio === turno.current) setBuscando(false) })
    }, 220)
    return () => clearTimeout(t)
  }, [q])

  // Módulos que coinciden por nombre (con los mismos permisos y licencias del menú)
  const modulos = useMemo(() => {
    const texto = sinTildes(q.trim())
    if (!texto) return []
    const habilitados = new Set(config.modulos_habilitados || [])
    const esAdmin = usuario?.is_superuser || (usuario?.roles || []).includes('Administrador del Sistema')
    return GRUPOS_MODULOS.flatMap((g) => g.items)
      .filter((i) => i.fase === 0 && i.ruta && sinTildes(i.nombre).includes(texto))
      .filter((i) => {
        if (i.libre || i.clave === 'dashboard') return true
        const m = i.modulo || i.clave
        if (habilitados.size > 0 && !habilitados.has(m)) return false
        return i.soloAdmin ? esAdmin : tienePermiso(m, 'leer')
      })
      .slice(0, 4)
  }, [q, config, usuario, tienePermiso])

  const opciones = useMemo(() => [
    ...modulos.map((m) => ({ tipo: 'modulo', clave: `m-${m.clave}`, ruta: m.ruta, nombre: m.nombre, Icono: m.icono })),
    ...resultados.map((r) => ({ ...r, tipo: 'registro', clave: `${r.modulo}-${r.id}`, ruta: rutaRegistro(r.ruta, r.id) })),
  ], [modulos, resultados])

  const grupos = useMemo(() => {
    const g = []
    opciones.forEach((o, i) => {
      const titulo = o.tipo === 'modulo' ? 'Ir a' : o.modulo_nombre
      if (!g.length || g[g.length - 1].titulo !== titulo) g.push({ titulo, items: [] })
      g[g.length - 1].items.push({ ...o, indice: i })
    })
    return g
  }, [opciones])

  const elegir = (o) => { if (!o) return; setAbierto(false); navigate(o.ruta) }

  const teclas = (e) => {
    if (e.key === 'Escape') { e.preventDefault(); setAbierto(false) }
    else if (e.key === 'ArrowDown') { e.preventDefault(); setActivo((a) => Math.min(a + 1, opciones.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActivo((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); elegir(opciones[activo]) }
  }

  useEffect(() => {
    listaRef.current?.querySelector(`[data-indice="${activo}"]`)?.scrollIntoView({ block: 'nearest' })
  }, [activo])

  const texto = q.trim()
  const atajo = typeof navigator !== 'undefined' && /Mac/i.test(navigator.platform) ? '⌘ K' : 'Ctrl K'

  return (
    <>
      <button type="button" onClick={() => setAbierto(true)} aria-label="Buscar en el sistema"
        className="mov-pulsar mr-auto flex h-9 w-full max-w-sm items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-left text-sm text-slate-500 transition-colors hover:border-slate-300 hover:bg-white dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400 dark:hover:bg-slate-800">
        <Search className="h-4 w-4 shrink-0" />
        <span className="flex-1 truncate">Buscar código, equipo, queja…</span>
        <kbd className="hidden rounded border border-slate-200 bg-white px-1.5 font-sans text-[11px] text-slate-500 sm:inline dark:border-slate-600 dark:bg-slate-900 dark:text-slate-400">{atajo}</kbd>
      </button>

      {abierto && createPortal(
        <div className="mov-fondo fixed inset-0 z-[70] flex items-start justify-center bg-slate-950/45 p-4 pt-[12vh] backdrop-blur-[2px]"
          onMouseDown={(e) => { if (e.target === e.currentTarget) setAbierto(false) }}>
          <div role="dialog" aria-modal="true" aria-label="Búsqueda global"
            className="mov-ventana flex max-h-[70vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-pop dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-3 border-b border-slate-200 px-4 dark:border-slate-800">
              {buscando ? <Loader2 className="h-5 w-5 shrink-0 animate-spin text-slate-400" /> : <Search className="h-5 w-5 shrink-0 text-slate-400" />}
              <input ref={inputRef} autoFocus value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={teclas}
                placeholder="Busca por código o texto: SAC-06, FP-02, manómetro, extintores…"
                aria-label="Texto a buscar" role="combobox" aria-expanded={opciones.length > 0} aria-controls="buscador-resultados"
                className="h-14 flex-1 border-0 bg-transparent text-[15px] shadow-none outline-none ring-0 placeholder:text-slate-400 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0" />
              <kbd className="rounded border border-slate-200 px-1.5 text-[11px] text-slate-500 dark:border-slate-700 dark:text-slate-400">Esc</kbd>
            </div>

            <div id="buscador-resultados" ref={listaRef} role="listbox" className="flex-1 overflow-y-auto p-2">
              {texto.length < 2 ? (
                <p className="px-3 py-8 text-center text-sm text-slate-500 dark:text-slate-400">
                  Escribe al menos dos letras. Busca en hallazgos, acciones correctivas, quejas, cambios, auditorías,
                  documentos, equipos, riesgos, trabajo no conforme y revisiones por la dirección.
                </p>
              ) : !buscando && opciones.length === 0 ? (
                <p className="px-3 py-8 text-center text-sm text-slate-500 dark:text-slate-400">Sin resultados para «{texto}».</p>
              ) : grupos.map((g) => (
                <div key={g.titulo} className="mb-1">
                  <p className="px-3 pb-1 pt-2 text-xs font-semibold text-slate-500 dark:text-slate-400">{g.titulo}</p>
                  {g.items.map((o) => {
                    const sel = o.indice === activo
                    return (
                      <button key={o.clave} type="button" role="option" aria-selected={sel} data-indice={o.indice}
                        onMouseMove={() => setActivo(o.indice)} onClick={() => elegir(o)}
                        className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${sel ? 'bg-esynapse-600/10 dark:bg-esynapse-500/15' : ''}`}>
                        {o.tipo === 'modulo' ? (
                          <>
                            {o.Icono && <o.Icono className="h-4 w-4 shrink-0 text-slate-500" />}
                            <span className="flex-1 text-sm font-medium">{o.nombre}</span>
                          </>
                        ) : (
                          <span className="min-w-0 flex-1">
                            <span className="flex flex-wrap items-center gap-2">
                              <span className="font-mono text-[13px] font-semibold">{o.codigo}</span>
                              {o.estado && <span className="text-xs text-slate-500 dark:text-slate-400">{o.estado}</span>}
                            </span>
                            <span className="block truncate text-[13px] text-slate-600 dark:text-slate-300">{o.titulo || '—'}</span>
                          </span>
                        )}
                        {sel ? <CornerDownLeft className="h-4 w-4 shrink-0 text-esynapse-600 dark:text-esynapse-300" /> : <ArrowRight className="h-4 w-4 shrink-0 text-slate-300 dark:text-slate-600" />}
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>

            <div className="flex items-center gap-4 border-t border-slate-200 px-4 py-2 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <span><kbd className="font-sans">↑ ↓</kbd> moverse</span>
              <span><kbd className="font-sans">Enter</kbd> abrir</span>
              <span className="ml-auto">Solo ves lo que tus permisos permiten leer</span>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </>
  )
}
