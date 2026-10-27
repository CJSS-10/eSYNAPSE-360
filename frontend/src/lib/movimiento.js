import { useLayoutEffect, useState } from 'react'

/**
 * Indicador que se desliza hasta el elemento activo (línea de pestaña, fondo del control
 * segmentado, selección del menú). Mide el elemento que cumple `selector` dentro de `ref` y
 * devuelve su posición relativa al contenedor. Se recalcula al cambiar `dep`, al redimensionar
 * el contenedor y cuando terminan de cargar las fuentes.
 */
export function useIndicador(ref, selector, dep) {
  const [caja, setCaja] = useState(null)
  useLayoutEffect(() => {
    const cont = ref.current
    if (!cont) return undefined
    const medir = () => {
      const el = cont.querySelector(selector)
      if (!el) { setCaja(null); return }
      const a = cont.getBoundingClientRect()
      const b = el.getBoundingClientRect()
      setCaja({ left: b.left - a.left + cont.scrollLeft, top: b.top - a.top + cont.scrollTop, width: b.width, height: b.height })
    }
    medir()
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(medir) : null
    ro?.observe(cont)
    document.fonts?.ready?.then(medir)
    return () => ro?.disconnect()
  }, [ref, selector, dep])
  return caja
}
