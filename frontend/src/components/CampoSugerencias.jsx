import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ChevronDown } from 'lucide-react'

const normal = (t) => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

/**
 * Campo de texto con lista de sugerencias propia (reemplaza a <datalist>, que cada
 * navegador dibuja a su manera y no respeta el tema). Se puede escribir un valor
 * nuevo o elegir uno de la lista; filtra sin distinguir mayúsculas ni tildes.
 *
 * opciones: ['texto', …] o [{ valor, etiqueta?, detalle? }, …]
 */
export default function CampoSugerencias({ value, onChange, opciones = [], placeholder = '', disabled = false, className = '', compacto = false }) {
  const [abierto, setAbierto] = useState(false)
  const [activo, setActivo] = useState(-1)
  const [escrito, setEscrito] = useState(false)
  const caja = useRef(null)
  const lista = useRef(null)
  const items = useMemo(() => opciones.map((o) => (typeof o === 'string' ? { valor: o } : o)), [opciones])
  const visibles = useMemo(() => {
    const q = normal(value)
    if (!escrito || !q) return items
    return items.filter((o) => normal(o.etiqueta || o.valor).includes(q) || normal(o.detalle).includes(q))
  }, [items, value, escrito])

  const [pos, setPos] = useState(null)
  // La lista se dibuja sobre la página (fuera de tablas o ventanas con desplazamiento, que la recortarían).
  useLayoutEffect(() => {
    if (!abierto) return undefined
    const ubicar = () => {
      const r = caja.current?.getBoundingClientRect()
      if (!r) return
      const abajo = window.innerHeight - r.bottom
      const arriba = abajo < 200 && r.top > abajo
      setPos({ left: r.left, width: r.width, ...(arriba ? { bottom: window.innerHeight - r.top + 4 } : { top: r.bottom + 4 }), alto: Math.max(120, Math.min(240, (arriba ? r.top : abajo) - 12)) })
    }
    ubicar()
    window.addEventListener('resize', ubicar)
    window.addEventListener('scroll', ubicar, true)
    return () => { window.removeEventListener('resize', ubicar); window.removeEventListener('scroll', ubicar, true) }
  }, [abierto])
  useEffect(() => {
    if (!abierto) return undefined
    const fuera = (e) => { if (!caja.current?.contains(e.target) && !lista.current?.contains(e.target)) setAbierto(false) }
    document.addEventListener('mousedown', fuera)
    return () => document.removeEventListener('mousedown', fuera)
  }, [abierto])
  useEffect(() => {
    if (activo >= 0 && lista.current) lista.current.children[activo]?.scrollIntoView({ block: 'nearest' })
  }, [activo])

  const elegir = (o) => { onChange(o.valor); setAbierto(false); setEscrito(false); setActivo(-1) }
  const tecla = (e) => {
    if (!abierto && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) { setAbierto(true); return }
    if (e.key === 'ArrowDown') { e.preventDefault(); setActivo((a) => Math.min(a + 1, visibles.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActivo((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter' && abierto && activo >= 0 && visibles[activo]) { e.preventDefault(); elegir(visibles[activo]) }
    else if (e.key === 'Escape' || e.key === 'Tab') setAbierto(false)
  }

  return (
    <div ref={caja} className="relative">
      <input
        className={compacto ? `w-full bg-transparent pr-6 ${className}` : `input-esynapse pr-8 ${className}`}
        value={value || ''}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        onFocus={() => { setAbierto(true); setEscrito(false); setActivo(-1) }}
        onChange={(e) => { onChange(e.target.value); setEscrito(true); setAbierto(true); setActivo(-1) }}
        onKeyDown={tecla}
      />
      {!disabled && items.length > 0 && (
        <button type="button" tabIndex={-1} aria-label="Ver opciones" onMouseDown={(e) => { e.preventDefault(); setAbierto((a) => !a); setEscrito(false) }}
          className={`absolute top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 ${compacto ? 'right-0' : 'right-2'}`}>
          <ChevronDown className="h-4 w-4" />
        </button>
      )}
      {abierto && !disabled && visibles.length > 0 && pos && createPortal(
        <ul ref={lista} role="listbox" style={{ position: 'fixed', left: pos.left, top: pos.top, bottom: pos.bottom, width: Math.max(pos.width, 192), maxHeight: pos.alto }}
          className={`z-[1000] overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 text-sm shadow-lg dark:border-slate-700 dark:bg-slate-900 ${document.documentElement.classList.contains('dark') ? 'dark' : ''}`}>
          {visibles.map((o, i) => (
            <li key={`${o.valor}-${i}`} role="option" aria-selected={o.valor === value}
              onMouseDown={(e) => { e.preventDefault(); elegir(o) }}
              onMouseEnter={() => setActivo(i)}
              className={`cursor-pointer px-3 py-1.5 text-left ${i === activo ? 'bg-esynapse-600/15' : ''} ${o.valor === value ? 'font-semibold text-esynapse-600 dark:text-esynapse-400' : 'text-slate-700 dark:text-slate-200'}`}>
              {o.etiqueta || o.valor}
              {o.detalle && <span className="ml-2 text-[11px] text-slate-400">{o.detalle}</span>}
            </li>
          ))}
        </ul>,
        document.body,
      )}
    </div>
  )
}
