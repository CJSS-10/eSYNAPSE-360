"""
Registro de trabajos y salidas no conformes, con la disposición de su plantilla (dos páginas):
página 1 — registro, descripción, responsable y acciones, corrección, análisis de impacto retroactivo y notificación;
página 2 — autorización para la reanudación, evaluación de la importancia, solicitud de acción correctiva y cierre.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _solo_fecha, esc_pdf
from quejas.pdf import _cabecera

from .models import ACCIONES

COD_REGISTRO = 'SIG-PRO-05-r01'
# Respaldo de la caja de control mientras el formato no esté vinculado a la lista maestra.
CONTROL_FORMATOS.setdefault(COD_REGISTRO, ('01', '2026-10-10', 'ASIG', 'GSIG/GT', 'GG'))

AZUL = colors.HexColor('#16365C')
GRIS = colors.HexColor('#BFBFBF')
BLANCO = colors.white


def _st():
    b = dict(fontName='Helvetica-Bold', fontSize=7.5, leading=9)
    return {
        'banda': ParagraphStyle('tb', alignment=TA_CENTER, textColor=BLANCO, **b),
        'lbl': ParagraphStyle('tl', alignment=TA_CENTER, **b),
        'lblb': ParagraphStyle('tlb', alignment=TA_CENTER, textColor=BLANCO, **b),
        'lblr': ParagraphStyle('tlr', alignment=TA_RIGHT, textColor=BLANCO, **b),
        'val': ParagraphStyle('tv', fontName='Helvetica', fontSize=7.5, leading=9, alignment=TA_CENTER),
        'vall': ParagraphStyle('tvl', fontName='Helvetica', fontSize=7.5, leading=9.5, alignment=TA_LEFT),
        'chico': ParagraphStyle('tc', fontName='Helvetica', fontSize=6, leading=7.5, alignment=TA_LEFT),
        'chicob': ParagraphStyle('tcb', fontName='Helvetica', fontSize=6, leading=7.5, textColor=BLANCO),
        'cod': ParagraphStyle('tcod', fontName='Helvetica-Bold', fontSize=11, leading=13, alignment=TA_CENTER),
    }


def _P(t, st):
    return Paragraph(esc_pdf('' if t is None else str(t)), st)


def _f(d):
    return _solo_fecha(d) if d else ''


def _sn(v):
    return '' if v is None else ('SI' if v else 'NO')


def _firma(f):
    return f.get('nombre', '') if f else ''


def _tabla(filas, anchos, estilos, alto=None):
    t = Table(filas, colWidths=anchos, rowHeights=alto)
    base = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 2.5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2.5), ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5)]
    t.setStyle(TableStyle(base + estilos))
    return t


def _banda(W, texto, s):
    return _tabla([[_P(texto, s['banda'])]], [W], [('BACKGROUND', (0, 0), (-1, -1), AZUL),
                                                   ('BOX', (0, 0), (-1, -1), 0.6, colors.black)])


def _cuadro(W, titulo, texto, s, alto):
    contenido = [Paragraph(f'<b><i>{esc_pdf(titulo)}</i></b>', s['chico'])] if titulo else []
    contenido.append(_P(texto, s['vall']))
    return _tabla([[contenido]], [W], [('BOX', (0, 0), (-1, -1), 0.6, colors.black), ('VALIGN', (0, 0), (-1, -1), 'TOP')],
                  alto=[alto])


def generar_registro_pdf(t) -> bytes:
    cfg = _cargar_cfg()
    s = _st()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm,
                            bottomMargin=10 * mm, title=f'Registro de trabajos y salidas no conformes {t.codigo}')
    W = doc.width
    cw = [W * 0.15, W * 0.62] + [W * 0.23 / 6] * 6

    def cabecera():
        return _cabecera(W, cw, 'REGISTRO DE TRABAJOS Y SALIDAS NO CONFORMES', COD_REGISTRO, cfg, 5.6 * mm, 6.5,
                         13, 1, 2)
    story = [cabecera(), Spacer(1, 3 * mm)]

    # N° de registro, tipo y nivel de riesgo
    fila = [[_P('N° de Registro', s['lbl']), _P(t.codigo, s['cod']), '', _P('Tipo:', s['lbl']),
             _P(t.tipo.upper(), s['val']), _P('Nivel de riesgo***:', s['lbl']),
             _P(t.get_nivel_riesgo_display().upper() if t.nivel_riesgo else '', s['val'])]]
    story += [_tabla(fila, [W * 0.13, W * 0.17, W * 0.05, W * 0.08, W * 0.12, W * 0.15, W * 0.13],
                     [('BACKGROUND', (0, 0), (0, 0), GRIS), ('BACKGROUND', (3, 0), (3, 0), GRIS),
                      ('BACKGROUND', (5, 0), (5, 0), GRIS), ('BOX', (0, 0), (1, 0), 0.6, colors.black),
                      ('INNERGRID', (0, 0), (1, 0), 0.6, colors.black), ('BOX', (3, 0), (6, 0), 0.6, colors.black),
                      ('INNERGRID', (3, 0), (6, 0), 0.6, colors.black)]), Spacer(1, 3 * mm)]

    # Descripción
    origen = ' / '.join(x for x in (t.queja.codigo if t.queja_id else '', t.hallazgo.codigo if t.hallazgo_id else '')
                        if x)
    equipos = ', '.join(e.codigo for e in t.equipos.all())
    refs = '; '.join(x for x in (t.referencias, equipos) if x)
    filas = [
        [_P('Reportado por:', s['lbl']), _P(t.reportado_por.nombre_completo, s['vall']),
         _P('Fecha de reporte a GSIG y GT**:', s['lbl']), _P(_f(t.fecha_reporte), s['val'])],
        [_P('Fecha de detección:', s['lbl']), _P(_f(t.fecha_deteccion), s['vall']),
         _P('Fuente de detección:', s['lbl']), _P(t.get_fuente_display(), s['val'])],
        [_P('OT / certificado / equipo:', s['lbl']), _P(refs, s['vall']), _P('Origen (queja RQ / NC):', s['lbl']),
         _P(origen, s['val'])],
    ]
    story += [_banda(W, 'DESCRIPCIÓN DEL TNC O SNC', s),
              _tabla(filas, [W * 0.18, W * 0.44, W * 0.2, W * 0.18], [('GRID', (0, 0), (-1, -1), 0.6, colors.black)]),
              _cuadro(W, f'{t.get_categoria_display()} · {t.area.nombre} · {t.get_naturaleza_display()}',
                      t.descripcion, s, 26 * mm), Spacer(1, 2 * mm)]

    # Responsable, acciones y corrección
    izq = W * 0.30
    der = W - izq
    acc = t.acciones or {}
    filas_acc = [[_P(_sn((acc.get(c) or {}).get('aplica')), s['val']), _P(n.upper(), s['chicob']),
                  _P(_sn((acc.get(c) or {}).get('ejecutada')), s['val'])] for c, n in ACCIONES]
    acciones = _tabla(filas_acc, [izq * 0.2, izq * 0.6, izq * 0.2],
                      [('BACKGROUND', (1, 0), (1, -1), AZUL), ('BACKGROUND', (0, 0), (0, -1), BLANCO),
                       ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F2F2F2')),
                       ('GRID', (0, 0), (0, -1), 0.5, colors.black), ('GRID', (2, 0), (2, -1), 0.5, colors.black)])
    corr_cab = _tabla([[_P('Realizado por:', s['lbl']),
                        _P(t.correccion_por.nombre_completo if t.correccion_por_id else '', s['vall']),
                        _P('Fecha:', s['lbl']), _P(_f(t.correccion_fecha), s['val'])]],
                      [(der - 6) * 0.18, (der - 6) * 0.47, (der - 6) * 0.12, (der - 6) * 0.23], [('GRID', (1, 0), (1, 0), 0.5, colors.black),
                                                                         ('GRID', (3, 0), (3, 0), 0.5, colors.black)])
    bloque = [
        [_P('RESPONSABLE DEL TRATAMIENTO (GT / GSIG)', s['lblb']), _P('CORRECCIÓN DEL TNC O SNC', s['banda'])],
        [_P(t.responsable_tratamiento.nombre_completo if t.responsable_tratamiento_id else '', s['val']), corr_cab],
        [_P('ACCIÓN: ¿APLICA? / ¿EJECUTADA?', s['lblb']), _P(t.correccion, s['vall'])],
        [acciones, ''],
        ['', [Paragraph('<b>Nota del cliente (si aplica):</b> ' + esc_pdf(t.nota_cliente or ''), s['chico'])]],
    ]
    story += [_tabla(bloque, [izq, der], [
        ('BACKGROUND', (0, 0), (0, 0), AZUL), ('BACKGROUND', (1, 0), (1, 0), AZUL),
        ('BACKGROUND', (0, 2), (0, 4), AZUL), ('BOX', (0, 1), (0, 1), 0.6, colors.black),
        ('SPAN', (1, 2), (1, 3)), ('VALIGN', (1, 2), (1, 2), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.black), ('LINEBEFORE', (1, 0), (1, -1), 0.6, colors.black),
        ('LINEABOVE', (1, 2), (1, 2), 0.6, colors.black), ('LINEABOVE', (1, 4), (1, 4), 0.6, colors.black)],
        alto=[None, None, None, None, 9 * mm]), Spacer(1, 2 * mm)]

    # Análisis de impacto retroactivo
    periodo = f'del {_f(t.periodo_desde)} al {_f(t.periodo_hasta)}' if t.periodo_desde else ''
    story += [_banda(W, 'ANÁLISIS DE IMPACTO RETROACTIVO Y NOTIFICACIÓN AL CLIENTE (Registra el Gerente Técnico)', s),
              _tabla([[_P('Período revisado:', s['lbl']), _P(periodo, s['vall']),
                       _P('Última condición conforme:', s['lbl']), _P(t.ultima_condicion, s['val'])]],
                     [W * 0.18, W * 0.44, W * 0.2, W * 0.18], [('GRID', (0, 0), (-1, -1), 0.6, colors.black)])]
    filas = [[_P(x, s['banda']) for x in ('N° OT', 'N° CERTIFICADO', '¿ENTREGADO?', '¿AFECTADO?',
                                          'ACCIÓN (retener / anular y reemitir / ninguna)')]]
    afect = list(t.afectaciones.filter(is_active=True))
    for a in afect:
        filas.append([_P(a.ot, s['val']), _P(a.certificado, s['val']), _P(_sn(a.entregado), s['val']),
                      _P(_sn(a.afectado), s['val']), _P(a.get_accion_display(), s['val'])])
    for _ in range(len(afect), 4):
        filas.append([''] * 5)
    story += [_tabla(filas, [W * 0.17, W * 0.17, W * 0.11, W * 0.11, W * 0.44],
                     [('BACKGROUND', (0, 0), (-1, 0), AZUL), ('GRID', (0, 0), (-1, -1), 0.5, colors.black)]),
              _tabla([[_P('Notificación al cliente:', s['lbl']), _P(t.notificacion_cliente, s['vall']),
                       _P('Fecha y medio:', s['lbl']), _P(t.notificacion_fecha_medio, s['val'])],
                      [_P('Certificado anulado N°:', s['lbl']), _P(t.certificado_anulado, s['vall']),
                       _P('Certificado de reemplazo N°:', s['lbl']), _P(t.certificado_reemplazo, s['val'])]],
                     [W * 0.18, W * 0.44, W * 0.2, W * 0.18], [('GRID', (0, 0), (-1, -1), 0.6, colors.black)]),
              _cuadro(W, 'Conclusión del análisis de impacto retroactivo:', t.conclusion_retroactivo, s, 16 * mm),
              PageBreak(), cabecera(), Spacer(1, 3 * mm)]

    # Página 2 — Autorización
    fa = t.firma_autorizacion or {}
    aut = [
        [_P('¿Acepta el TNC o SNC corregido como CONFORME y autoriza la reanudación del trabajo?', s['lblb']),
         _P(_sn(t.acepta) if fa else '', s['val']), _P('RESPONSABLE:', s['lblr']), _P(_firma(fa), s['val'])],
        ['', '', _P('FECHA:', s['lblr']), _P(_f(fa.get('fecha')), s['val'])],
        [_P('Sustente su autorización para la reanudación del trabajo:', s['lblb']), '', _P('ASIGNADO A:', s['lblr']),
         _P(t.asignado_a.nombre_completo if t.asignado_a_id else '', s['val'])],
    ]
    story += [_banda(W, 'AUTORIZACIÓN PARA REANUDACIÓN DEL TRABAJO', s),
              _tabla(aut, [W * 0.5, W * 0.1, W * 0.15, W * 0.25],
                     [('BACKGROUND', (0, 0), (-1, -1), AZUL), ('BACKGROUND', (1, 0), (1, 0), BLANCO),
                      ('BACKGROUND', (3, 0), (3, -1), BLANCO), ('GRID', (1, 0), (1, 0), 0.5, colors.black),
                      ('GRID', (3, 0), (3, -1), 0.5, colors.black), ('SPAN', (0, 0), (0, 1)),
                      ('BOX', (0, 0), (-1, -1), 0.8, colors.black)]),
              _cuadro(W, '', t.sustento_autorizacion, s, 22 * mm),
              _tabla([[_P('Nota: si la respuesta es NO, se debe considerar volver a ejecutar el trabajo si aún es '
                          'posible. De no ser posible hacerlo se debe notificar al cliente y anular el trabajo en '
                          'cuestión.', s['chico'])]], [W], [('BOX', (0, 0), (-1, -1), 0.6, colors.black)]),
              Spacer(1, 2 * mm)]

    # Evaluación de la importancia
    fe = t.firma_evaluacion or {}
    ev = [
        [_P('Realizado por:', s['lblb']), _P(_firma(fe), s['val']), _P('Fecha:', s['lblr']), _P(_f(fe.get('fecha')),
                                                                                              s['val']), ''],
        [_P('¿Afecta la validez de los resultados?', s['lblr']), _P(_sn(t.afecta_validez) if fe else '', s['val']),
         _P('Nivel de riesgo confirmado***:', s['lblr']),
         _P(t.get_nivel_confirmado_display().upper() if t.nivel_confirmado and fe else '', s['val']), ''],
        [_P('¿Incumple requisitos y alcances del SIG?', s['lblr']), _P(_sn(t.incumple_sig) if fe else '', s['val']),
         _P('N° de eventos similares (12 meses):', s['lblr']),
         _P(t.eventos_similares if fe and t.eventos_similares is not None else '', s['val']), ''],
        [_P('¿Compromete la competencia técnica del laboratorio?', s['lblr']),
         _P(_sn(t.compromete_competencia) if fe else '', s['val']), _P('Registros similares (N° TSNC):', s['lblr']),
         _P(', '.join(x for x in (t.registros_similares or []) if x != t.codigo) if fe else '', s['val']), ''],
    ]
    story += [_banda(W, 'EVALUACIÓN DE LA IMPORTANCIA DEL TNC O SNC (Registra el Área SIG)', s),
              _tabla(ev, [W * 0.42, W * 0.12, W * 0.24, W * 0.22, 0],
                     [('BACKGROUND', (0, 0), (-1, -1), AZUL), ('BACKGROUND', (1, 0), (1, -1), BLANCO),
                      ('BACKGROUND', (3, 0), (3, -1), BLANCO), ('GRID', (1, 0), (1, -1), 0.5, colors.black),
                      ('GRID', (3, 0), (3, -1), 0.5, colors.black), ('BOX', (0, 0), (3, -1), 0.8, colors.black)]),
              _cuadro(W, '', t.evaluacion if fe else '', s, 24 * mm),
              _tabla([[_P('Cuando la evaluación indique que el TNC o SNC podría volver a ocurrir o exista duda sobre el '
                          'cumplimiento del Sistema Integrado de Gestión, seguir el procedimiento SIG-PRO-11 Gestión '
                          'de No Conformidades y Acciones Correctivas.', s['chico'])]], [W],
                     [('BOX', (0, 0), (-1, -1), 0.6, colors.black)]), Spacer(1, 2 * mm)]

    # Solicitud de acción correctiva y cierre
    fc = t.firma_cierre or {}
    story += [_tabla([[_P('¿Amerita la solicitud de una Acción Correctiva?*', s['lblb']),
                       _P(_sn(t.amerita_sac) if fe else '', s['val']), _P('Identificación N° SAC', s['lblr']),
                       _P(t.sac.codigo if t.sac_id else '', s['val'])]],
                     [W * 0.42, W * 0.12, W * 0.24, W * 0.22],
                     [('BACKGROUND', (0, 0), (-1, -1), AZUL), ('BACKGROUND', (1, 0), (1, 0), BLANCO),
                      ('BACKGROUND', (3, 0), (3, 0), BLANCO), ('GRID', (1, 0), (1, 0), 0.5, colors.black),
                      ('GRID', (3, 0), (3, 0), 0.5, colors.black), ('BOX', (0, 0), (-1, -1), 0.8, colors.black)]),
              Spacer(1, 1.5 * mm), _banda(W, 'CIERRE DEL REGISTRO (Registra el Área SIG)', s),
              _tabla([[_P('Cerrado por:', s['lblb']), _P(_firma(fc), s['val']), _P('Fecha:', s['lblr']),
                       _P(_f(fc.get('fecha')), s['val'])],
                      [_P('Evidencias archivadas:', s['lblb']), _P(t.evidencias if fc else '', s['vall']), '', '']],
                     [W * 0.25, W * 0.43, W * 0.1, W * 0.22],
                     [('BACKGROUND', (0, 0), (-1, -1), AZUL), ('BACKGROUND', (1, 0), (1, 0), BLANCO),
                      ('BACKGROUND', (3, 0), (3, 0), BLANCO), ('BACKGROUND', (1, 1), (3, 1), BLANCO),
                      ('SPAN', (1, 1), (3, 1)), ('GRID', (1, 0), (1, 0), 0.5, colors.black),
                      ('GRID', (3, 0), (3, 0), 0.5, colors.black), ('GRID', (1, 1), (3, 1), 0.5, colors.black),
                      ('BOX', (0, 0), (-1, -1), 0.8, colors.black)]),
              Spacer(1, 2 * mm),
              _P('* Si la respuesta es SI, utilizar el formato SIG-PRO-11-r01 Solicitud de Acción Correctiva',
                 s['chico']),
              _P('** GSIG: Gerente SIG, GT: Gerente Técnico', s['chico']),
              Paragraph('<b><i><u>*** El nivel de riesgo lo asigna el GT (o el GSIG cuando el TNC o SNC es '
                        'administrativo) al registrar, y el Área SIG lo confirma en la evaluación de la importancia; '
                        'se determina según la Tabla N° 2 del procedimiento SIG-PRO-05. Ante duda entre dos niveles, '
                        'se asigna el mayor.</u></i></b>', s['chico'])]
    if not t.is_active:
        story += [Spacer(1, 3 * mm), _P(f'REGISTRO ANULADO: {t.motivo_anulacion}', s['vall'])]
    doc.build(story)
    return buf.getvalue()
