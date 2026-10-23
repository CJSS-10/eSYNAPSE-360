"""
Incidentes, accidentes, enfermedades ocupacionales y estadísticas de SST.

- Flujo: reportado → en investigación → en revisión → en acciones → cerrado; cada etapa cerrada es de solo lectura.
- Reporte después de 24 horas queda marcado; accidente mortal o incidente peligroso exige notificar al Ministerio.
- Concluir exige gravedad, porqués, causas y conclusiones, con firma; revisar (aprobar) registra hallazgo y SAC.
- El evento cierra solo con la solicitud de acción correctiva cerrada.
- Estadísticas: índices de la R.M. 050-2013-TR con horas-hombre propuestas y editables.
"""
from datetime import timedelta

from django.utils import timezone

from core.tests.base import CasoBase
from esynapse_sig.models import SolicitudAC
from organizacion.models import Area, Puesto, Trabajador
from sst.eventos import DatosMesSST, EnfermedadOcupacional, Evento


class BaseEventos(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gsig_ev', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'sst', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.sig)
        self.lab = Area.objects.get(nombre='Laboratorio de Masa y Volumen')
        self.t = Trabajador.objects.create(nombres='Rosa', apellidos='Lima', documento='40000001',
                                           puesto=Puesto.objects.get(nombre='Metrólogo'), area=self.lab)

    def _evento(self, tipo='accidente', horas=2, **extra):
        datos = {'tipo': tipo, 'fecha_hora': (timezone.now() - timedelta(hours=horas)).isoformat(),
                 'lugar': 'Laboratorio de Masa y Volumen, piso 3', 'unidad': self.lab.pk,
                 'descripcion': 'Al trasladar una pesa de 20 kg se golpeó el pie.'}
        datos.update(extra)
        r = self.client.post('/api/sst-eventos/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return Evento.objects.get(pk=r.data['id'])

    def _url(self, e, accion=''):
        return f'/api/sst-eventos/{e.pk}/' + (f'{accion}/' if accion else '')

    def _investigar(self, e, **extra):
        self.client.post(self._url(e, 'afectado'), {'trabajador': self.t.pk, 'edad': 34, 'sexo': 'F',
                                                    'partes_cuerpo': ['Pie'], 'tipos_lesion': ['Contusión'],
                                                    'dias_descanso': 3}, format='json')
        r = self.client.post(self._url(e, 'iniciar_investigacion'),
                             {'equipo_investigador': [{'nombre': 'Miembro del Comité SST'}]}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        datos = {'gravedad': 'incapacitante', 'grado_incapacidad': 'total_temporal',
                 'tipos_accidente': ['Golpeado por'], 'que_sucedio': 'La pesa cayó sobre el pie.',
                 'porques': ['Se trasladó a mano', 'No había carretilla disponible'],
                 'causas_inmediatas': 'Levantamiento inadecuado', 'causas_basicas': 'Falta de carretilla',
                 'conclusiones': 'Dotar carretilla y capacitar.', 'actos_subestandar': ['Levantamiento inadecuado']}
        datos.update(extra)
        r = self.client.patch(self._url(e), datos, format='json')
        self.assertEqual(r.status_code, 200, r.data)


class PruebasFlujo(BaseEventos):

    def test_codigo_reporte_y_afectado_desde_trabajador(self):
        e = self._evento()
        self.assertRegex(e.codigo, r'^AT-\d{3}-\d{4}$')
        self.assertFalse(e.reporte_tardio)
        r = self.client.post(self._url(e, 'afectado'), {'trabajador': self.t.pk, 'edad': 34}, format='json')
        a = r.data['afectados'][0]
        self.assertEqual((a['nombre'], a['documento'], a['puesto'], a['area']),
                         ('Rosa Lima', '40000001', 'Metrólogo', 'Laboratorio de Masa y Volumen'))
        self.assertEqual(self.client.post(self._url(e, 'afectado'), {'trabajador': self.t.pk}, format='json')
                         .status_code, 400)
        tardio = self._evento(tipo='incidente', horas=30)
        self.assertTrue(tardio.reporte_tardio)
        self.assertRegex(tardio.codigo, r'^IN-')

    def test_flujo_completo_con_sac(self):
        e = self._evento()
        self.assertEqual(self.client.post(self._url(e, 'iniciar_investigacion'), {}, format='json').status_code, 400)
        self._investigar(e)
        # El reporte quedó cerrado.
        r = self.client.patch(self._url(e), {'lugar': 'Otro'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('el reporte', r.data['detail'])
        self.assertEqual(self.client.post(self._url(e, 'concluir'), {'password': 'mala'}, format='json').status_code,
                         400)
        r = self.client.post(self._url(e, 'concluir'), {'password': self.CLAVE}, format='json')
        self.assertEqual(r.data['estado'], 'en_revision', r.data)
        self.assertEqual(self.client.patch(self._url(e), {'conclusiones': 'x'}, format='json').status_code, 400)
        r = self.client.post(self._url(e, 'devolver'), {'motivo': 'Completar porqués'}, format='json')
        self.assertEqual(r.data['estado'], 'en_investigacion')
        self.client.post(self._url(e, 'concluir'), {'password': self.CLAVE}, format='json')
        r = self.client.post(self._url(e, 'aprobar_informe'), {'password': self.CLAVE}, format='json')
        self.assertEqual(r.data['estado'], 'en_acciones', r.data)
        self.assertTrue(r.data['acciones']['sac'])
        e.refresh_from_db()
        self.assertEqual((e.hallazgo.tipo, e.hallazgo.fuente), ('nc_mayor', 'accidente'))
        # Descanso médico prolongado: se actualiza con historial.
        aid = r.data['afectados'][0]['id']
        r = self.client.post(self._url(e, 'actualizar_descanso'), {'id': aid, 'dias_descanso': 7}, format='json')
        self.assertEqual(r.data['dias_perdidos'], 7)
        # No cierra sin la SAC cerrada.
        r = self.client.post(self._url(e, 'cerrar'), {'password': self.CLAVE}, format='json')
        self.assertEqual(r.status_code, 400)
        SolicitudAC.objects.filter(pk=e.hallazgo.sac_id).update(estado='cerrada_conforme')
        r = self.client.post(self._url(e, 'cerrar'), {'password': self.CLAVE}, format='json')
        self.assertEqual(r.data['estado'], 'cerrado', r.data)
        for pdf in ('registro_pdf', 'informe_pdf'):
            rr = self.client.get(self._url(e, pdf))
            self.assertEqual(rr.status_code, 200, pdf)
            self.assertTrue(rr.content.startswith(b'%PDF'))

    def test_concluir_exige_analisis(self):
        e = self._evento()
        self._investigar(e, causas_basicas='', porques=[])
        r = self.client.post(self._url(e, 'concluir'), {'password': self.CLAVE}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('causas básicas', r.data['detail'])
        self.assertIn('porqués', r.data['detail'])

    def test_mortal_exige_notificacion_y_iperc(self):
        e = self._evento()
        self._investigar(e, gravedad='mortal', grado_incapacidad='', requiere_actualizar_iperc=True)
        self.client.post(self._url(e, 'concluir'), {'password': self.CLAVE}, format='json')
        self.client.post(self._url(e, 'aprobar_informe'), {'password': self.CLAVE}, format='json')
        e.refresh_from_db()
        SolicitudAC.objects.filter(pk=e.hallazgo.sac_id).update(estado='cerrada_conforme')
        r = self.client.post(self._url(e, 'cerrar'), {'password': self.CLAVE}, format='json')
        self.assertIn('Ministerio', r.data['detail'])
        self.client.post(self._url(e, 'notificar_mtpe'), {'fecha': str(timezone.localdate())}, format='multipart')
        r = self.client.post(self._url(e, 'cerrar'), {'password': self.CLAVE}, format='json')
        self.assertIn('IPERC', r.data['detail'])
        r = self.client.post(self._url(e, 'cerrar'), {'password': self.CLAVE, 'iperc_actualizado': True},
                             format='json')
        self.assertEqual(r.data['estado'], 'cerrado')

    def test_incidente_peligroso_registro_y_anulacion(self):
        e = self._evento(tipo='incidente_peligroso', potencialmente_afectados=4)
        self.assertTrue(self.client.get(self._url(e)).data['pendiente_mtpe'])
        self.assertTrue(self.client.get(self._url(e, 'registro_pdf')).content.startswith(b'%PDF'))
        self.assertEqual(self.client.delete(self._url(e)).status_code, 400)
        self.assertEqual(self.client.post(self._url(e, 'anular'), {}, format='json').status_code, 400)
        r = self.client.post(self._url(e, 'anular'), {'motivo': 'Registrado dos veces'}, format='json')
        self.assertEqual(r.data['estado'], 'anulado')

    def test_fecha_futura_y_opciones(self):
        r = self.client.post('/api/sst-eventos/', {'tipo': 'incidente', 'lugar': 'x', 'descripcion': 'x',
                                                   'fecha_hora': (timezone.now() + timedelta(days=1)).isoformat()},
                             format='json')
        self.assertEqual(r.status_code, 400)
        e = self._evento()
        self._investigar(e)
        r = self.client.patch(self._url(e), {'tipos_accidente': ['Inventado']}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.patch(self._url(e), {'tipos_accidente': ['Otro: caída de pesa']}, format='json')
        self.assertEqual(r.status_code, 200)


class PruebasEnfermedadesYEstadisticas(BaseEventos):

    def test_enfermedad_registro_y_acciones(self):
        r = self.client.post('/api/sst-enfermedades/', {'nombre': 'Hipoacusia inducida por ruido',
                                                        'unidad': self.lab.pk, 'agente': 'fisico',
                                                        'causas': 'Exposición a ruido de compresores',
                                                        'trabajadores_expuestos': 5}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        o = EnfermedadOcupacional.objects.get(pk=r.data['id'])
        self.assertRegex(o.codigo, r'^EO-')
        r = self.client.post(f'/api/sst-enfermedades/{o.pk}/registrar_acciones/', {'password': self.CLAVE},
                             format='json')
        self.assertEqual(r.data['estado'], 'en_acciones')
        self.assertEqual(self.client.patch(f'/api/sst-enfermedades/{o.pk}/', {'nombre': 'x'}, format='json')
                         .status_code, 400)
        self.assertTrue(self.client.get(f'/api/sst-enfermedades/{o.pk}/pdf/').content.startswith(b'%PDF'))

    def test_indices_rm_050(self):
        e = self._evento()
        self._investigar(e)
        mes, anio = timezone.localdate().month, timezone.localdate().year
        r = self.client.post('/api/sst-estadisticas/datos_mes/', {'anio': anio, 'mes': mes, 'trabajadores': 35,
                                                                  'horas_hombre': 6000}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(DatosMesSST.objects.get(anio=anio, mes=mes).propuesto)
        m = self.client.get(f'/api/sst-estadisticas/anio/?anio={anio}').data['meses'][mes - 1]
        self.assertEqual((m['incapacitantes'], m['dias_perdidos'], m['horas_hombre']), (1, 3, 6000))
        self.assertEqual(m['indice_frecuencia'], round(1 * 1_000_000 / 6000, 2))
        self.assertEqual(m['indice_gravedad'], 500.0)
        self.assertEqual(m['indice_accidentabilidad'], round(m['indice_frecuencia'] * 500.0 / 1000, 2))
        self.assertEqual(m['areas_incapacitantes'], ['Laboratorio de Masa y Volumen'])

    def test_horas_hombre_propuestas_y_pdfs(self):
        anio = timezone.localdate().year
        m = self.client.get(f'/api/sst-estadisticas/anio/?anio={anio}').data['meses'][0]
        self.assertTrue(m['propuesto'])
        self.assertEqual(m['horas_hombre'], m['trabajadores'] * 22 * 8)
        r = self.client.post('/api/sst-estadisticas/informe/', {'anio': anio, 'periodo': 'Enero–Octubre',
                                                                'resultados': 'Sin accidentes mortales.'},
                             format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post('/api/sst-estadisticas/informe/', {'anio': anio, 'periodo': 'Enero–Octubre',
                                                                'resultados': 'Sin accidentes mortales.',
                                                                'password': self.CLAVE}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        for url in (f'/api/sst-estadisticas/registro_pdf/?anio={anio}', f'/api/sst-estadisticas/datos_pdf/?anio={anio}'):
            rr = self.client.get(url)
            self.assertEqual(rr.status_code, 200, url)
            self.assertTrue(rr.content.startswith(b'%PDF'))
