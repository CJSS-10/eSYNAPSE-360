"""
Incidentes, accidentes de trabajo, emergencias y enfermedades ocupacionales, según el
procedimiento de investigación de accidentes e incidentes, y sus estadísticas mensuales
(índices según la R.M. 050-2013-TR).

Flujo del evento (cada etapa cerrada queda de solo lectura):
    reportado → en investigación → en revisión → en acciones (hallazgo → solicitud de
    acción correctiva) → cerrado.   (anulado: reporte registrado por error)
"""
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

TIPOS_EVENTO = [('accidente', 'Accidente de trabajo'), ('incidente_peligroso', 'Incidente peligroso'),
                ('incidente', 'Incidente'), ('emergencia', 'Emergencia')]
PREFIJO_EVENTO = {'accidente': 'AT', 'incidente_peligroso': 'IP', 'incidente': 'IN', 'emergencia': 'EM'}
GRAVEDADES = [('leve', 'Accidente leve'), ('incapacitante', 'Accidente incapacitante'), ('mortal', 'Mortal')]
GRADOS_INCAPACIDAD = [('total_temporal', 'Total temporal'), ('parcial_temporal', 'Parcial temporal'),
                      ('parcial_permanente', 'Parcial permanente'), ('total_permanente', 'Total permanente')]
ESTADOS_EVENTO = [('reportado', 'Reportado'), ('en_investigacion', 'En investigación'),
                  ('en_revision', 'En revisión'), ('en_acciones', 'En acciones correctivas'),
                  ('cerrado', 'Cerrado'), ('anulado', 'Anulado')]

# Listas del informe de investigación.
PARTES_CUERPO = ['Cráneo', 'Frente', 'Rostro', 'Ojo', 'Nariz', 'Boca', 'Dientes', 'Barbilla / Mentón', 'Cuello',
                 'Clavícula', 'Hombro', 'Brazo', 'Codo', 'Antebrazo', 'Muñeca', 'Mano', 'Dedos de la mano', 'Abdomen',
                 'Espalda', 'Pecho', 'Pulmón', 'Costillas', 'Cadera', 'Pelvis', 'Ingle', 'Nalga', 'Muslo', 'Rodilla',
                 'Pierna', 'Pantorrilla', 'Tobillo', 'Pie', 'Dedos del pie']
TIPOS_LESION = ['Contusión', 'Estiramiento', 'Esguince', 'Abrasión', 'Laceración', 'Perforación', 'Cuerpo extraño',
                'Corte', 'Quemadura térmica', 'Quemadura química', 'Fractura', 'Amputación', 'Enfermedad']
TIPOS_ACCIDENTE = ['Golpeado por', 'Golpeado contra', 'Atrapado dentro', 'Atrapado sobre', 'Atrapado entre',
                   'Resbalón', 'Caída a un mismo nivel', 'Caída a un nivel inferior', 'Sobreesfuerzo',
                   'Contacto con electricidad', 'Temperaturas extremas', 'Contacto con ácidos', 'Ruido',
                   'Sustancias tóxicas', 'Objetos extraños']
TIPOS_EMERGENCIA = ['Sismo', 'Incendio', 'Derrame de fluidos peligrosos', 'Explosión de balón de GLP',
                    'Emergencia médica', 'Inundación de oficinas']
TIPOS_AMBIENTAL = ['Derrame', 'Turbidez del agua / descarga no controlada', 'Muerte animal']
ACTOS_SUBESTANDAR = ['Operar un equipo sin autorización / entrenamiento', 'Falla al advertir', 'Falla al asegurar',
                     'Operar a velocidad inadecuada', 'Hacer inoperables los dispositivos de seguridad',
                     'Remover dispositivos de seguridad', 'Uso de equipo defectuoso', 'Uso de equipo inadecuado',
                     'Falla al usar EPP', 'Carga inadecuada', 'Almacenamiento inadecuado', 'Levantamiento inadecuado',
                     'Posición de tarea inadecuada', 'Bromas', 'No seguir los procedimientos']
