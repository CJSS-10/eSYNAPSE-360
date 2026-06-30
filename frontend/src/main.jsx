import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { ConfigProvider } from './context/ConfigContext.jsx'
import { ConfirmProvider } from './context/ConfirmContext.jsx'
import './index.css'

// Tema: oscuro por defecto, respeta la preferencia guardada
const tema = localStorage.getItem('esynapse_tema') || 'dark'
document.documentElement.classList.toggle('dark', tema === 'dark')

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <HashRouter>
      <ConfigProvider>
        <AuthProvider>
          <ConfirmProvider>
            <App />
          </ConfirmProvider>
        </AuthProvider>
      </ConfigProvider>
    </HashRouter>
  </React.StrictMode>,
)
