"""Archivos subidos solo para usuarios del sistema (César, 2026-10-24)."""
import os
import tempfile

from django.test import override_settings

from core.tests.base import CasoBase

CARPETA = tempfile.mkdtemp(prefix='media_prueba_')
os.makedirs(os.path.join(CARPETA, 'sst', 'emo'), exist_ok=True)
os.makedirs(os.path.join(CARPETA, 'config'), exist_ok=True)
with open(os.path.join(CARPETA, 'sst', 'emo', 'examen.pdf'), 'wb') as f:
    f.write(b'%PDF-1.4 examen')
with open(os.path.join(CARPETA, 'config', 'logo.png'), 'wb') as f:
    f.write(b'logo')


@override_settings(MEDIA_ROOT=CARPETA)
class PruebasArchivosProtegidos(CasoBase):

    def test_sin_sesion_no_se_ve_un_archivo(self):
        self.assertEqual(self.client.get('/media/sst/emo/examen.pdf').status_code, 403)

    def test_con_sesion_si_y_al_cerrar_no(self):
        u = self.crear_usuario('lector')
        self.autenticar(u)
        self.assertEqual(self.client.post('/api/auth/media/').status_code, 200)
        r = self.client.get('/media/sst/emo/examen.pdf')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), b'%PDF-1.4 examen')
        u.is_active = False
        u.save()
        self.assertEqual(self.client.get('/media/sst/emo/examen.pdf').status_code, 403, 'usuario desactivado')

    def test_cookie_falsificada_o_ruta_fuera_de_la_carpeta(self):
        self.client.cookies['esynapse_media'] = 'inventada'
        self.assertEqual(self.client.get('/media/sst/emo/examen.pdf').status_code, 403)
        u = self.crear_usuario('lector2')
        self.autenticar(u)
        self.client.post('/api/auth/media/')
        self.assertEqual(self.client.get('/media/../esynapse/settings.py').status_code, 404)

    def test_logos_publicos_para_la_pantalla_de_ingreso(self):
        self.assertEqual(self.client.get('/media/config/logo.png').status_code, 200)
