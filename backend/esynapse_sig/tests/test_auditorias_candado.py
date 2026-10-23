"""
M10 Auditorías — candado de aprobación e independencia del auditor.

- Aprobar el programa anual y cerrar el informe: quien tiene 'aprobar' lo hace
  directo; quien no, deja una solicitud pendiente que un aprobador aprueba,
  devuelve (para reenviar) o rechaza.
- Independencia: al agregar a alguien de la propia área auditada, el sistema
  avisa pero no bloquea.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Auditoria, ProgramaAuditoria, SolicitudCambioEquipo

from .flujo_auditoria import avanzar


class BaseCandadoAuditoria(CasoBase):

    def setUp(self):
        self.aprobador = self.crear_usuario('gerente')
        self.dar_permisos(self.aprobador, 'auditorias', 'leer', 'crear', 'editar', 'aprobar')
        self.asistente = self.crear_usuario('asistente_sig', area='Calidad')
        self.dar_permisos(self.asistente, 'auditorias', 'leer', 'crear', 'editar')
        self.lider = self.crear_usuario('lider', area='Calidad', cargo='Auditor líder')
        self.programa = ProgramaAuditoria.objects.create(anio=2026, created_by=self.asistente)
        # Un programa vacío no se aprueba: siempre con al menos una auditoría.
        self.aud_base = Auditoria.objects.create(programa=self.programa, areas_procesos='Metrología',
                                                 mes_programado=3, created_by=self.asistente)

    def _auditoria_en_informe(self, usuario):
        self.autenticar(usuario)
        r = self.client.post('/api/auditorias/', {'programa': self.programa.pk, 'normas_aplicables': ['sig_integrado'],
                                                  'areas_procesos': 'Logística y Metrología', 'mes_programado': 5}, format='json')
        aud = Auditoria.objects.get(pk=r.data['id'])
        # Quien conduce la auditoría figura como auditor líder (aprueba el plan).
        avanzar(self, aud, 'en_informe', lider=usuario)
        aud.refresh_from_db()
        self.assertEqual(aud.estado, 'en_informe')
        return aud


class PruebasCandadoPrograma(BaseCandadoAuditoria):

    def test_aprobador_aprueba_directo(self):
        self.autenticar(self.aprobador)
        r = self.client.post(f'/api/programas-auditoria/{self.programa.pk}/aprobar/')
        self.assertEqual(r.status_code, 200, r.data)
        self.programa.refresh_from_db()
        self.assertEqual(self.programa.estado, 'aprobado')
        self.assertEqual(self.programa.aprobado_por, self.aprobador)

    def test_sin_permiso_queda_pendiente_y_aprobador_lo_aprueba(self):
        self.autenticar(self.asistente)
        r = self.client.post(f'/api/programas-auditoria/{self.programa.pk}/aprobar/')
        self.assertEqual(r.status_code, 202, r.data)
        self.programa.refresh_from_db()
        self.assertEqual(self.programa.estado, 'borrador')
        sol = SolicitudCambioEquipo.objects.get(modulo='auditorias', entidad='programa_auditoria', entidad_id=self.programa.pk)
        self.assertEqual(sol.estado, 'pendiente')
        # No se duplica la solicitud
        r = self.client.post(f'/api/programas-auditoria/{self.programa.pk}/aprobar/')
        self.assertEqual(r.status_code, 400)
        # El aprobador la ve en su bandeja y la aprueba
        self.autenticar(self.aprobador)
        r = self.client.get('/api/solicitudes-auditoria/?estado=pendiente')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results'] if isinstance(r.data, dict) else r.data), 1)
        r = self.client.post(f'/api/solicitudes-auditoria/{sol.pk}/aprobar/', format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.programa.refresh_from_db()
        self.assertEqual(self.programa.estado, 'aprobado')
        self.assertEqual(self.programa.aprobado_por, self.aprobador)

    def test_programa_vacio_no_se_aprueba(self):
        vacio = ProgramaAuditoria.objects.create(anio=2027, created_by=self.aprobador)
        self.autenticar(self.aprobador)
        r = self.client.post(f'/api/programas-auditoria/{vacio.pk}/aprobar/')
        self.assertEqual(r.status_code, 400)

    def test_las_bandejas_no_se_mezclan_entre_modulos(self):
        self.autenticar(self.asistente)
        self.client.post(f'/api/programas-auditoria/{self.programa.pk}/aprobar/')
        self.dar_permisos(self.aprobador, 'equipos', 'leer', 'aprobar')
        self.autenticar(self.aprobador)
        r = self.client.get('/api/solicitudes-cambio-equipo/?estado=pendiente')
        self.assertEqual(len(r.data['results'] if isinstance(r.data, dict) else r.data), 0)


class PruebasCandadoInforme(BaseCandadoAuditoria):

    def test_cierre_sin_permiso_queda_pendiente_devolver_y_reenviar(self):
        aud = self._auditoria_en_informe(self.asistente)
        conclusiones = aud.conclusiones
        r = self.client.post(f'/api/auditorias/{aud.pk}/cerrar/', format='json')
        self.assertEqual(r.status_code, 202, r.data)
        aud.refresh_from_db()
        self.assertEqual(aud.estado, 'en_informe')
        sol = SolicitudCambioEquipo.objects.get(modulo='auditorias', entidad='informe_auditoria', entidad_id=aud.pk)

        self.autenticar(self.aprobador)
        r = self.client.post(f'/api/solicitudes-auditoria/{sol.pk}/devolver/', {'observaciones': 'Ampliar conclusiones'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

        self.autenticar(self.asistente)
        # Se corrige el informe (las conclusiones ya se comunicaron y no cambian)
        self.assertEqual(self.client.patch(f'/api/auditorias/{aud.pk}/', {'fortalezas': 'Ampliadas'}, format='json').status_code, 200)
        r = self.client.post(f'/api/solicitudes-auditoria/{sol.pk}/reenviar/', {'payload': {}}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

        self.autenticar(self.aprobador)
        r = self.client.post(f'/api/solicitudes-auditoria/{sol.pk}/aprobar/', format='json')
        self.assertEqual(r.status_code, 200, r.data)
        aud.refresh_from_db()
        self.assertEqual(aud.estado, 'cerrada')
        self.assertEqual(aud.conclusiones, conclusiones)
        self.assertEqual(aud.fortalezas, 'Ampliadas')

    def test_rechazar_deja_la_auditoria_en_informe(self):
        aud = self._auditoria_en_informe(self.asistente)
        self.client.post(f'/api/auditorias/{aud.pk}/cerrar/', {'conclusiones': 'x'}, format='json')
        sol = SolicitudCambioEquipo.objects.get(entidad='informe_auditoria', entidad_id=aud.pk)
        self.autenticar(self.aprobador)
        self.client.post(f'/api/solicitudes-auditoria/{sol.pk}/rechazar/', {'observaciones': 'no'}, format='json')
        aud.refresh_from_db()
        self.assertEqual(aud.estado, 'en_informe')

    def test_aprobador_cierra_directo(self):
        aud = self._auditoria_en_informe(self.aprobador)
        r = self.client.post(f'/api/auditorias/{aud.pk}/cerrar/', {'conclusiones': 'Conforme'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'cerrada')
        self.assertFalse(SolicitudCambioEquipo.objects.filter(modulo='auditorias').exists())


class PruebasIndependencia(BaseCandadoAuditoria):

    def test_avisa_si_el_auditor_pertenece_al_area_auditada(self):
        self.autenticar(self.aprobador)
        r = self.client.post('/api/auditorias/', {'programa': self.programa.pk, 'normas_aplicables': ['iso_9001'],
                                                  'areas_procesos': 'Calidad y Logística'}, format='json')
        aud_id = r.data['id']
        r = self.client.post(f'/api/auditorias/{aud_id}/agregar_integrante/', {'rol': 'auditor', 'usuario': self.lider.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn('aviso', r.data)
        self.assertIn('independencia', r.data['aviso'].lower())
        self.assertEqual(Auditoria.objects.get(pk=aud_id).equipo.count(), 1, 'se agrega igual: avisa, no bloquea')

    def test_no_avisa_si_el_area_es_distinta(self):
        self.autenticar(self.aprobador)
        r = self.client.post('/api/auditorias/', {'programa': self.programa.pk, 'normas_aplicables': ['iso_9001'],
                                                  'areas_procesos': 'Logística y Metrología'}, format='json')
        aud_id = r.data['id']
        r = self.client.post(f'/api/auditorias/{aud_id}/agregar_integrante/', {'rol': 'auditor', 'usuario': self.lider.pk}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('aviso', r.data)

    def test_observador_no_aplica_la_regla(self):
        self.autenticar(self.aprobador)
        r = self.client.post('/api/auditorias/', {'programa': self.programa.pk, 'normas_aplicables': ['iso_9001'],
                                                  'areas_procesos': 'Calidad'}, format='json')
        r = self.client.post(f'/api/auditorias/{r.data["id"]}/agregar_integrante/', {'rol': 'observador', 'usuario': self.lider.pk}, format='json')
        self.assertNotIn('aviso', r.data)
