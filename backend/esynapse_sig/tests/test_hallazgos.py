"""
M8 Hallazgos, según el procedimiento de no conformidades y acciones correctivas.

Reglas:
- Toda NC (mayor o menor) se trata en una solicitud de acción correctiva:
  nueva, o una abierta del mismo problema (la nueva ocurrencia se suma, no se
  duplica la solicitud).
- Las observaciones y oportunidades de mejora no se tratan aquí: quedan
  "Derivadas a riesgos y oportunidades".
- Etapa cerrada = solo lectura: el registro se corrige mientras no se haya
  derivado a una solicitud; los hallazgos de auditoría se corrigen desde la
  auditoría. El tipo solo cambia por reclasificación con motivo.
- Una NC de auditoría se deriva recién después de la reunión de cierre.
- Al cerrarse la solicitud (eficaz, o solo corrección) se cierran todas sus NC.
- Códigos: NC-NNN-AAAA con el año de detección (o del programa de auditoría);
  SAC-NN-AAAA como en el procedimiento.
"""
from datetime import date

from core.tests.base import CasoBase
from esynapse_sig.models import Auditoria, Hallazgo, ProgramaAuditoria, SolicitudAC


class BaseHallazgos(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gerente_sig_h')
        self.dar_permisos(self.sig, 'hallazgos', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.dar_permisos(self.sig, 'acciones_correctivas', 'leer', 'crear', 'editar', 'aprobar')
        self.autenticar(self.sig)

    def _crear(self, tipo='nc_menor', **extra):
        datos = {'tipo': tipo, 'fuente': 'seguimiento', 'proceso': 'Laboratorio de Masa',
                 'descripcion': 'Balanza sin etiqueta de calibración vigente', 'requisito': 'ISO 17025 6.4.8',
                 'fecha_deteccion': '2026-09-10'}
        datos.update(extra)
        r = self.client.post('/api/hallazgos/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return Hallazgo.objects.get(pk=r.data['id'])

    def _post(self, h, accion, datos=None):
        return self.client.post(f'/api/hallazgos/{h.pk}/{accion}/', datos or {}, format='json')


class PruebasTratamientoSegunProcedimiento(BaseHallazgos):

    def test_nc_requiere_sac_y_obs_se_deriva(self):
        nc = self._crear('nc_menor')
        self.assertTrue(nc.requiere_ac, 'toda NC se registra en una solicitud de acción correctiva')
        self.assertEqual((nc.estado, nc.tratamiento), ('registrado', 'accion_correctiva'))
        obs = self._crear('observacion')
        self.assertEqual((obs.estado, obs.tratamiento), ('derivado', 'riesgos_oportunidades'))
        self.assertFalse(obs.requiere_ac)
        r = self._post(obs, 'generar_sac')
        self.assertEqual(r.status_code, 400, 'una observación no genera solicitud de acción correctiva')

    def test_generar_sac_y_sumar_ocurrencia_a_sac_abierta(self):
        nc1 = self._crear('nc_mayor')
        r = self._post(nc1, 'generar_sac')
        self.assertEqual(r.status_code, 201, r.data)
        nc1.refresh_from_db()
        sac = nc1.sac
        self.assertEqual(nc1.estado, 'en_tratamiento')
        self.assertRegex(sac.codigo, r'^SAC-\d{2}-\d{4}$')
        nc2 = self._crear('nc_menor', descripcion='Otra balanza sin etiqueta')
        abiertas = self.client.get(f'/api/hallazgos/{nc2.pk}/sac_abiertas/').data
        self.assertEqual(abiertas[0]['codigo'], sac.codigo)
        self.assertTrue(abiertas[0]['similar'], 'mismo requisito: se sugiere como posible duplicado')
        r = self._post(nc2, 'vincular_sac', {'sac_id': sac.pk})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(SolicitudAC.objects.count(), 1, 'no se duplica la solicitud')
        r = self.client.get(f'/api/sac/{sac.pk}/')
        self.assertEqual({h['codigo'] for h in r.data['hallazgos_vinculados']}, {nc1.codigo, nc2.codigo})
        r = self._post(nc2, 'generar_sac')
        self.assertEqual(r.status_code, 400, 'ya se trata en una solicitud')

    def test_no_se_suma_a_una_sac_cerrada(self):
        nc1 = self._crear('nc_menor')
        self._post(nc1, 'generar_sac')
        sac = Hallazgo.objects.get(pk=nc1.pk).sac
        SolicitudAC.objects.filter(pk=sac.pk).update(estado='cerrada_conforme')
        nc2 = self._crear('nc_menor')
        r = self._post(nc2, 'vincular_sac', {'sac_id': sac.pk})
        self.assertEqual(r.status_code, 400)

    def test_cerrar_sac_cierra_todas_sus_nc(self):
        nc1 = self._crear('nc_menor')
        self._post(nc1, 'generar_sac')
        sac = Hallazgo.objects.get(pk=nc1.pk).sac
        nc2 = self._crear('nc_menor')
        self._post(nc2, 'vincular_sac', {'sac_id': sac.pk})
        base = f'/api/sac/{sac.pk}'
        r = self.client.post(f'{base}/evaluar/', {'requiere_ac': True, 'significancia': 'alto', 'responsable': self.sig.pk},
                             format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.client.post(f'{base}/registrar_analisis/', {'porques': ['a', 'b'], 'causa_raiz': 'Sin control de vencimientos'},
                         format='json')
        r = self.client.post(f'{base}/agregar_accion/', {'tipo': 'correctiva', 'descripcion': 'Programa de calibración con alertas',
                                                          'fecha_propuesta': '2026-10-30', 'responsable': self.sig.pk},
                             format='json')
        self.assertEqual(r.status_code, 201, r.data)
        accion = r.data['acciones'][0]['id']
        verificador = self.crear_usuario('verificador_h')
        r = self.client.post(f'{base}/aprobar_plan/', {'verificador': verificador.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        r = self.client.post(f'{base}/completar_accion/', {'accion_id': accion, 'verificacion': 'Implementado'}, format='json')
        self.assertEqual(r.data['estado'], 'en_verificacion')
        # No eficaz: vuelve a análisis y las NC siguen abiertas.
        r = self.client.post(f'{base}/verificar_eficacia/', {'eficaz': False, 'evaluacion': 'Recurrió'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'en_analisis')
        self.assertEqual(Hallazgo.objects.get(pk=nc1.pk).estado, 'en_tratamiento')
        SolicitudAC.objects.filter(pk=sac.pk).update(estado='en_verificacion')
        r = self.client.post(f'{base}/verificar_eficacia/', {'eficaz': True, 'evaluacion': 'Sin recurrencia en 3 meses'},
                             format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'cerrada_conforme')
        for h in (nc1, nc2):
            h.refresh_from_db()
            self.assertEqual(h.estado, 'cerrado')
            self.assertIn(sac.codigo, h.comentarios_cierre)


class PruebasEtapasHallazgo(BaseHallazgos):

    def test_registro_editable_hasta_derivar(self):
        nc = self._crear('nc_menor')
        r = self.client.patch(f'/api/hallazgos/{nc.pk}/', {'lugar': 'Lab. Masa, 3.er piso'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self._post(nc, 'generar_sac')
        r = self.client.patch(f'/api/hallazgos/{nc.pk}/', {'descripcion': 'Cambio tardío'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('Descripción', str(r.data), 'el mensaje nombra el campo')
        self.assertIn('SAC-', str(r.data), 'y la solicitud que ya lo trata')

    def test_tipo_solo_por_reclasificacion_con_motivo(self):
        nc = self._crear('nc_menor')
        r = self.client.patch(f'/api/hallazgos/{nc.pk}/', {'tipo': 'observacion'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self._post(nc, 'reclasificar', {'tipo': 'observacion'})
        self.assertEqual(r.status_code, 400, 'sin motivo no se reclasifica')
        anterior = nc.codigo
        r = self._post(nc, 'reclasificar', {'tipo': 'observacion', 'motivo': 'No hay requisito incumplido'})
        self.assertEqual(r.status_code, 200, r.data)
        nc.refresh_from_db()
        self.assertTrue(nc.codigo.startswith('OBS-'))
        self.assertEqual((nc.estado, nc.requiere_ac), ('derivado', False))
        self.assertEqual(nc.reclasificaciones[0]['codigo_anterior'], anterior)
        self.assertEqual(nc.reclasificaciones[0]['motivo'], 'No hay requisito incumplido')

    def test_hallazgo_de_auditoria_se_corrige_en_la_auditoria_y_se_deriva_tras_el_cierre(self):
        prog = ProgramaAuditoria.objects.create(anio=2027, created_by=self.sig)
        a = Auditoria.objects.create(programa=prog, areas_procesos='Masa', estado='conclusiones', created_by=self.sig)
        h = Hallazgo.objects.create(tipo='nc_menor', fuente='auditoria_interna', proceso='Masa',
                                    descripcion='x', fecha_deteccion=date(2026, 10, 1), auditoria=a,
                                    created_by=self.sig)
        self.assertTrue(h.codigo.endswith('-2027'), 'el código lleva el año del programa de auditoría')
        r = self.client.patch(f'/api/hallazgos/{h.pk}/', {'descripcion': 'y'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn(a.codigo, str(r.data))
        r = self._post(h, 'reclasificar', {'tipo': 'observacion', 'motivo': 'm'})
        self.assertEqual(r.status_code, 400)
        r = self._post(h, 'generar_sac')
        self.assertEqual(r.status_code, 400, 'en consolidación aún no se deriva')
        Auditoria.objects.filter(pk=a.pk).update(estado='en_informe')
        r = self._post(h, 'generar_sac')
        self.assertEqual(r.status_code, 201, r.data)

    def test_codigo_con_anio_de_deteccion(self):
        h = self._crear('nc_menor', fecha_deteccion='2025-12-30')
        self.assertTrue(h.codigo.endswith('-2025'))

    def test_eliminar_es_baja_logica(self):
        h = self._crear('odm')
        r = self.client.delete(f'/api/hallazgos/{h.pk}/')
        self.assertEqual(r.status_code, 204)
        h.refresh_from_db()
        self.assertFalse(h.is_active)


class PruebasCodigosHallazgo(BaseHallazgos):

    def test_codigo_liberado_al_reclasificar_no_se_reutiliza(self):
        nc = self._crear('nc_menor')
        anterior = nc.codigo
        self._post(nc, 'reclasificar', {'tipo': 'observacion', 'motivo': 'No hay requisito incumplido'})
        otra = self._crear('nc_menor')
        self.assertNotEqual(otra.codigo, anterior, 'el código queda en el historial del hallazgo reclasificado')


class PruebasResponsableDelHallazgo(BaseHallazgos):
    """El responsable del tratamiento se designa al evaluar la solicitud de acción correctiva; el hallazgo lo
    muestra desde ahí (antes de eso queda por designar)."""

    def test_responsable_viene_de_la_solicitud(self):
        nc = self._crear('nc_menor')
        self.assertIsNone(self.client.get(f'/api/hallazgos/{nc.pk}/').data['responsable_nombre'])
        self._post(nc, 'generar_sac')
        sac = Hallazgo.objects.get(pk=nc.pk).sac
        r = self.client.post(f'/api/sac/{sac.pk}/evaluar/', {'requiere_ac': True, 'significancia': 'alto',
                                                              'responsable': self.sig.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        nombre = self.sig.get_full_name() or self.sig.username
        self.assertEqual(self.client.get(f'/api/hallazgos/{nc.pk}/').data['responsable_nombre'], nombre)
        datos = self.client.get('/api/hallazgos/').data
        lista = datos['results'] if isinstance(datos, dict) else datos
        self.assertEqual(next(h for h in lista if h['id'] == nc.pk)['responsable_nombre'], nombre, 'también en la lista')
