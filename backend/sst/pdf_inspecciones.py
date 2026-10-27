"""
Formatos impresos de las inspecciones de SST (una disposición por familia de plantilla, con la
cabecera y los datos del empleador comunes a los formatos del procedimiento de seguimiento y
medición) y de los monitoreos de agentes ocupacionales (programa anual, registro y programa de
seguimiento de recomendaciones).
"""
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph, Spacer

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _solo_fecha, esc_pdf
from quejas.pdf import _cabecera

from .inspecciones import ESCALAS, TIPOS_INSPECCION
from .pdf_eventos import FS, GRIS, NOTA, TD, TDL, TH, THL, P, _doc, _empleador, _tabla, _texto

VERDE = colors.HexColor('#C6EFCE')
ROJO = colors.HexColor('#FFC7CE')
MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']
COD_PROG, COD_MON, COD_REC = 'SIG-PRO-06-r07', 'SIG-PRO-06-r08', 'SIG-PRO-06-r09'
CONTROL_FORMATOS.setdefault(COD_PROG, ('00', '2025-01-10', 'ASIG', 'GSIG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_MON, ('00', '2025-01-10', 'ASIG', 'GSIG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_REC, ('00', '2025-01-10', 'ASIG', 'GSIG', 'GG'))


def _respaldo(pl):
    """Caja de control de respaldo de la plantilla (si no está vinculada a la lista maestra)."""
    if pl.codigo_formato:
        CONTROL_FORMATOS.setdefault(pl.codigo_formato, (
            pl.version_formato or '00', pl.fecha_formato.isoformat() if pl.fecha_formato else '',
            pl.elaborado, pl.revisado, pl.aprobado))


def _valor(v, escala):
    """Texto de una respuesta; el ✔ se dibuja con la fuente de símbolos estándar."""
    if not v:
        return ''
    if escala == 'bueno_mal':
        return '✔' if v == 'B' else 'X'
    return dict(ESCALAS.get(escala, ESCALAS['c_nc_na'])['valores']).get(v, v)


def _pv(v, escala, estilo=TD):
    return Paragraph(_valor(v, escala), estilo)


def _fecha(f):
    return f.strftime('%d/%m/%Y') if f else ''


def _bloque_empleador(W, cfg, ins):
    d = _empleador(cfg)
    return _tabla([[P('RAZÓN SOCIAL O DENOMINACIÓN SOCIAL', TH), P('RUC', TH), P('DOMICILIO', TH),
                    P('ACTIVIDAD ECONÓMICA', TH), P('N° DE TRABAJADORES', TH)],
                   [P(d[0]), P(d[1]), P(d[2]), P(d[3]), P(ins.n_trabajadores if ins and ins.n_trabajadores else d[4])]],
                  [22, 10, 26, 18, 13], W, cabeceras=[0])


def _datos_inspeccion(W, ins):
    est = ins.estructura
    if est.get('tipo_elemento') in ('vehiculo', 'moto'):
        e = ins.elemento
        return _tabla([[P('NOMBRE DEL CONDUCTOR', TH), P(ins.conductor.nombre_completo if ins.conductor_id else '', TDL),
                        P('PLACA', TH), P((e.placa or e.codigo) if e else '')],
                       [P('LUGAR DE LA INSPECCIÓN', TH), P(ins.lugar, TDL), P('MARCA', TH), P(e.marca if e else '')],
                       [P('TIPO DE COMBUSTIBLE', TH), P(e.combustible if e else '', TDL), P('KM', TH), P(ins.km or '')],
                       [P('FECHA DE INSPECCIÓN', TH), P(_fecha(ins.fecha), TDL), P('HORA', TH),
                        P(ins.hora.strftime('%H:%M') if ins.hora else '')]],
                      [16, 34, 8, 16], W)
    marcas = ''.join(f'{n}: {"[X]" if ins.tipo_inspeccion == k else "[  ]"}   ' for k, n in TIPOS_INSPECCION)
    if ins.tipo_inspeccion == 'otro' and ins.tipo_detalle:
        marcas += f'({ins.tipo_detalle})'
    area = ins.area.nombre if ins.area_id else ''
    if ins.lugar:
        area = f'{area} — {ins.lugar}' if area else ins.lugar
    if est.get('familia') == 'contenido' and ins.elemento_id:
        area = f'{area} · {ins.elemento.get_tipo_display()} {ins.elemento.codigo} ({ins.elemento.ubicacion})'.strip(' ·')
    return _tabla([[P('ÁREA / LUGAR INSPECCIONADO', TH), P('RESPONSABLE DEL ÁREA INSPECCIONADA', TH),
                    P('OBJETIVO DE LA INSPECCIÓN', TH)],
                   [P(area, TDL), P(ins.responsable_area.nombre_completo if ins.responsable_area_id else '', TDL),
                    P(ins.objetivo, TDL)],
                   [P('TIPO DE INSPECCIÓN', TH), P('FECHA DE INSPECCIÓN', TH), P('HORA DE INSPECCIÓN', TH)],
                   [P(marcas, TDL), P(_fecha(ins.fecha)), P(ins.hora.strftime('%H:%M') if ins.hora else '')]],
                  [30, 25, 30], W, cabeceras=[0, 2])


def _leyenda(escala):
    vals = ESCALAS.get(escala, ESCALAS['c_nc_na'])['valores']
    if escala == 'bueno_mal':
        return 'Bueno / Sí: ✔     Mal / No: X'
    nombres = {'C': 'CONFORME', 'NC': 'NO CONFORME', 'NA': 'NO APLICA', 'SI': 'SÍ', 'NO': 'NO', 'OPT': 'ÓPTIMO',
               'MAL': 'MAL ESTADO'}
    return '     '.join(f'{nombres.get(k, k)}: "{v}"' for k, v in vals)


def _matriz(W, ins, items):
    """Familias por elemento y por trabajador: filas × criterios (con grupos si los hay)."""
    est = ins.estructura
    escala, crit = est.get('escala'), est.get('criterios') or []
    if est.get('familia') == 'trabajadores':
        cols_datos = ['Nombres y apellidos']
    else:
        cols_datos = est.get('columnas_datos') or (list(items[0].datos.keys()) if items else ['Descripción'])
    con_grupos = any(c.get('grupo') for c in crit)
    n_d, n_c = len(cols_datos), len(crit)
    largo = max((len(c['nombre']) for c in crit), default=10)
    # Cabecera de criterio: letra menor para que las palabras no se corten dentro de columnas angostas.
    fs = 5.5 if n_c > 10 else 6
    thc = ParagraphStyle('ithc', parent=TH, fontSize=fs, leading=fs * 1.15)
    th_v = lambda texto, _e=None: Paragraph(texto, thc)  # noqa: E731
    cab1 = [P('N°', TH)] + [P(c.upper(), TH) for c in cols_datos]
    cab2 = [''] * (1 + n_d)
    filas_cab = []
    if con_grupos:
        grupos, prev = [], None
        for c in crit:
            g = c.get('grupo') or ''
            grupos.append(P(g.upper(), TH) if g != prev else '')
            prev = g
        filas_cab.append(cab1 + grupos + [P('OBSERVACIONES', TH)])
        filas_cab.append(cab2 + [th_v(esc_pdf(c['nombre'])) for c in crit] + [''])
    else:
        filas_cab.append(cab1 + [th_v(esc_pdf(c['nombre'].upper() if largo < 40 else c['nombre']), TH) for c in crit]
                         + [P('OBSERVACIONES', TH)])
    filas = list(filas_cab)
    for it in items:
        if est.get('familia') == 'trabajadores':
            datos = [P(it.trabajador.nombre_completo if it.trabajador_id else it.texto, TDL)]
        else:
            datos = [P((it.datos or {}).get(c, ''), TDL if i == 0 else TD) for i, c in enumerate(cols_datos)]
        filas.append([P(it.orden)] + datos + [_pv((it.resultados or {}).get(str(k)), escala) for k in range(n_c)]
                     + [P(it.observacion, TDL)])
    if not items:
        filas.append([''] * (2 + n_d + n_c))
    a_d = 3.2 if n_c > 10 else 4.5
    anchos = [1.2] + [a_d * (1.6 if i == 0 else 1) for i in range(n_d)] + [1.6 if n_c > 10 else 2.2] * n_c + [6]
    if largo >= 40:  # preguntas como columnas (herramientas): cabecera más alta
        anchos = [1.2] + [3, 7][:n_d] + [3.2] * n_c + [6]
    extra = []
    nh = len(filas_cab)
    if con_grupos:
        extra += [('SPAN', (c, 0), (c, 1)) for c in range(1 + n_d)] + [('SPAN', (1 + n_d + n_c, 0), (1 + n_d + n_c, 1))]
        ini = 1 + n_d
        prev, desde = None, ini
        for i, c in enumerate(crit + [{'grupo': '__fin__'}]):
            g = c.get('grupo') or ''
            if g != prev and prev is not None:
                if ini + i - 1 > desde:
                    extra.append(('SPAN', (desde, 0), (ini + i - 1, 0)))
                desde = ini + i
            prev = g
    for r in range(nh, len(filas)):
        for k in range(n_c):
            it = items[r - nh] if items else None
            v = (it.resultados or {}).get(str(k)) if it else None
            malo = ESCALAS.get(escala, ESCALAS['c_nc_na'])['malo']
            bueno = ESCALAS.get(escala, ESCALAS['c_nc_na'])['valores'][0][0]
            if v and ((v == bueno) if crit[k].get('invertido') else (v == malo)):
                extra.append(('BACKGROUND', (1 + n_d + k, r), (1 + n_d + k, r), ROJO))
    return _tabla(filas, anchos, W, extra=extra, cabeceras=list(range(nh)))


def _contenido(W, ins, items):
    escala = ins.estructura.get('escala')
    vals = ESCALAS.get(escala, ESCALAS['c_nc_na'])['valores']
    filas = [[P('N°', TH), P('PRODUCTO / ELEMENTO', TH), P('CANTIDAD', TH), P('UNIDAD', TH),
              P('FECHA DE VENCIMIENTO', TH)] + [P(e, TH) for _, e in vals] + [P('OBSERVACIONES', TH)]]
    for it in items:
        r = (it.resultados or {}).get('r')
        d = it.datos or {}
        filas.append([P(it.orden), P(it.texto, TDL), P(d.get('Cantidad', '')), P(d.get('Unidad', '')),
                      P(_solo_fecha(d.get('Vencimiento') or ''))] + [P('X' if r == k else '') for k, _ in vals]
                     + [P(it.observacion, TDL)])
    return _tabla(filas, [1.2, 10, 3, 2.4, 3.4] + [1.6] * len(vals) + [7], W, cabeceras=[0])


def _preguntas(W, ins, items):
    escala = ins.estructura.get('escala')
    vals = ESCALAS.get(escala, ESCALAS['c_nc_na'])['valores']
    filas, extra, cab = [], [], []
    seccion = None
    for it in items:
        if it.seccion != seccion:
            seccion = it.seccion
            cab.append(len(filas))
            filas.append([P(seccion, THL)] + [P(e.upper(), TH) for _, e in vals] + [P('OBSERVACIONES', TH)])
        r = (it.resultados or {}).get('r')
        filas.append([P(it.texto, TDL)] + [P('X' if r == k else '') for k, _ in vals] + [P(it.observacion, TDL)])
        if r == ESCALAS.get(escala, ESCALAS['c_nc_na'])['malo']:
            extra.append(('BACKGROUND', (0, len(filas) - 1), (0, len(filas) - 1), ROJO))
    return _tabla(filas, [22] + [2.2] * len(vals) + [9], W, extra=extra, cabeceras=cab)


def _acciones(W, items):
    nc = [it for it in items if it.no_conforme]
    if not nc:
        return None
    filas = [[P('ACCIONES INMEDIATAS DE LOS ÍTEMS NO CONFORMES', TH), '', '', '', '', ''],
             [P('N°', TH), P('ÍTEM', TH), P('ACCIÓN', TH), P('RESPONSABLE', TH), P('PLAZO', TH), P('ESTADO', TH)]]
    for it in nc:
        estado = (f'Completada {_fecha(it.fecha_accion_completada)}' if it.accion_completada else 'Pendiente')
        if it.hallazgo_id:
            estado += f' · {it.hallazgo.codigo}'
        filas.append([P(it.orden), P(it.texto[:200], TDL), P(it.accion, TDL),
                      P(it.responsable_accion.get_full_name() if it.responsable_accion_id else ''),
                      P(_fecha(it.plazo_accion)), P(estado)])
    return _tabla(filas, [1.2, 10, 12, 6, 3, 5], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1])