CONDICIONES_SUBESTANDAR = ['Protecciones y barreras inadecuadas', 'EPP inadecuado o impropio',
                           'Herramientas / equipos / materiales defectuosos', 'Sistema de advertencia inadecuado',
                           'Área de trabajo congestionada / restringida', 'Peligro de explosión o incendio',
                           'Orden y limpieza deficiente', 'Peligro medioambiental', 'Exposición al ruido',
                           'Exposición a radiación', 'Exposición a temperaturas extremas',
                           'Iluminación inadecuada o excesiva', 'Ventilación inadecuada']
FACTORES_TRABAJO = ['Liderazgo / supervisión inadecuada', 'Ingeniería inadecuada', 'Adquisiciones inadecuadas',
                    'Mantenimiento inadecuado', 'Herramientas / equipos inadecuados', 'Estándares de trabajo inadecuados',
                    'Uso o desgaste excesivo', 'Abuso o maltrato', 'Diseño ergonómico inadecuado']
FACTORES_PERSONALES = ['Capacidad física / fisiológica inadecuada', 'Capacidad mental / psicológica inadecuada',
                       'Tensión física o fisiológica', 'Tensión mental / psicológica', 'Falta de conocimiento',
                       'Falta de habilidad', 'Motivación inadecuada']
METODOS_ANALISIS = [('5_porques', '5 porqués'), ('ishikawa', 'Diagrama de Ishikawa'),
                    ('lluvia_ideas', 'Lluvia de ideas'), ('modelo_causalidad', 'Modelo de causalidad')]
AGENTES = [('fisico', 'Físico'), ('quimico', 'Químico'), ('biologico', 'Biológico'), ('ergonomico', 'Ergonómico'),
           ('psicosocial', 'Psicosocial')]


def _siguiente_codigo(modelo, prefijo, anio):
    nums = [int(c.split('-')[1]) for c in modelo.objects.filter(codigo__startswith=f'{prefijo}-',
                                                                codigo__endswith=f'-{anio}')
            .values_list('codigo', flat=True) if c.split('-')[1].isdigit()]
    return f'{prefijo}-{(max(nums) + 1) if nums else 1:03d}-{anio}'


