"""
Medio ambiente (decisiones de César, 2026-10-24):
- Significativo si la suma de los cinco criterios es ≥ 10 o si el cumplimiento legal es 3; un positivo no se evalúa.
- Un significativo exige control operacional, responsable y plazo.
- La matriz la aprueban TODOS los titulares del Comité de SST; un cambio posterior la deja pendiente.
- Consumos: uno por tipo y mes, no futuros; indicadores calculados.
- Residuos: pesaje cerrado con firma; peligrosos solo a EO-RS; resumen anual en kg y toneladas.
"""
from datetime import date, timedelta

from django.utils import timezone

from core.tests.base import CasoBase
from organizacion.models import Area, Puesto, Trabajador
from sst.comite import ComiteSST, MiembroComite
from sst.tests.test_comite import texto_pdf

from ambiente.models import AspectoAmbiental

CLAVE = CasoBase.CLAVE


class Base(CasoBase):

    def setUp(self):
        self.sig = self.crear_usuario('gsig_amb', cargo='Gerente SIG', sigla_cargo='GSIG')
        self.dar_permisos(self.sig, 'medio_ambiente', 'leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.autenticar(self.sig)
        self.area = Area.objects.get(nombre='Laboratorio de Masa y Volumen')
        self.gsig = Puesto.objects.get(nombre='Gerente SIG')

    def _aspecto(self, **extra):
        datos = {'alcance': 'areas', 'areas': [self.area.pk], 'actividad': 'Lavado de material',
                 'aspecto': 'Consumo de agua', 'impacto': 'Agotamiento del recurso', 'situaciones': ['N'],
                 'generacion': 'directa', 'clase': 'negativo', 'legal': 1, 'severidad': 2, 'partes': 1,
                 'escala': 1, 'frecuencia': 3}
        datos.update(extra)
        return self.client.post('/api/amb-aspectos/', datos, format='json')


class PruebasMatriz(Base):

    def test_carga_inicial_consolidada(self):
        self.assertEqual(AspectoAmbiental.objects.filter(estado='vigente').count(), 176)
        sig = [a for a in AspectoAmbiental.objects.all() if a.significativo]
        self.assertEqual(len(sig), 5, 'incendio + 4 con incumplimiento legal')
        self.assertTrue(all(a.resultado is None for a in AspectoAmbiental.objects.filter(clase='positivo')))

    def test_regla_de_significancia_y_positivos(self):
        r = self._aspecto()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertFalse(r.data['significativo'])
        self.assertEqual(r.data['resultado'], 8)
        r = self._aspecto(legal=3)
        self.assertEqual(r.status_code, 400, 'incumplimiento legal → significativo → exige control, responsable y plazo')
        self.assertEqual(set(r.data), {'control_operacional', 'responsable', 'plazo'})
        r = self._aspecto(legal=3, control_operacional='Reparar fugas', responsable=self.gsig.pk,
                          plazo='2026-12-31')
        self.assertTrue(r.data['significativo'])
        self.assertEqual(r.data['resultado'], 10)
        r = self._aspecto(clase='positivo', aspecto='Uso de gases certificados')
        self.assertIsNone(r.data['resultado'])
        self.assertIsNone(r.data['legal'])
        self.assertFalse(r.data['significativo'])
        self.assertEqual(self._aspecto(severidad=None).status_code, 400, 'un negativo se valora completo')

    def test_retiro_y_solo_lectura(self):
        a = self._aspecto().data
        url = f'/api/amb-aspectos/{a["id"]}'
        self.assertEqual(self.client.post(f'{url}/retirar/', {}, format='json').status_code, 400)
        self.client.post(f'{url}/retirar/', {'motivo': 'Ya no se realiza'}, format='json')
        self.assertEqual(self.client.patch(f'{url}/', {'actividad': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.get('/api/amb-aspectos/pdf/').status_code, 200)

    def test_aprobacion_por_todos_los_titulares(self):
        met = Puesto.objects.get(nombre='Metrólogo')
        u1 = self.crear_usuario('pres_amb')
        t1 = Trabajador.objects.create(nombres='Pedro', apellidos='Titular', documento='47000001', puesto=met,
                                       area=self.area, usuario=u1)
        t2 = Trabajador.objects.create(nombres='Lucía', apellidos='Titular', documento='47000002', puesto=met,
                                       area=self.area)
        t3 = Trabajador.objects.create(nombres='Raúl', apellidos='Titular', documento='47000003', puesto=met,
                                       area=self.area)
        c = ComiteSST.objects.get(periodo='2025-2027')
        ms = [MiembroComite.objects.create(comite=c, trabajador=t, representacion='trabajadores',
                                           condicion='titular') for t in (t1, t2, t3)]
        url = '/api/amb-aspectos/aprobar/'
        firmas = [{'miembro': ms[0].pk, 'clave': CLAVE},
                  {'miembro': ms[1].pk, 'pin_nuevo': '2468', 'pin_confirmacion': '2468'}]
        r = self.client.post(url, {'firmas': firmas}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('todos los titulares', r.data['detail'], 'la mitad más uno no basta')
        firmas.append({'miembro': ms[2].pk, 'pin_nuevo': '1357', 'pin_confirmacion': '1357'})
        r = self.client.post(url, {'firmas': firmas}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'aprobada')
        # Bloque común del Comité en el PDF: titulares, cómo firmó cada uno y la fecha.
        texto = texto_pdf(self.client.get('/api/amb-aspectos/pdf/'))
        for esperado in ('REALIZADO Y APROBADO POR', 'Pedro Titular', 'Firmado con su usuario', 'Firmado con PIN'):
            self.assertIn(esperado, texto)
        a = AspectoAmbiental.objects.filter(estado='vigente').first()
        self.client.patch(f'/api/amb-aspectos/{a.pk}/', {'controles_existentes': 'Nuevo control'}, format='json')
        self.assertEqual(self.client.get('/api/amb-aspectos/resumen/').data['aprobacion']['estado'], 'pendiente')
        self.assertIn('PENDIENTE DE APROBACIÓN DEL COMITÉ DE SST', texto_pdf(self.client.get('/api/amb-aspectos/pdf/')))

    def test_criterio_legal_sugerido_desde_la_evaluacion(self):
        from legal.models import Evaluacion, Obligacion, ResultadoEvaluacion
        from ambiente.views import legal_sugerido
        o = Obligacion.objects.filter(ambito='ma', is_active=True).first() or \
            Obligacion.objects.create(ambito='ma', extracto='Declarar residuos')
        self.assertIn(legal_sugerido(o), (None, 1, 2, 3))
        ev = Evaluacion.objects.create(ambito='ma', anio=2099, periodo='Prueba', orden=9)
        ResultadoEvaluacion.objects.create(evaluacion=ev, obligacion=o, resultado='no_cumple')
        self.assertEqual(legal_sugerido(o), 3)


class PruebasConsumos(Base):
    """Consumo por suministro de una sede (César, 2026-10-24): por lectura del medidor (consumo = diferencia con la
    lectura anterior) o por recibo; uno por suministro y mes; indicadores por sede y de toda la organización."""

    def setUp(self):
        super().setUp()
        from organizacion.models import Nivel, Sede, Suministro
        self.operativa = Sede.objects.get(nombre='Sede operativa')
        self.admin = Sede.objects.get(nombre='Sede administrativa')
        self.medidor = Suministro.objects.create(sede=self.operativa, tipo='energia', modalidad='lectura',
                                                 nivel=Nivel.objects.get(sede=self.operativa, nombre='Piso 2'))
        self.recibo = Suministro.objects.create(sede=self.admin, tipo='energia', modalidad='recibo')

    def _lectura(self, mes, actual, anio=2026, **extra):
        return self.client.post('/api/amb-consumos/', {'suministro': self.medidor.pk, 'anio': anio, 'mes': mes,
                                                       'lectura_actual': str(actual), **extra}, format='json')

    def test_lecturas_del_medidor(self):
        r = self._lectura(1, 1000)
        self.assertIn('primera lectura', r.data['lectura_anterior'][0])
        r = self._lectura(1, 1000, lectura_anterior='900')
        self.assertEqual((r.status_code, float(r.data['consumo']), r.data['origen']), (201, 100.0, 'lectura'))
        self.assertIn('menor que la anterior', self._lectura(2, 950).data['lectura_actual'][0])
        m2 = self._lectura(2, 1180).data
        self.assertEqual((float(m2['lectura_anterior']), float(m2['consumo'])), (1000.0, 180.0))
        m3 = self._lectura(3, 1300).data
        self.assertEqual(float(m3['consumo']), 120)
        # Corregir un mes recalcula el siguiente; no puede superar la lectura del mes siguiente.
        self.client.patch(f'/api/amb-consumos/{m2["id"]}/', {'lectura_actual': '1200'}, format='json')
        self.assertEqual(float(self.client.get(f'/api/amb-consumos/{m3["id"]}/').data['consumo']), 100)
        r = self.client.patch(f'/api/amb-consumos/{m2["id"]}/', {'lectura_actual': '1400'}, format='json')
        self.assertIn('mes siguiente', r.data['lectura_actual'][0])
        self.assertEqual(self._lectura(1, 1001).status_code, 400, 'uno por suministro y mes')
        self.assertEqual(self._lectura(1, 10, anio=date.today().year + 1).status_code, 400, 'no meses futuros')
        # Cambio de medidor: exige motivo y lectura inicial del nuevo.
        self.assertEqual(self._lectura(4, 50).status_code, 400)
        r = self._lectura(4, 50, cambio_medidor=True, lectura_anterior='0')
        self.assertIn('motivo_cambio', r.data)
        r = self._lectura(4, 50, cambio_medidor=True, lectura_anterior='0', motivo_cambio='Medidor nuevo')
        self.assertEqual(float(r.data['consumo']), 50)
        # Aviso (no bloquea) de un consumo muy superior al promedio.
        r = self._lectura(5, 600)
        self.assertEqual(r.status_code, 201)
        self.assertIn('mayor que el promedio', r.data['aviso'])
        # Anular un mes: el siguiente toma la lectura del registro previo.
        self.client.delete(f'/api/amb-consumos/{m2["id"]}/')
        self.assertEqual(float(self.client.get(f'/api/amb-consumos/{m3["id"]}/').data['consumo']), 300)

    def test_recibo_e_indicadores_por_sede(self):
        self._lectura(3, 1100, lectura_anterior='1000')
        r = self.client.post('/api/amb-consumos/', {'suministro': self.recibo.pk, 'anio': 2026, 'mes': 3},
                             format='json')
        self.assertIn('consumo', r.data, 'por recibo se escribe el consumo')
        self.client.post('/api/amb-consumos/', {'suministro': self.recibo.pk, 'anio': 2026, 'mes': 3,
                                                'consumo': '300', 'monto': '250'}, format='json')
        self.client.post('/api/amb-consumos/', {'suministro': self.recibo.pk, 'anio': 2025, 'mes': 3,
                                                'consumo': '240'}, format='json')
        self.assertIn('suministro', self.client.post('/api/amb-consumos/', {'anio': 2026, 'mes': 4, 'consumo': '1'},
                                                     format='json').data)
        d = self.client.get('/api/amb-consumos/indicadores/?anio=2026').data
        marzo = d['tipos']['energia']['meses'][2]
        self.assertEqual((float(marzo['consumo']), marzo['registrados'], marzo['esperados']), (400.0, 2, 2))
        d = self.client.get(f'/api/amb-consumos/indicadores/?anio=2026&sede={self.admin.pk}').data
        marzo = d['tipos']['energia']['meses'][2]
        self.assertEqual((float(marzo['consumo']), marzo['variacion']), (300.0, 25.0))
        self.assertEqual([s['nombre'] for s in d['suministros']], [self.recibo.nombre])

    def test_tarea_mensual_del_responsable(self):
        from ambiente.tareas import lecturas_pendientes
        from organizacion.models import Suministro
        t = Trabajador.objects.create(nombres='Rosa', apellidos='Lecturas', documento='47000020', puesto=self.gsig,
                                      area=self.area, usuario=self.sig)
        Suministro.objects.filter(pk=self.medidor.pk).update(responsable=self.gsig,
                                                             created_at=timezone.now() - timedelta(days=70))
        tareas = lecturas_pendientes(self.sig)
        self.assertEqual(len(tareas), 1)
        self.assertIn('Registrar el consumo', tareas[0]['titulo'])
        hoy = timezone.localdate()
        anio, mes = (hoy.year, hoy.month - 1) if hoy.month > 1 else (hoy.year - 1, 12)
        self._lectura(mes, 10, anio=anio, lectura_anterior='0')
        self.assertEqual(lecturas_pendientes(self.sig), [])
        self.assertTrue(t.pk)


class PruebasResiduos(Base):

    def test_pesaje_disposicion_y_resumen_anual(self):
        resp = Trabajador.objects.create(nombres='Ana', apellidos='Pesaje', documento='47000010',
                                         puesto=Puesto.objects.get(nombre='Asistente SIG'), area=self.area)
        items = [{'categoria': 'azul', 'tipo': 'Papel', 'kg': '2.5'}, {'categoria': 'blanco', 'tipo': 'Plástico',
                                                                         'kg': '1.5'},
                 {'categoria': 'rojo_solido', 'tipo': 'Pilas', 'kg': '0.5'},
                 {'categoria': 'rojo_liquido', 'tipo': 'Buffer', 'litros': '0.3'}, {'categoria': 'azul'}]
        datos = {'fecha': '2026-03-10', 'tipo': 'ingreso', 'responsable': resp.pk, 'items': items}
        r = self.client.post('/api/amb-pesajes/', datos, format='json')
        self.assertIn('sede', r.data, 'con sedes registradas, el pesaje indica la suya')
        r = self.client.post('/api/amb-pesajes/', {**datos, 'sede': self.area.sede_id}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(len(r.data['items']), 4, 'las líneas vacías no se guardan')
        url = f'/api/amb-pesajes/{r.data["id"]}'
        self.assertIn('contraseña', self.client.post(f'{url}/cerrar/', {}, format='json').data['detail'])
        r = self.client.post(f'{url}/cerrar/', {'password': CLAVE}, format='json')
        self.assertEqual(r.data['estado'], 'cerrado')
        self.assertEqual(self.client.patch(f'{url}/', {'observaciones': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.get(f'{url}/pdf/').status_code, 200)
        sede = self.area.sede_id
        r = self.client.post('/api/amb-disposiciones/', {'fecha': '2026-03-20', 'grupo': 'peligroso', 'kg': '0.5',
                                                         'destino': 'municipal', 'sede': sede}, format='json')
        self.assertEqual(r.status_code, 400, 'un peligroso va a una EO-RS')
        self.client.post('/api/amb-disposiciones/', {'fecha': '2026-03-20', 'grupo': 'no_peligroso', 'kg': '4',
                                                     'destino': 'reciclaje', 'sede': sede}, format='json')
        otra = self.client.get(f'/api/amb-pesajes/resumen_anual/?anio=2026&sede={sede + 1000}').data
        self.assertEqual(float(otra['generado_kg']), 0, 'el resumen se filtra por sede')
        d = self.client.get(f'/api/amb-pesajes/resumen_anual/?anio=2026&sede={sede}').data
        marzo = d['meses'][2]
        self.assertEqual(float(marzo['generado_no_peligroso_kg']), 4.0)
        self.assertEqual(float(marzo['generado_peligroso_kg']), 0.5)
        self.assertEqual(float(d['generado_kg']), 4.5)
        self.assertEqual(float(d['dispuesto_kg']), 4.0)
