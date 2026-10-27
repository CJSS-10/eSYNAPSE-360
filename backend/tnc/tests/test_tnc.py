"""
Trabajos y salidas no conformes (procedimiento versión 01, decisiones de César del 2026-10-27):
- Registro con código TSNC-NNN-AAAA; queja y no conformidad de origen obligatorias según la fuente.
- Nivel de riesgo y responsable al iniciar el tratamiento (aprobar + contraseña).
- Tratamiento: acciones decididas y ejecutadas; nivel Alto exige detención, retroactivo y equipo fuera de servicio;
  certificado entregado y afectado exige notificar al cliente; «equipo fuera de servicio» inhabilita el equipo.
- Reanudación: técnica → Gerente Técnico o Jefe de Laboratorio; administrativa → solo el Gerente SIG (el
  Gerente Comercial gestiona la devolución del monto). Si no se acepta, vuelve al tratamiento.
- Evaluación: SAC obligatoria si es Alto o hay 3 eventos similares en 12 meses. Cierre con SAC y evidencias.
- Lo de una etapa cerrada no se modifica.
"""
from datetime import timedelta

from django.utils import timezone

from core.tests.base import CasoBase
from esynapse_sig.models import Equipo
from organizacion.models import Area, Puesto, Trabajador
from sst.tests.test_comite import texto_pdf
from tnc.models import ACCIONES, TrabajoNoConforme

CLAVE = CasoBase.CLAVE


def todas(aplica=False, **excepto):
    """Acciones con «aplica» decidido; las indicadas aplican y quedan ejecutadas."""
    return {c: ({'aplica': True, 'ejecutada': True} if c in excepto else {'aplica': aplica, 'ejecutada': None})
            for c, _ in ACCIONES}


