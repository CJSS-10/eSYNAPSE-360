"""
Programa anual como documento controlado.

- Aprobado = solo lectura: no se agregan ni quitan auditorías ni se cambian los
  campos que definen el programa (proceso, clase, cláusulas, mes, observaciones).
- Los datos del plan (objetivo, alcance…) y la reprogramación siguen permitidos.
- "Modificar programa" lo abre con motivo; al volver a aprobarlo sube la revisión.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Auditoria, ProgramaAuditoria


class PruebasBloqueoPrograma(CasoBase):

    def setUp(self):
        self.gg = self.crear_usuario('gerente')
        self.dar_permisos(self.gg, 'auditorias', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.gg)
        self.programa = ProgramaAuditoria.objects.create(anio=2026, created_by=self.gg)
        r = self.client.post('/api/auditorias/', {'programa': self.programa.pk, 'normas_aplicables': ['iso_9001'],
                                                  'areas_procesos': 'Logística', 'mes_programado': 4}, format='json')
        self.aud = Auditoria.objects.get(pk=r.data['id'])
        self.assertEqual(self.client.post(f'/api/programas-auditoria/{self.programa.pk}/aprobar/').status_code, 200)
        self.programa.refresh_from_db()

    def test_aprobado_queda_de_solo_lectura(self):
        self.assertTrue(self.programa.bloqueado)
        self.assertEqual(self.programa.revision, 0)
        # No se agregan auditorías
        r = self.client.post('/api/auditorias/', {'programa': self.programa.pk, 'areas_procesos': 'Masa', 'mes_programado': 6}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('solo lectura', r.data['detail'])
        # No se quitan
        self.assertEqual(self.client.delete(f'/api/auditorias/{self.aud.pk}/').status_code, 400)
        # No se cambian los campos del programa
        for campo, valor in (('mes_programado', 9), ('clase', 'externa'), ('areas_procesos', 'Otro'),
                             ('requisitos_por_norma', {'iso_9001': '4.1'}), ('observaciones_programa', 'x')):
            r = self.client.patch(f'/api/auditorias/{self.aud.pk}/', {campo: valor}, format='json')
            self.assertEqual(r.status_code, 400, campo)
        # El programa mismo tampoco
        self.assertEqual(self.client.patch(f'/api/programas-auditoria/{self.programa.pk}/', {'observaciones': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/programas-auditoria/{self.programa.pk}/').status_code, 400)

    def test_el_plan_y_la_reprogramacion_siguen_permitidos(self):
        r = self.client.patch(f'/api/auditorias/{self.aud.pk}/', {'objetivo': 'Evaluar', 'alcance': 'Procesos', 'modalidad': 'remota'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        r = self.client.patch(f'/api/auditorias/{self.aud.pk}/', {'mes_programado': 4}, format='json')
        self.assertEqual(r.status_code, 200, 'enviar el mismo valor no cuenta como cambio')
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/reprogramar/', {'mes_programado': 7, 'motivo': 'Carga'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.aud.refresh_from_db()
        self.assertEqual((self.aud.mes_programado, self.aud.mes_reprogramado), (4, 7))

    def test_modificar_exige_motivo_y_reabre(self):
        r = self.client.post(f'/api/programas-auditoria/{self.programa.pk}/abrir_modificacion/', {}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post(f'/api/programas-auditoria/{self.programa.pk}/abrir_modificacion/', {'motivo': 'Se agrega auditoría a Masa'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'en_modificacion')
        self.assertFalse(r.data['bloqueado'])
        self.assertEqual(r.data['modificado_por_nombre'], self.gg.get_full_name())
        # Ya se puede cambiar
        r = self.client.post('/api/auditorias/', {'programa': self.programa.pk, 'areas_procesos': 'Masa', 'mes_programado': 6}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client.patch(f'/api/auditorias/{self.aud.pk}/', {'mes_programado': 5}, format='json').status_code, 200)

    def test_reaprobar_sube_la_revision_y_vuelve_a_bloquear(self):
        self.client.post(f'/api/programas-auditoria/{self.programa.pk}/abrir_modificacion/', {'motivo': 'Cambio de mes'}, format='json')
        r = self.client.post(f'/api/programas-auditoria/{self.programa.pk}/aprobar/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'aprobado')
        self.assertEqual(r.data['revision'], 1)
        self.assertTrue(r.data['bloqueado'])
        self.assertEqual(self.client.post(f'/api/programas-auditoria/{self.programa.pk}/abrir_modificacion/', {'motivo': 'otro'}, format='json').status_code, 200)
        self.client.post(f'/api/programas-auditoria/{self.programa.pk}/aprobar/')
        self.programa.refresh_from_db()
        self.assertEqual(self.programa.revision, 2)

    def test_programada_exige_programa_y_extraordinaria_no(self):
        r = self.client.post('/api/auditorias/', {'tipo': 'programada', 'areas_procesos': 'Masa', 'normas_aplicables': ['iso_9001']}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('programa', r.data)
        r = self.client.post('/api/auditorias/', {'tipo': 'extraordinaria', 'areas_procesos': 'Queja cliente', 'normas_aplicables': ['iso_9001']}, format='json')
        self.assertEqual(r.status_code, 201, r.data)

    def test_mover_auditoria_entre_programas(self):
        borrador = ProgramaAuditoria.objects.create(anio=2027, created_by=self.gg)
        otra = Auditoria.objects.create(programa=borrador, areas_procesos='Temperatura', created_by=self.gg)
        # No se mueve hacia un programa aprobado
        r = self.client.patch(f'/api/auditorias/{otra.pk}/', {'programa': self.programa.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        # Sí entre programas no aprobados
        destino = ProgramaAuditoria.objects.create(anio=2028, created_by=self.gg)
        self.assertEqual(otra.codigo, 'AI-01-2027', 'el código nace con el año del programa')
        r = self.client.patch(f'/api/auditorias/{otra.pk}/', {'programa': destino.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['programa_anio'], 2028)
        self.assertEqual(r.data['codigo'], 'AI-01-2028', 'al cambiar de programa el código sigue al año')
        # El listado filtra por programa
        r = self.client.get(f'/api/auditorias/?programa={destino.pk}')
        datos = r.data['results'] if isinstance(r.data, dict) else r.data
        self.assertEqual([a['codigo'] for a in datos], ['AI-01-2028'])
        self.assertEqual(datos[0]['programa_anio'], 2028)

    def test_codigo_sigue_al_anio_del_programa(self):
        p27 = ProgramaAuditoria.objects.create(anio=2027, created_by=self.gg)
        p28 = ProgramaAuditoria.objects.create(anio=2028, created_by=self.gg)
        a = Auditoria.objects.create(programa=p27, areas_procesos='Masa', created_by=self.gg)
        b = Auditoria.objects.create(programa=p27, areas_procesos='Longitud', created_by=self.gg)
        self.assertEqual((a.codigo, b.codigo), ('AI-01-2027', 'AI-02-2027'))
        # Una auditoría con el año equivocado (registrada antes de la regla) se corrige al guardar
        Auditoria.objects.filter(pk=b.pk).update(codigo='AI-09-2026')
        b.refresh_from_db()
        b.save()
        self.assertEqual(b.codigo, 'AI-02-2027')
        # El correlativo del año destino continúa donde iba
        a.programa = p28
        a.save()
        self.assertEqual(a.codigo, 'AI-01-2028')
        b.programa = p28
        b.save()
        self.assertEqual(b.codigo, 'AI-02-2028')
        # En ejecución o cerrada conserva el código: ya está impreso en actas y listas
        b.estado = 'en_ejecucion'
        b.programa = p27
        b.save()
        self.assertEqual(b.codigo, 'AI-02-2028')

    def test_solo_un_programa_aprobado_se_abre(self):
        borrador = ProgramaAuditoria.objects.create(anio=2027, created_by=self.gg)
        r = self.client.post(f'/api/programas-auditoria/{borrador.pk}/abrir_modificacion/', {'motivo': 'x'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_reaprobacion_por_candado_tambien_sube_revision(self):
        asistente = self.crear_usuario('asistente')
        self.dar_permisos(asistente, 'auditorias', 'leer', 'crear', 'editar')
        self.client.post(f'/api/programas-auditoria/{self.programa.pk}/abrir_modificacion/', {'motivo': 'Ajuste'}, format='json')
        self.autenticar(asistente)
        r = self.client.post(f'/api/programas-auditoria/{self.programa.pk}/aprobar/')
        self.assertEqual(r.status_code, 202)
        from esynapse_sig.models import SolicitudCambioEquipo
        sol = SolicitudCambioEquipo.objects.get(entidad='programa_auditoria', entidad_id=self.programa.pk, estado='pendiente')
        self.assertIn('revisión 1', sol.resumen)
        self.autenticar(self.gg)
        self.assertEqual(self.client.post(f'/api/solicitudes-auditoria/{sol.pk}/aprobar/', format='json').status_code, 200)
        self.programa.refresh_from_db()
        self.assertEqual((self.programa.estado, self.programa.revision), ('aprobado', 1))
