"""
M7 Procesos.

- Carga inicial: catálogo del mapa y 18 fichas en versión 01 en elaboración.
- Solo la versión en elaboración se edita (etapa cerrada = solo lectura).
- Enviar, revisar y aprobar con contraseña; quien revisa ≠ quien elabora y
  quien aprueba ≠ quien revisa.
- Aprobar deja vigente, la anterior obsoleta y atiende los avisos.
- Nueva versión con motivo, sin otra en curso; copia el contenido.
- Aprobar un documento vinculado a un proceso crea el aviso.
- Los procesos escritos en Hallazgos y Documentos se vinculan al catálogo.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Documento, Hallazgo
from procesos.models import Actividad, Aviso, Ficha, Proceso, avisar_ficha_por_revisar


class BaseProcesos(CasoBase):

    def setUp(self):
        self.asig = self.crear_usuario('asistente_sig', cargo='Asistente SIG', sigla_cargo='ASIG')
        self.gsig = self.crear_usuario('gerente_sig', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.gg = self.crear_usuario('gerente_general', cargo='Gerente General', sigla_cargo='GG')
        for u in (self.asig, self.gsig, self.gg):
            self.dar_permisos(u, 'procesos', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.asig)
        self.met = Proceso.objects.get(nombre='Metrología')
        self.ficha = self.met.fichas.get(version='01')

    def _post(self, ficha, accion, datos=None, usuario=None):
        if usuario:
            self.autenticar(usuario)
        return self.client.post(f'/api/fichas-proceso/{ficha.pk}/{accion}/', datos or {}, format='json')

    def _aprobar_completa(self, ficha):
        self.assertEqual(self._post(ficha, 'enviar', {'password': self.CLAVE}, self.asig).status_code, 200)
        self.assertEqual(self._post(ficha, 'revisar', {'password': self.CLAVE}, self.gsig).status_code, 200)
        r = self._post(ficha, 'aprobar', {'password': self.CLAVE}, self.gg)
        self.assertEqual(r.status_code, 200, r.data)
        ficha.refresh_from_db()
        return ficha


class PruebasCargaYMapa(BaseProcesos):

    def test_carga_inicial(self):
        # 19 de la carga inicial + Recepción de Equipos y/o Instrumentos y Marketing (agregados con Riesgos).
        self.assertEqual(Proceso.objects.count(), 21)
        self.assertEqual(Proceso.objects.get(nombre='Recepción de Equipos y/o Instrumentos').padre.nombre, 'Metrología')
        self.assertEqual(Ficha.objects.filter(version='01', estado='borrador').count(), 18)
        sig = Proceso.objects.get(nombre='Sistema Integrado de Gestión')
        self.assertEqual(sig.subprocesos.count(), 9)
        self.assertFalse(sig.fichas.exists())
        primera = self.ficha.actividades.first()
        self.assertEqual(list(primera.proveedores.values_list('nombre', flat=True)), ['Comercial'])
        self.assertEqual(self.ficha.indicadores.count(), 2)

    def test_mapa_desde_el_catalogo(self):
        r = self.client.get('/api/procesos/mapa/')
        self.assertEqual(r.status_code, 200)
        bandas = {b['tipo']: [p['nombre'] for p in b['procesos']] for b in r.data['bandas']}
        self.assertEqual(bandas['operativo'], ['Comercial', 'Metrología'])
        self.assertIn('Facturación y Cobranzas', bandas['soporte'])
        # Un proceso nuevo aparece solo; uno desactivado desaparece.
        self.client.post('/api/procesos/', {'nombre': 'Logística', 'tipo': 'operativo', 'orden': 13}, format='json')
        self.client.delete(f'/api/procesos/{Proceso.objects.get(nombre="Compras").pk}/')
        r = self.client.get('/api/procesos/mapa/')
        bandas = {b['tipo']: [p['nombre'] for p in b['procesos']] for b in r.data['bandas']}
        self.assertIn('Logística', bandas['operativo'])
        self.assertNotIn('Compras', bandas['soporte'])
        self.assertTrue(Proceso.objects.filter(nombre='Compras', is_active=False).exists())

    def test_no_desactiva_con_subprocesos(self):
        sig = Proceso.objects.get(nombre='Sistema Integrado de Gestión')
        r = self.client.delete(f'/api/procesos/{sig.pk}/')
        self.assertEqual(r.status_code, 400)

    def test_pdfs(self):
        r = self.client.get(f'/api/fichas-proceso/{self.ficha.pk}/pdf/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))
        r = self.client.get('/api/procesos/mapa_pdf/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))


class PruebasEdicion(BaseProcesos):

    def test_edita_en_elaboracion_y_reemplaza_listas(self):
        acts = [{'actividad': 'Recepción', 'proveedores': [Proceso.objects.get(nombre='Comercial').pk],
                 'proveedor_otro': 'Cliente', 'clientes': [self.met.pk], 'salida': 'Equipo recibido'},
                {'actividad': 'Calibración', 'seccion': 'Ejecución'}]
        r = self.client.patch(f'/api/fichas-proceso/{self.ficha.pk}/', {'objetivo': 'Nuevo objetivo',
                                                                          'actividades': acts}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.ficha.actividades.count(), 2)
        # Las filas quitadas se dan de baja, no se borran.
        self.assertEqual(Actividad.todos.filter(ficha=self.ficha, is_active=False).count(), 11)
        self.assertEqual(r.data['actividades'][0]['proveedores_nombres'], ['Comercial'])

    def test_actividad_sin_descripcion(self):
        r = self.client.patch(f'/api/fichas-proceso/{self.ficha.pk}/', {'actividades': [{'actividad': ' '}]},
                              format='json')
        self.assertEqual(r.status_code, 400)

    def test_etapa_cerrada_solo_lectura(self):
        self._post(self.ficha, 'enviar', {'password': self.CLAVE})
        r = self.client.patch(f'/api/fichas-proceso/{self.ficha.pk}/', {'objetivo': 'Cambio'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('elaboración está cerrada', r.data['detail'])

    def test_segunda_ficha_por_post_rechazada(self):
        r = self.client.post('/api/fichas-proceso/', {'proceso': self.met.pk, 'objetivo': 'x'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_primera_ficha_de_proceso_nuevo(self):
        p = Proceso.objects.create(nombre='Logística', tipo='operativo')
        r = self.client.post('/api/fichas-proceso/', {'proceso': p.pk, 'objetivo': 'Recojo y entrega'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['version'], '01')


class PruebasFirmas(BaseProcesos):

    def test_enviar_exige_contrasena(self):
        self.assertEqual(self._post(self.ficha, 'enviar', {}).status_code, 400)
        self.assertEqual(self._post(self.ficha, 'enviar', {'password': 'mala'}).status_code, 400)
        r = self._post(self.ficha, 'enviar', {'password': self.CLAVE})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['estado'], 'en_revision')
        self.assertEqual(r.data['firmas'][0]['sigla'], 'ASIG')

    def test_enviar_exige_contenido(self):
        self.ficha.alcance = ''
        self.ficha.save()
        r = self._post(self.ficha, 'enviar', {'password': self.CLAVE})
        self.assertEqual(r.status_code, 400)
        self.assertIn('alcance', r.data['detail'])

    def test_quien_elabora_no_revisa_y_quien_revisa_no_aprueba(self):
        self._post(self.ficha, 'enviar', {'password': self.CLAVE})
        r = self._post(self.ficha, 'revisar', {'password': self.CLAVE}, self.asig)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._post(self.ficha, 'revisar', {'password': self.CLAVE}, self.gsig).status_code, 200)
        r = self._post(self.ficha, 'aprobar', {'password': self.CLAVE}, self.gsig)
        self.assertEqual(r.status_code, 400)

    def test_aprobar_deja_vigente_y_atiende_avisos(self):
        avisar_ficha_por_revisar(self.met, 'Cambió el procedimiento.')
        f = self._aprobar_completa(self.ficha)
        self.assertEqual(f.estado, 'vigente')
        self.assertEqual(len(f.hash_contenido), 64)
        self.assertEqual([x['rol'] for x in f.firmas], ['elaborado', 'revisado', 'aprobado'])
        a = Aviso.objects.get(proceso=self.met)
        self.assertTrue(a.atendido)
        self.assertEqual(a.ficha_atencion, f)

    def test_devolver_vuelve_a_elaboracion(self):
        self._post(self.ficha, 'enviar', {'password': self.CLAVE})
        self.assertEqual(self._post(self.ficha, 'devolver', {}, self.gsig).status_code, 400)
        r = self._post(self.ficha, 'devolver', {'comentarios': 'Falta el indicador de satisfacción.'}, self.gsig)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['estado'], 'borrador')
        self.assertEqual(r.data['firmas'], [])
        self.assertEqual(len(r.data['devoluciones']), 1)


class PruebasVersiones(BaseProcesos):

    def test_nueva_version(self):
        f = self._aprobar_completa(self.ficha)
        self.autenticar(self.asig)
        self.assertEqual(self._post(f, 'nueva_version', {}).status_code, 400)
        r = self._post(f, 'nueva_version', {'motivo': 'Entra la orden de trabajo en el sistema.'})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['version'], '02')
        self.assertEqual(len(r.data['actividades']), f.actividades.count())
        self.assertEqual(r.data['actividades'][0]['proveedores_nombres'], ['Comercial'])
        # Solo una en curso.
        self.assertEqual(self._post(f, 'nueva_version', {'motivo': 'Otra'}).status_code, 400)
        nueva = Ficha.objects.get(pk=r.data['id'])
        nueva = self._aprobar_completa(nueva)
        f.refresh_from_db()
        self.assertEqual(f.estado, 'obsoleta')
        self.assertEqual(nueva.estado, 'vigente')

    def test_nueva_version_solo_desde_vigente(self):
        self.assertEqual(self._post(self.ficha, 'nueva_version', {'motivo': 'x'}).status_code, 400)


class PruebasAvisos(BaseProcesos):

    def test_aprobar_documento_del_proceso_crea_aviso(self):
        from django.core.files.base import ContentFile
        from esynapse_sig.models import VersionDocumento
        from io import BytesIO
        from reportlab.pdfgen import canvas
        buf = BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, 'Procedimiento')
        c.save()
        self.dar_permisos(self.asig, 'documentos', 'leer', 'crear', 'editar', 'aprobar')
        self.dar_permisos(self.gsig, 'documentos', 'leer', 'crear', 'editar', 'aprobar')
        doc = Documento.objects.create(codigo='MET-PRO-99', titulo='Calibración de manómetros', tipo='procedimiento',
                                       proceso='Metrología')
        self.assertEqual(doc.proceso_catalogo, self.met)
        v = VersionDocumento(documento=doc, version='00', estado='en_aprobacion', elaborado_por=self.asig,
                             revisado_por=self.asig)
        v.archivo.save('p.pdf', ContentFile(buf.getvalue()), save=True)
        self.autenticar(self.gsig)
        r = self.client.post(f'/api/documentos/{doc.pk}/aprobar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        a = Aviso.objects.get(proceso=self.met)
        self.assertEqual(a.origen, 'documento')
        self.assertIn('MET-PRO-99', a.motivo)

    def test_descartar_aviso_con_motivo(self):
        a = avisar_ficha_por_revisar(self.met, 'Cambió el formato de recepción.')
        r = self.client.post(f'/api/avisos-proceso/{a.pk}/descartar/', {}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post(f'/api/avisos-proceso/{a.pk}/descartar/', {'motivo': 'No afecta la ficha.'},
                             format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['atendido'])


class PruebasCatalogoEnOtrosModulos(BaseProcesos):

    def test_hallazgo_se_vincula_por_nombre(self):
        h = Hallazgo.objects.create(tipo='nc_menor', fuente='otro', proceso='metrología', descripcion='x', fecha_deteccion='2026-10-01')
        self.assertEqual(h.proceso_catalogo, self.met)
        self.assertEqual(h.proceso, 'Metrología')
        h2 = Hallazgo.objects.create(tipo='nc_menor', fuente='otro', proceso='SIG', descripcion='x', fecha_deteccion='2026-10-01')
        self.assertEqual(h2.proceso_catalogo.nombre, 'Sistema Integrado de Gestión')
        h3 = Hallazgo.objects.create(tipo='nc_menor', fuente='otro', proceso='Laboratorio de Masa', descripcion='x', fecha_deteccion='2026-10-01')
        self.assertIsNone(h3.proceso_catalogo)
        self.assertEqual(h3.proceso, 'Laboratorio de Masa')

    def test_renombrar_proceso_actualiza_textos(self):
        h = Hallazgo.objects.create(tipo='nc_menor', fuente='otro', proceso='Metrología', descripcion='x', fecha_deteccion='2026-10-01')
        r = self.client.patch(f'/api/procesos/{self.met.pk}/', {'nombre': 'Metrología y Calibración'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        h.refresh_from_db()
        self.assertEqual(h.proceso, 'Metrología y Calibración')

    def test_vinculados_cuenta_nc_abiertas(self):
        Hallazgo.objects.create(tipo='nc_mayor', fuente='otro', proceso='Metrología', descripcion='x', fecha_deteccion='2026-10-01')
        r = self.client.get(f'/api/procesos/{self.met.pk}/vinculados/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['nc_abiertas'], 1)

    def test_resultado_de_indicador_y_semaforo(self):
        ind = self.ficha.indicadores.first()
        r = self.client.post('/api/resultados-indicador/', {'proceso': self.met.pk, 'indicador': ind.nombre,
                                                            'periodo': '2026-09-15', 'valor': '87 %',
                                                            'estado': 'en_riesgo'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['periodo'], '2026-09-01')
        r = self.client.post('/api/resultados-indicador/', {'proceso': self.met.pk, 'indicador': ind.nombre,
                                                            'periodo': '2026-09-01', 'valor': '90 %',
                                                            'estado': 'cumple'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.get('/api/procesos/mapa/')
        met = [p for b in r.data['bandas'] for p in b['procesos'] if p['nombre'] == 'Metrología'][0]
        self.assertEqual(met['semaforo'], 'en_riesgo')
