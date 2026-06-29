/**
 * eSYNAPSE 360 — Catálogo de módulos para el sidebar (arquitectura del CLAUDE.md).
 * fase: número de fase del roadmap en la que se habilita. Fase 0 = disponible hoy.
 */
import {
  Bell, CalendarDays, LayoutDashboard, Users, ShieldCheck, ScrollText, Target, Scale, AlertTriangle,
  BarChart3, ClipboardCheck, FileText, GitBranch, SearchX, Wrench, ClipboardList,
  BookCheck, RefreshCw, MessageSquareWarning, BookOpen, Lightbulb, GraduationCap,
  Gauge, FlaskConical, Crosshair, FileX, Leaf, HardHat, ShoppingCart, Building2,
  Boxes, Hammer, Handshake, Truck, FileBadge, UserCog, Briefcase, Landmark,
  Megaphone, MonitorCog, SlidersHorizontal,
} from 'lucide-react'

export const GRUPOS_MODULOS = [
  {
    titulo: 'General',
    items: [
      { clave: 'dashboard', nombre: 'Dashboard', icono: LayoutDashboard, ruta: '/', fase: 0 },
      { clave: 'mis_tareas', modulo: null, nombre: 'Mis tareas', icono: Bell, ruta: '/mis-tareas', fase: 0, libre: true },
      { clave: 'calendario', modulo: null, nombre: 'Calendario', icono: CalendarDays, ruta: '/calendario', fase: 0, libre: true },
    ],
  },
  {
    titulo: 'Administración',
    items: [
      { clave: 'usuarios', nombre: 'Usuarios', icono: Users, ruta: '/usuarios', fase: 0 },
      { clave: 'usuarios_roles', modulo: 'usuarios', nombre: 'Roles y permisos', icono: ShieldCheck, ruta: '/roles', fase: 0 },
      { clave: 'auditoria', modulo: 'configuracion', nombre: 'Log de auditoría', icono: ScrollText, ruta: '/auditoria', fase: 0, soloAdmin: true },
      { clave: 'configuracion', nombre: 'Configuración', icono: SlidersHorizontal, ruta: '/configuracion', fase: 0, soloAdmin: true },
    ],
  },
  {
    titulo: 'Nivel 1 — Estratégicos',
    items: [
      { clave: 'planeamiento', nombre: 'Planeamiento', icono: Target, fase: 5 },
      { clave: 'legal', nombre: 'Legal', icono: Scale, fase: 5 },
      { clave: 'riesgos', nombre: 'Riesgos', icono: AlertTriangle, fase: 4 },
      { clave: 'indicadores', nombre: 'Indicadores BI', icono: BarChart3, fase: 5 },
      { clave: 'revision_direccion', nombre: 'Revisión Dirección', icono: ClipboardCheck, fase: 5 },
    ],
  },
  {
    titulo: 'Nivel 2 — SIG Core',
    items: [
      { clave: 'documentos', nombre: 'Documentos', icono: FileText, ruta: '/documentos', fase: 0 },
      { clave: 'procesos', nombre: 'Procesos', icono: GitBranch, fase: 4 },
      { clave: 'hallazgos', nombre: 'Hallazgos', icono: SearchX, ruta: '/hallazgos', fase: 0 },
      { clave: 'acciones_correctivas', nombre: 'Acciones Correctivas', icono: Wrench, ruta: '/acciones-correctivas', fase: 0 },
      { clave: 'auditorias', nombre: 'Auditorías', icono: ClipboardList, ruta: '/auditorias', fase: 0 },
      { clave: 'cumplimiento', nombre: 'Cumplimiento', icono: BookCheck, fase: 4 },
      { clave: 'cambios', nombre: 'Cambios', icono: RefreshCw, fase: 4 },
      { clave: 'quejas', nombre: 'Quejas, Reclamos y Satisf.', icono: MessageSquareWarning, fase: 4 },
      { clave: 'conocimiento', nombre: 'Conocimiento', icono: BookOpen, fase: 5 },
      { clave: 'innovacion', nombre: 'Innovación', icono: Lightbulb, fase: 5 },
    ],
  },
  {
    titulo: 'Nivel 2 — Laboratorio 17025',
    items: [
      { clave: 'competencia_tecnica', nombre: 'Competencia Técnica', icono: GraduationCap, fase: 2 },
      { clave: 'equipos', nombre: 'Equipos', icono: Gauge, ruta: '/equipos', fase: 0 },
      { clave: 'metodos', nombre: 'Métodos', icono: FlaskConical, fase: 2 },
      { clave: 'ensayos_aptitud', nombre: 'Ensayos de Aptitud', icono: Crosshair, fase: 2 },
      { clave: 'trabajo_no_conforme', nombre: 'Trabajo No Conforme', icono: FileX, fase: 2 },
    ],
  },
  {
    titulo: 'Nivel 2 — SST y Medio Ambiente',
    items: [
      { clave: 'medio_ambiente', nombre: 'Medio Ambiente', icono: Leaf, fase: 4 },
      { clave: 'sst', nombre: 'SST', icono: HardHat, fase: 4 },
    ],
  },
  {
    titulo: 'Nivel 2 — Operaciones',
    items: [
      { clave: 'compras', nombre: 'Compras', icono: ShoppingCart, fase: 5 },
      { clave: 'proveedores', nombre: 'Proveedores', icono: Building2, fase: 5 },
      { clave: 'inventarios', nombre: 'Inventarios', icono: Boxes, fase: 5 },
      { clave: 'mantenimiento', nombre: 'Mantenimiento', icono: Hammer, fase: 5 },
    ],
  },
  {
    titulo: 'Nivel 2 — Cadena Comercial',
    items: [
      { clave: 'crm', nombre: 'CRM', icono: Handshake, fase: 3 },
      { clave: 'logistica', nombre: 'Logística', icono: Truck, fase: 3 },
      { clave: 'ordenes_trabajo', nombre: 'Órdenes de Trabajo', icono: FileBadge, fase: 3 },
    ],
  },
  {
    titulo: 'Nivel 3 — Soporte',
    items: [
      { clave: 'rrhh', nombre: 'RRHH', icono: UserCog, fase: 5 },
      { clave: 'administracion', nombre: 'Administración', icono: Briefcase, fase: 5 },
      { clave: 'activos', nombre: 'Activos', icono: Landmark, fase: 5 },
      { clave: 'marketing', nombre: 'Marketing', icono: Megaphone, fase: 5 },
      { clave: 'ti', nombre: 'TI', icono: MonitorCog, fase: 5 },
    ],
  },
]
