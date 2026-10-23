"""
M9 Acciones correctivas, según el procedimiento de no conformidades y
acciones correctivas.

Reglas:
- Toda solicitud trata una NC del registro de hallazgos: la elegida (si aún no
  se trata en otra) o una que se crea con su clasificación (NC mayor / menor).
- Etapa cerrada = solo lectura: el registro (procedencia y descripción) se
  corrige solo mientras está Registrada.
- Sin responsable designado no se evalúa.
- Acciones correctivas solo en el análisis (antes de aprobar el plan);
  correcciones hasta la implementación si no requiere acción correctiva.
- Si la verificación es no eficaz, el ciclo queda en el historial y se
  define un nuevo plan con nuevas acciones.
- La eficacia la verifica el verificador designado (o quien puede aprobar).
- Al cerrar (eficaz o solo corrección) se cierran sus NC.
- Se imprimen la Solicitud y el Seguimiento.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Hallazgo, SolicitudAC


class BaseSAC(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gerente_sig_ac')
        self.dar_permisos(self.sig, 'acciones_correctivas', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.dar_permisos(self.sig, 'hallazgos', 'leer', 'crear', 'editar')
        self.resp = self.crear_usuario('responsable_ac')
        self.autenticar(self.sig)

    def _nueva(self, **extra):
        datos = {'fuente': 'auditoria_externa', 'normas_aplicables': ['iso_17025'], 'entidad_auditora': 'INACAL-DA',
                 'auditor': 'Ing. Pérez', 'requisito_auditado': 'NTP-ISO/IEC 17025 7.8.6',
                 'descripcion_nc': 'Certificados sin declaración de conformidad acordada',
                 'tipo_nc': 'nc_menor', 'proceso': 'Emisión de certificados'}
        datos.update(extra)
        return self.client.post('/api/sac/', datos, format='json')

    def _post(self, sac, accion, datos=None):
        return self.client.post(f'/api/sac/{sac.pk}/{accion}/', datos or {}, format='json')

    def _hasta_analisis(self):
        r = self._nueva()
        sac = SolicitudAC.objects.get(pk=r.data['id'])
        r = self._post(sac, 'evaluar', {'requiere_ac': True, 'significancia': 'alto', 'responsable': self.resp.pk})
        self.assertEqual(r.status_code, 200, r.data)
        self._post(sac, 'registrar_analisis', {'porques': ['a', 'b'], 'causa_raiz': 'Plantilla sin el campo'})
        return sac

    def _accion(self, sac, tipo='correctiva'):
        return self._post(sac, 'agregar_accion', {'tipo': tipo, 'descripcion': f'{tipo} de prueba',
                                                  'fecha_propuesta': '2026-11-30', 'responsable': self.resp.pk})


class PruebasRegistroSAC(BaseSAC):

    def test_nueva_sac_crea_su_nc_en_hallazgos(self):
        r = self._nueva()
        self.assertEqual(r.status_code, 201, r.data)
        sac = SolicitudAC.objects.get(pk=r.data['id'])
        self.assertRegex(sac.codigo, r'^SAC-\d{2}-\d{4}$')
        h = sac.hallazgo
        self.assertEqual((h.tipo, h.estado, h.sac_id), ('nc_menor', 'en_tratamiento', sac.pk))
        self.assertEqual(h.fuente, 'auditoria_externa')
        self.assertEqual(r.data['entidad_auditora'], 'INACAL-DA')
        self.assertEqual(r.data['clasificacion'], 'NC Menor')

    def test_nueva_sac_sin_clasificacion_o_proceso_se_rechaza(self):
        self.assertEqual(self._nueva(tipo_nc='').status_code, 400)
        self.assertEqual(self._nueva(proceso='').status_code, 400)
        self.assertEqual(SolicitudAC.objects.count(), 0)

    def test_sac_desde_nc_existente_hereda_y_enlaza(self):
        h = Hallazgo.objects.create(tipo='nc_mayor', fuente='inspeccion', proceso='Masa', descripcion='Desc. NC',
                                    requisito='ISO 9001 7.1.5', fecha_deteccion='2026-10-01', created_by=self.sig)
        r = self.client.post('/api/sac/', {'fuente': 'otros', 'hallazgo': h.pk, 'fuente_detalle': 'Inspección'},
                             format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['descripcion_nc'], 'Desc. NC')
        self.assertEqual(r.data['requisito_auditado'], 'ISO 9001 7.1.5')
        h.refresh_from_db()
        self.assertEqual((h.sac_id, h.estado), (r.data['id'], 'en_tratamiento'))
        r = self.client.post('/api/sac/', {'fuente': 'otros', 'hallazgo': h.pk}, format='json')
        self.assertEqual(r.status_code, 400, 'la NC ya se trata en una solicitud')
        obs = Hallazgo.objects.create(tipo='observacion', fuente='otro', proceso='x', descripcion='x',
                                      fecha_deteccion='2026-10-01', created_by=self.sig)
        r = self.client.post('/api/sac/', {'fuente': 'otros', 'hallazgo': obs.pk}, format='json')
        self.assertEqual(r.status_code, 400, 'una observación no se trata con solicitud')

    def test_registro_solo_editable_registrada(self):
        sac = SolicitudAC.objects.get(pk=self._nueva().data['id'])
        r = self.client.patch(f'/api/sac/{sac.pk}/', {'auditor': 'Ing. Pérez Soto'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self._post(sac, 'evaluar', {'requiere_ac': True, 'significancia': 'bajo', 'responsable': self.resp.pk})
        r = self.client.patch(f'/api/sac/{sac.pk}/', {'descripcion_nc': 'otra'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('Descripción de la No Conformidad', str(r.data))

    def test_evaluar_exige_responsable(self):
        sac = SolicitudAC.objects.get(pk=self._nueva().data['id'])
        r = self._post(sac, 'evaluar', {'requiere_ac': True, 'significancia': 'bajo'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('responsable', str(r.data).lower())


class PruebasEtapasSAC(BaseSAC):

    def test_acciones_segun_etapa(self):
        sac = SolicitudAC.objects.get(pk=self._nueva().data['id'])
        self.assertEqual(self._accion(sac, 'correccion').status_code, 201, 'corrección inmediata en el registro')
        self.assertEqual(self._accion(sac, 'correctiva').status_code, 400, 'la AC se define en el análisis')
        self._post(sac, 'evaluar', {'requiere_ac': True, 'significancia': 'bajo', 'responsable': self.resp.pk})
        self.assertEqual(self._accion(sac, 'correctiva').status_code, 201)
        self._post(sac, 'registrar_analisis', {'porques': ['a'], 'causa_raiz': 'Causa'})
        r = self._post(sac, 'aprobar_plan', {'verificador': self.sig.pk})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self._accion(sac, 'correctiva').status_code, 400, 'plan aprobado: no se agregan AC')
        self.assertEqual(self._accion(sac, 'correccion').status_code, 400, 'requiere AC: no se agregan correcciones')

    def test_no_eficaz_guarda_ciclo_y_pide_nuevo_plan(self):
        sac = self._hasta_analisis()
        acc = self._accion(sac).data['acciones'][0]['id']
        self._post(sac, 'aprobar_plan', {'verificador': self.sig.pk})
        self._post(sac, 'completar_accion', {'accion_id': acc, 'verificacion': 'Hecho'})
        r = self._post(sac, 'verificar_eficacia', {'eficaz': False, 'evaluacion': 'Recurrió en la siguiente emisión'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['estado'], r.data['ciclo']), ('en_analisis', 2))
        self.assertEqual(r.data['ciclos_anteriores'][0]['causa_raiz'], 'Plantilla sin el campo')
        self.assertEqual(r.data['ciclos_anteriores'][0]['evaluacion'], 'Recurrió en la siguiente emisión')
        # El nuevo ciclo empieza con el análisis en blanco (no se duplica el anterior).
        self.assertEqual((r.data['porques'], r.data['causa_raiz']), ([], ''))
        self.assertEqual(self._accion(sac).data['acciones'][-1]['ciclo'], 2)
        r = self._post(sac, 'aprobar_plan', {'verificador': self.sig.pk})
        self.assertEqual(r.status_code, 400, 'el nuevo ciclo necesita su propio análisis de causa')
        self._post(sac, 'registrar_analisis', {'porques': [{'pregunta': '¿Por qué recurrió?', 'respuesta': 'Otra plantilla'}],
                                               'causa_raiz': 'Plantillas sin control de versiones'})
        self.assertEqual(self._post(sac, 'aprobar_plan', {'verificador': self.sig.pk}).status_code, 200)
        pdf = self.client.get(f'/api/sac/{sac.pk}/pdf/')
        self.assertEqual(pdf.status_code, 200)

    def test_no_eficaz_nuevo_ciclo_exige_accion_propia(self):
        sac = self._hasta_analisis()
        acc = self._accion(sac).data['acciones'][0]['id']
        self._post(sac, 'aprobar_plan', {'verificador': self.sig.pk})
        self._post(sac, 'completar_accion', {'accion_id': acc, 'verificacion': 'Hecho'})
        self._post(sac, 'verificar_eficacia', {'eficaz': False, 'evaluacion': 'Recurrió'})
        self._post(sac, 'registrar_analisis', {'causa_raiz': 'Plantilla sin el campo'})
        r = self._post(sac, 'aprobar_plan', {'verificador': self.sig.pk})
        self.assertEqual(r.status_code, 400, 'el nuevo ciclo necesita su propia acción correctiva')

    def test_verifica_el_designado_o_quien_aprueba(self):
        sac = self._hasta_analisis()
        acc = self._accion(sac).data['acciones'][0]['id']
        verificador = self.crear_usuario('verificador_ac')
        self.dar_permisos(verificador, 'acciones_correctivas', 'leer', 'editar')
        otro = self.crear_usuario('otro_ac')
        self.dar_permisos(otro, 'acciones_correctivas', 'leer', 'editar')
        self._post(sac, 'aprobar_plan', {'verificador': verificador.pk})
        self._post(sac, 'completar_accion', {'accion_id': acc, 'verificacion': 'Hecho'})
        self.autenticar(otro)
        r = self._post(sac, 'verificar_eficacia', {'eficaz': True, 'evaluacion': 'ok'})
        self.assertEqual(r.status_code, 400, 'ni designado ni aprobador')
        self.autenticar(verificador)
        r = self._post(sac, 'verificar_eficacia', {'eficaz': True, 'evaluacion': 'Sin recurrencia'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'cerrada_conforme')
        self.assertEqual(Hallazgo.objects.get(pk=sac.hallazgo_id).estado, 'cerrado')

    def test_solo_correccion_cierra_la_nc(self):
        sac = SolicitudAC.objects.get(pk=self._nueva().data['id'])
        r = self._post(sac, 'evaluar', {'requiere_ac': False, 'significancia': 'bajo', 'responsable': self.resp.pk})
        self.assertEqual(r.data['estado'], 'en_implementacion')
        acc = self._accion(sac, 'correccion').data['acciones'][0]['id']
        r = self._post(sac, 'completar_accion', {'accion_id': acc, 'verificacion': 'Corregido'})
        self.assertEqual(r.data['estado'], 'cerrada_sin_ac')
        self.assertEqual(r.data['clasificacion'], 'NC Menor / Solo corrección')
        self.assertEqual(Hallazgo.objects.get(pk=sac.hallazgo_id).estado, 'cerrado')


class PruebasImpresosSAC(BaseSAC):

    def test_solicitud_y_seguimiento_pdf(self):
        sac = self._hasta_analisis()
        self._accion(sac)
        r = self.client.get(f'/api/sac/{sac.pk}/pdf/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))
        r = self.client.get('/api/sac/seguimiento_pdf/?abiertas=1')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))


class PruebasCincoPorques(BaseSAC):

    def test_pregunta_y_respuesta_las_redacta_el_analista(self):
        sac = SolicitudAC.objects.get(pk=self._nueva().data['id'])
        self._post(sac, 'evaluar', {'requiere_ac': True, 'significancia': 'bajo', 'responsable': self.resp.pk})
        cadena = [{'pregunta': '¿Por qué el certificado salió sin la declaración?', 'respuesta': 'La plantilla no la tiene'},
                  {'pregunta': '¿Por qué la plantilla no la tiene?', 'respuesta': 'No se actualizó tras el cambio de norma'},
                  {'pregunta': '', 'respuesta': ''}]
        r = self._post(sac, 'registrar_analisis', {'porques': cadena, 'causa_raiz': 'Sin control de cambios de plantillas'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['porques'], cadena[:2], 'se guardan los pares y se descartan los vacíos')
        r = self.client.get(f'/api/sac/{sac.pk}/pdf/')
        self.assertTrue(r.content.startswith(b'%PDF'))


class PruebasDatosDelFormato(BaseSAC):
    """Fecha de registro y quién verificó la eficacia (cabecera, evaluación de la eficacia y conformidad)."""

    def test_fecha_de_registro(self):
        from django.utils import timezone
        r = self._nueva()
        self.assertEqual(r.data['fecha_registro'], str(timezone.localdate()), 'sin indicarla, la de hoy')
        r = self._nueva(fecha_registro='2026-09-15')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['fecha_registro'], '2026-09-15')
        nc = Hallazgo.objects.get(sac_id=r.data['id'])
        self.assertEqual(str(nc.fecha_deteccion), '2026-09-15', 'la NC creada toma esa fecha')
        futura = str(timezone.localdate() + timezone.timedelta(days=2))
        self.assertEqual(self._nueva(fecha_registro=futura).status_code, 400)

    def test_fecha_de_registro_es_parte_del_registro(self):
        sac = self._hasta_analisis()
        r = self.client.patch(f'/api/sac/{sac.pk}/', {'fecha_registro': '2026-01-01'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('Fecha de registro', str(r.data))

    def test_se_registra_quien_verifico(self):
        sac = self._hasta_analisis()
        acc = self._accion(sac).data['acciones'][0]['id']
        self._post(sac, 'aprobar_plan', {'verificador': self.resp.pk})
        self._post(sac, 'completar_accion', {'accion_id': acc, 'verificacion': 'Hecho'})
        # Verifica quien tiene permiso de aprobar, no el designado.
        r = self._post(sac, 'verificar_eficacia', {'eficaz': True, 'evaluacion': 'Sin recurrencia'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['verificado_por'], self.sig.pk)
        self.assertEqual(r.data['verificado_por_nombre'], self.sig.get_full_name())
        self.assertEqual(r.data['responsable_cierre_nombre'], self.sig.get_full_name())
        from esynapse_sig.ficha_pdf import responsable_cierre_sac
        self.assertEqual(responsable_cierre_sac(SolicitudAC.objects.get(pk=sac.pk)), self.sig.get_full_name())


class PruebasCorregirAcciones(BaseSAC):
    """Una corrección o acción correctiva olvidada o mal escrita se agrega,
    corrige o quita mientras su etapa sigue abierta; después, solo lectura."""

    def test_corregir_y_quitar_mientras_la_etapa_esta_abierta(self):
        sac = self._hasta_analisis()
        r = self._accion(sac, 'correccion')
        self.assertEqual(r.status_code, 201, 'en el análisis aún se agregan correcciones')
        corr = r.data['acciones'][0]
        self.assertTrue(corr['editable'])
        r = self._post(sac, 'editar_accion', {'accion_id': corr['id'], 'descripcion': 'Corrección corregida',
                                              'fecha_propuesta': '2026-12-01'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['acciones'][0]['descripcion'], 'Corrección corregida')
        acc = self._accion(sac).data['acciones']
        correctiva = next(a for a in acc if a['tipo'] == 'correctiva')
        r = self._post(sac, 'quitar_accion', {'accion_id': correctiva['id']})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([a['tipo'] for a in r.data['acciones']], ['correccion'], 'se quita (baja lógica)')
        from esynapse_sig.models import AccionSAC
        self.assertFalse(AccionSAC.objects.get(pk=correctiva['id']).is_active)
        self.assertEqual(self._post(sac, 'aprobar_plan', {'verificador': self.sig.pk}).status_code, 400,
                         'la acción quitada no cuenta para el plan')

    def test_cerrada_la_etapa_no_se_modifica(self):
        sac = self._hasta_analisis()
        acc = self._accion(sac).data['acciones'][0]
        self._post(sac, 'aprobar_plan', {'verificador': self.sig.pk})
        r = self._post(sac, 'editar_accion', {'accion_id': acc['id'], 'descripcion': 'tarde'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('etapa está cerrada', str(r.data))
        self.assertEqual(self._post(sac, 'quitar_accion', {'accion_id': acc['id']}).status_code, 400)

    def test_sig_integrado_marca_las_tres_normas(self):
        from esynapse_sig.views import normas_de_sac
        self.assertEqual(normas_de_sac(['iso_17025', 'sig_integrado']),
                         ['iso_17025', 'iso_9001', 'iso_14001', 'iso_45001'])


class PruebasCompletarYReabrir(BaseSAC):
    """Completar exige describir la verificación; una acción completada por error
    se reabre con motivo hasta que se verifique la eficacia."""

    def _en_implementacion(self):
        sac = self._hasta_analisis()
        ids = [a['id'] for a in self._accion(sac).data['acciones']]
        ids.append(self._accion(sac).data['acciones'][-1]['id'])
        self._post(sac, 'aprobar_plan', {'verificador': self.sig.pk})
        return sac, ids

    def test_completar_exige_verificacion(self):
        sac, ids = self._en_implementacion()
        r = self._post(sac, 'completar_accion', {'accion_id': ids[0], 'verificacion': '  '})
        self.assertEqual(r.status_code, 400)
        self.assertIn('verificación', str(r.data))

    def test_reabrir_con_motivo_y_volver_a_implementacion(self):
        sac, ids = self._en_implementacion()
        self._post(sac, 'completar_accion', {'accion_id': ids[0], 'verificacion': 'Hecho A'})
        r = self._post(sac, 'completar_accion', {'accion_id': ids[1], 'verificacion': 'Hecho B'})
        self.assertEqual(r.data['estado'], 'en_verificacion')
        self.assertEqual(self._post(sac, 'reabrir_accion', {'accion_id': ids[1]}).status_code, 400, 'sin motivo')
        r = self._post(sac, 'reabrir_accion', {'accion_id': ids[1], 'motivo': 'Se completó por error'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'en_implementacion', 'vuelve a implementación')
        acc = next(a for a in r.data['acciones'] if a['id'] == ids[1])
        self.assertEqual(acc['estado'], 'pendiente')
        self.assertEqual(acc['reaperturas'][0]['motivo'], 'Se completó por error')
        self.assertEqual(acc['reaperturas'][0]['verificacion'], 'Hecho B')
        r = self._post(sac, 'completar_accion', {'accion_id': ids[1], 'verificacion': 'Hecho B corregido'})
        self.assertEqual(r.data['estado'], 'en_verificacion')
        self._post(sac, 'verificar_eficacia', {'eficaz': True, 'evaluacion': 'Sin recurrencia'})
        r = self._post(sac, 'reabrir_accion', {'accion_id': ids[0], 'motivo': 'tarde'})
        self.assertEqual(r.status_code, 400, 'verificada la eficacia ya no se reabre')


class PruebasFechaActualizacionSeguimiento(BaseSAC):

    def test_es_la_ultima_modificacion_real(self):
        from datetime import datetime, timezone as tz
        from esynapse_sig.models import AccionSAC
        from esynapse_sig.views import _ultima_modificacion_sac
        sac = self._hasta_analisis()
        acc = self._accion(sac).data['acciones'][0]['id']
        SolicitudAC.objects.filter(pk=sac.pk).update(updated_at=datetime(2026, 3, 1, 15, tzinfo=tz.utc))
        Hallazgo.objects.filter(sac=sac).update(updated_at=datetime(2026, 2, 1, 15, tzinfo=tz.utc))
        AccionSAC.objects.filter(pk=acc).update(updated_at=datetime(2026, 4, 9, 15, tzinfo=tz.utc))
        self.assertEqual(str(_ultima_modificacion_sac([SolicitudAC.objects.get(pk=sac.pk)])), '2026-04-09',
                         'la acción es lo último que cambió')
        self.assertIsNone(_ultima_modificacion_sac([]))
