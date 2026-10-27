"""
Regla 3 (nunca borrar): firmas de documentos, filas de la hoja de vida, actividades del programa de equipos,
integrantes del equipo auditor y resultados del intervalo de calibración se dan de baja, no se borran
(revisión 2026-10-24). Las consultas normales ven solo lo vigente; `todos` conserva lo dado de baja.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import (ActividadPrograma, Documento, Equipo, FirmaVersion, PuntoIntervalo, RegistroEquipo,
                                 ResultadoIntervalo, VersionDocumento)
from esynapse_sig.views import aplicar_matriz_intervalo


class PruebasBajaLogica(CasoBase):

    def setUp(self):
        self.u = self.crear_usuario('dueno_bl', superusuario=True)
        self.autenticar(self.u)
        self.eq = Equipo.objects.create(codigo='BL-01', nombre='Balanza de prueba', laboratorio='Masa',
                                        created_by=self.u)

    def test_firma_anulada_se_conserva_y_se_puede_volver_a_firmar(self):
        doc = Documento.objects.create(codigo='DOC-BL', titulo='Prueba', tipo='formato', created_by=self.u)
        v = VersionDocumento.objects.create(documento=doc, version='01', estado='borrador', elaborado_por=self.u)
        f = FirmaVersion.objects.create(version=v, rol='elaborado', usuario=self.u, hash_archivo='x' * 64)
        f.anular('Se reemplazó el archivo de la versión', self.u)
        FirmaVersion.objects.create(version=v, rol='elaborado', usuario=self.u, hash_archivo='y' * 64)
        self.assertEqual(v.firmas.count(), 1)
        self.assertEqual(FirmaVersion.todos.filter(version=v).count(), 2)

    def test_fila_de_hoja_de_vida_se_da_de_baja(self):
        reg = RegistroEquipo.objects.create(equipo=self.eq, tipo='mantenimiento', numero_documento='MT-1')
        r = self.client.post(f'/api/equipos/{self.eq.pk}/eliminar_registro/', {'registro_id': reg.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(self.eq.registros.exists())
        self.assertFalse(RegistroEquipo.todos.get(pk=reg.pk).is_active)

    def test_actividad_retirada_del_programa_se_conserva(self):
        ActividadPrograma.objects.create(equipo=self.eq, tipo='mantenimiento', anio=2026, meses=[3])
        r = self.client.post(f'/api/equipos/{self.eq.pk}/programar/', {'tipo': 'mantenimiento', 'anio': 2026,
                                                                       'meses': []}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.eq.actividades.exists())
        self.assertEqual(ActividadPrograma.todos.filter(equipo=self.eq).count(), 1)

    def test_celda_vaciada_del_intervalo_se_reactiva_al_volver_a_llenarse(self):
        p = PuntoIntervalo.objects.create(equipo=self.eq, valor_nominal='100 g')
        celda = {'punto': p.pk, 'anio': 2025, 'resultado': 0.1, 'incertidumbre': 0.02, 'emp': 0.5}
        aplicar_matriz_intervalo(self.eq.pk, [celda], self.u)
        original = ResultadoIntervalo.objects.get(punto=p)
        aplicar_matriz_intervalo(self.eq.pk, [], self.u)
        self.assertFalse(ResultadoIntervalo.objects.filter(punto=p).exists())
        aplicar_matriz_intervalo(self.eq.pk, [{**celda, 'resultado': 0.2}], self.u)
        r = ResultadoIntervalo.objects.get(punto=p)
        self.assertEqual((r.pk, r.resultado), (original.pk, 0.2), 'un solo registro por punto y año')

    def test_anulados_visibles_y_restaurables(self):
        reg = RegistroEquipo.objects.create(equipo=self.eq, tipo='calibracion', numero_documento='CAL-9')
        self.client.post(f'/api/equipos/{self.eq.pk}/eliminar_registro/', {'registro_id': reg.pk}, format='json')
        d = self.client.get(f'/api/equipos/{self.eq.pk}/').data
        self.assertEqual([r['numero_documento'] for r in d['registros_anulados']], ['CAL-9'])
        self.assertTrue(d['registros_anulados'][0]['anulado_por'])
        r = self.client.post(f'/api/equipos/{self.eq.pk}/restaurar/', {'entidad': 'registro', 'id': reg.pk},
                             format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([x['numero_documento'] for x in r.data['registros']], ['CAL-9'])
        self.assertEqual(r.data['registros_anulados'], [])
        # Sin permiso de aprobar no se restaura
        tecnico = self.crear_usuario('tecnico_bl')
        self.dar_permisos(tecnico, 'equipos', 'leer', 'editar', 'eliminar')
        self.autenticar(tecnico)
        reg.is_active = False
        reg.save()
        r = self.client.post(f'/api/equipos/{self.eq.pk}/restaurar/', {'entidad': 'registro', 'id': reg.pk},
                             format='json')
        self.assertEqual(r.status_code, 403)

    def test_pdf_de_ficha_tecnica_solo_la_ficha(self):
        from pypdf import PdfReader
        from io import BytesIO
        RegistroEquipo.objects.create(equipo=self.eq, tipo='mantenimiento', numero_documento='MT-1')
        sola = PdfReader(BytesIO(self.client.get(f'/api/equipos/{self.eq.pk}/ficha_pdf/').content))
        completa = PdfReader(BytesIO(self.client.get(f'/api/equipos/{self.eq.pk}/ficha_pdf/?completa=1').content))
        self.assertLess(len(sola.pages), len(completa.pages), 'la ficha técnica se imprime sola')
