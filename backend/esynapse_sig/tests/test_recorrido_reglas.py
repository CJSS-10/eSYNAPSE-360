"""
Reglas que se agregaron tras el recorrido de prueba de todos los módulos.

Equipos: la próxima calibración es posterior a la calibración; fuera de
servicio exige motivo; un equipo dado de baja es de solo lectura (no se
calibra, no sale, no se reactiva); solo se reactiva un equipo fuera de
servicio; no hay dos salidas abiertas a la vez ni dos retornos de la misma.
Competencia: entrenamiento con método, tutor y al menos una actividad; quien
firma tiene alcance (y laboratorio si es por laboratorio); vigente con fecha;
una sola autorización activa por persona y método.
Documentos: un documento archivado no se firma ni versiona; el resumen de
cambios no puede ser la contraseña del usuario.
Hallazgos: el tablero cuenta solo los abiertos.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Documento, Equipo, Hallazgo, MetodoCalibracion, ProcesoEntrenamiento


class PruebasEquiposReglas(CasoBase):

    def setUp(self):
        self.u = self.crear_usuario('jefe_equipos')
        self.dar_permisos(self.u, 'equipos', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.u)
        self.eq = Equipo.objects.create(codigo='PR-01', nombre='Balanza de prueba', magnitud='masa',
                                        periodicidad_dias=365, created_by=self.u)
        self.base = f'/api/equipos/{self.eq.pk}'

    def _post(self, accion, datos=None):
        return self.client.post(f'{self.base}/{accion}/', datos or {}, format='json')

    def test_proxima_calibracion_posterior(self):
        r = self._post('registrar_calibracion', {'n_certificado': 'C-1', 'fecha_ultima_calibracion': '2027-01-01',
                                                 'fecha_proxima_calibracion': '2026-01-01'})
        self.assertEqual(r.status_code, 400)
        r = self._post('registrar_calibracion', {'n_certificado': 'C-1', 'fecha_ultima_calibracion': '2026-10-01'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['fecha_proxima_calibracion'], '2027-10-01')

    def test_fuera_de_servicio_y_reactivar(self):
        self.assertEqual(self._post('marcar_inoperativo').status_code, 400, 'sin motivo')
        self.assertEqual(self._post('reactivar').status_code, 400, 'un equipo operativo no se reactiva')
        self.assertEqual(self._post('marcar_inoperativo', {'motivo': 'Golpe'}).status_code, 200)
        self.assertEqual(self._post('reactivar').data['estado'], 'operativo')

    def test_baja_es_solo_lectura(self):
        self.assertEqual(self._post('dar_baja').status_code, 200)
        for accion, datos in (('registrar_calibracion', {'n_certificado': 'C-2', 'fecha_ultima_calibracion': '2026-10-01'}),
                              ('reactivar', {}), ('marcar_inoperativo', {'motivo': 'x'}),
                              ('registrar_movimiento', {'motivo': 'campo'}),
                              ('programar', {'tipo': 'calibracion', 'anio': 2027, 'meses': [3]})):
            r = self._post(accion, datos)
            self.assertEqual(r.status_code, 400, accion)
            self.assertIn('baja', str(r.data))
        self.eq.refresh_from_db()
        self.assertEqual(self.eq.estado, 'baja')

    def test_una_salida_abierta_y_un_retorno(self):
        self.assertEqual(self._post('registrar_movimiento', {'motivo': 'prestamo', 'destino': 'Lab'}).status_code, 200)
        self.assertEqual(self._post('registrar_movimiento', {'motivo': 'campo'}).status_code, 400)
        mov = self.eq.movimientos.get()
        self.assertEqual(self._post('registrar_retorno', {'movimiento_id': mov.pk}).status_code, 200)
        self.assertEqual(self._post('registrar_retorno', {'movimiento_id': mov.pk}).status_code, 400)
        self.assertEqual(self._post('registrar_movimiento', {'motivo': 'campo'}).status_code, 200)


class PruebasCompetenciaReglas(CasoBase):

    def setUp(self):
        self.u = self.crear_usuario('gerente_tecnico_r')
        self.dar_permisos(self.u, 'competencia_tecnica', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.u)
        self.m = MetodoCalibracion.objects.create(nombre='Calibración de balanzas', codigo='PC-001')
        # Entrenamiento superado: requisito para quedar vigente.
        ProcesoEntrenamiento.objects.create(usuario=self.u, metodo=self.m, estado='completado', created_by=self.u)

    def _aut(self, **extra):
        datos = {'usuario': self.u.pk, 'metodo': self.m.pk, 'funciones': ['ejecutar'], 'estado': 'vigente',
                 'fecha_autorizacion': '2026-10-20'}
        datos.update(extra)
        return self.client.post('/api/autorizaciones/', datos, format='json')

    def test_entrenamiento_requiere_metodo_tutor_y_actividad(self):
        r = self.client.post('/api/procesos-entrenamiento/', {'usuario': self.u.pk, 'tipo': 'entrenamiento'}, format='json')
        self.assertEqual(r.status_code, 400)
        for campo in ('metodo', 'tutor', 'checklist_entrenamiento'):
            self.assertIn(campo, r.data)
        r = self.client.post('/api/procesos-entrenamiento/', {
            'usuario': self.u.pk, 'metodo': self.m.pk, 'tutor': self.u.pk, 'tipo': 'entrenamiento',
            'checklist_entrenamiento': [{'actividad': 'Lectura del procedimiento', 'documento': 'PC-001'}]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)

    def test_firma_con_alcance_y_laboratorio(self):
        r = self._aut(funciones=['ejecutar', 'firmar'])
        self.assertIn('alcance_firma', r.data)
        r = self._aut(funciones=['firmar'], alcance_firma='laboratorio', laboratorio='')
        self.assertIn('laboratorio', r.data)
        r = self._aut(funciones=['firmar'], alcance_firma='laboratorio', laboratorio='Masa')
        self.assertEqual(r.status_code, 201, r.data)

    def test_vigente_con_fecha_y_sin_duplicados(self):
        r = self._aut(fecha_autorizacion=None)
        self.assertIn('fecha_autorizacion', r.data)
        self.assertEqual(self._aut().status_code, 201)
        r = self._aut()
        self.assertEqual(r.status_code, 400, 'segunda autorización activa del mismo método')
        self.assertIn('metodo', r.data)


class PruebasDocumentosReglas(CasoBase):

    def setUp(self):
        self.u = self.crear_usuario('asistente_sig_r')
        self.dar_permisos(self.u, 'documentos', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.u)
        self.doc = Documento.objects.create(codigo='SIG-PRO-98', titulo='Doc', tipo='procedimiento',
                                            archivado=True, created_by=self.u)

    def test_archivado_no_se_firma_ni_versiona(self):
        r = self.client.post(f'/api/documentos/{self.doc.pk}/enviar_revision/', {'password': self.CLAVE}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('archivado', str(r.data))

    def test_resumen_no_puede_ser_la_contrasena(self):
        Documento.objects.filter(pk=self.doc.pk).update(archivado=False)
        r = self.client.post(f'/api/documentos/{self.doc.pk}/nueva_version/', {'resumen_cambios': self.CLAVE},
                             format='multipart')
        self.assertEqual(r.status_code, 400)
        self.assertIn('contraseña', str(r.data))


class PruebasTableroHallazgos(CasoBase):

    def test_abiertos_excluye_cerrados(self):
        u = self.crear_usuario('lector_h')
        self.dar_permisos(u, 'hallazgos', 'leer')
        self.autenticar(u)
        Hallazgo.objects.create(tipo='nc_menor', fuente='otro', proceso='x', descripcion='a',
                                fecha_deteccion='2026-10-01', created_by=u)
        Hallazgo.objects.create(tipo='nc_menor', fuente='otro', proceso='x', descripcion='b', estado='cerrado',
                                fecha_deteccion='2026-10-01', created_by=u)
        r = self.client.get('/api/hallazgos/?abiertos=1')
        self.assertEqual(r.data['count'] if isinstance(r.data, dict) else len(r.data), 1)
