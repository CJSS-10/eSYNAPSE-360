"""
M2 Requisitos legales, según el procedimiento de identificación, acceso y evaluación
de requisitos legales y otros requisitos.

- Lista de requisitos por ámbito (incluye «Acreditación»); derogar saca sus obligaciones de las evaluaciones.
- Evaluación semestral por ámbito: una en curso a la vez; no cierra con pendientes; cierre con firma.
- Cada incumplimiento se registra como hallazgo al cerrar; la evaluación cerrada no se modifica.
- Un cambio normativo puede abrir una solicitud de cambio.
- Carga inicial de la lista y de la matriz existentes.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Hallazgo
from legal.models import Evaluacion, Obligacion, Requisito


class BaseLegal(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gerente_sig_l', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'legal', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.dar_permisos(self.sig, 'cambios', 'leer', 'crear')
        self.lector = self.crear_usuario('lector_l')
        self.dar_permisos(self.lector, 'legal', 'leer')
        self.autenticar(self.sig)

    def _requisito(self, **extra):
        datos = {'ambito': 'acreditacion', 'tema': 'INACAL', 'tipo': 'Directriz', 'codigo': 'DA-acr-06D',
                 'nombre': 'Directriz para la acreditación de laboratorios', 'fecha_aprobacion': '2024-01-10'}
        datos.update(extra)
        r = self.client.post('/api/requisitos-legales/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return Requisito.objects.get(pk=r.data['id'])

    def _obligacion(self, req, **extra):
        datos = {'ambito': req.ambito, 'tema': req.tema, 'requisito': req.pk, 'articulo': '6.1',
                 'extracto': 'Mantener la revisión por la dirección anual.', 'evidencia_documento': 'Acta de revisión',
                 'responsable': 'Gerente SIG', 'periodicidad': 'Anual'}
        datos.update(extra)
        r = self.client.post('/api/obligaciones-legales/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return Obligacion.objects.get(pk=r.data['id'])

    def _evaluacion(self, ambito='acreditacion', periodo='Semestre 2'):
        r = self.client.post('/api/evaluaciones-legales/', {'ambito': ambito, 'anio': 2026, 'periodo': periodo},
                             format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return Evaluacion.objects.get(pk=r.data['id'])

    def _resultados(self, e):
        return self.client.get(f'/api/evaluaciones-legales/{e.pk}/resultados/').data


class PruebasLista(BaseLegal):

    def test_ambito_acreditacion_y_orden(self):
        r1 = self._requisito()
        r2 = self._requisito(codigo='DA-acr-01P', nombre='Reglamento de acreditación')
        self.assertEqual((r1.orden, r2.orden), (1, 2))
        self.assertEqual(self.client.patch(f'/api/requisitos-legales/{r1.pk}/', {'ambito': 'sst'},
                                           format='json').status_code, 400)

    def test_lector_no_edita(self):
        self.autenticar(self.lector)
        r = self.client.post('/api/requisitos-legales/', {'ambito': 'sst', 'nombre': 'x'}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_modificatoria_y_derogacion(self):
        req = self._requisito()
        o = self._obligacion(req)
        res = self.client.post(f'/api/requisitos-legales/{req.pk}/registrar_modificacion/',
                               {'descripcion': 'Modificada por DA-acr-06D v.08', 'fecha': '2026-05-01'}, format='json')
        self.assertIn('v.08 (2026-05-01)', res.data['modificatorias'])
        e = self._evaluacion()
        self.assertEqual(self.client.post(f'/api/requisitos-legales/{req.pk}/derogar/', {}, format='json')
                         .status_code, 400)
        res = self.client.post(f'/api/requisitos-legales/{req.pk}/derogar/', {'motivo': 'Reemplazada por DA-acr-06E'},
                               format='json')
        self.assertEqual(res.data['estado'], 'derogada')
        o.refresh_from_db()
        self.assertEqual(o.estado, 'derogada')
        self.assertEqual(self._resultados(e)[0]['resultado'], 'no_aplica')
        self.assertEqual(self.client.patch(f'/api/requisitos-legales/{req.pk}/', {'nombre': 'x'},
                                           format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/requisitos-legales/{req.pk}/').status_code, 400)

    def test_solicitud_de_cambio_por_norma(self):
        req = self._requisito()
        res = self.client.post(f'/api/requisitos-legales/{req.pk}/solicitar_cambio/', {}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        from cambios.models import Cambio
        c = Cambio.objects.get(pk=res.data['cambio_id'])
        self.assertEqual((c.origen, c.motivo_origen), ('externo', 'Requisitos legales'))

    def test_comunicacion(self):
        req = self._requisito()
        self.assertEqual(self.client.post(f'/api/requisitos-legales/{req.pk}/comunicar/', {'medio': 'correo'},
                                          format='json').status_code, 400)
        res = self.client.post(f'/api/requisitos-legales/{req.pk}/comunicar/', {
            'medio': 'reunion', 'destinatarios': 'Metrología', 'resumen': 'Nueva directriz y su impacto.'}, format='json')
        self.assertEqual(len(res.data['comunicaciones']), 1)


class PruebasEvaluacion(BaseLegal):

    def test_una_en_curso_y_obligaciones_nuevas_se_suman(self):
        req = self._requisito()
        self._obligacion(req)
        e = self._evaluacion()
        r = self.client.post('/api/evaluaciones-legales/', {'ambito': 'acreditacion', 'periodo': 'Semestre 3'},
                             format='json')
        self.assertEqual(r.status_code, 400)
        self._obligacion(req, articulo='7.1')
        self.assertEqual(len(self._resultados(e)), 2)

    def test_cierre_exige_todo_evaluado_firma_y_genera_hallazgos(self):
        req = self._requisito()
        o1 = self._obligacion(req)
        self._obligacion(req, articulo='7.1')
        e = self._evaluacion()
        rs = self._resultados(e)
        url = f'/api/evaluaciones-legales/{e.pk}/'
        self.assertEqual(self.client.post(url + 'evaluar/', {'resultado_id': rs[0]['id'], 'resultado': 'no_cumple'},
                                          format='multipart').status_code, 400)
        for r, val in zip(rs, ('cumple', 'no_cumple')):
            res = self.client.post(url + 'evaluar/', {'resultado_id': r['id'], 'resultado': val,
                                                      'observaciones': 'Acta del 2026'}, format='multipart')
            self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(self.client.post(url + 'cerrar/', {}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url + 'cerrar/', {'password': 'mala'}, format='json').status_code, 400)
        n = Hallazgo.objects.count()
        res = self.client.post(url + 'cerrar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['resumen']['porcentaje'], 50.0)
        self.assertEqual(Hallazgo.objects.count(), n + 1)
        self.assertEqual(self.client.post(url + 'evaluar/', {'resultado_id': rs[0]['id'], 'resultado': 'no_cumple',
                                                             'observaciones': 'x'}, format='multipart').status_code, 400)
        res = self.client.get(f'/api/obligaciones-legales/{o1.pk}/')
        self.assertEqual(res.data['ultimo_resultado']['resultado'], 'cumple')

    def test_orden_por_numero_de_periodo(self):
        req = self._requisito()
        self._obligacion(req)
        e2 = self._evaluacion(periodo='Semestre 2')
        Evaluacion.objects.filter(pk=e2.pk).update(estado='cerrada')
        e1 = self._evaluacion(periodo='Semestre 1')
        self.assertEqual((Evaluacion.objects.get(pk=e1.pk).orden, Evaluacion.objects.get(pk=e2.pk).orden), (1, 2))

    def test_pendientes_bloquean_cierre(self):
        req = self._requisito()
        self._obligacion(req)
        e = self._evaluacion()
        res = self.client.post(f'/api/evaluaciones-legales/{e.pk}/cerrar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Faltan', res.data['detail'])

    def test_cerrar_requiere_aprobar(self):
        req = self._requisito()
        self._obligacion(req)
        e = self._evaluacion()
        self.autenticar(self.lector)
        self.assertEqual(self.client.post(f'/api/evaluaciones-legales/{e.pk}/cerrar/', {'password': self.CLAVE},
                                          format='json').status_code, 403)


class PruebasCargaYReportes(BaseLegal):

    def test_carga_inicial(self):
        self.assertEqual(Requisito.objects.count(), 299)
        self.assertEqual(Obligacion.objects.count(), 447)
        hist = Evaluacion.objects.filter(historica=True, ambito='sst').order_by('orden')
        self.assertEqual([e.periodo for e in hist], ['Cuatrimestre 1', 'Cuatrimestre 2', 'Cuatrimestre 3'])
        self.assertTrue(all(e.estado == 'cerrada' for e in hist))

    def test_indicadores_y_pdfs(self):
        res = self.client.get('/api/requisitos-legales/indicadores/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['ambitos']), 5)
        for url in ('/api/requisitos-legales/lista_pdf/?ambito=ma', '/api/evaluaciones-legales/matriz_pdf/?ambito=ma',
                    '/api/requisitos-legales/lista_pdf/?ambito=acreditacion'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertTrue(r.content.startswith(b'%PDF'))
