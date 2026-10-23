"""
Configuración del sistema y versión instalada.
"""
import re

from core.tests.base import CasoBase


class PruebasConfiguracion(CasoBase):

    def test_config_publica_es_accesible_sin_login_y_trae_version(self):
        r = self.client.get('/api/configuracion/publica/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('version', r.data)
        self.assertRegex(r.data['version'], re.compile(r'^\d+\.\d+\.\d+'))
        self.assertIn('nombre_sistema', r.data)
        self.assertIn('modulos_habilitados', r.data)

    def test_config_publica_avisa_el_modo_pruebas(self):
        from django.test import override_settings
        self.assertFalse(self.client.get('/api/configuracion/publica/').data['modo_pruebas'])
        with override_settings(MODO_PRUEBAS=True):
            self.assertTrue(self.client.get('/api/configuracion/publica/').data['modo_pruebas'])

    def test_config_sistema_exige_administrador(self):
        u = self.crear_usuario('ana')
        self.autenticar(u)
        self.assertEqual(self.client.get('/api/configuracion/sistema/').status_code, 403)
        su = self.crear_usuario('root', superusuario=True)
        self.autenticar(su)
        r = self.client.get('/api/configuracion/sistema/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('direccion', r.data)
        self.assertIn('responsable_sig', r.data)

    def test_direccion_y_responsable_se_guardan(self):
        su = self.crear_usuario('root', superusuario=True)
        self.autenticar(su)
        r = self.client.patch('/api/configuracion/sistema/',
                              {'direccion': 'Av. Industrial 123', 'responsable_sig': 'Ing. Rosa Díaz'},
                              format='json')
        self.assertEqual(r.status_code, 200, r.data)
        r = self.client.get('/api/configuracion/sistema/')
        self.assertEqual(r.data['direccion'], 'Av. Industrial 123')
        self.assertEqual(r.data['responsable_sig'], 'Ing. Rosa Díaz')
