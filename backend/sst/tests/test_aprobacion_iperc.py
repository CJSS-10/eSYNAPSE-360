"""
La matriz IPERC la realiza y aprueba el Comité de SST (pie del formato "realizado y aprobado por").

- Cada titular firma en pantalla: con la contraseña de su usuario si lo tiene; si no, con su PIN.
- Se requiere la mitad más uno de los titulares; o el acta firmada en papel adjunta.
- Si una fila del área cambia después de aprobarse, el área queda pendiente de una nueva aprobación.
- La carga inicial retiró las filas que eran el pie de cada hoja (datos del empleador).
"""
from django.core.files.uploadedfile import SimpleUploadedFile

from core.tests.base import CasoBase
from organizacion.models import Area, Puesto, Trabajador
from sst.comite import ComiteSST, MiembroComite
from sst.models import FilaIPERC

CLAVE = CasoBase.CLAVE


class PruebasAprobacionIPERC(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gsig_iperc', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'sst', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.sig)
        area = Area.objects.get(nombre='Laboratorio de Masa y Volumen')
        met = Puesto.objects.get(nombre='Metrólogo')
        self.u1 = self.crear_usuario('presidente_csst', cargo='Metrólogo', sigla_cargo='MET')
        self.t1 = Trabajador.objects.create(nombres='Pedro', apellidos='Con Usuario', documento='43000001', puesto=met,
                                            area=area, usuario=self.u1)
        self.t2 = Trabajador.objects.create(nombres='Lucía', apellidos='Sin Usuario', documento='43000002', puesto=met,
                                            area=area)
        c = ComiteSST.objects.get(periodo='2025-2027')
        self.m1 = MiembroComite.objects.create(comite=c, trabajador=self.t1, representacion='empleador',
                                               condicion='titular', cargo='presidente')
        self.m2 = MiembroComite.objects.create(comite=c, trabajador=self.t2, representacion='trabajadores',
                                               condicion='titular', cargo='secretario')
        self.area = 'SIG'

    def _estado(self, area):
        return next(a for a in self.client.get('/api/sst-iperc/aprobaciones/').data['areas'] if a['area'] == area)

    def test_carga_inicial_aprobada_y_sin_filas_del_pie(self):
        self.assertFalse(FilaIPERC.objects.filter(estado='vigente', actividad__iendswith='RUC:').exists())
        self.assertFalse(FilaIPERC.objects.filter(estado='vigente', actividad='20601338204').exists())
        self.assertEqual(self._estado(self.area)['estado'], 'aprobada')

    def test_cambio_deja_pendiente_y_el_comite_aprueba_con_usuario_y_pin(self):
        f = FilaIPERC.objects.filter(area=self.area, estado='vigente').first()
        self.client.patch(f'/api/sst-iperc/{f.pk}/', {'controles_existentes': 'Pausas activas cada 2 horas'},
                          format='json')
        self.assertEqual(self._estado(self.area)['estado'], 'pendiente')
        d = self.client.get('/api/sst-iperc/aprobaciones/').data
        self.assertEqual({t['id']: t['firma'] for t in d['titulares']}, {self.m1.pk: 'usuario', self.m2.pk: 'sin_pin'})
        url = '/api/sst-iperc/aprobar_comite/'
        r = self.client.post(url, {'areas': [self.area], 'firmas': [{'miembro': self.m1.pk, 'clave': CLAVE}]},
                             format='json')
        self.assertIn('al menos 2', r.data['detail'])
        firmas = [{'miembro': self.m1.pk, 'clave': 'otra'}, {'miembro': self.m2.pk, 'pin_nuevo': '1357',
                                                              'pin_confirmacion': '1357'}]
        r = self.client.post(url, {'areas': [self.area], 'firmas': firmas}, format='json')
        self.assertIn('Contraseña incorrecta de Pedro', r.data['detail'])
        r = self.client.post(url, {'areas': [self.area], 'firmas': firmas[::-1]}, format='json')
        self.assertIn('Contraseña incorrecta de Pedro', r.data['detail'])
        d = self.client.get('/api/sst-iperc/aprobaciones/').data
        self.assertEqual({t['id']: t['firma'] for t in d['titulares']}[self.m2.pk], 'sin_pin',
                         'si una firma falla, no se guarda el PIN nuevo de los demás')
        firmas[0]['clave'] = CLAVE
        r = self.client.post(url, {'areas': [self.area], 'firmas': firmas}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self._estado(self.area)['estado'], 'aprobada')
        d = self.client.get('/api/sst-iperc/aprobaciones/').data
        self.assertEqual([x['metodo'] for x in d['historial'][0]['firmas']], ['usuario', 'pin'])
        self.assertEqual(self.client.get(f'/api/sst-iperc/matriz_pdf/?area={self.area}').status_code, 200)
        # La segunda vez la titular sin usuario firma con su PIN ya creado.
        firmas = [{'miembro': self.m1.pk, 'clave': CLAVE}, {'miembro': self.m2.pk, 'pin': '0000'}]
        self.assertIn('PIN incorrecto', self.client.post(url, {'areas': [self.area], 'firmas': firmas},
                                                         format='json').data['detail'])

    def test_aprobacion_con_acta_en_papel(self):
        r = self.client.post('/api/sst-iperc/aprobar_comite/', {
            'areas': '["SIG", "Comedor"]', 'firmantes': f'[{self.m1.pk}, {self.m2.pk}]', 'password': CLAVE,
            'archivo': SimpleUploadedFile('acta.pdf', b'%PDF-1.4', 'application/pdf')})
        self.assertEqual(r.status_code, 201, r.data)
        h = self.client.get('/api/sst-iperc/aprobaciones/').data['historial'][0]
        self.assertEqual(h['areas'], ['SIG', 'Comedor'])
        self.assertTrue(h['archivo_url'])

    def test_firma_del_trabajador_con_usuario_usa_su_contrasena(self):
        ev = self.client.post('/api/sst-emo/', {'tipo': 'periodico', 'fecha': '2026-10-01', 'trabajadores': [self.t1.pk],
                                                'centro_medico': 'Clínica'}, format='json').data
        res = ev['resultados'][0]
        self.assertEqual(res['estado_pin'], 'usuario')
        self.client.post(f'/api/sst-emo/{ev["id"]}/resultado/', {'id': res['id'], 'aptitud': 'apto'}, format='json')
        self.client.post(f'/api/sst-emo/{ev["id"]}/firmar/', {'password': CLAVE}, format='json')
        url = f'/api/sst-emo/{ev["id"]}/entregar_resultados/'
        r = self.client.post(url, {'id': res['id'], 'password': CLAVE, 'pin_nuevo': '2468', 'pin_confirmacion': '2468'},
                             format='json')
        self.assertIn('contraseña de su usuario', r.data['detail'])
        r = self.client.post(url, {'id': res['id'], 'password': CLAVE, 'clave_trabajador': CLAVE}, format='json')
        self.assertEqual(r.data['resultados'][0]['entrega_resultados']['metodo'], 'usuario')
