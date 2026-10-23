"""
M18 Quejas, según el procedimiento de gestión de quejas.

- Código RQ-NNN-AAAA correlativo por año de recepción.
- Validación: relacionada → evaluación; no relacionada → cierre con motivos.
- Decisión (permiso de aprobar) sobre una evaluación registrada: procedente →
  tratamiento; no procedente → cierre con motivos.
- Tratamiento: registrar la NC en Hallazgos (procedencia Queja), sin duplicar.
- Cierre con comunicación al cliente, notificada por alguien no involucrado.
- Etapa cerrada = solo lectura; reabrir con motivo.
- Plazos: acuse 24 h, validación 2 días hábiles, informe 7 días hábiles.
"""
from datetime import date, datetime, timedelta, timezone as tz

from django.utils import timezone

from core.tests.base import CasoBase
from esynapse_sig.models import Hallazgo
from quejas.models import Queja, sumar_dias_habiles


class BaseQuejas(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gerente_sig_q', cargo='Gerente SIG')
        self.dar_permisos(self.sig, 'quejas', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.tecnico = self.crear_usuario('metrologo_q', cargo='Metrólogo')
        self.autenticar(self.sig)

    def _nueva(self, **extra):
        datos = {'empresa': 'Minera Andina S.A.', 'contacto': 'Ing. Rosa Vega', 'contacto_email': 'rvega@andina.pe',
                 'orden_trabajo': 'OT-0450', 'medio_recepcion': 'email', 'origen': 'tecnica',
                 'motivo': 'Errores en los certificados de calibración',
                 'descripcion': 'El certificado indica una serie distinta a la del manómetro.',
                 'recibido_por': self.sig.pk}
        datos.update(extra)
        r = self.client.post('/api/quejas/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return Queja.objects.get(pk=r.data['id'])

    def _post(self, q, accion, datos=None, fmt='json'):
        return self.client.post(f'/api/quejas/{q.pk}/{accion}/', datos or {}, format=fmt)

    def _patch(self, q, datos):
        return self.client.patch(f'/api/quejas/{q.pk}/', datos, format='json')

    def _hasta_decision(self, procedente=True):
        q = self._nueva()
        self.assertEqual(self._post(q, 'validar', {'relacionada': True}).status_code, 200)
        r = self._patch(q, {'responsables': [self.sig.pk], 'involucrados': [self.tecnico.pk],
                            'fecha_evaluacion': '2026-10-20', 'evaluacion': 'Se revisó el registro de ingreso.',
                            'investigacion': 'Error de digitación al transcribir la serie.', 'dentro_alcance': True})
        self.assertEqual(r.status_code, 200, r.data)
        r = self._post(q, 'decidir', {'procedente': procedente, 'fundamento': 'La serie no coincide.'})
        self.assertEqual(r.status_code, 200, r.data)
        return q


class PruebasRegistroYValidacion(BaseQuejas):

    def test_codigo_correlativo_por_anio(self):
        a = self._nueva()
        b = self._nueva()
        anio = timezone.localtime(a.fecha_recepcion).year
        self.assertEqual((a.codigo, b.codigo), (f'RQ-001-{anio}', f'RQ-002-{anio}'))
        c = self._nueva(fecha_recepcion='2025-12-30T10:00:00-05:00')
        self.assertEqual(c.codigo, 'RQ-001-2025')

    def test_motivo_del_origen_y_otro_medio(self):
        r = self.client.post('/api/quejas/', {'empresa': 'X', 'medio_recepcion': 'otros', 'origen': 'logistica',
                                              'motivo': 'Errores de cálculo', 'descripcion': 'd'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('motivo', r.data)
        self.assertIn('medio_otro', r.data)

    def test_no_relacionada_se_cierra_con_motivos(self):
        q = self._nueva()
        self.assertEqual(self._post(q, 'validar', {'relacionada': False}).status_code, 400, 'sin motivo')
        r = self._post(q, 'validar', {'relacionada': False, 'motivo': 'El equipo lo calibró otro laboratorio.'})
        self.assertEqual((r.data['estado'], r.data['resultado']), ('en_cierre', 'no_relacionada'))
        r = self._post(q, 'cerrar', {'comunicacion_cliente': 'Se explicó que el servicio no fue nuestro.',
                                     'medio_cierre': 'email'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'cerrada')
        self.assertEqual(r.data['comunicaciones'][-1]['tipo'], 'no_procede')

    def test_registro_solo_lectura_tras_validar(self):
        q = self._nueva()
        self.assertEqual(self._patch(q, {'empresa': 'Minera Andina SAA'}).status_code, 200)
        self._post(q, 'validar', {'relacionada': True})
        r = self._patch(q, {'empresa': 'Otra'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('Nombre de la empresa', str(r.data))
        r = self._patch(q, {'acciones': 'adelantar'})
        self.assertEqual(r.status_code, 400, 'los datos de etapas futuras no se capturan por adelantado')
        self.assertIn('tratamiento aún no se abre', str(r.data))

    def test_anular_solo_antes_de_validar(self):
        q = self._nueva()
        self.assertEqual(self.client.delete(f'/api/quejas/{q.pk}/').status_code, 204)
        self.assertFalse(Queja.objects.get(pk=q.pk).is_active)
        q2 = self._nueva()
        self._post(q2, 'validar', {'relacionada': True})
        self.assertEqual(self.client.delete(f'/api/quejas/{q2.pk}/').status_code, 400)


class PruebasDecisionYTratamiento(BaseQuejas):

    def test_decidir_exige_evaluacion_y_permiso_de_aprobar(self):
        q = self._nueva()
        self._post(q, 'validar', {'relacionada': True})
        r = self._post(q, 'decidir', {'procedente': True, 'fundamento': 'x'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('responsables', str(r.data))
        editor = self.crear_usuario('asistente_q')
        self.dar_permisos(editor, 'quejas', 'leer', 'editar')
        self.autenticar(editor)
        self.assertEqual(self._post(q, 'decidir', {'procedente': True, 'fundamento': 'x'}).status_code, 403)

    def test_no_procedente_pasa_a_cierre(self):
        q = self._hasta_decision(procedente=False)
        q.refresh_from_db()
        self.assertEqual((q.estado, q.resultado), ('en_cierre', 'no_procedente'))

    def test_registrar_nc_en_hallazgos_sin_duplicar(self):
        q = self._hasta_decision()
        r = self._post(q, 'registrar_nc', {'tipo_nc': 'nc_menor', 'proceso': 'Emisión de certificados',
                                           'requisito': 'NTP-ISO/IEC 17025 7.8.2'})
        self.assertEqual(r.status_code, 200, r.data)
        h = Hallazgo.objects.get(pk=r.data['hallazgo'])
        self.assertEqual((h.fuente, h.tipo), ('queja', 'nc_menor'))
        self.assertIn(q.codigo, h.descripcion)
        self.assertEqual(self._post(q, 'registrar_nc', {'tipo_nc': 'nc_menor', 'proceso': 'x'}).status_code, 400)

    def test_certificado_nuevo_referencia_al_original(self):
        q = self._hasta_decision()
        r = self._patch(q, {'certificado_nuevo': 'MT-0123-2026'})
        self.assertEqual(r.status_code, 400)
        r = self._patch(q, {'certificado_nuevo': 'MT-0123-2026', 'certificado_original': 'MT-0098-2026'})
        self.assertEqual(r.status_code, 200, r.data)

    def test_pasar_a_cierre_exige_acciones_y_seguimiento(self):
        q = self._hasta_decision()
        self.assertEqual(self._post(q, 'pasar_a_cierre').status_code, 400)
        self._patch(q, {'acciones': 'Emitir certificado corregido.', 'responsable_acciones': self.tecnico.pk,
                        'seguimiento': 'Certificado corregido entregado.', 'fecha_seguimiento': '2026-10-21'})
        r = self._post(q, 'pasar_a_cierre')
        self.assertEqual(r.data['estado'], 'en_cierre')


class PruebasCierre(BaseQuejas):

    def _en_cierre(self):
        q = self._hasta_decision()
        self._patch(q, {'acciones': 'Emitir certificado corregido.', 'responsable_acciones': self.tecnico.pk,
                        'seguimiento': 'Entregado.', 'fecha_seguimiento': '2026-10-21'})
        self._post(q, 'pasar_a_cierre')
        return q

    def test_cierre_exige_comunicacion_conformidad_y_no_involucrado(self):
        q = self._en_cierre()
        self.assertEqual(self._post(q, 'cerrar', {'medio_cierre': 'email'}).status_code, 400)
        datos = {'comunicacion_cliente': 'Se entregó el certificado corregido.', 'medio_cierre': 'email'}
        r = self._post(q, 'cerrar', datos)
        self.assertIn('conformidad', str(r.data))
        datos['conformidad_cliente'] = 'conforme'
        r = self._post(q, 'cerrar', {**datos, 'notificado_por': self.tecnico.pk})
        self.assertEqual(r.status_code, 400)
        self.assertIn('involucrado', str(r.data))
        r = self._post(q, 'cerrar', datos)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'cerrada')
        self.assertEqual(r.data['notificado_por'], self.sig.pk)
        self.assertEqual(r.data['comunicaciones'][-1]['tipo'], 'resultado')

    def test_reabrir_con_motivo(self):
        q = self._en_cierre()
        self._post(q, 'cerrar', {'comunicacion_cliente': 'ok', 'medio_cierre': 'email',
                                 'conformidad_cliente': 'no_conforme'})
        self.assertEqual(self._post(q, 'reabrir').status_code, 400)
        r = self._post(q, 'reabrir', {'motivo': 'El cliente no quedó conforme.'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'en_tratamiento')
        self.assertEqual(r.data['reaperturas'][0]['conformidad_cliente'], 'no_conforme')


class PruebasPlazosYComunicaciones(BaseQuejas):

    def test_dias_habiles(self):
        self.assertEqual(sumar_dias_habiles(date(2026, 10, 16), 2), date(2026, 10, 20))   # viernes → martes
        self.assertEqual(sumar_dias_habiles(date(2026, 10, 19), 7), date(2026, 10, 28))

    def test_plazos_de_acuse_y_validacion(self):
        recepcion = datetime(2026, 10, 16, 15, 0, tzinfo=tz.utc)
        q = self._nueva(fecha_recepcion=recepcion.isoformat())
        plazos = {p['clave']: p for p in q.plazos()}
        self.assertEqual(plazos['acuse']['limite'], recepcion + timedelta(hours=24))
        self.assertEqual(plazos['acuse']['estado'], 'vencido')
        self.assertEqual(timezone.localtime(plazos['validacion']['limite']).date(), date(2026, 10, 20))
        r = self._post(q, 'comunicar', {'tipo': 'acuse', 'medio': 'email', 'resumen': 'Se envió el código RQ.',
                                        'fecha': '2026-10-16T18:00:00+00:00'})
        self.assertEqual(r.status_code, 201, r.data)
        plazos = {p['clave']: p for p in r.data['plazos']}
        self.assertEqual(plazos['acuse']['estado'], 'cumplido')

    def test_informe_solo_si_lo_pide_y_tras_validar(self):
        q = self._nueva()
        r = self._post(q, 'comunicar', {'tipo': 'informe', 'medio': 'email', 'resumen': 'x'})
        self.assertEqual(r.status_code, 400)
        self._post(q, 'validar', {'relacionada': True})
        self._patch(q, {'cliente_solicita_informe': True})
        q.refresh_from_db()
        self.assertIn('informe', [p['clave'] for p in q.plazos()])

    def test_ampliacion_exige_motivo_y_fecha(self):
        q = self._nueva()
        self._post(q, 'validar', {'relacionada': True})
        r = self._patch(q, {'plazo_ampliado': True})
        self.assertEqual(r.status_code, 400)
        self.assertIn('motivo_ampliacion', r.data)

    def test_pdfs(self):
        q = self._hasta_decision()
        r = self.client.get(f'/api/quejas/{q.pk}/pdf/')
        self.assertTrue(r.content.startswith(b'%PDF'))
        r = self.client.get('/api/quejas/seguimiento_pdf/?abiertas=1')
        self.assertTrue(r.content.startswith(b'%PDF'))
