"""
Seguridad de usuarios y roles (revisión 2026-10-23):
- El rol de Administrador del Sistema solo lo asigna o retira el propietario (superusuario), por cualquier vía.
- Permisos y asignaciones de rol no se crean ni se borran físicamente por rutas sueltas.
- is_active no se cambia por PATCH (solo desactivar/reactivar, con sus protecciones); reactivar funciona.
- La matriz de permisos de un rol se reemplaza todo o nada.
- Una escritura sin operación declarada nunca se evalúa como lectura.
"""
from core.models import Permiso, Rol, RolUsuario
from core.permissions import PermisoModular
from core.tests.base import CasoBase


class PruebasEscalada(CasoBase):

    def setUp(self):
        self.dueno = self.crear_usuario('dueno', superusuario=True)
        self.gestor = self.crear_usuario('gestor')
        self.dar_permisos(self.gestor, 'usuarios', 'leer', 'crear', 'editar', 'eliminar')
        self.admin_rol = Rol.objects.create(nombre='Administrador del Sistema (prueba)', es_admin_sistema=True)
        self.autenticar(self.gestor)

    def test_no_se_asigna_el_rol_admin_sin_ser_propietario(self):
        r = self.client.post(f'/api/usuarios/{self.gestor.pk}/asignar_roles/',
                             {'roles': [self.admin_rol.pk]}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertFalse(RolUsuario.objects.filter(usuario=self.gestor, rol=self.admin_rol, is_active=True).exists())
        r = self.client.post('/api/usuarios/', {'username': 'nuevo', 'email': 'n@x.pe', 'area': 'A', 'cargo': 'C',
                                                'password': 'Larga.Clave.2026', 'roles': [self.admin_rol.pk]},
                             format='json')
        self.assertEqual(r.status_code, 400)

    def test_rutas_sueltas_de_permisos_y_asignaciones_son_de_consulta(self):
        r = self.client.post('/api/roles-usuarios/', {'usuario': self.gestor.pk, 'rol': self.admin_rol.pk},
                             format='json')
        self.assertEqual(r.status_code, 405)
        r = self.client.post('/api/permisos/', {'rol': self.admin_rol.pk, 'modulo': 'documentos',
                                                'operacion': 'leer'}, format='json')
        self.assertEqual(r.status_code, 405)
        p = Permiso.objects.filter(rol__usuarios_asignados__usuario=self.gestor).first()
        self.assertEqual(self.client.delete(f'/api/permisos/{p.pk}/').status_code, 405)

    def test_is_active_no_cambia_por_patch_y_reactivar_funciona(self):
        otro = self.crear_usuario('otro')
        self.client.patch(f'/api/usuarios/{otro.pk}/', {'is_active': False}, format='json')
        otro.refresh_from_db()
        self.assertTrue(otro.is_active)
        r = self.client.patch(f'/api/usuarios/{self.dueno.pk}/', {'first_name': 'X'}, format='json')
        self.assertEqual(r.status_code, 403, 'la cuenta del propietario solo la modifica él')
        self.assertEqual(self.client.delete(f'/api/usuarios/{otro.pk}/').status_code, 204)
        r = self.client.post(f'/api/usuarios/{otro.pk}/activar/')
        self.assertEqual(r.status_code, 200)
        otro.refresh_from_db()
        self.assertTrue(otro.is_active)

    def test_matriz_de_permisos_todo_o_nada(self):
        rol = Rol.objects.create(nombre='Lectores')
        Permiso.objects.create(rol=rol, modulo='documentos', operacion='leer')
        Permiso.objects.create(rol=rol, modulo='documentos', operacion='crear')
        r = self.client.patch(f'/api/roles/{rol.pk}/', {'permisos': [
            {'modulo': 'documentos', 'operacion': 'leer'}, {'modulo': 'documentos', 'operacion': 'leer'}]},
            format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(rol.permisos.count(), 2, 'un error no deja el rol sin permisos')

    def test_escritura_sin_operacion_declarada_exige_editar(self):
        class Vista:
            action = 'accion_nueva'

            def accion_nueva(self):
                pass
        self.assertEqual(PermisoModular._resolver_operacion(Vista(), 'POST'), 'editar')
        self.assertEqual(PermisoModular._resolver_operacion(Vista(), 'GET'), 'leer')

    def test_contrasena_debil_rechazada(self):
        r = self.client.post('/api/usuarios/', {'username': 'debil', 'email': 'd@x.pe', 'area': 'A', 'cargo': 'C',
                                                'password': '12345678'}, format='json')
        self.assertEqual(r.status_code, 400)
