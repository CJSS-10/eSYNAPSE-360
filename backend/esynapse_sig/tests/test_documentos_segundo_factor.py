"""
M6 Documentos — segundo factor de autenticación.

Regla: editar la ficha de un documento (y firmar una versión) exige confirmar
la contraseña del propio usuario. Sin contraseña o con una incorrecta, nada
se guarda. Esto sostiene la regla "nadie firma con credenciales de otro".
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Documento


class PruebasSegundoFactor(CasoBase):

    def setUp(self):
        self.editor = self.crear_usuario('editor')
        self.dar_permisos(self.editor, 'documentos', 'leer', 'crear', 'editar')
        self.doc = Documento.objects.create(codigo='SIG-PRO-99', titulo='Título original',
                                            tipo='procedimiento', created_by=self.editor)
        self.autenticar(self.editor)

    def _editar(self, datos):
        return self.client.post(f'/api/documentos/{self.doc.pk}/editar_ficha/', datos, format='json')

    def test_sin_contrasena_no_edita(self):
        r = self._editar({'titulo': 'Nuevo'})
        self.assertEqual(r.status_code, 400)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.titulo, 'Título original')

    def test_contrasena_incorrecta_no_edita(self):
        r = self._editar({'titulo': 'Nuevo', 'password': 'incorrecta'})
        self.assertEqual(r.status_code, 400)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.titulo, 'Título original')

    def test_contrasena_correcta_edita_y_registra_autor(self):
        r = self._editar({'titulo': 'Título corregido', 'password': self.CLAVE})
        self.assertEqual(r.status_code, 200, r.data)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.titulo, 'Título corregido')
        self.assertEqual(self.doc.updated_by, self.editor)

    def test_sin_permiso_editar_403(self):
        lector = self.crear_usuario('lector')
        self.dar_permisos(lector, 'documentos', 'leer')
        self.autenticar(lector)
        r = self._editar({'titulo': 'Nuevo', 'password': self.CLAVE})
        self.assertEqual(r.status_code, 403)
