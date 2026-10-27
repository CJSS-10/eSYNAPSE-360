"""
Formatos impresos de la revisión por la dirección, con la disposición de sus plantillas:
- Programa de revisión por la dirección (horizontal: ítem, agenda, responsable, meses con P/E, observaciones).
- Informe de la revisión por la dirección (vertical, encabezado en cada página y pie de documento confidencial:
  datos generales, asistentes, agenda con entradas y salidas, acuerdos, conclusiones, observaciones y firmas).
- Plan de acción (horizontal: acuerdos con elemento, responsable, plazo, costo, evidencia, estado, seguimientos, V°B°).
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import CondPageBreak, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _pie_confidencial, _solo_fecha, esc_pdf
from quejas.pdf import _cabecera

from .models import ENTRADAS, SALIDAS, TITULO_ELEMENTO

COD_PROGRAMA, COD_INFORME, COD_PLAN = 'PES-PRO-03-r01', 'PES-PRO-03-r02', 'PES-PRO-03-r03'
# Respaldo de la caja de control mientras el formato no esté vinculado a la lista maestra.
for _cod in (COD_PROGRAMA, COD_INFORME, COD_PLAN):
    CONTROL_FORMATOS.setdefault(_cod, ('01', '2026-09-28', 'ASIG', 'GSIG/GCOM', 'GG'))

AZUL = colors.HexColor('#17375E')
LILA = colors.HexColor('#DCE1F2')
GRIS = colors.HexColor('#D9D9D9')
AZUL_TXT = colors.HexColor('#1F3864')
MESES = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SET', 'OCT', 'NOV', 'DIC']
ESTADO_ACUERDO = {'abierto': 'Abierto', 'en_proceso': 'En proceso', 'cerrado': 'Cerrado'}


def _st(fs):
    return {'th': ParagraphStyle('rth', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15,
                                 alignment=TA_CENTER, textColor=colors.white),
            'thn': ParagraphStyle('rthn', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15,
                                  alignment=TA_CENTER),
            'thl': ParagraphStyle('rthl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15),
            'td': ParagraphStyle('rtd', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER),
            'tdl': ParagraphStyle('rtdl', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_LEFT),
            'tdr': ParagraphStyle('rtdr', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_RIGHT)}


def _P(t, st):
    return Paragraph(esc_pdf('' if t is None else str(t)), st)


def _f(d):
    return _solo_fecha(d) if d else ''


def _monto(v):
    if v in (None, ''):
        return ''
    return f'{float(v):,.2f}'


def _firma_txt(f):
    if not f:
        return ''
    metodo = 'PIN' if f.get('metodo') == 'pin' else 'contraseña'
    return f'Firmado el {_solo_fecha(f.get("fecha"))} ({metodo})'


def _elemento_corto(clave):
    """«e-a» → «Entrada a)», «s-c» → «Salida c)»."""
    if not clave or '-' not in clave:
        return ''
    tipo, letra = clave.split('-', 1)
    return f'{"Entrada" if tipo == "e" else "Salida"} {letra})'


def _doc(buf, pag, titulo, margen=8 * mm):
    return SimpleDocTemplate(buf, pagesize=pag, leftMargin=margen, rightMargin=margen, topMargin=margen,
                             bottomMargin=margen, title=titulo)


def _campo(W, etiqueta, valor, s, ancho_et=0.38):
    t = Table([[_P(etiqueta, s['thn']), _P(valor, s['tdl'])]], colWidths=[W * ancho_et, W * (1 - ancho_et)])
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5)]))
    return [t, Spacer(1, 1.6 * mm)]


# ============================================================================================ programa (r01)
def generar_programa_pdf(p) -> bytes:
    cfg = _cargar_cfg()
    buf = BytesIO()
    pag = landscape(A4)
    doc = _doc(buf, pag, f'Programa de revisión por la dirección {p.anio}')
    W = doc.width
    s = _st(6.6)
    mmw = [8, 102, 36] + [9] * 12 + [39]
    esc = W / (sum(mmw) * mm)
    cw = [x * mm * esc for x in mmw]
    story = [_cabecera(W, cw, 'PROGRAMA DE REVISIÓN POR LA DIRECCIÓN', COD_PROGRAMA, cfg, 5.6 * mm, 6.5, 15, 2, 12),
             Spacer(1, 2 * mm)]
    story += _campo(W, 'Año:', p.anio, s)
    story += _campo(W, 'Fecha de Elaboración:', _f(p.fecha_elaboracion), s)

    filas = [[_P('Ítem', s['th']), _P('Agenda', s['th']), _P('Responsable de la información', s['th'])]
             + [_P(m, s['th']) for m in MESES] + [_P('Observaciones', s['th'])]]
    estilos = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), AZUL),
               ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 1.5),
               ('RIGHTPADDING', (0, 0), (-1, -1), 1.5), ('TOPPADDING', (0, 0), (-1, -1), 1.2),
               ('BOTTOMPADDING', (0, 0), (-1, -1), 1.2)]
    items = {i.clave: i for i in p.items.select_related('responsable')}
    n = 0
    for grupo, lista, pref in (('ELEMENTOS DE ENTRADA', ENTRADAS, 'e'), ('SALIDAS', SALIDAS, 's')):
        filas.append([_P(grupo, s['thl'])] + [''] * 15)
        r = len(filas) - 1
        estilos += [('SPAN', (0, r), (-1, r)), ('BACKGROUND', (0, r), (-1, r), LILA)]
        for c, titulo in lista:
            n += 1
            it = items.get(f'{pref}-{c}')
            meses, ejec = (it.meses, it.ejecutados) if it else ([], [])
            celdas = []
            for m in range(1, 13):
                marca = ('P' if m in meses else '') + ('/E' if m in ejec and m in meses else ('E' if m in ejec else ''))
                celdas.append(_P(marca, s['td']))
                if m in ejec:
                    estilos.append(('BACKGROUND', (2 + m, len(filas)), (2 + m, len(filas)), colors.HexColor('#C6EFCE')))
                elif m in meses:
                    estilos.append(('BACKGROUND', (2 + m, len(filas)), (2 + m, len(filas)), colors.HexColor('#DDEBF7')))
            filas.append([_P(n, s['td']), _P(f'{c}) {titulo}', s['tdl']),
                          _P(it.responsable.nombre if it and it.responsable else '', s['td'])] + celdas
                         + [_P(it.observaciones if it else '', s['tdl'])])
    t = Table(filas, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(estilos))
    story.append(t)
    story += [Spacer(1, 2 * mm), _P('P: programado · E: ejecutado.', s['tdl'])]
    if p.observaciones:
        story += [Spacer(1, 1.5 * mm), _P(f'Observaciones: {p.observaciones}', s['tdl'])]
    doc.build(story)
    return buf.getvalue()


# ============================================================================================= informe (r02)
def generar_informe_pdf(r) -> bytes:
    cfg = _cargar_cfg()
    margen_cab = 15 * mm
    Wc = A4[0] - 2 * margen_cab
    cw_cab = [Wc * 0.16, Wc * 0.42] + [Wc * 0.42 / 6] * 6
    cabecera = _cabecera(Wc, cw_cab, 'INFORME DE LA REVISIÓN<br/>POR LA DIRECCIÓN', COD_INFORME, cfg, 5.6 * mm, 6.5,
                         13, 1, 2)
    _, alto_cab = cabecera.wrap(Wc, A4[1])

    def _pagina(canvas, doc_):
        canvas.saveState()
        cabecera.drawOn(canvas, margen_cab, A4[1] - 10 * mm - alto_cab)
        _pie_confidencial(canvas, doc_, cfg)
        canvas.restoreState()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=18 * mm,
                            topMargin=10 * mm + alto_cab + 5 * mm, bottomMargin=24 * mm,
                            title=f'Informe de la revisión por la dirección {r.codigo}')
    W = doc.width
    tit = ParagraphStyle('rit', fontName='Helvetica-Bold', fontSize=14, leading=18, alignment=TA_CENTER, spaceAfter=6)
    cod = ParagraphStyle('ric', fontName='Helvetica-Bold', fontSize=11, leading=14, alignment=TA_CENTER, spaceAfter=10)
    dato = ParagraphStyle('rid', fontName='Helvetica', fontSize=9, leading=12)
    h1 = ParagraphStyle('rih1', fontName='Helvetica-BoldOblique', fontSize=9.5, leading=12, spaceBefore=9, spaceAfter=4)
    h_ent = ParagraphStyle('rihe', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=AZUL_TXT,
                           leftIndent=14, spaceBefore=4, spaceAfter=2)
    h2 = ParagraphStyle('rih2', fontName='Helvetica-Bold', fontSize=8.5, leading=11, leftIndent=14, spaceBefore=6,
                        spaceAfter=2)
    txt = ParagraphStyle('ritx', fontName='Helvetica', fontSize=8.5, leading=11, leftIndent=26, alignment=TA_JUSTIFY)
    nota = ParagraphStyle('rino', fontName='Helvetica-Oblique', fontSize=7.5, leading=9.5, leftIndent=26,
                          textColor=colors.HexColor('#555555'))
    s = _st(7.5)

    def texto(t, estilo=txt):
        return Paragraph(esc_pdf(t) if (t or '').strip() else '—', estilo)

    desde, hasta = r.periodo_desde, r.periodo_hasta
    story = [Paragraph('INFORME DE LA REVISIÓN POR LA DIRECCIÓN', tit), Paragraph(esc_pdf(r.codigo), cod)]
    tipo = r.get_tipo_display()
    if r.tipo == 'extraordinaria' and r.motivo_extraordinaria:
        tipo += f' — {r.get_motivo_extraordinaria_display()}'
    for et, v in (('FECHA:', _f(r.fecha)), ('TIPO DE REVISIÓN:', tipo), ('LUGAR / MODALIDAD:', r.lugar),
                  ('RESPONSABLE DE LA RECOPILACIÓN DE LA INFORMACIÓN:',
                   r.responsable_recopilacion.nombre_completo if r.responsable_recopilacion else ''),
                  ('RESPONSABLE DE LA VERIFICACIÓN DE LA INFORMACIÓN:',
                   r.responsable_verificacion.nombre_completo if r.responsable_verificacion else '')):
        story.append(Paragraph(f'<b>{et}</b> {esc_pdf(v)}', dato))
    story.append(Paragraph(f'<b><i><u>PERIODO EVALUADO: del {_f(desde)} al {_f(hasta)}</u></i></b>', dato))
    if r.tipo == 'extraordinaria' and r.detalle_motivo:
        story.append(Paragraph(f'<b>DETALLE DEL MOTIVO:</b> {esc_pdf(r.detalle_motivo)}', dato))

    # 1. Asistentes
    story.append(Paragraph('1.&nbsp;&nbsp;&nbsp;<u>ASISTENTES</u>', h1))
    asis = list(r.asistentes.filter(is_active=True).select_related('trabajador'))
    filas = [[_P('N°', s['thn']), _P('Nombre', s['thn']), _P('Cargo', s['thn']), _P('Firma', s['thn'])]]
    for i, a in enumerate(asis, 1):
        filas.append([_P(i, s['td']), _P(a.trabajador.nombre_completo, s['tdl']), _P(a.cargo, s['tdl']),
                      _P(_firma_txt(a.firma), s['td'])])
    for i in range(len(asis) + 1, max(len(asis), 4) + 1):
        filas.append([_P(i, s['td']), '', '', ''])
    t = Table(filas, colWidths=[W * 0.07, W * 0.36, W * 0.33, W * 0.24], repeatRows=1)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), GRIS),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 3),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    story.append(t)

    # 2. Agenda
    story.append(Paragraph('2.&nbsp;&nbsp;&nbsp;AGENDA', h1))
    story.append(Paragraph('&#10146;&nbsp;ENTRADAS', h_ent))
    entradas = {e.clave: e for e in r.entradas.all()}
    for c, titulo in ENTRADAS:
        e = entradas.get(c)
        bloque = [Paragraph(f'{c}.&nbsp;&nbsp;{esc_pdf(titulo.upper())}', h2)]
        if e and e.sin_actividad and not (e.analisis or '').strip():
            bloque.append(texto('Sin actividad en el periodo evaluado.'))
        else:
            for b in (e.datos if e else []) or []:
                filas_b = b.get('filas') or []
                if filas_b:
                    datos_t = Table([[_P(b.get('titulo', ''), s['thl']), '']]
                                    + [[_P(x, s['tdl']), _P(y, s['tdr'])] for x, y in filas_b],
                                    colWidths=[(W - 26) * 0.72, (W - 26) * 0.28])
                    datos_t.hAlign = 'RIGHT'
                    datos_t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#999999')),
                                                 ('SPAN', (0, 0), (1, 0)), ('BACKGROUND', (0, 0), (1, 0), LILA),
                                                 ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                                 ('TOPPADDING', (0, 0), (-1, -1), 1.2),
                                                 ('BOTTOMPADDING', (0, 0), (-1, -1), 1.2)]))
                    bloque += [datos_t]
                    if b.get('nota'):
                        bloque.append(Paragraph(esc_pdf(b['nota']), nota))
                    bloque.append(Spacer(1, 1.5 * mm))
                elif b.get('nota') and b.get('titulo') != 'Sin fuente en el sistema':
                    bloque.append(Paragraph(f'{esc_pdf(b.get("titulo", ""))}: {esc_pdf(b["nota"])}', nota))
            bloque.append(texto(e.analisis if e else ''))
        story.append(KeepTogether(bloque[:3]))
        story += bloque[3:]
    story.append(Paragraph('&#10146;&nbsp;SALIDAS', h_ent))
    salidas = {x.clave: x for x in r.salidas.all()}
    for c, titulo in SALIDAS:
        story.append(KeepTogether([Paragraph(f'{c}.&nbsp;&nbsp;{esc_pdf(titulo.upper())}', h2),
                                   texto(salidas[c].texto if c in salidas else '')]))
        if c == 'i' and (r.comunicacion_fecha or r.comunicacion_detalle or r.reunion_comite_id):
            partes = []
            if r.comunicacion_fecha:
                partes.append(f'Fecha: {_f(r.comunicacion_fecha)}')
            if r.reunion_comite_id:
                partes.append(f'Reunión del Comité de SST: {r.reunion_comite}')
            if r.comunicacion_detalle:
                partes.append(r.comunicacion_detalle)
            story.append(texto(' · '.join(partes)))

    # 3. Acuerdos
    story.append(CondPageBreak(45 * mm))
    story.append(Paragraph('3.&nbsp;&nbsp;&nbsp;<u>ACUERDOS</u>', h1))
    story.append(Paragraph('<b><i><u>Cada acuerdo se registra y se sigue en el Plan de Acción; su estado se presenta '
                           'en la siguiente revisión.</u></i></b>', dato))
    story.append(Spacer(1, 2 * mm))
    acuerdos = list(r.acuerdos.filter(is_active=True).select_related('responsable'))
    filas = [[_P(x, s['thn']) for x in ('N°', 'Acuerdo', 'Elemento que lo origina', 'Responsable', 'Plazo',
                                         'Costo estimado (S/)')]]
    for a in acuerdos:
        filas.append([_P(a.numero, s['td']), _P(a.descripcion, s['tdl']),
                      _P(_elemento_corto(a.elemento), s['td']),
                      _P(a.responsable.nombre_completo if a.responsable else '', s['td']),
                      _P(_f(a.fecha_compromiso), s['tdr']), _P(_monto(a.costo_estimado), s['tdr'])])
    for i in range(len(acuerdos) + 1, max(len(acuerdos), 3) + 1):
        filas.append([_P(i, s['td']), '', '', '', '', ''])
    t = Table(filas, colWidths=[W * 0.06, W * 0.36, W * 0.16, W * 0.17, W * 0.12, W * 0.13], repeatRows=1)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), GRIS),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 3),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    story.append(t)

    # 4 y 5
    story.append(Paragraph('4.&nbsp;&nbsp;&nbsp;CONCLUSIONES', h1))
    story.append(texto(r.conclusiones))
    story.append(Paragraph('5.&nbsp;&nbsp;&nbsp;OBSERVACIONES', h1))
    story.append(texto(r.observaciones))

    # Firmas: Gerente General al centro, Técnico y Comercial a los lados, Gerente SIG al centro.
    firmados = {a.sigla: a for a in asis if a.firma}
    fn = ParagraphStyle('rifn', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_CENTER)
    fc = ParagraphStyle('rifc', fontName='Helvetica', fontSize=9.5, leading=12, alignment=TA_CENTER)
    fx = ParagraphStyle('rifx', fontName='Helvetica-Oblique', fontSize=6.8, leading=8.5, alignment=TA_CENTER,
                        textColor=colors.HexColor('#555555'))

    def firma(sigla, cargo):
        a = firmados.get(sigla)
        return [Paragraph(esc_pdf(a.trabajador.nombre_completo) if a else '&nbsp;', fn),
                Paragraph(esc_pdf(_firma_txt(a.firma)) if a else '&nbsp;', fx),
                Paragraph('_' * 26, fc), Paragraph(cargo, fc)]
    col = W / 2
    bloque = Table([[firma('GG', 'Gerente General'), ''], ['', ''],
                    [firma('GT', 'Gerente Técnico'), firma('GCOM', 'Gerente Comercial')], ['', ''],
                    [firma('GSIG', 'Gerente SIG'), '']],
                   colWidths=[col, col], rowHeights=[None, 16 * mm, None, 16 * mm, None])
    bloque.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)), ('SPAN', (0, 4), (1, 4)), ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    pie = []
    if r.firma_cierre:
        pie = [Spacer(1, 6 * mm), Paragraph(esc_pdf(f'Informe cerrado por {r.firma_cierre.get("nombre", "")} el '
                                                    f'{_solo_fecha(r.firma_cierre.get("fecha"))}.'), fx)]
    story += [CondPageBreak(95 * mm), Spacer(1, 18 * mm), KeepTogether([bloque] + pie)]
    doc.build(story, onFirstPage=_pagina, onLaterPages=_pagina)
    return buf.getvalue()


# =========================================================================================== plan de acción (r03)
def generar_plan_pdf(r) -> bytes:
    cfg = _cargar_cfg()
    buf = BytesIO()
    pag = landscape(A4)
    doc = _doc(buf, pag, f'Plan de acción {r.codigo}')
    W = doc.width
    s = _st(6.4)
    mmw = [11, 74, 48, 30, 26, 24, 42, 20, 35, 35, 28]
    esc = W / (sum(mmw) * mm)
    cw = [x * mm * esc for x in mmw]
    story = [_cabecera(W, cw, 'PLAN DE ACCIÓN', COD_PLAN, cfg, 5.4 * mm, 6, 15, 2, 8), Spacer(1, 2 * mm)]
    acuerdos = list(r.acuerdos.filter(is_active=True).select_related('responsable'))
    actualizado = max([a.updated_at for a in acuerdos] + [r.updated_at])
    ultimo = max(acuerdos + [r], key=lambda x: x.updated_at)
    por = ultimo.updated_by.get_full_name() or ultimo.updated_by.username if ultimo.updated_by_id else ''
    for et, v in (('Informe de Revisión por la Dirección (N°):', r.codigo), ('Fecha de la Revisión:', _f(r.fecha)),
                  ('Fecha de Actualización:', _f(actualizado)), ('Actualizado por:', por)):
        story += _campo(W, et, v, s, 0.38)
    filas = [[_P(x, s['th']) for x in ('Ítem', 'Acuerdo / acción', 'Elemento de la revisión que lo origina',
                                        'Responsable', 'Fecha de cumplimiento', 'Costo estimado (S/)',
                                        'Evidencia de ejecución', 'Estado', 'Seguimiento 1° semestre',
                                        'Seguimiento 2° semestre', 'V° B° de cumplimiento')]]
    for a in acuerdos:
        vb = ''
        if a.firma_cierre:
            vb = f'{a.firma_cierre.get("nombre", "")}\n{_f(a.fecha_cierre)}'
        evid = a.evidencia + ('\n(archivo adjunto)' if a.archivo_evidencia else '')
        filas.append([_P(a.numero, s['td']), _P(a.descripcion, s['tdl']), _P(TITULO_ELEMENTO.get(a.elemento, ''), s['tdl']),
                      _P(a.responsable.nombre_completo if a.responsable else '', s['td']),
                      _P(_f(a.fecha_compromiso), s['tdr']), _P(_monto(a.costo_estimado), s['tdr']),
                      _P(evid, s['tdl']), _P(ESTADO_ACUERDO.get(a.estado, a.estado), s['td']),
                      _P(a.seguimiento_1, s['tdl']), _P(a.seguimiento_2, s['tdl']), _P(vb, s['td'])])
    for i in range(len(acuerdos) + 1, max(len(acuerdos), 5) + 1):
        filas.append([_P(i, s['td'])] + [''] * 10)
    t = Table(filas, colWidths=cw, repeatRows=1, rowHeights=[None] + [None] * (len(filas) - 1))
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), AZUL),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 2),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 2), ('TOPPADDING', (0, 1), (-1, -1), 4),
                           ('BOTTOMPADDING', (0, 1), (-1, -1), 4)]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()
