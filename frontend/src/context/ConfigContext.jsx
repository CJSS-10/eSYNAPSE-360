import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../lib/api.js'

const DEFAULTS = {
  nombre_sistema: 'eSYNAPSE 360°',
  nombre_corto: 'eSYNAPSE 360°',
  subtitulo: '',
  logo_url: null,
  color_primario: '',
  modulos_habilitados: [],
}

const ConfigContext = createContext({ config: DEFAULTS, recargarConfig: () => {} })

export function ConfigProvider({ children }) {
  const [config, setConfig] = useState(DEFAULTS)

  const cargar = () =>
    api.configPublica().then((d) => setConfig({ ...DEFAULTS, ...d })).catch(() => {})

  useEffect(() => { cargar() }, [])
  useEffect(() => { document.title = config.nombre_sistema || 'eSYNAPSE 360°' }, [config.nombre_sistema])

  return (
    <ConfigContext.Provider value={{ config, recargarConfig: cargar }}>
      {children}
    </ConfigContext.Provider>
  )
}

export const useConfig = () => useContext(ConfigContext)