def _firmas(W, ins):
    f = ins.firma_registro or {}
    insp = ins.inspector
    return _tabla([[P('RESPONSABLE DE LA INSPECCIÓN', TH), '', P('RESPONSABLE DEL REGISTRO', TH), ''],
                   [P('NOMBRE', TH), P(insp.get_full_name() or insp.username if insp else '', TDL), P('NOMBRE', TH),
                    P(f.get('nombre', ''), TDL)],
                   [P('CARGO', TH), P(getattr(insp, 'cargo', '') if insp else '', TDL), P('CARGO', TH),
                    P(f.get('cargo', ''), TDL)],
                   [P('FIRMA', TH), P('', TDL), P('FIRMA / FECHA', TH),
                    P((f'Firmado electrónicamente · {_solo_fecha(f.get("fecha") or "")}') if f else '', TDL)]],
                  [6, 20, 6, 20], W, extra=[('SPAN', (0, 0), (1, 0)), ('SPAN', (2, 0), (3, 0))], cabeceras=[0])


def generar_inspeccion_pdf(ins) -> bytes:
    pl, est = ins.plantilla, ins.estructura
    _respaldo(pl)
    familia = est.get('familia')
    horizontal = familia in ('elementos', 'trabajadores')
    buf = BytesIO()
    doc = _doc(buf, f'{est.get("nombre", pl.nombre)} {ins.codigo}', horizontal=horizontal)
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    items = list(ins.items.filter(is_active=True).select_related('trabajador', 'responsable_accion', 'hallazgo'))
    story = [_cabecera(W, cw, esc_pdf((est.get('nombre') or pl.nombre).upper()), est.get('codigo_formato')
                       or pl.codigo_formato, cfg, 12, 7, 12, 4, 18), Spacer(1, 4),
             _tabla([[P('N° DE INSPECCIÓN', TH), P(ins.codigo)]], [1, 2], W * 0.3, izquierda=True), Spacer(1, 3)]
    if est.get('tipo_elemento') not in ('vehiculo', 'moto'):
        story += [_bloque_empleador(W, cfg, ins), Spacer(1, 3)]
    story += [_datos_inspeccion(W, ins), Spacer(1, 4)]
    if familia != 'preguntas':
        story += [Paragraph(f'<b>CONDICIONES:</b> {_leyenda(est.get("escala"))}', TDL), Spacer(1, 3)]
    if familia in ('elementos', 'trabajadores'):
        story.append(_matriz(W, ins, items))
    elif familia == 'contenido':
        story.append(_contenido(W, ins, items))
    else:
        story.append(_preguntas(W, ins, items))
    story.append(Spacer(1, 4))
    acc = _acciones(W, items)
    if acc:
        story += [acc, Spacer(1, 4)]
    story += [KeepTogether([_texto(W, 'CONCLUSIONES / OBSERVACIONES / RECOMENDACIONES', ins.conclusiones, alto=30),
                            Spacer(1, 4), _firmas(W, ins)])]
    if est.get('nota'):
        story += [Spacer(1, 3), Paragraph(esc_pdf('Nota: ' + est['nota']), NOTA)]
    if ins.estado == 'anulada':
        story += [Spacer(1, 3), Paragraph(esc_pdf(f'INSPECCIÓN ANULADA: {ins.motivo_anulacion}'), TDL)]
    doc.build(story)
    return buf.getvalue()


