import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import { useAuth } from './context/AuthContext.jsx'
import Auditoria from './pages/Auditoria.jsx'
import Cumplimiento from './pages/Cumplimiento.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Documentos from './pages/Documentos.jsx'
import Hallazgos from './pages/Hallazgos.jsx'
import AccionesCorrectivas from './pages/AccionesCorrectivas.jsx'
import Quejas from './pages/Quejas.jsx'
import Procesos from './pages/Procesos.jsx'
import Cambios from './pages/Cambios.jsx'
import Riesgos from './pages/Riesgos.jsx'
import Legal from './pages/Legal.jsx'
import Sst from './pages/Sst.jsx'
import Organizacion from './pages/Organizacion.jsx'
import Auditorias from './pages/Auditorias.jsx'
import MisTareas from './pages/MisTareas.jsx'
import Calendario from './pages/Calendario.jsx'
import Configuracion from './pages/Configuracion.jsx'
import Equipos from './pages/Equipos.jsx'
import Competencia from './pages/Competencia.jsx'
import Capacitacion from './pages/Capacitacion.jsx'
import Ambiente from './pages/Ambiente.jsx'
import RevisionDireccion from './pages/RevisionDireccion.jsx'
import TrabajoNoConforme from './pages/TrabajoNoConforme.jsx'
import Login from './pages/Login.jsx'
import Roles from './pages/Roles.jsx'
import Usuarios from './pages/Usuarios.jsx'

export default function App() {
  const { usuario, cargando } = useAuth()

  if (cargando) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="animate-pulse text-sm text-slate-500">Cargando eSYNAPSE 360°…</p>
      </div>
    )
  }

  if (!usuario) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/documentos" element={<Documentos />} />
        <Route path="/hallazgos" element={<Hallazgos />} />
        <Route path="/acciones-correctivas" element={<AccionesCorrectivas />} />
        <Route path="/quejas" element={<Quejas />} />
        <Route path="/procesos" element={<Procesos />} />
        <Route path="/cambios" element={<Cambios />} />
        <Route path="/riesgos" element={<Riesgos />} />
        <Route path="/legal" element={<Legal />} />
        <Route path="/sst" element={<Sst />} />
        <Route path="/organizacion" element={<Organizacion />} />
        <Route path="/auditorias" element={<Auditorias />} />
        <Route path="/mis-tareas" element={<MisTareas />} />
        <Route path="/calendario" element={<Calendario />} />
        <Route path="/configuracion" element={<Configuracion />} />
        <Route path="/equipos" element={<Equipos />} />
        <Route path="/competencia" element={<Competencia />} />
        <Route path="/capacitacion" element={<Capacitacion />} />
        <Route path="/medio-ambiente" element={<Ambiente />} />
        <Route path="/revision-direccion" element={<RevisionDireccion />} />
        <Route path="/trabajo-no-conforme" element={<TrabajoNoConforme />} />
        <Route path="/cumplimiento" element={<Cumplimiento />} />
        <Route path="/usuarios" element={<Usuarios />} />
        <Route path="/roles" element={<Roles />} />
        <Route path="/auditoria" element={<Auditoria />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
