"""
Medio ambiente: aspectos e impactos ambientales, consumos de energía y agua, y residuos sólidos.

- Matriz de aspectos e impactos: cada aspecto se evalúa con cinco criterios (cumplimiento legal, severidad, partes
  interesadas, escala y frecuencia; 1 a 3). Es significativo si la suma es 10 o más, o si el cumplimiento legal es 3
  (no cumple). Los aspectos positivos se identifican pero no se evalúan. La matriz la aprueban todos los titulares del
  Comité de SST; un cambio posterior la deja pendiente de nueva aprobación.
- Consumos: un registro por suministro (medidor de una sede o de uno de sus niveles) y mes, por lectura del medidor
  (el consumo es la diferencia con la lectura anterior) o por recibo / dato del arrendador / estimación.
- Residuos: pesajes (ingreso al almacén temporal o salida) con el formato del laboratorio, disposiciones con su
  certificado y resumen anual para la declaración.
"""
from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.models import AuditableModel

UMBRAL_SIGNIFICANCIA = 10

ALCANCES = [('empresa', 'Toda la empresa'), ('laboratorios', 'Todos los laboratorios'),
            ('oficinas', 'Oficinas administrativas'), ('areas', 'Áreas o laboratorios'), ('otro', 'Otro lugar')]
SITUACIONES = [('N', 'Normal (rutinario)'), ('A', 'Anormal (no rutinario)'), ('E', 'Emergencia')]
GENERACION = [('directa', 'Directa'), ('indirecta', 'Indirecta')]
CLASES = [('negativo', 'Negativo'), ('positivo', 'Positivo')]
ETAPAS_CICLO = [('', '—'), ('entrada', 'Entrada (recursos, energía)'), ('proceso', 'Proceso (emisiones, transformación)'),
                ('salida', 'Salida (desechos)')]
CRITERIOS = [('legal', 'Cumplimiento legal (A)'), ('severidad', 'Severidad (B)'),
             ('partes', 'Partes interesadas (C)'), ('escala', 'Escala (D)'), ('frecuencia', 'Frecuencia (E)')]
# Tabla de valoración del procedimiento (Alto 3 · Medio 2 · Bajo 1)
VALORACION = {
    'legal': {3: 'No cumple el requisito legal aplicable', 2: 'Cumplimiento en trámite o en implementación',
              1: 'Cumple, o no existe requisito legal aplicable'},
    'severidad': {3: 'Daños graves o irreversibles, o no existen controles',
                  2: 'Daños reversibles a mediano o largo plazo, o hay controles pero no son efectivos',
                  1: 'Daño reversible de inmediato al suspender la actividad, o hay controles efectivos'},
    'partes': {3: 'Quejas que trascendieron a la prensa nacional o internacional',
               2: 'Quejas individuales sin trascender a la prensa', 1: 'Sin quejas'},
    'escala': {3: 'Global, nacional o provincial (más allá del distrito)', 2: 'Zonal (alrededores inmediatos)',
               1: 'Dentro de las instalaciones'},
    'frecuencia': {3: 'Diaria o continua', 2: 'Semanal o frecuente', 1: 'Mensual o más espaciada, u ocasional'},
}
ESTADOS_ASPECTO = [('vigente', 'Vigente'), ('retirado', 'Retirado')]

TIPOS_CONSUMO = [('energia', 'Energía eléctrica'), ('agua', 'Agua')]
UNIDAD_CONSUMO = {'energia': 'kWh', 'agua': 'm³'}
ORIGENES_CONSUMO = [('lectura', 'Lectura del medidor'), ('recibo', 'Recibo'),
                    ('arrendador', 'Informado por el arrendador'), ('estimado', 'Estimado')]
FACTOR_PICO = Decimal('1.5')  # aviso si el consumo supera en 50 % el promedio de los registros anteriores

TIPOS_PESAJE = [('ingreso', 'Ingreso al almacén temporal'), ('salida', 'Salida del almacén')]
ESTADOS_PESAJE = [('en_registro', 'En registro'), ('cerrado', 'Cerrado'), ('anulado', 'Anulado')]
# Categorías del formato de pesaje: (clave, nombre, tacho, peligroso, unidad)
CATEGORIAS_RESIDUO = [
    ('azul', 'No peligroso — tacho azul (papel, cartón)', 'azul', False, 'kg'),
    ('blanco', 'No peligroso — tacho blanco (plásticos)', 'blanco', False, 'kg'),
    ('rojo_liquido', 'Peligroso — líquido de laboratorio (tipo A)', 'rojo', True, 'L'),
    ('rojo_solido', 'Peligroso — sólido (tipo B)', 'rojo', True, 'kg'),
    ('raee', 'Residuos de aparatos eléctricos y electrónicos (RAEE)', 'raee', True, 'kg'),
]
TIPOS_SUGERIDOS = {'azul': ['Papel', 'Cartón', 'Otros'], 'blanco': ['Botellas', 'Plástico', 'Tuberías PVC', 'Otros'],
                   'rojo_liquido': [], 'rojo_solido': ['Pilas', 'General'], 'raee': []}
