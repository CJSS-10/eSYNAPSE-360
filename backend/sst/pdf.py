"""
Formatos impresos de SST: Matriz IPERC (una hoja por área, con la disposición de la
plantilla en Excel: situación, evaluación inicial, controles por jerarquía y
evaluación residual) y Análisis de Trabajo Seguro (ATS).
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _p_ajustado, _solo_fecha, esc_pdf
from legal.pdf import _limpio
from quejas.pdf import _cabecera

from .models import TIPOS_TRABAJO, RevisionIPERC, estado_aprobacion_iperc

COD_IPERC = 'SIG-PRO-08-r01'
COD_ATS = 'SIG-PRO-08-r02'
# Respaldo de la caja de control mientras el formato no esté vinculado a la lista maestra.
CONTROL_FORMATOS.setdefault(COD_IPERC, ('01', '2025-10-01', 'GSIG', 'GSIG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_ATS, ('00', '2026-03-20', 'ASIG', 'GSIG/GG', 'GG'))

AZUL = colors.HexColor('#16365C')
CELESTE = colors.HexColor('#95B3D7')
AZUL_EVAL = colors.HexColor('#366092')
ROJO_CTRL = colors.HexColor('#C0504D')
COLOR_NIVEL = {'IT': colors.HexColor('#FF0000'), 'IM': colors.HexColor('#FFCC00'), 'M': colors.HexColor('#FFFF99')}
COLOR_ATS = {'tolerable': colors.HexColor('#92D050'), 'poco_significativo': colors.HexColor('#FFFF00'),
             'significativo': colors.HexColor('#FFC000'), 'intolerable': colors.HexColor('#FF0000')}


def _estilos(fs):
    return {
        'th': ParagraphStyle('sth', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER),
        'thb': ParagraphStyle('stb', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER,
                              textColor=colors.white),
        'td': ParagraphStyle('std', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER),
        'tdl': ParagraphStyle('stl', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_LEFT),
    }


def _celda(texto, estilo, ancho):
    texto = _limpio(texto)
    if '\n' in texto:
        return Paragraph(esc_pdf(texto), estilo)
    return _p_ajustado(texto, estilo, ancho - 3)


def _barra(W, etiqueta, valor, fs=8, ancho_etq=0.16):
    lb = ParagraphStyle('sbl', fontName='Helvetica-Bold', fontSize=fs, alignment=TA_CENTER, textColor=colors.white)
    vl = ParagraphStyle('sbv', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_LEFT)
    t = Table([[Paragraph(etiqueta, lb), Paragraph(esc_pdf(_limpio(valor)), vl)]],
              colWidths=[W * ancho_etq, W * (1 - ancho_etq)], hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), AZUL), ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
                           ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    return t


# --- Matriz IPERC ---
# Anchos de columna de la plantilla (A … AH).
ANCHOS_IPERC = [15.1, 12.0, 21.7, 22.3, 21.6, 29.6, 7.1, 7.1, 7.1, 32.3, 7.9, 7.9, 7.9, 7.9, 8.6, 7.9, 7.9, 9.0,
                10.7, 17.0, 17.3, 17.0, 34.1, 14.6, 16.7, 7.6, 7.9, 5.7, 5.1, 8.0, 6.0, 6.1, 7.0, 12.7]


def _puestos_area(filas):
    nombres = []
    for f in filas:
        for p in f.puestos.all():
            if p.nombre not in nombres:
                nombres.append(p.nombre)
    return ', '.join(nombres) or 'Todos los puestos'


def _tabla_iperc(filas, cw, st):
    th, thb = st['th'], st['thb']
    cab1 = ['SUBPROCESO', 'PUESTO', 'ACTIVIDAD', 'PELIGROS', 'RIESGO', 'CONSECUENCIA DEL RIESGO', 'SITUACIÓN', '', '',
            'CONTROLES EXISTENTES', 'EVALUACIÓN DEL RIESGO'] + [''] * 8 + ['CONTROLES OPERACIONALES'] + [''] * 4 + \
           ['RESPONSABLE (S)', 'EVALUACIÓN DEL RIESGO RESIDUAL'] + [''] * 8
    cab2 = [''] * 10 + ['CRITERIOS DE PROBABILIDAD', '', '', '', 'ÍNDICE DE PROBABILIDAD (A+B+C+D)',
                        'ÍNDICE DE SEVERIDAD', 'NIVEL DE RIESGO', '', ''] + [''] * 6 + \
           ['CRITERIOS DE PROBABILIDAD', '', '', '', 'ÍNDICE DE PROBABILIDAD (A+B+C+D)', 'ÍNDICE DE SEVERIDAD',
            'NIVEL DE RIESGO', '', '']
    evalc = ['PERSONAS EXPUESTAS (A)', 'PROCEDIMIENTO EXISTENTE (B)', 'CAPACITACIÓN (C)', 'EXPOSICIÓN AL RIESGO (D)',
             '', '', 'NR = S x P', 'CLASIFICACIÓN DEL RIESGO', 'RIESGO ACEPTABLE / NO ACEPTABLE']
    cab3 = [''] * 6 + ['RUTINARIO', 'NO RUTINARIO', 'EMERGENCIA', ''] + evalc + \
           ['ELIMINACIÓN', 'SUSTITUCIÓN', 'INGENIERÍA', 'CONTROL ADMINISTRATIVO', 'EQUIPO DE PROTECCIÓN PERSONAL', ''] + evalc
    blancos = set(range(10, 19)) | set(range(19, 24)) | set(range(25, 34))

    def hdr(fila):
        return [_celda(t, thb if i in blancos else th, cw[i]) if t else '' for i, t in enumerate(fila)]

    data = [hdr(cab1), hdr(cab2), hdr(cab3)]
    est = [('GRID', (0, 0), (-1, -1), 0.4, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('LEFTPADDING', (0, 0), (-1, -1), 1.5), ('RIGHTPADDING', (0, 0), (-1, -1), 1.5),
           ('BACKGROUND', (0, 0), (9, 2), CELESTE), ('BACKGROUND', (24, 0), (24, 2), CELESTE),
           ('BACKGROUND', (10, 0), (18, 2), AZUL_EVAL), ('BACKGROUND', (25, 0), (33, 2), AZUL_EVAL),
           ('BACKGROUND', (19, 0), (23, 2), ROJO_CTRL)]
    for c in list(range(0, 6)) + [9, 24]:
        est.append(('SPAN', (c, 0), (c, 2)))
    est += [('SPAN', (6, 0), (8, 1)), ('SPAN', (10, 0), (18, 0)), ('SPAN', (10, 1), (13, 1)), ('SPAN', (14, 1), (14, 2)),
            ('SPAN', (15, 1), (15, 2)), ('SPAN', (16, 1), (18, 1)), ('SPAN', (19, 0), (23, 1)), ('SPAN', (25, 0), (33, 0)),
            ('SPAN', (25, 1), (28, 1)), ('SPAN', (29, 1), (29, 2)), ('SPAN', (30, 1), (30, 2)), ('SPAN', (31, 1), (33, 1))]
    td, tdl = st['td'], st['tdl']

    def ac(v):
        return '' if v is None else ('Aceptable' if v else 'No Aceptable')

    for f in filas:
        puestos = 'Todos los puestos' if f.todos_los_puestos else (f.puestos_texto or ', '.join(
            p.nombre for p in f.puestos.all()))
        sit = f.situaciones or []
        valores = [
            (f.subproceso, td), (puestos, td), (f.actividad, tdl), (f.peligro, td), (f.riesgo, td), (f.consecuencia, tdl),
            ('x' if 'rutinaria' in sit else '', td), ('x' if 'no_rutinaria' in sit else '', td),
            ('x' if 'emergencia' in sit else '', td), (f.controles_existentes, tdl),
            (f.personas, td), (f.procedimientos, td), (f.capacitacion, td), (f.exposicion, td), (f.probabilidad, td),
            (f.severidad, td), (f.nivel_riesgo, td), (f.clasificacion, td), (ac(f.aceptable), td),
            (f.control_eliminacion, tdl), (f.control_sustitucion, tdl), (f.control_ingenieria, tdl),
            (f.control_administrativo, tdl), (f.control_epp, tdl),
            ('\n'.join(p.nombre for p in f.responsables.all()) or f.responsable, td),
            (f.r_personas, td), (f.r_procedimientos, td), (f.r_capacitacion, td), (f.r_exposicion, td),
            (f.r_probabilidad, td), (f.r_severidad, td), (f.r_nivel_riesgo, td), (f.r_clasificacion, td),
            (ac(f.r_aceptable), td)]
        r = len(data)
        data.append([_celda('' if v is None else v, s, cw[i]) for i, (v, s) in enumerate(valores)])
        for col, nivel in ((16, f.clasificacion), (31, f.r_clasificacion)):
            if nivel in COLOR_NIVEL:
                est.append(('BACKGROUND', (col, r), (col + 1, r), COLOR_NIVEL[nivel]))
    t = Table(data, colWidths=cw, repeatRows=3, splitInRow=1)
    t.setStyle(TableStyle(est))
    return t


def generar_iperc_pdf(filas, area=None) -> bytes:
    """Matriz IPERC: una sección por área (hoja de la matriz), cada una en página nueva."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A3), leftMargin=7 * mm, rightMargin=7 * mm, topMargin=7 * mm,
                            bottomMargin=7 * mm, title='Matriz IPERC' + (f' - {area}' if area else ''))
    W = doc.width
    cfg = _cargar_cfg()
    cw = [W * a / sum(ANCHOS_IPERC) for a in ANCHOS_IPERC]
    st = _estilos(6)
    titulo = 'MATRIZ DE IDENTIFICACIÓN DE PELIGROS, EVALUACIÓN DE RIESGOS Y CONTROLES (IPERC)'
    areas = []
    for f in filas:
        if not areas or areas[-1][0] != f.area:
            areas.append((f.area, []))
        areas[-1][1].append(f)
    story = []
    if not areas:
        story += [_cabecera(W, cw, titulo, COD_IPERC, cfg, 13, 7, 12, 2, 27), Spacer(1, 6),
                  Paragraph('No hay filas vigentes para los filtros indicados.', st['tdl'])]
    for i, (nombre, grupo) in enumerate(areas):
        if i:
            story.append(PageBreak())
        est, ap = estado_aprobacion_iperc(nombre)
        rev = RevisionIPERC.objects.filter(area=nombre).first()
        actualizada = ap.fecha if ap and est == 'aprobada' else (rev.fecha if rev else None)
        story += [_cabecera(W, cw, titulo, COD_IPERC, cfg, 13, 7, 12, 2, 27), Spacer(1, 5),
                  _barra(W, 'Área:', nombre, ancho_etq=0.1), Spacer(1, 2),
                  _barra(W, 'Fecha de Actualización:', _solo_fecha(str(actualizada)) if actualizada else '',
                         ancho_etq=0.1),
                  Spacer(1, 2), _barra(W, 'Puestos:', _puestos_area(grupo), ancho_etq=0.1), Spacer(1, 5),
                  _tabla_iperc(grupo, cw, st), Spacer(1, 8), _pie_iperc(W, cfg, est, ap)]
    doc.build(story)
    return buf.getvalue()




