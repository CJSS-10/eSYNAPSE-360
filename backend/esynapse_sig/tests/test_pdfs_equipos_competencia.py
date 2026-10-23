"""
Humo de los PDF de Equipos (M13) y Competencia (M12): se generan y llevan la
caja de control con los datos del formato (regla: cada PDF imprime código,
versión, fecha y siglas de su formato).
"""
from io import BytesIO

import pdfplumber

from core.tests.base import CasoBase
from esynapse_sig.models import Autorizacion, Equipo, MetodoCalibracion


class PruebasPdfEquipos(CasoBase):

    def setUp(self):
        self.u = self.crear_usuario('supervisor', laboratorio='Masa')
        self.dar_permisos(self.u, 'equipos', 'leer', 'crear', 'editar', 'aprobar')
        self.autenticar(self.u)
        self.eq = Equipo.objects.create(codigo='M-001', nombre='Balanza patrón', laboratorio='Masa', created_by=self.u)

    def _pdf_texto(self, r):
        self.assertEqual(r.status_code, 200, getattr(r, 'data', r.content[:200]))
        self.assertEqual(r['Content-Type'], 'application/pdf')
        with pdfplumber.open(BytesIO(r.content)) as pdf:
            return pdf.pages[0].extract_text() or ''

    def test_hoja_de_vida(self):
        t = self._pdf_texto(self.client.get(f'/api/equipos/{self.eq.pk}/ficha_pdf/'))
        self.assertIn('MET-PRO-04-r01', t)
        self.assertIn('M-001', t)

    def test_bitacora(self):
        t = self._pdf_texto(self.client.get(f'/api/equipos/{self.eq.pk}/bitacora_pdf/?tipo=calibracion&titulo=Calibraciones'))
        self.assertIn('MET-PRO-04-r01', t)

    def test_inventario(self):
        t = self._pdf_texto(self.client.get('/api/equipos/inventario_pdf/'))
        self.assertIn('MET-PRO-04-r02', t)
        self.assertIn('2026-02-11', t)

    def test_programa_anual_equipos(self):
        t = self._pdf_texto(self.client.get('/api/equipos/programa_pdf/?anio=2026'))
        self.assertIn('MET-PRO-04-r03', t)


class PruebasPdfCompetencia(CasoBase):

    def test_autorizacion_pdf(self):
        gt = self.crear_usuario('gt', cargo='Gerente Técnico')
        self.dar_permisos(gt, 'competencia_tecnica', 'leer', 'crear', 'editar', 'aprobar')
        tec = self.crear_usuario('tecnico', cargo='Metrólogo', laboratorio='Masa')
        met = MetodoCalibracion.objects.create(nombre='Calibración de balanzas', magnitud='Masa')
        aut = Autorizacion.objects.create(usuario=tec, metodo=met, magnitud='Masa', funciones=['ejecutar'],
                                          estado='vigente', autorizado_por=gt, created_by=gt)
        self.autenticar(gt)
        r = self.client.get(f'/api/autorizaciones/{aut.pk}/autorizacion_pdf/')
        self.assertEqual(r.status_code, 200)
        with pdfplumber.open(BytesIO(r.content)) as pdf:
            t = pdf.pages[0].extract_text() or ''
        self.assertIn('MET-PRO-12-r02', t)
        self.assertIn('2026-02-11', t)
