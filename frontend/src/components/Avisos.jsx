import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Check, X } from 'lucide-react'

// Pila de avisos de confirmación (ver lib/avisos.js). Cada uno dura 3 s; un aviso igual al
// anterior dentro de ese lapso no se repite (p. ej. un formulario que guarda en dos pasos).
export default function Avisos() {
  const [lista, setLista] = useState([])
  const sig = useRef(1)

  useEffect(() => {
    const llegar = (e) => {
      const { texto, tipo } = e.detail || {}
      setLista((l) => {
        if (l.some((a) => a.texto === texto && Date.now() - a.t < 3000)) return l
        const id = sig.current++
        setTimeout(() => setLista((x) => x.filter((a) => a.id !== id)), 3000)
        return [...l.slice(-2), { id, texto, tipo, t: Date.now() }]
      })
    }
    window.addEventListener('esynapse:aviso', llegar)
    return () => window.removeEventListener('esynapse:aviso', llegar)
  }, [])

  return createPortal(
    <div aria-live="polite" className="pointer-events-none fixed bottom-5 right-5 z-[80] flex flex-col items-end gap-2">
      {lista.map((a) => (
        <div key={a.id} role="status"
          className="mov-aviso pointer-events-auto flex items-center gap-3 rounded-xl bg-slate-900 py-2.5 pl-3 pr-2 text-sm text-white shadow-pop dark:bg-slate-700">
          <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${a.tipo === 'error' ? 'bg-red-500' : 'bg-emerald-500'}`}>
            {a.tipo === 'error' ? <X className="h-3.5 w-3.5" /> : <Check className="mov-check h-3.5 w-3.5" strokeWidth={3} />}
          </span>
          <span className="pr-1">{a.texto}</span>
          <button type="button" onClick={() => setLista((x) => x.filter((y) => y.id !== a.id))} aria-label="Cerrar aviso"
            className="rounded-md p-1 text-white/60 hover:bg-white/10 hover:text-white"><X className="h-3.5 w-3.5" /></button>
        </div>
      ))}
    </div>,
    document.body,
  )
}
