"""
Inspecciones de SST y monitoreos de agentes ocupacionales.

- Las 11 plantillas del procedimiento quedan cargadas; cada inspección copia la estructura de su plantilla.
- Inventario: código único por tipo, alertas de vencimiento, baja con motivo (no se elimina).
- Inspección: filas generadas según la familia; no se firma con respuestas faltantes ni con un «no conforme»
  sin acción, responsable y plazo; firmada queda de solo lectura; con acciones pendientes no se cierra hasta
  completarlas; el hallazgo se registra solo para los ítems elegidos y una sola vez.
- Criterio invertido («Requiere cambio»): la respuesta buena es la no conforme.
- Monitoreo: no se registra sin resultados frente al LMP, causas de las desviaciones, conclusiones e informe.
"""
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from core.tests.base import CasoBase
from organizacion.models import Area, Puesto, Trabajador
from sst.inspecciones import (ElementoSeguridad, Inspeccion, Monitoreo, PlantillaInspeccion, ProgramaMonitoreo,
                              RecomendacionMonitoreo)

CLAVE = CasoBase.CLAVE


class BaseInspecciones(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gsig_in', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'sst', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.sig)
        self.ext = PlantillaInspeccion.objects.get(codigo_formato='SIG-PRO-06-r02')
        hoy = timezone.localdate()
        self.e1 = ElementoSeguridad.objects.create(tipo='extintor', codigo='EXT-01', ubicacion='Recepción', piso='1°',
                                                   subtipo='PQS ABC', capacidad='6 kg',
                                                   fecha_vencimiento=hoy + timedelta(days=200))
        self.e2 = ElementoSeguridad.objects.create(tipo='extintor', codigo='EXT-02', ubicacion='Laboratorio de Masa',
                                                   piso='3°', fecha_vencimiento=hoy - timedelta(days=3))

    def _crear(self, plantilla, **extra):
        r = self.client.post('/api/sst-inspecciones/', {'plantilla': plantilla.pk, 'fecha': str(timezone.localdate()),
                                                        **extra}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def _url(self, ins, accion=''):
        return f'/api/sst-inspecciones/{ins["id"]}/' + (f'{accion}/' if accion else '')

    def _responder_todo(self, ins, valor, malos=()):
        n = len(ins['estructura']['criterios'])
        items = []
        for it in ins['items']:
            res = {str(k): valor for k in range(n)} if n else {'r': valor}
            if it['id'] in malos:
                res = dict(res, **({'0': malos[it['id']]} if n else {'r': malos[it['id']]}))
            items.append({'id': it['id'], 'resultados': res})
        r = self.client.post(self._url(ins, 'responder'), {'items': items}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return r.data


class PruebasCarga(BaseInspecciones):

    def test_plantillas_y_monitoreos_cargados(self):
        self.assertEqual(PlantillaInspeccion.objects.count(), 11)
        familias = set(PlantillaInspeccion.objects.values_list('familia', flat=True))
        self.assertEqual(familias, {'elementos', 'contenido', 'preguntas', 'trabajadores'})
        sstma = PlantillaInspeccion.objects.get(codigo_formato='SIG-PRO-06-r04')
        self.assertGreater(sum(len(s['preguntas']) for s in sstma.secciones), 50)
        epp = PlantillaInspeccion.objects.get(codigo_formato='SIG-PRO-06-r06')
        self.assertEqual(sum(1 for c in epp.criterios if c['invertido']), 8)
        self.assertEqual(ProgramaMonitoreo.objects.count(), 2)
        m = Monitoreo.objects.get(codigo='MON-001-2025')
        self.assertTrue(m.con_desviaciones)
        self.assertEqual(m.programados.count(), 3)
        self.assertEqual(RecomendacionMonitoreo.objects.count(), 20)


class PruebasInventario(BaseInspecciones):

    def test_codigo_unico_por_tipo_y_baja_con_motivo(self):
        r = self.client.post('/api/sst-elementos/', {'tipo': 'extintor', 'codigo': 'ext-01'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post('/api/sst-elementos/', {'tipo': 'escalera', 'codigo': 'EXT-01', 'subtipo': 'Tijera'},
                             format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client.delete(f'/api/sst-elementos/{self.e1.pk}/').status_code, 400)
        self.assertEqual(self.client.post(f'/api/sst-elementos/{self.e1.pk}/dar_baja/', {}).status_code, 400)
        r = self.client.post(f'/api/sst-elementos/{self.e1.pk}/dar_baja/', {'motivo': 'Robo'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.e1.refresh_from_db()
        self.assertFalse(self.e1.is_active)

    def test_alertas_de_vencimiento(self):
        r = self.client.get('/api/sst-inspecciones/resumen/')
        v = {x['nombre']: x['estado'] for x in r.data['vencimientos']}
        self.assertEqual(v.get('Extintor EXT-02'), 'vencido')
        self.assertNotIn('Extintor EXT-01', v)


class PruebasInspeccion(BaseInspecciones):

    def test_filas_desde_el_inventario_y_estructura_copiada(self):
        ins = self._crear(self.ext)
        self.assertRegex(ins['codigo'], r'^INS-\d{3}-\d{4}$')
        self.assertEqual([i['elemento_codigo'] for i in ins['items']], ['EXT-01', 'EXT-02'])
        self.assertEqual(ins['items'][0]['datos']['Capacidad'], '6 kg')
        # Cambiar la plantilla no altera la inspección ya creada.
        self.ext.criterios = self.ext.criterios[:2]
        self.ext.save()
        r = self.client.get(self._url(ins))
        self.assertEqual(len(r.data['estructura']['criterios']), 7)

    def test_no_se_firma_incompleta_ni_con_no_conforme_sin_accion(self):
        ins = self._crear(self.ext)
        r = self.client.post(self._url(ins, 'firmar'), {'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('Faltan respuestas', r.data['detail'])
        malo = ins['items'][1]['id']
        ins = self._responder_todo(ins, 'C', malos={malo: 'NC'})
        self.assertTrue([i for i in ins['items'] if i['id'] == malo][0]['no_conforme'])
        r = self.client.post(self._url(ins, 'firmar'), {'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('acción inmediata', r.data['detail'])
        r = self.client.post(self._url(ins, 'responder'), {'items': [
            {'id': malo, 'accion': 'Recargar el extintor', 'responsable_accion': self.sig.pk,
             'plazo_accion': str(timezone.localdate() + timedelta(days=5))}]}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.post(self._url(ins, 'firmar'), {'password': 'mala'}, format='json').status_code,
                         400)
        r = self.client.post(self._url(ins, 'firmar'), {'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'con_acciones')
        # Firmada: ni respuestas ni datos del registro se modifican.
        self.assertEqual(self.client.post(self._url(ins, 'responder'), {'items': [
            {'id': malo, 'resultados': {'0': 'C'}}]}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(self._url(ins), {'conclusiones': 'x'}, format='json').status_code, 400)
        # Completar la acción cierra la inspección.
        r = self.client.post(self._url(ins, 'completar_accion'), {'item_id': malo, 'seguimiento': 'Recargado'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'cerrada')

    def test_todo_conforme_cierra_al_firmar_y_hallazgo_una_vez(self):
        ins = self._crear(self.ext)
        malo = ins['items'][0]['id']
        ins = self._responder_todo(ins, 'C', malos={malo: 'NC'})
        self.client.post(self._url(ins, 'responder'), {'items': [
            {'id': malo, 'accion': 'Retirar obstáculo', 'responsable_accion': self.sig.pk,
             'plazo_accion': str(timezone.localdate())}]}, format='json')
        self.assertEqual(self.client.post(self._url(ins, 'registrar_hallazgo'), {'item_id': malo,
                                                                                 'tipo_nc': 'nc_menor'},
                                          format='json').status_code, 400, 'antes de firmar no hay hallazgo')
        self.client.post(self._url(ins, 'firmar'), {'password': CLAVE}, format='json')
        r = self.client.post(self._url(ins, 'registrar_hallazgo'), {'item_id': malo, 'tipo_nc': 'nc_menor'},
                             format='json')
        self.assertEqual(r.status_code, 200, r.data)
        it = [i for i in r.data['items'] if i['id'] == malo][0]
        self.assertTrue(it['hallazgo_codigo'].startswith('NC-'))
        self.assertEqual(self.client.post(self._url(ins, 'registrar_hallazgo'), {'item_id': malo,
                                                                                 'tipo_nc': 'nc_menor'},
                                          format='json').status_code, 400)
        ins2 = self._crear(self.ext)
        self._responder_todo(ins2, 'C')
        r = self.client.post(self._url(ins2, 'firmar'), {'password': CLAVE}, format='json')
        self.assertEqual(r.data['estado'], 'cerrada')

    def test_contenido_preguntas_y_trabajadores(self):
        bot = ElementoSeguridad.objects.create(tipo='botiquin', codigo='BOT-1', ubicacion='Oficina')
        pl = PlantillaInspeccion.objects.get(codigo_formato='SIG-PRO-06-r01')
        self.assertEqual(self.client.post('/api/sst-inspecciones/', {'plantilla': pl.pk}, format='json').status_code,
                         400, 'la inspección de contenido exige el botiquín')
        ins = self._crear(pl, elemento=bot.pk)
        self.assertEqual(len(ins['items']), 14)
        sstma = PlantillaInspeccion.objects.get(codigo_formato='SIG-PRO-06-r04')
        ins = self._crear(sstma)
        self.assertEqual(len(ins['items']), sum(len(s['preguntas']) for s in sstma.secciones))
        self.assertEqual(self.client.post(self._url(ins, 'quitar_fila'), {'item_id': ins['items'][0]['id']},
                                          format='json').status_code, 400)
        epp = PlantillaInspeccion.objects.get(codigo_formato='SIG-PRO-06-r06')
        area = Area.objects.get(nombre='Laboratorio de Masa y Volumen')
        t = Trabajador.objects.create(nombres='Ana', apellidos='Paz', puesto=Puesto.objects.get(nombre='Metrólogo'),
                                      area=area)
        ins = self._crear(epp, area=area.pk)
        self.assertEqual([i['trabajador'] for i in ins['items']], [t.pk])
        # «Requiere cambio» marcado (✔) es no conforme; «Estado» bueno no lo es.
        idx = next(k for k, c in enumerate(ins['estructura']['criterios']) if c['invertido'])
        r = self.client.post(self._url(ins, 'responder'), {'items': [
            {'id': ins['items'][0]['id'], 'resultados': {'0': 'B', str(idx): 'B'}}]}, format='json')
        self.assertTrue(r.data['items'][0]['no_conforme'])
        r = self.client.post(self._url(ins, 'responder'), {'items': [
            {'id': ins['items'][0]['id'], 'resultados': {'0': 'B', str(idx): 'M'}}]}, format='json')
        self.assertFalse(r.data['items'][0]['no_conforme'])

    def test_anular_solo_en_registro_y_pdf(self):
        ins = self._crear(self.ext)
        self.assertEqual(self.client.get(self._url(ins, 'pdf')).status_code, 200)
        self.assertEqual(self.client.post(self._url(ins, 'anular'), {}).status_code, 400)
        r = self.client.post(self._url(ins, 'anular'), {'motivo': 'Duplicada'}, format='json')
        self.assertEqual(r.data['estado'], 'anulada')
        for pl in PlantillaInspeccion.objects.exclude(familia='contenido').exclude(tipo_elemento__in=['vehiculo',
                                                                                                     'moto']):
            i = self._crear(pl)
            self.assertEqual(self.client.get(self._url(i, 'pdf')).status_code, 200, pl.nombre)

    def test_programa_de_inspecciones(self):
        self._responder_todo(self._crear(self.ext), 'C')
        r = self.client.get('/api/sst-inspecciones/programa/')
        fila = next(f for f in r.data['filas'] if f['plantilla'] == self.ext.pk)
        mes = fila['meses'][timezone.localdate().month - 1]
        self.assertEqual(mes['situacion'], 'realizado')
        # Los meses anteriores a la carga de la plantilla no cuentan como atrasados.
        if timezone.localdate().month > 1:
            self.assertEqual(fila['meses'][0]['situacion'], 'antes_del_sistema')
        self.assertFalse(any(m['situacion'] == 'atrasado' for f in r.data['filas'] for m in f['meses']))


class PruebasMonitoreos(BaseInspecciones):

    def test_registro_exige_resultados_causas_conclusiones_e_informe(self):
        r = self.client.post('/api/sst-monitoreos/', {'area_monitoreada': 'Laboratorios', 'fecha': '2026-10-01'},
                             format='json')
        self.assertEqual(r.status_code, 201, r.data)
        mid = r.data['id']
        self.assertRegex(r.data['codigo'], r'^MON-\d{3}-2026$')
        r = self.client.post(f'/api/sst-monitoreos/{mid}/firmar/', {'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 400)
        self.client.patch(f'/api/sst-monitoreos/{mid}/', {'resultados': [
            {'agente': 'Ruido', 'resultado': '88 dB', 'lmp': '85 dB', 'dentro_lmp': False}],
            'conclusiones': 'Dotar protección auditiva.'}, format='json')
        r = self.client.post(f'/api/sst-monitoreos/{mid}/firmar/', {'password': CLAVE}, format='json')
        self.assertIn('causas', r.data['detail'])
        self.assertIn('informe', r.data['detail'])
        self.client.patch(f'/api/sst-monitoreos/{mid}/', {'causas_desviacion': 'Compresor sin aislamiento'},
                          format='json')
        self.client.post(f'/api/sst-monitoreos/{mid}/informe/',
                         {'archivo': SimpleUploadedFile('informe.pdf', b'%PDF-1.4', 'application/pdf')})
        r = self.client.post(f'/api/sst-monitoreos/{mid}/firmar/', {'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'registrado')
        self.assertEqual(self.client.patch(f'/api/sst-monitoreos/{mid}/', {'conclusiones': 'x'},
                                           format='json').status_code, 400)
        self.assertEqual(self.client.get(f'/api/sst-monitoreos/{mid}/pdf/').status_code, 200)

    def test_programa_y_recomendaciones(self):
        p = ProgramaMonitoreo.objects.get(anio=2025)
        r = self.client.get('/api/sst-programa-monitoreos/anio/?anio=2025')
        self.assertEqual([i['meses_ejecutados'] for i in r.data['items']], [[12], [12], [12]])
        self.assertEqual(self.client.get(f'/api/sst-programa-monitoreos/{p.pk}/pdf/').status_code, 200)
        it = r.data['items'][0]
        self.assertEqual(self.client.post(f'/api/sst-programa-monitoreos/{p.pk}/quitar_item/',
                                          {'id': it['id'], 'motivo': 'x'}, format='json').status_code, 400,
                         'con registros no se quita del programa')
        rec = RecomendacionMonitoreo.objects.filter(estado='en_proceso').first()
        r = self.client.patch(f'/api/sst-recomendaciones/{rec.pk}/', {'estado': 'ejecutada'}, format='json')
        self.assertEqual(r.status_code, 200)
        rec.refresh_from_db()
        self.assertEqual(rec.fecha_ejecucion, timezone.localdate())
        self.assertEqual(self.client.get('/api/sst-recomendaciones/programa_pdf/?anio=2026').status_code, 200)
