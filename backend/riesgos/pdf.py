"""
Formatos impresos de Riesgos y oportunidades: Matriz de Riesgos y Oportunidades
y Matriz de Oportunidades de Mejora, con la disposición, columnas y colores de
sus plantillas (A3 horizontal).
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _p_ajustado, _solo_fecha, esc_pdf
from quejas.pdf import _cabecera

from .models import NIVELES, RevisionMatriz

COD_MATRIZ = 'PES-PRO-02-r01'
COD_MEJORAS = 'PES-PRO-02-r02'
# Respaldo de la caja de control (valores de las plantillas) mientras el formato
# no esté vinculado a su documento de la lista maestra.
for _cod in (COD_MATRIZ, COD_MEJORAS):
    CONTROL_FORMATOS.setdefault(_cod, ('00', '2026-01-23', 'ASIG', 'GSIG/GT', 'GG'))

AZUL_OSCURO = colors.HexColor('#16365C')
AZUL = colors.HexColor('#2E5E9C')
VERDE = colors.HexColor('#00B050')
VERDE_CLARO = colors.HexColor('#92D050')
AZUL_CLARO = colors.HexColor('#95B3D7')
NARANJA = colors.HexColor('#E46C0A')
NARANJA_CLARO = colors.HexColor('#FAC090')

# Colores de nivel, eficacia, decisión y estado (formato condicional de las plantillas).
COLOR_NIVEL = {'critico': ('#C00000', '#FFFFFF'), 'importante': ('#ED7D31', None), 'moderado': ('#FFC000', None),
               'tolerado': ('#A9D08E', None), 'no_significativo': ('#D9D9D9', None)}
COLOR_EFICACIA = {'eficaz': ('#A9D08E', None), 'no_eficaz': ('#C00000', '#FFFFFF'), 'sin_cambio': ('#FFC000', None),
                  'pendiente': ('#D9D9D9', None), 'no_aplica': ('#FFFFFF', '#808080')}
COLOR_REQUIERE = {'si': ('#C00000', '#FFFFFF'), 'en_cartera': ('#FFC000', None), 'no': ('#D9D9D9', None)}
COLOR_TIPO = {'riesgo': ('#FCE4E4', '#C00000'), 'oportunidad': ('#DDEBF7', '#1F4E79')}
COLOR_DECISION = {'se_implementa': ('#A9D08E', None), 'no_se_implementa': ('#D9D9D9', None),
                  'en_evaluacion': ('#FFC000', None)}
COLOR_EF_MEJORA = {'lograda': ('#A9D08E', None), 'parcial': ('#FFC000', None), 'no_lograda': ('#C00000', '#FFFFFF'),
                   'pendiente': ('#D9D9D9', None)}
COLOR_ESTADO = {'ejecutado': ('#A9D08E', None), 'en_proceso': ('#FFC000', None), 'pendiente': ('#D9D9D9', None),
                'no_aplica': ('#FFFFFF', '#808080')}

EFICACIAS = {'eficaz': 'EFICAZ', 'no_eficaz': 'NO EFICAZ', 'sin_cambio': 'SIN CAMBIO', 'pendiente': 'PENDIENTE',
             'no_aplica': 'NO APLICA'}
REQUIERE = {'si': 'SÍ', 'no': 'NO', 'en_cartera': 'EN CARTERA'}


def _doc(buf, titulo):
    return SimpleDocTemplate(buf, pagesize=landscape(A3), leftMargin=8 * mm, rightMargin=8 * mm, topMargin=8 * mm,
                             bottomMargin=8 * mm, title=titulo)


def _ultima(matriz, tipo):
    return RevisionMatriz.objects.filter(matriz=matriz, tipo=tipo).select_related('usuario').first()


def _bloque_revisiones(W, cw, matriz, c_act, c_sup, fs):
    """Filas «Fecha / responsable de la actualización» y «de la supervisión» de la plantilla.
    c_act, c_sup: (columna de la etiqueta, n.º de columnas de la etiqueta, n.º de columnas del valor)."""
    lb = ParagraphStyle('rvl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER,
                        textColor=colors.white)
    vl = ParagraphStyle('rvv', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    act, sup = _ultima(matriz, 'actualizacion'), _ultima(matriz, 'supervision')
    n = len(cw)
    filas = [[''] * n, [''] * n]
    est = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 2),
           ('RIGHTPADDING', (0, 0), (-1, -1), 2)]
    for (col, n_lab, n_val), rev, nombre in ((c_act, act, 'ACTUALIZACIÓN'), (c_sup, sup, 'SUPERVISIÓN')):
        for fila, etiqueta, valor in ((0, f'FECHA DE LA {nombre}' if nombre == 'SUPERVISIÓN' else 'FECHA DE ACTUALIZACIÓN',
                                       _solo_fecha(rev.fecha) if rev else ''),
                                      (1, f'RESPONSABLE DE LA {nombre}', rev.responsable_nombre if rev else '')):
            w_lab = sum(cw[col:col + n_lab])
            filas[fila][col] = _p_ajustado(etiqueta, lb, w_lab - 4, una_linea=True)
            filas[fila][col + n_lab] = Paragraph(esc_pdf(valor), vl)
            fin_lab, fin_val = col + n_lab - 1, col + n_lab + n_val - 1
            est += [('SPAN', (col, fila), (fin_lab, fila)), ('SPAN', (col + n_lab, fila), (fin_val, fila)),
                    ('BACKGROUND', (col, fila), (fin_lab, fila), AZUL_OSCURO),
                    ('BOX', (col, fila), (fin_lab, fila), 0.6, colors.black),
                    ('BOX', (col + n_lab, fila), (fin_val, fila), 0.6, colors.black)]
    t = Table(filas, colWidths=cw, rowHeights=[16, 16])
    t.setStyle(TableStyle(est))
    return t


def _fila_actualizacion(cw, matriz, fs):
    """Fila única de la plantilla de mejoras: fecha (B:E → F:G) y responsable (J:L → M:O) de la actualización."""
    lb = ParagraphStyle('rfl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER,
                        textColor=colors.white)
    vl = ParagraphStyle('rfv', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    act = _ultima(matriz, 'actualizacion')
    fila = [''] * len(cw)
    fila[1] = Paragraph('FECHA DE ACTUALIZACIÓN', lb)
    fila[5] = Paragraph(esc_pdf(_solo_fecha(act.fecha) if act else ''), vl)
    fila[9] = Paragraph('RESPONSABLE DE LA ACTUALIZACIÓN', lb)
    fila[12] = Paragraph(esc_pdf(act.responsable_nombre if act else ''), vl)
    t = Table([fila], colWidths=cw, rowHeights=[16])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('SPAN', (1, 0), (4, 0)), ('SPAN', (5, 0), (6, 0)),
        ('SPAN', (9, 0), (11, 0)), ('SPAN', (12, 0), (14, 0)), ('BACKGROUND', (1, 0), (4, 0), AZUL_OSCURO),
        ('BACKGROUND', (9, 0), (11, 0), AZUL_OSCURO), ('BOX', (1, 0), (4, 0), 0.6, colors.black),
        ('BOX', (5, 0), (6, 0), 0.6, colors.black), ('BOX', (9, 0), (11, 0), 0.6, colors.black),
        ('BOX', (12, 0), (14, 0), 0.6, colors.black)]))
    return t


def _proporcionales(W, anchos):
    total = sum(anchos)
    return [W * a / total for a in anchos]


def _lista(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return items[0] if items else ''
    return '\n'.join(f'{n}. {t}' for n, t in enumerate(items, start=1))


class _Celdas:
    """Arma celdas (texto, estilo) que luego se ajustan al ancho de su columna."""

    def __init__(self, fs):
        self.td = ParagraphStyle('rtd', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER)
        self.tdl = ParagraphStyle('rtl', parent=self.td, alignment=TA_LEFT)
        self.tdb = ParagraphStyle('rtb', parent=self.td, fontName='Helvetica-Bold')
        self.th = ParagraphStyle('rth', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15,
                                 alignment=TA_CENTER, textColor=colors.white)

    @staticmethod
    def ajustar(fila, cw):
        salida = []
        for k, celda in enumerate(fila):
            if isinstance(celda, tuple):
                texto, estilo = celda
                if '\n' in texto:
                    celda = Paragraph(esc_pdf(texto).replace('\n', '<br/>'), estilo)
                else:
                    celda = _p_ajustado(texto, estilo, cw[k] - 2)
            salida.append(celda)
        return salida


def _color(est, col, fila, pareja):
    if not pareja:
        return
    fondo, letra = pareja
    est.append(('BACKGROUND', (col, fila), (col, fila), colors.HexColor(fondo)))
    if letra:
        est.append(('TEXTCOLOR', (col, fila), (col, fila), colors.HexColor(letra)))


def _texto_color(estilo, letra, bold=False):
    if not letra and not bold:
        return estilo
    return ParagraphStyle(f'{estilo.name}_{letra}_{bold}', parent=estilo,
                          textColor=colors.HexColor(letra) if letra else estilo.textColor,
                          fontName='Helvetica-Bold' if bold else estilo.fontName)


def generar_matriz_pdf(registros) -> bytes:
    """Matriz de Riesgos y Oportunidades: una fila por riesgo u oportunidad."""
    buf = BytesIO()
    doc = _doc(buf, 'Matriz de riesgos y oportunidades')
    W = doc.width
    cfg = _cargar_cfg()
    # Anchos de la plantilla; las casillas de nivel, ¿requiere acción?, estrategia y eficacia algo más anchas
    # (a costa de las columnas de texto largo) para que sus palabras no se partan.
    anchos = [20.0, 30.0, 30.0, 20.0, 20.0, 18.0, 26.0, 17.1, 11.0, 28.0, 40.0, 33.0, 33.0, 33.0, 17.1, 17.1, 15.0,
              23.0, 21.0, 21.0, 38.0, 48.0, 22.0, 17.1, 26.0, 22.0, 14.0, 34.0, 17.1, 17.1, 15.0, 23.0, 23.0]
    cw = _proporcionales(W, anchos)
    fs = 5.6
    c = _Celdas(fs)
    niveles = dict(NIVELES)
    P = lambda t, s=None: (str(t or ''), s or c.td)  # noqa: E731

    grupos = [P('IDENTIFICACIÓN Y ANALISIS DEL RIESGO U OPORTUNIDADES', c.th)] + [''] * 13 + \
             [P('EVALUACION INICIAL DEL RIESGO U OPORTUNIDAD', c.th)] + [''] * 4 + \
             [P('TRATAMIENTO', c.th)] + [''] * 8 + \
             [P('EVALUACIÓN DEL RIESGO RESIDUAL U OPORTUNIDAD IMPLEMENTADA', c.th)] + [''] * 4
    titulos = ['PROCESO', 'CONTEXTO INTERNO (FORTALEZA / DEBILIDAD)', 'CONTEXTO EXTERNO (OPORTUNIDAD / AMENAZA)',
               'PARTES INTERESADAS', 'TIPO', 'CATEGORÍA', 'FUENTE / ORIGEN DE LA IDENTIFICACIÓN',
               'FECHA DE IDENTIFICACIÓN', 'CÓDIGO', 'ACTIVIDAD / ETAPA', 'DESCRIPCIÓN DEL RIESGO U OPORTUNIDAD',
               'CAUSA', 'EFECTO / CONSECUENCIA', 'CONTROLES EXISTENTES', 'PROBABILIDAD / VIABILIDAD',
               'IMPACTO / BENEFICIO', 'NIVEL', 'VALORACIÓN', '¿REQUIERE ACCIÓN?', 'ESTRATEGIA', 'ACCIÓN O ACTIVIDAD',
               'IMPLEMENTACIÓN DOCUMENTAL PROPUESTA', 'RESPONSABLE', 'FECHA MÁX. DE IMPLEMENTACIÓN', 'RECURSOS',
               'ESTADO', 'FECHA DE VERIFICACIÓN', 'EVIDENCIA / OBSERVACIONES', 'PROBABILIDAD / VIABILIDAD',
               'IMPACTO / BENEFICIO', 'NIVEL', 'VALORACIÓN', 'EFICACIA']
    filas = [grupos, [P(t, c.th) for t in titulos]]
    colores = []
    for r in registros:
        fila_n = len(filas)
        ctx = list(r.contexto.all())
        interno = '\n'.join(f'{e.codigo}: {e.descripcion}' for e in ctx if e.tipo in ('fortaleza', 'debilidad'))
        externo = '\n'.join(f'{e.codigo}: {e.descripcion}' for e in ctx if e.tipo in ('oportunidad', 'amenaza'))
        partes = '\n'.join(e.descripcion for e in ctx if e.tipo == 'parte_interesada')
        acciones = r.acciones_activas()
        nivel, nivel_r, req, ef = r.nivel, r.nivel_residual, r.requiere_accion, r.eficacia
        tipo_c = COLOR_TIPO.get(r.tipo)
        filas.append([
            P(r.proceso.nombre.upper() if r.proceso_id else ''), P(interno, c.tdl), P(externo, c.tdl), P(partes),
            P(r.get_tipo_display().upper(), _texto_color(c.td, tipo_c[1])),
            P(r.get_categoria_display().upper()), P(r.get_fuente_display().upper()),
            P(_solo_fecha(r.fecha_identificacion)), P(r.codigo, _texto_color(c.td, tipo_c[1], True)),
            P(r.actividad, c.tdl), P(r.descripcion, c.tdl), P(r.causa, c.tdl), P(r.efecto, c.tdl),
            P(r.controles_existentes, c.tdl), P(r.probabilidad), P(r.impacto), P(r.valor),
            P(niveles.get(nivel, '').upper(), _texto_color(c.tdb, COLOR_NIVEL.get(nivel, (0, None))[1])),
            P(REQUIERE.get(req, ''), _texto_color(c.tdb, COLOR_REQUIERE.get(req, (0, None))[1])),
            P(r.get_estrategia_display().upper()),
            P(_lista([a.actividad for a in acciones]), c.tdl),
            P(_lista([a.implementacion_documental for a in acciones]), c.tdl),
            P(_lista([a.responsable_nombre for a in acciones])),
            P(_lista([_solo_fecha(a.fecha_maxima) for a in acciones])),
            P(_lista([a.recursos for a in acciones]), c.tdl),
            P(_lista([a.get_estado_display().upper() for a in acciones])),
            P(_solo_fecha(r.fecha_verificacion)), P(r.evidencia_verificacion, c.tdl),
            P(r.residual_probabilidad), P(r.residual_impacto), P(r.valor_residual),
            P(niveles.get(nivel_r, '').upper(), _texto_color(c.tdb, COLOR_NIVEL.get(nivel_r, (0, None))[1])),
            P(EFICACIAS.get(ef, ''), _texto_color(c.tdb, COLOR_EFICACIA.get(ef, (0, None))[1])),
        ])
        colores += [(4, fila_n, tipo_c), (8, fila_n, tipo_c), (17, fila_n, COLOR_NIVEL.get(nivel)),
                    (18, fila_n, COLOR_REQUIERE.get(req)), (31, fila_n, COLOR_NIVEL.get(nivel_r)),
                    (32, fila_n, COLOR_EFICACIA.get(ef))]
        if len(acciones) == 1:
            colores.append((25, fila_n, COLOR_ESTADO.get(acciones[0].estado)))
    filas = [c.ajustar(f, cw) for f in filas]
    while len(filas) < 12:
        filas.append([''] * 33)
    t = Table(filas, colWidths=cw, repeatRows=2,
              rowHeights=[16, 34] + [None if any(isinstance(x, Paragraph) for x in f) else 16 for f in filas[2:]])
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('LEFTPADDING', (0, 0), (-1, -1), 1.5), ('RIGHTPADDING', (0, 0), (-1, -1), 1.5),
           ('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
           ('SPAN', (0, 0), (13, 0)), ('SPAN', (14, 0), (18, 0)), ('SPAN', (19, 0), (27, 0)), ('SPAN', (28, 0), (32, 0)),
           ('BACKGROUND', (0, 0), (13, 0), AZUL_OSCURO), ('BACKGROUND', (14, 0), (18, 0), VERDE),
           ('BACKGROUND', (19, 0), (27, 0), AZUL), ('BACKGROUND', (28, 0), (32, 0), NARANJA),
           ('BACKGROUND', (0, 1), (13, 1), AZUL), ('BACKGROUND', (14, 1), (18, 1), VERDE_CLARO),
           ('BACKGROUND', (19, 1), (27, 1), AZUL_CLARO), ('BACKGROUND', (28, 1), (32, 1), NARANJA_CLARO)]
    for col, fila, pareja in colores:
        _color(est, col, fila, pareja)
    t.setStyle(TableStyle(est))
    cab = _cabecera(W, [cw[0] + cw[1], sum(cw[2:28])], 'MATRIZ DE RIESGOS Y OPORTUNIDADES', COD_MATRIZ, cfg, 13.0,
                    7, 18, 1, 2)
    rev = _bloque_revisiones(W, cw, 'ryo', (8, 3, 2), (20, 3, 3), 6.5)
    doc.build([cab, Spacer(1, 4), rev, Spacer(1, 4), t])
    return buf.getvalue()


def generar_mejoras_pdf(mejoras) -> bytes:
    """Matriz de Oportunidades de Mejora: una fila por oportunidad de mejora."""
    buf = BytesIO()
    doc = _doc(buf, 'Matriz de oportunidades de mejora')
    W = doc.width
    cfg = _cargar_cfg()
    anchos = [20.0, 30.0, 22.0, 17.1, 11.0, 54.0, 46.0, 17.0, 42.0, 44.0, 22.0, 17.1, 22.1, 17.1, 38.0, 22.1]
    cw = _proporcionales(W, anchos)
    fs = 6.4
    c = _Celdas(fs)
    P = lambda t, s=None: (str(t or ''), s or c.td)  # noqa: E731
    grupos = [P('IDENTIFICACIÓN Y ANÁLISIS DE LA OPORTUNIDAD DE MEJORA', c.th)] + [''] * 6 + \
             [P('SELECCIÓN', c.th), ''] + [P('IMPLEMENTACIÓN Y SEGUIMIENTO', c.th)] + [''] * 6
    titulos = ['PROCESO', 'FUENTE / ORIGEN DE LA IDENTIFICACIÓN', 'DETECTADO POR', 'FECHA DE IDENTIFICACIÓN',
               'CÓDIGO', 'DESCRIPCIÓN DE LA OPORTUNIDAD DE MEJORA', 'SITUACIÓN QUE LA MOTIVA', 'DECISIÓN',
               'JUSTIFICACIÓN DE LA DECISIÓN', 'ACCIÓN O ACTIVIDAD', 'RESPONSABLE', 'FECHA MÁX. DE IMPLEMENTACIÓN',
               'ESTADO', 'FECHA DE VERIFICACIÓN', 'EVIDENCIA / OBSERVACIONES', 'EFICACIA DE LA MEJORA']
    filas = [grupos, [P(t, c.th) for t in titulos]]
    colores = []
    for m in mejoras:
        n = len(filas)
        implementa = m.decision == 'se_implementa'
        filas.append([
            P(m.proceso.nombre.upper() if m.proceso_id else ''), P(m.get_fuente_display().upper()),
            P(m.detectado_por), P(_solo_fecha(m.fecha_identificacion)),
            P(m.codigo, _texto_color(c.td, '#375623', True)), P(m.descripcion, c.tdl), P(m.situacion, c.tdl),
            P(m.get_decision_display().upper(), c.tdb), P(m.justificacion, c.tdl), P(m.accion, c.tdl),
            P(m.responsable_nombre), P(_solo_fecha(m.fecha_maxima)),
            P(m.get_estado_accion_display().upper() if implementa else '', c.tdb),
            P(_solo_fecha(m.fecha_verificacion)), P(m.evidencia, c.tdl),
            P(m.get_eficacia_display().upper() if implementa else '',
              _texto_color(c.tdb, COLOR_EF_MEJORA.get(m.eficacia, (0, None))[1])),
        ])
        colores += [(4, n, ('#E2EFDA', None)), (7, n, COLOR_DECISION.get(m.decision))]
        if implementa:
            colores += [(12, n, COLOR_ESTADO.get(m.estado_accion)), (15, n, COLOR_EF_MEJORA.get(m.eficacia))]
    filas = [c.ajustar(f, cw) for f in filas]
    while len(filas) < 14:
        filas.append([''] * 16)
    t = Table(filas, colWidths=cw, repeatRows=2,
              rowHeights=[16, 32] + [None if any(isinstance(x, Paragraph) for x in f) else 16 for f in filas[2:]])
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
           ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
           ('SPAN', (0, 0), (6, 0)), ('SPAN', (7, 0), (8, 0)), ('SPAN', (9, 0), (15, 0)),
           ('BACKGROUND', (0, 0), (6, 0), AZUL_OSCURO), ('BACKGROUND', (7, 0), (8, 0), VERDE),
           ('BACKGROUND', (9, 0), (15, 0), NARANJA),
           ('BACKGROUND', (0, 1), (6, 1), AZUL), ('BACKGROUND', (7, 1), (8, 1), VERDE_CLARO),
           ('BACKGROUND', (9, 1), (15, 1), NARANJA_CLARO)]
    for col, fila, pareja in colores:
        _color(est, col, fila, pareja)
    t.setStyle(TableStyle(est))
    cab = _cabecera(W, [cw[0] + cw[1], sum(cw[2:13])], 'MATRIZ DE OPORTUNIDADES DE MEJORA', COD_MEJORAS, cfg, 13.0,
                    7, 18, 1, 2)
    rev = _fila_actualizacion(cw, 'om', 6.5)
    doc.build([cab, Spacer(1, 4), rev, Spacer(1, 4), t])
    return buf.getvalue()