# ================================================================================ monitoreos
def generar_programa_monitoreos_pdf(prog) -> bytes:
    buf = BytesIO()
    doc = _doc(buf, f'Programa anual de monitoreos {prog.anio}', horizontal=True)
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    filas = [[P('ÍTEM', TH), P('AGENTE', TH), P('FECHA PROGRAMADA (fecha / frecuencia)', TH),
              P(f'AÑO: {prog.anio}', TH)] + [''] * 11 + [P('COMENTARIOS / OBSERVACIONES', TH)],
             ['', '', ''] + [P(m, TH) for m in MESES_CORTOS] + ['']]
    extra = [('SPAN', (3, 0), (14, 0)), ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)), ('SPAN', (2, 0), (2, 1)),
             ('SPAN', (15, 0), (15, 1))]
    for n, it in enumerate(prog.items.filter(is_active=True), 1):
        ejec = it.meses_ejecutados()
        r = len(filas)
        filas.append([P(n), P(it.nombre, TDL), P(f'{_fecha(it.fecha_programada)} / {it.get_frecuencia_display().upper()}')]
                     + [P('X') if m in (it.meses or []) or m in ejec else '' for m in range(1, 13)]
                     + [P(it.comentarios, TDL)])
        for m in ejec:
            extra.append(('BACKGROUND', (2 + m, r), (2 + m, r), VERDE))
    story = [_cabecera(W, cw, f'PROGRAMA ANUAL DE MONITOREOS DE AGENTES OCUPACIONALES', COD_PROG, cfg, 12, 7, 12, 4, 18),
             Spacer(1, 4),
             _tabla([[P('Fecha de actualización:', THL), P(_fecha(prog.fecha_actualizacion)), P('Programado', TH),
                      P('X'), P('Ejecutado', TH), P('X')]], [6, 4, 4, 1.5, 4, 1.5], W * 0.55, izquierda=True,
                    extra=[('BACKGROUND', (5, 0), (5, 0), VERDE)]),
             Spacer(1, 4), _tabla(filas, [1.5, 7, 6] + [1.5] * 12 + [12], W, extra=extra, cabeceras=[0, 1])]
    doc.build(story)
    return buf.getvalue()