class Evento(AuditableModel):
    """Accidente de trabajo, incidente peligroso, incidente o emergencia."""
    codigo = models.CharField('Código', max_length=16, unique=True, editable=False)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPOS_EVENTO)
    estado = models.CharField('Estado', max_length=16, choices=ESTADOS_EVENTO, default='reportado')

    # Etapa «reporte» (hasta iniciar la investigación).
    fecha_hora = models.DateTimeField('Fecha y hora de ocurrencia')
    lugar = models.CharField('Lugar exacto', max_length=250)
    unidad = models.ForeignKey('organizacion.Area', verbose_name='Área', on_delete=models.PROTECT, null=True,
                               blank=True, related_name='eventos_sst')
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso', on_delete=models.PROTECT, null=True,
                                blank=True, related_name='eventos_sst')
    en_campo = models.BooleanField('En instalaciones del cliente', default=False)
    cliente = models.CharField('Cliente', max_length=200, blank=True)
    actividad = models.CharField('Actividad que se ejecutaba', max_length=250, blank=True)
    descripcion = models.TextField('Descripción de los hechos')
    acciones_inmediatas = models.TextField('Acciones inmediatas', blank=True)
    primeros_auxilios = models.TextField('Atención de primeros auxilios', blank=True)
    potencialmente_afectados = models.PositiveIntegerField('Trabajadores potencialmente afectados', null=True,
                                                           blank=True)
    pobladores_afectados = models.PositiveIntegerField('Pobladores potencialmente afectados', null=True, blank=True)
    tipos_emergencia = models.JSONField('Tipo de emergencia', default=list, blank=True)
    tipos_ambiental = models.JSONField('Tipo de accidente ambiental', default=list, blank=True)
    testigos = models.JSONField('Testigos', default=list, blank=True, help_text='[{trabajador, nombre, cargo, empresa}]')
    reportado_por = models.ForeignKey('core.Usuario', verbose_name='Reportado por', on_delete=models.PROTECT,
                                      null=True, blank=True, related_name='eventos_sst_reportados')
    fecha_reporte = models.DateTimeField('Fecha del reporte', default=timezone.now)
    notificacion_mtpe = models.DateField('Notificado al Ministerio de Trabajo', null=True, blank=True)
    constancia_mtpe = models.FileField('Constancia de notificación', upload_to='sst/eventos/%Y/', null=True, blank=True)

    # Etapa «investigación».
    gravedad = models.CharField('Gravedad del accidente', max_length=14, choices=GRAVEDADES, blank=True)
    grado_incapacidad = models.CharField('Grado del accidente incapacitante', max_length=20,
                                         choices=GRADOS_INCAPACIDAD, blank=True)
    tipos_accidente = models.JSONField('Tipo de accidente', default=list, blank=True)
    fecha_inicio_investigacion = models.DateField('Inicio de la investigación', null=True, blank=True)
    equipo_investigador = models.JSONField('Equipo investigador', default=list, blank=True,
                                           help_text='[{trabajador, nombre, puesto, rol}]')
    metodo_analisis = models.CharField('Metodología de análisis', max_length=20, choices=METODOS_ANALISIS,
                                       default='5_porques')
    actos_subestandar = models.JSONField('Actos subestándar', default=list, blank=True)
    condiciones_subestandar = models.JSONField('Condiciones subestándar', default=list, blank=True)
    detalle_actos_condiciones = models.TextField('Actos o condiciones subestándar existentes', blank=True)
    factores_trabajo = models.JSONField('Factores de trabajo', default=list, blank=True)
    detalle_factores_trabajo = models.TextField('Explicación de los factores de trabajo', blank=True)
    factores_personales = models.JSONField('Factores personales', default=list, blank=True)
    detalle_factores_personales = models.TextField('Explicación de los factores personales', blank=True)
    que_sucedio = models.TextField('¿Qué sucedió?', blank=True)
    porques = models.JSONField('¿Por qué?', default=list, blank=True)
    causas_inmediatas = models.TextField('Causas inmediatas', blank=True)
    causas_basicas = models.TextField('Causas básicas (raíz)', blank=True)
    conclusiones = models.TextField('Conclusiones', blank=True)
    filas_iperc = models.ManyToManyField('sst.FilaIPERC', verbose_name='Filas IPERC relacionadas', blank=True,
                                         related_name='eventos')
    requiere_actualizar_iperc = models.BooleanField('Requiere actualizar la matriz IPERC', default=False)
    firma_elaborado = models.JSONField('Firma de quien elabora el informe', default=dict, blank=True)

    # Revisión y acciones.
    firma_revisado = models.JSONField('Firma de quien revisa el informe', default=dict, blank=True)
    hallazgo = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='Hallazgo (acciones correctivas)',
                                 on_delete=models.PROTECT, null=True, blank=True, related_name='eventos_sst')
    firma_cierre = models.JSONField('Firma del cierre', default=dict, blank=True)
    fecha_cierre = models.DateTimeField('Fecha de cierre', null=True, blank=True)
    motivo_anulacion = models.TextField('Motivo de anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    CAMPOS_REPORTE = ('tipo', 'fecha_hora', 'lugar', 'unidad', 'proceso', 'en_campo', 'cliente', 'actividad',
                      'descripcion', 'acciones_inmediatas', 'primeros_auxilios', 'potencialmente_afectados',
                      'pobladores_afectados', 'tipos_emergencia', 'tipos_ambiental', 'testigos')
    CAMPOS_INVESTIGACION = ('gravedad', 'grado_incapacidad', 'tipos_accidente', 'fecha_inicio_investigacion',
                            'equipo_investigador', 'metodo_analisis', 'actos_subestandar', 'condiciones_subestandar',
                            'detalle_actos_condiciones', 'factores_trabajo', 'detalle_factores_trabajo',
                            'factores_personales', 'detalle_factores_personales', 'que_sucedio', 'porques',
                            'causas_inmediatas', 'causas_basicas', 'conclusiones', 'filas_iperc',
                            'requiere_actualizar_iperc')
    ETAPAS = [('reporte', ('reportado',), CAMPOS_REPORTE),
              ('investigacion', ('en_investigacion',), CAMPOS_INVESTIGACION)]

    class Meta:
        verbose_name = 'Incidente / accidente'
        verbose_name_plural = 'Incidentes y accidentes'
        ordering = ['-fecha_hora', '-id']

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _siguiente_codigo(Evento, PREFIJO_EVENTO[self.tipo], timezone.localtime(self.fecha_hora).year)
        super().save(*args, **kwargs)

    def etapas_abiertas(self):
        return [n for n, estados, _ in self.ETAPAS if self.estado in estados]

    def etapa_de_campo(self, campo):
        for n, _, campos in self.ETAPAS:
            if campo in campos:
                return n
        return None

    @property
    def reporte_tardio(self):
        """El reporte debe hacerse dentro de las 24 horas de ocurrido el evento."""
        return bool(self.fecha_reporte and self.fecha_hora
                    and (self.fecha_reporte - self.fecha_hora).total_seconds() > 24 * 3600)

    @property
    def requiere_notificacion_mtpe(self):
        """Accidente mortal o incidente peligroso: notificación al Ministerio de Trabajo."""
        return self.tipo == 'incidente_peligroso' or (self.tipo == 'accidente' and self.gravedad == 'mortal')

    @property
    def dias_perdidos(self):
        return sum(a.dias_descanso or 0 for a in self.afectados.filter(is_active=True))


