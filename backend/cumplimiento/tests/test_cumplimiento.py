"""
Reglas del M11 Cumplimiento:
- La matriz usa el catálogo de Auditorías: cláusulas para 9001/14001/45001, numerales e ítems de seguimiento para 17025.
- No aplica exige justificación; cumple o parcial exigen cómo se cumple o la evidencia; el proceso es uno principal.
- Las cláusulas comunes de la estructura de alto nivel se reflejan en las otras normas ISO (8.2 solo 14001 ↔ 45001).
- Cumple o parcial pasa a «en riesgo» con evidencia automática en alerta o con la evaluación de más de 12 meses.
- Grado de cumplimiento: cumple 100, parcial 50, no cumple 0; no aplica se excluye.
- Brecha → hallazgo solo desde parcial o no cumple y uno abierto por requisito.
- Otros requisitos: se registran, se evalúan y se dan de baja con motivo.
- Permisos: leer no evalúa; el corte exige aprobar.
"""
from datetime import timedelta

from django.utils import timezone

from core.tests.base import CasoBase
from cumplimiento.models import EvaluacionRequisito
from esynapse_sig.models import Equipo, Hallazgo, RequisitoNorma
from procesos.models import Proceso


class Base(CasoBase):

    def setUp(self):
        self.u = self.crear_usuario('sig_cum')
        self.dar_permisos(self.u, 'cumplimiento', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.u)
        self.proceso = Proceso.objects.filter(is_active=True, padre__isnull=True).first()

    def req(self, norma, codigo, bloque='requisitos'):
        return RequisitoNorma.objects.get(norma=norma, bloque=bloque, codigo=codigo, es_seccion=False)

    def evaluar(self, r, estado='cumple', **extra):
        datos = {'requisito': r.id, 'estado': estado, 'como_se_cumple': 'Procedimiento vigente', **extra}
        return self.client.post('/api/cumplimiento/evaluar/', datos, format='json')

    def fila(self, norma, r):
        filas = self.client.get(f'/api/cumplimiento/matriz/?norma={norma}').data['filas']
        return next(f for f in filas if f.get('requisito') == r.id)


class PruebasMatriz(Base):

    def test_catalogo_por_norma(self):
        d = self.client.get('/api/cumplimiento/matriz/?norma=iso_9001').data
        codigos = [f['codigo'] for f in d['filas'] if f['tipo'] == 'requisito']
        self.assertIn('7.2', codigos)
        self.assertNotIn('7.', codigos)          # los capítulos son títulos, no requisitos
        self.assertTrue(any(f['tipo'] == 'seccion' for f in d['filas']))
        d = self.client.get('/api/cumplimiento/matriz/?norma=iso_17025').data
        codigos = [f['codigo'] for f in d['filas'] if f['tipo'] == 'requisito']
        self.assertIn('6.4.7', codigos)
        self.assertIn('S7', codigos)            # ítem de seguimiento del organismo de acreditación

    def test_no_aplica_exige_justificacion_y_cumple_exige_sustento(self):
        r = self.req('iso_9001', '8.3')
        self.assertIn('Justifique', self.evaluar(r, 'no_aplica').data['detail'])
        self.assertEqual(self.evaluar(r, 'no_aplica', justificacion='No se diseñan productos').status_code, 200)
        r2 = self.req('iso_9001', '8.5')
        self.assertIn('cómo se cumple', self.evaluar(r2, 'cumple', como_se_cumple='').data['detail'])

    def test_proceso_debe_ser_principal(self):
        hijo = Proceso.objects.filter(is_active=True, padre__isnull=False).first()
        if hijo:
            r = self.evaluar(self.req('iso_9001', '8.5'), proceso=hijo.id)
            self.assertIn('proceso principal', r.data['detail'])
        self.assertEqual(self.evaluar(self.req('iso_9001', '8.5'), proceso=self.proceso.id).status_code, 200)

    def test_reflejo_de_clausulas_comunes(self):
        r = self.evaluar(self.req('iso_9001', '7.2'))
        self.assertEqual(len(r.data['reflejada_en']), 2)
        for n in ('iso_14001', 'iso_45001'):
            ev = EvaluacionRequisito.objects.get(requisito=self.req(n, '7.2'))
            self.assertEqual(ev.estado, 'cumple')
            self.assertIn('reflejada_desde', ev.historial[-1])
        # 8.2: solo entre 14001 y 45001
        r = self.evaluar(self.req('iso_14001', '8.2'))
        self.assertEqual(r.data['reflejada_en'], ['ISO 45001 / Ley 29783 8.2'])
        # sin reflejo si se desmarca, y nunca para 17025 ni cláusulas propias
        self.assertEqual(self.evaluar(self.req('iso_9001', '9.3'), reflejar=False).data['reflejada_en'], [])
        self.assertEqual(self.evaluar(self.req('iso_9001', '8.3')).data['reflejada_en'], [])

    def test_en_riesgo_por_evidencia_en_alerta_o_evaluacion_vencida(self):
        # 9.2 sin programa de auditorías aprobado del año → evidencia en alerta
        r = self.req('iso_9001', '9.2')
        self.evaluar(r, reflejar=False)
        f = self.fila('iso_9001', r)
        self.assertEqual(f['evidencias'][0]['nivel'], 'alerta')
        self.assertTrue(f['en_riesgo'])
        # 8.5 no tiene evidencia automática: solo pasa a riesgo cuando la evaluación vence
        r = self.req('iso_9001', '8.5')
        self.evaluar(r)
        self.assertFalse(self.fila('iso_9001', r)['en_riesgo'])
        EvaluacionRequisito.objects.filter(requisito=r).update(
            fecha_evaluacion=timezone.localdate() - timedelta(days=400))
        self.assertTrue(self.fila('iso_9001', r)['en_riesgo'])

    def test_equipo_vencido_alerta_17025(self):
        Equipo.objects.create(codigo='CUM-EQ-1', nombre='Termómetro patrón', laboratorio='Temperatura',
                              estado='operativo', requiere_calibracion=True,
                              fecha_proxima_calibracion=timezone.localdate() - timedelta(days=5))
        f = self.fila('iso_17025', self.req('iso_17025', '6.4.7'))
        self.assertEqual(f['evidencias'][0]['nivel'], 'alerta')
        self.assertIn('vencida', f['evidencias'][0]['texto'])

    def test_grado_de_cumplimiento(self):
        self.evaluar(self.req('iso_17025', '7.7.1'), 'cumple')
        self.evaluar(self.req('iso_17025', '7.7.2'), 'parcial')
        self.evaluar(self.req('iso_17025', '7.7.3'), 'no_cumple', como_se_cumple='')
        self.evaluar(self.req('iso_17025', '7.3.1'), 'no_aplica', justificacion='No se realiza muestreo')
        res = self.client.get('/api/cumplimiento/matriz/?norma=iso_17025').data['resumen']
        self.assertEqual(res['porcentaje'], 50.0)
        self.assertEqual(res['evaluados'], 3)
        self.assertEqual(res['no_aplica'], 1)