def _pie_iperc(W, cfg, estado, ap):
    """Pie del formato: datos del empleador y "realizado y aprobado por" el Comité de SST, con firma y fecha.
    Si el área cambió después de aprobarse (o nunca se aprobó), imprime a los titulares vigentes con las
    casillas en blanco, para firmar."""
    from .pdf_eventos import _empleador
    th = ParagraphStyle('pth', fontName='Helvetica-Bold', fontSize=7, leading=8.5, alignment=TA_CENTER)
    thb = ParagraphStyle('ptb', parent=th, textColor=colors.white)
    td = ParagraphStyle('ptd', fontName='Helvetica', fontSize=7, leading=8.5, alignment=TA_CENTER)
    d = _empleador(cfg)
    emp = Table([[Paragraph(x, thb) for x in ('RAZÓN SOCIAL O DENOMINACIÓN SOCIAL:', 'RUC:', 'DOMICILIO (Dirección, '
                  'distrito, departamento, provincia)', 'ACTIVIDAD ECONÓMICA', 'N° TRABAJADORES EN EL CENTRO LABORAL')],
                 [Paragraph(esc_pdf(str(x)), td) for x in d]], colWidths=[W * x for x in (0.2, 0.1, 0.38, 0.2, 0.12)])
    emp.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.6, colors.black), ('BACKGROUND', (0, 0), (-1, 0), AZUL),
                             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    from reportlab.platypus import KeepTogether

    from .comite_pdf import bloque_firmas_comite
    if ap and estado == 'aprobada':
        bloque = bloque_firmas_comite(W, ap.firmas, fecha=ap.fecha)
    else:
        bloque = bloque_firmas_comite(W, nota=(
            'PENDIENTE DE APROBACIÓN DEL COMITÉ DE SST: la matriz del área cambió después de su aprobación del '
            f'{_solo_fecha(str(ap.fecha))}.' if ap else 'PENDIENTE DE APROBACIÓN DEL COMITÉ DE SST.'))
    return KeepTogether([emp, Spacer(1, 3)] + bloque)