def generar_monitoreo_pdf(m) -> bytes:
    buf = BytesIO()
    doc = _doc(buf, f'Monitoreo de agentes ocupacionales {m.codigo}')
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    d = _empleador(cfg)
    res = [[P('AGENTE', TH), P('RESULTADO', TH), P('LÍMITE MÁXIMO PERMISIBLE', TH), P('¿DENTRO DEL LMP?', TH)]]
    extra = []
    for r in m.resultados or []:
        ok = r.get('dentro_lmp')
        res.append([P(r.get('agente', ''), TDL), P(r.get('resultado', '') + (f' ({r["valor"]})' if r.get('valor') else ''),
                                                    TDL), P(r.get('lmp', '')),
                    P('' if ok is None else ('Sí' if ok else 'No'))])
        if ok is False:
            extra.append(('BACKGROUND', (3, len(res) - 1), (3, len(res) - 1), ROJO))
    f = m.firma_registro or {}
    story = [
        _cabecera(W, cw, 'MONITOREO DE AGENTES FÍSICOS, QUÍMICOS, BIOLÓGICOS, PSICOSOCIALES Y FACTORES DE RIESGO '
                         'DISERGONÓMICOS', COD_MON, cfg, 12, 7, 10, 4, 18), Spacer(1, 4),
        _tabla([[P('N° REGISTRO', TH), P(m.codigo)]], [1, 2], W * 0.35, izquierda=True), Spacer(1, 3),
        _tabla([[P('RAZÓN SOCIAL O DENOMINACIÓN SOCIAL', TH), P('RUC', TH), P('DOMICILIO', TH),
                 P('ACTIVIDAD ECONÓMICA', TH)], [P(d[0]), P(d[1]), P(d[2]), P(d[3])]], [24, 10, 30, 20], W,
               cabeceras=[0]), Spacer(1, 3),
        _tabla([[P('DATOS DEL MONITOREO', TH), '', '', '', '', ''],
                [P('ÁREA MONITOREADA', TH), P('FECHA DEL MONITOREO', TH), P('FRECUENCIA DE MONITOREO', TH),
                 P('¿CUENTA CON PROGRAMA DE MONITOREO? (SÍ/NO)', TH),
                 P('TIPO DE RIESGO MONITOREADO (agentes físicos, químicos, biológicos, psicosociales y factores de '
                   'riesgo disergonómicos)', TH), P('N° TRABAJADORES EXPUESTOS EN EL CENTRO LABORAL', TH)],
                [P(m.area_monitoreada), P(_fecha(m.fecha)), P(m.get_frecuencia_display().upper()),
                 P('SÍ' if m.programados.exists() else 'NO'), P(m.tipo_riesgo, TDL), P(m.n_expuestos or '')]],
               [12, 9, 9, 9, 22, 9], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1]), Spacer(1, 3),
        _texto(W, 'NOMBRE DE LA ORGANIZACIÓN QUE REALIZA EL MONITOREO (de ser el caso)', m.organizacion), Spacer(1, 3),
        _tabla([[P('RESULTADOS DEL MONITOREO', TH), '', '', '']] + res, [10, 26, 8, 6], W,
               extra=[('SPAN', (0, 0), (-1, 0))] + [(a, (b[0], b[1] + 1), (c[0], c[1] + 1), dd) for a, b, c, dd in extra],
               cabeceras=[0, 1]), Spacer(1, 3),
        _texto(W, 'DESCRIPCIÓN DE LAS CAUSAS ANTE DESVIACIONES PRESENTADAS', m.causas_desviacion, alto=40), Spacer(1, 3),
        _texto(W, 'CONCLUSIONES Y RECOMENDACIONES SOBRE LOS RESULTADOS DEL MONITOREO', m.conclusiones,
               nota='Incluir las medidas que se adoptarán para corregir las desviaciones presentadas en el monitoreo.',
               alto=50), Spacer(1, 3),
        Paragraph(esc_pdf('ADJUNTAR: programa anual de monitoreo; informe con resultados de las mediciones (agentes o '
                          'factores objeto de la muestra, límite permisible, metodología, tamaño de muestra, '
                          'instrumentos utilizados); copia del certificado de calibración de los instrumentos de '
                          'monitoreo, de ser el caso.' + (' Informe adjunto en el sistema.' if m.informe else '')), NOTA),
        Spacer(1, 4),
        KeepTogether(_tabla([[P('RESPONSABLE DEL REGISTRO', TH), ''],
                             [P('Nombre:', THL), P(f.get('nombre', ''), TDL)],
                             [P('Cargo:', THL), P(f.get('cargo', ''), TDL)],
                             [P('Fecha:', THL), P(_solo_fecha(f.get('fecha') or ''), TDL)],
                             [P('Firma:', THL), P('Firmado electrónicamente' if f.get('usuario_id') else
                                                  (f.get('origen') or ''), TDL)]],
                            [8, 30], W * 0.6, extra=[('SPAN', (0, 0), (1, 0))], cabeceras=[0], izquierda=True)),
    ]
    doc.build(story)
    return buf.getvalue()


