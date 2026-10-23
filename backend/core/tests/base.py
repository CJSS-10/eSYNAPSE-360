"""
Base común para las pruebas automáticas de eSYNAPSE 360.

Uso:
    from core.tests.base import CasoBase

    class PruebaX(CasoBase):
        def test_algo(self):
            u = self.crear_usuario('ana')
            self.dar_permisos(u, 'equipos', 'leer', 'crear')
            self.autenticar(u)
            r = self.client.get('/api/equipos/')
            self.assertEqual(r.status_code, 200)

Las pruebas corren contra una base de datos temporal que Django crea y
destruye en cada ejecución; nunca tocan la base de desarrollo.
"""
from rest_framework.test import APITestCase

from core.models import Permiso, Rol, RolUsuario, Usuario


class CasoBase(APITestCase):
    CLAVE = 'Clave.123'

    @classmethod
    def crear_usuario(cls, username, superusuario=False, **extra):
        """Crea un usuario activo con contraseña conocida (CasoBase.CLAVE)."""
        datos = {
            'email': f'{username}@prueba.local',
            'first_name': username.capitalize(),
            'last_name': 'Prueba',
            'area': extra.pop('area', 'Calidad'),
            'cargo': extra.pop('cargo', 'Analista'),
        }
        datos.update(extra)
        if superusuario:
            return Usuario.objects.create_superuser(username=username, password=cls.CLAVE, **datos)
        return Usuario.objects.create_user(username=username, password=cls.CLAVE, **datos)

    @classmethod
    def dar_permisos(cls, usuario, modulo, *operaciones):
        """Asigna al usuario un rol con las operaciones indicadas sobre el módulo."""
        rol, _ = Rol.objects.get_or_create(nombre=f'rol-{modulo}-{usuario.username}')
        for op in operaciones:
            Permiso.objects.get_or_create(rol=rol, modulo=modulo, operacion=op, defaults={'permitido': True})
        RolUsuario.objects.get_or_create(usuario=usuario, rol=rol)
        return rol

    def autenticar(self, usuario):
        self.client.force_authenticate(user=usuario)
