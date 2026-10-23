"""
Ayudantes de los formatos PDF: hora en 12 horas y nombre de la empresa.
"""
from django.test import SimpleTestCase

from esynapse_sig.ficha_pdf import _hora_ampm, empresa_nombre


class _Cfg:
    def __init__(self, subtitulo, nombre_sistema='eSYNAPSE 360°'):
        self.subtitulo = subtitulo
        self.nombre_sistema = nombre_sistema


class PruebasAyudantesPdf(SimpleTestCase):

    def test_hora_en_formato_12_horas(self):
        self.assertEqual(_hora_ampm('08:00'), '08:00 a. m.')
        self.assertEqual(_hora_ampm('10:30'), '10:30 a. m.')
        self.assertEqual(_hora_ampm('12:00'), '12:00 p. m.')
        self.assertEqual(_hora_ampm('14:05'), '02:05 p. m.')
        self.assertEqual(_hora_ampm('00:15'), '12:15 a. m.')
        self.assertEqual(_hora_ampm('16:45:00'), '04:45 p. m.')
        # Texto que no es hora se respeta
        self.assertEqual(_hora_ampm('por confirmar'), 'por confirmar')
        self.assertEqual(_hora_ampm(''), '')
        self.assertEqual(_hora_ampm(None), '')

    def test_empresa_nunca_cae_al_nombre_del_producto(self):
        self.assertEqual(empresa_nombre(_Cfg('Metrindust S.A.C.')), 'Metrindust S.A.C.')
        self.assertEqual(empresa_nombre(_Cfg('')), 'LA EMPRESA')
        self.assertEqual(empresa_nombre(_Cfg('  '), vacio=''), '')
        self.assertEqual(empresa_nombre(None, vacio=''), '')
