"""
EPP y vigilancia médica.

- Catálogo y matriz cargados; la matriz exige al trabajador los EPP de su puesto (y laboratorio).
- Entrega: la firma el responsable (contraseña) y el trabajador con su PIN; la primera vez crea el PIN;
  PIN incorrecto cuenta intentos y al quinto se bloquea; SIG lo restablece. Firmada no se modifica.
- Reposición: exige motivo y reemplaza el EPP anterior del mismo tipo; renovación según la vida útil.
- Devolución por cese; alerta de EPP de cesados sin devolver.
- Evaluación médica: solo aptitud; no se registra sin aptitud, restricciones (si aplica), próximo examen y centro.
"""
from datetime import date

from django.utils import timezone

from core.tests.base import CasoBase
from organizacion.models import Area, Puesto, Trabajador
from sst.epp import CatalogoEPP, EntregaEPP, PerfilEPP, PinTrabajador, sumar_meses

CLAVE = CasoBase.CLAVE


class BaseEPP(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gsig_epp', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'sst', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.sig)
        self.lab = Area.objects.get(nombre='Laboratorio de Masa y Volumen')
        self.t = Trabajador.objects.create(nombres='Luis', apellidos='Rojas', documento='41000001',
                                           puesto=Puesto.objects.get(nombre='Metrólogo'), area=self.lab)
        self.guantes = CatalogoEPP.objects.get(nombre='Guantes anticorte')
        self.botas = CatalogoEPP.objects.get(nombre='Botas de seguridad punta de acero')

    def _entrega(self, items=None, **extra):
        datos = {'trabajador': self.t.pk, 'fecha': str(timezone.localdate()), 'tipo': 'dotacion',
                 'items': items or [{'epp': self.guantes.pk, 'cantidad': 2, 'talla': 'M'}]}
        datos.update(extra)
        r = self.client.post('/api/sst-epp-entregas/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def _url(self, e, accion):
        return f'/api/sst-epp-entregas/{e["id"]}/{accion}/'


class PruebasMatriz(BaseEPP):

    def test_carga_y_requeridos_del_trabajador(self):
        self.assertGreaterEqual(CatalogoEPP.objects.count(), 29)
        self.assertEqual(PerfilEPP.objects.count(), 14)
        r = self.client.get(f'/api/sst-epp-entregas/estado/?trabajador={self.t.pk}')
        nombres = {f['nombre']: f['estado'] for f in r.data['filas']}
        # Masa y Volumen: guantes anticorte y botas punta de acero, entre otros; nada entregado aún.
        self.assertEqual(nombres.get('Guantes anticorte'), 'falta')
        self.assertEqual(nombres.get('Botas de seguridad punta de acero'), 'falta')
        self.assertNotIn('Guantes dieléctricos', nombres)
        self.assertEqual(r.data['estado_pin'], 'sin_pin')
        self.assertEqual(self.client.get('/api/sst-epp-matriz/matriz_pdf/').status_code, 200)


class PruebasEntrega(BaseEPP):

    def test_primera_firma_crea_pin_y_luego_lo_exige(self):
        e = self._entrega()
        r = self.client.post(self._url(e, 'firmar'), {'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(r.data.get('requiere_pin_nuevo'))
        r = self.client.post(self._url(e, 'firmar'), {'password': CLAVE, 'pin_nuevo': '4821', 'pin_confirmacion': '4812'},
                             format='json')
        self.assertIn('no coincide', r.data['detail'])
        self.assertEqual(self.client.post(self._url(e, 'firmar'), {'password': 'mala', 'pin_nuevo': '4821',
                                                                    'pin_confirmacion': '4821'}, format='json')
                         .status_code, 400, 'sin la contraseña del responsable no se firma')
        self.assertFalse(PinTrabajador.objects.filter(trabajador=self.t).exists())
        r = self.client.post(self._url(e, 'firmar'), {'password': CLAVE, 'pin_nuevo': '4821', 'pin_confirmacion': '4821'},
                             format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'firmada')
        self.assertEqual(r.data['firma_trabajador']['metodo'], 'pin')
        self.assertNotEqual(PinTrabajador.objects.get(trabajador=self.t).pin, '4821', 'el PIN se guarda cifrado')
        # Firmada no se modifica.
        self.assertEqual(self.client.patch(f'/api/sst-epp-entregas/{e["id"]}/', {'observaciones': 'x'},
                                           format='json').status_code, 400)
        # Segunda entrega: exige el PIN; 5 errores lo bloquean; SIG lo restablece.
        e2 = self._entrega([{'epp': self.botas.pk}])
        for _ in range(5):
            r = self.client.post(self._url(e2, 'firmar'), {'password': CLAVE, 'pin': '0000'}, format='json')
            self.assertEqual(r.status_code, 400)
        self.assertTrue(PinTrabajador.objects.get(trabajador=self.t).bloqueado)
        r = self.client.post(self._url(e2, 'firmar'), {'password': CLAVE, 'pin': '4821'}, format='json')
        self.assertIn('bloqueado', r.data['detail'])
        self.client.post('/api/sst-epp-entregas/restablecer_pin/', {'trabajador': self.t.pk}, format='json')
        r = self.client.post(self._url(e2, 'firmar'), {'password': CLAVE, 'pin_nuevo': '9090', 'pin_confirmacion': '9090'},
                             format='json')
        self.assertEqual(r.data['estado'], 'firmada')

    def test_reposicion_reemplaza_y_renovacion_por_vida_util(self):
        self.guantes.vida_util_meses = 6
        self.guantes.save()
        e = self._entrega()
        self.client.post(self._url(e, 'firmar'), {'password': CLAVE, 'pin_nuevo': '1234', 'pin_confirmacion': '1234'},
                         format='json')
        e = self.client.get(f'/api/sst-epp-entregas/{e["id"]}/').data
        self.assertEqual(e['items'][0]['renovar_el'], sumar_meses(timezone.localdate(), 6).isoformat())
        r2 = self._entrega(tipo='reposicion')
        self.assertIn('motivo', self.client.post(self._url(r2, 'firmar'), {'password': CLAVE, 'pin': '1234'},
                                                 format='json').data['detail'])
        self.client.patch(f'/api/sst-epp-entregas/{r2["id"]}/', {'motivo': 'dano'}, format='json')
        r = self.client.post(self._url(r2, 'firmar'), {'password': CLAVE, 'pin': '1234'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        antes = self.client.get(f'/api/sst-epp-entregas/{e["id"]}/').data['items'][0]
        self.assertFalse(antes['vigente'])
        self.assertEqual(antes['reemplazado_por'], r.data['items'][0]['id'])

    def test_papel_devolucion_y_alerta_de_cesado(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        e = self._entrega([{'epp': self.botas.pk}])
        r = self.client.post(self._url(e, 'firmar_papel'), {'password': CLAVE})
        self.assertIn('Adjunte', r.data['detail'])
        r = self.client.post(self._url(e, 'firmar_papel'), {'password': CLAVE, 'archivo': SimpleUploadedFile(
            'cargo.pdf', b'%PDF-1.4', 'application/pdf')})
        self.assertEqual(r.data['firma_trabajador']['metodo'], 'papel')
        self.t.estado = 'cesado'
        self.t.save()
        res = self.client.get('/api/sst-epp-entregas/resumen/').data
        self.assertTrue(any(x['epp'] == self.botas.nombre for x in res['sin_devolver']))
        it = r.data['items'][0]['id']
        r = self.client.post(self._url(e, 'devolver'), {'items': [{'id': it, 'estado_devolucion': 'reutilizable'}]},
                             format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(self.client.get('/api/sst-epp-entregas/resumen/').data['sin_devolver'])
        self.assertEqual(self.client.get(f'/api/sst-epp-entregas/{e["id"]}/pdf/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/sst-epp-entregas/tarjeta_pdf/?trabajador={self.t.pk}').status_code, 200)

    def test_anular_solo_en_registro(self):
        e = self._entrega()
        self.assertEqual(self.client.post(self._url(e, 'anular'), {}).status_code, 400)
        r = self.client.post(self._url(e, 'anular'), {'motivo': 'Duplicada'}, format='json')
        self.assertEqual(r.data['estado'], 'anulada')
        self.assertEqual(EntregaEPP.objects.get(pk=e['id']).estado, 'anulada')


class PruebasVigilancia(BaseEPP):

    def test_registro_de_aptitud_y_proximo_examen(self):
        r = self.client.post('/api/sst-emo/', {'tipo': 'periodico', 'fecha': '2026-10-01', 'trabajadores': [self.t.pk]},
                             format='json')
        self.assertEqual(r.status_code, 201, r.data)
        ev = r.data
        res = ev['resultados'][0]
        # Personal operativo (laboratorio): próximo examen a los 12 meses.
        self.assertEqual(res['fecha_proximo'], date(2027, 10, 1).isoformat())
        r = self.client.post(f'/api/sst-emo/{ev["id"]}/firmar/', {'password': CLAVE}, format='json')
        self.assertIn('aptitud', r.data['detail'])
        self.assertIn('centro médico', r.data['detail'])
        self.client.post(f'/api/sst-emo/{ev["id"]}/resultado/', {'id': res['id'], 'aptitud': 'apto_restricciones'},
                         format='json')
        self.client.patch(f'/api/sst-emo/{ev["id"]}/', {'centro_medico': 'Clínica Ocupacional SAC'}, format='json')
        r = self.client.post(f'/api/sst-emo/{ev["id"]}/firmar/', {'password': CLAVE}, format='json')
        self.assertIn('restricciones', r.data['detail'])
        self.client.post(f'/api/sst-emo/{ev["id"]}/resultado/', {'id': res['id'], 'restricciones':
                                                                  'Evitar cargas mayores a 15 kg.'}, format='json')
        r = self.client.post(f'/api/sst-emo/{ev["id"]}/firmar/', {'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'registrado')
        self.assertEqual(self.client.post(f'/api/sst-emo/{ev["id"]}/resultado/', {'id': res['id'], 'aptitud': 'apto'},
                                          format='json').status_code, 400)
        v = {x['trabajador']: x for x in self.client.get('/api/sst-emo/vigilancia/').data}
        self.assertEqual(v[self.t.pk]['aptitud'], 'apto_restricciones')
        self.assertEqual(v[self.t.pk]['personal'], 'operativo')
        self.assertEqual(self.client.get(f'/api/sst-emo/{ev["id"]}/pdf/').status_code, 200)
