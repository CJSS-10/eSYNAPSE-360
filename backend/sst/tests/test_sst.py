"""
M23 SST — primera entrega: catálogo de puestos, matriz IPERC y ATS, según el
procedimiento de identificación de peligros, evaluación de riesgos y controles.

- Nivel de riesgo = (A+B+C+D) × S; T ≤4, TO 5–8, M 9–16, IM 17–24, IT ≥25; aceptable hasta M.
- Riesgo no aceptable sin controles o sin evaluación residual = «requiere control»;
  residual todavía no aceptable = «trabajo detenido».
- Las filas no se eliminan: se retiran con motivo; cada cambio queda en el historial.
- La revisión de la matriz de un área se firma con contraseña.
- ATS: se valida con firma del supervisor; exige etapas evaluadas y medidas; con riesgo
  intolerable no se valida; validado o anulado no se modifica.
- Carga inicial de la matriz en Excel.
"""
from core.tests.base import CasoBase
from django.core.files.uploadedfile import SimpleUploadedFile

from organizacion.models import Puesto
from sst.models import ATS, ATSTipo, FilaIPERC, nivel_ats, nivel_iperc


class BaseSST(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gerente_sig_s', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'sst', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.lector = self.crear_usuario('lector_s')
        self.dar_permisos(self.lector, 'sst', 'leer')
        self.autenticar(self.sig)

    def _fila(self, **extra):
        datos = {'area': 'Laboratorio de Prueba', 'actividad': 'Calibración de manómetros', 'peligro': 'Fluidos a presión',
                 'riesgo': 'Golpeado por fluidos a presión', 'situaciones': ['rutinaria'], 'personas': 2,
                 'procedimientos': 2, 'capacitacion': 2, 'exposicion': 3, 'severidad': 2}
        datos.update(extra)
        r = self.client.post('/api/sst-iperc/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return FilaIPERC.objects.get(pk=r.data['id'])


class PruebasEscalas(BaseSST):

    def test_niveles_iperc_y_ats(self):
        self.assertEqual([nivel_iperc(v) for v in (4, 5, 8, 9, 16, 17, 24, 25, 36)],
                         ['T', 'TO', 'TO', 'M', 'M', 'IM', 'IM', 'IT', 'IT'])
        self.assertEqual([nivel_ats(v) for v in (2, 3, 6, 8, 9, 12)],
                         ['tolerable', 'poco_significativo', 'poco_significativo', 'significativo', 'significativo',
                          'intolerable'])


class PruebasIPERC(BaseSST):

    def test_calculo_y_situacion_de_control(self):
        f = self._fila()
        res = self.client.get(f'/api/sst-iperc/{f.pk}/').data
        self.assertEqual((res['probabilidad'], res['nivel_riesgo'], res['clasificacion']), (9, 18, 'IM'))
        self.assertFalse(res['aceptable'])
        self.assertEqual(res['situacion_control'], 'requiere_control')
        res = self.client.patch(f'/api/sst-iperc/{f.pk}/', {
            'control_ingenieria': 'Guarda de protección', 'responsable': 'Encargado de laboratorio',
            'r_personas': 2, 'r_procedimientos': 2, 'r_capacitacion': 2, 'r_exposicion': 3, 'r_severidad': 2},
            format='json').data
        self.assertEqual((res['r_clasificacion'], res['situacion_control']), ('IM', 'trabajo_detenido'))
        res = self.client.patch(f'/api/sst-iperc/{f.pk}/', {'r_procedimientos': 1, 'r_capacitacion': 1,
                                                            'r_severidad': 1}, format='json').data
        self.assertEqual((res['r_clasificacion'], res['situacion_control']), ('TO', 'controlado'))
        self.assertIn('IM → TO', res['historial'][-1]['residual'])
        # Reenviar los mismos puestos no se registra como cambio.
        res = self.client.patch(f'/api/sst-iperc/{f.pk}/', {'puestos': [], 'responsable': 'Supervisor'},
                                format='json').data
        self.assertNotIn('Puestos', res['historial'][-1]['campos'])

    def test_escala_y_situacion_obligatoria(self):
        r = self.client.post('/api/sst-iperc/', {'area': 'X', 'actividad': 'a', 'peligro': 'p', 'riesgo': 'r',
                                                 'situaciones': ['rutinaria'], 'personas': 4}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post('/api/sst-iperc/', {'area': 'X', 'actividad': 'a', 'peligro': 'p', 'riesgo': 'r',
                                                 'situaciones': []}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_retiro_con_motivo_y_sin_eliminar(self):
        f = self._fila()
        self.assertEqual(self.client.delete(f'/api/sst-iperc/{f.pk}/').status_code, 400)
        self.assertEqual(self.client.post(f'/api/sst-iperc/{f.pk}/retirar/', {}, format='json').status_code, 400)
        res = self.client.post(f'/api/sst-iperc/{f.pk}/retirar/', {'motivo': 'Actividad eliminada'}, format='json')
        self.assertEqual(res.data['estado'], 'retirado')
        self.assertEqual(self.client.patch(f'/api/sst-iperc/{f.pk}/', {'peligro': 'x'}, format='json').status_code, 400)
        codigos = [x['codigo'] for x in self.client.get('/api/sst-iperc/?area=Laboratorio de Prueba').data]
        self.assertNotIn(f.codigo, codigos)

    def test_proceso_es_el_principal(self):
        from procesos.models import Proceso
        sub = Proceso.objects.filter(padre__isnull=False).first()
        r = self.client.post('/api/sst-iperc/', {'area': 'X', 'actividad': 'a', 'peligro': 'p', 'riesgo': 'r',
                                                 'situaciones': ['rutinaria'], 'proceso': sub.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('principal', str(r.data['proceso']))
        self.assertFalse(FilaIPERC.objects.filter(proceso__padre__isnull=False).exists())
        self.assertFalse(Puesto.objects.filter(proceso__padre__isnull=False).exists())

    def test_lector_no_edita(self):
        f = self._fila()
        self.autenticar(self.lector)
        self.assertEqual(self.client.patch(f'/api/sst-iperc/{f.pk}/', {'peligro': 'x'}, format='json').status_code, 403)

    def test_revision_de_area_con_firma(self):
        self._fila()
        url = '/api/sst-iperc/revisar_area/'
        self.assertEqual(self.client.post(url, {'area': 'Laboratorio de Prueba'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'area': 'Laboratorio de Prueba', 'password': 'mala'},
                                          format='json').status_code, 400)
        r = self.client.post(url, {'area': 'Laboratorio de Prueba', 'password': self.CLAVE}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        area = [a for a in self.client.get('/api/sst-iperc/resumen/').data['areas']
                if a['area'] == 'Laboratorio de Prueba'][0]
        self.assertIsNotNone(area['ultima_revision'])

    def test_filtro_por_puesto_incluye_todos_los_puestos(self):
        p = Puesto.objects.get(nombre='Metrólogo')
        f1 = self._fila(puestos=[p.pk])
        f2 = self._fila(todos_los_puestos=True)
        f3 = self._fila(puestos=[Puesto.objects.get(nombre='Gerente General').pk])
        codigos = {x['codigo'] for x in self.client.get(f'/api/sst-iperc/?puesto={p.pk}&area=Laboratorio de Prueba').data}
        self.assertEqual(codigos, {f1.codigo, f2.codigo})
        self.assertNotIn(f3.codigo, codigos)


class PruebasATS(BaseSST):

    def _ats(self):
        r = self.client.post('/api/sst-ats/', {'zona': 'Planta del cliente', 'tarea': 'Calibración in situ de balanza',
                                               'ejecutantes': [{'nombre': 'Juan Pérez'}], 'tipos_trabajo': ['altura']},
                             format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return ATS.objects.get(pk=r.data['id'])

    def test_codigo_y_validacion(self):
        a = self._ats()
        self.assertRegex(a.codigo, r'^ATS-\d{3}-\d{4}$')
        url = f'/api/sst-ats/{a.pk}/'
        self.assertEqual(self.client.post(url + 'validar/', {'password': self.CLAVE}, format='json').status_code, 400)
        self.client.post(url + 'agregar_paso/', {'etapa': 'Traslado de pesas', 'peligros': 'Carga',
                                                 'riesgos': 'Sobreesfuerzo', 'severidad': 3, 'probabilidad': 3,
                                                 'medidas': 'Uso de carretilla'}, format='json')
        res = self.client.post(url + 'validar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('residuales', res.data['detail'])
        paso = a.pasos.get()
        self.client.post(url + 'editar_paso/', {'paso_id': paso.pk, 'r_severidad': 2, 'r_probabilidad': 1},
                         format='json')
        self.assertEqual(self.client.post(url + 'validar/', {'password': 'mala'}, format='json').status_code, 400)
        res = self.client.post(url + 'validar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['estado'], 'validado')
        self.assertEqual(res.data['firma_supervisor']['sigla'], 'GSIG')
        self.assertEqual(self.client.patch(url, {'zona': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url + 'agregar_paso/', {'etapa': 'x'}, format='json').status_code, 400)

    def test_quitar_etapa_renumera(self):
        a = self._ats()
        url = f'/api/sst-ats/{a.pk}/'
        for e in ('Uno', 'Dos', 'Tres'):
            self.client.post(url + 'agregar_paso/', {'etapa': e}, format='json')
        self.client.post(url + 'quitar_paso/', {'paso_id': a.pasos.get(etapa='Dos').pk}, format='json')
        res = self.client.post(url + 'agregar_paso/', {'etapa': 'Cuatro'}, format='json')
        self.assertEqual([(p['orden'], p['etapa']) for p in res.data['pasos']], [(1, 'Uno'), (2, 'Tres'), (3, 'Cuatro')])

    def test_intolerable_no_se_valida(self):
        a = self._ats()
        url = f'/api/sst-ats/{a.pk}/'
        self.client.post(url + 'agregar_paso/', {'etapa': 'Trabajo en techo', 'severidad': 4, 'probabilidad': 4,
                                                 'r_severidad': 4, 'r_probabilidad': 3, 'medidas': 'Arnés'},
                         format='json')
        res = self.client.post(url + 'validar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('intolerable', res.data['detail'])

    def test_escala_ats_y_anulacion(self):
        a = self._ats()
        url = f'/api/sst-ats/{a.pk}/'
        self.assertEqual(self.client.post(url + 'agregar_paso/', {'etapa': 'x', 'severidad': 5},
                                          format='json').status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 400)
        self.assertEqual(self.client.post(url + 'anular/', {}, format='json').status_code, 400)
        res = self.client.post(url + 'anular/', {'motivo': 'Cambiaron las condiciones'}, format='json')
        self.assertEqual(res.data['estado'], 'anulado')


class PruebasATSCampo(BaseSST):
    """ATS de trabajos en campo: preparación → en campo → recibido (con el ATS firmado) → revisado por SST."""

    PASOS = [{'etapa': 'Traslado de pesas', 'peligros': 'Carga', 'riesgos': 'Sobreesfuerzo', 'severidad': 3,
              'probabilidad': 3, 'medidas': 'Carretilla', 'r_severidad': 2, 'r_probabilidad': 1},
             {'etapa': 'Calibración', 'peligros': 'Postura', 'riesgos': 'Fatiga', 'severidad': 1,
              'probabilidad': 2, 'medidas': 'Pausas activas'}]

    def _tipo(self):
        r = self.client.post('/api/sst-ats-tipo/', {'nombre': 'Calibración de balanzas en planta',
                                                    'tipos_trabajo': ['izaje'], 'pasos': self.PASOS}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return ATSTipo.objects.get(pk=r.data['id'])

    def _ats(self, **extra):
        datos = {'lugar_ejecucion': 'campo', 'cliente': 'Cliente de prueba', 'zona': 'Planta del cliente',
                 'tarea': 'Calibración de balanza de plataforma', 'ejecutantes': [{'nombre': 'Juan Pérez'}]}
        datos.update(extra)
        r = self.client.post('/api/sst-ats/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return ATS.objects.get(pk=r.data['id'])

    def _archivo(self):
        return SimpleUploadedFile('ats_firmado.jpg', b'imagen', content_type='image/jpeg')

    def test_tipo_prellena_y_flujo_completo(self):
        t = self._tipo()
        a = self._ats(ats_tipo=t.pk)
        url = f'/api/sst-ats/{a.pk}/'
        d = self.client.get(url).data
        self.assertEqual(len(d['pasos']), 2)
        self.assertEqual(d['tipos_trabajo'], ['izaje'])
        self.assertEqual(self.client.post(url + 'validar/', {'password': self.CLAVE}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url + 'recibir/', {}, format='multipart').status_code, 400)
        res = self.client.post(url + 'enviar_a_campo/', {}, format='json')
        self.assertEqual(res.data['estado'], 'en_campo')
        # En campo: se transcribe lo que cambió (ejecutantes, etapas); la preparación queda cerrada.
        self.assertEqual(self.client.patch(url, {'zona': 'Otra'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'ejecutantes': [{'nombre': 'Juan Pérez'}, {'nombre': 'Ana Ríos'}]},
                                           format='json').status_code, 200)
        self.assertEqual(self.client.post(url + 'agregar_paso/', {'etapa': 'Retiro de pesas', 'severidad': 2,
                                                                  'probabilidad': 2, 'medidas': 'Guantes'},
                                          format='json').status_code, 201)
        self.assertEqual(self.client.post(url + 'recibir/', {}, format='multipart').status_code, 400)
        res = self.client.post(url + 'recibir/', {'evidencia': self._archivo(), 'observaciones': 'Sin novedades'},
                               format='multipart')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['estado'], 'recibido')
        self.assertTrue(res.data['evidencia_url'])
        self.assertEqual(self.client.post(url + 'agregar_paso/', {'etapa': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'comentarios': 'x'}, format='json').status_code, 400)
        # SST lo devuelve con observación y vuelve a recibirse.
        self.assertEqual(self.client.post(url + 'observar/', {}, format='json').status_code, 400)
        res = self.client.post(url + 'observar/', {'motivo': 'Falta la firma del cliente'}, format='json')
        self.assertEqual(res.data['estado'], 'en_campo')
        self.client.post(url + 'recibir/', {'evidencia': self._archivo()}, format='multipart')
        self.assertEqual(self.client.post(url + 'revisar/', {'password': 'mala'}, format='json').status_code, 400)
        res = self.client.post(url + 'revisar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data['estado'], res.data['firma_revision']['sigla']), ('revisado', 'GSIG'))
        self.assertEqual(self.client.post(url + 'anular/', {'motivo': 'x'}, format='json').status_code, 400)
        acciones = [h['accion'] for h in res.data['historial']]
        self.assertEqual(acciones, ['Preparación', 'Enviado a campo', 'Recepción', 'Devuelto con observación',
                                    'Recepción', 'Revisión de SST'])

    def test_formato_del_cliente(self):
        self.assertEqual(self.client.post('/api/sst-ats/', {'zona': 'Lab', 'tarea': 't', 'formato': 'cliente'},
                                          format='json').status_code, 400)
        a = self._ats(formato='cliente')
        url = f'/api/sst-ats/{a.pk}/'
        self.client.post(url + 'enviar_a_campo/', {}, format='json')
        self.assertEqual(self.client.post(url + 'agregar_paso/', {'etapa': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.get(url + 'pdf/').status_code, 400)
        self.client.post(url + 'recibir/', {'evidencia': self._archivo()}, format='multipart')
        res = self.client.post(url + 'revisar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(res.data['estado'], 'revisado')

    def test_revision_exige_etapas_y_observacion_si_intolerable(self):
        a = self._ats()
        url = f'/api/sst-ats/{a.pk}/'
        self.client.post(url + 'enviar_a_campo/', {}, format='json')
        self.client.post(url + 'recibir/', {'evidencia': self._archivo()}, format='multipart')
        res = self.client.post(url + 'revisar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Transcriba', res.data['detail'])
        self.client.post(url + 'observar/', {'motivo': 'Transcribir etapas'}, format='json')
        self.client.post(url + 'agregar_paso/', {'etapa': 'Techo', 'severidad': 4, 'probabilidad': 4,
                                                 'r_severidad': 4, 'r_probabilidad': 3, 'medidas': 'Arnés'},
                         format='json')
        self.client.post(url + 'recibir/', {}, format='multipart')
        res = self.client.post(url + 'revisar/', {'password': self.CLAVE}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('intolerable', res.data['detail'])
        res = self.client.post(url + 'revisar/', {'password': self.CLAVE, 'observaciones': 'Se registró hallazgo'},
                               format='json')
        self.assertEqual(res.data['estado'], 'revisado')

    def test_guardar_como_tipo_y_pendientes(self):
        from datetime import timedelta
        from django.utils import timezone
        t = self._tipo()
        a = self._ats(ats_tipo=t.pk, fecha=str(timezone.localdate() - timedelta(days=3)))
        url = f'/api/sst-ats/{a.pk}/'
        self.assertEqual(self.client.post(url + 'guardar_como_tipo/', {'nombre': t.nombre.upper()},
                                          format='json').status_code, 400)
        res = self.client.post(url + 'guardar_como_tipo/', {'nombre': 'Balanzas camioneras'}, format='json')
        self.assertEqual((res.status_code, len(res.data['pasos'])), (201, 2))
        self.client.post(url + 'enviar_a_campo/', {}, format='json')
        r = self.client.get('/api/sst-ats/resumen/').data
        self.assertEqual([p['codigo'] for p in r['sin_recibir']], [a.codigo])
        self.assertEqual(r['sin_recibir'][0]['dias'], 3)
        self.assertEqual(self.client.post('/api/sst-ats-tipo/', {'nombre': 'x', 'pasos': [{'etapa': 'a', 'severidad': 5}]},
                                          format='json').status_code, 400)


class PruebasCargaYReportes(BaseSST):

    def test_carga_inicial(self):
        self.assertEqual(FilaIPERC.objects.count(), 385)
        self.assertEqual(FilaIPERC.objects.filter(estado='vigente').count(), 353, 'sin las 32 filas del pie del formato')
        self.assertEqual(Puesto.objects.filter(tipo='tercero').count(), 5)
        corregidas = [f for f in FilaIPERC.objects.filter(estado='vigente') if len(f.historial) > 1]
        self.assertEqual(len(corregidas), 26)
        f = FilaIPERC.objects.filter(area='Laboratorio de Fuerza y Presión', todos_los_puestos=False).first()
        self.assertEqual({p.nombre for p in f.puestos.all()},
                         {'Supervisor de Laboratorio', 'Encargado de Laboratorio', 'Metrólogo'})

    def test_pdfs(self):
        a = ATS.objects.create(zona='Lab', tarea='Prueba')
        for url in ('/api/sst-iperc/matriz_pdf/?area=Alta Dirección', f'/api/sst-ats/{a.pk}/pdf/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertTrue(r.content.startswith(b'%PDF'))


class PruebasAlineacionOrganizacion(BaseSST):
    """SST usa Organización y personal: ejecutantes del ATS, responsables de controles y riesgos del trabajador."""

    def setUp(self):
        super().setUp()
        from organizacion.models import Area, Trabajador
        self.lab = Area.objects.get(nombre='Laboratorio de Fuerza y Presión')
        self.t = Trabajador.objects.create(nombres='Luis', apellidos='Paz', puesto=Puesto.objects.get(nombre='Metrólogo'),
                                           area=self.lab)

    def test_ejecutantes_trabajadores_o_externos(self):
        r = self.client.post('/api/sst-ats/', {'zona': 'Lab', 'tarea': 'Mantenimiento', 'ejecutantes': [
            {'trabajador': self.t.pk}, {'nombre': 'Técnico del cliente'}]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['ejecutantes'], [
            {'trabajador': self.t.pk, 'nombre': 'Luis Paz', 'puesto': 'Metrólogo'},
            {'trabajador': None, 'nombre': 'Técnico del cliente', 'puesto': ''}])
        r = self.client.post('/api/sst-ats/', {'zona': 'Lab', 'tarea': 'x', 'ejecutantes': [
            {'trabajador': self.t.pk}, {'trabajador': self.t.pk}]}, format='json')
        self.assertEqual(r.status_code, 400)
        self.t.estado = 'cesado'
        self.t.save()
        r = self.client.post('/api/sst-ats/', {'zona': 'Lab', 'tarea': 'x', 'ejecutantes': [{'trabajador': self.t.pk}]},
                             format='json')
        self.assertEqual(r.status_code, 400)

    def test_responsables_son_puestos(self):
        f = self._fila()
        gs = Puesto.objects.get(nombre='Gerente SIG')
        r = self.client.patch(f'/api/sst-iperc/{f.pk}/', {'responsables': [gs.pk]}, format='json')
        self.assertEqual(r.data['responsables_nombres'], ['Gerente SIG'])
        self.assertIn('Responsable(s) de los controles', r.data['historial'][-1]['campos'])
        # Carga: el texto de la matriz quedó enlazado a los puestos.
        fila = FilaIPERC.objects.filter(responsable='Alta Direccion\nGerente SIG').first()
        self.assertEqual({p.nombre for p in fila.responsables.all()}, {'Gerente General', 'Gerente SIG'})
        self.assertTrue(Puesto.objects.filter(nombre='Supervisor de SSOMA').exists())
        self.assertFalse(FilaIPERC.objects.filter(responsable__contains='+A').exists())

    def test_riesgos_del_trabajador(self):
        r = self.client.get(f'/api/sst-iperc/por_trabajador/?trabajador={self.t.pk}').data
        hojas = {f['hoja'] for f in r['filas']}
        self.assertIn('Laboratorio de Fuerza y Presión', hojas)
        self.assertIn('Comedor', hojas)  # lugares comunes: aplican a todos
        self.assertNotIn('Laboratorio de Masa y Volumen', hojas)  # su puesto, pero otra área
        self.assertGreater(len(r['filas']), 20)
        # Solo lectura para quien tiene SST.
        self.autenticar(self.lector)
        self.assertEqual(self.client.get(f'/api/sst-iperc/por_trabajador/?trabajador={self.t.pk}').status_code, 200)
