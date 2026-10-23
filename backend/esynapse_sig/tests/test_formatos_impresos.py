"""
Caja de control de los formatos impresos.

Regla: la versión, fecha y siglas que imprime cada PDF salen de la **versión
vigente del documento de la lista maestra** al que el formato está vinculado.
Sin vínculo, de la tabla de respaldo; y si tampoco, de Configuración.
"""
import datetime

from core.tests.base import CasoBase
from esynapse_sig.ficha_pdf import control_formato
from esynapse_sig.models import Documento, FormatoImpreso, VersionDocumento


class PruebasControlFormato(CasoBase):

    def setUp(self):
        self.asig = self.crear_usuario('asig', cargo='Asistente SIG', sigla_cargo='ASIG')
        self.gsig = self.crear_usuario('gsig', cargo='Gestor SIG', sigla_cargo='GSIG')
        self.gg = self.crear_usuario('gg', cargo='Gerente General', sigla_cargo='GG')

    def test_catalogo_cargado_con_los_formatos_del_sistema(self):
        claves = set(FormatoImpreso.objects.values_list('clave', flat=True))
        self.assertIn('auditoria_programa_anual', claves)
        self.assertIn('equipos_hoja_vida', claves)
        self.assertIn('competencia_autorizacion', claves)
        self.assertEqual(FormatoImpreso.objects.get(clave='auditoria_programa_anual').codigo_sgc, 'SIG-PRO-16-r01')

    def test_sin_vinculo_usa_la_tabla_de_respaldo(self):
        c = control_formato('SIG-PRO-16-r01')
        self.assertEqual((c['origen'], c['version'], c['fecha']), ('tabla', '02', '2026-01-12'))
        self.assertEqual((c['elaborado'], c['revisado'], c['aprobado']), ('ASIG', 'GSIG/GT', 'GG'))

    def test_codigo_desconocido_usa_valores_globales(self):
        c = control_formato('XX-PRO-99-r99')
        self.assertEqual(c['origen'], 'global')
        self.assertEqual(c['codigo'], 'XX-PRO-99-r99')

    def test_vinculado_a_lista_maestra_toma_la_version_vigente(self):
        doc = Documento.objects.create(codigo='SIG-PRO-16-r01', titulo='Programa anual de auditorías', tipo='formato',
                                       created_by=self.asig)
        VersionDocumento.objects.create(documento=doc, version='03', estado='vigente',
                                        elaborado_por=self.asig, revisado_por=self.gsig, aprobado_por=self.gg,
                                        fecha_vigencia=datetime.date(2026, 11, 1))
        fi = FormatoImpreso.objects.get(clave='auditoria_programa_anual')
        fi.documento = doc
        fi.save()
        c = control_formato('SIG-PRO-16-r01')
        self.assertEqual(c['origen'], 'lista_maestra')
        self.assertEqual(c['version'], '03')
        self.assertEqual(c['fecha'], '2026-11-01')
        self.assertEqual((c['elaborado'], c['revisado'], c['aprobado']), ('ASIG', 'GSIG', 'GG'))

    def test_sin_version_vigente_cae_al_respaldo(self):
        doc = Documento.objects.create(codigo='SIG-PRO-16-r02', titulo='Plan', tipo='formato', created_by=self.asig)
        VersionDocumento.objects.create(documento=doc, version='02', estado='borrador', elaborado_por=self.asig)
        fi = FormatoImpreso.objects.get(clave='auditoria_plan'); fi.documento = doc; fi.save()
        c = control_formato('SIG-PRO-16-r02')
        self.assertEqual(c['origen'], 'tabla')
        self.assertEqual(c['version'], '01')

    def test_firmante_sin_sigla_usa_la_sigla_de_respaldo(self):
        sin_sigla = self.crear_usuario('nuevo', cargo='Analista')
        doc = Documento.objects.create(codigo='SIG-PRO-16-r03', titulo='Acta apertura', tipo='formato', created_by=self.asig)
        VersionDocumento.objects.create(documento=doc, version='01', estado='vigente', elaborado_por=sin_sigla,
                                        revisado_por=self.gsig, aprobado_por=self.gg, fecha_vigencia=datetime.date(2026, 6, 1))
        fi = FormatoImpreso.objects.get(clave='auditoria_acta_apertura'); fi.documento = doc; fi.save()
        c = control_formato('SIG-PRO-16-r03')
        self.assertEqual(c['elaborado'], 'ASIG', 'respaldo de la tabla')
        self.assertEqual(c['revisado'], 'GSIG')

    def test_el_pdf_imprime_la_version_de_la_lista_maestra(self):
        import pdfplumber
        from io import BytesIO
        from esynapse_sig.models import ProgramaAuditoria
        from esynapse_sig.ficha_pdf import generar_programa_anual_pdf
        doc = Documento.objects.create(codigo='SIG-PRO-16-r01', titulo='Programa', tipo='formato', created_by=self.asig)
        VersionDocumento.objects.create(documento=doc, version='05', estado='vigente', elaborado_por=self.asig,
                                        revisado_por=self.gsig, aprobado_por=self.gg, fecha_vigencia=datetime.date(2027, 1, 15))
        fi = FormatoImpreso.objects.get(clave='auditoria_programa_anual'); fi.documento = doc; fi.save()
        prog = ProgramaAuditoria.objects.create(anio=2027, created_by=self.asig)
        with pdfplumber.open(BytesIO(generar_programa_anual_pdf(prog))) as pdf:
            texto = pdf.pages[0].extract_text()
        self.assertIn('05', texto)
        self.assertIn('2027-01-15', texto)


class PruebasApiFormatos(CasoBase):

    def test_lista_visible_para_autenticados_y_edicion_solo_administradores(self):
        u = self.crear_usuario('ana')
        self.autenticar(u)
        r = self.client.get('/api/formatos-impresos/')
        self.assertEqual(r.status_code, 200)
        datos = r.data['results'] if isinstance(r.data, dict) else r.data
        self.assertGreaterEqual(len(datos), 15)
        self.assertIn('control', datos[0])
        fi = FormatoImpreso.objects.get(clave='auditoria_plan')
        r = self.client.patch(f'/api/formatos-impresos/{fi.pk}/', {'documento': None}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_administrador_vincula_un_documento(self):
        su = self.crear_usuario('root', superusuario=True)
        doc = Documento.objects.create(codigo='SIG-PRO-16-r02', titulo='Plan', tipo='formato', created_by=su)
        VersionDocumento.objects.create(documento=doc, version='02', estado='vigente', elaborado_por=su,
                                        fecha_vigencia=datetime.date(2026, 9, 1))
        self.autenticar(su)
        fi = FormatoImpreso.objects.get(clave='auditoria_plan')
        r = self.client.patch(f'/api/formatos-impresos/{fi.pk}/', {'documento': doc.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['documento_codigo'], 'SIG-PRO-16-r02')
        self.assertEqual(r.data['control']['version'], '02')
        self.assertEqual(r.data['control']['origen'], 'lista_maestra')
