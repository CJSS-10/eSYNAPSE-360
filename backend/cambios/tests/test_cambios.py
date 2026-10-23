"""
M17 Cambios, según el procedimiento de control de cambios.

- Código SC-NNN-AAAA; proceso solicitante del catálogo.
- Solicitud → evaluación → aprobación del Gerente General (firma) → planificación
  → implementación → verificación de la eficacia → cierre.
- Cambio mayor o técnico: planificación obligatoria; temporal: fecha de reversión.
- Si afecta clientes o actividades acreditadas: comunicación antes de implementar.
- Al aprobar, los procesos afectados reciben el aviso «ficha por revisar».
- Etapa cerrada = solo lectura; rechazo → reevaluar o archivar; reabrir con motivo.
- Temporal eficaz: queda en vigor hasta registrar su fin; prórroga firmada por el Gerente General.
"""
from datetime import timedelta

from django.utils import timezone

from cambios.models import Cambio
from core.tests.base import CasoBase
from procesos.models import Aviso, Proceso


class BaseCambios(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gerente_sig_c', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'cambios', 'leer', 'crear', 'editar', 'eliminar')
        self.gg = self.crear_usuario('gerente_general_c', cargo='Gerente General', sigla_cargo='GG')
        self.dar_permisos(self.gg, 'cambios', 'leer', 'crear', 'editar', 'aprobar')
        self.met = Proceso.objects.get(nombre='Metrología')
        self.com = Proceso.objects.get(nombre='Comercial')
        self.autenticar(self.sig)

    def _post(self, c, accion, datos=None, fmt='json', usuario=None):
        if usuario:
            self.autenticar(usuario)
        return self.client.post(f'/api/cambios/{c.pk}/{accion}/', datos or {}, format=fmt)

    def _patch(self, c, datos):
        return self.client.patch(f'/api/cambios/{c.pk}/', datos, format='json')

    def _nuevo(self, **extra):
        datos = {'proceso_solicitante': self.met.pk, 'prioridad': 'alta', 'origen': 'interno',
                 'motivo_origen': 'Incorporación de equipos',
                 'descripcion': 'Reemplazo del patrón de presión por uno de mayor exactitud.',
                 'justificacion': 'Reducir la incertidumbre del servicio de manómetros.'}
        datos.update(extra)
        r = self.client.post('/api/cambios/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return Cambio.objects.get(pk=r.data['id'])

    def _evaluado(self, clasificacion='menor', es_tecnico=False, afecta_clientes=False):
        c = self._nuevo()
        self.assertEqual(self._post(c, 'enviar_evaluacion').status_code, 200)
        r = self._patch(c, {'factibilidad_tecnica': 'Factible.', 'aspectos_operativos': 'Sin parada del servicio.',
                            'aspectos_financieros': 'S/ 12,000.', 'procesos_afectados': [self.met.pk, self.com.pk],
                            'beneficios': 'Menor incertidumbre.', 'riesgos': 'Trazabilidad del nuevo patrón.',
                            'controles': 'Calibración en INACAL antes del uso.', 'consecuencias': 'Pérdida de clientes.',
                            'impactos': ['calidad', 'tecnico'], 'clasificacion': clasificacion, 'es_tecnico': es_tecnico,
                            'afecta_clientes': afecta_clientes, 'responsable_evaluador': self.sig.pk})
        self.assertEqual(r.status_code, 200, r.data)
        r = self._post(c, 'agregar_actividad', {'actividad': 'Comprar y calibrar el patrón', 'responsable': self.sig.pk,
                                                'recursos': 'Presupuesto 2026',
                                                'plazo': str(timezone.localdate() + timedelta(days=30))})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self._post(c, 'enviar_aprobacion').status_code, 200)
        return c

    def _aprobado(self, **kw):
        c = self._evaluado(**kw)
        r = self._post(c, 'resolver', {'aprobado': True, 'password': self.CLAVE}, usuario=self.gg)
        self.assertEqual(r.status_code, 200, r.data)
        self.autenticar(self.sig)
        c.refresh_from_db()
        return c

    def _planificar(self, c):
        r = self._patch(c, {'responsable_implementacion': self.sig.pk,
                            'plazo_implementacion': str(timezone.localdate() + timedelta(days=45)),
                            'prevision': 'previsto', 'temporalidad': 'permanente', 'fuentes': ['tecnologia']})
        self.assertEqual(r.status_code, 200, r.data)

    def _comunicar(self, c, destinatario='personal'):
        r = self._post(c, 'comunicar', {'destinatario': destinatario, 'medio': 'email',
                                        'resumen': 'Se informa el reemplazo del patrón y su fecha.'}, fmt='multipart')
        self.assertEqual(r.status_code, 201, r.data)

    def _implementado(self, **kw):
        c = self._aprobado(**kw)
        self._planificar(c)
        if c.afecta_clientes:
            self._comunicar(c, 'clientes')
        r = self._post(c, 'iniciar_implementacion')
        self.assertEqual(r.status_code, 200, r.data)
        a = c.actividades.first()
        r = self._post(c, 'completar_actividad', {'actividad_id': a.pk, 'seguimiento': 'Patrón calibrado en INACAL.'},
                       fmt='multipart')
        self.assertEqual(r.status_code, 200, r.data)
        return c


class PruebasSolicitudYEvaluacion(BaseCambios):

    def test_codigo_y_solicitante(self):
        c = self._nuevo()
        self.assertTrue(c.codigo.startswith('SC-001-'))
        self.assertEqual(c.solicitante, self.sig)
        self.assertEqual(self._nuevo().codigo[:6], 'SC-002')

    def test_motivo_de_otro_origen_rechazado(self):
        r = self.client.post('/api/cambios/', {'origen': 'externo', 'motivo_origen': 'Incorporación de equipos',
                                               'descripcion': 'x'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_enviar_evaluacion_exige_datos(self):
        c = self._nuevo(justificacion='')
        r = self._post(c, 'enviar_evaluacion')
        self.assertEqual(r.status_code, 400)
        self.assertIn('justificación', r.data['detail'])

    def test_enviar_aprobacion_exige_evaluacion_completa(self):
        c = self._nuevo()
        self._post(c, 'enviar_evaluacion')
        r = self._post(c, 'enviar_aprobacion')
        self.assertEqual(r.status_code, 400)
        self.assertIn('procesos afectados', r.data['detail'])

    def test_etapa_cerrada_solo_lectura(self):
        c = self._nuevo()
        self._post(c, 'enviar_evaluacion')
        r = self._patch(c, {'descripcion': 'Otra'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('solicitud está cerrada', r.data['detail'])
        # Una etapa futura no se captura por adelantado, y el mensaje lo dice así.
        r = self._patch(c, {'prevision': 'previsto'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('planificación aún no se abre', r.data['detail'])


class PruebasResolucion(BaseCambios):

    def test_solo_quien_aprueba_resuelve_con_contrasena(self):
        c = self._evaluado()
        self.assertEqual(self._post(c, 'resolver', {'aprobado': True, 'password': self.CLAVE}).status_code, 403)
        self.autenticar(self.gg)
        self.assertEqual(self._post(c, 'resolver', {'aprobado': True}).status_code, 400)
        self.assertEqual(self._post(c, 'resolver', {'aprobado': True, 'password': 'mala'}).status_code, 400)
        r = self._post(c, 'resolver', {'aprobado': True, 'password': self.CLAVE})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['estado'], 'en_planificacion')
        self.assertEqual(r.data['resuelto_por_nombre'], self.gg.get_full_name())

    def test_aprobar_avisa_a_los_procesos_afectados(self):
        c = self._aprobado()
        avisos = Aviso.objects.filter(origen='cambio', atendido=False)
        self.assertEqual(set(avisos.values_list('proceso__nombre', flat=True)), {'Metrología', 'Comercial'})
        self.assertIn(c.codigo, avisos.first().motivo)

    def test_rechazo_exige_motivo_y_luego_reevaluar_o_archivar(self):
        c = self._evaluado()
        self.autenticar(self.gg)
        self.assertEqual(self._post(c, 'resolver', {'aprobado': False, 'password': self.CLAVE}).status_code, 400)
        r = self._post(c, 'resolver', {'aprobado': False, 'comentarios': 'Falta el costo.', 'password': self.CLAVE})
        self.assertEqual(r.data['estado'], 'rechazado')
        self.autenticar(self.sig)
        r = self._post(c, 'reevaluar', {'motivo': 'Se agrega la cotización.'})
        self.assertEqual(r.data['estado'], 'en_evaluacion')
        self.assertEqual(len(r.data['historial']), 2)
        c2 = self._evaluado()
        self._post(c2, 'resolver', {'aprobado': False, 'comentarios': 'No procede.', 'password': self.CLAVE},
                   usuario=self.gg)
        self.autenticar(self.sig)
        self.assertEqual(self._post(c2, 'archivar', {'motivo': 'Se descarta.'}).data['estado'], 'archivado')


class PruebasPlanificacionEImplementacion(BaseCambios):

    def test_cambio_menor_basta_el_plan(self):
        c = self._aprobado(clasificacion='menor')
        r = self._patch(c, {'responsable_implementacion': self.sig.pk,
                            'plazo_implementacion': str(timezone.localdate() + timedelta(days=10))})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._post(c, 'iniciar_implementacion').status_code, 200)

    def test_cambio_menor_sin_planificacion_toma_responsable_y_plazo_del_plan(self):
        c = self._aprobado()
        r = self._post(c, 'iniciar_implementacion')
        self.assertEqual(r.status_code, 200, r.data)
        a = c.actividades.first()
        self.assertEqual(r.data['responsable_implementacion'], a.responsable_id)
        self.assertEqual(r.data['plazo_implementacion'], str(a.plazo))

    def test_cambio_mayor_exige_planificacion(self):
        c = self._aprobado(clasificacion='mayor')
        self._patch(c, {'responsable_implementacion': self.sig.pk,
                        'plazo_implementacion': str(timezone.localdate() + timedelta(days=10))})
        r = self._post(c, 'iniciar_implementacion')
        self.assertEqual(r.status_code, 400)
        self.assertIn('planificación es obligatoria', r.data['detail'])

    def test_temporal_exige_fecha_de_reversion(self):
        c = self._aprobado()
        self._planificar(c)
        self._patch(c, {'temporalidad': 'temporal'})
        r = self._post(c, 'iniciar_implementacion')
        self.assertEqual(r.status_code, 400)
        self.assertIn('reversión', r.data['detail'])

    def test_afecta_clientes_exige_comunicar_antes(self):
        c = self._aprobado(afecta_clientes=True)
        self._planificar(c)
        r = self._post(c, 'iniciar_implementacion')
        self.assertEqual(r.status_code, 400)
        self.assertIn('clientes', r.data['detail'])
        self._comunicar(c, 'clientes')
        self.assertEqual(self._post(c, 'iniciar_implementacion').status_code, 200)

    def test_verificacion_exige_actividades_y_comunicacion(self):
        c = self._aprobado()
        self._planificar(c)
        self._post(c, 'iniciar_implementacion')
        self.assertEqual(self._post(c, 'pasar_a_verificacion').status_code, 400)
        a = c.actividades.first()
        self._post(c, 'completar_actividad', {'actividad_id': a.pk, 'seguimiento': 'Hecho.'}, fmt='multipart')
        r = self._post(c, 'pasar_a_verificacion')
        self.assertEqual(r.status_code, 400)
        self.assertIn('comunicación', r.data['detail'])
        self._comunicar(c)
        self.assertEqual(self._post(c, 'pasar_a_verificacion').status_code, 200)


class PruebasEficaciaYCierre(BaseCambios):

    def _en_verificacion(self, **kw):
        c = self._implementado(**kw)
        self._comunicar(c)
        self.assertEqual(self._post(c, 'pasar_a_verificacion').status_code, 200)
        return c

    def test_cierre_eficaz(self):
        c = self._en_verificacion()
        self.assertEqual(self._post(c, 'cerrar').status_code, 400)
        self._patch(c, {'se_implemento': True, 'fue_eficaz': True, 'criterios_eficacia': ['resultado', 'calidad'],
                        'verificacion': 'Incertidumbre reducida según la carta de control.'})
        r = self._post(c, 'cerrar')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'cerrado')
        self.assertEqual(r.data['cerrado_por_nombre'], self.sig.get_full_name())

    def test_no_eficaz_exige_reversion_o_accion_correctiva(self):
        c = self._en_verificacion()
        self._patch(c, {'se_implemento': True, 'fue_eficaz': False, 'verificacion': 'No redujo la incertidumbre.'})
        r = self._post(c, 'cerrar')
        self.assertEqual(r.status_code, 400)
        self.assertIn('reversión', r.data['detail'])
        self._patch(c, {'reversion': 'total', 'detalle_reversion': 'Se volvió al patrón anterior.',
                        'fecha_reversion_real': str(timezone.localdate())})
        self.assertEqual(self._post(c, 'cerrar').status_code, 200)

    def test_reabrir_con_motivo(self):
        c = self._en_verificacion()
        self._patch(c, {'se_implemento': True, 'fue_eficaz': True, 'verificacion': 'Eficaz.'})
        self._post(c, 'cerrar')
        self.assertEqual(self._post(c, 'reabrir', {'motivo': 'x'}).status_code, 403)
        r = self._post(c, 'reabrir', {'motivo': 'Se detectó una desviación posterior.'}, usuario=self.gg)
        self.assertEqual(r.data['estado'], 'en_verificacion')
        self.assertEqual(len(r.data['reaperturas']), 1)

    def test_pdfs(self):
        c = self._en_verificacion()
        for url in (f'/api/cambios/{c.pk}/pdf/', f'/api/cambios/{c.pk}/planificacion_pdf/',
                    '/api/cambios/seguimiento_pdf/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertTrue(r.content.startswith(b'%PDF'))


class PruebasCambioTemporal(BaseCambios):
    """Cambio temporal eficaz: queda en vigor hasta registrar su fin; prórroga firmada por el Gerente General."""

    def _temporal_en_verificacion(self):
        c = self._aprobado()
        self._planificar(c)
        fin = timezone.localdate() + timedelta(days=60)
        self.assertEqual(self._patch(c, {'temporalidad': 'temporal', 'fecha_reversion': str(fin)}).status_code, 200)
        self.assertEqual(self._post(c, 'iniciar_implementacion').status_code, 200)
        a = c.actividades.first()
        self._post(c, 'completar_actividad', {'actividad_id': a.pk, 'seguimiento': 'Hecho.'}, fmt='multipart')
        self._comunicar(c)
        self.assertEqual(self._post(c, 'pasar_a_verificacion').status_code, 200)
        self._patch(c, {'se_implemento': True, 'fue_eficaz': True, 'verificacion': 'Eficaz durante el periodo.'})
        return c

    def test_eficaz_queda_en_vigor_y_la_eficacia_se_bloquea(self):
        c = self._temporal_en_verificacion()
        r = self._post(c, 'cerrar')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'temporal_vigente')
        self.assertIsNone(r.data['cerrado_por'])
        r = self._patch(c, {'verificacion': 'Otra cosa.'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('verificación de la eficacia', r.data['detail'])

    def test_registrar_fin_cierra_el_cambio(self):
        c = self._temporal_en_verificacion()
        self._post(c, 'cerrar')
        r = self._post(c, 'registrar_fin_temporal', {'fecha': str(timezone.localdate())}, fmt='multipart')
        self.assertEqual(r.status_code, 400)
        r = self._post(c, 'registrar_fin_temporal', {'fecha': str(timezone.localdate() + timedelta(days=1)),
                                                     'detalle': 'Se restituyó.'}, fmt='multipart')
        self.assertEqual(r.status_code, 400)
        r = self._post(c, 'registrar_fin_temporal', {'fecha': str(timezone.localdate()),
                                                     'detalle': 'Se restituyó el patrón anterior.'}, fmt='multipart')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'cerrado')
        self.assertEqual(r.data['reversion'], 'ninguna')
        self.assertEqual(r.data['fin_temporal_por_nombre'], self.sig.get_full_name())

    def test_temporal_revertido_por_ineficacia_se_cierra_directo(self):
        c = self._temporal_en_verificacion()
        self._patch(c, {'fue_eficaz': False, 'reversion': 'total', 'detalle_reversion': 'Se volvió atrás.',
                        'fecha_reversion_real': str(timezone.localdate())})
        r = self._post(c, 'cerrar')
        self.assertEqual(r.data['estado'], 'cerrado')

    def test_prorroga_solo_gerente_general_con_firma(self):
        c = self._temporal_en_verificacion()
        self._post(c, 'cerrar')
        c.refresh_from_db()
        nueva = c.fecha_reversion + timedelta(days=30)
        datos = {'fecha_nueva': str(nueva), 'motivo': 'El sistema definitivo aún no se instala.'}
        self.assertEqual(self._post(c, 'prorrogar', {**datos, 'password': self.CLAVE}).status_code, 403)
        r = self._post(c, 'prorrogar', datos, usuario=self.gg)
        self.assertEqual(r.status_code, 400)
        r = self._post(c, 'prorrogar', {**datos, 'fecha_nueva': str(c.fecha_reversion), 'password': self.CLAVE})
        self.assertEqual(r.status_code, 400)
        r = self._post(c, 'prorrogar', {**datos, 'password': self.CLAVE})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['fecha_reversion'], str(nueva))
        self.assertEqual(len(r.data['prorrogas']), 1)
        self.assertEqual(r.data['prorrogas'][0]['fecha_anterior'], str(c.fecha_reversion))

    def test_fin_vencido_alerta(self):
        c = self._temporal_en_verificacion()
        self._post(c, 'cerrar')
        Cambio.objects.filter(pk=c.pk).update(fecha_reversion=timezone.localdate() - timedelta(days=1))
        c.refresh_from_db()
        self.assertTrue(c.reversion_vencida)
        self._post(c, 'registrar_fin_temporal', {'fecha': str(timezone.localdate()), 'detalle': 'Restituido.'},
                   fmt='multipart')
        c.refresh_from_db()
        self.assertFalse(c.reversion_vencida)

    def test_nuevo_cambio_permanente(self):
        c = self._temporal_en_verificacion()
        self.assertEqual(self._post(c, 'nuevo_cambio_permanente').status_code, 400)
        self._post(c, 'cerrar')
        r = self._post(c, 'nuevo_cambio_permanente')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['estado'], 'solicitado')
        self.assertEqual(r.data['cambio_origen_codigo'], c.codigo)
        self.assertIn(c.codigo, r.data['descripcion'])
        self.assertEqual(self._post(c, 'nuevo_cambio_permanente').status_code, 400)

    def test_reabrir_temporal_cerrado_vuelve_a_verificacion(self):
        c = self._temporal_en_verificacion()
        self._post(c, 'cerrar')
        self._post(c, 'registrar_fin_temporal', {'fecha': str(timezone.localdate()), 'detalle': 'Restituido.'},
                   fmt='multipart')
        r = self._post(c, 'reabrir', {'motivo': 'Revisar la eficacia.'}, usuario=self.gg)
        self.assertEqual(r.data['estado'], 'en_verificacion')
        self.assertIsNone(r.data['fin_temporal_fecha'])
        self.assertEqual(r.data['reaperturas'][0]['fin_temporal']['detalle'], 'Restituido.')
