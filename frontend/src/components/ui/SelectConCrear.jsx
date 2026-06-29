import { useEffect, useState } from 'react'
import { Check, Plus, X } from 'lucide-react'
import { api } from '../../lib/api.js'

// Desplegable alimentado por un catálogo gestionable (áreas / laboratorios),
// con opción de crear una opción nueva sobre la marcha.
export default function SelectConCrear({ tipo, label, value, onChange, required = false }) {
  const [opciones, setOpciones] = useState([])
  const [creando, setCreando] = useState(false)
  const [nuevo, setNuevo] = useState('')
  const [error, setError] = useState('')

  const cargar = () => api.opcionesCatalogo.listar(tipo).then((d) => setOpciones(d.results ?? d)).catch(() => {})
  useEffect(() => { cargar() }, [tipo])

  const crear = async () => {
    const nombre = nuevo.trim()
    if (!nombre) return
    setError('')
    try {
      const o = await api.opcionesCatalogo.crear(tipo, nombre)
      await cargar()
      onChange(o.nombre)
      setNuevo('')
      setCreando(false)
    } catch (e) {
      setError(e.message || 'No se pudo crear')
    }
  }

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">{label}</label>
      {creando ? (
        <div>
          <div className="flex gap-1">
            <input
              autoFocus
              className="input-esynapse"
              placeholder={`Nueva ${label.toLowerCase()}…`}
              value={nuevo}
              onChange={(e) => setNuevo(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); crear() } }}
            />
            <button type="button" onClick={crear} title="Crear" className="btn-primary !px-2.5"><Check className="h-4 w-4" /></button>
            <button type="button" onClick={() => { setCreando(false); setNuevo(''); setError('') }} title="Cancelar" className="btn-secondary !px-2.5"><X className="h-4 w-4" /></button>
          </div>
          {error && <p className="mt-1 text-[11px] text-red-500">{error}</p>}
        </div>
      ) : (
        <div className="flex gap-1">
          <select
            className="input-esynapse"
            value={value || ''}
            required={required}
            onChange={(e) => onChange(e.target.value)}
          >
            <option value="">— Selecciona —</option>
            {value && !opciones.some((o) => o.nombre === value) && <option value={value}>{value}</option>}
            {opciones.map((o) => <option key={o.id} value={o.nombre}>{o.nombre}</option>)}
          </select>
          <button type="button" onClick={() => setCreando(true)} title={`Crear ${label.toLowerCase()}`} className="btn-secondary !px-2.5">
            <Plus className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}
