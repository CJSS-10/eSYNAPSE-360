import { useEffect, useRef, useState } from 'react'

// Cifra que cuenta desde 0 hasta su valor al aparecer (700 ms, desaceleración). Si el valor cambia,
// cuenta desde el anterior. Con «reducir animaciones» del sistema operativo se muestra directo.
const reducir = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export default function Cifra({ valor, duracion = 700, className = '' }) {
  const fin = Number(valor) || 0
  const [mostrado, setMostrado] = useState(reducir() ? fin : 0)
  const desde = useRef(reducir() ? fin : 0)

  useEffect(() => {
    if (reducir()) { setMostrado(fin); desde.current = fin; return undefined }
    const inicio = performance.now()
    const origen = desde.current
    let raf
    const paso = (ahora) => {
      const t = Math.min(1, (ahora - inicio) / duracion)
      const k = 1 - Math.pow(1 - t, 3)
      setMostrado(Math.round(origen + (fin - origen) * k))
      if (t < 1) raf = requestAnimationFrame(paso)
      else desde.current = fin
    }
    raf = requestAnimationFrame(paso)
    return () => cancelAnimationFrame(raf)
  }, [fin, duracion])

  if (valor === null || valor === undefined) return <span className={className}>—</span>
  return <span className={className}>{mostrado}</span>
}