class Base(CasoBase):

    def _usuario(self, nombre, puesto, *ops):
        u = self.crear_usuario(nombre)
        self.dar_permisos(u, 'trabajo_no_conforme', *ops)
        t = Trabajador.objects.create(nombres=nombre.capitalize(), apellidos='Prueba', puesto=Puesto.objects.get(
            nombre=puesto), usuario=u)
        return u, t

    def setUp(self):
        todos = ('leer', 'crear', 'editar', 'aprobar', 'eliminar')
        self.sig, self.t_sig = self._usuario('gsig_tnc', 'Gerente SIG', *todos)
        self.gt, self.t_gt = self._usuario('gt_tnc', 'Gerente Técnico', 'leer', 'crear', 'editar', 'aprobar')
        self.jefe, self.t_jefe = self._usuario('jefe_tnc', 'Jefe de Laboratorio', 'leer', 'crear', 'editar')
        self.sup, self.t_sup = self._usuario('sup_tnc', 'Supervisor de Laboratorio', 'leer', 'crear', 'editar')
        self.com, self.t_com = self._usuario('gcom_tnc', 'Gerente Comercial y Marketing', 'leer', 'editar')
        self.met, self.t_met = self._usuario('met_tnc', 'Metrólogo', 'leer', 'crear', 'editar')
        self.lab = Area.objects.filter(tipo='laboratorio').first()
        self.eq = Equipo.objects.create(codigo='TNC-EQ-1', nombre='Manómetro patrón', laboratorio='Presión',
                                        created_by=self.sig)
        self.hoy = timezone.localdate()
        self.autenticar(self.met)

    def _registrar(self, **extra):
        datos = {'tipo': 'tnc', 'naturaleza': 'tecnica', 'categoria': 'equipo', 'area': self.lab.pk,
                 'reportado_por': self.t_met.pk, 'fecha_deteccion': str(self.hoy), 'fecha_reporte': str(self.hoy),
                 'fuente': 'equipos', 'descripcion': 'Manómetro patrón fuera de tolerancia', 'equipos': [self.eq.pk]}
        datos.update(extra)
        r = self.client.post('/api/tnc/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def _url(self, t, accion=''):
        return f'/api/tnc/{t["id"]}/' + (f'{accion}/' if accion else '')

    def _iniciar(self, t, nivel='bajo'):
        self.autenticar(self.gt)
        r = self.client.post(self._url(t, 'iniciar_tratamiento'), {'nivel_riesgo': nivel,
                                                                   'responsable_tratamiento': self.t_met.pk,
                                                                   'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.autenticar(self.met)
        return r.data

    def _corregir(self, t, acciones=None):
        r = self.client.patch(self._url(t), {'correccion': 'Se reemplazó el patrón', 'correccion_por': self.t_met.pk,
                                             'correccion_fecha': str(self.hoy),
                                             'acciones': acciones or todas()}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    def _hasta_autorizacion(self, nivel='bajo', **extra):
        t = self._registrar(**extra)
        self._iniciar(t, nivel)
        self._corregir(t)
        r = self.client.post(self._url(t, 'pasar_autorizacion'), {}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    def _autorizar(self, t, usuario=None, acepta=True):
        self.autenticar(usuario or self.gt)
        return self.client.post(self._url(t, 'autorizar'), {'acepta': acepta, 'sustento': 'Corrección verificada',
                                                            'password': CLAVE}, format='json')


class PruebasRegistro(Base):

    def test_codigo_y_fuentes_con_origen(self):
        t = self._registrar()
        self.assertEqual(t['codigo'], f'TSNC-001-{self.hoy.year}')
        self.assertEqual(self._registrar()['codigo'], f'TSNC-002-{self.hoy.year}')
        r = self.client.post('/api/tnc/', {**self._datos_min(), 'fuente': 'queja'}, format='json')
        self.assertIn('queja', r.data)
        r = self.client.post('/api/tnc/', {**self._datos_min(), 'fuente': 'no_conformidad'}, format='json')
        self.assertIn('hallazgo', r.data)
        r = self.client.post('/api/tnc/', {**self._datos_min(), 'fecha_deteccion': str(self.hoy + timedelta(days=1))},
                             format='json')
        self.assertIn('fecha_deteccion', r.data)
        r = self.client.post('/api/tnc/', {**self._datos_min(), 'correccion': 'adelantada'}, format='json')
        self.assertEqual(r.status_code, 400, 'no se capturan etapas futuras al registrar')

    def _datos_min(self):
        return {'tipo': 'snc', 'naturaleza': 'administrativa', 'categoria': 'resultado', 'area': self.lab.pk,
                'reportado_por': self.t_met.pk, 'fecha_deteccion': str(self.hoy), 'fuente': 'verificacion',
                'descripcion': 'Certificado con razón social errada'}

    def test_nivel_lo_asigna_quien_aprueba(self):
        t = self._registrar()
        r = self.client.post(self._url(t, 'iniciar_tratamiento'), {'nivel_riesgo': 'bajo', 'password': CLAVE,
                                                                   'responsable_tratamiento': self.t_met.pk},
                             format='json')
        self.assertEqual(r.status_code, 403, 'el metrólogo no asigna el nivel')
        self.autenticar(self.gt)
        self.assertEqual(self.client.post(self._url(t, 'iniciar_tratamiento'), {'nivel_riesgo': 'bajo',
                                          'responsable_tratamiento': self.t_met.pk, 'password': 'mala'},
                                          format='json').status_code, 400)
        d = self._iniciar(t, 'medio')
        self.assertEqual(d['estado'], 'tratamiento')
        self.assertEqual(self.client.patch(self._url(t), {'descripcion': 'otra'}, format='json').status_code, 400,
                         'registro cerrado: solo lectura')


class PruebasTratamiento(Base):

    def test_acciones_decididas_y_ejecutadas(self):
        t = self._registrar()
        self._iniciar(t)
        r = self.client.post(self._url(t, 'pasar_autorizacion'), {}, format='json')
        self.assertIn('corrección', r.data['detail'])
        self.assertIn('decidir si aplica', r.data['detail'])
        acc = todas()
        acc['detencion'] = {'aplica': True, 'ejecutada': False}
        self._corregir(t, acc)
        r = self.client.post(self._url(t, 'pasar_autorizacion'), {}, format='json')
        self.assertIn('ejecutar: detención del trabajo', r.data['detail'])
        self._corregir(t, todas(detencion=1))
        self.assertEqual(self.client.post(self._url(t, 'pasar_autorizacion'), {}, format='json').status_code, 200)

    def test_alto_exige_detencion_retroactivo_y_fuera_de_servicio(self):
        t = self._registrar()
        self._iniciar(t, 'alto')
        self._corregir(t)
        r = self.client.post(self._url(t, 'pasar_autorizacion'), {}, format='json')
        for txt in ('detención del trabajo', 'análisis de impacto retroactivo', 'equipo fuera de servicio'):
            self.assertIn(txt, r.data['detail'])
        self._corregir(t, todas(detencion=1, retroactivo=1, fuera_servicio=1, notificacion=1))
        self.eq.refresh_from_db()
        self.assertEqual(self.eq.estado, 'inoperativo', 'el equipo queda fuera de servicio')
        r = self.client.post(self._url(t, 'pasar_autorizacion'), {}, format='json')
        self.assertIn('periodo revisado', r.data['detail'])
        self.client.patch(self._url(t), {'periodo_desde': str(self.hoy - timedelta(days=30)),
                                         'periodo_hasta': str(self.hoy), 'ultima_condicion': 'Calibración CC-01',
                                         'conclusion_retroactivo': 'Un certificado entregado afectado'},
                          format='json')
        self.client.post(self._url(t, 'afectacion'), {'ot': 'OT-100', 'certificado': 'CP-200', 'entregado': True,
                                                      'afectado': True, 'accion': 'anular_reemitir'}, format='json')
        r = self.client.post(self._url(t, 'pasar_autorizacion'), {}, format='json')
        self.assertIn('notificación al cliente', r.data['detail'])
        self.client.patch(self._url(t), {'notificacion_cliente': 'Carta al cliente', 'notificacion_fecha_medio':
                                         'Correo del día'}, format='json')
        self.assertEqual(self.client.post(self._url(t, 'pasar_autorizacion'), {}, format='json').status_code, 200)


class PruebasAutorizacion(Base):

    def test_tecnica_gt_o_jefe_de_laboratorio(self):
        t = self._hasta_autorizacion()
        r = self._autorizar(t, self.com)
        self.assertIn('Gerente Técnico o el Jefe de Laboratorio', r.data['detail'])
        # El Supervisor de Laboratorio ya no autoriza (procedimiento ajustado por César, 2026-10-27).
        self.assertIn('Jefe de Laboratorio', self._autorizar(t, self.sup).data['detail'])
        r = self._autorizar(t, self.jefe)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['estado'], 'evaluacion')

    def test_administrativa_solo_gsig(self):
        t = self._hasta_autorizacion(naturaleza='administrativa', categoria='administrativo', equipos=[])
        self.assertIn('la autoriza el Gerente SIG', self._autorizar(t, self.gt).data['detail'])
        self.assertIn('la autoriza el Gerente SIG', self._autorizar(t, self.com).data['detail'],
                      'el Gerente Comercial ya no autoriza la reanudación')
        self.assertEqual(self._autorizar(t, self.sig).status_code, 200)

    def test_no_aceptado_vuelve_al_tratamiento(self):
        t = self._hasta_autorizacion()
        r = self._autorizar(t, acepta=False)
        self.assertEqual(r.data['estado'], 'tratamiento')


class PruebasEvaluacionYCierre(Base):

    def _evaluar(self, t, **extra):
        self.autenticar(self.sig)
        datos = {'afecta_validez': False, 'incumple_sig': False, 'compromete_competencia': False,
                 'nivel_confirmado': 'bajo', 'evaluacion': 'Error aislado', 'amerita_sac': False}
        datos.update(extra)
        self.assertEqual(self.client.patch(self._url(t), datos, format='json').status_code, 200)
        return self.client.post(self._url(t, 'evaluar'), {'password': CLAVE}, format='json')

    def test_alto_confirmado_exige_sac_y_cierre(self):
        t = self._hasta_autorizacion()
        self._autorizar(t)
        r = self._evaluar(t, nivel_confirmado='alto')
        self.assertIn('Alto', r.data['detail'])
        r = self._evaluar(t, nivel_confirmado='alto', amerita_sac=True)
        self.assertEqual(r.data['estado'], 'cierre')
        r = self.client.post(self._url(t, 'cerrar'), {'password': CLAVE}, format='json')
        self.assertIn('solicitud de acción correctiva', r.data['detail'])
        self.assertIn('evidencias', r.data['detail'])
        r = self.client.post(self._url(t, 'crear_sac'), {}, format='json')
        self.assertTrue(r.data['sac_codigo'].startswith('SAC-'))
        self.client.patch(self._url(t), {'evidencias': 'Registro y certificado reemitido'}, format='json')
        r = self.client.post(self._url(t, 'cerrar'), {'password': CLAVE}, format='json')
        self.assertEqual(r.data['estado'], 'cerrado')
        self.assertEqual(self.client.patch(self._url(t), {'evidencias': 'x'}, format='json').status_code, 400)
        pdf = self.client.get(self._url(t, 'pdf'))
        txt = texto_pdf(pdf)
        for frag in ('REGISTRO DE TRABAJOS Y SALIDAS NO CONFORMES', t['codigo'], 'AUTORIZACIÓN PARA REANUDACIÓN',
                     r.data['sac_codigo'], 'Gsig_tnc'):
            self.assertIn(frag, txt)

    def test_tres_eventos_similares_exigen_sac(self):
        for _ in range(2):
            self._registrar()
        t = self._hasta_autorizacion()
        self._autorizar(t)
        r = self._evaluar(t)
        self.assertIn('3 eventos similares', r.data['detail'])
        self.assertEqual(self._evaluar(t, amerita_sac=True).data['eventos_similares'], 3)

    def test_bajo_sin_sac_y_mis_tareas(self):
        t = self._registrar()
        self.autenticar(self.gt)
        self.assertIn(t['codigo'], [x['codigo'] for x in self.client.get('/api/mis-tareas/').data['tareas']])
        self._iniciar(t)
        self.assertIn(t['codigo'], [x['codigo'] for x in self.client.get('/api/mis-tareas/').data['tareas']],
                      'el responsable del tratamiento lo ve')
        self._corregir(t)
        self.client.post(self._url(t, 'pasar_autorizacion'), {}, format='json')
        self._autorizar(t)
        self.assertEqual(self._evaluar(t).data['estado'], 'cierre')
        self.client.patch(self._url(t), {'evidencias': 'Registro'}, format='json')
        self.assertEqual(self.client.post(self._url(t, 'cerrar'), {'password': CLAVE}, format='json')
                         .data['estado'], 'cerrado')

    def test_anular_antes_de_autorizar(self):
        t = self._registrar()
        self.autenticar(self.sig)
        self.assertEqual(self.client.post(self._url(t, 'anular'), {}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self._url(t, 'anular'), {'motivo': 'Duplicado'}, format='json')
                         .status_code, 200)
        self.assertFalse(TrabajoNoConforme.objects.get(pk=t['id']).is_active)
