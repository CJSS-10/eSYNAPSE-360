"""
Secuencia del procedimiento de auditoría interna y regla "etapa cerrada =
solo lectura" (ADR-0005).

Plan (aprobado por el auditor líder) → documentos de trabajo (lista de
verificación, opcional) → reunión de apertura (acta) → ejecución (evaluación
y hallazgos) → conclusiones (consolidar y clasificar hallazgos) → reunión de
cierre (acta; congela los hallazgos) → informe → cierre.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Auditoria, Hallazgo, ProgramaAuditoria

from .flujo_auditoria import PARTICIPANTES, avanzar


class PruebasSecuenciaAuditoria(CasoBase):

    def setUp(self):
        self.gg = self.crear_usuario('gerente_etapas')
        self.dar_permisos(self.gg, 'auditorias', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.gg)
        self.prog = ProgramaAuditoria.objects.create(anio=2026, created_by=self.gg)
        self.a = Auditoria.objects.create(programa=self.prog, areas_procesos='Masa', normas_aplicables=['iso_17025'],
                                          auditor_lider=self.gg, created_by=self.gg)

    def _patch(self, datos):
        return self.client.patch(f'/api/auditorias/{self.a.pk}/', datos, format='json')

    def _post(self, accion, datos=None):
        return self.client.post(f'/api/auditorias/{self.a.pk}/{accion}/', datos or {}, format='json')

    def test_etapas_abiertas_por_estado(self):
        abiertas = {
            'programada': {'programa', 'plan'},
            'planificada': {'documentos'},
            'apertura': {'apertura'},
            'en_ejecucion': {'ejecucion'},
            'conclusiones': {'conclusiones'},
            'reunion_cierre': {'cierre'},
            'en_informe': {'informe'},
            'cerrada': set(),
        }
        for estado, esperado in abiertas.items():
            self.a.estado = estado
            self.assertEqual({k for k, v in self.a.etapas_abiertas().items() if v}, esperado, estado)

    def test_plan_exige_cronograma_y_lo_aprueba_el_lider(self):
        self._patch({'objetivo': 'Evaluar', 'alcance': 'Todo'})
        r = self._post('planificar')
        self.assertEqual(r.status_code, 400)
        self.assertIn('cronograma', r.data['detail'])
        self._patch({'cronograma_entrevistas': [{'fecha': '2026-10-14', 'area': 'Masa'}]})
        otro = self.crear_usuario('asistente_plan')
        self.dar_permisos(otro, 'auditorias', 'leer', 'editar')
        self.autenticar(otro)
        r = self._post('planificar')
        self.assertEqual(r.status_code, 400, 'quien no es el líder ni aprobador no aprueba el plan')
        self.assertIn('auditor líder', r.data['detail'])
        self.autenticar(self.gg)
        r = self._post('planificar')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'planificada')
        self.assertEqual(r.data['plan_aprobado_por'], self.gg.pk)
        self.assertIsNotNone(r.data['fecha_aprobacion_plan'])
        # Plan aprobado = solo lectura
        r = self._patch({'objetivo': 'Otro'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('Plan de auditoría', r.data['detail'])
        self.assertEqual(self._post('agregar_integrante', {'rol': 'auditor', 'nombre_externo': 'Ana'}).status_code, 400)

    def test_lista_se_prepara_en_documentos_de_trabajo(self):
        avanzar(self, self.a, 'planificada')
        r = self._post('generar_lista', {'norma': 'iso_17025'})
        self.assertEqual(r.status_code, 200, r.data)
        item = self.a.listas.get().items.filter(es_seccion=False).first()
        # En la preparación se anota el documento de referencia…
        r = self._post('evaluar_item', {'item_id': item.pk, 'documento_referencia': 'Manual de calidad'})
        self.assertEqual(r.status_code, 200, r.data)
        # …pero la evaluación espera a la ejecución
        r = self._post('evaluar_item', {'item_id': item.pk, 'resultado': 'cumple'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('reunión de apertura', r.data['detail'])
        # Sin acta de apertura no hay hallazgos
        avanzar(self, self.a, 'apertura')
        self.assertEqual(self._post('registrar_hallazgo', {'tipo': 'observacion', 'descripcion': 'x'}).status_code, 400)
        self.assertEqual(self._post('generar_lista', {'norma': 'sig_integrado'}).status_code, 400,
                         'la lista se prepara antes de la apertura')

    def test_la_lista_es_opcional(self):
        avanzar(self, self.a, 'en_informe')
        self.a.refresh_from_db()
        self.assertEqual(self.a.estado, 'en_informe')
        self.assertFalse(self.a.listas.exists())

    def test_acta_de_apertura_inicia_la_ejecucion(self):
        avanzar(self, self.a, 'apertura')
        r = self._post('registrar_acta', {'tipo': 'apertura', 'participantes': [], 'contenido': 'x'})
        self.assertEqual(r.status_code, 400, 'sin participantes no hay acta')
        r = self._post('registrar_acta', {'tipo': 'cierre', 'participantes': PARTICIPANTES, 'contenido': 'x'})
        self.assertEqual(r.status_code, 400, 'el acta de cierre no va antes de la ejecución')
        r = self._post('registrar_acta', {'tipo': 'apertura', 'participantes': PARTICIPANTES, 'contenido': 'Inicio'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'en_ejecucion')
        self.assertIsNotNone(r.data['fecha_inicio'])
        r = self._post('registrar_acta', {'tipo': 'apertura', 'participantes': PARTICIPANTES, 'contenido': 'Editada'})
        self.assertEqual(r.status_code, 400, 'un acta registrada no se edita')

    def test_conclusiones_consolidan_y_el_acta_de_cierre_congela(self):
        avanzar(self, self.a, 'en_ejecucion')
        self._post('registrar_hallazgo', {'tipo': 'nc_menor', 'descripcion': 'Registro sin firma', 'requisito': '7.5'})
        self._post('registrar_hallazgo', {'tipo': 'odm', 'descripcion': 'Digitalizar registros'})
        nc = Hallazgo.objects.get(auditoria=self.a, tipo='nc_menor')
        self.assertTrue(nc.requiere_ac, 'toda NC de auditoría va a acción correctiva')
        self.assertEqual(nc.tratamiento, 'accion_correctiva')
        odm = Hallazgo.objects.get(auditoria=self.a, tipo='odm')
        self.assertEqual((odm.tratamiento, odm.requiere_ac), ('riesgos_oportunidades', False))
        # Conclusiones: el equipo reclasifica y descarta
        self.assertEqual(self._post('terminar_ejecucion').status_code, 200)
        r = self._post('editar_hallazgo', {'hallazgo_id': nc.pk, 'tipo': 'observacion'})
        self.assertEqual(r.status_code, 200, r.data)
        nc.refresh_from_db()
        self.assertTrue(nc.codigo.startswith('OBS-'), 'al cambiar de tipo toma el código del nuevo tipo')
        self.assertEqual((nc.tratamiento, nc.requiere_ac), ('riesgos_oportunidades', False))
        self.assertEqual(self._post('anular_hallazgo', {'hallazgo_id': odm.pk}).status_code, 200)
        odm.refresh_from_db()
        self.assertFalse(odm.is_active, 'se descarta con baja lógica')
        # Pasar a la reunión de cierre exige conclusiones
        self.assertEqual(self._post('validar_hallazgos').status_code, 400)
        r = self._post('validar_hallazgos', {'conclusiones': 'Conforme con observaciones'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'reunion_cierre')
        # Ya no se tocan hallazgos ni conclusiones
        self.assertEqual(self._post('editar_hallazgo', {'hallazgo_id': nc.pk, 'tipo': 'nc_mayor'}).status_code, 400)
        self.assertEqual(self._post('registrar_hallazgo', {'tipo': 'observacion', 'descripcion': 'tarde'}).status_code, 400)
        self.assertEqual(self._patch({'conclusiones': 'otra'}).status_code, 400)
        # Sin acta de cierre no hay informe
        self.assertEqual(self._patch({'fortalezas': 'Orden'}).status_code, 400)
        r = self._post('registrar_acta', {'tipo': 'cierre', 'participantes': PARTICIPANTES, 'contenido': 'Resultados'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'en_informe')
        self.assertEqual(self._patch({'fortalezas': 'Orden', 'lugar': 'Sede operativa'}).status_code, 200)

    def test_cerrada_todo_solo_lectura(self):
        avanzar(self, self.a, 'cerrada')
        self.a.refresh_from_db()
        self.assertEqual(self.a.estado, 'cerrada')
        self.assertIsNotNone(self.a.fecha_informe)
        for campo, valor in (('fortalezas', 'x'), ('objetivo', 'x'), ('conclusiones', 'x')):
            self.assertEqual(self._patch({campo: valor}).status_code, 400, campo)

    def test_reprogramar_solo_antes_de_la_apertura(self):
        avanzar(self, self.a, 'planificada')
        self.assertEqual(self._post('reprogramar', {'mes_programado': 9, 'motivo': 'Carga'}).status_code, 200)
        avanzar(self, self.a, 'apertura')
        self.assertEqual(self._post('reprogramar', {'mes_programado': 10, 'motivo': 'x'}).status_code, 400)

    def test_etapa_futura_no_se_edita(self):
        r = self._patch({'fortalezas': 'antes de tiempo'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('aún no se abre', r.data['detail'])


class PruebasTrazabilidadListaHallazgos(CasoBase):
    """Cada ítem evaluado como No cumple u Observación debe terminar en un
    hallazgo (nuevo o existente) o descartado con motivo antes de validar."""

    def setUp(self):
        self.gg = self.crear_usuario('lider_traza')
        self.dar_permisos(self.gg, 'auditorias', 'leer', 'crear', 'editar', 'aprobar')
        self.autenticar(self.gg)
        prog = ProgramaAuditoria.objects.create(anio=2026, created_by=self.gg)
        self.a = Auditoria.objects.create(programa=prog, areas_procesos='Masa', normas_aplicables=['iso_17025'],
                                          auditor_lider=self.gg, created_by=self.gg)
        avanzar(self, self.a, 'planificada')
        self._post('generar_lista', {'norma': 'iso_17025'})
        avanzar(self, self.a, 'en_ejecucion')
        items = self.a.listas.get().items.filter(es_seccion=False, bloque='requisitos').order_by('orden')
        self.i1, self.i2, self.i3 = items[0], items[1], items[2]
        for it, res in ((self.i1, 'no_cumple'), (self.i2, 'no_cumple'), (self.i3, 'observa')):
            r = self._post('evaluar_item', {'item_id': it.pk, 'resultado': res, 'evidencia': f'Evidencia {it.codigo}'})
            self.assertEqual(r.status_code, 200, r.data)

    def _post(self, accion, datos=None):
        return self.client.post(f'/api/auditorias/{self.a.pk}/{accion}/', datos or {}, format='json')

    def test_pendientes_se_muestran_y_bloquean_la_validacion(self):
        r = self.client.get(f'/api/auditorias/{self.a.pk}/')
        self.assertEqual([p['id'] for p in r.data['pendientes_clasificar']], [self.i1.pk, self.i2.pk, self.i3.pk])
        self._post('terminar_ejecucion')
        r = self._post('validar_hallazgos', {'conclusiones': 'Conforme'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('sin clasificar', r.data['detail'])

    def test_un_hallazgo_de_varios_items_otro_sumado_y_un_descarte(self):
        r = self._post('registrar_hallazgo', {'tipo': 'nc_menor', 'descripcion': 'Registro sin firma',
                                              'item_ids': [self.i1.pk, self.i2.pk]})
        self.assertEqual(r.status_code, 200, r.data)
        h = Hallazgo.objects.get(auditoria=self.a)
        self.assertEqual(sorted(x['id'] for x in r.data['hallazgos'][0]['items']), sorted([self.i1.pk, self.i2.pk]))
        self.assertEqual([p['id'] for p in r.data['pendientes_clasificar']], [self.i3.pk])
        # Descartar exige motivo
        self.assertEqual(self._post('descartar_items', {'item_ids': [self.i3.pk]}).status_code, 400)
        r = self._post('descartar_items', {'item_ids': [self.i3.pk], 'motivo': 'Ya cubierto por el hallazgo de registros'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['pendientes_clasificar'], [])
        # Reabrir y sumarlo al hallazgo existente
        self._post('reabrir_item', {'item_id': self.i3.pk})
        r = self._post('vincular_items', {'hallazgo_id': h.pk, 'item_ids': [self.i3.pk]})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(len(r.data['hallazgos'][0]['items']), 3)
        # Con todo clasificado, se valida
        self._post('terminar_ejecucion')
        self.assertEqual(self._post('validar_hallazgos', {'conclusiones': 'Conforme'}).status_code, 200)

    def test_descartar_un_hallazgo_devuelve_sus_items_a_pendientes(self):
        self._post('registrar_hallazgo', {'tipo': 'observacion', 'descripcion': 'x', 'item_ids': [self.i3.pk]})
        h = Hallazgo.objects.get(auditoria=self.a)
        self._post('terminar_ejecucion')
        r = self._post('anular_hallazgo', {'hallazgo_id': h.pk})
        self.assertIn(self.i3.pk, [p['id'] for p in r.data['pendientes_clasificar']])

    def test_solo_items_no_cumple_u_observacion_originan_hallazgo(self):
        self._post('evaluar_item', {'item_id': self.i1.pk, 'resultado': 'cumple'})
        r = self._post('registrar_hallazgo', {'tipo': 'nc_menor', 'descripcion': 'x', 'item_ids': [self.i1.pk]})
        self.assertEqual(r.status_code, 400)

    def test_si_el_item_pasa_a_cumple_se_libera(self):
        self._post('registrar_hallazgo', {'tipo': 'nc_menor', 'descripcion': 'x', 'item_ids': [self.i1.pk]})
        self._post('evaluar_item', {'item_id': self.i1.pk, 'resultado': 'cumple'})
        self.i1.refresh_from_db()
        self.assertIsNone(self.i1.hallazgo)
