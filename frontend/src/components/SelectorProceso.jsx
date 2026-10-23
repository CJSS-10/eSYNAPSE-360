import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'

// Catálogo oficial de procesos (M7), compartido por todas las pantallas.
let cache = null
export function useCatalogoProcesos() {
  const [procesos, setProcesos] = useState(cache || [])
  useEffect(() => {
    if (cache) return
    api.procesos.listar().then((d) => { cache = d.results ?? d; setProcesos(cache) }).catch(() => {})
  }, [])
  return procesos
}
export function refrescarCatalogoProcesos() { cache = null }

const GRUPOS = [['estrategico', 'Estratégicos'], ['operativo', 'Principales'], ['soporte', 'Soporte']]

// Opciones agrupadas por tipo, con los subprocesos debajo de su proceso.
export function OpcionesProcesos({ procesos }) {
  return GRUPOS.map(([tipo, nombre]) => {
    const raiz = procesos.filter((p) => p.tipo === tipo && !p.padre)
    if (!raiz.length) return null
    return (
      <optgroup key={tipo} label={nombre}>
        {raiz.flatMap((p) => [
          <option key={p.id} value={p.nombre}>{p.nombre}</option>,
          ...procesos.filter((s) => s.padre === p.id).map((s) => (
            <option key={s.id} value={s.nombre}>{'   '}{s.nombre}</option>
          )),
        ])}
      </optgroup>
    )
  })
}

/**
 * Lista desplegable del catálogo de procesos. Trabaja con el nombre del proceso
 * (el servidor lo vincula al catálogo). Un texto antiguo que no está en el
 * catálogo se muestra como «sin vincular» para poder corregirlo.
 */
export default function SelectorProceso({ value, onChange, required, className = 'input-esynapse', disabled }) {
  const procesos = useCatalogoProcesos()
  const enCatalogo = !value || procesos.some((p) => p.nombre.toLowerCase() === String(value).toLowerCase())
  return (
    <select className={className} value={value || ''} required={required} disabled={disabled}
      onChange={(e) => onChange(e.target.value)}>
      <option value="">— Elige el proceso —</option>
      {!enCatalogo && procesos.length > 0 && <option value={value}>{value} (sin vincular al catálogo)</option>}
      <OpcionesProcesos procesos={procesos} />
    </select>
  )
}
