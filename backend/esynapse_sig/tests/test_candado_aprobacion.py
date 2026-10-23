"""
Candado de aprobación (control de cambios) — probado sobre Equipos (M13).

Reglas:
- Quien no tiene permiso de 'aprobar' no modifica directamente: su cambio queda
  como solicitud pendiente (respuesta 202) y el dato original no se toca.
- Aprobar aplica el cambio; rechazar lo descarta; devolver lo regresa al
  solicitante, que puede corregir y reenviar.
- Solo el creador reenvía; solo quien tiene 'aprobar' resuelve.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Equipo, SolicitudCambioEquipo


class PruebasCandado(CasoBase):

    def setUp(self):
        self.aprobador = self.crear_usuario('supervisor')
        self.dar_permisos(self.aprobador, 'equipos', 'leer', 'crear', 'editar', 'aprobar')
        self.solicitante = self.crear_usuario('metrologo')
        self.dar_permisos(self.solicitante, 'equipos', 'leer', 'crear', 'editar')
        self.equipo = Equipo.objects.create(codigo='M-001', nombre='Balanza patrón',
                                            observaciones='original', created_by=self.aprobador)

    def _solicitar_cambio(self, texto='propuesto'):
        self.autenticar(self.solicitante)
        r = self.client.patch(f'/api/equipos/{self.equipo.pk}/', {'observaciones': texto}, format='json')
        self.assertEqual(r.status_code, 202, r.data)
        self.assertTrue(r.data.get('pendiente'))
        return SolicitudCambioEquipo.objects.get(equipo=self.equipo, estado='pendiente')

    def test_sin_permiso_aprobar_el_cambio_queda_pendiente(self):
        sol = self._solicitar_cambio()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.observaciones, 'original')
        self.assertEqual(sol.operacion, 'editar')
        self.assertEqual(sol.created_by, self.solicitante)

    def test_con_permiso_aprobar_el_cambio_es_directo(self):
        self.autenticar(self.aprobador)
        r = self.client.patch(f'/api/equipos/{self.equipo.pk}/', {'observaciones': 'directo'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.observaciones, 'directo')
        self.assertFalse(SolicitudCambioEquipo.objects.exists())

    def test_aprobar_aplica_el_cambio(self):
        sol = self._solicitar_cambio('aprobado')
        self.autenticar(self.aprobador)
        r = self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/aprobar/', {'observaciones': 'ok'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        sol.refresh_from_db(); self.equipo.refresh_from_db()
        self.assertEqual(sol.estado, 'aprobada')
        self.assertEqual(sol.resuelto_por, self.aprobador)
        self.assertEqual(self.equipo.observaciones, 'aprobado')

    def test_rechazar_no_aplica_el_cambio(self):
        sol = self._solicitar_cambio('rechazado')
        self.autenticar(self.aprobador)
        r = self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/rechazar/', {'observaciones': 'no procede'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        sol.refresh_from_db(); self.equipo.refresh_from_db()
        self.assertEqual(sol.estado, 'rechazada')
        self.assertEqual(self.equipo.observaciones, 'original')

    def test_devolver_corregir_y_reenviar(self):
        sol = self._solicitar_cambio('v1')
        self.autenticar(self.aprobador)
        r = self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/devolver/', {'observaciones': 'falta detalle'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, 'devuelta')

        self.autenticar(self.solicitante)
        r = self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/reenviar/',
                             {'payload': {'observaciones': 'v2 corregida'}}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, 'pendiente')

        self.autenticar(self.aprobador)
        r = self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/aprobar/', format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.observaciones, 'v2 corregida')

    def test_solicitante_no_puede_aprobar(self):
        sol = self._solicitar_cambio()
        self.autenticar(self.solicitante)
        r = self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/aprobar/', format='json')
        self.assertEqual(r.status_code, 403)

    def test_solo_el_creador_reenvia(self):
        sol = self._solicitar_cambio()
        self.autenticar(self.aprobador)
        self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/devolver/', format='json')
        otro = self.crear_usuario('otro')
        self.dar_permisos(otro, 'equipos', 'leer', 'editar')
        self.autenticar(otro)
        r = self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/reenviar/', format='json')
        self.assertEqual(r.status_code, 400)

    def test_una_solicitud_resuelta_no_se_resuelve_dos_veces(self):
        sol = self._solicitar_cambio()
        self.autenticar(self.aprobador)
        self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/rechazar/', format='json')
        r = self.client.post(f'/api/solicitudes-cambio-equipo/{sol.pk}/aprobar/', format='json')
        self.assertEqual(r.status_code, 400)
