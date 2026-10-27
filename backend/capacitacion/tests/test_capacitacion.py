"""
Capacitación e inducción, según el procedimiento de gestión del personal.

- El programa 2026 se carga aprobado por el Comité; agregar o corregir capacitaciones lo deja pendiente de una nueva
  aprobación (reprogramar fechas, no). El programa histórico no se modifica.
- La lista de asistencia no se cierra sin asistentes firmados (usuario o PIN, o la lista en papel), sin notas si hay
  evaluación, ni sin la contraseña de quien registra; al cerrarse, la capacitación del programa queda realizada.
  Nota ≥ 14 → certificado de aprobación; si no, de participación. Cerrada, no cambia.
- La eficacia se evalúa una vez, con evidencia; vence a los 6 meses.
- Inducción: cada parte se aprueba con 14; desaprobada se repite solo esa parte; completa con las tres.
"""
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from capacitacion.models import ItemPrograma, ProgramaCapacitacion, Sesion
from core.tests.base import CasoBase
from organizacion.models import Area, Puesto, Trabajador

CLAVE = CasoBase.CLAVE


class Base(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('asig_cap', cargo='Asistente SIG', sigla_cargo='ASIG')
        self.dar_permisos(self.sig, 'capacitacion', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.sig)
        self.area = Area.objects.get(nombre='Laboratorio de Masa y Volumen')
        met = Puesto.objects.get(nombre='Metrólogo')
        self.u1 = self.crear_usuario('metrologo_cap', cargo='Metrólogo', sigla_cargo='MET')
        self.t1 = Trabajador.objects.create(nombres='Luis', apellidos='Con Usuario', documento='45000001', puesto=met,
                                            area=self.area, usuario=self.u1)
        self.t2 = Trabajador.objects.create(nombres='Ana', apellidos='Sin Usuario', documento='45000002', puesto=met,
                                            area=self.area)
        self.p = ProgramaCapacitacion.objects.get(anio=2026)


class PruebasPrograma(Base):

    def test_carga_y_aprobacion(self):
        self.assertEqual(self.p.estado_aprobacion, 'aprobado')
        self.assertEqual(self.p.items.count(), 36, 'el Reglamento Interno de Trabajo reprogramado es una sola fila')
        self.assertEqual(self.p.items.filter(fecha_realizada__isnull=False).count(), 27)
        self.assertEqual(self.p.aprobacion['firmas'][1]['nombre'], 'Erika Vega Rondo')
        self.assertTrue(ProgramaCapacitacion.objects.get(anio=2025).historico)
        i = self.p.items.filter(fecha_realizada__isnull=True, cancelado=False).first()
        url = f'/api/cap-programas/{self.p.pk}'
        r = self.client.post(f'{url}/reprogramar/', {'id': i.pk, 'fecha': '2026-12-20', 'motivo': 'Agenda del expositor'},
                             format='json')
        self.assertEqual(r.data['estado_aprobacion'], 'aprobado', 'reprogramar no exige nueva aprobación')
        r = self.client.post(f'{url}/item/', {'tema': 'Primeros auxilios básicos', 'tipo': 'sst', 'alcance': 'todos',
                                              'fecha_programada': '2026-12-05', 'horas': 2}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado_aprobacion'], 'pendiente')
        self.assertEqual(self.client.get(f'{url}/pdf/').status_code, 200)
        h = ProgramaCapacitacion.objects.get(anio=2025)
        r = self.client.post(f'/api/cap-programas/{h.pk}/item/', {'tema': 'x', 'tipo': 'sst',
                                                                  'fecha_programada': '2025-12-05'}, format='json')
        self.assertIn('histórico', r.data['detail'])

    def test_capacitacion_dirigida_a_areas(self):
        i = self.p.items.filter(dirigido_texto='Metrología').first()
        self.assertTrue(i.aplica_a(self.t1), 'Metrología = laboratorios')
        rh = Trabajador.objects.create(nombres='Rosa', apellidos='RRHH', documento='45000009',
                                       puesto=Puesto.objects.get(nombre='Metrólogo'),
                                       area=Area.objects.get(nombre='Recursos Humanos'))
        self.assertFalse(i.aplica_a(rh))


class PruebasSesion(Base):

    def _sesion(self, **extra):
        i = self.p.items.filter(fecha_realizada__isnull=True, cancelado=False).first()
        datos = {'item': i.pk, 'tipo_actividad': 'capacitacion', 'temas': ['seguridad'], 'tema_tratado': i.tema,
                 'capacitador': 'Miryam Canaza', 'fecha': str(timezone.localdate()), 'duracion_horas': '1.5'}
        datos.update(extra)
        r = self.client.post('/api/cap-sesiones/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data, i

    def test_lista_de_asistencia_firmas_notas_y_cierre(self):
        s, item = self._sesion(con_evaluacion=True)
        url = f'/api/cap-sesiones/{s["id"]}'
        r = self.client.post(f'{url}/asistentes/', {'trabajadores': [self.t1.pk, self.t2.pk]}, format='json')
        a1, a2 = r.data['asistentes']
        self.assertEqual({a1['forma_firma'], a2['forma_firma']}, {'usuario', 'sin_pin'})
        self.assertIn('Falta la firma', self.client.post(f'{url}/cerrar/', {'password': CLAVE}, format='json')
                      .data['detail'])
        con_usuario = a1 if a1['forma_firma'] == 'usuario' else a2
        sin_usuario = a2 if con_usuario is a1 else a1
        r = self.client.post(f'{url}/firmar_asistente/', {'id': con_usuario['id'], 'clave_trabajador': 'mal'},
                             format='json')
        self.assertIn('Contraseña incorrecta', r.data['detail'])
        self.client.post(f'{url}/firmar_asistente/', {'id': con_usuario['id'], 'clave_trabajador': CLAVE}, format='json')
        self.client.post(f'{url}/firmar_asistente/', {'id': sin_usuario['id'], 'pin_nuevo': '4321',
                                                      'pin_confirmacion': '4321'}, format='json')
        self.assertIn('Falta la nota', self.client.post(f'{url}/cerrar/', {'password': CLAVE}, format='json')
                      .data['detail'])
        self.client.post(f'{url}/nota/', {'id': con_usuario['id'], 'nota': 15}, format='json')
        self.client.post(f'{url}/nota/', {'id': sin_usuario['id'], 'nota': 12}, format='json')
        r = self.client.post(f'{url}/cerrar/', {'password': CLAVE}, format='json')
        self.assertEqual(r.data['estado'], 'cerrada')
        cert = {a['id']: a['certificado'] for a in r.data['asistentes']}
        self.assertEqual((cert[con_usuario['id']], cert[sin_usuario['id']]), ('aprobacion', 'participacion'))
        self.assertIsNotNone(ItemPrograma.objects.get(pk=item.pk).fecha_realizada)
        self.assertEqual(self.client.patch(url + '/', {'tema_tratado': 'otro'}, format='json').status_code, 400)
        self.assertEqual(self.client.get(f'{url}/pdf/').status_code, 200)
        # Eficacia
        self.assertEqual(r.data['estado_eficacia'], 'pendiente')
        r = self.client.post(f'{url}/eficacia/', {'resultado': 'eficaz', 'password': CLAVE}, format='json')
        self.assertIn('evidencia', r.data['detail'])
        r = self.client.post(f'{url}/eficacia/', {'resultado': 'eficaz', 'comentario': 'Inspección posterior sin '
                                                  'observaciones', 'password': CLAVE}, format='json')
        self.assertEqual(r.data['estado_eficacia'], 'evaluada')
        sit = self.client.get(f'/api/cap-programas/situacion/?trabajador={self.t1.pk}').data[0]
        self.assertTrue(any(d['asistio'] for d in sit['detalle']))

    def test_duracion_se_calcula_con_las_horas(self):
        s, _ = self._sesion(hora_desde='10:50', hora_hasta='12:20', duracion_horas='5')
        self.assertEqual(s['duracion_horas'], '1.50', 'la duración sale de Desde y Hasta, no de lo digitado')
        r = self.client.patch(f'/api/cap-sesiones/{s["id"]}/', {'hora_hasta': '10:30'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('hora_hasta', r.data)
        s2, _ = self._sesion(duracion_horas='2')
        self.assertEqual(s2['duracion_horas'], '2.00', 'sin horas se acepta la duración indicada')

    def test_lista_en_papel_y_eficacia_vencida(self):
        s, _ = self._sesion(fecha='2026-01-10')
        url = f'/api/cap-sesiones/{s["id"]}'
        self.client.post(f'{url}/asistentes/', {'trabajadores': [self.t2.pk]}, format='json')
        self.client.post(f'{url}/lista_papel/', {'archivo': SimpleUploadedFile('l.pdf', b'%PDF-1.4', 'application/pdf')})
        r = self.client.post(f'{url}/cerrar/', {'password': CLAVE}, format='json')
        self.assertEqual(r.data['estado'], 'cerrada', r.data)
        self.assertEqual(r.data['asistentes'][0]['firma']['metodo'], 'papel')
        if timezone.localdate() > date(2026, 7, 10):
            self.assertEqual(Sesion.objects.get(pk=s['id']).estado_eficacia, 'vencida')


class PruebasContenidoInduccion(Base):
    """El contenido de la inducción se configura: cada cambio pide motivo, sube la versión y queda en el historial;
    los documentos se vinculan a la lista maestra (versión vigente); las inducciones ya creadas no cambian."""

    def test_cambios_versionados_enlaces_y_lista_maestra(self):
        from esynapse_sig.models import Documento, VersionDocumento
        pl = self.client.get('/api/cap-plantillas/').data[0]
        url = f'/api/cap-plantillas/{pl["id"]}/'
        r = self.client.post('/api/cap-inducciones/', {'trabajador': self.t2.pk}, format='json')
        parte_antes = next(p for p in r.data['partes'] if p['parte'] == pl['parte'])
        r = self.client.patch(url, {'temas': pl['temas'], 'documentos': pl['documentos'], 'preguntas': pl['preguntas'],
                                    'motivo': 'sin cambios'}, format='json')
        self.assertEqual(r.status_code, 400, 'reenviar el contenido cargado tal cual no crea una versión')
        temas = pl['temas'] + [{'grupo': 'Nuevo', 'tema': 'Uso del sistema', 'enlace': 'https://intranet/sistema'}]
        self.assertIn('motivo', self.client.patch(url, {'temas': temas}, format='json').data['detail'])
        r = self.client.patch(url, {'temas': [{'tema': 'X', 'enlace': 'intranet/sin-protocolo'}], 'motivo': 'x'},
                              format='json')
        self.assertEqual(r.status_code, 400, 'el enlace debe ser http(s)')
        doc = Documento.objects.create(codigo='DOC-PRUEBA', titulo='Reglamento de prueba', tipo='formato',
                                       created_by=self.sig)
        VersionDocumento.objects.create(documento=doc, version='04', estado='vigente', elaborado_por=self.sig,
                                        revisado_por=self.sig, aprobado_por=self.sig)
        self.assertIn(doc.pk, [d['id'] for d in self.client.get('/api/cap-plantillas/documentos_sig/').data])
        docs = pl['documentos'] + [{'documento_id': doc.pk}]
        r = self.client.patch(url, {'temas': temas, 'documentos': docs, 'motivo': 'Se agrega el uso del sistema'},
                              format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['version'], pl['version'] + 1)
        self.assertEqual(r.data['historial'][-1]['motivo'], 'Se agrega el uso del sistema')
        vinculado = r.data['documentos'][-1]
        self.assertEqual((vinculado['documento'], vinculado['codigo'], vinculado['version']),
                         ('Reglamento de prueba', 'DOC-PRUEBA', '04'))
        self.assertEqual(self.client.patch(url, {'temas': temas, 'motivo': 'otra vez'}, format='json').status_code,
                         400, 'sin cambios no hay versión nueva')
        ind = self.client.get(f'/api/cap-inducciones/').data[0]
        parte = next(p for p in ind['partes'] if p['parte'] == pl['parte'])
        self.assertEqual(len(parte['temas']), len(parte_antes['temas']), 'la inducción ya creada no cambia')
        nueva = self.client.post('/api/cap-inducciones/', {'trabajador': self.t1.pk}, format='json').data
        parte = next(p for p in nueva['partes'] if p['parte'] == pl['parte'])
        self.assertEqual(parte['temas'][-1]['enlace'], 'https://intranet/sistema')
        self.assertEqual(parte['documentos'][-1]['codigo'], 'DOC-PRUEBA')


class PruebasIntegridadInduccion(Base):
    """Lo que el cliente envía al guardar una parte no altera el contenido ni los puntos (la nota no se infla)."""

    def test_no_se_inflan_puntos_ni_se_cambia_el_contenido(self):
        ind = self.client.post('/api/cap-inducciones/', {'trabajador': self.t2.pk}, format='json').data
        url = f'/api/cap-inducciones/{ind["id"]}'
        parte = next(p for p in ind['partes'] if p['preguntas'])
        r = self.client.post(f'{url}/guardar_parte/', {'id': parte['id'], 'preguntas': [
            {'pregunta': 'x', 'puntos': 1, 'calificacion': 1}]}, format='json')
        self.assertEqual(r.status_code, 400, 'una lista distinta a la de la inducción se rechaza')
        trampa = [{**q, 'puntos': 1, 'calificacion': 1} for q in parte['preguntas']]
        r = self.client.post(f'{url}/guardar_parte/', {'id': parte['id'], 'preguntas': trampa}, format='json')
        guardada = next(p for p in r.data['partes'] if p['id'] == parte['id'])
        self.assertEqual([q['puntos'] for q in guardada['preguntas']], [q['puntos'] for q in parte['preguntas']])
        self.assertLess(float(guardada['nota']), 14, 'la nota se calcula sobre los puntos reales')
        r = self.client.post(f'{url}/guardar_parte/', {'id': parte['id'], 'evaluacion_url': 'javascript:alert(1)'},
                             format='json')
        self.assertEqual(r.status_code, 400)
        self.client.post(f'{url}/anular/', {'motivo': 'prueba'}, format='json')
        r = self.client.post(f'{url}/guardar_parte/', {'id': parte['id'], 'observaciones': 'x'}, format='json')
        self.assertEqual(r.status_code, 400, 'una inducción anulada no avanza')

    def test_consultas_con_anio_no_numerico(self):
        self.assertEqual(self.client.get('/api/cap-programas/anio/?anio=abc').status_code, 200)


class PruebasInduccion(Base):

    def test_tres_partes_repetir_desaprobada_y_completa(self):
        r = self.client.post('/api/cap-inducciones/', {'trabajador': self.t2.pk}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        ind = r.data
        url = f'/api/cap-inducciones/{ind["id"]}'
        self.assertEqual(len(ind['partes']), 3)
        self.assertEqual(self.client.post('/api/cap-inducciones/', {'trabajador': self.t2.pk}, format='json')
                         .status_code, 400, 'una inducción en proceso a la vez')
        pin = {'pin_nuevo': '2580', 'pin_confirmacion': '2580'}
        for parte in ind['partes']:
            temas = [{**t, 'incluido': True} for t in parte['temas']]
            datos = {'id': parte['id'], 'responsable': 'Responsable', 'fecha': '2026-10-01', 'temas': temas}
            if parte['preguntas']:
                nota_baja = parte['parte'] == 'especifica'
                datos['preguntas'] = [{**q, 'calificacion': (1 if nota_baja else q['puntos'])}
                                      for q in parte['preguntas']]
            else:
                datos['nota_directa'] = 18
            self.assertEqual(self.client.post(f'{url}/guardar_parte/', datos, format='json').status_code, 200)
            r = self.client.post(f'{url}/firmar_parte/', {'id': parte['id'], 'password': CLAVE, **pin}, format='json')
            self.assertEqual(r.status_code, 200, r.data)
            pin = {'pin': '2580'}
        estados = {p['parte']: p['estado'] for p in r.data['partes']}
        self.assertEqual(estados['especifica'], 'desaprobada')
        self.assertEqual(r.data['estado'], 'en_proceso')
        r = self.client.post(f'{url}/repetir_parte/', {'parte': 'especifica'}, format='json')
        nueva = next(p for p in r.data['partes'] if p['parte'] == 'especifica' and p['intento'] == 2)
        self.client.post(f'{url}/guardar_parte/', {'id': nueva['id'], 'responsable': 'Responsable',
                                                   'fecha': '2026-10-02',
                                                   'temas': [{**t, 'incluido': True} for t in nueva['temas']],
                                                   'preguntas': [{**q, 'calificacion': q['puntos']}
                                                                 for q in nueva['preguntas']]}, format='json')
        r = self.client.post(f'{url}/firmar_parte/', {'id': nueva['id'], 'password': CLAVE, 'pin': '2580'},
                             format='json')
        self.assertEqual(r.data['estado'], 'completa')
        self.assertEqual(self.client.get(f'{url}/pdf/').status_code, 200)
        resumen = self.client.get('/api/cap-programas/resumen/').data
        self.assertNotIn(self.t2.pk, [x['id'] for x in resumen['sin_induccion']])
        self.assertIn(self.t1.pk, [x['id'] for x in resumen['sin_induccion']])