DESTINOS = [('municipal', 'Recolección municipal'), ('eors', 'Empresa operadora autorizada (EO-RS)'),
            ('reciclaje', 'Reciclaje'), ('donacion', 'Donación'), ('venta', 'Venta'),
            ('acopio_raee', 'Punto de acopio de RAEE'), ('otro', 'Otro')]
GRUPOS_DISPOSICION = [('no_peligroso', 'No peligroso'), ('peligroso', 'Peligroso'), ('raee', 'RAEE')]


def siguiente_codigo(modelo, prefijo, anio):
    nums = [int(c.split('-')[1]) for c in modelo.objects.filter(codigo__startswith=f'{prefijo}-',
                                                                codigo__endswith=f'-{anio}')
            .values_list('codigo', flat=True) if c.split('-')[1].isdigit()]
    return f'{prefijo}-{(max(nums) + 1) if nums else 1:03d}-{anio}'


class AspectoAmbiental(AuditableModel):
    sede = models.ForeignKey('organizacion.Sede', verbose_name='Sede (vacío: todas)', on_delete=models.PROTECT,
                             null=True, blank=True, related_name='aspectos_ambientales')
    alcance = models.CharField('Lugar', max_length=14, choices=ALCANCES, default='areas')
    areas = models.ManyToManyField('organizacion.Area', verbose_name='Áreas o laboratorios', blank=True,
                                   related_name='aspectos_ambientales')
    lugar = models.CharField('Lugar (descripción)', max_length=120, blank=True)
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso (vacío: todos)', on_delete=models.PROTECT,
                                null=True, blank=True, related_name='aspectos_ambientales')
    actividad = models.CharField('Actividad', max_length=300)
    aspecto = models.CharField('Aspecto ambiental', max_length=300)
    impacto = models.CharField('Impacto ambiental', max_length=300)
    situaciones = models.JSONField('Situación (N/A/E)', default=list, blank=True)
    generacion = models.CharField('Generación', max_length=10, choices=GENERACION, default='directa')
    clase = models.CharField('Clase', max_length=10, choices=CLASES, default='negativo')
    etapa_ciclo = models.CharField('Etapa del ciclo de vida', max_length=10, choices=ETAPAS_CICLO, blank=True)
    controles_existentes = models.TextField('Controles existentes', blank=True)
    legal = models.PositiveSmallIntegerField('Cumplimiento legal (A)', null=True, blank=True)
    severidad = models.PositiveSmallIntegerField('Severidad (B)', null=True, blank=True)
    partes = models.PositiveSmallIntegerField('Partes interesadas (C)', null=True, blank=True)
    escala = models.PositiveSmallIntegerField('Escala (D)', null=True, blank=True)
    frecuencia = models.PositiveSmallIntegerField('Frecuencia (E)', null=True, blank=True)
    obligacion = models.ForeignKey('legal.Obligacion', verbose_name='Requisito legal asociado',
                                   on_delete=models.PROTECT, null=True, blank=True, related_name='aspectos_ambientales')
    control_operacional = models.TextField('Control operacional', blank=True)
    registro_asociado = models.CharField('Registro asociado', max_length=300, blank=True)
    responsable = models.ForeignKey('organizacion.Puesto', verbose_name='Responsable', on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='aspectos_ambientales')
    plazo = models.DateField('Plazo de implementación', null=True, blank=True)
    criterio_seguimiento = models.CharField('Criterio de seguimiento', max_length=300, blank=True)
    orden = models.PositiveIntegerField('Orden', default=0)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS_ASPECTO, default='vigente')
    motivo_retiro = models.TextField('Motivo del retiro', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Aspecto ambiental'
        verbose_name_plural = 'Aspectos ambientales'
        ordering = ['orden', 'id']

    def __str__(self):
        return f'{self.aspecto} ({self.actividad})'

    @property
    def evaluable(self):
        return self.clase == 'negativo'

    @property
    def resultado(self):
        valores = [self.legal, self.severidad, self.partes, self.escala, self.frecuencia]
        if not self.evaluable or any(v is None for v in valores):
            return None
        return sum(valores)

    @property
    def significativo(self):
        """Regla del procedimiento: suma ≥ 10 o incumplimiento legal (A = 3). Un positivo no es significativo."""
        if not self.evaluable:
            return False
        return (self.resultado or 0) >= UMBRAL_SIGNIFICANCIA or self.legal == 3

    @property
    def lugar_texto(self):
        if self.alcance == 'areas':
            return ', '.join(a.nombre for a in self.areas.all()) or '—'
        if self.sede_id and self.alcance == 'empresa':
            return f'{self.sede.nombre} (toda la sede)'
        base = (self.lugar or 'Otro lugar') if self.alcance == 'otro' else self.get_alcance_display()
        return f'{base} · {self.sede.nombre}' if self.sede_id else base


class AprobacionMatrizAmbiental(AuditableModel):
    """Aprobación de la matriz de aspectos por todos los titulares del Comité de SST."""
    fecha = models.DateField('Fecha de aprobación')
    reunion = models.ForeignKey('sst.ReunionComite', on_delete=models.PROTECT, null=True, blank=True,
                                related_name='aprobaciones_ambientales')
    firmas = models.JSONField('Firmas', default=list, blank=True)
    archivo = models.FileField('Acta firmada (papel)', upload_to='ambiente/aprobaciones/%Y/', null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    registro = models.JSONField('Registrado por', default=dict, blank=True)
    aspectos = models.PositiveIntegerField('Aspectos vigentes aprobados', default=0)

    class Meta:
        verbose_name = 'Aprobación de la matriz de aspectos'
        ordering = ['-created_at', '-id']


def estado_aprobacion_matriz():
    """'aprobada' si nada cambió después de la última aprobación; 'pendiente' si hubo cambios; 'sin_aprobar'."""
    ultima = AprobacionMatrizAmbiental.objects.order_by('-created_at', '-id').first()
    if not ultima:
        return 'sin_aprobar', None
    cambio = AspectoAmbiental.objects.filter(updated_at__gt=ultima.created_at).exists()
    return ('pendiente' if cambio else 'aprobada'), ultima


class ConsumoMensual(AuditableModel):
    suministro = models.ForeignKey('organizacion.Suministro', verbose_name='Suministro', on_delete=models.PROTECT,
                                   null=True, blank=True, related_name='consumos')
    tipo = models.CharField('Tipo', max_length=8, choices=TIPOS_CONSUMO)
    anio = models.PositiveIntegerField('Año')
    mes = models.PositiveSmallIntegerField('Mes')
    origen = models.CharField('Origen del dato', max_length=10, choices=ORIGENES_CONSUMO, default='recibo')
    fecha_lectura = models.DateField('Fecha de la lectura', null=True, blank=True)
    lectura_anterior = models.DecimalField('Lectura anterior', max_digits=14, decimal_places=2, null=True, blank=True)
    lectura_actual = models.DecimalField('Lectura actual', max_digits=14, decimal_places=2, null=True, blank=True)
    cambio_medidor = models.BooleanField('Cambio o reinicio del medidor', default=False)
    motivo_cambio = models.CharField('Motivo del cambio de medidor', max_length=200, blank=True)
    consumo = models.DecimalField('Consumo', max_digits=12, decimal_places=2)
    monto = models.DecimalField('Monto (S/)', max_digits=12, decimal_places=2, null=True, blank=True)
    evidencia = models.FileField('Recibo o foto del medidor', upload_to='ambiente/consumos/%Y/', null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Consumo mensual'
        ordering = ['-anio', '-mes', 'tipo']
        constraints = [
            models.UniqueConstraint(fields=['suministro', 'anio', 'mes'],
                                    condition=models.Q(is_active=True, suministro__isnull=False),
                                    name='unico_consumo_activo_por_suministro_mes'),
            models.UniqueConstraint(fields=['tipo', 'anio', 'mes'],
                                    condition=models.Q(is_active=True, suministro__isnull=True),
                                    name='unico_consumo_sin_suministro_por_mes')]

    @property
    def unidad(self):
        return UNIDAD_CONSUMO.get(self.tipo, '')

    def _vecinos(self):
        return ConsumoMensual.objects.filter(is_active=True, suministro_id=self.suministro_id) \
            .exclude(pk=self.pk) if self.suministro_id else ConsumoMensual.objects.none()

    def anterior(self):
        """Registro activo inmediatamente anterior del mismo suministro."""
        return self._vecinos().filter(models.Q(anio__lt=self.anio) | models.Q(anio=self.anio, mes__lt=self.mes)) \
            .order_by('-anio', '-mes').first()

    def siguiente(self):
        return self._vecinos().filter(models.Q(anio__gt=self.anio) | models.Q(anio=self.anio, mes__gt=self.mes)) \
            .order_by('anio', 'mes').first()

    @property
    def consumo_diario(self):
        """Consumo por día entre la lectura anterior y esta (para comparar meses de distinta duración)."""
        ant = self.anterior() if self.origen == 'lectura' and not self.cambio_medidor else None
        if not (ant and ant.fecha_lectura and self.fecha_lectura) or self.fecha_lectura <= ant.fecha_lectura:
            return None
        return round(self.consumo / (self.fecha_lectura - ant.fecha_lectura).days, 2)

    @property
    def aviso(self):
        """Aviso (no bloquea) si el consumo supera en 50 % el promedio de hasta seis registros anteriores, o si cubre
        más de un mes porque faltan registros intermedios."""
        avisos = []
        previos = list(self._vecinos().filter(models.Q(anio__lt=self.anio) | models.Q(anio=self.anio,
                                                                                         mes__lt=self.mes))
                       .order_by('-anio', '-mes').values_list('consumo', 'anio', 'mes')[:6])
        if len(previos) >= 3:
            promedio = sum(p[0] for p in previos) / len(previos)
            if promedio and self.consumo > promedio * FACTOR_PICO:
                avisos.append(f'Consumo {round((self.consumo / promedio - 1) * 100)} % mayor que el promedio de los '
                              f'{len(previos)} meses anteriores: revise la lectura o una posible fuga.')
        if previos and self.origen == 'lectura' and not self.cambio_medidor:
            meses = (self.anio - previos[0][1]) * 12 + self.mes - previos[0][2]
            if meses > 1:
                avisos.append(f'Faltan {meses - 1} mes(es) sin registro: este consumo los incluye.')
        return ' '.join(avisos) or None


class PesajeResiduos(AuditableModel):
    codigo = models.CharField('N° de pesaje', max_length=16, unique=True, editable=False)
    sede = models.ForeignKey('organizacion.Sede', verbose_name='Sede', on_delete=models.PROTECT, null=True,
                             blank=True, related_name='pesajes_residuos')
    tipo = models.CharField('Tipo de pesaje', max_length=8, choices=TIPOS_PESAJE, default='ingreso')
    fecha = models.DateField('Fecha', default=timezone.localdate)
    hora = models.TimeField('Hora', null=True, blank=True)
    responsable = models.ForeignKey('organizacion.Trabajador', verbose_name='Responsable del pesaje',
                                    on_delete=models.PROTECT, null=True, blank=True, related_name='pesajes_residuos')
    # [{categoria, tipo, kg, litros, cantidad, observaciones}]
    items = models.JSONField('Detalle', default=list, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_PESAJE, default='en_registro')
    firma = models.JSONField('Firma de quien registra', default=dict, blank=True)
    motivo_anulacion = models.TextField('Motivo de la anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Pesaje de residuos'
        ordering = ['-fecha', '-id']

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = siguiente_codigo(PesajeResiduos, 'PES', (self.fecha or timezone.localdate()).year)
        super().save(*args, **kwargs)

    def totales(self):
        t = {k: {'kg': Decimal('0'), 'litros': Decimal('0'), 'cantidad': 0} for k, *_ in CATEGORIAS_RESIDUO}
        for i in self.items or []:
            c = t.get(i.get('categoria'))
            if c is None:
                continue
            c['kg'] += Decimal(str(i.get('kg') or 0))
            c['litros'] += Decimal(str(i.get('litros') or 0))
            c['cantidad'] += int(i.get('cantidad') or 0)
        no_peligrosos = t['azul']['kg'] + t['blanco']['kg']
        peligrosos = t['rojo_solido']['kg'] + t['raee']['kg']
        return {'por_categoria': t, 'no_peligrosos_kg': no_peligrosos, 'peligrosos_kg': peligrosos,
                'peligrosos_litros': t['rojo_liquido']['litros'], 'total_kg': no_peligrosos + peligrosos}


class DisposicionResiduos(AuditableModel):
    sede = models.ForeignKey('organizacion.Sede', verbose_name='Sede', on_delete=models.PROTECT, null=True,
                             blank=True, related_name='disposiciones_residuos')
    fecha = models.DateField('Fecha')
    grupo = models.CharField('Residuo', max_length=14, choices=GRUPOS_DISPOSICION)
    descripcion = models.CharField('Descripción', max_length=200, blank=True)
    kg = models.DecimalField('Cantidad (kg)', max_digits=10, decimal_places=2)
    destino = models.CharField('Destino', max_length=12, choices=DESTINOS)
    operadora = models.CharField('Operadora / receptor', max_length=150, blank=True)
    registro_operadora = models.CharField('N° de registro de la operadora', max_length=60, blank=True)
    manifiesto = models.CharField('N° de manifiesto / guía', max_length=60, blank=True)
    certificado = models.FileField('Certificado / constancia', upload_to='ambiente/disposiciones/%Y/', null=True,
                                   blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Disposición de residuos'
        ordering = ['-fecha', '-id']
