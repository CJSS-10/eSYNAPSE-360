"""
Comité de SST, Programa anual SSOMA y cargo de entrega de resultados médicos.

- Comité: un solo presidente y un solo secretario (titulares); alerta de paridad y de T-Registro.
- Reunión: no se cierra sin agenda, quórum (mitad más uno de los titulares) ni acta firmada; cerrada no cambia;
  los acuerdos se siguen después.
- Programa: aprobado no cambia lo programado; la ejecución exige evidencia y no admite meses futuros; reprogramar
  abre una nueva versión.
- Cargo de resultados: solo después de registrar la evaluación; firma con PIN; una sola vez.
- Anexo 4: pendiente del año anterior hasta registrarlo.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from core.tests.base import CasoBase
from organizacion.models import Area, Puesto, Trabajador
from sst.comite import ComiteSST, ProgramaSSOMA

CLAVE = CasoBase.CLAVE


def _pdf(nombre='acta.pdf'):
    return SimpleUploadedFile(nombre, b'%PDF-1.4', 'application/pdf')


class BaseComite(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gsig_csst', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'sst', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.sig)
        area = Area.objects.get(nombre='Laboratorio de Masa y Volumen')
        met = Puesto.objects.get(nombre='Metrólogo')
        self.t = [Trabajador.objects.create(nombres=f'T{i}', apellidos='Comité', documento=f'4200000{i}', puesto=met,
                                            area=area) for i in range(4)]
        self.c = ComiteSST.objects.get(periodo='2025-2027')

    def _miembro(self, t, rep, cargo='miembro', cond='titular'):
        return self.client.post(f'/api/sst-comite/{self.c.pk}/miembro/', {'trabajador': t.pk, 'representacion': rep,
                                                                          'cargo': cargo, 'condicion': cond},
                                format='json')


class PruebasComite(BaseComite):

    def test_cargos_unicos_y_alertas(self):
        self.assertEqual(self._miembro(self.t[0], 'empleador', 'presidente').status_code, 200)
        r = self._miembro(self.t[1], 'trabajadores', 'presidente')
        self.assertIn('ya tiene presidente', r.data['detail'])
        r = self._miembro(self.t[1], 'trabajadores', 'secretario', 'suplente')
        self.assertIn('titulares', r.data['detail'])
        r = self._miembro(self.t[1], 'trabajadores', 'secretario')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._miembro(self.t[1], 'empleador').status_code, 400, 'no se repite el trabajador')
        r = self._miembro(self.t[2], 'empleador')
        alertas = ' '.join(r.data['alertas'])
        self.assertIn('no paritario', alertas)
        self.assertIn('T-Registro', alertas)

    def test_reunion_quorum_acta_y_acuerdos(self):
        for t, rep, cargo in ((self.t[0], 'empleador', 'presidente'), (self.t[1], 'trabajadores', 'secretario'),
                              (self.t[2], 'empleador', 'miembro'), (self.t[3], 'trabajadores', 'miembro')):
            self._miembro(t, rep, cargo)
        miembros = {m['trabajador']: m['id'] for m in self.client.get(f'/api/sst-comite/{self.c.pk}/').data['miembros']}
        r = self.client.post('/api/sst-comite-reuniones/', {'comite': self.c.pk, 'tipo': 'ordinaria',
                                                             'fecha': str(timezone.localdate()), 'lugar': 'Sala',
                                                             'agenda': ['Revisión de incidentes'],
                                                             'asistentes': [miembros[self.t[0].pk],
                                                                            miembros[self.t[1].pk]]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        rid = r.data['id']
        self.assertRegex(r.data['codigo'], r'^\d{3}-\d{4}-CSST$')
        self.client.post(f'/api/sst-comite-reuniones/{rid}/acuerdo/', {'descripcion': 'Comprar camilla',
                                                                        'responsable': self.t[0].pk,
                                                                        'plazo': '2026-01-01'}, format='json')
        self.assertEqual(self.client.get(f'/api/sst-comite-reuniones/{rid}/pdf/').status_code, 200)
        r = self.client.post(f'/api/sst-comite-reuniones/{rid}/cerrar/', {'acta': _pdf()})
        self.assertIn('quórum', r.data['detail'], 'con 2 de 4 titulares no hay quórum (se requieren 3)')
        self.client.patch(f'/api/sst-comite-reuniones/{rid}/', {'asistentes': list(miembros.values())}, format='json')
        r = self.client.post(f'/api/sst-comite-reuniones/{rid}/cerrar/', {})
        self.assertIn('acta firmada', r.data['detail'])
        r = self.client.post(f'/api/sst-comite-reuniones/{rid}/cerrar/', {'acta': _pdf()})
        self.assertEqual(r.data['estado'], 'realizada')
        self.assertEqual(self.client.patch(f'/api/sst-comite-reuniones/{rid}/', {'desarrollo': 'x'},
                                           format='json').status_code, 400)
        ac = self.client.get(f'/api/sst-comite-acuerdos/?comite={self.c.pk}').data[0]
        self.assertTrue(ac['vencido'])
        self.assertEqual(self.client.post(f'/api/sst-comite-acuerdos/{ac["id"]}/seguimiento/', {'estado': 'cumplido'},
                                          format='json').status_code, 400)
        r = self.client.post(f'/api/sst-comite-acuerdos/{ac["id"]}/seguimiento/',
                             {'estado': 'cumplido', 'comentario': 'Camilla comprada (OC 123)'}, format='json')
        self.assertEqual(r.data['estado'], 'cumplido')
        self.assertFalse(r.data['vencido'])


class PruebasPrograma(BaseComite):

    def test_programa_cargado_aprobado_ejecucion_y_reprogramacion(self):
        p = ProgramaSSOMA.objects.get(anio=2026)
        self.assertEqual(p.estado, 'aprobado')
        self.assertEqual(p.actividades.count(), 9)
        r = self.client.get('/api/sst-programa-ssoma/anio/?anio=2026')
        act = next(a for a in r.data['actividades'] if a['descripcion'].startswith('Identificación'))
        self.assertEqual(self.client.post(f'/api/sst-programa-ssoma/{p.pk}/actividad/', {'id': act['id'], 'meses': [1]},
                                          format='json').status_code, 400, 'aprobado no se reprograma sin versión')
        insp = next(a for a in r.data['actividades'] if 'inspecciones' in a['descripcion'])
        r = self.client.post(f'/api/sst-programa-ssoma/{p.pk}/ejecutar/', {'actividad': insp['id'], 'mes': 2,
                                                                          'ejecutado': True}, format='json')
        self.assertIn('evidencia', r.data['detail'])
        r = self.client.post(f'/api/sst-programa-ssoma/{p.pk}/ejecutar/', {'actividad': insp['id'], 'mes': 2,
                                                                          'ejecutado': True,
                                                                          'evidencia': 'INS-001-2026'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        if timezone.localdate().year == 2026 and timezone.localdate().month < 12:
            r = self.client.post(f'/api/sst-programa-ssoma/{p.pk}/ejecutar/', {'actividad': insp['id'], 'mes': 12,
                                                                              'ejecutado': True, 'evidencia': 'x'},
                                 format='json')
            self.assertIn('futuro', r.data['detail'])
        r = self.client.post(f'/api/sst-programa-ssoma/{p.pk}/reprogramar/', {'motivo': 'Cambio de fecha del monitoreo'},
                             format='json')
        self.assertEqual((r.data['estado'], r.data['version']), ('reprogramacion', 2))
        r = self.client.post(f'/api/sst-programa-ssoma/{p.pk}/actividad/', {'id': act['id'], 'meses': [12]},
                             format='json')
        self.assertEqual(r.status_code, 200)
        r = self.client.post(f'/api/sst-programa-ssoma/{p.pk}/aprobar/', {'password': CLAVE}, format='json')
        self.assertEqual(r.data['estado'], 'aprobado')
        self.assertEqual(len(r.data['aprobado']), 5)
        self.assertEqual(self.client.get(f'/api/sst-programa-ssoma/{p.pk}/pdf/').status_code, 200)


class PruebasCargoEMO(BaseComite):

    def test_cargo_de_resultados_con_pin_y_anexo4(self):
        ev = self.client.post('/api/sst-emo/', {'tipo': 'periodico', 'fecha': '2026-10-01', 'trabajadores': [self.t[0].pk],
                                                'centro_medico': 'Clínica'}, format='json').data
        res = ev['resultados'][0]
        r = self.client.post(f'/api/sst-emo/{ev["id"]}/entregar_resultados/', {'id': res['id'], 'password': CLAVE,
                                                                               'pin_nuevo': '2468',
                                                                               'pin_confirmacion': '2468'}, format='json')
        self.assertIn('después de registrar', r.data['detail'])
        self.client.post(f'/api/sst-emo/{ev["id"]}/resultado/', {'id': res['id'], 'aptitud': 'apto'}, format='json')
        self.client.post(f'/api/sst-emo/{ev["id"]}/firmar/', {'password': CLAVE}, format='json')
        r = self.client.post(f'/api/sst-emo/{ev["id"]}/entregar_resultados/', {'id': res['id'], 'password': CLAVE,
                                                                               'pin_nuevo': '2468',
                                                                               'pin_confirmacion': '2468'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['resultados'][0]['entrega_resultados']['metodo'], 'pin')
        r = self.client.post(f'/api/sst-emo/{ev["id"]}/entregar_resultados/', {'id': res['id'], 'password': CLAVE,
                                                                               'pin': '2468'}, format='json')
        self.assertIn('ya se entregaron', r.data['detail'])
        a = self.client.get('/api/sst-emo/anexo4/').data
        self.assertEqual(a['pendiente']['anio'], timezone.localdate().year - 1)
        r = self.client.post('/api/sst-emo/registrar_anexo4/', {'anio': a['pendiente']['anio'],
                                                                 'fecha_presentacion': '2026-03-20',
                                                                 'archivo': _pdf('anexo4.pdf')})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIsNone(r.data['pendiente'])
        datos = {'anio': a['pendiente']['anio'], 'fecha_presentacion': '2026-03-25', 'archivo': _pdf('otro.pdf')}
        self.assertIn('ya está registrado', self.client.post('/api/sst-emo/registrar_anexo4/', datos).data['detail'])
        datos.update(reemplazar='1', archivo=_pdf('otro.pdf'))
        self.assertIn('motivo', self.client.post('/api/sst-emo/registrar_anexo4/', datos).data['detail'])
        datos.update(motivo='Se adjuntó el cargo equivocado', archivo=_pdf('otro.pdf'))
        r = self.client.post('/api/sst-emo/registrar_anexo4/', datos)
        self.assertEqual(r.data['informes'][0]['fecha_presentacion'], '2026-03-25')
        self.assertIn('equivocado', r.data['informes'][0]['observaciones'])