class AfectadoEvento(AuditableModel):
    """Trabajador (o persona externa) afectado por el evento, con los datos del registro oficial."""
    evento = models.ForeignKey(Evento, on_delete=models.PROTECT, related_name='afectados')
    trabajador = models.ForeignKey('organizacion.Trabajador', verbose_name='Trabajador', on_delete=models.PROTECT,
                                   null=True, blank=True, related_name='eventos_sst')
    nombre = models.CharField('Apellidos y nombres', max_length=200)
    documento = models.CharField('DNI / CE', max_length=20, blank=True)
    edad = models.PositiveSmallIntegerField('Edad', null=True, blank=True)
    sexo = models.CharField('Sexo', max_length=1, choices=[('F', 'F'), ('M', 'M')], blank=True)
    area = models.CharField('Área', max_length=120, blank=True)
    puesto = models.CharField('Puesto de trabajo', max_length=150, blank=True)
    empresa = models.CharField('Empresa (si es externo)', max_length=150, blank=True)
    antiguedad = models.CharField('Antigüedad en el empleo', max_length=60, blank=True)
    turno = models.CharField('Turno', max_length=1, choices=[('D', 'Día'), ('T', 'Tarde'), ('N', 'Noche')],
                             blank=True)
    tipo_contrato = models.CharField('Tipo de contrato', max_length=60, blank=True)
    experiencia_puesto = models.CharField('Experiencia en el puesto', max_length=60, blank=True)
    horas_trabajadas = models.DecimalField('Horas trabajadas en la jornada (antes del evento)', max_digits=4,
                                           decimal_places=1, null=True, blank=True)
    sctr = models.BooleanField('Con SCTR', null=True, blank=True)
    partes_cuerpo = models.JSONField('Parte del cuerpo lesionada', default=list, blank=True)
    tipos_lesion = models.JSONField('Tipo de lesión', default=list, blank=True)
    dias_descanso = models.PositiveIntegerField('Días de descanso médico', null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        ordering = ['id']


class ArchivoEvento(AuditableModel):
    """Evidencia del evento: fotografías, croquis, declaraciones firmadas, descanso médico…"""
    evento = models.ForeignKey(Evento, on_delete=models.PROTECT, related_name='archivos')
    archivo = models.FileField('Archivo', upload_to='sst/eventos/%Y/')
    descripcion = models.CharField('Descripción', max_length=200)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        ordering = ['id']


class EnfermedadOcupacional(AuditableModel):
    """Registro de enfermedad ocupacional (sin datos personales de salud: agregado por área)."""
    codigo = models.CharField('Código', max_length=16, unique=True, editable=False)
    estado = models.CharField('Estado', max_length=12, choices=[('registrada', 'Registrada'),
                                                                ('en_acciones', 'En acciones correctivas'),
                                                                ('cerrada', 'Cerrada'), ('anulada', 'Anulada')],
                              default='registrada')
    fecha = models.DateField('Fecha del diagnóstico / registro', default=timezone.localdate)
    nombre = models.CharField('Nombre de la enfermedad ocupacional', max_length=200)
    trabajadores_afectados = models.PositiveIntegerField('N° de trabajadores afectados', default=1)
    unidad = models.ForeignKey('organizacion.Area', verbose_name='Área', on_delete=models.PROTECT, null=True,
                               blank=True, related_name='enfermedades_ocupacionales')
    agente = models.CharField('Agente / factor de riesgo', max_length=12, choices=AGENTES)
    agente_detalle = models.CharField('Detalle del agente', max_length=200, blank=True)
    causas = models.TextField('Causas que generan la enfermedad')
    trabajadores_expuestos = models.PositiveIntegerField('N° de trabajadores expuestos al agente', null=True,
                                                         blank=True)
    cancer_profesional = models.BooleanField('Cáncer profesional', default=False)
    filas_iperc = models.ManyToManyField('sst.FilaIPERC', verbose_name='Filas IPERC relacionadas', blank=True,
                                         related_name='enfermedades')
    hallazgo = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='Hallazgo (acciones correctivas)',
                                 on_delete=models.PROTECT, null=True, blank=True, related_name='enfermedades_sst')
    firma_registro = models.JSONField('Firma del responsable del registro', default=dict, blank=True)
    motivo_anulacion = models.TextField('Motivo de anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Enfermedad ocupacional'
        verbose_name_plural = 'Enfermedades ocupacionales'
        ordering = ['-fecha', '-id']

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _siguiente_codigo(EnfermedadOcupacional, 'EO', self.fecha.year)
        super().save(*args, **kwargs)

    @property
    def veces_en_area(self):
        """N° de veces que se presentó la enfermedad en el área (registros vigentes)."""
        return EnfermedadOcupacional.objects.filter(nombre__iexact=self.nombre, unidad=self.unidad,
                                                    is_active=True).exclude(estado='anulada').count()


class DatosMesSST(AuditableModel):
    """Datos del mes para las estadísticas: trabajadores, horas-hombre y descansos médicos."""
    anio = models.PositiveIntegerField('Año')
    mes = models.PositiveSmallIntegerField('Mes')
    trabajadores = models.PositiveIntegerField('N° total de trabajadores')
    dias_laborables = models.PositiveSmallIntegerField('Días laborables', default=22)
    horas_hombre = models.PositiveIntegerField('Horas-hombre trabajadas')
    propuesto = models.BooleanField('Valor propuesto por el sistema', default=True)
    trabajadores_dm = models.PositiveIntegerField('N° de trabajadores con descanso médico', default=0)
    dias_dm_calendario = models.PositiveIntegerField('Días de descanso médico (calendario)', default=0)
    dias_dm_laborales = models.PositiveIntegerField('Días de descanso médico (laborables)', default=0)
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        unique_together = [('anio', 'mes')]
        ordering = ['anio', 'mes']


class InformeEstadisticasSST(AuditableModel):
    """Análisis del registro de estadísticas: resultados frente a objetivos, causas y conclusiones."""
    anio = models.PositiveIntegerField('Año')
    periodo = models.CharField('Periodo analizado', max_length=60)
    resultados = models.TextField('Resultados estadísticos (comparados con los objetivos)')
    causas_desviaciones = models.TextField('Análisis de las causas de las desviaciones', blank=True)
    conclusiones = models.TextField('Conclusiones y recomendaciones', blank=True)
    firma = models.JSONField('Firma del responsable del registro', default=dict, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        ordering = ['-anio', '-id']
