"""
Autenticación y permisos granulares (núcleo).

Reglas que protegen estas pruebas:
- El acceso es con JWT y solo para usuarios activos.
- Sin permiso explícito sobre el módulo y la operación, la API responde 403.
- Un rol con solo 'leer' no puede crear.
- Los usuarios nunca se eliminan físicamente (soft delete).
"""
from core.models import Usuario
from core.tests.base import CasoBase


class PruebasAutenticacion(CasoBase):

    def test_login_devuelve_tokens(self):
        self.crear_usuario('ana')
        r = self.client.post('/api/auth/login/', {'username': 'ana', 'password': self.CLAVE}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)
        self.assertIn('refresh', r.data)

    def test_login_con_clave_incorrecta_falla(self):
        self.crear_usuario('ana')
        r = self.client.post('/api/auth/login/', {'username': 'ana', 'password': 'otra'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_usuario_inactivo_no_puede_entrar(self):
        u = self.crear_usuario('ana')
        u.is_active = False
        u.save()
        r = self.client.post('/api/auth/login/', {'username': 'ana', 'password': self.CLAVE}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_sin_token_no_hay_acceso(self):
        r = self.client.get('/api/equipos/')
        self.assertEqual(r.status_code, 401)


class PruebasPermisos(CasoBase):

    def test_sin_permiso_sobre_el_modulo_403(self):
        u = self.crear_usuario('ana')
        self.autenticar(u)
        r = self.client.get('/api/equipos/')
        self.assertEqual(r.status_code, 403)

    def test_con_permiso_leer_200(self):
        u = self.crear_usuario('ana')
        self.dar_permisos(u, 'equipos', 'leer')
        self.autenticar(u)
        r = self.client.get('/api/equipos/')
        self.assertEqual(r.status_code, 200)

    def test_permiso_leer_no_permite_crear(self):
        u = self.crear_usuario('ana')
        self.dar_permisos(u, 'equipos', 'leer')
        self.autenticar(u)
        r = self.client.post('/api/magnitudes-equipo/', {'nombre': 'Magnitud de prueba', 'prefijo': 'MP'}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_permiso_crear_permite_crear(self):
        u = self.crear_usuario('ana')
        self.dar_permisos(u, 'equipos', 'leer', 'crear')
        self.autenticar(u)
        r = self.client.post('/api/magnitudes-equipo/', {'nombre': 'Magnitud de prueba', 'prefijo': 'MP'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)

    def test_union_de_permisos_entre_roles(self):
        """Un usuario con varios roles tiene la unión de sus permisos."""
        u = self.crear_usuario('ana')
        self.dar_permisos(u, 'equipos', 'leer')
        self.dar_permisos(u, 'documentos', 'leer')
        self.assertTrue(u.tiene_permiso('equipos', 'leer'))
        self.assertTrue(u.tiene_permiso('documentos', 'leer'))
        self.assertFalse(u.tiene_permiso('equipos', 'crear'))

    def test_superusuario_accede_a_todo(self):
        su = self.crear_usuario('root', superusuario=True)
        self.autenticar(su)
        self.assertEqual(self.client.get('/api/equipos/').status_code, 200)
        self.assertEqual(self.client.get('/api/auditorias/').status_code, 200)


class PruebasSoftDelete(CasoBase):

    def test_eliminar_usuario_solo_lo_desactiva(self):
        su = self.crear_usuario('root', superusuario=True)
        u = self.crear_usuario('ana')
        self.autenticar(su)
        r = self.client.delete(f'/api/usuarios/{u.pk}/')
        self.assertIn(r.status_code, (200, 204))
        u.refresh_from_db()
        self.assertFalse(u.is_active)
        self.assertTrue(Usuario.objects.filter(pk=u.pk).exists())