def generar_recomendaciones_pdf(anio) -> bytes:
    from .inspecciones import RecomendacionMonitoreo
    buf = BytesIO()
    doc = _doc(buf, f'Programa de seguimiento de recomendaciones de monitoreos {anio}', horizontal=True)
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    # Agentes en el orden en que se registraron (como el formato), y dentro de cada uno por ítem.
    todas = list(RecomendacionMonitoreo.objects.filter(is_active=True, anio=anio).order_by('id'))
    orden_agente = {}
    for r in todas:
        orden_agente.setdefault(r.agente, len(orden_agente))
    recs = sorted(todas, key=lambda r: (orden_agente[r.agente], r.orden, r.id))
    actualizado = max((r.updated_at for r in recs), default=None)
    filas = [[P('ÍTEM', TH), P('ACTIVIDADES', TH), P('FECHA PROGRAMADA (fecha / frecuencia)', TH),
              P(str(anio - 1), TH), P(f'AÑO {anio}', TH)] + [''] * 11 + [P('OBSERVACIONES', TH)],
             ['', '', '', P('Dic', TH)] + [P(m, TH) for m in MESES_CORTOS] + ['']]
    extra = [('SPAN', (4, 0), (15, 0))] + [('SPAN', (c, 0), (c, 1)) for c in (0, 1, 2, 16)]
    agente = None
    for r in recs:
        if r.agente != agente:
            agente = r.agente
            filas.append(['', P(agente, THL)] + [''] * 15)
            extra += [('SPAN', (1, len(filas) - 1), (16, len(filas) - 1)),
                      ('BACKGROUND', (0, len(filas) - 1), (-1, len(filas) - 1), GRIS)]
        fp = r.fecha_programada
        prev = bool(fp and fp.year == anio - 1 and fp.month == 12)
        ej = set(r.meses_ejecutados or [])
        if r.estado == 'ejecutada' and r.fecha_ejecucion and r.fecha_ejecucion.year == anio:
            ej.add(r.fecha_ejecucion.month)
        fila = len(filas)
        celdas = [P('X') if prev else '']
        for m in range(1, 13):
            celdas.append(P('X') if m in (r.meses or []) or m in ej else '')
            if m in ej:
                extra.append(('BACKGROUND', (3 + m, fila), (3 + m, fila), VERDE))
        if prev and r.estado == 'ejecutada':
            extra.append(('BACKGROUND', (3, fila), (3, fila), VERDE))
        obs = r.observaciones + (f' [{r.get_estado_display()}]' if r.estado != 'pendiente' else '')
        filas.append([P(r.orden), P(r.actividad, TDL), P(_fecha(fp) if fp else r.programacion)] + celdas
                     + [P(obs, TDL)])
    story = [_cabecera(W, cw, 'PROGRAMA DE SEGUIMIENTO DE RECOMENDACIONES DE MONITOREOS', COD_REC, cfg, 12, 7, 12, 4,
                       18), Spacer(1, 4),
             _tabla([[P('Fecha de actualización:', THL), P(_fecha(timezone.localtime(actualizado).date())
                                                           if actualizado else ''),
                      P('Programado', TH), P('X'), P('Ejecutado', TH), P('X')]], [6, 4, 4, 1.5, 4, 1.5], W * 0.55,
                    izquierda=True, extra=[('BACKGROUND', (5, 0), (5, 0), VERDE)]),
             Spacer(1, 4), _tabla(filas, [2, 16, 5, 1.6] + [1.4] * 12 + [11], W, extra=extra, cabeceras=[0, 1])]
    doc.build(story)
    return buf.getvalue()
