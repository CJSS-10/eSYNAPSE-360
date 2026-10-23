"""
Organización y personal (núcleo): áreas, puestos y trabajadores comunes a todo el sistema.

- Cualquier usuario activo consulta los catálogos; crearlos o cambiarlos exige el permiso «organización».
- El usuario vinculado a un trabajador toma el cargo, la sigla y el área de su puesto (las firmas los usan).
- Nada se elimina: áreas y puestos se desactivan (sin dependientes activos); el trabajador se cesa.
- El perfil del puesto se versiona.
- Carga inicial: organigrama propuesto, puestos de SST y lista anterior de áreas y laboratorios.
"""
from core.tests.base import CasoBase
from core.models import Usuario
from organizacion.models import Area, Puesto, Trabajador
from sst.models import FilaIPERC


class BaseOrg(CasoBase):

    def setUp(self):
        self.admin_org = self.crear_usuario('rrhh_o', cargo='Coordinador Administrativo')
        self.dar_permisos(self.admin_org, 'organizacion', 'leer', 'crear', 'editar', 'eliminar')
        self.dar_permisos(self.admin_org, 'usuarios', 'leer', 'crear', 'editar')
        self.otro = self.crear_usuario('lector_o')
        self.autenticar(self.admin_org)
        self.lab = Area.objects.get(nombre='Laboratorio de Masa y Volumen')