# --- Análisis de Trabajo Seguro ---
def _matriz_ats(ancho, fs):
    """Matriz de clasificación de riesgo del ATS (severidad × probabilidad, 1–4)."""
    from .models import nivel_ats
    th = ParagraphStyle('amh', fontName='Helvetica-Bold', fontSize=fs, alignment=TA_CENTER)
    td = ParagraphStyle('amd', fontName='Helvetica', fontSize=fs, alignment=TA_CENTER)
    data = [[Paragraph('S/P', th)] + [Paragraph(str(p), th) for p in range(1, 5)]]
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('BACKGROUND', (0, 0), (-1, 0), CELESTE), ('BACKGROUND', (0, 0), (0, -1), CELESTE)]
    for s in range(4, 0, -1):
        r = len(data)
        data.append([Paragraph(str(s), th)] + [Paragraph(str(s * p), td) for p in range(1, 5)])
        for p in range(1, 5):
            est.append(('BACKGROUND', (p, r), (p, r), COLOR_ATS[nivel_ats(s * p)]))
    t = Table(data, colWidths=[ancho * 0.24] + [ancho * 0.19] * 4)
    t.setStyle(TableStyle(est))
    leyenda = Table([[Paragraph(txt, td)] for txt in ('1–2 Tolerable', '3–6 Poco significativo', '8–9 Significativo',
                                                      '12–16 Intolerable')], colWidths=[ancho * 0.7])
    leyenda.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black)] + [
        ('BACKGROUND', (0, i), (0, i), COLOR_ATS[k]) for i, k in enumerate(
            ('tolerable', 'poco_significativo', 'significativo', 'intolerable'))]))
    return t, leyenda


