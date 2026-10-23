"""
M3 Riesgos y oportunidades, según el procedimiento de gestión de riesgos y oportunidades.

- Nivel por valor (1–3, 4–7, 8–14, 15–19, 20–25); ¿requiere acción?: riesgo ≥ 8, oportunidad ≥ 15 (8–14 en cartera).
- Registro en la matriz exige identificación, valoración y tratamiento (si corresponde); luego solo revaloración.
- Aceptar un riesgo Importante o Crítico: firma del Gerente General.
- Verificación: acciones ejecutadas, fecha ≥ ejecución + 3 meses; eficacia por valoración residual.
- Oportunidades de mejora: decisión, implementación, eficacia.
- Carga inicial de las matrices existentes.
"""
from datetime import timedelta

from django.utils import timezone

from core.tests.base import CasoBase
from procesos.models import Proceso
from riesgos.models import OportunidadMejora, RevisionMatriz, RiesgoOportunidad, nivel_de

HOY = timezone.localdate


class BaseRiesgos(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gerente_sig_r', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'riesgos', 'leer', 'crear', 'editar', 'eliminar')
        self.gg = self.crear_usuario('gerente_general_r', cargo='Gerente General', sigla_cargo='GG')
        self.dar_permisos(self.gg, 'riesgos', 'leer', 'crear', 'editar', 'aprobar')
        self.met = Proceso.objects.get(nombre='Metrología')
        self.autenticar(self.sig)

    def _post(self, r, accion, datos=None, fmt='json', usuario=None, base='riesgos'):
        if usuario:
            self.autenticar(usuario)
        return self.client.post(f'/api/{base}/{r.pk}/{accion}/', datos or {}, format=fmt)

    def _nuevo(self, tipo='riesgo', p=3, i=4, **extra):
        datos = {'tipo': tipo, 'proceso': self.met.pk, 'categoria': 'tecnico_metrologico',
                 'fuente': 'actividad_del_proceso', 'actividad': 'Calibración de manómetros',
                 'descripcion': 'Uso de un patrón con calibración vencida.',
                 'causa': 'Falta de control del programa de calibración.', 'efecto': 'Certificados inválidos.',
                 'controles_existentes': 'Programa anual de calibración.', 'probabilidad': p, 'impacto': i}
        datos.update(extra)
        r = self.client.post('/api/riesgos/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return RiesgoOportunidad.objects.get(pk=r.data['id'])

    def _accion(self, r, **extra):
        datos = {'actividad': 'Alerta de vencimiento de patrones', 'responsable': self.sig.pk,
                 'fecha_maxima': str(HOY() + timedelta(days=30)), 'recursos': 'Sistema'}
        datos.update(extra)
        res = self._post(r, 'agregar_accion', datos)
        self.assertEqual(res.status_code, 201, res.data)
        return r.acciones.order_by('-id').first()


class PruebasValoracion(BaseRiesgos):

    def test_niveles_y_requiere_accion(self):
        self.assertEqual([nivel_de(v) for v in (1, 3, 4, 7, 8, 14, 15, 19, 20, 25)],
                         ['no_significativo', 'no_significativo', 'tolerado', 'tolerado', 'moderado', 'moderado',
                          'importante', 'importante', 'critico', 'critico'])
        r = self._nuevo(p=2, i=4)
        self.assertEqual((r.valor, r.nivel, r.requiere_accion), (8, 'moderado', 'si'))
        o = self._nuevo(tipo='oportunidad', p=3, i=4, estrategia='')
        self.assertEqual(o.requiere_accion, 'en_cartera')
        o2 = self._nuevo(tipo='oportunidad', p=4, i=4)
        self.assertEqual(o2.requiere_accion, 'si')
        self.assertTrue(r.codigo.startswith('R-') and o.codigo.startswith('O-'))

    def test_estrategia_segun_tipo(self):
        r = self.client.post('/api/riesgos/', {'tipo': 'riesgo', 'descripcion': 'x', 'estrategia': 'incrementar'},
                             format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post('/api/riesgos/', {'tipo': 'oportunidad', 'descripcion': 'x', 'estrategia': 'reducir'},
                             format='json')
        self.assertEqual(r.status_code, 400)

    def test_escala_1_a_5(self):
        r = self.client.post('/api/riesgos/', {'tipo': 'riesgo', 'descripcion': 'x', 'probabilidad': 6},
                             format='json')
        self.assertEqual(r.status_code, 400)


class PruebasRegistro(BaseRiesgos):

    def test_registro_exige_tratamiento_si_requiere_accion(self):
        r = self._nuevo()
        res = self._post(r, 'registrar')
        self.assertEqual(res.status_code, 400)
        self.assertIn('estrategia', res.data['detail'])
        self.client.patch(f'/api/riesgos/{r.pk}/', {'estrategia': 'reducir'}, format='json')
        self.assertIn('acción', self._post(r, 'registrar').data['detail'])
        self._accion(r)
        res = self._post(r, 'registrar')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['estado'], 'vigente')

    def test_tolerado_se_registra_sin_tratamiento(self):
        r = self._nuevo(p=1, i=4)
        self.assertEqual(self._post(r, 'registrar').status_code, 200)

    def test_en_la_matriz_solo_se_revalora(self):
        r = self._nuevo(p=1, i=4)
        self._post(r, 'registrar')
        res = self.client.patch(f'/api/riesgos/{r.pk}/', {'probabilidad': 3}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('revaloración', res.data['detail'])
        self.assertEqual(self._post(r, 'revalorar', {'probabilidad': 3, 'impacto': 4}).status_code, 400)
        res = self._post(r, 'revalorar', {'probabilidad': 3, 'impacto': 4, 'motivo': 'Revisión anual.'})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['valor'], 12)
        self.assertEqual(res.data['historial'][-1]['de'], '1×4')

    def test_aceptar_importante_exige_firma_del_gerente_general(self):
        r = self._nuevo(p=4, i=4, estrategia='aceptar',
                        justificacion_aceptacion='El costo de reducirlo supera el impacto esperado.')
        res = self._post(r, 'registrar')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Gerente General', res.data['detail'])
        self.assertEqual(self._post(r, 'aceptar_riesgo', {'password': self.CLAVE}).status_code, 403)
        self.assertEqual(self._post(r, 'aceptar_riesgo', {'password': 'x'}, usuario=self.gg).status_code, 400)
        res = self._post(r, 'aceptar_riesgo', {'password': self.CLAVE}, usuario=self.gg)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['firma_aceptacion']['sigla'], 'GG')
        self.autenticar(self.sig)
        self.assertEqual(self._post(r, 'registrar').status_code, 200)
        # Firmada la aceptación, la estrategia y su decisión no se tocan; la revaloración anula la firma.
        res = self.client.patch(f'/api/riesgos/{r.pk}/', {'justificacion_aceptacion': 'Otra razón.'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('firmada', res.data['detail'])
        res = self._post(r, 'revalorar', {'probabilidad': 4, 'impacto': 5, 'motivo': 'Nuevo cliente dominante.'})
        self.assertEqual(res.data['firma_aceptacion'], {})
        self.assertIn('aceptacion_anulada', res.data['historial'][-1])

    def test_cartera_decide_la_alta_direccion(self):
        o = self._nuevo(tipo='oportunidad', p=3, i=3)
        self._post(o, 'registrar')
        self.assertEqual(self._post(o, 'decidir_cartera', {'decision': 'abordar', 'motivo': 'x'}).status_code, 403)
        res = self._post(o, 'decidir_cartera', {'decision': 'descartar', 'motivo': 'Sin presupuesto este año.'},
                         usuario=self.gg)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['situacion'], 'descartado')


class PruebasSeguimientoYEficacia(BaseRiesgos):

    def _en_matriz(self):
        r = self._nuevo(estrategia='reducir')
        a = self._accion(r)
        self.assertEqual(self._post(r, 'registrar').status_code, 200)
        return r, a

    def test_verificacion_exige_acciones_ejecutadas_y_tres_meses(self):
        r, a = self._en_matriz()
        datos = {'residual_probabilidad': 1, 'residual_impacto': 4, 'fecha_verificacion': str(HOY()),
                 'evidencia': 'Sin patrones vencidos en 3 meses.'}
        self.assertIn('ejecutadas', self._post(r, 'verificar', datos).data['detail'])
        res = self._post(r, 'seguimiento_accion', {'accion_id': a.pk, 'estado': 'ejecutado',
                                                   'fecha_ejecucion': str(HOY())}, fmt='multipart')
        self.assertEqual(res.status_code, 400)
        res = self._post(r, 'seguimiento_accion', {'accion_id': a.pk, 'estado': 'ejecutado',
                                                   'fecha_ejecucion': str(HOY() - timedelta(days=10)),
                                                   'observaciones': 'Alerta configurada.'}, fmt='multipart')
        self.assertEqual(res.status_code, 200, res.data)
        res = self._post(r, 'verificar', datos)
        self.assertEqual(res.status_code, 400)
        self.assertIn('tres meses', res.data['detail'])
        a.refresh_from_db()
        a.fecha_ejecucion = HOY() - timedelta(days=100)
        a.save()
        res = self._post(r, 'verificar', datos)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data['valor_residual'], res.data['eficacia']), (4, 'eficaz'))
        res = self.client.patch(f'/api/riesgos/{r.pk}/', {'estrategia': 'evitar'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_no_eficaz_abre_nuevo_tratamiento(self):
        r, a = self._en_matriz()
        self._post(r, 'seguimiento_accion', {'accion_id': a.pk, 'estado': 'ejecutado',
                                             'fecha_ejecucion': str(HOY() - timedelta(days=95)),
                                             'observaciones': 'Hecho.'}, fmt='multipart')
        res = self._post(r, 'verificar', {'residual_probabilidad': 3, 'residual_impacto': 4,
                                          'fecha_verificacion': str(HOY()), 'evidencia': 'Igual.'})
        self.assertEqual(res.data['eficacia'], 'sin_cambio')
        self.assertEqual(self._post(r, 'agregar_accion', {'actividad': 'Otra'}).status_code, 400)
        res = self._post(r, 'nuevo_tratamiento', {'motivo': 'Se cambia el control.'})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIsNone(res.data['valor_residual'])
        self.assertEqual(res.data['historial'][-1]['eficacia'], 'sin_cambio')
        self._accion(r, actividad='Doble verificación del estado del patrón antes de usarlo')

    def test_accion_vencida_se_registra_como_hallazgo(self):
        r, a = self._en_matriz()
        self.assertEqual(self._post(r, 'registrar_incumplimiento', {'accion_id': a.pk}).status_code, 400)
        a.fecha_maxima = HOY() - timedelta(days=1)
        a.save()
        res = self._post(r, 'registrar_incumplimiento', {'accion_id': a.pk})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data['acciones'][0]['hallazgo_codigo'])

    def test_materializacion_registra_hallazgo(self):
        r, _ = self._en_matriz()
        res = self._post(r, 'materializar', {'descripcion': 'Se usó un patrón vencido en una OT.'})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['historial'][-1]['accion'], 'Materialización')

    def test_retiro_con_motivo(self):
        r, _ = self._en_matriz()
        self.assertEqual(self._post(r, 'retirar').status_code, 400)
        res = self._post(r, 'retirar', {'motivo': 'El servicio dejó de prestarse.'})
        self.assertEqual(res.data['estado'], 'retirado')
        self.assertEqual(self.client.delete(f'/api/riesgos/{r.pk}/').status_code, 400)


