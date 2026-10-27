"""
Sedes (catálogo único de Organización y personal, decisión de César del 24-10-2026):

- La migración convierte la sede y el piso que las áreas tenían como texto en sedes y niveles del catálogo.
- Cada sede indica si sus instalaciones son propias o alquiladas (sin datos del arrendador ni del contrato).
- Una sola sede principal; una sede o un nivel con áreas o suministros activos no se desactiva.
- El nivel de un área o de un suministro pertenece a su sede.
"""
from organizacion.models import Area, Nivel, Sede

from .test_organizacion import BaseOrg


class PruebasSedes(BaseOrg):

    def test_conversion_de_los_textos_de_las_areas(self):
        operativa = Sede.objects.get(nombre='Sede operativa')
        self.assertTrue(Sede.objects.filter(nombre='Sede administrativa').exists())
        self.assertEqual(self.lab.sede, operativa)
        self.assertEqual(self.lab.nivel.nombre, 'Piso 3')
        self.assertEqual(sorted(operativa.niveles.values_list('nombre', flat=True)), ['Piso 1', 'Piso 2', 'Piso 3'])
        self.assertEqual(Area.objects.get(nombre='Gerencia Técnica').nivel, None)

    def test_reglas_de_la_sede(self):
        self.assertEqual(self.client.post('/api/org-sedes/', {'nombre': 'Sede X', 'tenencia': 'cedida'},
                                          format='json').status_code, 400, 'solo propia o alquilada')
        r = self.client.post('/api/org-sedes/', {'nombre': 'sede NORTE ', 'tenencia': 'alquilada', 'principal': True},
                             format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data['nombre'], r.data['tenencia_display']), ('sede NORTE', 'Alquilada'))
        self.assertEqual(self.client.post('/api/org-sedes/', {'nombre': 'Sede norte'}, format='json').status_code,
                         400, 'nombre único sin distinguir mayúsculas')
        otra = self.client.post('/api/org-sedes/', {'nombre': 'Sede sur', 'principal': True}, format='json').data
        self.assertFalse(Sede.objects.get(pk=r.data['id']).principal, 'solo una sede principal')
        self.assertTrue(Sede.objects.get(pk=otra['id']).principal)

    def test_niveles_suministros_y_bajas(self):
        operativa = Sede.objects.get(nombre='Sede operativa')
        admin = Sede.objects.get(nombre='Sede administrativa')
        p1 = Nivel.objects.get(sede=operativa, nombre='Piso 1')
        self.assertEqual(self.client.post('/api/org-niveles/', {'sede': operativa.pk, 'nombre': 'piso 1'},
                                          format='json').status_code, 400, 'nivel único por sede')
        r = self.client.post('/api/org-suministros/', {'sede': admin.pk, 'nivel': p1.pk, 'tipo': 'energia'},
                             format='json')
        self.assertIn('nivel', r.data, 'el nivel es de otra sede')
        r = self.client.post('/api/org-suministros/', {'sede': operativa.pk, 'nivel': p1.pk, 'tipo': 'agua',
                                                       'numero': 'M-01'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['unidad'], 'm³')
        # Un área toma la sede de su nivel; un nivel de otra sede se rechaza.
        r = self.client.patch(f'/api/org-areas/{self.lab.pk}/', {'nivel': p1.pk}, format='json')
        self.assertEqual(r.data['sede_nombre'], 'Sede operativa')
        r = self.client.patch(f'/api/org-areas/{self.lab.pk}/', {'sede': admin.pk, 'nivel': p1.pk}, format='json')
        self.assertIn('nivel', r.data)
        r = self.client.patch(f'/api/org-areas/{self.lab.pk}/', {'sede': admin.pk}, format='json')
        self.assertIsNone(r.data['nivel'], 'al cambiar de sede se limpia el nivel de la anterior')
        # No se desactiva lo que tiene dependientes activos.
        self.assertIn('áreas activas', self.client.delete(f'/api/org-sedes/{operativa.pk}/').data['detail'])
        n = self.client.post('/api/org-niveles/', {'sede': admin.pk, 'nombre': 'Azotea'}, format='json').data
        self.client.post('/api/org-suministros/', {'sede': admin.pk, 'nivel': n['id'], 'tipo': 'energia'},
                         format='json')
        self.assertIn('suministros', self.client.delete(f'/api/org-niveles/{n["id"]}/').data['detail'])

    def test_ubigeo_completo_y_ubicacion_de_la_sede(self):
        from core.models import Ubigeo
        self.assertEqual(Ubigeo.objects.count(), 1893)
        self.assertEqual(Ubigeo.objects.values('departamento').distinct().count(), 25)
        self.assertEqual(Ubigeo.objects.values('departamento', 'provincia').distinct().count(), 196)
        lista = self.client.get('/api/ubigeos/').data
        self.assertIn(['150111', 'Lima', 'Lima', 'El Agustino'], lista)
        operativa = Sede.objects.get(nombre='Sede operativa')
        r = self.client.patch(f'/api/org-sedes/{operativa.pk}/', {'ubigeo': '150111', 'distrito': 'otro'},
                              format='json')
        self.assertEqual((r.data['distrito'], r.data['provincia'], r.data['departamento']),
                         ('El Agustino', 'Lima', 'Lima'), 'la ubicación sale del ubigeo, no se escribe a mano')

    def test_lectura_para_todos_escritura_con_permiso(self):
        self.autenticar(self.otro)
        self.assertEqual(self.client.get('/api/org-sedes/').status_code, 200)
        self.assertEqual(self.client.post('/api/org-sedes/', {'nombre': 'X'}, format='json').status_code, 403)