def generar_ats_pdf(a) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=8 * mm, rightMargin=8 * mm, topMargin=6 * mm,
                            bottomMargin=6 * mm, title=f'ATS {a.codigo}')
    W = doc.width
    cfg = _cargar_cfg()
    fs = 7
    st = _estilos(fs)
    lb = ParagraphStyle('alb', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2, alignment=TA_LEFT)
    th, td, tdl = st['th'], st['td'], st['tdl']
    n = 24
    cw = [W / n] * n
    story = [_cabecera(W, cw, 'ANÁLISIS DE TRABAJO SEGURO - ATS', COD_ATS, cfg, 12, 7, 12, 3, 17), Spacer(1, 4)]

    def P(t, s=td):
        return Paragraph(esc_pdf(_limpio(t if t is not None else '')), s)

    def L(t, span=1, s=lb):
        return _p_ajustado(t, s, cw[0] * span - 12, relleno=3, una_linea=True)

    def hora(h):
        return h.strftime('%H:%M') if h else ''

    def marca(v):
        return '(X)' if v else '( )'

    pl = a.planificado
    tipos = dict(TIPOS_TRABAJO)
    marcados = '     '.join(f'{marca(k in (a.tipos_trabajo or []))} {v}' for k, v in tipos.items() if k != 'otro')
    marcados += f'     {marca("otro" in (a.tipos_trabajo or []))} Otro: {a.tipo_otro}'
    gen = [
        [P('ZONA DE TRABAJO:', lb), '', P(a.zona, tdl), '', '', '', '', '', L('FECHA:'), P(_solo_fecha(a.fecha)), '',
         L('HORA DE INICIO:', 2), '', P(hora(a.hora_inicio)), L('HORA FINAL:', 2), '', P(hora(a.hora_fin)), '',
         L('N.º:'), P(a.codigo), '', '', '', ''],
        [P('TAREA A REALIZAR:', lb), '', P(a.tarea, tdl), '', '', '', '', '', '', '', '', P('LUGAR DE SERVICIO:', lb), '',
         P(a.lugar, tdl)] + [''] * 10,
        [P('ORDEN DE TRABAJO:', lb), '', P(a.orden_trabajo), '', P('EMPRESA QUE REALIZA EL SERVICIO:', lb), '', '',
         P(a.empresa), '', '', '', P('PLANIFICADO:', lb), '', P(f'{marca(pl == "si")} SI   {marca(pl == "no")} NO   '
                                                                 f'{marca(pl == "emergencia")} EMERGENCIA', tdl)] + [''] * 10,
        [P('TIPO DE TRABAJO:', lb), '', P(marcados, tdl)] + [''] * 21,
    ]
    t = Table(gen, colWidths=cw)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 0), (1, 0)), ('SPAN', (2, 0), (7, 0)), ('SPAN', (9, 0), (10, 0)), ('SPAN', (11, 0), (12, 0)),
        ('SPAN', (14, 0), (15, 0)), ('SPAN', (16, 0), (17, 0)), ('SPAN', (19, 0), (23, 0)),
        ('SPAN', (0, 1), (1, 1)), ('SPAN', (2, 1), (10, 1)), ('SPAN', (11, 1), (12, 1)), ('SPAN', (13, 1), (23, 1)),
        ('SPAN', (0, 2), (1, 2)), ('SPAN', (2, 2), (3, 2)), ('SPAN', (4, 2), (6, 2)), ('SPAN', (7, 2), (10, 2)),
        ('SPAN', (11, 2), (12, 2)), ('SPAN', (13, 2), (23, 2)), ('SPAN', (0, 3), (1, 3)), ('SPAN', (2, 3), (23, 3))]))
    story += [t, Spacer(1, 3)]

    # Personal ejecutante: 9 casillas en tres columnas (nombre y firma).
    ejec = [e.get('nombre', '') for e in (a.ejecutantes or [])] + [''] * 9
    filas = [[P('PERSONAL EJECUTANTE', th), '', P('#', th), P('Nombres y Apellidos', th), '', '', '', P('Firma', th), '',
              P('#', th), P('Nombres y Apellidos', th), '', '', '', P('Firma', th), '', P('#', th),
              P('Nombres y Apellidos', th), '', '', '', P('Firma', th), '', '']]
    for i in range(3):
        fila = ['', '']
        for k in (i, i + 3, i + 6):
            fila += [P(k + 1), P(ejec[k], tdl), '', '', '', '', '']
        filas.append(fila)
    t = Table(filas, colWidths=cw, rowHeights=[12, 13, 13, 13])
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('SPAN', (0, 0), (1, 3)), ('BACKGROUND', (0, 0), (-1, 0), CELESTE), ('BACKGROUND', (0, 0), (1, 3), CELESTE)]
    for r in range(4):
        for base in (2, 9, 16):
            est += [('SPAN', (base + 1, r), (base + 4, r)), ('SPAN', (base + 5, r), (base + 6 if base < 16 else 23, r))]
    t.setStyle(TableStyle(est))
    story += [t, Spacer(1, 3)]

    # Etapas.
    cab = [P('Etapas (Descripción de actividades)', th), '', '', '', '', P('Peligros', th), '', '', P('Riesgos', th), '',
           '', P('S', th), P('P', th), L('R=S*P', 1, th), P('Medidas de Control', th), '', '', '', '', '', '', P('S', th),
           P('P', th), L('R=S*P', 1, th)]
    filas = [cab]
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('BACKGROUND', (0, 0), (-1, 0), CELESTE)]
    pasos = list(a.pasos.filter(is_active=True))
    for k in range(max(len(pasos), 4)):
        p = pasos[k] if k < len(pasos) else None
        r = len(filas)
        filas.append([P(f'{p.orden}. {p.etapa}' if p else '', tdl), '', '', '', '', P(p.peligros if p else '', tdl), '',
                      '', P(p.riesgos if p else '', tdl), '', '', P(p.severidad if p else ''),
                      P(p.probabilidad if p else ''), P(p.valor if p else ''), P(p.medidas if p else '', tdl), '', '', '',
                      '', '', '', P(p.r_severidad if p else ''), P(p.r_probabilidad if p else ''),
                      P(p.r_valor if p else '')])
        if p and p.nivel:
            est.append(('BACKGROUND', (13, r), (13, r), COLOR_ATS[p.nivel]))
        if p and p.r_nivel:
            est.append(('BACKGROUND', (23, r), (23, r), COLOR_ATS[p.r_nivel]))
    for r in range(len(filas)):
        est += [('SPAN', (0, r), (4, r)), ('SPAN', (5, r), (7, r)), ('SPAN', (8, r), (10, r)), ('SPAN', (14, r), (20, r))]
    t = Table(filas, colWidths=cw, repeatRows=1, splitInRow=1)
    t.setStyle(TableStyle(est))
    story += [t, Spacer(1, 3)]

    # Comentarios y equipos.
    eq = list(a.equipos or []) + [''] * 6
    filas = [[P('COMENTARIOS / OBSERVACIONES', th)] + [''] * 11 + [P('EQUIPOS, HERRAMIENTAS O INSUMOS UTILIZADOS', th)]
             + [''] * 11]
    for i in range(3):
        filas.append([P(a.comentarios, tdl) if i == 0 else ''] + [''] * 11 +
                     [P(i + 1), P(eq[i], tdl), '', '', '', '', P(i + 4), P(eq[i + 3], tdl), '', '', '', ''])
    t = Table(filas, colWidths=cw)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('BACKGROUND', (0, 0), (-1, 0), CELESTE), ('SPAN', (0, 0), (11, 0)), ('SPAN', (12, 0), (23, 0)),
                           ('SPAN', (0, 1), (11, 3))] + [s for r in (1, 2, 3) for s in (
                               ('SPAN', (13, r), (17, r)), ('SPAN', (19, r), (23, r)))]))
    story += [t, Spacer(1, 3)]

    # Firmas y matriz de clasificación.
    f = a.firma_supervisor or {}
    from django.utils import timezone
    from django.utils.dateparse import parse_datetime
    momento = parse_datetime(f.get('fecha') or '') if f else None
    if momento and timezone.is_aware(momento):
        momento = timezone.localtime(momento)
    sup = [P('Identificación', th), P('Responsable del Servicio (Cliente)', th), P('Área de SSOMA (Cliente)', th),
           P('Supervisor o Prevencionista de SST (Metrindust)', th)]
    firmas = Table([
        [P('FIRMAS DE AUTORIZACIONES', th), '', '', ''], sup,
        [P('Nombre y Apellidos', lb), P(a.responsable_cliente), P(a.ssoma_cliente),
         P(f.get('nombre') or '')],
        [P('Firma', lb), '', '', P(f'Firmado electrónicamente\n{_solo_fecha(momento)}' if momento else '')],
        [P('Hora', lb), '', '', P(momento.strftime('%H:%M') if momento else '')],
    ], colWidths=[W * 0.1, W * 0.17, W * 0.17, W * 0.17], rowHeights=[12, 20, 16, 24, 13])
    firmas.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 1), CELESTE),
                                ('BACKGROUND', (0, 2), (0, -1), CELESTE)]))
    matriz, leyenda = _matriz_ats(W * 0.14, fs)
    bloque_m = Table([[P('MATRIZ DE CLASIFICACIÓN DE RIESGO', th), ''], [matriz, leyenda]],
                     colWidths=[W * 0.15, W * 0.12])
    bloque_m.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)), ('BACKGROUND', (0, 0), (1, 0), CELESTE),
                                  ('BOX', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    pie = Table([[firmas, bloque_m]], colWidths=[W * 0.62, W * 0.38])
    pie.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    story.append(pie)
    if a.estado == 'anulado':
        story += [Spacer(1, 4), Paragraph(esc_pdf(f'ATS ANULADO: {a.motivo_anulacion}'), th)]
    doc.build(story)
    return buf.getvalue()
