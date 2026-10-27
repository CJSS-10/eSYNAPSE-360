import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api.js'

// Catálogo de ubigeos del Perú: se descarga una sola vez por sesión y se comparte entre pantallas.
let cache = null
function useUbigeos() {
  const [lista, setLista] = useState(cache || [])
  useEffect(() => {
    if (cache) return
    api.ubigeos().then((d) => { cache = d; setLista(d) }).catch(() => {})
  }, [])
  return lista
}

const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'
const orden = (a, b) => a.localeCompare(b, 'es')

/**
 * Departamento → provincia → distrito encadenados (codificación INEI). valor/onChange: código de ubigeo del distrito
 * (6 dígitos) o ''. Al cambiar el departamento se limpian provincia y distrito; al cambiar la provincia, el distrito.
 */
export default function SelectorUbigeo({ valor, onChange, disabled = false }) {
  const lista = useUbigeos()
  const actual = useMemo(() => lista.find((u) => u[0] === valor), [lista, valor])
  const [dep, setDep] = useState('')
  const [prov, setProv] = useState('')
  useEffect(() => { if (actual) { setDep(actual[1]); setProv(actual[2]) } }, [actual])
  const departamentos = useMemo(() => [...new Set(lista.map((u) => u[1]))].sort(orden), [lista])
  const provincias = useMemo(() => [...new Set(lista.filter((u) => u[1] === dep).map((u) => u[2]))].sort(orden), [lista, dep])
  const distritos = useMemo(() => lista.filter((u) => u[1] === dep && u[2] === prov).sort((a, b) => orden(a[3], b[3])), [lista, dep, prov])
  const inp = 'input-esynapse'
  return (
    <>
      <div><label className={lbl}>Departamento</label>
        <select className={inp} disabled={disabled || !lista.length} value={dep} onChange={(e) => { setDep(e.target.value); setProv(''); onChange('') }}>
          <option value="">{lista.length ? '— Elija —' : 'Cargando…'}</option>{departamentos.map((d) => <option key={d} value={d}>{d}</option>)}
        </select></div>
      <div><label className={lbl}>Provincia</label>
        <select className={inp} disabled={disabled || !dep} value={prov} onChange={(e) => { setProv(e.target.value); onChange('') }}>
          <option value="">— Elija —</option>{provincias.map((p) => <option key={p} value={p}>{p}</option>)}
        </select></div>
      <div><label className={lbl}>Distrito</label>
        <select className={inp} disabled={disabled || !prov} value={valor || ''} onChange={(e) => onChange(e.target.value)}>
          <option value="">— Elija —</option>{distritos.map((u) => <option key={u[0]} value={u[0]}>{u[3]}</option>)}
        </select></div>
    </>
  )
}