class PruebasOportunidadesDeMejora(BaseRiesgos):

    def _om(self):
        res = self.client.post('/api/oportunidades-mejora/', {
            'proceso': self.met.pk, 'fuente': 'sugerencia_del_personal', 'detectado_por': 'Metrólogo',
            'descripcion': 'Automatizar el cálculo de incertidumbre.', 'situacion': 'Cálculo manual.'}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        return OportunidadMejora.objects.get(pk=res.data['id'])

    def test_flujo_decision_implementacion_eficacia(self):
        o = self._om()
        self.assertTrue(o.codigo.startswith('OM-'))
        res = self._post(o, 'decidir', {'decision': 'se_implementa', 'justificacion': 'Reduce errores.'},
                         base='oportunidades-mejora')
        self.assertEqual(res.status_code, 400)
        res = self._post(o, 'decidir', {'decision': 'se_implementa', 'justificacion': 'Reduce errores.',
                                        'accion': 'Desarrollar la hoja', 'responsable': self.sig.pk,
                                        'fecha_maxima': str(HOY() + timedelta(days=20))}, base='oportunidades-mejora')
        self.assertEqual(res.status_code, 200, res.data)
        res = self.client.patch(f'/api/oportunidades-mejora/{o.pk}/', {'descripcion': 'otra'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self._post(o, 'evaluar_eficacia', {'eficacia': 'lograda'},
                                    base='oportunidades-mejora').status_code, 400)
        res = self._post(o, 'seguimiento', {'estado': 'ejecutado', 'fecha_ejecucion': str(HOY()),
                                            'evidencia': 'Hoja en uso.'}, fmt='multipart', base='oportunidades-mejora')
        self.assertEqual(res.status_code, 200, res.data)
        res = self._post(o, 'evaluar_eficacia', {'eficacia': 'lograda', 'fecha_verificacion': str(HOY()),
                                                 'evidencia': 'Cero errores de cálculo en el mes.'},
                         base='oportunidades-mejora')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data['cerrada'])

    def test_no_se_implementa_exige_justificacion(self):
        o = self._om()
        self.assertEqual(self._post(o, 'decidir', {'decision': 'no_se_implementa'},
                                    base='oportunidades-mejora').status_code, 400)
        res = self._post(o, 'decidir', {'decision': 'no_se_implementa', 'justificacion': 'Ya no aplica.'},
                         base='oportunidades-mejora')
        self.assertTrue(res.data['cerrada'])


class PruebasRevisionesYCarga(BaseRiesgos):

    def test_supervision_independiente_con_firma(self):
        res = self.client.post('/api/revisiones-riesgos/actualizacion/', {'matriz': 'ryo', 'password': self.CLAVE},
                               format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.dar_permisos(self.sig, 'riesgos', 'aprobar')
        res = self.client.post('/api/revisiones-riesgos/supervision/', {'matriz': 'ryo', 'password': self.CLAVE},
                               format='json')
        self.assertEqual(res.status_code, 400)
        self.autenticar(self.gg)
        res = self.client.post('/api/revisiones-riesgos/supervision/', {'matriz': 'ryo', 'password': self.CLAVE},
                               format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(RevisionMatriz.objects.filter(tipo='supervision').count(), 1)

    def test_carga_inicial(self):
        self.assertEqual(RiesgoOportunidad.objects.count(), 151)
        self.assertEqual(OportunidadMejora.objects.count(), 28)
        r = RiesgoOportunidad.objects.get(codigo='R-005')
        self.assertEqual(r.proceso.nombre, 'Metrología')
        self.assertTrue(RiesgoOportunidad.objects.filter(proceso__nombre='Recepción de Equipos y/o Instrumentos')
                        .exists())

    def test_indicadores_y_pdfs(self):
        res = self.client.get('/api/riesgos/indicadores/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['riesgos_oportunidades'][0]['total'], 151)
        self.assertEqual(len(res.data['mapa_riesgos']), 5)
        for url in ('/api/riesgos/matriz_pdf/', '/api/oportunidades-mejora/matriz_pdf/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertTrue(r.content.startswith(b'%PDF'))