class PruebasCatalogo(BaseOrg):

    def test_carga_inicial(self):
        self.assertEqual(Area.objects.get(nombre='Laboratorio de Masa y Volumen').padre.nombre, 'Gerencia Técnica')
        self.assertEqual(Puesto.objects.get(nombre='Gerente SIG').sigla, 'GSIG')
        self.assertEqual(Puesto.objects.get(nombre='Asistente SIG').reporta_a.nombre, 'Gerente SIG')
        self.assertEqual(Puesto.objects.filter(tipo='tercero').count(), 5)
        # Los puestos de SST quedaron enlazados al catálogo único.
        f = FilaIPERC.objects.filter(area='Laboratorio de Fuerza y Presión', todos_los_puestos=False).first()
        self.assertEqual({p.nombre for p in f.puestos.all()},
                         {'Supervisor de Laboratorio', 'Encargado de Laboratorio', 'Metrólogo'})
        self.assertEqual(f.unidad.nombre, 'Laboratorio de Fuerza y Presión')

    def test_lectura_para_todos_escritura_con_permiso(self):
        self.autenticar(self.otro)
        self.assertEqual(self.client.get('/api/org-puestos/').status_code, 200)
        self.assertEqual(self.client.post('/api/org-areas/', {'nombre': 'X'}, format='json').status_code, 403)

    def test_documento_solo_para_quien_gestiona(self):
        p = Puesto.objects.get(nombre='Metrólogo')
        r = self.client.post('/api/org-trabajadores/', {'nombres': 'Ana', 'apellidos': 'Ríos', 'documento': '12345678',
                                                        'puesto': p.pk, 'area': self.lab.pk}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['documento'], '12345678')
        self.autenticar(self.otro)
        self.assertNotIn('documento', self.client.get(f'/api/org-trabajadores/{r.data["id"]}/').data)

    def test_nombres_unicos_y_sin_ciclos(self):
        self.assertEqual(self.client.post('/api/org-areas/', {'nombre': 'gerencia sig'}, format='json').status_code, 400)
        gt = Area.objects.get(nombre='Gerencia Técnica')
        r = self.client.patch(f'/api/org-areas/{gt.pk}/', {'padre': self.lab.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        gg = Puesto.objects.get(nombre='Gerente General')
        r = self.client.patch(f'/api/org-puestos/{gg.pk}/', {'reporta_a': Puesto.objects.get(nombre='Metrólogo').pk},
                              format='json')
        self.assertEqual(r.status_code, 400)

    def test_desactivar_exige_sin_dependientes(self):
        p = Puesto.objects.get(nombre='Metrólogo')
        Trabajador.objects.create(nombres='Luis', apellidos='Paz', puesto=p)
        self.assertEqual(self.client.delete(f'/api/org-puestos/{p.pk}/').status_code, 400)
        gt = Area.objects.get(nombre='Gerencia Técnica')
        self.assertEqual(self.client.delete(f'/api/org-areas/{gt.pk}/').status_code, 400)
        nueva = Area.objects.create(nombre='Área temporal')
        self.assertEqual(self.client.delete(f'/api/org-areas/{nueva.pk}/').status_code, 204)
        nueva.refresh_from_db()
        self.assertFalse(nueva.is_active)

    def test_perfil_versionado(self):
        p = Puesto.objects.get(nombre='Metrólogo')
        r = self.client.patch(f'/api/org-puestos/{p.pk}/', {'educacion': 'Técnico o bachiller en ingeniería'},
                              format='json')
        self.assertEqual(r.data['version_perfil'], 1)
        r = self.client.patch(f'/api/org-puestos/{p.pk}/', {'sigla': 'met'}, format='json')
        self.assertEqual((r.data['version_perfil'], r.data['sigla']), (1, 'MET'))
        self.assertIn('Perfil del puesto (versión 1)', [h['accion'] for h in r.data['historial']])


class PruebasTrabajadorYUsuario(BaseOrg):

    def _trabajador(self, puesto='Gerente SIG', **extra):
        datos = {'nombres': 'César', 'apellidos': 'Prueba', 'puesto': Puesto.objects.get(nombre=puesto).pk}
        datos.update(extra)
        r = self.client.post('/api/org-trabajadores/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return Trabajador.objects.get(pk=r.data['id'])

    def test_usuario_toma_cargo_sigla_y_area_del_puesto(self):
        t = self._trabajador()
        r = self.client.post('/api/usuarios/', {'username': 'cesar_p', 'email': 'cesar_p@prueba.local',
                                                'first_name': 'César', 'trabajador': t.pk}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        u = Usuario.objects.get(username='cesar_p')
        self.assertEqual((u.cargo, u.sigla_cargo, u.area), ('Gerente SIG', 'GSIG', 'Gerencia SIG'))
        # Cambio de puesto → la firma cambia sola.
        gt = Puesto.objects.get(nombre='Gerente Técnico')
        r = self.client.patch(f'/api/org-trabajadores/{t.pk}/', {'puesto': gt.pk}, format='json')
        self.assertEqual(r.data['historial'][-1]['accion'], 'Cambio de puesto')
        u.refresh_from_db()
        self.assertEqual((u.cargo, u.sigla_cargo), ('Gerente Técnico', 'GT'))
        # Cambio de sigla del puesto → también.
        self.client.patch(f'/api/org-puestos/{gt.pk}/', {'sigla': 'GTEC'}, format='json')
        u.refresh_from_db()
        self.assertEqual(u.sigla_cargo, 'GTEC')

    def test_laboratorio_del_usuario(self):
        t = self._trabajador('Metrólogo', area=self.lab.pk)
        u = self.crear_usuario('metro_o')
        r = self.client.patch(f'/api/usuarios/{u.pk}/', {'trabajador': t.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        u.refresh_from_db()
        self.assertEqual((u.area, u.laboratorio), ('Gerencia Técnica', 'Laboratorio de Masa y Volumen'))

    def test_usuario_sin_trabajador_exige_area_y_cargo(self):
        r = self.client.post('/api/usuarios/', {'username': 'externo', 'email': 'ext@prueba.local'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post('/api/usuarios/', {'username': 'externo', 'email': 'ext@prueba.local',
                                                'area': 'Externo', 'cargo': 'Auditor externo'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)

    def test_un_trabajador_un_usuario(self):
        t = self._trabajador()
        u1, u2 = self.crear_usuario('u1_o'), self.crear_usuario('u2_o')
        self.client.patch(f'/api/usuarios/{u1.pk}/', {'trabajador': t.pk}, format='json')
        r = self.client.patch(f'/api/usuarios/{u2.pk}/', {'trabajador': t.pk}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_cese_desactiva_usuario_y_no_se_elimina(self):
        t = self._trabajador()
        u = self.crear_usuario('cesado_o')
        t.usuario = u
        t.save()
        url = f'/api/org-trabajadores/{t.pk}/'
        self.assertEqual(self.client.delete(url).status_code, 400)
        self.assertEqual(self.client.post(url + 'cesar/', {}, format='json').status_code, 400)
        r = self.client.post(url + 'cesar/', {'motivo': 'Renuncia', 'fecha': '2026-10-31'}, format='json')
        self.assertEqual(r.data['estado'], 'cesado')
        u.refresh_from_db()
        self.assertFalse(u.is_active)
        self.assertNotIn(t.pk, [x['id'] for x in self.client.get('/api/org-trabajadores/').data])
        r = self.client.post(url + 'reingresar/', {'fecha': '2027-01-02'}, format='json')
        self.assertEqual(r.data['estado'], 'activo')
