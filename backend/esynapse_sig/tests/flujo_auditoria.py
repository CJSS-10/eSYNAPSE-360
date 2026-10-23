"""
Ayudante de pruebas: lleva una auditoría por la secuencia del procedimiento
hasta el estado pedido, usando la API (como lo haría la pantalla).

Secuencia: programada → planificada (plan aprobado) → apertura → en_ejecucion
(acta de apertura) → conclusiones → reunion_cierre (hallazgos validados) →
en_informe (acta de cierre) → cerrada.
"""

SECUENCIA = ['programada', 'planificada', 'apertura', 'en_ejecucion', 'conclusiones',
             'reunion_cierre', 'en_informe', 'cerrada']

PARTICIPANTES = [{'nombre': 'Oscar Pérez', 'condicion': 'Equipo auditor', 'cargo': 'Auditor líder'},
                 {'nombre': 'Dennis Ruiz', 'condicion': 'Auditado', 'cargo': 'Jefe de laboratorio'}]


def avanzar(test, aud, hasta, lider=None):
    """`test` es el caso de prueba (usa su cliente autenticado); `lider` es el
    usuario que figura como auditor líder (por defecto, el autenticado)."""
    c = test.client
    base = f'/api/auditorias/{aud.pk}'
    aud.refresh_from_db()
    destino = SECUENCIA.index(hasta)
    while SECUENCIA.index(aud.estado) < destino:
        e = aud.estado
        if e == 'programada':
            c.patch(f'{base}/', {'objetivo': 'Evaluar el SIG', 'alcance': 'Procesos del laboratorio',
                                 'cronograma_entrevistas': [{'fecha': '2026-10-14', 'hora': '08:00', 'area': 'Masa'}]},
                    format='json')
            if lider is not None and not aud.equipo.filter(rol='lider').exists():
                c.post(f'{base}/agregar_integrante/', {'rol': 'lider', 'usuario': lider.pk}, format='json')
            r = c.post(f'{base}/planificar/')
        elif e == 'planificada':
            r = c.post(f'{base}/iniciar/')
        elif e == 'apertura':
            r = c.post(f'{base}/registrar_acta/', {'tipo': 'apertura', 'participantes': PARTICIPANTES,
                                                   'contenido': 'Objetivo, alcance y metodología'}, format='json')
        elif e == 'en_ejecucion':
            r = c.post(f'{base}/terminar_ejecucion/')
        elif e == 'conclusiones':
            r = c.post(f'{base}/validar_hallazgos/', {'conclusiones': 'El SIG es conforme con observaciones.'},
                       format='json')
        elif e == 'reunion_cierre':
            r = c.post(f'{base}/registrar_acta/', {'tipo': 'cierre', 'participantes': PARTICIPANTES,
                                                   'contenido': 'Se presentan los hallazgos'}, format='json')
        elif e == 'en_informe':
            r = c.post(f'{base}/cerrar/')
        test.assertIn(r.status_code, (200, 202), f'{e}: {getattr(r, "data", r)}')
        aud.refresh_from_db()
        if aud.estado == e:   # quedó pendiente de aprobación (candado)
            break
    return aud
