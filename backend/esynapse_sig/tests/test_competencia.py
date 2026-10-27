"""
M12 Competencia técnica — reglas de técnico autorizado (regla 5) y firma
controlada (regla 7). La función `esta_autorizado` es la que consultarán las
órdenes de trabajo y la emisión de certificados.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Autorizacion, MetodoCalibracion, esta_autorizado


class PruebasAutorizacion(CasoBase):

    def setUp(self):
        self.tecnico = self.crear_usuario('tecnico', laboratorio='Masa')
        self.metodo = MetodoCalibracion.objects.create(nombre='Calibración de balanzas', magnitud='Masa')
        self.otro_metodo = MetodoCalibracion.objects.create(nombre='Calibración de termómetros', magnitud='Temperatura')

    def _autorizar(self, estado='vigente', funciones=None, **extra):
        return Autorizacion.objects.create(
            usuario=self.tecnico, metodo=self.metodo, magnitud='Masa',
            funciones=funciones if funciones is not None else ['ejecutar'],
            estado=estado, **extra)

    def test_autorizacion_vigente_permite_ejecutar(self):
        self._autorizar()
        self.assertTrue(esta_autorizado(self.tecnico, self.metodo, 'ejecutar'))

    def test_sin_autorizacion_no_puede_ejecutar(self):
        self.assertFalse(esta_autorizado(self.tecnico, self.metodo, 'ejecutar'))

    def test_en_entrenamiento_no_cuenta_como_autorizado(self):
        self._autorizar(estado='en_entrenamiento')
        self.assertFalse(esta_autorizado(self.tecnico, self.metodo, 'ejecutar'))

    def test_suspendida_o_revocada_bloquea(self):
        a = self._autorizar()
        self.assertTrue(esta_autorizado(self.tecnico, self.metodo, 'ejecutar'))
        a.estado = 'suspendida'
        a.save()
        self.assertFalse(esta_autorizado(self.tecnico, self.metodo, 'ejecutar'))
        a.estado = 'revocada'
        a.save()
        self.assertFalse(esta_autorizado(self.tecnico, self.metodo, 'ejecutar'))

    def test_autorizacion_es_por_metodo(self):
        self._autorizar()
        self.assertFalse(esta_autorizado(self.tecnico, self.otro_metodo, 'ejecutar'))

    def test_la_funcion_importa(self):
        self._autorizar(funciones=['ejecutar'])
        self.assertFalse(esta_autorizado(self.tecnico, self.metodo, 'supervisar'))

    def test_autorizacion_inactiva_no_cuenta(self):
        self._autorizar(is_active=False)
        self.assertFalse(esta_autorizado(self.tecnico, self.metodo, 'ejecutar'))


class PruebasFirmaControlada(CasoBase):
    """Regla 7: el firmante autorizado firma solo dentro de su alcance."""

    def setUp(self):
        self.gt = self.crear_usuario('gerente_tecnico')
        self.encargado = self.crear_usuario('encargado_masa', laboratorio='Masa')
        self.metodo = MetodoCalibracion.objects.create(nombre='Genérico')

    def test_gerente_tecnico_firma_en_todos_los_laboratorios(self):
        Autorizacion.objects.create(usuario=self.gt, metodo=self.metodo, funciones=['firmar'],
                                    alcance_firma='todos', estado='vigente')
        self.assertTrue(esta_autorizado(self.gt, funcion='firmar', laboratorio='Masa'))
        self.assertTrue(esta_autorizado(self.gt, funcion='firmar', laboratorio='Temperatura'))

    def test_encargado_firma_solo_en_su_laboratorio(self):
        Autorizacion.objects.create(usuario=self.encargado, metodo=self.metodo, funciones=['firmar'],
                                    alcance_firma='laboratorio', laboratorio='Masa', estado='vigente')
        self.assertTrue(esta_autorizado(self.encargado, funcion='firmar', laboratorio='Masa'))
        self.assertFalse(esta_autorizado(self.encargado, funcion='firmar', laboratorio='Temperatura'))

    def test_sin_funcion_firmar_no_firma(self):
        Autorizacion.objects.create(usuario=self.encargado, metodo=self.metodo, funciones=['ejecutar'],
                                    alcance_firma='todos', estado='vigente')
        self.assertFalse(esta_autorizado(self.encargado, funcion='firmar', laboratorio='Masa'))


class PruebasReautorizacionTrasSuspension(CasoBase):
    """Una suspensión exige re-entrenamiento posterior por cualquier camino (revisión 2026-10-23)."""

    def setUp(self):
        self.tecnico = self.crear_usuario('tecnico2', laboratorio='Masa')
        self.metodo = MetodoCalibracion.objects.create(nombre='Calibración de pesas', magnitud='Masa')
        from esynapse_sig.models import ProcesoEntrenamiento
        # Entrenamiento inicial superado (antes de la suspensión): no basta para reautorizar.
        ProcesoEntrenamiento.objects.create(usuario=self.tecnico, metodo=self.metodo, estado='completado',
                                            created_by=self.tecnico)
        self.a = Autorizacion.objects.create(usuario=self.tecnico, metodo=self.metodo, magnitud='Masa',
                                             funciones=['ejecutar'], estado='suspendida')

    def _valido(self, inst, **datos):
        from django.utils import timezone
        from esynapse_sig.serializers import AutorizacionSerializer
        base = {'usuario': self.tecnico.pk, 'metodo': self.metodo.pk, 'magnitud': 'Masa', 'funciones': ['ejecutar'],
                'fecha_autorizacion': str(timezone.localdate())}
        s = AutorizacionSerializer(inst, data={**base, **datos}, partial=inst is not None)
        return s.is_valid()

    def test_pasar_por_en_entrenamiento_no_salta_el_reentrenamiento(self):
        self.a.estado = 'en_entrenamiento'
        self.a.save()
        self.assertFalse(self._valido(self.a, estado='vigente'))

    def test_autorizacion_nueva_tampoco(self):
        self.assertFalse(self._valido(None, estado='vigente'))
