"""
M12 Competencia técnica — autorización según el procedimiento de autorización
del personal técnico.

- Un entrenamiento se da por superado solo con todas las actividades y todos los
  ítems de supervisión conformes, nota teórica de 14 o más y un control de
  validez satisfactorio. Concluido, es de solo lectura y no se elimina.
- Una autorización queda vigente solo si la persona superó el entrenamiento del
  mismo método. Excepción: el Gerente Técnico, eximido con sustento.
- Suspendida, se reautoriza solo con un re-entrenamiento superado después de la
  suspensión. Revocada, no se reactiva.
- Seguimiento: el servidor calcula total, máximo, mínimo (70 %), n.° de
  preguntas y resultado con las fórmulas del formato; la decisión es coherente
  con el resultado.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Autorizacion, ControlValidez, MetodoCalibracion, ProcesoEntrenamiento


class BaseCompetencia(CasoBase):

    def setUp(self):
        self.gt = self.crear_usuario('gerente_tec', cargo='Gerente Técnico')
        self.dar_permisos(self.gt, 'competencia_tecnica', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.gt)
        self.tecnico = self.crear_usuario('metrologo', cargo='Metrólogo')
        self.m = MetodoCalibracion.objects.create(nombre='Calibración de pesas', codigo='PC-021')
        self.cv = ControlValidez.objects.create(nombre='Réplica')

    def _entrenamiento(self, tipo='entrenamiento'):
        r = self.client.post('/api/procesos-entrenamiento/', {
            'usuario': self.tecnico.pk, 'metodo': self.m.pk, 'tutor': self.gt.pk, 'tipo': tipo,
            'checklist_entrenamiento': [{'actividad': 'Lectura del procedimiento', 'conformidad': 'CONFORME'}]},
            format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data['id']

    def _superar(self, pk, **extra):
        datos = {'tutor_supervision': self.gt.pk, 'checklist_supervision': [{'item': 'Ejecuta la calibración',
                                                                               'conformidad': 'CONFORME'}],
                 'nota_teorica': 16, 'control_validez': self.cv.pk, 'resultado_control': 'satisfactorio',
                 'estado': 'completado'}
        datos.update(extra)
        return self.client.patch(f'/api/procesos-entrenamiento/{pk}/', datos, format='json')

    def _autorizar(self, usuario=None, **extra):
        datos = {'usuario': (usuario or self.tecnico).pk, 'metodo': self.m.pk, 'funciones': ['ejecutar'],
                 'estado': 'vigente', 'fecha_autorizacion': '2026-10-20'}
        datos.update(extra)
        return self.client.post('/api/autorizaciones/', datos, format='json')


class PruebasEntrenamientoSuperado(BaseCompetencia):

    def test_requisitos_para_superar(self):
        pk = self._entrenamiento()
        casos = [({'nota_teorica': 13.5}, 'nota teórica'),
                 ({'resultado_control': 'no_satisfactorio'}, 'control de validez'),
                 ({'control_validez': None}, 'control de validez'),
                 ({'checklist_supervision': [{'item': 'x', 'conformidad': 'NO CONFORME'}]}, 'supervisión'),
                 ({'checklist_supervision': []}, 'supervisión'),
                 ({'tutor_supervision': None}, 'tutor')]
        for extra, texto in casos:
            r = self._superar(pk, **extra)
            self.assertEqual(r.status_code, 400, extra)
            self.assertIn(texto, str(r.data['estado']), extra)
        r = self._superar(pk)
        self.assertEqual(r.status_code, 200, r.data)

    def test_actividad_no_conforme_impide_superar(self):
        pk = self._entrenamiento()
        r = self._superar(pk, checklist_entrenamiento=[{'actividad': 'a', 'conformidad': 'CONFORME'},
                                                       {'actividad': 'b', 'conformidad': ''}])
        self.assertEqual(r.status_code, 400)
        self.assertIn('actividades', str(r.data['estado']))

    def test_concluido_es_solo_lectura_y_no_se_elimina(self):
        pk = self._entrenamiento()
        self._superar(pk)
        r = self.client.patch(f'/api/procesos-entrenamiento/{pk}/', {'comentarios': 'cambio'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('solo lectura', str(r.data))
        r = self.client.delete(f'/api/procesos-entrenamiento/{pk}/')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(ProcesoEntrenamiento.objects.get(pk=pk).is_active)


class PruebasAutorizacionExigeEntrenamiento(BaseCompetencia):

    def test_vigente_sin_entrenamiento_superado_se_rechaza(self):
        r = self._autorizar()
        self.assertEqual(r.status_code, 400)
        self.assertIn('entrenamiento', str(r.data['estado']))
        pk = self._entrenamiento()
        self.assertEqual(self._autorizar().status_code, 400, 'en proceso no basta')
        self._superar(pk)
        r = self._autorizar()
        self.assertEqual(r.status_code, 201, r.data)

    def test_en_entrenamiento_no_lo_exige_pero_pasar_a_vigente_si(self):
        r = self._autorizar(estado='en_entrenamiento', fecha_autorizacion=None)
        self.assertEqual(r.status_code, 201, r.data)
        r = self.client.patch(f'/api/autorizaciones/{r.data["id"]}/', {'estado': 'vigente',
                                                                     'fecha_autorizacion': '2026-10-20'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_entrenamiento_de_otro_metodo_no_cuenta(self):
        pk = self._entrenamiento()
        self._superar(pk)
        otro = MetodoCalibracion.objects.create(nombre='Calibración de balanzas')
        self.assertEqual(self._autorizar(metodo=otro.pk).status_code, 400)

    def test_exencion_solo_gerente_tecnico_con_sustento(self):
        r = self._autorizar(exento_entrenamiento=True, sustento_exencion='Experiencia')
        self.assertIn('exento_entrenamiento', r.data, 'el metrólogo no se exime')
        r = self._autorizar(usuario=self.gt, exento_entrenamiento=True)
        self.assertIn('sustento_exencion', r.data)
        r = self._autorizar(usuario=self.gt, exento_entrenamiento=True, funciones=['firmar'], alcance_firma='todos',
                            sustento_exencion='Ingeniero, 15 años en metrología, ensayos de aptitud satisfactorios')
        self.assertEqual(r.status_code, 201, r.data)

    def test_suspendida_se_reautoriza_solo_con_reentrenamiento_posterior(self):
        self._superar(self._entrenamiento())
        aut = self._autorizar().data['id']
        r = self.client.post('/api/evaluaciones-seguimiento/', {
            'usuario': self.tecnico.pk, 'autorizacion': aut, 'tipo': 'control_validez',
            'resultado': 'no_satisfactorio', 'decision': 'suspender'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        a = Autorizacion.objects.get(pk=aut)
        self.assertEqual(a.estado, 'suspendida')
        self.assertIsNotNone(a.suspendida_en)
        # El entrenamiento inicial no sirve para reautorizar.
        r = self.client.patch(f'/api/autorizaciones/{aut}/', {'estado': 'vigente'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('re-entrenamiento', str(r.data['estado']))
        seg = {'usuario': self.tecnico.pk, 'autorizacion': aut, 'tipo': 'control_validez',
               'resultado': 'satisfactorio', 'decision': 'reautorizar'}
        r = self.client.post('/api/evaluaciones-seguimiento/', seg, format='json')
        self.assertEqual(r.status_code, 400)
        self._superar(self._entrenamiento(tipo='reentrenamiento'))
        r = self.client.post('/api/evaluaciones-seguimiento/', seg, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Autorizacion.objects.get(pk=aut).estado, 'vigente')

    def test_revocada_no_se_reactiva(self):
        self._superar(self._entrenamiento())
        aut = self._autorizar().data['id']
        self.client.patch(f'/api/autorizaciones/{aut}/', {'estado': 'revocada'}, format='json')
        r = self.client.patch(f'/api/autorizaciones/{aut}/', {'estado': 'vigente'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('revocada', str(r.data['estado']))


class PruebasTotalesSeguimiento(BaseCompetencia):

    def _seg(self, preguntas, **extra):
        datos = {'usuario': self.tecnico.pk, 'tipo': 'entrevista', 'preguntas': preguntas,
                 # Lo que mande la pantalla no cuenta: el servidor recalcula.
                 'puntaje_total': 999, 'puntaje_minimo': 1, 'puntaje_maximo': 2, 'n_preguntas': 50,
                 'resultado': 'satisfactorio'}
        datos.update(extra)
        return self.client.post('/api/evaluaciones-seguimiento/', datos, format='json')

    def test_formulas_del_formato(self):
        preg = [{'establecido': 4, 'obtenido': 3}, {'establecido': 4, 'obtenido': 4},
                {'establecido': 4, 'obtenido': 2}, {'establecido': 4, 'obtenido': 3}, {'establecido': 4, 'obtenido': 3}]
        r = self._seg(preg)
        self.assertEqual(r.status_code, 201, r.data)
        d = r.data
        self.assertEqual((d['puntaje_total'], d['puntaje_maximo'], d['puntaje_minimo'], d['n_preguntas']),
                         (15, 20, 14, 5))
        self.assertEqual(d['resultado'], 'satisfactorio')
        self.assertEqual([p['n'] for p in d['preguntas']], [1, 2, 3, 4, 5])

    def test_bajo_el_minimo_es_no_satisfactorio_y_no_se_mantiene(self):
        preg = [{'establecido': 4, 'obtenido': 1}, {'establecido': 4, 'obtenido': 2}]
        r = self._seg(preg, decision='mantener')
        self.assertEqual(r.status_code, 400)
        self.assertIn('decision', r.data)
        r = self._seg(preg)
        self.assertEqual(r.data['resultado'], 'no_satisfactorio')

    def test_puntaje_por_pregunta_define_el_maximo(self):
        r = self._seg([{'establecido': 4, 'obtenido': 4}], puntaje_por_pregunta=5)
        self.assertEqual((r.data['puntaje_maximo'], r.data['puntaje_minimo']), (5, 3.5))

    def test_obtenido_no_supera_establecido(self):
        r = self._seg([{'establecido': 4, 'obtenido': 5}])
        self.assertEqual(r.status_code, 400)
        self.assertIn('supera', str(r.data['preguntas']))

    def test_decidir_exige_resultado_y_autorizacion(self):
        r = self.client.post('/api/evaluaciones-seguimiento/', {'usuario': self.tecnico.pk, 'tipo': 'testificacion',
                                                                 'decision': 'suspender'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('resultado', r.data)
        self.assertIn('autorizacion', r.data)