class PruebasSede(Base):
    """SIG completo y cada sede con su propia evaluación, independiente (César, 2026-10-27)."""

    def setUp(self):
        super().setUp()
        from organizacion.models import Sede
        self.ag = Sede.objects.create(nombre='Sede prueba A', codigo='SA')
        self.lv = Sede.objects.create(nombre='Sede prueba B', codigo='SB')

    def test_evaluacion_individual_por_sede(self):
        r = self.req('iso_45001', '8.1')
        self.assertIn('evidencia en Sede prueba A',
                      self.evaluar(r, sedes=[{'sede': self.ag.id, 'estado': 'cumple'}]).data['detail'])
        resp = self.evaluar(r, sedes=[{'sede': self.ag.id, 'estado': 'parcial', 'observacion': 'Falta señalización'}])
        self.assertEqual(resp.status_code, 200, resp.data)
        f = self.fila('iso_45001', r)
        self.assertEqual(f['evaluacion']['estado_sig'], 'cumple')            # el SIG completo no se contagia
        d = self.client.get('/api/cumplimiento/matriz/?norma=iso_45001').data
        self.assertEqual(d['resumen']['cumple'], 1)
        self.assertEqual(d['resumen_sedes'][str(self.ag.id)]['parcial'], 1)   # sede A: su propia evaluación
        self.assertEqual(d['resumen_sedes'][str(self.lv.id)]['evaluados'], 0)  # sede B: no hereda nada
        self.assertEqual(d['resumen_sedes'][str(self.lv.id)]['sin_evaluar'], d['resumen_sedes'][str(self.lv.id)]['total'])
        # la cláusula común se refleja con su evaluación por sede
        f14 = self.fila('iso_14001', self.req('iso_14001', '8.1'))
        self.assertEqual(f14['evaluacion']['sedes'][str(self.ag.id)]['estado'], 'parcial')
        t = self.client.get('/api/cumplimiento/tablero/').data
        sa = next(x for x in t['sedes'] if x['id'] == self.ag.id)
        self.assertEqual(next(n for n in sa['normas'] if n['norma'] == 'iso_45001')['porcentaje'], 50.0)
        self.assertEqual(next(n for n in t['normas'] if n['norma'] == 'iso_45001')['porcentaje'], 100.0)

    def test_hallazgo_con_sede_y_pdf(self):
        r = self.req('iso_14001', '8.2')
        self.evaluar(r, sedes=[{'sede': self.lv.id, 'estado': 'no_cumple', 'observacion': 'Sin simulacro'}])
        sin_sede = self.client.post('/api/cumplimiento/hallazgo/', {'requisito': r.id, 'tipo': 'nc_menor',
                                                                   'descripcion': 'x'}, format='json')
        self.assertIn('SIG completo', sin_sede.data['detail'])               # el SIG completo cumple
        h = self.client.post('/api/cumplimiento/hallazgo/', {'requisito': r.id, 'tipo': 'nc_menor', 'sede': self.lv.id,
                                                            'descripcion': 'Sin simulacro en la sede'}, format='json')
        self.assertEqual(h.status_code, 201, h.data)
        self.assertEqual(Hallazgo.objects.get(pk=h.data['hallazgo']).lugar, 'Sede prueba B')
        for q in ('', f'&sede={self.lv.id}'):
            p = self.client.get(f'/api/cumplimiento/pdf/?norma=todas{q}')
            self.assertEqual(p.status_code, 200)
            self.assertTrue(p.content.startswith(b'%PDF'))


