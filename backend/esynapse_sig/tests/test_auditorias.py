"""
M10 Auditorías internas.

Reglas:
- Programada → Planificada exige objetivo, alcance y auditor líder (el líder
  del equipo auditor vale como auditor líder).
- Los hallazgos de auditoría se registran en M8 (Hallazgos); una NC mayor
  marca "requiere acción correctiva".
- La lista de verificación se genera desde el catálogo (la integrada tiene
  201 filas: 36 títulos y 165 preguntas) y no se duplica.
- No se cierra una auditoría sin conclusiones.
- Los seis formatos PDF se generan.
"""
from core.tests.base import CasoBase
from esynapse_sig.models import Auditoria, Hallazgo, ProgramaAuditoria

from .flujo_auditoria import avanzar


class BaseAuditoria(CasoBase):

    def setUp(self):
        self.auditor = self.crear_usuario('auditor', cargo='Auditor líder')
        self.dar_permisos(self.auditor, 'auditorias', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.lider = self.crear_usuario('oscar', cargo='Gerente Técnico')
        self.autenticar(self.auditor)
        self.programa = ProgramaAuditoria.objects.create(anio=2026, created_by=self.auditor)
        r = self.client.post('/api/auditorias/', {
            'programa': self.programa.pk, 'tipo': 'programada',
            'normas_aplicables': ['sig_integrado'], 'areas_procesos': 'Logística y Metrología',
            'modalidad': 'presencial', 'mes_programado': 5,
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.aud = Auditoria.objects.get(pk=r.data['id'])

    def _hasta(self, estado):
        avanzar(self, self.aud, estado, lider=self.lider)
        self.assertEqual(self.aud.estado, estado)

    def _planificar_e_iniciar(self):
        self._hasta('en_ejecucion')


class PruebasCicloAuditoria(BaseAuditoria):

    def test_codigo_correlativo_anual(self):
        self.assertRegex(self.aud.codigo, r'^AI-\d{2}-\d{4}$')

    def test_el_codigo_lleva_el_anio_del_programa(self):
        """Una auditoría del Programa 2027 es AI-01-2027 aunque se registre antes;
        el correlativo es independiente por año."""
        p2027 = ProgramaAuditoria.objects.create(anio=2027, created_by=self.auditor)
        a1 = Auditoria.objects.create(programa=p2027, areas_procesos='Masa', created_by=self.auditor)
        a2 = Auditoria.objects.create(programa=p2027, areas_procesos='Temperatura', created_by=self.auditor)
        self.assertEqual((a1.codigo, a2.codigo), ('AI-01-2027', 'AI-02-2027'))
        self.assertEqual(self.aud.codigo, 'AI-01-2026', 'el programa 2026 tiene su propio correlativo')
        sin_programa = Auditoria.objects.create(areas_procesos='Extraordinaria', created_by=self.auditor)
        from django.utils import timezone
        self.assertTrue(sin_programa.codigo.endswith(f'-{timezone.now().year}'))

    def test_planificar_exige_objetivo_alcance_y_lider(self):
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/planificar/')
        self.assertEqual(r.status_code, 400)
        self.client.patch(f'/api/auditorias/{self.aud.pk}/',
                          {'objetivo': 'Evaluar el SIG', 'alcance': 'Todos los procesos'}, format='json')
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/planificar/')
        self.assertEqual(r.status_code, 400, 'sin líder no se planifica')

    def test_lider_del_equipo_vale_como_auditor_lider(self):
        self.client.patch(f'/api/auditorias/{self.aud.pk}/',
                          {'objetivo': 'Evaluar el SIG', 'alcance': 'Todos los procesos',
                           'cronograma_entrevistas': [{'fecha': '2026-05-12', 'area': 'Logística'}]}, format='json')
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/agregar_integrante/',
                             {'rol': 'lider', 'usuario': self.lider.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.aud.refresh_from_db()
        self.assertEqual(self.aud.auditor_lider, self.lider, 'el líder del equipo se sincroniza')
        integrante = self.aud.equipo.get(rol='lider')
        self.assertEqual(integrante.cargo, 'Gerente Técnico', 'el cargo se hereda del usuario')
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/planificar/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'planificada')

    def test_no_se_cierra_sin_conclusiones(self):
        self._hasta('conclusiones')
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/validar_hallazgos/', {'conclusiones': ''}, format='json')
        self.assertEqual(r.status_code, 400, 'sin conclusiones no se pasa a la reunión de cierre')
        self._hasta('cerrada')

    def test_reprogramar_conserva_el_mes_original(self):
        """Programa anual: la fila 'Programado' mantiene el mes original y
        'Reprogramado' recibe el nuevo; el motivo es obligatorio."""
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/reprogramar/', {'mes_programado': 8}, format='json')
        self.assertEqual(r.status_code, 400, 'sin motivo no se reprograma')
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/reprogramar/',
                             {'mes_programado': 8, 'motivo': 'Inventario anual'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.aud.refresh_from_db()
        self.assertEqual(self.aud.mes_programado, 5)
        self.assertEqual(self.aud.mes_reprogramado, 8)
        self.assertTrue(self.aud.reprogramada)
        self.assertEqual(self.aud.motivo_reprogramacion, 'Inventario anual')

    def test_clase_requisitos_y_observaciones_del_programa(self):
        r = self.client.post('/api/auditorias/', {
            'programa': self.programa.pk, 'clase': 'externa', 'areas_procesos': 'Acreditación INACAL',
            'normas_aplicables': ['iso_17025'], 'mes_programado': 11,
            'requisitos_por_norma': {'iso_17025': 'Todas'}, 'observaciones_programa': 'Visita de vigilancia',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['clase'], 'externa')
        self.assertEqual(r.data['requisitos_por_norma'], {'iso_17025': 'Todas'})
        self.assertEqual(r.data['observaciones_programa'], 'Visita de vigilancia')
        self.assertEqual(Auditoria.objects.get(pk=self.aud.pk).clase, 'interna', 'por defecto es interna')

    def test_eliminar_solo_desactiva(self):
        r = self.client.delete(f'/api/auditorias/{self.aud.pk}/')
        self.assertEqual(r.status_code, 204)
        self.aud.refresh_from_db()
        self.assertFalse(self.aud.is_active)


class PruebasHallazgosYListas(BaseAuditoria):

    def test_hallazgos_solo_durante_ejecucion(self):
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/registrar_hallazgo/',
                             {'tipo': 'nc_menor', 'descripcion': 'Registro sin firma'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_hallazgo_se_registra_en_m8_y_nc_mayor_requiere_ac(self):
        self._planificar_e_iniciar()
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/registrar_hallazgo/',
                             {'tipo': 'nc_mayor', 'descripcion': 'Sin control de registros', 'requisito': '7.5'},
                             format='json')
        self.assertEqual(r.status_code, 200, r.data)
        h = Hallazgo.objects.get(auditoria=self.aud, tipo='nc_mayor')
        self.assertEqual(h.fuente, 'auditoria_interna')
        self.assertTrue(h.requiere_ac)
        self.assertTrue(h.codigo)
        self.client.post(f'/api/auditorias/{self.aud.pk}/registrar_hallazgo/',
                         {'tipo': 'observacion', 'descripcion': 'Mejorar rotulado'}, format='json')
        self.assertFalse(Hallazgo.objects.get(auditoria=self.aud, tipo='observacion').requiere_ac)

    def test_lista_integrada_se_genera_del_catalogo_y_no_se_duplica(self):
        self._hasta('planificada')
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/generar_lista/', {'norma': 'sig_integrado'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        lista = self.aud.listas.get(norma='sig_integrado')
        self.assertEqual(lista.items.count(), 201)
        self.assertEqual(lista.items.filter(es_seccion=True).count(), 36)
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/generar_lista/', {'norma': 'sig_integrado'}, format='json')
        self.assertEqual(r.status_code, 400, 'la lista no se duplica')
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/generar_lista/', {'norma': 'inexistente'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_evaluar_item_guarda_documento_referencia_y_evidencia(self):
        self._hasta('planificada')
        self.client.post(f'/api/auditorias/{self.aud.pk}/generar_lista/', {'norma': 'sig_integrado'}, format='json')
        self._hasta('en_ejecucion')
        item = self.aud.listas.get(norma='sig_integrado').items.filter(es_seccion=False).first()
        r = self.client.post(f'/api/auditorias/{self.aud.pk}/evaluar_item/', {
            'item_id': item.pk, 'resultado': 'cumple',
            'documento_referencia': 'Manual SIG', 'evidencia': 'Se revisó la matriz FODA'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        item.refresh_from_db()
        self.assertEqual(item.resultado, 'cumple')
        self.assertEqual(item.documento_referencia, 'Manual SIG')
        self.assertEqual(item.evidencia, 'Se revisó la matriz FODA')


class PruebasPdfAuditoria(BaseAuditoria):

    def _es_pdf(self, r):
        self.assertEqual(r.status_code, 200, getattr(r, 'data', r.content[:200]))
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))

    def test_los_seis_formatos_se_generan(self):
        self._hasta('planificada')
        self.client.post(f'/api/auditorias/{self.aud.pk}/generar_lista/', {'norma': 'sig_integrado'}, format='json')
        self._hasta('en_informe')
        base = f'/api/auditorias/{self.aud.pk}'
        self._es_pdf(self.client.get(f'{base}/plan_pdf/'))
        self._es_pdf(self.client.get(f'{base}/acta_pdf/?tipo=apertura'))
        self._es_pdf(self.client.get(f'{base}/acta_pdf/?tipo=cierre'))
        self._es_pdf(self.client.get(f'{base}/lista_pdf/?norma=sig_integrado'))
        self._es_pdf(self.client.get(f'{base}/informe_pdf/'))
        # Programa anual con una interna reprogramada y una externa
        self.client.post(f'/api/auditorias/{self.aud.pk}/reprogramar/', {'mes_programado': 7, 'motivo': 'Carga'}, format='json')
        self.client.post('/api/auditorias/', {'programa': self.programa.pk, 'clase': 'externa', 'areas_procesos': 'INACAL',
                                              'normas_aplicables': ['iso_17025'], 'mes_programado': 11,
                                              'requisitos_por_norma': {'iso_17025': 'Todas'}}, format='json')
        self._es_pdf(self.client.get(f'/api/programas-auditoria/{self.programa.pk}/programa_pdf/'))

    def test_lista_pdf_sin_lista_generada_avisa(self):
        r = self.client.get(f'/api/auditorias/{self.aud.pk}/lista_pdf/?norma=iso_17025')
        self.assertEqual(r.status_code, 400)


class PruebasFechaElaboracionPlan(CasoBase):
    """El plan impreso lleva fecha de elaboración: la indicada o, si no, la del día en que se planificó."""

    def test_se_fija_al_planificar_y_se_puede_indicar(self):
        from datetime import date
        from esynapse_sig.models import Auditoria, ProgramaAuditoria
        u = self.crear_usuario('lider_plan')
        self.dar_permisos(u, 'auditorias', 'leer', 'crear', 'editar', 'aprobar')
        self.autenticar(u)
        prog = ProgramaAuditoria.objects.create(anio=2026, created_by=u)
        crono = [{'fecha': '2026-03-10', 'area': 'Masa'}]
        a = Auditoria.objects.create(programa=prog, areas_procesos='Masa', objetivo='Evaluar', alcance='Todo',
                                     auditor_lider=u, cronograma_entrevistas=crono, created_by=u)
        self.assertIsNone(a.fecha_elaboracion_plan)
        r = self.client.post(f'/api/auditorias/{a.pk}/planificar/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['fecha_elaboracion_plan'], date.today().isoformat())
        b = Auditoria.objects.create(programa=prog, areas_procesos='Longitud', objetivo='Evaluar', alcance='Todo',
                                     auditor_lider=u, cronograma_entrevistas=crono, created_by=u)
        r = self.client.patch(f'/api/auditorias/{b.pk}/', {'fecha_elaboracion_plan': '2026-03-05'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        r = self.client.post(f'/api/auditorias/{b.pk}/planificar/')
        self.assertEqual(r.data['fecha_elaboracion_plan'], '2026-03-05', 'la fecha indicada se respeta')
        r = self.client.get(f'/api/auditorias/{a.pk}/plan_pdf/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))


class PruebasLista17025Formato(CasoBase):
    """La lista NTP-ISO/IEC 17025 es la del formato: cláusulas completas más
    los ítems para auditorías internas de seguimiento, y el PDF las imprime."""

    def test_lista_17025_completa_y_pdf(self):
        from esynapse_sig.models import Auditoria, ProgramaAuditoria, RequisitoNorma
        u = self.crear_usuario('auditor17025')
        self.dar_permisos(u, 'auditorias', 'leer', 'crear', 'editar')
        self.autenticar(u)
        cat = RequisitoNorma.objects.filter(norma='iso_17025')
        self.assertEqual(cat.count(), 183)
        self.assertEqual(cat.filter(bloque='seguimiento').count(), 8)
        self.assertTrue(cat.filter(codigo='7.7.1').exists())
        self.assertIn('Directriz DA-acr-06D', cat.get(codigo='4.1.1').titulo)
        prog = ProgramaAuditoria.objects.create(anio=2026, created_by=u)
        a = Auditoria.objects.create(programa=prog, areas_procesos='Masa', normas_aplicables=['iso_17025'],
                                     objetivo='x', alcance='y', auditor_lider=u, estado='planificada', created_by=u)
        r = self.client.post(f'/api/auditorias/{a.pk}/generar_lista/', {'norma': 'iso_17025'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        Auditoria.objects.filter(pk=a.pk).update(estado='en_ejecucion')
        lista = a.listas.get(norma='iso_17025')
        self.assertEqual(lista.items.count(), 183)
        self.assertEqual(lista.items.filter(bloque='seguimiento').count(), 8)
        item = lista.items.get(codigo='3', bloque='seguimiento')
        r = self.client.post(f'/api/auditorias/{a.pk}/evaluar_item/',
                             {'item_id': item.pk, 'resultado': 'cumple', 'evidencia': 'Sin cambios'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        r = self.client.get(f'/api/auditorias/{a.pk}/lista_pdf/?norma=iso_17025')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))
        self.assertGreater(len(r.content), 30000)


class PruebasCatalogoRequisitos(CasoBase):

    def test_catalogo_completo_sin_paginar(self):
        u = self.crear_usuario('lector_cat')
        self.dar_permisos(u, 'auditorias', 'leer')
        self.autenticar(u)
        r = self.client.get('/api/requisitos-norma/?norma=iso_17025')
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.data, list, 'el catálogo se entrega entero, sin paginar')
        self.assertEqual(len(r.data), 183)
        self.assertEqual(r.data[0]['bloque'], 'seguimiento')
        self.assertTrue(any(x['es_seccion'] and x['codigo'] == '4.1' for x in r.data))


class PruebasFormatoTextoLista17025(CasoBase):
    """El texto de la lista 17025 conserva la presentación del formato:
    viñetas a) b) c), guiones anidados y negritas de la directriz."""

    def test_vinetas_y_negritas_en_catalogo_y_lista(self):
        from esynapse_sig.models import Auditoria, ProgramaAuditoria, RequisitoNorma
        r55 = RequisitoNorma.objects.get(norma='iso_17025', bloque='requisitos', codigo='5.5')
        self.assertEqual([p.get('l') for p in r55.formato if p.get('l')], ['a)', 'b)', 'c)'])
        self.assertIn('a) Definir la organización', r55.titulo)
        self.assertTrue(any('<b>Directriz DA-acr-06D:' in p['t'] for p in r55.formato))
        r871 = RequisitoNorma.objects.get(norma='iso_17025', bloque='requisitos', codigo='8.7.1')
        sangrias = {p.get('l'): p.get('i') for p in r871.formato if p.get('l')}
        self.assertGreater(sangrias['−'], sangrias['a)'], 'los guiones van sangrados bajo su literal')
        u = self.crear_usuario('auditor_fmt')
        self.dar_permisos(u, 'auditorias', 'leer', 'crear', 'editar')
        self.autenticar(u)
        prog = ProgramaAuditoria.objects.create(anio=2026, created_by=u)
        a = Auditoria.objects.create(programa=prog, areas_procesos='Masa', normas_aplicables=['iso_17025'],
                                     estado='planificada', created_by=u)
        self.client.post(f'/api/auditorias/{a.pk}/generar_lista/', {'norma': 'iso_17025'}, format='json')
        item = a.listas.get(norma='iso_17025').items.get(bloque='requisitos', codigo='5.5')
        self.assertEqual(item.formato, r55.formato, 'la lista generada copia el formato del catálogo')
        r = self.client.get(f'/api/auditorias/{a.pk}/lista_pdf/?norma=iso_17025')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))


class PruebasListaIntegradaCompleta(CasoBase):
    """La lista integrada cubre todos los numerales de ISO 9001, ISO 14001 e
    ISO 45001 y cada pregunta cita la norma y el numeral que la exige."""

    REQUERIDOS = {
        'ISO 9001': '4.1 4.2 4.3 4.4.1 4.4.2 5.1.1 5.1.2 5.2.1 5.2.2 5.3 6.1.1 6.1.2 6.2.1 6.2.2 6.3 7.1.1 7.1.2 '
                    '7.1.3 7.1.4 7.1.5.1 7.1.5.2 7.1.6 7.2 7.3 7.4 7.5.1 7.5.2 7.5.3.1 7.5.3.2 8.1 8.2.1 8.2.2 '
                    '8.2.3.1 8.2.3.2 8.2.4 8.3.1 8.3.2 8.3.3 8.3.4 8.3.5 8.3.6 8.4.1 8.4.2 8.4.3 8.5.1 8.5.2 '
                    '8.5.3 8.5.4 8.5.5 8.5.6 8.6 8.7.1 8.7.2 9.1.1 9.1.2 9.1.3 9.2.1 9.2.2 9.3.1 9.3.2 9.3.3 '
                    '10.1 10.2.1 10.2.2 10.3',
        'ISO 14001': '4.1 4.2 4.3 4.4 5.1 5.2 5.3 6.1.1 6.1.2 6.1.3 6.1.4 6.2.1 6.2.2 7.1 7.2 7.3 7.4.1 7.4.2 '
                     '7.4.3 7.5.1 7.5.2 7.5.3 8.1 8.2 9.1.1 9.1.2 9.2.1 9.2.2 9.3 10.1 10.2 10.3',
        'ISO 45001': '4.1 4.2 4.3 4.4 5.1 5.2 5.3 5.4 6.1.1 6.1.2.1 6.1.2.2 6.1.2.3 6.1.3 6.1.4 6.2.1 6.2.2 7.1 '
                     '7.2 7.3 7.4.1 7.4.2 7.4.3 7.5.1 7.5.2 7.5.3 8.1.1 8.1.2 8.1.3 8.1.4.1 8.1.4.2 8.1.4.3 8.2 '
                     '9.1.1 9.1.2 9.2.1 9.2.2 9.3 10.1 10.2 10.3',
    }

    def test_todos_los_numerales_y_cada_pregunta_referenciada(self):
        import re
        from esynapse_sig.models import RequisitoNorma
        preguntas = RequisitoNorma.objects.filter(norma='sig_integrado', es_seccion=False)
        citados = {n: set() for n in self.REQUERIDOS}
        for p in preguntas:
            ref = p.titulo.split('\n')[0]
            pares = re.findall(r'(ISO \d+): ([\d.]+)', ref)
            self.assertTrue(pares, f'{p.codigo} sin referencia a la norma')
            self.assertEqual(p.formato[0]['t'].replace('&nbsp;', ' '), f'<b>{ref}</b>', 'la referencia va en negrita')
            for norma, num in pares:
                citados[norma].add(num)
        for norma, nums in self.REQUERIDOS.items():
            faltan = set(nums.split()) - citados[norma]
            self.assertFalse(faltan, f'{norma}: numerales sin pregunta {sorted(faltan)}')
        self.assertFalse(RequisitoNorma.objects.filter(norma='sig_integrado', codigo__startswith='8.2e').exists(),
                         'no hay numerales inventados')

    def test_nro_es_correlativo_y_el_hallazgo_cita_el_numeral_iso(self):
        """El Nro. de cada pregunta es un correlativo (no un numeral que no existe
        en la norma); los títulos de cláusula conservan su numeral, y el
        requisito que se cita (hallazgo, informe) es el de la norma."""
        from esynapse_sig.models import ItemVerificacion, ListaVerificacion, RequisitoNorma
        preguntas = list(RequisitoNorma.objects.filter(norma='sig_integrado', es_seccion=False).order_by('orden'))
        self.assertEqual([p.codigo for p in preguntas], [str(n) for n in range(1, len(preguntas) + 1)])
        secciones = set(RequisitoNorma.objects.filter(norma='sig_integrado', es_seccion=True)
                        .values_list('codigo', flat=True))
        self.assertTrue({'4', '4.1', '8.2', '10.3'} <= secciones)
        p = next(x for x in preguntas if x.titulo.startswith('ISO 9001: 7.1.5.2'))
        it = ItemVerificacion(lista=ListaVerificacion(norma='sig_integrado'), codigo=p.codigo, titulo=p.titulo)
        self.assertEqual(it.referencias_norma(), [('ISO 9001', '7.1.5.2')])
        self.assertEqual(it.referencia_texto(), 'ISO 9001 7.1.5.2')


class PruebasListasPorNorma(CasoBase):
    """ISO 9001, 14001 o 45001 auditadas por separado: su lista trae solo las
    preguntas que esa norma exige, citando solo su numeral, con correlativo, y
    sin aclaraciones de las otras normas. No se combinan con el integrado."""

    def setUp(self):
        self.u = self.crear_usuario('aud_norma')
        self.dar_permisos(self.u, 'auditorias', 'leer', 'crear', 'editar', 'aprobar')
        self.autenticar(self.u)
        self.prog = ProgramaAuditoria.objects.create(anio=2026, created_by=self.u)

    def _lista(self, norma):
        a = Auditoria.objects.create(programa=self.prog, areas_procesos='SIG', normas_aplicables=[norma],
                                     objetivo='x', alcance='y', auditor_lider=self.u, estado='planificada',
                                     created_by=self.u)
        r = self.client.post(f'/api/auditorias/{a.pk}/generar_lista/', {'norma': norma}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return a.listas.get(norma=norma)

    def test_cada_norma_su_lista(self):
        import re
        esperado = {'iso_9001': ('ISO 9001', 105, r'en SST|en ambiental|peligro|emergencia'),
                    'iso_14001': ('ISO 14001', 88, r'en SST|en calidad|peligro|cliente'),
                    'iso_45001': ('ISO 45001', 102, r'en ambiental|en calidad|cliente|aspectos ambientales')}
        for norma, (etiqueta, total, ajenas) in esperado.items():
            lista = self._lista(norma)
            preguntas = list(lista.items.filter(es_seccion=False).order_by('orden'))
            self.assertEqual(len(preguntas), total, norma)
            self.assertEqual([p.codigo for p in preguntas], [str(n) for n in range(1, total + 1)])
            for p in preguntas:
                ref = p.titulo.split('\n')[0]
                self.assertEqual(set(re.findall(r'ISO \d+', ref)), {etiqueta}, f'{norma} {p.codigo}: {ref}')
                self.assertFalse(re.search(ajenas, p.titulo), f'{norma} {p.codigo}: {p.titulo}')
                self.assertEqual(p.bloque, 'requisitos')
        secciones_9001 = set(self._lista('iso_9001').items.filter(es_seccion=True).values_list('codigo', flat=True))
        self.assertNotIn('5.4', secciones_9001, 'la consulta a los trabajadores es solo de ISO 45001')
        t82 = self._lista('iso_14001').items.get(es_seccion=True, codigo='8.2').titulo
        self.assertEqual(t82, 'Preparación y respuesta ante emergencias')

    def test_los_selectores_conservan_los_titulos_de_clausula(self):
        from esynapse_sig.models import RequisitoNorma
        r = self.client.get('/api/requisitos-norma/?norma=iso_9001')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RequisitoNorma.objects.filter(norma='iso_9001', bloque='requisitos').count(), 35)

    def test_integrado_y_norma_suelta_no_se_combinan(self):
        r = self.client.post('/api/auditorias/', {
            'programa': self.prog.pk, 'tipo': 'programada', 'normas_aplicables': ['sig_integrado', 'iso_9001'],
            'areas_procesos': 'SIG', 'modalidad': 'presencial', 'mes_programado': 5}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('normas_aplicables', r.data)

    def test_cada_lista_individual_cubre_todos_los_numerales_de_su_norma(self):
        """La lista de 14001 (o 45001, o 9001) generada sola tiene al menos una
        pregunta para cada numeral de esa norma, igual que la integrada."""
        import re
        claves = {'ISO 9001': 'iso_9001', 'ISO 14001': 'iso_14001', 'ISO 45001': 'iso_45001'}
        for etiqueta, numerales in PruebasListaIntegradaCompleta.REQUERIDOS.items():
            lista = self._lista(claves[etiqueta])
            citados = set()
            for p in lista.items.filter(es_seccion=False):
                citados |= set(re.findall(r'ISO \d+: ([\d.]+)', p.titulo.split('\n')[0]))
            faltan = set(numerales.split()) - citados
            self.assertFalse(faltan, f'{etiqueta} sola: numerales sin pregunta {sorted(faltan)}')
