"""
Revisión por la dirección (procedimiento versión 01):
- Programa anual con las 23 entradas y 10 salidas; meses ejecutados no futuros.
- Etapas: preparación → reunión → cerrada; lo de una etapa cerrada no se modifica (ADR-0005).
- Convocar exige datos generales y todas las entradas con análisis o «sin actividad».
- Cerrar exige conclusiones, salidas a–i, asistentes firmados con el Gerente SIG y el Gerente General, y contraseña.
- Acuerdos: se registran en la reunión con costo estimado; tras el cierre solo se sigue; cerrar exige evidencia y V°B°.
"""
from datetime import date, timedelta

from django.utils import timezone

from core.tests.base import CasoBase
from organizacion.models import Puesto, Trabajador
from revision import datos as fuentes
from revision.models import ENTRADAS, SALIDAS, Revision
from sst.tests.test_comite import texto_pdf

CLAVE = CasoBase.CLAVE


class Base(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gsig_rd', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'revision_direccion', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.sig)
        p_sig = Puesto.objects.get(nombre='Gerente SIG')
        p_gg = Puesto.objects.get(nombre='Gerente General')
        p_gt = Puesto.objects.get(nombre='Gerente Técnico')
        self.t_sig = Trabajador.objects.filter(usuario=self.sig).first() or Trabajador.objects.create(
            nombres='Gina', apellidos='SIG', documento='48000001', puesto=p_sig, usuario=self.sig)
        if self.t_sig.puesto_id != p_sig.pk:
            self.t_sig.puesto = p_sig
            self.t_sig.save()
        self.gg = self.crear_usuario('gg_rd')
        self.t_gg = Trabajador.objects.create(nombres='Gonzalo', apellidos='General', documento='48000002',
                                              puesto=p_gg, usuario=self.gg)
        self.t_gt = Trabajador.objects.create(nombres='Tomás', apellidos='Técnico', documento='48000003', puesto=p_gt)
        self.hoy = timezone.localdate()

    def _revision(self, **extra):
        datos = {'tipo': 'ordinaria', 'fecha': str(self.hoy), 'lugar': 'Sala de reuniones',
                 'periodo_desde': str(date(self.hoy.year, 1, 1)), 'periodo_hasta': str(self.hoy),
                 'responsable_recopilacion': self.t_sig.pk, 'responsable_verificacion': self.t_sig.pk}
        datos.update(extra)
        r = self.client.post('/api/rd-revisiones/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def _url(self, r, accion=''):
        return f'/api/rd-revisiones/{r["id"]}/' + (f'{accion}/' if accion else '')

    def _completar_entradas(self, r):
        for c, _ in ENTRADAS:
            self.client.post(self._url(r, 'entrada'), {'clave': c, 'analisis': f'Análisis {c}'}, format='json')

    def _en_reunion(self):
        r = self._revision()
        self._completar_entradas(r)
        res = self.client.post(self._url(r, 'convocar'), {}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        return res.data

    def _listo_para_cerrar(self, r):
        self.client.patch(self._url(r), {'conclusiones': 'El SIG es conveniente, adecuado y eficaz.'}, format='json')
        for c, _ in SALIDAS[:-1]:
            self.client.post(self._url(r, 'salida'), {'clave': c, 'texto': f'Decisión {c}'}, format='json')
        for t in (self.t_sig, self.t_gg):
            d = self.client.post(self._url(r, 'asistente'), {'trabajador': t.pk}, format='json').data
        for a in [x for x in d['asistentes'] if x['trabajador'] in (self.t_sig.pk, self.t_gg.pk)]:
            res = self.client.post(self._url(r, 'firmar_asistente'), {'id': a['id'], 'clave': CLAVE}, format='json')
            self.assertEqual(res.status_code, 200, res.data)
        return res.data


class PruebasPrograma(Base):

    def test_programa_anual_con_entradas_y_salidas(self):
        r = self.client.post('/api/rd-programas/', {'anio': self.hoy.year}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(len(r.data['items']), len(ENTRADAS) + len(SALIDAS))
        self.assertEqual(self.client.post('/api/rd-programas/', {'anio': self.hoy.year}, format='json').status_code,
                         400, 'uno por año')
        item = r.data['items'][0]
        url = f'/api/rd-programas/{r.data["id"]}/item/'
        ok = self.client.post(url, {'id': item['id'], 'meses': [3, 9], 'ejecutados': [1]}, format='json')
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(ok.data['items'][0]['meses'], [3, 9])
        self.assertEqual(self.client.post(url, {'id': item['id'], 'meses': [13]}, format='json').status_code, 400)
        if self.hoy.month < 12:
            self.assertEqual(self.client.post(url, {'id': item['id'], 'ejecutados': [12]}, format='json').status_code,
                             400, 'no se ejecuta un mes futuro')
        pdf = self.client.get(f'/api/rd-programas/{r.data["id"]}/pdf/')
        self.assertEqual(pdf.status_code, 200)
        self.assertIn('PROGRAMA DE REVISIÓN POR LA DIRECCIÓN', texto_pdf(pdf))


class PruebasRevision(Base):

    def test_registro_crea_entradas_y_salidas_y_codigo(self):
        r = self._revision()
        self.assertTrue(r['codigo'].startswith('IRD-01-'))
        self.assertEqual(len(r['entradas']), 23)
        self.assertEqual(len(r['salidas']), 10)
        self.assertEqual(self._revision()['codigo'], f'IRD-02-{self.hoy.year}')

    def test_extraordinaria_exige_motivo_y_periodo_coherente(self):
        r = self.client.post('/api/rd-revisiones/', {'tipo': 'extraordinaria'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('motivo_extraordinaria', r.data)
        r = self.client.post('/api/rd-revisiones/', {'periodo_desde': '2026-06-01', 'periodo_hasta': '2026-01-01'},
                             format='json')
        self.assertEqual(r.status_code, 400)

    def test_datos_del_sistema_para_todas_las_entradas(self):
        r = self._revision()
        res = self.client.post(self._url(r, 'generar_datos'), {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.data['datos_generados'])
        rev = Revision.objects.get(pk=r['id'])
        for c, _ in ENTRADAS:
            bloques = fuentes.generar(rev, c)
            self.assertTrue(bloques, f'entrada {c} sin bloques')
            for b in bloques:
                self.assertNotEqual(b['titulo'], 'No se pudieron obtener los datos', f'entrada {c}: {b["nota"]}')

    def test_convocar_exige_todas_las_entradas(self):
        r = self._revision()
        res = self.client.post(self._url(r, 'convocar'), {}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(len(res.data['entradas']), 23)
        self._completar_entradas(r)
        self.client.post(self._url(r, 'entrada'), {'clave': 'h', 'analisis': '', 'sin_actividad': True},
                         format='json')
        self.assertEqual(self.client.post(self._url(r, 'convocar'), {}, format='json').status_code, 200)

    def test_etapa_cerrada_solo_lectura(self):
        r = self._en_reunion()
        res = self.client.patch(self._url(r), {'lugar': 'Otro'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('preparación', res.data['detail'])
        self.assertEqual(self.client.post(self._url(r, 'entrada'), {'clave': 'a', 'analisis': 'x'},
                                          format='json').status_code, 400)
        self.assertEqual(self.client.patch(self._url(r), {'conclusiones': 'Bien'}, format='json').status_code, 200)

    def test_reunion_no_se_captura_por_adelantado(self):
        r = self._revision()
        res = self.client.patch(self._url(r), {'conclusiones': 'Adelantado'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('aún no se abre', res.data['detail'])

    def test_cierre_exige_firmas_de_gsig_y_gg(self):
        r = self._en_reunion()
        res = self.client.post(self._url(r, 'cerrar'), {'password': CLAVE}, format='json')
        self.assertEqual(res.status_code, 400)
        for txt in ('conclusiones', 'salidas', 'asistentes', 'Gerente SIG', 'Gerente General'):
            self.assertIn(txt, res.data['detail'])
        self.client.post(self._url(r, 'asistente'), {'trabajador': self.t_gt.pk}, format='json')
        d = self._listo_para_cerrar(r)
        gt = next(a for a in d['asistentes'] if a['trabajador'] == self.t_gt.pk)
        self.assertIsNone(gt['firma'] or None)
        res = self.client.post(self._url(r, 'cerrar'), {'password': CLAVE}, format='json')
        self.assertIn('Tomás Técnico', res.data['detail'], 'todos los asistentes firman')
        self.client.post(self._url(r, 'firmar_asistente'),
                         {'id': gt['id'], 'pin_nuevo': '2468', 'pin_confirmacion': '2468'}, format='json')
        self.assertEqual(self.client.post(self._url(r, 'cerrar'), {'password': 'mala'}, format='json').status_code, 400)
        res = self.client.post(self._url(r, 'cerrar'), {'password': CLAVE}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['estado'], 'cerrada')
        self.assertEqual(self.client.patch(self._url(r), {'conclusiones': 'x'}, format='json').status_code, 400)

    def test_firma_de_asistente_con_su_contrasena(self):
        r = self._en_reunion()
        d = self.client.post(self._url(r, 'asistente'), {'trabajador': self.t_gg.pk}, format='json').data
        a = d['asistentes'][0]
        self.assertEqual(a['sigla'], 'GG')
        self.assertEqual(self.client.post(self._url(r, 'firmar_asistente'), {'id': a['id'], 'clave': 'mala'},
                                          format='json').status_code, 400)
        self.assertEqual(self.client.post(self._url(r, 'asistente'), {'trabajador': self.t_gg.pk},
                                          format='json').status_code, 400, 'no se repite')

    def test_anular_antes_del_cierre(self):
        r = self._revision()
        self.assertEqual(self.client.post(self._url(r, 'anular'), {}, format='json').status_code, 400)
        res = self.client.post(self._url(r, 'anular'), {'motivo': 'Registrada por error'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(r['id'], [x['id'] for x in self.client.get('/api/rd-revisiones/').data])
        r2 = self._en_reunion()
        self.assertEqual(self.client.post(self._url(r2, 'anular'), {'motivo': 'Error'}, format='json').status_code, 200,
                         'en reunión, antes del cierre, también se anula')


class PruebasAcuerdos(Base):

    def _cerrada_con_acuerdo(self):
        r = self._en_reunion()
        res = self.client.post(self._url(r, 'acuerdo'), {
            'descripcion': 'Adquirir patrón de presión', 'elemento': 's-c', 'responsable': self.t_sig.pk,
            'fecha_compromiso': str(self.hoy - timedelta(days=1)), 'costo_estimado': '12500.50'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self._listo_para_cerrar(r)
        self.assertEqual(self.client.post(self._url(r, 'cerrar'), {'password': CLAVE}, format='json').status_code, 200)
        return r, res.data['acuerdos'][0]

    def test_acuerdo_exige_responsable_y_fecha(self):
        r = self._en_reunion()
        self.assertEqual(self.client.post(self._url(r, 'acuerdo'), {'descripcion': 'x'}, format='json').status_code,
                         400)
        self.assertEqual(self.client.post(self._url(r, 'acuerdo'), {
            'descripcion': 'x', 'responsable': self.t_sig.pk, 'fecha_compromiso': '2026-12-01',
            'costo_estimado': '-5'}, format='json').status_code, 400, 'costo no negativo')

    def test_seguimiento_y_cierre_con_evidencia(self):
        r, a = self._cerrada_con_acuerdo()
        self.assertEqual(a['costo_estimado'], '12500.50')
        url = f'/api/rd-acuerdos/{a["id"]}/'
        self.assertEqual(self.client.patch(url, {'descripcion': 'Otra cosa'}, format='json').status_code, 400,
                         'lo acordado no cambia tras el cierre')
        self.assertEqual(self.client.post(url + 'cerrar/', {'password': CLAVE}, format='json').status_code, 400,
                         'sin evidencia no se cierra')
        res = self.client.patch(url, {'seguimiento_1': 'Cotizaciones solicitadas', 'estado': 'en_proceso'},
                                format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['estado'], 'en_proceso')
        self.assertEqual(self.client.patch(url, {'estado': 'cerrado'}, format='json').status_code, 400)
        self.client.patch(url, {'evidencia': 'OC 123 y certificado del patrón'}, format='json')
        res = self.client.post(url + 'cerrar/', {'password': CLAVE}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['estado'], 'cerrado')
        self.assertEqual(self.client.patch(url, {'seguimiento_2': 'x'}, format='json').status_code, 400)

    def test_mis_tareas_y_vencido(self):
        r, a = self._cerrada_con_acuerdo()
        res = self.client.get('/api/mis-tareas/')
        t = [x for x in res.data['tareas'] if x['tipo'] == 'acuerdo_rd']
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0]['estado'], 'Vencido')

    def test_acuerdos_alimentan_la_siguiente_revision_y_pdfs(self):
        r, a = self._cerrada_con_acuerdo()
        nueva = Revision.objects.get(pk=self._revision()['id'])
        texto = str(fuentes.generar(nueva, 'd'))
        self.assertIn(r['codigo'], texto)
        inf = self.client.get(self._url(r, 'pdf'))
        self.assertEqual(inf.status_code, 200)
        txt = texto_pdf(inf)
        for frag in ('INFORME DE LA REVISIÓN POR LA DIRECCIÓN', r['codigo'], 'ASISTENTES', 'ACUERDOS',
                     'Adquirir patrón de presión', 'Gerente General', 'Gerente SIG'):
            self.assertIn(frag, txt)
        plan = self.client.get(self._url(r, 'plan_pdf'))
        self.assertEqual(plan.status_code, 200)
        self.assertIn('PLAN DE ACCIÓN', texto_pdf(plan))
        self.assertIn('12,500.50', texto_pdf(plan))