class PruebasHallazgo(Base):

    def test_brecha_a_hallazgo(self):
        r = self.req('iso_9001', '8.5')
        self.evaluar(r, 'cumple')
        datos = {'requisito': r.id, 'tipo': 'nc_menor', 'descripcion': 'Falta evidencia'}
        self.assertIn('parcial o no cumple', self.client.post('/api/cumplimiento/hallazgo/', datos,
                                                              format='json').data['detail'])
        self.evaluar(r, 'parcial', proceso=self.proceso.id)
        resp = self.client.post('/api/cumplimiento/hallazgo/', datos, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        h = Hallazgo.objects.get(pk=resp.data['hallazgo'])
        self.assertEqual((h.fuente, h.tipo, h.requisito), ('seguimiento', 'nc_menor', 'ISO 9001 8.5'))
        self.assertEqual(h.proceso_catalogo, self.proceso)
        self.assertIn('ya tiene el hallazgo', self.client.post('/api/cumplimiento/hallazgo/', datos,
                                                               format='json').data['detail'])


class PruebasOtrosYPermisos(Base):

    def test_otros_requisitos(self):
        r = self.client.post('/api/cumplimiento-otros/', {
            'fuente': 'acreditacion', 'referencia': 'Directriz de prueba', 'codigo': '5.1',
            'texto': 'Usar el símbolo de acreditación según la directriz', 'norma': 'iso_17025'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        aid = r.data['id']
        filas = self.client.get('/api/cumplimiento/matriz/?norma=iso_17025').data['filas']
        self.assertTrue(any(f.get('adicional') == aid for f in filas))
        e = self.client.post('/api/cumplimiento/evaluar/', {'adicional': aid, 'estado': 'cumple',
                                                            'evidencia': 'Certificados revisados'}, format='json')
        self.assertEqual(e.status_code, 200, e.data)
        self.assertIn('motivo', self.client.post(f'/api/cumplimiento-otros/{aid}/baja/', {}, format='json')
                      .data['detail'])
        self.client.post(f'/api/cumplimiento-otros/{aid}/baja/', {'motivo': 'Directriz derogada'}, format='json')
        self.assertFalse(any(f.get('adicional') == aid for f in
                             self.client.get('/api/cumplimiento/matriz/?norma=iso_17025').data['filas']))

    def test_permisos(self):
        lector = self.crear_usuario('lector_cum')
        self.dar_permisos(lector, 'cumplimiento', 'leer', 'editar')
        self.autenticar(lector)
        self.assertEqual(self.client.get('/api/cumplimiento/tablero/').status_code, 200)
        self.assertEqual(self.client.post('/api/cumplimiento/corte/', {}, format='json').status_code, 403)
        solo = self.crear_usuario('solo_cum')
        self.dar_permisos(solo, 'cumplimiento', 'leer')
        self.autenticar(solo)
        self.assertEqual(self.evaluar(self.req('iso_9001', '8.5')).status_code, 403)

    def test_revision_por_la_direccion_muestra_el_cumplimiento(self):
        from revision.datos import p_desempeno
        self.evaluar(self.req('iso_9001', '8.5'))
        hoy = timezone.localdate()
        bloques = p_desempeno(None, hoy.replace(month=1, day=1), hoy)
        b = next(x for x in bloques if x['titulo'].startswith('Cumplimiento'))
        self.assertEqual(b['filas'][0][0], 'ISO 9001')
        self.assertIn('100.0 %', b['filas'][0][1])

    def test_corte(self):
        self.evaluar(self.req('iso_9001', '8.5'))
        r = self.client.post('/api/cumplimiento/corte/', {'observaciones': 'Corte de prueba'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['resultados']['iso_9001']['cumple'], 1)
        self.assertEqual(len(self.client.get('/api/cumplimiento/tablero/').data['cortes']), 1)
