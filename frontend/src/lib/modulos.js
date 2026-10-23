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
  Megaphone, MonitorCog, SlidersHorizontal, Network,
} from 'lucide-react'

// Grupos del menú lateral por área de trabajo (ADR-0007). Los módulos aún no construidos
// (fase > 0) no ocupan lugar en su grupo: el menú los reúne al final en «Por construir».
export const GRUPOS_MODULOS = [
  {
    titulo: 'General',
    items: [
      { clave: 'dashboard', nombre: 'Tablero', icono: LayoutDashboard, ruta: '/', fase: 0 },
      { clave: 'mis_tareas', modulo: null, nombre: 'Mis tareas', icono: Bell, ruta: '/mis-tareas', fase: 0, libre: true },
      { clave: 'calendario', modulo: null, nombre: 'Calendario', icono: CalendarDays, ruta: '/calendario', fase: 0, libre: true },
    ],
  },
  {
    titulo: 'Sistema de gestión',
    items: [
      { clave: 'documentos', nombre: 'Documentos', icono: FileText, ruta: '/documentos', fase: 0 },
      { clave: 'procesos', nombre: 'Procesos', icono: GitBranch, ruta: '/procesos', fase: 0 },
      { clave: 'hallazgos', nombre: 'Hallazgos', icono: SearchX, ruta: '/hallazgos', fase: 0 },
      { clave: 'acciones_correctivas', nombre: 'Acciones correctivas', icono: Wrench, ruta: '/acciones-correctivas', fase: 0 },
      { clave: 'auditorias', nombre: 'Auditorías', icono: ClipboardList, ruta: '/auditorias', fase: 0 },
      { clave: 'cambios', nombre: 'Cambios', icono: RefreshCw, ruta: '/cambios', fase: 0 },
      { clave: 'quejas', nombre: 'Quejas', icono: MessageSquareWarning, ruta: '/quejas', fase: 0 },
      { clave: 'cumplimiento', nombre: 'Cumplimiento', icono: BookCheck, fase: 4 },
      { clave: 'conocimiento', nombre: 'Conocimiento', icono: BookOpen, fase: 5 },
      { clave: 'innovacion', nombre: 'Innovación', icono: Lightbulb, fase: 5 },
    ],
  },
  {
    titulo: 'Estratégico',
    items: [
      { clave: 'legal', nombre: 'Requisitos legales', icono: Scale, ruta: '/legal', fase: 0 },
      { clave: 'riesgos', nombre: 'Riesgos y oportunidades', icono: AlertTriangle, ruta: '/riesgos', fase: 0 },
      { clave: 'planeamiento', nombre: 'Planeamiento', icono: Target, fase: 5 },
      { clave: 'indicadores', nombre: 'Indicadores', icono: BarChart3, fase: 5 },
      { clave: 'revision_direccion', nombre: 'Revisión por la dirección', icono: ClipboardCheck, fase: 5 },
    ],
  },
  {
    titulo: 'Laboratorio',
    items: [
      { clave: 'competencia_tecnica', nombre: 'Competencia técnica', icono: GraduationCap, ruta: '/competencia', fase: 0 },
      { clave: 'equipos', nombre: 'Equipos', icono: Gauge, ruta: '/equipos', fase: 0 },
      { clave: 'metodos', nombre: 'Métodos', icono: FlaskConical, fase: 2 },
      { clave: 'ensayos_aptitud', nombre: 'Ensayos de aptitud', icono: Crosshair, fase: 2 },
      { clave: 'trabajo_no_conforme', nombre: 'Trabajo no conforme', icono: FileX, fase: 2 },
    ],
  },
  {
    titulo: 'Seguridad, salud y ambiente',
    items: [
      { clave: 'sst', nombre: 'Seguridad y salud', icono: HardHat, ruta: '/sst', fase: 0 },
      { clave: 'medio_ambiente', nombre: 'Medio ambiente', icono: Leaf, fase: 4 },
    ],
  },
  {
    titulo: 'Cadena comercial',
    items: [
      { clave: 'crm', nombre: 'Clientes y cotizaciones', icono: Handshake, fase: 3 },
      { clave: 'logistica', nombre: 'Logística', icono: Truck, fase: 3 },
      { clave: 'ordenes_trabajo', nombre: 'Órdenes de trabajo', icono: FileBadge, fase: 3 },
    ],
  },
  {
    titulo: 'Operaciones',
    items: [
      { clave: 'compras', nombre: 'Compras', icono: ShoppingCart, fase: 5 },
      { clave: 'proveedores', nombre: 'Proveedores', icono: Building2, fase: 5 },
      { clave: 'inventarios', nombre: 'Inventarios', icono: Boxes, fase: 5 },
      { clave: 'mantenimiento', nombre: 'Mantenimiento', icono: Hammer, fase: 5 },
    ],
  },
  {
    titulo: 'Soporte',
    items: [
      { clave: 'rrhh', nombre: 'Recursos humanos', icono: UserCog, fase: 5 },
      { clave: 'administracion', nombre: 'Administración', icono: Briefcase, fase: 5 },
      { clave: 'activos', nombre: 'Activos', icono: Landmark, fase: 5 },
      { clave: 'marketing', nombre: 'Marketing', icono: Megaphone, fase: 5 },
      { clave: 'ti', nombre: 'TI', icono: MonitorCog, fase: 5 },
    ],
  },
  {
    titulo: 'Administración',
    items: [
      { clave: 'usuarios', nombre: 'Usuarios', icono: Users, ruta: '/usuarios', fase: 0 },
      { clave: 'usuarios_roles', modulo: 'usuarios', nombre: 'Roles y permisos', icono: ShieldCheck, ruta: '/roles', fase: 0 },
      { clave: 'organizacion', nombre: 'Organización y personal', icono: Network, ruta: '/organizacion', fase: 0 },
      { clave: 'auditoria', modulo: 'configuracion', nombre: 'Log de auditoría', icono: ScrollText, ruta: '/auditoria', fase: 0, soloAdmin: true },
      { clave: 'configuracion', nombre: 'Configuración', icono: SlidersHorizontal, ruta: '/configuracion', fase: 0, soloAdmin: true },
    ],
  },
]
