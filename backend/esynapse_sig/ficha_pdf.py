"""
Generación del PDF de la Ficha Técnica del equipo (Hoja de Vida — página 1),
replicando el formato del laboratorio: cabecera de control con logo y caja de
código/versión/firmas, DATOS GENERALES y ESPECIFICACIONES TÉCNICAS con franjas
grises, y la foto del equipo.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable, Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# --- Datos del formato controlado (editables / configurables al comercializar) ---
CODIGO_FORMATO = 'MET-PRO-04-r01'
VERSION_FORMATO = '00'
FECHA_FORMATO = '2026-02-11'   # fecha de aprobación del FORMATO (no del equipo)
FIRMAS = [('Elaborado', 'ASIG'), ('Revisado', 'GSIG/GT'), ('Aprobado', 'GG')]

# Colores tomados del documento original
BANDA = colors.HexColor('#1E3A5C')   # franjas de sección (azul marino)
LABEL = colors.HexColor('#1E3A5C')   # fondo de etiquetas (azul marino)
LINEA = colors.HexColor('#808080')   # líneas de la grilla

CLASIFICACIONES = [
    ('patron_referencia', 'Patrón de Referencia'),
    ('patron_verificacion', 'Patrón de Verificación'),
    ('patron_trabajo', 'Patrón de Trabajo'),
    ('equipamiento', 'Equipamiento Auxiliar'),
]


def _f(d):
    if not d:
        return ''
    return d.isoformat() if hasattr(d, 'isoformat') else str(d)


def _anio(d):
    return str(d.year) if d else ''


def _hora_ampm(h):
    """'14:30' (como lo guarda el selector de hora) → '02:30 p. m.' (misma forma que la pantalla). Cualquier
    otro texto se imprime tal cual."""
    h = str(h or '').strip()
    try:
        hh, mm = h.split(':')[:2]
        hh = int(hh); mm = int(mm)
        if not (0 <= hh < 24 and 0 <= mm < 60):
            return h
    except (ValueError, AttributeError):
        return h
    sufijo = 'a. m.' if hh < 12 else 'p. m.'
    h12 = hh % 12 or 12
    return f'{h12:02d}:{mm:02d} {sufijo}'


def _mk(v):
    return 'X' if v else ''


def _banda(texto, ancho, estilo):
    t = Table([[Paragraph(texto, estilo)]], colWidths=[ancho])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BANDA),
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t


TERMINOS_COL_BIT = {
    'mantenimiento': 'Mantenimiento', 'calibracion': 'Calibración',
    'verificacion': 'Verificación', 'comprobacion_intermedia': 'Comprobación Int.',
    'caracterizacion': 'Caracterización',
}
TITULOS_BIT = {
    'mantenimiento': 'MANTENIMIENTOS', 'calibracion': 'CALIBRACIONES',
    'verificacion': 'VERIFICACIONES', 'comprobacion_intermedia': 'COMPROBACIONES INTERMEDIAS',
    'caracterizacion': 'CARACTERIZACIONES', 'suceso': 'HISTORIAL DE SUCESOS',
}


# Hojas de bitácora de la Hoja de Vida (una pestaña del Excel por tipo):
# título de la franja, encabezados de columna y anchos reales de cada pestaña.
_ANCHOS_BIT = [4.71] * 5 + [3.86] * 26                       # columnas A..AE
_ANCHOS_BIT_MANT = [3.86, 4.43, 6.0, 6.0, 5.71, 3.86, 3.14, 3.14, 3.14] + [3.86] * 22
_ANCHOS_BIT_HIST = [4.71] * 5 + [3.86] * 4 + [5.14] * 3 + [3.86] * 17 + [2.43]   # A..AD (+AE)
HOJAS_BITACORA = {
    'mantenimiento': ('MANTENIMIENTO PREVENTIVO', ['Frecuencia de Mantenimiento', 'N° de Informe de Mantenimiento',
                      'F. de Mantenimiento', 'F. de Próx. Mantenimiento'], 39.75),
    'calibracion': ('CALIBRACIONES', ['Frecuencia de Calibración', 'N° de Certificado de Calibración',
                    'F. de Calibración', 'F. de Próx. Calibración'], 36.75),
    'verificacion': ('VERIFICACIONES', ['Frecuencia de Verificación', 'N° de Informe de Verificación',
                     'F. de Verificación', 'F. de Próx. Verificación'], 35.25),
    'comprobacion_intermedia': ('COMPROBACIONES INTERMEDIAS', ['Frecuencia de Comprobación Int.', 'N° de Informe de Comprobación Int.',
                                'F. de Comprobación Int.', 'F. de Próx. Comprobación Int.'], 37.5),
    'caracterizacion': ('CARACTERIZACIÓN', ['Frecuencia de Caracterización', 'N° de informe de Caracterización',
                        'F. de Caracterización', 'F. de Próx. Caracterización'], 40.5),
}


def _hoja_bitacora(W, alto_util, tipo, registros, identificacion=None):
    """Flowables de una pestaña de bitácora con la grilla del Excel: franja con
    el título, encabezado y filas de 41,25 pt (escaladas) hasta llenar la hoja."""
    azul = colors.HexColor('#16365C')
    es_suceso = tipo == 'suceso'
    anchos = _ANCHOS_BIT_HIST[:30] if es_suceso else (_ANCHOS_BIT_MANT if tipo == 'mantenimiento' else _ANCHOS_BIT)
    cwx, k = _grilla_excel(W, anchos)
    tot = float(sum(anchos))
    seg = (lambda a, b: W * sum(anchos[_col_idx(a):_col_idx(b) + 1]) / tot)
    f = 7.2
    th = ParagraphStyle('bth', fontName='Helvetica-Bold', fontSize=f, leading=f * 1.15, alignment=TA_CENTER, textColor=colors.white)
    td = ParagraphStyle('btd', fontName='Helvetica', fontSize=f + 0.4, leading=(f + 0.4) * 1.2)
    tdc = ParagraphStyle('btdc', parent=td, alignment=TA_CENTER)
    banda = ParagraphStyle('bband', fontName='Helvetica-Bold', fontSize=f + 0.6, leading=f * 1.3, alignment=TA_CENTER, textColor=colors.white)
    out = []
    if identificacion:
        out += [Paragraph(identificacion, ParagraphStyle('bid', fontName='Helvetica', fontSize=7.5, leading=9)), Spacer(1, 3)]
    if es_suceso:
        titulo = 'HISTORIAL DE SUCESOS'
        cols = [seg('A', 'A'), seg('B', 'I'), seg('J', 'L'), seg('M', 'P'), seg('Q', 'Y'), seg('Z', 'AD')]
        cab = ['Nº', 'Sucesos', 'F. de Suceso', 'F. de Solución', 'Observaciones / Solución', 'Firma V°B°']
        alto_cab = 30
    else:
        titulo, nombres, alto_cab = HOJAS_BITACORA.get(tipo, (str(tipo).upper(), ['Frecuencia', 'N° de documento', 'Fecha', 'Próxima fecha'], 36))
        cols = [seg('A', 'A'), seg('B', 'E'), seg('F', 'J'), seg('K', 'N'), seg('O', 'R'), seg('S', 'AA'), seg('AB', 'AE')]
        cab = ['N°'] + nombres + ['Observaciones', 'Firma V°B°']
    band_t = Table([[Paragraph(titulo, banda)]], colWidths=[W], rowHeights=[22.5 * k])
    band_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), azul), ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    out += [Spacer(1, 7.5 * k), band_t, Spacer(1, 6 * k)]
    filas = [[Paragraph(c, th) for c in cab]]
    for n, r in enumerate(registros, 1):
        if es_suceso:
            celdas = [str(n), r.descripcion or '', _f(r.fecha), _f(r.fecha_proxima), r.observaciones or '', r.vb or '']
            estilos = [tdc, td, tdc, tdc, td, tdc]
        else:
            celdas = [str(n), r.frecuencia or '', r.numero_documento or '', _f(r.fecha), _f(r.fecha_proxima), r.observaciones or '', r.vb or '']
            estilos = [tdc, tdc, tdc, tdc, tdc, td, tdc]
        filas.append([Paragraph(str(c).replace('&', '&amp;').replace('<', '&lt;'), st) for c, st in zip(celdas, estilos)])
    alto_fila = 41.25 * k
    usado = 7.5 * k + 22.5 * k + 6 * k + alto_cab * k + (12 if identificacion else 0)
    minimo = max(1, int((alto_util - usado - 14) // (alto_fila + 0.5)))   # margen para bordes y redondeos
    while len(filas) - 1 < minimo:
        filas.append([''] * len(cols))
    t = Table(filas, colWidths=cols, rowHeights=[alto_cab * k] + [alto_fila] * (len(filas) - 1), repeatRows=1)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), azul),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2)]))
    out.append(t)
    return out


def _hoja_ficha_tecnica(W, equipo, cfg):
    """Pestaña "Ficha Técnica" de la Hoja de Vida con la grilla del Excel
    (29 columnas de 4,29): fecha de actualización, datos generales con las
    casillas de clasificación, especificaciones técnicas y recuadro de imagen."""
    azul = colors.HexColor('#16365C')
    anchos = [4.29] * 29                                      # columnas A..AC
    _, k = _grilla_excel(W, anchos)
    ancho, fila = _grilla(W, anchos)
    f = 7.6
    lblw = ParagraphStyle('ftlw', fontName='Helvetica-Bold', fontSize=f, leading=f * 1.15, textColor=colors.white)
    lblwc = ParagraphStyle('ftlwc', parent=lblw, alignment=TA_CENTER)
    lbl = ParagraphStyle('ftl', fontName='Helvetica-Bold', fontSize=f, leading=f * 1.2)
    lblc = ParagraphStyle('ftlc', parent=lbl, alignment=TA_CENTER)
    val = ParagraphStyle('ftv', fontName='Helvetica', fontSize=f + 0.6, leading=(f + 0.6) * 1.2)
    valc = ParagraphStyle('ftvc', parent=val, alignment=TA_CENTER)
    nombre_st = ParagraphStyle('ftnom', fontName='Helvetica-BoldOblique', fontSize=f + 2, leading=(f + 2) * 1.2,
                               alignment=TA_CENTER, textColor=colors.HexColor('#C00000'))

    def esc(t):
        return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    rh = lambda pt: pt * k
    sep = lambda pt=15: Spacer(1, rh(pt) * 0.6)
    out = [fila([('G', 'N', Paragraph('FECHA DE ACTUALIZACIÓN:', lblwc), azul),
                 ('O', 'W', Paragraph(_f(equipo.updated_at.date() if getattr(equipo, 'updated_at', None) else None), valc))], alto=rh(21)),
           sep(),
           fila([('A', 'AC', Paragraph('DATOS GENERALES', lblw), azul)], alto=rh(15), borde=False),
           fila([('A', 'C', Paragraph('Clasificación', lbl))], alto=rh(18.75), borde=False)]

    # Casillas de clasificación (B:F rótulo, G:H casilla) y, a la derecha,
    # inicio de servicio y código de identificación (O:S rótulo, V:AA valor).
    marcas = [(nombre, equipo.clasificacion == nombre) for _, nombre in CLASIFICACIONES]
    filas = []
    for n, (nombre, marcado) in enumerate(marcas):
        rot = 'Equipamiento' if nombre == 'Equipamiento Auxiliar' else nombre
        filas.append(['', Paragraph(rot, lbl), Paragraph('X' if marcado else '', valc), '', '', '', ''])
        if n < 3:
            filas.append([''] * 7)
    der = [(0, 'Inicio de Servicio', _anio(getattr(equipo, 'inicio_servicio', None))),
           (4, 'Código de Identificación', equipo.codigo)]
    for r0, rot, v in der:
        filas[r0][4] = Paragraph(rot, lblc)
        filas[r0][6] = Paragraph(f'<b>{esc(v)}</b>', ParagraphStyle('ftbig', parent=valc, fontSize=f + 3, leading=(f + 3) * 1.2))
    cw = [ancho('A', 'A'), ancho('B', 'F'), ancho('G', 'H'), ancho('I', 'N'), ancho('O', 'S'), ancho('T', 'U'), ancho('V', 'AA')]
    cw.append(W - sum(cw))
    filas = [x + [''] for x in filas]
    est = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]
    for r in (0, 2, 4, 6):
        est.append(('BOX', (2, r), (2, r), 0.6, colors.black))
    for r0, _, _ in der:
        est += [('SPAN', (4, r0), (4, r0 + 2)), ('SPAN', (6, r0), (6, r0 + 2)), ('BOX', (6, r0), (6, r0 + 2), 0.6, colors.black)]
    t = Table(filas, colWidths=cw, rowHeights=[rh(18.75)] * 7)
    t.setStyle(TableStyle(est))
    out += [t, sep(),
            fila([('A', 'AC', Paragraph('ESPECIFICACIONES TÉCNICAS', lblw), azul)], alto=rh(15), borde=False),
            fila([('A', 'AC', Paragraph(esc(equipo.nombre or '').upper(), nombre_st))], alto=rh(27))]

    def par(r1, v1, r2, v2, alto):
        return fila([('A', 'C', Paragraph(r1, lblw), azul), ('D', 'O', Paragraph(esc(v1), valc)),
                     ('P', 'T', Paragraph(r2, lblw), azul), ('U', 'AC', Paragraph(esc(v2), valc))], alto=rh(alto))
    out += [par('Marca', equipo.marca, 'Intervalo de Indicación/ Valor Nominal', equipo.intervalo_indicacion or equipo.cantidad, 37.5),
            par('Modelo', equipo.modelo, 'División de Escala (d) / División de Verificación (e)', equipo.division_escala or equipo.resolucion, 42.75),
            par('Nº de Serie', equipo.serie, 'Clase de Exactitud', equipo.clase_exactitud, 30),
            par('Procedencia', equipo.procedencia, 'Cantidad', equipo.cantidad_unidades, 30),
            par('Tipo de Indicación', equipo.tipo_indicacion, 'Material', equipo.material, 30),
            fila([('A', 'C', Paragraph('Ubicación', lblw), azul), ('D', 'O', Paragraph(esc(equipo.laboratorio), valc)),
                  ('P', 'T', Paragraph('Instructivo', lblwc), azul), ('U', 'V', Paragraph(_mk(equipo.instructivo), valc)),
                  ('W', 'Z', Paragraph('Manual', lblwc), azul), ('AA', 'AB', Paragraph(_mk(equipo.manual), valc))], alto=rh(30)),
            fila([('A', 'F', Paragraph('Criterio de Aceptación', lblw), azul), ('G', 'AC', Paragraph(esc(equipo.criterio_aceptacion), val))], alto=rh(30)),
            Spacer(1, rh(30))]
    # Recuadro de la imagen del equipo (B30:AB56)
    caja_w, caja_h = ancho('B', 'AB'), rh(15) * 27
    contenido = ''
    try:
        if equipo.imagen and equipo.imagen.path:
            img = Image(equipo.imagen.path)
            r = min((caja_w - 12) / img.imageWidth, (caja_h - 12) / img.imageHeight)
            img.drawWidth, img.drawHeight = img.imageWidth * r, img.imageHeight * r
            contenido = img
    except Exception:
        contenido = ''
    caja = Table([['', contenido, '']], colWidths=[ancho('A', 'A'), caja_w, W - ancho('A', 'A') - caja_w], rowHeights=[caja_h])
    caja.setStyle(TableStyle([('BOX', (1, 0), (1, 0), 0.6, colors.black), ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                              ('VALIGN', (1, 0), (1, 0), 'MIDDLE')]))
    out.append(caja)
    return out


def _doc_hoja_de_vida(titulo_pdf):
    """Documento A4 con la cabecera de la Hoja de Vida repetida en cada hoja."""
    cfg = _cargar_cfg()
    margen = 10 * mm
    W = A4[0] - 2 * margen
    cab = _cabecera_met12(W, 'HOJA DE VIDA', CODIGO_FORMATO, cfg)
    _, alto_cab = cab.wrap(W, A4[1])

    def _pag(canvas, doc_):
        canvas.saveState()
        cab.drawOn(canvas, margen, A4[1] - margen - alto_cab)
        canvas.restoreState()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=margen, rightMargin=margen,
                            topMargin=margen + alto_cab + 2 * mm, bottomMargin=margen, title=titulo_pdf)
    alto_util = A4[1] - (margen + alto_cab + 2 * mm) - margen - 8
    return buf, doc, W, alto_util, cfg, _pag


def generar_ficha_pdf(equipo) -> bytes:
    """Hoja de Vida completa del equipo, como el libro Excel del formato: la
    Ficha Técnica y una hoja por cada bitácora (mantenimiento preventivo,
    calibraciones, verificaciones, comprobaciones intermedias,
    caracterización e historial de sucesos)."""
    buf, doc, W, alto_util, cfg, pag = _doc_hoja_de_vida(f'Hoja de Vida {equipo.codigo}')
    story = _hoja_ficha_tecnica(W, equipo, cfg)
    ident = f'<b>{equipo.codigo}</b> · {(equipo.nombre or "").replace("&", "&amp;")}'
    for tipo in ('mantenimiento', 'calibracion', 'verificacion', 'comprobacion_intermedia', 'caracterizacion', 'suceso'):
        regs = list(equipo.registros.filter(tipo=tipo).order_by('fecha', 'id')) if hasattr(equipo, 'registros') else []
        story.append(PageBreak())
        story += _hoja_bitacora(W, alto_util, tipo, regs, identificacion=ident)
    doc.build(story, onFirstPage=pag, onLaterPages=pag)
    return buf.getvalue()


def generar_bitacora_pdf(equipo, tipo, titulo, registros) -> bytes:
    """Una hoja de bitácora de la Hoja de Vida (la pestaña del tipo pedido), con
    una línea que identifica al equipo porque se imprime suelta."""
    buf, doc, W, alto_util, cfg, pag = _doc_hoja_de_vida(f'{titulo} {equipo.codigo}')
    ident = f'<b>{equipo.codigo}</b> · {(equipo.nombre or "").replace("&", "&amp;")}'
    regs = sorted(list(registros), key=lambda r: (r.fecha is None, r.fecha, r.id))
    doc.build(_hoja_bitacora(W, alto_util, tipo, regs, identificacion=ident), onFirstPage=pag, onLaterPages=pag)
    return buf.getvalue()


def generar_inventario_pdf(equipos, laboratorio='') -> bytes:
    """Inventario de equipos con las columnas del formato en Excel (A a R, con
    Observaciones en P:R), fecha de actualización y laboratorio, filas en
    blanco hasta llenar la hoja y el estado calculado como en el Excel:
    Instrumento Calibrado (próxima calibración futura), Calibración Requerida
    (vencida) o No Aplica, con sus colores."""
    from reportlab.lib.pagesizes import landscape
    from django.utils import timezone
    margen = 8 * mm
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=margen, rightMargin=margen,
                            topMargin=margen, bottomMargin=margen, title='Inventario de Equipos')
    W = doc.width
    cfg = _cargar_cfg()
    azul = colors.HexColor('#16365C')
    anchos = [20.43, 35.57, 18.86, 24.71, 20.71, 22.57, 17.43, 14.86, 16.86, 19.14, 15.86, 19.0, 19.0, 24.57, 25.0, 19.71, 19.71, 19.71]
    ancho, fila = _grilla(W, anchos)
    lblw = ParagraphStyle('ivlblw', fontName='Helvetica-Bold', fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=colors.white)
    valc = ParagraphStyle('ivvalc', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_CENTER)
    th = ParagraphStyle('ivth', fontName='Helvetica-Bold', fontSize=5.5, leading=6.6, alignment=TA_CENTER, textColor=colors.white)
    td = ParagraphStyle('ivtd', fontName='Helvetica', fontSize=6.3, leading=7.6, alignment=TA_CENTER)
    tdb = ParagraphStyle('ivtdb', parent=td, fontName='Helvetica-Bold')
    tdl = ParagraphStyle('ivtdl', parent=td, alignment=TA_LEFT)

    hoy = timezone.now().date()
    fechas_upd = [e.updated_at for e in equipos if getattr(e, 'updated_at', None)]
    fecha_act = (max(fechas_upd).date() if fechas_upd else hoy)
    story = [_cabecera_met12(W, 'INVENTARIO DE EQUIPOS', 'MET-PRO-04-r02', cfg), Spacer(1, 6),
             fila([('B', 'B', Paragraph('FECHA DE ACTUALIZACIÓN', ParagraphStyle('ivfa', parent=lblw, fontSize=6.8)), azul), ('C', 'D', Paragraph(_f(fecha_act), valc)),
                   ('I', 'J', Paragraph('LABORATORIO:', lblw), azul), ('K', 'M', Paragraph(str(laboratorio or ''), valc))], alto=16),
             Spacer(1, 6)]
    band = Table([[Paragraph('EQUIPOS', lblw)]], colWidths=[W], rowHeights=[14])
    band.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), azul), ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story.append(band)

    VERDE, AMBAR, ROJO = colors.HexColor('#C6EFCE'), colors.HexColor('#FFEB9C'), colors.HexColor('#FFC7CE')
    TXT = {VERDE: colors.HexColor('#006100'), AMBAR: colors.HexColor('#9C5700'), ROJO: colors.HexColor('#9C0006')}
    encabezados = ['Código', 'Descripción', 'Clasificación', 'Marca', 'Modelo', 'Nº Serie', 'Alcance / Cantidad', 'Clase',
                   'Resolución', 'N° de Certificado de Calibración', 'Periodicidad de Calibración (Días)',
                   'Fecha de la Última Calibración', 'Fecha de Próxima Calibración', 'Estado', 'Proveedor de Calibración', 'Observaciones']
    cw = anchos[:15] + [sum(anchos[15:18])]
    tot = float(sum(anchos))
    cw = [W * a / tot for a in cw]
    filas = [[Paragraph(h, th) for h in encabezados]]
    estilos = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), azul),
               ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
               ('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
               ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2)]
    for n, e in enumerate(equipos, start=1):
        prox, ult = e.fecha_proxima_calibracion, e.fecha_ultima_calibracion
        if not e.requiere_calibracion:
            estado_txt, color = 'No Aplica', AMBAR
            prox_txt = ult_txt = 'No aplica'
        else:
            ult_txt, prox_txt = _f(ult) or '-', _f(prox) or '-'
            if prox and prox > hoy:
                estado_txt, color = 'Instrumento Calibrado', VERDE
            elif prox:
                estado_txt, color = 'Calibración Requerida', ROJO
            else:
                estado_txt, color = '-', None
        celdas = [e.codigo, e.nombre, e.clasificacion, e.marca, e.modelo, e.serie,
                  e.cantidad or e.intervalo_indicacion, e.clase_exactitud, e.resolucion or e.division_escala, e.n_certificado,
                  (e.periodicidad_dias if e.requiere_calibracion else 'No aplica') or '', ult_txt, prox_txt, estado_txt,
                  e.proveedor_calibracion, e.observaciones]
        estilos_c = [tdb] + [td] * 14 + [tdl]
        fila_p = [Paragraph(str(c or '').replace('&', '&amp;').replace('<', '&lt;'), st) for c, st in zip(celdas, estilos_c)]
        if color is not None:
            fila_p[13] = Paragraph(estado_txt, ParagraphStyle(f'ives{n}', parent=td, textColor=TXT[color]))
            estilos.append(('BACKGROUND', (13, n), (13, n), color))
        filas.append(fila_p)
    # Filas en blanco hasta completar la hoja, como el formato impreso
    while len(filas) - 1 < 30:
        filas.append([''] * 16)
    t = Table(filas, colWidths=cw, rowHeights=[24] + [None] * (len(filas) - 1), repeatRows=1)
    for r in range(len(equipos) + 1, len(filas)):
        estilos.append(('ROWBACKGROUNDS', (0, r), (-1, r), [colors.white]))
    t.setStyle(TableStyle(estilos))
    t._argH = [None] + [h if h else 11.5 for h in t._argH[1:]]
    if len(equipos):
        t._argH[1:len(equipos) + 1] = [None] * len(equipos)
    story.append(t)
    doc.build(story)
    return buf.getvalue()


BLOQUES_PROGRAMA = [
    ('MANTENIMIENTO Y CALIBRACIÓN', ['calibracion', 'mantenimiento']),
    ('COMPROBACIÓN INTERMEDIA Y CARACTERIZACIÓN', ['comprobacion_intermedia', 'caracterizacion']),
    ('COMPROBACIÓN FUNCIONAL', ['comprobacion_funcional']),
]
MESES_PROGRAMA = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
SIGLAS_PROGRAMA = {'mantenimiento': 'M', 'calibracion': 'C', 'comprobacion_intermedia': 'CI', 'comprobacion_funcional': 'CF', 'caracterizacion': 'Ca'}


def generar_programa_pdf(equipos, anio, laboratorio='') -> bytes:
    """PDF horizontal del Programa Anual: matriz equipos x bloques x meses."""
    from reportlab.lib.pagesizes import landscape
    from django.utils import timezone
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=6 * mm, rightMargin=6 * mm, topMargin=8 * mm, bottomMargin=8 * mm,
        title='Programa Anual de Equipos',
    )
    W = doc.width

    title = ParagraphStyle('pgtitle', fontName='Helvetica-Bold', fontSize=11, leading=12, alignment=TA_CENTER)
    minic = ParagraphStyle('pgminic', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_CENTER)
    minibc = ParagraphStyle('pgminibc', fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=TA_CENTER)
    lblw = ParagraphStyle('pglblw', fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=TA_CENTER, textColor=colors.white)
    valc = ParagraphStyle('pgvalc', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_CENTER)
    band = ParagraphStyle('pgband', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER, textColor=colors.white)
    th = ParagraphStyle('pgth', fontName='Helvetica-Bold', fontSize=5.2, leading=6, alignment=TA_CENTER, textColor=colors.white)
    td = ParagraphStyle('pgtd', fontName='Helvetica', fontSize=5.2, leading=6, alignment=TA_CENTER)
    tdb = ParagraphStyle('pgtdb', fontName='Helvetica-Bold', fontSize=5.2, leading=6, alignment=TA_CENTER)
    thm = ParagraphStyle('pgthm', fontName='Helvetica-Bold', fontSize=4.2, leading=5, alignment=TA_CENTER, textColor=colors.white)

    cfg = None
    empresa = ''
    try:
        from core.models import ConfiguracionSistema
        cfg = ConfiguracionSistema.cargar()
        empresa = empresa_nombre(cfg, vacio='')
    except Exception:
        pass
    _c = control_formato('MET-PRO-04-r03', cfg)
    elaborado_s, revisado_s, aprobado_s = _c['elaborado'], _c['revisado'], _c['aprobado']

    story = []
    logo_cell = Paragraph(empresa or 'EMPRESA', ParagraphStyle('pglogo', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER))
    try:
        _logo = (getattr(cfg, 'logo_empresa', None) or getattr(cfg, 'logo', None)) if cfg else None
        if _logo and _logo.path:
            im = Image(_logo.path)
            r = min((W * 0.13) / im.imageWidth, (20 * mm) / im.imageHeight)
            im.drawWidth = im.imageWidth * r
            im.drawHeight = im.imageHeight * r
            im.hAlign = 'CENTER'
            logo_cell = im
    except Exception:
        pass

    c6 = W * 0.24 / 6.0
    hdr_data = [
        [logo_cell, Paragraph('PROGRAMA DE MANTENIMIENTO, CALIBRACIÓN, COMPROBACIÓN INTERMEDIA, COMPROBACIÓN FUNCIONAL Y CARACTERIZACIÓN', title), Paragraph('Código:', minibc), '', '', Paragraph(_c['codigo'], minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(_c['version'], minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(_c['fecha'], minic), '', ''],
        ['', '', Paragraph('Elaborado', minibc), '', Paragraph('Revisado', minibc), '', Paragraph('Aprobado', minibc), ''],
        ['', '', Paragraph(elaborado_s, minic), '', Paragraph(revisado_s, minic), '', Paragraph(aprobado_s, minic), ''],
    ]
    hdr = Table(hdr_data, colWidths=[W * 0.14, W * 0.62, c6, c6, c6, c6, c6, c6], rowHeights=[4.6 * mm] * 5)
    hdr.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('SPAN', (0, 0), (0, 4)), ('SPAN', (1, 0), (1, 4)),
        ('SPAN', (2, 0), (4, 0)), ('SPAN', (5, 0), (7, 0)),
        ('SPAN', (2, 1), (4, 1)), ('SPAN', (5, 1), (7, 1)),
        ('SPAN', (2, 2), (4, 2)), ('SPAN', (5, 2), (7, 2)),
        ('SPAN', (2, 3), (3, 3)), ('SPAN', (4, 3), (5, 3)), ('SPAN', (6, 3), (7, 3)),
        ('SPAN', (2, 4), (3, 4)), ('SPAN', (4, 4), (5, 4)), ('SPAN', (6, 4), (7, 4)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 4), 'CENTER'), ('ALIGN', (2, 0), (7, 4), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 6))

    hoy = timezone.now().date()
    # Fecha de actualización y laboratorio, como dos bloques separados del formato.
    info = Table([['', Paragraph('FECHA DE ACTUALIZACIÓN:', lblw), Paragraph(_f(hoy), valc), '',
                   Paragraph('LABORATORIO:', lblw), Paragraph(laboratorio or '', valc), '']],
                 colWidths=[W * 0.14, W * 0.12, W * 0.09, W * 0.20, W * 0.08, W * 0.12, W * 0.25], rowHeights=[5.5 * mm])
    info.setStyle(TableStyle([
        ('BOX', (1, 0), (2, 0), 0.6, colors.black), ('LINEAFTER', (1, 0), (1, 0), 0.6, colors.black),
        ('BOX', (4, 0), (5, 0), 0.6, colors.black), ('LINEAFTER', (4, 0), (4, 0), 0.6, colors.black),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#16365C')), ('BACKGROUND', (4, 0), (4, 0), colors.HexColor('#16365C')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(info)
    story.append(Spacer(1, 6))

    # ---- Matriz ----
    eq_cols = ['Equipo / Instrumento', 'Código', 'Alcance / Cantidad', 'Clase', 'Marca', 'Modelo', 'Serie']
    n_eq = len(eq_cols)
    # Fila superior del formato: "AÑO" sobre los datos del equipo y el año sobre el programa.
    fila_anio = [Paragraph('AÑO', th)] + [''] * (n_eq - 1) + [Paragraph(str(anio), ParagraphStyle('pgan', parent=th, fontSize=9, leading=11))] + [''] * 38
    fila0 = [Paragraph(h, th) for h in eq_cols]
    fila1 = ['' for _ in eq_cols]
    for titulo_bloque, _tipos in BLOQUES_PROGRAMA:
        fila0.append(Paragraph(titulo_bloque, th))
        fila0 += [''] * 12
        fila1.append(Paragraph('Frecuencia', thm))
        fila1 += [Paragraph(m, thm) for m in MESES_PROGRAMA]
    filas = [fila_anio, fila0, fila1]

    for e in equipos:
        acts = e.get('actividades', {})
        celdas = [Paragraph(str(e.get('nombre') or ''), tdb), Paragraph(str(e.get('codigo') or ''), tdb),
                  Paragraph(str(e.get('cantidad') or ''), td), Paragraph(str(e.get('clase_exactitud') or ''), td),
                  Paragraph(str(e.get('marca') or ''), td), Paragraph(str(e.get('modelo') or ''), td),
                  Paragraph(str(e.get('serie') or ''), td)]
        for _titulo, tipos in BLOQUES_PROGRAMA:
            frecs = []
            por_mes = {mi: [] for mi in range(1, 13)}
            for t in tipos:
                a = acts.get(t)
                if a:
                    if a.get('frecuencia'):
                        frecs.append(a['frecuencia'])
                    for m in (a.get('meses') or []):
                        por_mes[int(m)].append(SIGLAS_PROGRAMA.get(t, 'X'))
            celdas.append(Paragraph(' / '.join(dict.fromkeys(frecs)), td))
            for mi in range(1, 13):
                celdas.append(Paragraph('/'.join(por_mes[mi]), tdb))
        filas.append(celdas)

    # Anchos de columna del Excel (A..AT)
    u = [28.29, 13.14, 23.29, 15.43, 27.14, 27.14, 17.14] + [13.86] + [6.43] * 12 + [13.86] + [7.14] * 12 + [17.29] + [7.29] * 12
    while len(filas) - 3 < 25:
        filas.append([''] * len(u))
    anchos = [W * x / sum(u) for x in u]

    estilos = [
        ('GRID', (0, 0), (-1, -1), 0.4, LINEA),
        ('BACKGROUND', (0, 0), (-1, 1), BANDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 1), ('RIGHTPADDING', (0, 0), (-1, -1), 1),
    ]
    estilos += [('BACKGROUND', (0, 2), (-1, 2), BANDA), ('SPAN', (0, 0), (n_eq - 1, 0)), ('SPAN', (n_eq, 0), (-1, 0))]
    for j in range(n_eq):
        estilos.append(('SPAN', (j, 1), (j, 2)))
    for b in range(3):
        ini = n_eq + b * 13
        estilos.append(('SPAN', (ini, 1), (ini + 12, 1)))

    tb = Table(filas, colWidths=anchos, repeatRows=3, rowHeights=[None] * 3 + [None if n < len(equipos) else 11 for n in range(len(filas) - 3)])
    # Meses: sin margen interno para que el rótulo entre en la columna angosta.
    estilos += [('LEFTPADDING', (n_eq, 2), (-1, 2), 0), ('RIGHTPADDING', (n_eq, 2), (-1, 2), 0)]
    tb.setStyle(TableStyle(estilos))
    story.append(tb)

    story.append(Spacer(1, 5))
    story.append(Paragraph(
        '<b>Leyenda:</b> &nbsp; M: Mantenimiento &nbsp;&nbsp; C: Calibración &nbsp;&nbsp; '
        'CI: Comprobación Intermedia &nbsp;&nbsp; CF: Comprobación Funcional &nbsp;&nbsp; Ca: Caracterización',
        ParagraphStyle('pgleyenda', fontName='Helvetica', fontSize=7, leading=9)))

    doc.build(story)
    return buf.getvalue()


def generar_carta_trazabilidad_pdf(carta, nodos) -> bytes:
    """
    Dibuja el árbol de una carta de trazabilidad (cajas + conectores) en una
    página horizontal con el encabezado del formato. 'nodos' es una lista de
    dicts con: id, padre, orden, entidad, descripcion, codigo, procedimiento,
    certificado, incertidumbre.
    """
    from reportlab.lib.pagesizes import landscape
    from reportlab.platypus import Flowable
    from reportlab.pdfbase.pdfmetrics import stringWidth

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=8 * mm, rightMargin=8 * mm, topMargin=8 * mm, bottomMargin=8 * mm,
        title=f'Carta de Trazabilidad {getattr(carta, "magnitud", "") or ""}',
    )
    W = doc.width

    title = ParagraphStyle('cttitle', fontName='Helvetica-Bold', fontSize=16, leading=18, alignment=TA_CENTER)
    minic = ParagraphStyle('ctminic', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_CENTER)
    minibc = ParagraphStyle('ctminibc', fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=TA_CENTER)
    lblw = ParagraphStyle('ctlblw', fontName='Helvetica-Bold', fontSize=8.5, leading=10, alignment=TA_CENTER, textColor=colors.white)
    valc = ParagraphStyle('ctvalc', fontName='Helvetica-Bold', fontSize=8.5, leading=10, alignment=TA_CENTER)
    band = ParagraphStyle('ctband', fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=TA_CENTER, textColor=colors.white)

    cfg = None
    empresa = ''
    try:
        from core.models import ConfiguracionSistema
        cfg = ConfiguracionSistema.cargar()
        empresa = empresa_nombre(cfg, vacio='')
    except Exception:
        pass
    _c = control_formato('MET-PRO-04-r04', cfg)
    elaborado_s, revisado_s, aprobado_s = _c['elaborado'], _c['revisado'], _c['aprobado']

    story = []
    logo_cell = Paragraph(empresa or 'EMPRESA', ParagraphStyle('ctlogo', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER))
    try:
        _logo = (getattr(cfg, 'logo_empresa', None) or getattr(cfg, 'logo', None)) if cfg else None
        if _logo and _logo.path:
            im = Image(_logo.path)
            r = min((W * 0.13) / im.imageWidth, (20 * mm) / im.imageHeight)
            im.drawWidth = im.imageWidth * r
            im.drawHeight = im.imageHeight * r
            im.hAlign = 'CENTER'
            logo_cell = im
    except Exception:
        pass

    c6 = W * 0.24 / 6.0
    hdr_data = [
        [logo_cell, Paragraph('CARTA DE TRAZABILIDAD', title), Paragraph('Código:', minibc), '', '', Paragraph(_c['codigo'], minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(_c['version'], minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(_c['fecha'], minic), '', ''],
        ['', '', Paragraph('Elaborado', minibc), '', Paragraph('Revisado', minibc), '', Paragraph('Aprobado', minibc), ''],
        ['', '', Paragraph(elaborado_s, minic), '', Paragraph(revisado_s, minic), '', Paragraph(aprobado_s, minic), ''],
    ]
    hdr = Table(hdr_data, colWidths=[W * 0.14, W * 0.62, c6, c6, c6, c6, c6, c6], rowHeights=[4.6 * mm] * 5)
    hdr.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('SPAN', (0, 0), (0, 4)), ('SPAN', (1, 0), (1, 4)),
        ('SPAN', (2, 0), (4, 0)), ('SPAN', (5, 0), (7, 0)),
        ('SPAN', (2, 1), (4, 1)), ('SPAN', (5, 1), (7, 1)),
        ('SPAN', (2, 2), (4, 2)), ('SPAN', (5, 2), (7, 2)),
        ('SPAN', (2, 3), (3, 3)), ('SPAN', (4, 3), (5, 3)), ('SPAN', (6, 3), (7, 3)),
        ('SPAN', (2, 4), (3, 4)), ('SPAN', (4, 4), (5, 4)), ('SPAN', (6, 4), (7, 4)),
        ('ALIGN', (0, 0), (0, 4), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 5))

    fecha = carta.fecha_actualizacion.isoformat() if getattr(carta, 'fecha_actualizacion', None) else ''
    info = Table([
        [Paragraph('MAGNITUD:', lblw), Paragraph(carta.magnitud or '', valc)],
        [Paragraph('PROCEDIMIENTO DE CALIBRACIÓN:', lblw), Paragraph(carta.procedimiento_calibracion or '', valc)],
        [Paragraph('FECHA DE ACTUALIZACIÓN:', lblw), Paragraph(fecha, valc)],
    ], colWidths=[W * 0.22, W * 0.78], rowHeights=[6.5 * mm] * 3)
    info.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('BACKGROUND', (0, 0), (0, -1), BANDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(info)
    story.append(Spacer(1, 4))

    rojo = colors.HexColor('#C00000')
    banda = Table([[Paragraph('PATRONES NACIONALES E INTERNACIONALES', band)]], colWidths=[W], rowHeights=[7 * mm])
    banda.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), rojo), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story.append(banda)
    story.append(Spacer(1, 2))

    nodos = list(nodos or [])
    avail_h = doc.height - 58 * mm
    if avail_h < 120:
        avail_h = doc.height * 0.55

    if not nodos:
        story.append(Paragraph('La carta aún no tiene nodos. Agrega eslabones desde el editor.',
                               ParagraphStyle('ctempty', fontName='Helvetica', fontSize=10, alignment=TA_CENTER)))
        doc.build(story)
        return buf.getvalue()

    by_id = {n['id']: n for n in nodos}
    ids_all = [n['id'] for n in nodos]
    from collections import defaultdict
    # Hijos por cada padre (un nodo puede tener varios padres)
    kids = defaultdict(list)
    for n in nodos:
        for p in (n.get('padres') or []):
            if p in by_id:
                kids[p].append(n['id'])
    # Agrupar por nivel y ordenar por 'orden'
    por_nivel = defaultdict(list)
    for n in nodos:
        por_nivel[int(n.get('nivel') or 1)].append(n['id'])
    for lv in por_nivel:
        por_nivel[lv].sort(key=lambda i: (by_id[i].get('orden') or 0, i))
    niveles = sorted(por_nivel)
    maxcount = max((len(v) for v in por_nivel.values()), default=1)
    col_w = W / maxcount
    bw = min(col_w - 10, 150)
    PADX, HEADH, line_h = 4, 9, 6.2

    def niv(nid):
        return int(by_id[nid].get('nivel') or 1)

    # x de cada nodo: repartido en su nivel a lo ancho de la página
    node_x = {}
    for lv, ids in por_nivel.items():
        n_in = len(ids) or 1
        for i, nid in enumerate(ids):
            node_x[nid] = (i + 0.5) * (W / n_in)

    def wrap(text, font, size, maxw):
        out = []
        for raw in str(text).split('\n'):
            cur = ''
            for w in raw.split():
                t = (cur + ' ' + w).strip()
                if stringWidth(t, font, size) <= maxw:
                    cur = t
                else:
                    if cur:
                        out.append(cur)
                    cur = w
            out.append(cur)
        return out or ['']

    # Cajas como en el formato: descripción en negrita, código de
    # identificación, certificado de calibración e incertidumbre (U = …),
    # centradas. Las hojas finales sin patrón (los instrumentos que se
    # calibran) van en el recuadro beige al pie, como en el Excel.
    def es_instrumento(n):
        return not kids.get(n['id']) and not n.get('equipo') and not n.get('certificado') and not n.get('codigo')

    def lineas_nodo(n):
        ls = []
        innerw = bw - 2 * PADX
        if n.get('descripcion'):
            for L in wrap(n['descripcion'], 'Helvetica-Bold', 5.6, innerw):
                ls.append(('Helvetica-Bold', 5.6, L))
        if n.get('codigo'):
            ls.append(('Helvetica', 5.2, 'Cód. Identificación: ' + n['codigo']))
        if n.get('certificado'):
            for L in wrap('Certificado de Calib.: ' + n['certificado'], 'Helvetica', 5.2, innerw):
                ls.append(('Helvetica', 5.2, L))
        if n.get('incertidumbre'):
            u = str(n['incertidumbre'])
            ls.append(('Helvetica', 5.2, u if u.strip().upper().startswith('U') else 'U = ' + u))
        for campo in ('procedimiento', 'nota'):
            if n.get(campo):
                for L in wrap(n[campo], 'Helvetica', 5.0, innerw):
                    ls.append(('Helvetica', 5.0, L))
        return ls

    node_lines = {nid: lineas_nodo(by_id[nid]) for nid in ids_all}
    node_h = {nid: 6 + max(1, len(node_lines[nid])) * line_h for nid in ids_all}
    for nid in ids_all:
        if es_instrumento(by_id[nid]):
            node_h[nid] += 6

    row_h = {}
    for nid in ids_all:
        lv = niv(nid)
        row_h[lv] = max(row_h.get(lv, 0), node_h[nid])
    VGAP = 26
    TOPGAP = 9  # flecha corta desde la banda al nivel 1, pegada (sin espacio extra)
    y_top = {}
    acc = TOPGAP
    for lv in niveles:
        y_top[lv] = acc
        acc += row_h.get(lv, 40) + VGAP
    total_h = acc - VGAP + 6

    # Color por nivel (nivel 1 verde, 2 azul, 3 naranja, 4 ámbar, 5 violeta)
    PALETA = [
        (colors.HexColor('#C6E0B4'), colors.HexColor('#548235')),
        (colors.HexColor('#BDD7EE'), colors.HexColor('#2E75B6')),
        (colors.HexColor('#F8CBAD'), colors.HexColor('#C55A11')),
        (colors.HexColor('#FFE699'), colors.HexColor('#BF8F00')),
        (colors.HexColor('#D9D2E9'), colors.HexColor('#674EA7')),
    ]

    def box_color(n):
        lv = int(n.get('nivel') or 1)
        return PALETA[(lv - 1) % len(PALETA)]

    fl_h = min(total_h, avail_h)
    sc = (fl_h / total_h) if total_h else 1

    def dibujar(cv):
        if sc != 1:
            cv.scale(sc, sc)

        def cx(nid):
            return node_x[nid]

        def ytop(nid):
            return total_h - y_top[niv(nid)]

        naranja = colors.HexColor('#ED7D31')
        cv.setStrokeColor(naranja); cv.setLineWidth(1.8); cv.setFillColor(naranja)
        aw, ah = 3.2, 5.5

        def flecha(x1, y1, x2, y2):
            cv.line(x1, y1, x2, y2 + ah - 0.5)
            p = cv.beginPath(); p.moveTo(x2, y2); p.lineTo(x2 - aw, y2 + ah); p.lineTo(x2 + aw, y2 + ah); p.close()
            cv.drawPath(p, fill=1, stroke=0)

        # Zona celeste: patrones propios del laboratorio (nodos enlazados a
        # equipos del inventario), detrás de sus niveles, como en el Excel.
        niveles_lab = [lv for lv in niveles if any(by_id[i].get('equipo') for i in por_nivel[lv])]
        if niveles_lab:
            arriba = total_h - y_top[niveles_lab[0]] + 6
            abajo = total_h - y_top[niveles_lab[-1]] - row_h[niveles_lab[-1]] - 6
            cv.setFillColor(colors.HexColor('#DCE6F1')); cv.setStrokeColor(colors.black); cv.setLineWidth(0.6)
            cv.rect(8, abajo, W - 16, arriba - abajo, fill=1, stroke=1)
            cv.setStrokeColor(naranja); cv.setFillColor(naranja); cv.setLineWidth(1.8)

        # Marco negro alrededor de hermanos con el mismo padre (grupos del formato)
        cv.setStrokeColor(colors.black); cv.setLineWidth(0.8)
        for pid, hijos in kids.items():
            mismos = [h for h in hijos if not es_instrumento(by_id[h])]
            if len(mismos) >= 2 and len({niv(h) for h in mismos}) == 1:
                xs = [cx(h) for h in mismos]
                yt_ = ytop(mismos[0]) + 3
                yb_ = ytop(mismos[0]) - max(node_h[h] for h in mismos) - 3
                cv.rect(min(xs) - bw / 2 - 3, yb_, max(xs) - min(xs) + bw + 6, yt_ - yb_, fill=0, stroke=1)
        cv.setStrokeColor(naranja); cv.setFillColor(naranja); cv.setLineWidth(1.8)

        # Flechas de cada padre hacia cada hijo; hacia los instrumentos, la
        # flecha gruesa del formato.
        for pid, hijos in kids.items():
            for hid in hijos:
                if es_instrumento(by_id[hid]):
                    x, y1, y2 = cx(hid), ytop(pid) - node_h[pid] - 2, ytop(hid) + 2
                    a = 9
                    p_ = cv.beginPath()
                    p_.moveTo(x - a * 0.55, y1); p_.lineTo(x + a * 0.55, y1); p_.lineTo(x + a * 0.55, (y1 + y2) / 2)
                    p_.lineTo(x + a * 1.3, (y1 + y2) / 2); p_.lineTo(x, y2); p_.lineTo(x - a * 1.3, (y1 + y2) / 2)
                    p_.lineTo(x - a * 0.55, (y1 + y2) / 2); p_.close()
                    cv.setFillColor(colors.HexColor('#F79646')); cv.setStrokeColor(colors.HexColor('#C0504D')); cv.setLineWidth(0.6)
                    cv.drawPath(p_, fill=1, stroke=1)
                    cv.setStrokeColor(naranja); cv.setFillColor(naranja); cv.setLineWidth(1.8)
                else:
                    flecha(cx(pid), ytop(pid) - node_h[pid], cx(hid), ytop(hid))

        # Flecha desde la banda hacia las cajas del nivel superior (pegada, sin espacio)
        for nid in por_nivel[niveles[0]]:
            flecha(cx(nid), total_h, cx(nid), ytop(nid))

        for nid in ids_all:
            n = by_id[nid]
            instr = es_instrumento(n)
            ancho_caja = bw * (1.6 if instr else 1)
            x0 = cx(nid) - ancho_caja / 2
            yt = ytop(nid)
            h = node_h[nid]
            if instr:
                cv.setFillColor(colors.HexColor('#EEECE1')); cv.setStrokeColor(colors.HexColor('#EEECE1'))
            else:
                cv.setFillColor(colors.HexColor('#92D050')); cv.setStrokeColor(colors.black)
            cv.setLineWidth(0.6)
            cv.rect(x0, yt - h, ancho_caja, h, fill=1, stroke=1)
            ty = yt - line_h - (4 if instr else 1)
            cv.setFillColor(colors.black)
            for fn, fs, txt in node_lines[nid]:
                cv.setFont(fn, fs)
                cv.drawCentredString(cx(nid), ty, txt)
                ty -= line_h

    class _Arbol(Flowable):
        def __init__(self, w, h):
            self.width = w
            self.height = h

        def wrap(self, aw, ah):
            return (self.width, self.height)

        def draw(self):
            dibujar(self.canv)

    story.append(_Arbol(W, fl_h))
    doc.build(story)
    return buf.getvalue()


def generar_intervalo_pdf(equipo, puntos) -> bytes:
    """
    PDF del Intervalo de Calibración: encabezado del formato,
    y por cada punto nominal del patrón una tarjeta con la tabla por año, el
    resumen (EMP/Umáx/Tolerancia/Deriva/Periodo OIML D10) y la gráfica con los
    límites ±EMP. 'puntos' es la lista serializada (valor_nominal, resultados, calculo).
    """
    from reportlab.lib.pagesizes import landscape
    from reportlab.platypus import Flowable
    from django.utils import timezone

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=8 * mm, rightMargin=8 * mm, topMargin=8 * mm, bottomMargin=8 * mm,
        title=f'Intervalo de Calibración {equipo.codigo}',
    )
    W = doc.width

    title = ParagraphStyle('intit', fontName='Helvetica-Bold', fontSize=15, leading=17, alignment=TA_CENTER)
    minic = ParagraphStyle('inminic', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_CENTER)
    minibc = ParagraphStyle('inminibc', fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=TA_CENTER)
    lblw = ParagraphStyle('inlblw', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_CENTER, textColor=colors.white)
    valc = ParagraphStyle('invalc', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_CENTER)

    cfg = None
    empresa = ''
    try:
        from core.models import ConfiguracionSistema
        cfg = ConfiguracionSistema.cargar()
        empresa = empresa_nombre(cfg, vacio='')
    except Exception:
        pass
    _c = control_formato('MET-PRO-04-r08', cfg)
    elaborado_s, revisado_s, aprobado_s = _c['elaborado'], _c['revisado'], _c['aprobado']

    story = []
    logo_cell = Paragraph(empresa or 'EMPRESA', ParagraphStyle('inlogo', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER))
    try:
        _logo = (getattr(cfg, 'logo_empresa', None) or getattr(cfg, 'logo', None)) if cfg else None
        if _logo and _logo.path:
            im = Image(_logo.path)
            r = min((W * 0.13) / im.imageWidth, (20 * mm) / im.imageHeight)
            im.drawWidth = im.imageWidth * r
            im.drawHeight = im.imageHeight * r
            im.hAlign = 'CENTER'
            logo_cell = im
    except Exception:
        pass

    c6 = W * 0.24 / 6.0
    hdr_data = [
        [logo_cell, Paragraph('INTERVALO DE CALIBRACIÓN', title), Paragraph('Código:', minibc), '', '', Paragraph(_c['codigo'], minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(_c['version'], minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(_c['fecha'], minic), '', ''],
        ['', '', Paragraph('Elaborado', minibc), '', Paragraph('Revisado', minibc), '', Paragraph('Aprobado', minibc), ''],
        ['', '', Paragraph(elaborado_s, minic), '', Paragraph(revisado_s, minic), '', Paragraph(aprobado_s, minic), ''],
    ]
    hdr = Table(hdr_data, colWidths=[W * 0.14, W * 0.62, c6, c6, c6, c6, c6, c6], rowHeights=[4.6 * mm] * 5)
    hdr.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('SPAN', (0, 0), (0, 4)), ('SPAN', (1, 0), (1, 4)),
        ('SPAN', (2, 0), (4, 0)), ('SPAN', (5, 0), (7, 0)),
        ('SPAN', (2, 1), (4, 1)), ('SPAN', (5, 1), (7, 1)),
        ('SPAN', (2, 2), (4, 2)), ('SPAN', (5, 2), (7, 2)),
        ('SPAN', (2, 3), (3, 3)), ('SPAN', (4, 3), (5, 3)), ('SPAN', (6, 3), (7, 3)),
        ('SPAN', (2, 4), (3, 4)), ('SPAN', (4, 4), (5, 4)), ('SPAN', (6, 4), (7, 4)),
        ('ALIGN', (0, 0), (0, 4), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 5))

    # Fila 7 del formato: fecha de actualización (B:D + E:H) y laboratorio (J:L + M:O)
    info = Table([['', Paragraph('FECHA DE ACTUALIZACIÓN:', lblw), Paragraph(_f(timezone.now().date()), valc), '',
                   Paragraph('LABORATORIO:', lblw), Paragraph(equipo.laboratorio or '', valc), '']],
                 colWidths=[W * 0.06, W * 0.19, W * 0.22, W * 0.06, W * 0.17, W * 0.2, W * 0.1], rowHeights=[6 * mm])
    info.setStyle(TableStyle([
        ('BOX', (1, 0), (2, 0), 0.6, colors.black), ('LINEAFTER', (1, 0), (1, 0), 0.6, colors.black),
        ('BOX', (4, 0), (5, 0), 0.6, colors.black), ('LINEAFTER', (4, 0), (4, 0), 0.6, colors.black),
        ('BACKGROUND', (1, 0), (1, 0), BANDA), ('BACKGROUND', (4, 0), (4, 0), BANDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(info)
    story.append(Spacer(1, 1))

    th = ParagraphStyle('inth', fontName='Helvetica-Bold', fontSize=4.8, leading=5.6, alignment=TA_CENTER, textColor=colors.white)
    td = ParagraphStyle('intd', fontName='Helvetica', fontSize=5.0, leading=6, alignment=TA_CENTER)
    tlbl = ParagraphStyle('intlbl', fontName='Helvetica-Bold', fontSize=4.8, leading=5.6)
    tval = ParagraphStyle('intval', fontName='Helvetica', fontSize=4.8, leading=5.6, alignment=TA_CENTER)
    cabp = ParagraphStyle('incabp', fontName='Helvetica-Bold', fontSize=6.2, leading=7.4, alignment=TA_CENTER, textColor=colors.white)

    def fnum(v, n=3):
        try:
            return f'{float(v):.{n}f}'
        except Exception:
            return ''

    class _ChartIntervalo(Flowable):
        def __init__(self, w, h, resultados, emp):
            self.width = w; self.height = h; self.rs = resultados; self.emp = abs(emp or 0)

        def wrap(self, aw, ah):
            return (self.width, self.height)

        def draw(self):
            import math
            c = self.canv; w = self.width; h = self.height
            rs = sorted([r for r in self.rs if r.get('anio') is not None], key=lambda r: r['anio'])
            if not rs:
                return
            anios = [r['anio'] for r in rs]
            a0 = min(anios); a1 = max(anios) + 1
            emp = self.emp or 0.001
            datamax = max((abs(r.get('resultado') or 0) + abs(r.get('incertidumbre') or 0) for r in rs), default=emp)
            raw = max(emp, datamax) * 1.2

            def nice(v):
                if v <= 0:
                    return 1.0
                e = math.floor(math.log10(v)); f = v / 10 ** e
                nf = 1 if f < 1.5 else 2 if f < 3 else 5 if f < 7 else 10
                return nf * 10 ** e
            step = nice(raw / 4.0)
            ymax = math.ceil(raw / step) * step

            px0, px1, py0, py1 = 20, w - 16, 12, h - 5
            def X(a):
                return px0 + (a - a0) / max(1, (a1 - a0)) * (px1 - px0)
            def Y(v):
                return (py0 + py1) / 2 + (v / ymax) * ((py1 - py0) / 2)

            c.setStrokeColor(LINEA); c.setLineWidth(0.5); c.rect(px0, py0, px1 - px0, py1 - py0, fill=0, stroke=1)
            # gridlines + etiquetas Y
            ticks, t = [], 0.0
            while t <= ymax + 1e-12:
                ticks.append(t); t += step
            for tv in sorted(set([-x for x in ticks] + ticks)):
                yy = Y(tv)
                c.setStrokeColor(colors.HexColor('#E2E2E2')); c.setLineWidth(0.3); c.line(px0, yy, px1, yy)
                c.setFillColor(colors.HexColor('#666666')); c.setFont('Helvetica', 3.6)
                c.drawRightString(px0 - 2, yy - 1.2, f'{tv:.3f}')
            # líneas EMP +/- (rojas, etiquetadas)
            c.setStrokeColor(colors.HexColor('#C00000')); c.setLineWidth(0.9)
            c.line(px0, Y(emp), px1, Y(emp)); c.line(px0, Y(-emp), px1, Y(-emp))
            c.setFillColor(colors.HexColor('#C00000')); c.setFont('Helvetica-Bold', 3.6)
            c.drawString(px1 + 1, Y(emp) - 1.2, 'EMP+'); c.drawString(px1 + 1, Y(-emp) - 1.2, 'EMP-')
            # serie azul + marcadores cuadrados + barras de incertidumbre
            azul = colors.HexColor('#2E75B6')
            pts = [(X(r['anio']), Y(r.get('resultado') or 0)) for r in rs]
            c.setStrokeColor(azul); c.setLineWidth(1)
            for i in range(1, len(pts)):
                c.line(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1])
            for r, (x, y) in zip(rs, pts):
                u = abs(r.get('incertidumbre') or 0)
                if u:
                    c.setStrokeColor(colors.black); c.setLineWidth(0.5)
                    c.line(x, Y((r.get('resultado') or 0) - u), x, Y((r.get('resultado') or 0) + u))
                    c.line(x - 1.6, Y((r.get('resultado') or 0) + u), x + 1.6, Y((r.get('resultado') or 0) + u))
                    c.line(x - 1.6, Y((r.get('resultado') or 0) - u), x + 1.6, Y((r.get('resultado') or 0) - u))
                c.setFillColor(azul); c.rect(x - 1.4, y - 1.4, 2.8, 2.8, fill=1, stroke=0)
            # años eje X (incluye un año más, como el Excel)
            c.setFillColor(colors.black); c.setFont('Helvetica', 3.8)
            for a in range(a0, a1 + 1):
                c.drawCentredString(X(a), py0 - 6, str(a))

    def tarjeta(p, cw):
        rs = p.get('resultados') or []
        cal = p.get('calculo') or {}
        deriv = {d['anio']: d['deriva'] for d in (cal.get('derivas') or [])}
        # banda título
        titulo = Table([[Paragraph(f'{equipo.codigo}  —  {p.get("valor_nominal", "")}', cabp)]],
                       colWidths=[cw], rowHeights=[5.6 * mm])
        titulo.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), BANDA), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        # tabla por año
        # Columnas del formato: año de calibración, resultados, incertidumbre,
        # EMP, desviación y tiempo hasta la siguiente calibración, y deriva.
        filas = [[Paragraph(x, th) for x in ['CALIBRA-<br/>CIÓN AÑO', 'RESULTA-<br/>DOS', 'INCERTI-<br/>DUMBRE', 'EMP',
                                             'DESVIA-<br/>CIÓN', 'TIEMPO<br/>(AÑO)', 'DERIVA']]]
        for i_, r in enumerate(rs):
            sig = rs[i_ + 1] if i_ + 1 < len(rs) else None
            desv = abs((sig.get('resultado') or 0) - (r.get('resultado') or 0)) if sig else None
            tiempo = (sig['anio'] - r['anio']) if sig else None
            d = deriv.get(r['anio'])
            filas.append([
                Paragraph(str(r['anio']), td), Paragraph(fnum(r.get('resultado')), td),
                Paragraph(fnum(r.get('incertidumbre')), td), Paragraph(fnum(r.get('emp')), td),
                Paragraph('' if desv is None else fnum(desv), td), Paragraph('' if tiempo is None else str(tiempo), td),
                Paragraph('---' if d is None else fnum(d), td),
            ])
        tabla = Table(filas, colWidths=[cw / 7.0] * 7)
        tabla.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, LINEA),
            ('BACKGROUND', (0, 0), (-1, 0), BANDA),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        # Resumen del formato: tolerancia y deriva máxima; periodo de calibración
        # (OIML D10, factores CENAM 0,2 y 0,7, PC = 0,5 × periodo) y periodo de
        # comprobación a partir del resultado de la última calibración (PV).
        per = cal.get('periodo')
        der = cal.get('deriva_maxima') or 0
        tol = cal.get('tolerancia') or 0
        ult_res = (rs[-1].get('resultado') or 0) if rs else 0
        per_c = ((tol - abs(ult_res)) / der) if der else None
        anios = lambda v: 'DERIVA 0' if v is None else f'{v:.2f} años'
        x = lambda f_, v: '---' if v is None else f'{f_ * v:.2f} años'
        res = Table([
            [Paragraph('EMP', tlbl), Paragraph(fnum(cal.get('emp')), tval), Paragraph('DERIVA MÁXIMA', tlbl), Paragraph(fnum(der), tval)],
            [Paragraph('Incert. Máxima (Umáx)', tlbl), Paragraph(fnum(cal.get('umax')), tval), '', ''],
            [Paragraph('Tolerancia = EMP - Umáx.', tlbl), Paragraph(fnum(tol), tval), '', ''],
            [Paragraph('Periodo de Calibración OIML D10', tlbl), Paragraph(anios(per), tval), Paragraph('CENAM 0,2 / 0,7', tlbl),
             Paragraph(f'{x(0.2, per)} / {x(0.7, per)}', tval)],
            [Paragraph('<b>PERIODO DE CALIBRACIÓN</b> OIML D10 · PC', tlbl), Paragraph(x(0.5, per), tval), '', ''],
            [Paragraph('Resultado Ult. Cal.', tlbl), Paragraph(fnum(ult_res), tval), '', ''],
            [Paragraph('Periodo de Calibración OIML D10', tlbl), Paragraph(anios(per_c), tval), Paragraph('CENAM 0,2 / 0,7', tlbl),
             Paragraph(f'{x(0.2, per_c)} / {x(0.7, per_c)}', tval)],
            [Paragraph('<b>PERIODO DE COMPROBACIÓN</b> OIML D10 · PV', tlbl), Paragraph(x(0.5, per_c), tval), '', ''],
        ], colWidths=[cw * 0.36, cw * 0.18, cw * 0.24, cw * 0.22])
        res.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, LINEA),
            ('SPAN', (2, 0), (2, 2)), ('SPAN', (3, 0), (3, 2)),
            ('SPAN', (1, 4), (3, 4)), ('SPAN', (1, 5), (3, 5)), ('SPAN', (1, 7), (3, 7)),
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#DCE6F1')), ('BACKGROUND', (0, 7), (-1, 7), colors.HexColor('#DCE6F1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        chart = _ChartIntervalo(cw, 130, rs, cal.get('emp'))
        celda = Table([[titulo], [tabla], [res], [chart]], colWidths=[cw])
        celda.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        return celda

    puntos = list(puntos or [])
    if not puntos:
        story.append(Paragraph('El patrón aún no tiene puntos nominales registrados.',
                               ParagraphStyle('invac', fontName='Helvetica', fontSize=10, alignment=TA_CENTER)))
        doc.build(story)
        return buf.getvalue()

    NCOL = 3
    g = 6
    cw = (W - g * (NCOL - 1)) / NCOL

    def fila_grid(cards):
        row = []
        for i in range(NCOL):
            row.append(cards[i] if i < len(cards) else '')
            if i < NCOL - 1:
                row.append('')   # columna separadora (gap real, sin relleno)
        return row

    grid = []
    fila = []
    for p in puntos:
        fila.append(tarjeta(p, cw))
        if len(fila) == NCOL:
            grid.append(fila_grid(fila)); fila = []
    if fila:
        grid.append(fila_grid(fila))

    colWidths = []
    for i in range(NCOL):
        colWidths.append(cw)
        if i < NCOL - 1:
            colWidths.append(g)
    outer = Table(grid, colWidths=colWidths)
    outer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(outer)
    doc.build(story)
    return buf.getvalue()


FUNCIONES_TEXTO_AUTORIZACION = {
    'ejecutar': 'Ejecutar las labores de calibración conforme a los procedimientos de calibración aplicables, la NTP-ISO/IEC 17025 y la Directriz de Acreditación DA-acr-06D.',
    'supervisar': 'Supervisar las calibraciones conforme al cronograma de actividades (orden de trabajo).',
    'informar': 'Informar los resultados de las calibraciones.',
    'revisar': 'Revisar y autorizar los resultados de las calibraciones previo a su emisión.',
    'analizar': 'Analizar los resultados y emitir opiniones e interpretaciones.',
    'firmar': 'Firmar los certificados de calibración.',
    'operar': 'Operar los equipos y manipular los ítems de calibración.',
}


# Funciones del formato de autorización, en su orden. La clave indica la
# función autorizada que habilita el literal; None = obligación general que el
# formato incluye siempre. {metodo} y {empresa} se completan al imprimir.
LITERALES_AUTORIZACION = [
    ('ejecutar', 'Ejecutar las labores de calibración bajo el estricto cumplimiento del {metodo}, la Norma NTP-ISO/IEC 17025 y de la Directriz de Acreditación DA-acr-06D.'),
    (None, 'Verificar la vigencia de los métodos de calibración periódicamente.'),
    (None, 'Cumplir la política y objetivos de la Calidad establecidos por {empresa}.'),
    (None, 'Realizar las calibraciones bajo las condiciones ambientales dadas por los Procedimientos Normados por el DM-INACAL.'),
    (None, 'Respetar las coordinaciones emitidas por el Responsable de Laboratorio.'),
    ('ejecutar', 'Ejecutar las calibraciones cumpliendo la fecha y hora conforme al cronograma de actividades (Orden de trabajo) de {empresa}.'),
    ('supervisar', 'Supervisar las calibraciones cumpliendo la fecha y hora conforme al cronograma de actividades (Orden de trabajo) de {empresa}.'),
    ('ejecutar', 'Después de realizar las calibraciones entregar las hojas de registro correctamente llenadas al Responsable de Laboratorio para obtener la firma de conformidad.'),
    ('supervisar', 'Después de realizar las calibraciones revisar las hojas de registro correctamente llenadas al Responsable de Laboratorio para obtener la firma de conformidad.'),
    ('informar', 'Informar los resultados de las calibraciones.'),
    ('analizar', 'Analizar los resultados y las opiniones e interpretaciones después de las calibraciones.'),
    ('revisar', 'Revisar y autorizar los resultados de las calibraciones previo a su emisión.'),
    ('firmar', 'Firmar los certificados de calibración realizados{alcance}.'),
    (None, 'Mantener el orden e higiene dentro del laboratorio, así como el buen funcionamiento de los equipos, patrones, reactivos y herramientas de trabajo.'),
    (None, 'Solicitar ante las instancias correspondientes el suministro de equipos patrones, herramientas y reactivos para las operaciones técnicas del laboratorio.'),
    (None, 'Suspender el desarrollo de la calibración por razones de seguridad e informar al Responsable de Laboratorio.'),
    (None, 'Aplicar los formatos vigentes para cumplir con el Sistema de Gestión de la Calidad.'),
    (None, 'Implementar, mejorar y mantener el buen desarrollo del trabajo de las calibraciones.'),
    (None, 'Apoyar en charlas para nuestros clientes y personal de nuestra empresa.'),
    (None, 'Recepcionar la queja emitida por el cliente, realizando el tratamiento correspondiente y evalúa junto con el responsable del área involucrada si procede o no procede la queja, de acuerdo a los procedimientos de quejas establecidos.'),
    ('operar', 'Operación de equipos y manipulación de ítems de ensayo.'),
    (None, 'Cumplir con las responsabilidades y funciones de acuerdo al Manual de Organización y Funciones.'),
]


def _ciudad_empresa(cfg):
    """Distrito o ciudad para la fecha de las cartas: el penúltimo tramo de la
    dirección configurada ("Av. X 123, El Agustino, Lima" → "El Agustino")."""
    partes = [x.strip() for x in (getattr(cfg, 'direccion', '') or '').split(',') if x.strip()] if cfg else []
    if len(partes) >= 3:
        return partes[-2]
    if len(partes) == 2:
        return partes[-1]
    return 'Lima'


def generar_autorizacion_pdf(aut) -> bytes:
    """Carta de autorización del personal con el texto del formato en Word:
    párrafo de otorgamiento, nombre centrado, funciones con literales a), b)…
    (las obligaciones generales y las funciones autorizadas), lugar y fecha a la
    derecha, firma del Gerente Técnico y pie de documento confidencial."""
    cfg = _cargar_cfg()
    margen_cab = 12 * mm
    Wc = A4[0] - 2 * margen_cab
    cabecera = _cabecera_met12(Wc, 'AUTORIZACIÓN DEL PERSONAL', 'MET-PRO-12-r02', cfg)
    _, alto_cab = cabecera.wrap(Wc, A4[1])

    def _pagina(canvas, doc_):
        canvas.saveState()
        cabecera.drawOn(canvas, margen_cab, A4[1] - 10 * mm - alto_cab)
        _pie_confidencial(canvas, doc_, cfg)
        canvas.restoreState()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=22 * mm, rightMargin=20 * mm,
                            topMargin=10 * mm + alto_cab + 5 * mm, bottomMargin=24 * mm, title='Autorización del Personal')
    from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
    cuerpo = ParagraphStyle('aucpo', fontName='Helvetica', fontSize=10, leading=15, alignment=TA_JUSTIFY)
    nombre_st = ParagraphStyle('aunom', fontName='Helvetica-Bold', fontSize=12, leading=16, alignment=TA_CENTER, spaceBefore=4, spaceAfter=4)
    item = ParagraphStyle('auitem', fontName='Helvetica', fontSize=9.6, leading=11.6, alignment=TA_JUSTIFY, leftIndent=14, bulletIndent=0)
    derecha = ParagraphStyle('auder', fontName='Helvetica', fontSize=10, leading=13, alignment=TA_RIGHT)
    firma_b = ParagraphStyle('aufb', fontName='Helvetica-Bold', fontSize=10, leading=13)
    firma_n = ParagraphStyle('aufn', fontName='Helvetica', fontSize=10, leading=13)

    def esc(t):
        return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    empresa = empresa_corta(cfg)
    gt = _nom_u(getattr(aut, 'autorizado_por', None))
    persona = _nom_u(getattr(aut, 'usuario', None))
    metodo = getattr(aut, 'metodo', None)
    if metodo:
        cod = (getattr(metodo, 'codigo', '') or '').strip()
        metodo_txt = f'{esc(cod)} “{esc(metodo.nombre)}”' if cod else f'procedimiento “{esc(metodo.nombre)}”'
    else:
        metodo_txt = 'procedimiento de calibración aplicable'
    alcance = ''
    if getattr(aut, 'alcance_firma', '') == 'todos':
        alcance = ' de todos los laboratorios'
    elif getattr(aut, 'alcance_firma', '') == 'laboratorio' and getattr(aut, 'laboratorio', ''):
        alcance = f' del laboratorio de {esc(aut.laboratorio)}'
    funciones = set(getattr(aut, 'funciones', None) or [])

    story = [
        Paragraph(f'En virtud a su competencia técnica, confiabilidad y destreza demostrada, la gerencia de <b>{esc(empresa)}</b> '
                  f'representado por {esc(gt) or "……………………"}, otorga la siguiente autorización al Sr(a):', cuerpo),
        Paragraph(esc(persona).upper(), nombre_st),
        Paragraph('Quien con independencia técnica y autoridad desempeñará las funciones que a continuación se detallan:', cuerpo),
        Spacer(1, 3),
    ]
    letra = 0
    for clave, texto in LITERALES_AUTORIZACION:
        if clave is not None and clave not in funciones:
            continue
        t = texto.format(metodo=metodo_txt, empresa=esc(empresa), alcance=alcance).replace('..', '.')
        story.append(Paragraph(t, item, bulletText=f'{chr(97 + letra)})'))
        letra += 1

    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'setiembre', 'octubre', 'noviembre', 'diciembre']
    fa = getattr(aut, 'fecha_autorizacion', None)
    fecha = f'{fa.day} de {meses[fa.month - 1]} del {fa.year}' if fa else ''
    story += [Spacer(1, 8), Paragraph(f'{esc(_ciudad_empresa(cfg))}, {fecha}', derecha), Spacer(1, 36)]
    firma = Table([[''], [Paragraph(esc(gt), firma_n)], [Paragraph('GERENTE TÉCNICO', firma_b)]],
                  colWidths=[60 * mm], rowHeights=[4, None, None], hAlign='LEFT')
    firma.setStyle(TableStyle([('LINEABOVE', (0, 0), (0, 0), 0.6, colors.black),
                               ('LEFTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    from reportlab.platypus import KeepTogether
    story.append(KeepTogether([firma]))
    doc.build(story, onFirstPage=_pagina, onLaterPages=_pagina)
    return buf.getvalue()


def _cabecera_met12(W, titulo, codigo, cfg):
    """Encabezado de control estándar (logo + título + caja código/versión/fecha/firmas)."""
    minic = ParagraphStyle('m12minic', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_CENTER)
    minibc = ParagraphStyle('m12minibc', fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=TA_CENTER)
    tit = ParagraphStyle('m12tit', fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=TA_CENTER)
    empresa = ''
    try:
        empresa = empresa_nombre(cfg, vacio='')
    except Exception:
        pass
    # Código, versión, fecha y siglas: de la lista maestra si el formato está
    # vinculado; si no, de la tabla de respaldo o de Configuración.
    _c = control_formato(codigo, cfg)
    codigo, version_s, fecha_s = _c['codigo'], _c['version'], _c['fecha']
    elaborado_s, revisado_s, aprobado_s = _c['elaborado'], _c['revisado'], _c['aprobado']
    logo_cell = Paragraph(empresa or 'EMPRESA', ParagraphStyle('m12logo', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER))
    try:
        _logo = (getattr(cfg, 'logo_empresa', None) or getattr(cfg, 'logo', None)) if cfg else None
        if _logo and _logo.path:
            im = Image(_logo.path)
            r = min((W * 0.16) / im.imageWidth, (20 * mm) / im.imageHeight)
            im.drawWidth = im.imageWidth * r; im.drawHeight = im.imageHeight * r; im.hAlign = 'CENTER'
            logo_cell = im
    except Exception:
        pass
    c6 = W * 0.24 / 6.0
    data = [
        [logo_cell, Paragraph(titulo, tit), Paragraph('Código:', minibc), '', '', Paragraph(codigo, minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(version_s, minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(fecha_s, minic), '', ''],
        ['', '', Paragraph('Elaborado', minibc), '', Paragraph('Revisado', minibc), '', Paragraph('Aprobado', minibc), ''],
        ['', '', Paragraph(elaborado_s, minic), '', Paragraph(revisado_s, minic), '', Paragraph(aprobado_s, minic), ''],
    ]
    hdr = Table(data, colWidths=[W * 0.18, W * 0.58, c6, c6, c6, c6, c6, c6], rowHeights=[4.6 * mm] * 5)
    hdr.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('SPAN', (0, 0), (0, 4)), ('SPAN', (1, 0), (1, 4)),
        ('SPAN', (2, 0), (4, 0)), ('SPAN', (5, 0), (7, 0)),
        ('SPAN', (2, 1), (4, 1)), ('SPAN', (5, 1), (7, 1)),
        ('SPAN', (2, 2), (4, 2)), ('SPAN', (5, 2), (7, 2)),
        ('SPAN', (2, 3), (3, 3)), ('SPAN', (4, 3), (5, 3)), ('SPAN', (6, 3), (7, 3)),
        ('SPAN', (2, 4), (3, 4)), ('SPAN', (4, 4), (5, 4)), ('SPAN', (6, 4), (7, 4)),
        ('ALIGN', (0, 0), (0, 4), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    return hdr


def _cargar_cfg():
    try:
        from core.models import ConfiguracionSistema
        return ConfiguracionSistema.cargar()
    except Exception:
        return None


def _fila_dato(W, etiqueta, valor):
    lblw = ParagraphStyle('m12lblw', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white)
    valc = ParagraphStyle('m12valc', fontName='Helvetica', fontSize=8.5, leading=11)
    t = Table([[Paragraph(etiqueta, lblw), Paragraph(str(valor or ''), valc)]],
              colWidths=[W * 0.28, W * 0.72])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, LINEA), ('BACKGROUND', (0, 0), (0, 0), BANDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t


def _nom_u(u):
    return (u.get_full_name() or u.username) if u else ''


def _grilla(W, anchos):
    """Ayudantes para replicar una hoja de Excel: `ancho('B', 'F')` da el ancho
    de un rango de columnas y `fila([...])` arma una fila con celdas que ocupan
    rangos de columnas (las columnas omitidas quedan en blanco, sin borde)."""
    tot = float(sum(anchos))

    def ancho(c1, c2):
        return W * sum(anchos[_col_idx(c1):_col_idx(c2) + 1]) / tot

    def fila(celdas, alto=None, fondo=None, borde=True, pad=2):
        """celdas: (col_ini, col_fin, contenido[, color_de_fondo])."""
        cols, data, est = [], [], []
        pos = 0
        for cel in celdas:
            c1, c2, cont = cel[0], cel[1], cel[2]
            color = cel[3] if len(cel) > 3 else None
            ini = _col_idx(c1)
            if ini > pos:
                cols.append(W * sum(anchos[pos:ini]) / tot); data.append('')
            cols.append(ancho(c1, c2)); data.append(cont)
            n = len(data) - 1
            if borde:
                est.append(('BOX', (n, 0), (n, 0), 0.5, colors.black))
            if color is not None:
                est.append(('BACKGROUND', (n, 0), (n, 0), color))
            pos = _col_idx(c2) + 1
        if pos < len(anchos):
            cols.append(W * sum(anchos[pos:]) / tot); data.append('')
        t = Table([data], colWidths=cols, rowHeights=[alto])
        t.setStyle(TableStyle(est + [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                     ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                                     ('LEFTPADDING', (0, 0), (-1, -1), pad), ('RIGHTPADDING', (0, 0), (-1, -1), pad)]))
        return t
    return ancho, fila


_CONFORMIDAD_LBL = {'conforme': 'Conforme', 'no_conforme': 'No conforme', 'no conforme': 'No conforme', 'na': 'N/A'}


def generar_entrenamiento_pdf(proc) -> bytes:
    """Entrenamiento y supervisión de actividades con la grilla del formato en
    Excel: nombre, cargo y casillas Entrenamiento / Re-entrenamiento; hoja 1 con
    el entrenamiento (10 actividades) y hoja 2 con el trabajo bajo supervisión
    (15 ítems) y los comentarios."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=8 * mm, bottomMargin=10 * mm, title='Entrenamiento y Supervisión')
    W = doc.width
    cfg = _cargar_cfg()
    azul = colors.HexColor('#16365C')
    ancho, fila = _grilla(W, [5.71] * 18)                  # columnas A..R
    f = 7
    lbl = ParagraphStyle('e1lbl', fontName='Helvetica-Bold', fontSize=f, leading=f * 1.2, alignment=TA_CENTER)
    lbli = ParagraphStyle('e1lbli', parent=lbl, alignment=TA_LEFT)
    banda = ParagraphStyle('e1band', fontName='Helvetica-Bold', fontSize=f, leading=f * 1.2, textColor=colors.white)
    val = ParagraphStyle('e1val', fontName='Helvetica', fontSize=f + 0.5, leading=(f + 0.5) * 1.2)
    valc = ParagraphStyle('e1valc', parent=val, alignment=TA_CENTER)
    nota = ParagraphStyle('e1nota', fontName='Helvetica-Bold', fontSize=f - 0.6, leading=f, alignment=TA_CENTER)
    notai = ParagraphStyle('e1notai', parent=nota, alignment=TA_LEFT)

    def esc(t):
        return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def tabla(filas_, anchos_, alturas, estilos):
        t = Table(filas_, colWidths=anchos_, rowHeights=alturas)
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                               ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                               ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3)] + estilos))
        return t

    def marco(contenido):
        """Recuadro de la sección (de la franja azul al final de la sección)."""
        m = Table([[contenido]], colWidths=[W])
        m.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                               ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
        return m

    usuario = getattr(proc, 'usuario', None)
    reentrena = getattr(proc, 'tipo', '') == 'reentrenamiento'
    X = lambda c: Paragraph('X' if c else '', valc)
    story = [_cabecera_met12(W, 'ENTRENAMIENTO Y SUPERVISIÓN DE ACTIVIDADES', 'MET-PRO-12-r01', cfg), Spacer(1, 6)]
    story += [fila([('B', 'F', Paragraph('Nombre del Colaborador:', lbl)), ('G', 'Q', Paragraph(esc(_nom_u(usuario)), val))], alto=15),
              Spacer(1, 6),
              fila([('B', 'F', Paragraph('Cargo:', lbl)), ('G', 'J', Paragraph(esc(getattr(usuario, 'cargo', '')), val)),
                    ('M', 'N', X(not reentrena)), ('O', 'Q', Paragraph('ENTRENAMIENTO', lbl))], alto=15),
              Spacer(1, 6),
              fila([('M', 'N', X(reentrena)), ('O', 'Q', Paragraph('RE-ENTRENAMIENTO', lbl))], alto=15),
              Spacer(1, 8)]

    # 1. Entrenamiento / re-entrenamiento
    cont1 = [fila([('A', 'R', Paragraph('1. ENTRENAMIENTO / RE-ENTRENAMIENTO', banda), azul)], alto=15, borde=False), Spacer(1, 6),
             fila([('B', 'F', Paragraph('Tutor Asignado:', lbl)), ('G', 'Q', Paragraph(esc(_nom_u(getattr(proc, 'tutor', None))), val))], alto=15),
             Spacer(1, 6)]
    acts = [x for x in (getattr(proc, 'checklist_entrenamiento', None) or []) if isinstance(x, dict)]
    filas = [[Paragraph('ACTIVIDAD', lbl), Paragraph('DOCUMENTO', lbl), Paragraph('FECHA INICIO', lbl), Paragraph('CONFORMIDAD', lbl)]]
    for n in range(max(10, len(acts))):
        it = acts[n] if n < len(acts) else {}
        filas.append([Paragraph(esc(it.get('actividad', '')), val), Paragraph(esc(it.get('documento', '')), val),
                      Paragraph(esc(it.get('fecha_inicio', '')), valc),
                      Paragraph(_CONFORMIDAD_LBL.get(str(it.get('conformidad', '')).lower(), esc(it.get('conformidad', ''))), valc)])
    filas.append([Paragraph('Nota: Para superar con éxito el entrenamiento todos los ítems deben ser conformes.', nota), '', '', ''])
    cw1 = [ancho('B', 'E'), ancho('F', 'K'), ancho('L', 'N'), ancho('O', 'Q')]
    t1 = tabla(filas, cw1, [15] + [17] * (len(filas) - 2) + [16], [('SPAN', (0, len(filas) - 1), (3, len(filas) - 1))])
    cont1.append(Table([['', t1, '']], colWidths=[ancho('A', 'A'), sum(cw1), ancho('R', 'R')],
                       style=TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])))
    story.append(marco(cont1))

    # 2. Trabajo bajo supervisión (hoja 2, como el formato)
    story.append(PageBreak())
    fi = getattr(proc, 'fecha_inicio_supervision', None)
    cont2 = [fila([('A', 'R', Paragraph('2. TRABAJO BAJO SUPERVISIÓN', banda), azul)], alto=15, borde=False), Spacer(1, 6),
             fila([('B', 'F', Paragraph('Tutor Asignado:', lbl)),
                   ('G', 'Q', Paragraph(esc(_nom_u(getattr(proc, 'tutor_supervision', None) or getattr(proc, 'tutor', None))), val))], alto=15),
             Spacer(1, 8),
             fila([('B', 'F', Paragraph('Periodo de Trabajo Bajo Supervisión (días)', lbl)),
                   ('G', 'J', Paragraph(esc(getattr(proc, 'periodo_supervision_dias', '') or ''), valc)),
                   ('L', 'N', Paragraph('Fecha Inicio:', lbl)), ('O', 'Q', Paragraph(_f(fi), valc))], alto=18),
             Spacer(1, 8)]
    sup = [x for x in (getattr(proc, 'checklist_supervision', None) or []) if isinstance(x, dict)]
    filas = [[Paragraph('El personal demuestra habilidad o conocimiento en:', lbl), Paragraph('Conformidad', lbl)]]
    for n in range(max(15, len(sup))):
        it = sup[n] if n < len(sup) else {}
        filas.append([Paragraph(esc(it.get('item', '') or it.get('actividad', '')), val),
                      Paragraph(_CONFORMIDAD_LBL.get(str(it.get('conformidad', '')).lower(), esc(it.get('conformidad', ''))), valc)])
    filas.append([Paragraph('Nota: Para superar con éxito la evaluación todos los ítems deben ser conformes.', notai), ''])
    cont2.append(tabla(filas, [ancho('A', 'N'), ancho('O', 'R')], [26] + [17] * (len(filas) - 2) + [16],
                       [('SPAN', (0, len(filas) - 1), (1, len(filas) - 1))]))
    story.append(marco(cont2))
    story += [Spacer(1, 8),
              Table([['']], colWidths=[W], rowHeights=[2], style=TableStyle([('LINEABOVE', (0, 0), (-1, -1), 0.6, colors.black)])),
              fila([('A', 'E', Paragraph('COMENTARIOS:', lbl)), ('F', 'R', Paragraph(esc(getattr(proc, 'comentarios', '')), val))], alto=26)]
    doc.build(story)
    return buf.getvalue()


def generar_seguimiento_pdf(seg) -> bytes:
    """Entrevista de seguimiento al personal con la grilla del formato en Excel
    (columnas A a P, horizontal): responsable, tema y entrevistado; fecha, hora y
    área; tabla de desarrollo con 5 filas de preguntas y los resultados en
    celdas combinadas; puntaje por pregunta, N° de preguntas, conclusiones y
    observaciones con sus recuadros."""
    from reportlab.lib.pagesizes import landscape
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=8 * mm, bottomMargin=8 * mm, title='Entrevista de Seguimiento')
    W = doc.width
    cfg = _cargar_cfg()
    azul = colors.HexColor('#16365C')
    anchos = [11.43] * 4 + [13.86] + [11.43] * 11              # columnas A..P
    ancho, fila = _grilla(W, anchos)
    k = 0.72
    rh = lambda pt: pt * k
    f = 7
    lbl = ParagraphStyle('r3lbl', fontName='Helvetica-Bold', fontSize=f, leading=f * 1.2, textColor=colors.white, alignment=TA_CENTER)
    banda = ParagraphStyle('r3band', parent=lbl, alignment=TA_LEFT)
    val = ParagraphStyle('r3val', fontName='Helvetica', fontSize=f + 0.6, leading=(f + 0.6) * 1.25)
    valc = ParagraphStyle('r3valc', parent=val, alignment=TA_CENTER)
    RES = {'satisfactorio': 'Satisfactorio', 'no_satisfactorio': 'No satisfactorio'}
    DEC = {'mantener': 'Mantener', 'suspender': 'Suspender', 'reautorizar': 'Reautorizar'}

    def esc(t):
        return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')

    def fn(v):
        return '' if v is None or v == '' else (f'{v:g}' if isinstance(v, (int, float)) else str(v))

    sep = lambda: Spacer(1, rh(18.75) * 0.5)
    story = [_cabecera_met12(W, 'ENTREVISTA DE SEGUIMIENTO AL PERSONAL', 'MET-PRO-12-r03', cfg), sep()]
    for rot, v in (('Responsable de la Entrevista:', _nom_u(getattr(seg, 'evaluador', None))),
                   ('Tema de la Entrevista', getattr(seg, 'tema', '')),
                   ('Personal(es) Entrevistado(s)', _nom_u(getattr(seg, 'usuario', None)))):
        story += [fila([('D', 'F', Paragraph(rot, lbl), azul), ('G', 'M', Paragraph(esc(v), val))], alto=rh(18.75)), sep()]
    story += [fila([('B', 'C', Paragraph('Fecha', lbl), azul), ('D', 'E', Paragraph(_f(getattr(seg, 'fecha', None)), valc)),
                    ('G', 'H', Paragraph('Hora', lbl), azul), ('I', 'J', Paragraph(_hora_ampm(getattr(seg, 'hora', '')), valc)),
                    ('L', 'M', Paragraph('Área', lbl), azul), ('N', 'O', Paragraph(esc(getattr(seg, 'area', '')), valc))], alto=rh(18.75)),
              sep(), fila([('A', 'P', Paragraph('I. DESARROLLO', banda), azul)], alto=rh(18.75), borde=False), sep()]

    preg = [x for x in (getattr(seg, 'preguntas', None) or []) if isinstance(x, dict)]
    n_filas = max(5, len(preg))
    cw = [ancho('A', 'D'), ancho('E', 'E'), ancho('F', 'F'), ancho('G', 'H'), ancho('I', 'J'), ancho('K', 'L'), ancho('M', 'N'), ancho('O', 'P')]
    lbl_s = ParagraphStyle('r3lbls', parent=lbl, fontSize=f - 1, leading=(f - 1) * 1.15)
    filas = [[Paragraph(x, lbl_s if 'BR' in x.upper() else lbl) for x in ('N°', 'PUNTAJE<br/>ESTABLECIDO', 'PUNTAJE<br/>OBTENIDO', 'PUNTAJE TOTAL',
                                                                           'PUNTAJE MÍNIMO', 'PUNTAJE MÁXIMO', 'RESULTADO', 'DECISIÓN')]]
    for n in range(n_filas):
        q = preg[n] if n < len(preg) else {}
        fila_q = [Paragraph(fn(q.get('n', '')), valc), Paragraph(fn(q.get('establecido', '')), valc), Paragraph(fn(q.get('obtenido', '')), valc)]
        if n == 0:
            fila_q += [Paragraph(fn(getattr(seg, 'puntaje_total', None) if getattr(seg, 'puntaje_obtenido', None) is None else getattr(seg, 'puntaje_obtenido')), valc),
                       Paragraph(fn(getattr(seg, 'puntaje_minimo', None)), valc), Paragraph(fn(getattr(seg, 'puntaje_maximo', None)), valc),
                       Paragraph(RES.get(getattr(seg, 'resultado', ''), ''), valc), Paragraph(DEC.get(getattr(seg, 'decision', ''), ''), valc)]
        else:
            fila_q += [''] * 5
        filas.append(fila_q)
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), azul), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('LEFTPADDING', (1, 0), (2, 0), 1), ('RIGHTPADDING', (1, 0), (2, 0), 1)]
    for c in range(3, 8):
        est.append(('SPAN', (c, 1), (c, n_filas)))
    t = Table(filas, colWidths=cw, rowHeights=[rh(37.5)] * (n_filas + 1))
    t.setStyle(TableStyle(est))
    story += [t, sep(),
              fila([('D', 'E', Paragraph('PUNTAJE POR PREGUNTA', lbl), azul), ('F', 'G', Paragraph(fn(getattr(seg, 'puntaje_por_pregunta', None)), valc)),
                    ('J', 'K', Paragraph('N° DE PREGUNTAS', lbl), azul), ('L', 'M', Paragraph(fn(getattr(seg, 'n_preguntas', None) or (len(preg) or '')), valc))],
                   alto=rh(18.75)), sep()]
    for rot, texto in (('II. CONCLUSIONES', getattr(seg, 'conclusiones', '')),
                       ('III. OBSERVACIONES Y/O RECOMENDACIONES', getattr(seg, 'observaciones', ''))):
        story += [fila([('A', 'P', Paragraph(rot, banda), azul)], alto=rh(18.75), borde=False), sep()]
        p_ = Paragraph(esc(texto), val)
        caja = Table([[p_]], colWidths=[W])
        _, h_ = p_.wrap(W - 6, 1000)
        caja._argH[0] = max(rh(37.5), h_ + 6)
        caja.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story += [caja, sep()]
    doc.build(story)
    return buf.getvalue()


COD_PROGRAMA_ANUAL = 'SIG-PRO-16-r01'
COD_PLAN_AUDITORIA = 'SIG-PRO-16-r02'
COD_ACTA_APERTURA = 'SIG-PRO-16-r03'
COD_INFORME_AUD = 'SIG-PRO-16-r04'
COD_ACTA_CIERRE = 'SIG-PRO-16-r05'
COD_LISTA_VERIF_17025 = 'SIG-PRO-16-r06'
COD_LISTA_VERIF_SIG = 'SIG-PRO-16-r07'
COD_SAC = 'SIG-PRO-11-r01'
COD_SEGUIMIENTO_SAC = 'SIG-PRO-11-r02'

# Control de cada formato tal como figura en su plantilla (encabezado):
# versión, fecha y siglas de elaborado / revisado / aprobado. Si un formato
# no está aquí, la cabecera usa los valores globales y las siglas de Configuración.
CONTROL_FORMATOS = {
    'SIG-PRO-16-r01': ('02', '2026-01-12', 'ASIG', 'GSIG/GT', 'GG'),
    'SIG-PRO-16-r02': ('01', '2026-01-12', 'ASIG', 'GSIG/GT', 'GG'),
    'SIG-PRO-16-r03': ('00', '2025-01-10', 'ASIG', 'GSIG', 'GG'),
    'SIG-PRO-16-r04': ('00', '2025-01-10', 'ASIG', 'GSIG', 'GG'),
    'SIG-PRO-16-r05': ('00', '2025-01-10', 'ASIG', 'GSIG', 'GG'),
    'SIG-PRO-16-r06': ('00', '2026-01-12', 'ASIG', 'GSIG/GT', 'GG'),
    'SIG-PRO-16-r07': ('00', '2026-01-12', 'ASIG', 'GSIG/GT', 'GG'),
    'MET-PRO-12-r01': ('00', '2026-02-11', 'ASIG', 'GSIG/GT', 'GG'),
    'MET-PRO-12-r02': ('00', '2026-02-11', 'ASIG', 'GSIG/GT', 'GG'),
    'MET-PRO-12-r03': ('00', '2026-02-11', 'ASIG', 'GSIG/GT', 'GG'),
    'SIG-PRO-11-r01': ('01', '2026-02-13', 'ASIG', 'GSIG/GT', 'GG'),
    'SIG-PRO-11-r02': ('00', '2025-12-19', 'ASIG', 'GSIG/GT', 'GG'),
}


def control_formato(codigo, cfg=None):
    """
    Datos de la caja de control de un formato impreso: código, versión, fecha
    y siglas de elaboró / revisó / aprobó.

    Fuente, en orden de prioridad:
    1. La **lista maestra (M6)**: si el formato está vinculado a un documento con
       versión vigente, se toman su código, número de versión, fecha de vigencia
       (o de aprobación) y las siglas de cargo de quien elaboró, revisó y aprobó
       esa versión. Es la fuente única: al aprobar una nueva versión en M6, todos
       los PDF la imprimen.
    2. La tabla de respaldo CONTROL_FORMATOS (valores leídos de las plantillas).
    3. Los valores globales y las siglas de Configuración.
    """
    version, fecha = VERSION_FORMATO, FECHA_FORMATO
    elab = (getattr(cfg, 'formato_hv_elaborado', '') if cfg else '') or FIRMAS[0][1]
    rev = (getattr(cfg, 'formato_hv_revisado', '') if cfg else '') or FIRMAS[1][1]
    apr = (getattr(cfg, 'formato_hv_aprobado', '') if cfg else '') or FIRMAS[2][1]
    origen = 'global'
    if codigo in CONTROL_FORMATOS:
        version, fecha, elab, rev, apr = CONTROL_FORMATOS[codigo]
        origen = 'tabla'
    try:
        from .models import FormatoImpreso
        fi = (FormatoImpreso.objects.filter(codigo_sgc=codigo, is_active=True)
              .select_related('documento').first())
        doc = fi.documento if fi else None
        vv = doc.version_vigente if (doc and doc.is_active) else None
        if vv:
            codigo = doc.codigo
            version = vv.version or version
            f = vv.fecha_vigencia or vv.fecha_aprobacion
            if f:
                fecha = f.date().isoformat() if hasattr(f, 'date') else f.isoformat()

            def sigla(u, respaldo):
                return (getattr(u, 'sigla_cargo', '') or '').strip() or respaldo
            elab = sigla(vv.elaborado_por, elab)
            rev = sigla(vv.revisado_por, rev)
            apr = sigla(vv.aprobado_por, apr)
            origen = 'lista_maestra'
    except Exception:
        # Sin tabla aún (migración pendiente) o sin base de datos: respaldo.
        pass
    return {'codigo': codigo, 'version': version, 'fecha': fecha,
            'elaborado': elab, 'revisado': rev, 'aprobado': apr, 'origen': origen}

_NORMAS_LBL = {
    'iso_9001': 'ISO 9001', 'iso_14001': 'ISO 14001',
    'iso_45001': 'ISO 45001 / Ley 29783', 'iso_17025': 'NTP ISO/IEC 17025',
    'sig_integrado': 'ISO 9001:2015, ISO 14001:2015 e ISO 45001:2018',
}
_ESTADOS_AUD_LBL = {
    'programada': 'Programada', 'planificada': 'Planificada', 'apertura': 'Reunión de apertura',
    'en_ejecucion': 'En ejecución', 'conclusiones': 'Conclusiones', 'reunion_cierre': 'Reunión de cierre',
    'en_informe': 'En informe', 'cerrada': 'Cerrada',
}
# Colores semánticos de estado (regla 10): gris inicial · ámbar revisión ·
# azul en proceso · violeta verificación · verde cerrado · rojo rechazado.
_ESTADO_COLOR = {
    'programada': colors.HexColor('#E5E7EB'), 'planificada': colors.HexColor('#FDE8C8'),
    'apertura': colors.HexColor('#D6E4F7'), 'en_ejecucion': colors.HexColor('#D6E4F7'),
    'conclusiones': colors.HexColor('#D6E4F7'), 'reunion_cierre': colors.HexColor('#D6E4F7'),
    'en_informe': colors.HexColor('#E7DAF7'),
    'cerrada': colors.HexColor('#D6EFD8'),
    'borrador': colors.HexColor('#E5E7EB'), 'aprobado': colors.HexColor('#D6EFD8'),
}
_TIPOS_HALLAZGO_LBL = {
    'nc_mayor': 'No conformidad mayor', 'nc_menor': 'No conformidad menor',
    'observacion': 'Observación', 'odm': 'Oportunidad de mejora',
}
# Conclusión impresa en la columna "C / NC / OBS / NA" del formato; sin evaluar
# queda en blanco, como en el formato vacío.
_RESULTADOS_ITEM_LBL = {
    'pendiente': '', 'cumple': 'C', 'no_cumple': 'NC',
    'na': 'NA', 'observa': 'OBS',
}
_MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']


def _bloque_texto(W, titulo, texto, band_style, cuerpo_style):
    """Banda de sección + un párrafo de cuerpo (para objetivo, alcance, etc.)."""
    out = [_banda(titulo, W, band_style), Spacer(1, 2),
           Paragraph((str(texto).strip() if texto else '—').replace('\n', '<br/>'), cuerpo_style),
           Spacer(1, 6)]
    return out


def _tabla_equipo(W, auditoria, th, td):
    """Tabla del equipo auditor (rol, nombre, cargo)."""
    ROLES = {'lider': 'Auditor líder', 'auditor': 'Auditor', 'experto': 'Experto técnico', 'observador': 'Observador'}
    filas = [[Paragraph('ROL', th), Paragraph('NOMBRE', th), Paragraph('CARGO', th)]]
    integrantes = list(getattr(auditoria, 'equipo').all()) if hasattr(auditoria, 'equipo') else []
    if not integrantes:
        filas.append([Paragraph('—', td), Paragraph('—', td), Paragraph('—', td)])
    for ig in integrantes:
        nombre = _nom_u(getattr(ig, 'usuario', None)) or getattr(ig, 'nombre_externo', '') or '—'
        filas.append([Paragraph(ROLES.get(getattr(ig, 'rol', ''), getattr(ig, 'rol', '')), td),
                      Paragraph(nombre, td), Paragraph(getattr(ig, 'cargo', '') or '', td)])
    t = Table(filas, colWidths=[W * 0.25, W * 0.45, W * 0.30])
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, LINEA), ('BACKGROUND', (0, 0), (-1, 0), BANDA),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t


def _fila_estado(W, etiqueta, clave, label_map):
    """Fila etiqueta/valor con el valor coloreado según su estado (regla 10)."""
    lblw = ParagraphStyle('audlbl', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white)
    valc = ParagraphStyle('audval', fontName='Helvetica-Bold', fontSize=8.5, leading=11)
    t = Table([[Paragraph(etiqueta, lblw), Paragraph(label_map.get(clave, clave or ''), valc)]],
              colWidths=[W * 0.28, W * 0.72])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, LINEA), ('BACKGROUND', (0, 0), (0, 0), BANDA),
        ('BACKGROUND', (1, 0), (1, 0), _ESTADO_COLOR.get(clave, colors.white)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t


def _sublabel(W, texto):
    """Franja clara con etiqueta (subcampo dentro de una sección numerada)."""
    st = ParagraphStyle('audsub', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#1E3A5C'))
    t = Table([[Paragraph(texto, st)]], colWidths=[W])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EEF2F7')),
                           ('BOX', (0, 0), (-1, -1), 0.4, LINEA),
                           ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                           ('LEFTPADDING', (0, 0), (-1, -1), 4)]))
    return t


def _campo(W, etiqueta, valor, cuerpo):
    """Subcampo: etiqueta en franja clara + valor en párrafo."""
    out = [_sublabel(W, etiqueta)]
    txt = (str(valor).strip() if valor else '—').replace('\n', '<br/>')
    out.append(Paragraph(txt, cuerpo))
    out.append(Spacer(1, 3))
    return out


def _equipo_por_rol(a, rol):
    """Nombres (coma-separados) del equipo auditor con ese rol."""
    if not (a and hasattr(a, 'equipo')):
        return ''
    nombres = []
    for ig in a.equipo.all():
        if getattr(ig, 'rol', '') == rol:
            nombres.append(_nom_u(getattr(ig, 'usuario', None)) or getattr(ig, 'nombre_externo', '') or '')
    return ', '.join([n for n in nombres if n])


def _xml(t):
    """Texto seguro para Paragraph (escapa &, < y >)."""
    return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _nombre_lider(a):
    """Auditor líder tal como figura en el equipo auditor (única fuente)."""
    if not a:
        return ''
    if hasattr(a, 'nombre_lider'):
        return a.nombre_lider()
    return _equipo_por_rol(a, 'lider') or _nom_u(getattr(a, 'auditor_lider', None))


def _tipo_marcado(W, modalidad, lblw, td):
    """Fila 'Tipo de auditoría' con In Situ / Remoto / Híbrido marcando la opción."""
    def marca(clave):
        return 'X' if modalidad == clave else ''
    t = Table([[Paragraph('Tipo de auditoría:', lblw),
                Paragraph('In Situ', td), Paragraph(marca('presencial'), td),
                Paragraph('Remoto', td), Paragraph(marca('remota'), td),
                Paragraph('Híbrido', td), Paragraph(marca('hibrido'), td)]],
              colWidths=[W * 0.28, W * 0.12, W * 0.06, W * 0.12, W * 0.06, W * 0.12, W * 0.24])
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, LINEA), ('BACKGROUND', (0, 0), (0, 0), BANDA),
                           ('ALIGN', (2, 0), (2, 0), 'CENTER'), ('ALIGN', (4, 0), (4, 0), 'CENTER'), ('ALIGN', (6, 0), (6, 0), 'CENTER'),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t


def _col_idx(letra):
    n = 0
    for ch in letra:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def generar_plan_auditoria_pdf(a) -> bytes:
    """Plan de auditoría interna con la grilla del formato en Excel (columnas
    A a AU): datos del laboratorio, características con casillas de normas y de
    tipo de auditoría, equipo auditor, cronograma (una fila por entrevista
    registrada), observaciones y firma del auditor líder."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=8 * mm, bottomMargin=8 * mm, title='Plan de auditoría')
    W = doc.width
    cfg = _cargar_cfg()
    azul = colors.HexColor('#16365C')
    # Anchos de las columnas A..AU del Excel
    anchos = [3.86] * 47
    tot = float(sum(anchos))
    def ancho(c1, c2):
        return W * sum(anchos[_col_idx(c1):_col_idx(c2) + 1]) / tot
    k = 0.5                        # escala de alturas y letras del Excel al imprimirse en A4
    rh = lambda pt: pt * k
    f = 6.4                        # letra del Excel (11) a la escala de impresión
    lbl = ParagraphStyle('pllbl', fontName='Helvetica-Bold', fontSize=f, leading=f * 1.15, textColor=colors.white)
    lblc = ParagraphStyle('pllblc', parent=lbl, alignment=TA_CENTER)
    lbls = ParagraphStyle('pllbls', parent=lblc, fontSize=f - 0.9, leading=(f - 0.9) * 1.15)
    val = ParagraphStyle('plval', fontName='Helvetica', fontSize=f + 0.4, leading=(f + 0.4) * 1.2)
    valc = ParagraphStyle('plvalc', parent=val, alignment=TA_CENTER)
    marca = ParagraphStyle('plx', fontName='Helvetica-Bold', fontSize=f + 1, leading=f * 1.3, alignment=TA_CENTER)

    def esc(t):
        return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')

    def fila(celdas, alto=18.75, grilla=True):
        """celdas: (col_inicio, col_fin, contenido, fondo_azul). Las columnas no
        listadas quedan como espacio en blanco sin borde."""
        cols, data, est = [], [], []
        pos = 0
        for c1, c2, cont, azulado in celdas:
            ini = _col_idx(c1)
            if ini > pos:
                cols.append(W * sum(anchos[pos:ini]) / tot); data.append('')
            cols.append(ancho(c1, c2)); data.append(cont)
            n = len(data) - 1
            if grilla:
                est.append(('BOX', (n, 0), (n, 0), 0.5, colors.black))
            if azulado:
                est.append(('BACKGROUND', (n, 0), (n, 0), azul))
            pos = _col_idx(c2) + 1
        if pos < len(anchos):
            cols.append(W * sum(anchos[pos:]) / tot); data.append('')
        t = Table([data], colWidths=cols, rowHeights=[rh(alto) if alto else None])
        t.setStyle(TableStyle(est + [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                     ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                                     ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2)]))
        return t

    def sep():
        return Spacer(1, rh(7.5))

    def banda(texto):
        return fila([('A', 'AU', Paragraph(texto, lblc), True)])

    def campo(c_lbl, c_ini, texto, filas=1, centrado=False):
        """Rótulo azul + valor; el alto mínimo es el de las filas del Excel."""
        p = Paragraph(esc(texto), valc if centrado else val)
        t = fila([('A', c_lbl, Paragraph(lbl_txt[0], lbl), True), (c_ini, 'AU', p, False)], alto=None)
        _, h = p.wrap(ancho(c_ini, 'AU') - 4, 1000)
        t._argH[0] = max(rh(18.75) * filas, h + 3)
        return t

    import datetime as _dt
    fecha_elab = getattr(a, 'fecha_elaboracion_plan', None) or _dt.date.today()
    normas_cod = set()
    for n in (getattr(a, 'normas_aplicables', None) or []):
        normas_cod.update(['iso_9001', 'iso_14001', 'iso_45001'] if n == 'sig_integrado' else [n])
    X = lambda cond: Paragraph('X' if cond else '', marca)
    modalidad = getattr(a, 'modalidad', '') or ''

    story = [_cabecera_met12(W, 'PLAN DE AUDITORÍA INTERNA', COD_PLAN_AUDITORIA, cfg), sep()]
    story.append(fila([('D', 'O', Paragraph('AUDITORÍA INTERNA N°', lblc), True), ('P', 'U', Paragraph(esc(getattr(a, 'codigo', '')), valc), False),
                       ('AA', 'AL', Paragraph('FECHA&nbsp;&nbsp;DE ELABORACIÓN', lblc), True), ('AM', 'AR', Paragraph(_f(fecha_elab), valc), False)]))
    story += [sep(), banda('1. DATOS DEL LABORATORIO'), sep()]
    lbl_txt = ['EMPRESA']; story += [campo('E', 'F', empresa_nombre(cfg, vacio=''), centrado=True), sep()]
    lbl_txt = ['DIRECCIÓN']; story += [campo('E', 'F', getattr(cfg, 'direccion', '') if cfg else ''), sep()]
    lbl_txt = ['RESPONSABLE DEL SISTEMA INTEGRADO DE GESTIÓN']; story += [campo('R', 'S', getattr(cfg, 'responsable_sig', '') if cfg else ''), sep()]
    story += [banda('2. CARACTERÍSTICAS DE LA AUDITORÍA'), sep()]
    lbl_txt = ['OBJETIVO']; story += [campo('E', 'F', getattr(a, 'objetivo', ''), filas=2), sep()]
    lbl_txt = ['ALCANCE']; story += [campo('E', 'F', getattr(a, 'alcance', ''), filas=2), sep()]
    otros = getattr(a, 'criterios', '') or ''
    story += [fila([('A', 'H', Paragraph('CRITERIOS A AUDITAR', ParagraphStyle('pllblcr', parent=lbl, fontSize=f - 0.6)), True),
                    ('I', 'M', Paragraph('ISO 9001:2015', lblc), True), ('N', 'O', X('iso_9001' in normas_cod), False),
                    ('P', 'T', Paragraph('ISO 14001:2015', lblc), True), ('U', 'V', X('iso_14001' in normas_cod), False),
                    ('W', 'AA', Paragraph('ISO 45001:2018', lblc), True), ('AB', 'AC', X('iso_45001' in normas_cod), False),
                    ('AD', 'AK', Paragraph('NTP ISO/IEC 17025:2017', lblc), True), ('AL', 'AM', X('iso_17025' in normas_cod), False),
                    ('AN', 'AP', Paragraph('OTRO(S)', lblc), True), ('AQ', 'AU', Paragraph(esc(otros), ParagraphStyle('plot', parent=val, fontSize=f - 0.6, leading=f)), False)],
                   alto=None), sep()]
    lbl_txt = ['DOCUMENTOS DE REFERENCIA']; story += [campo('K', 'L', getattr(a, 'documentos_referencia', ''), filas=3), sep()]
    story += [fila([('A', 'H', Paragraph('TIPO DE AUDITORÍA', lbl), True),
                    ('I', 'R', Paragraph('PRESENCIAL', lblc), True), ('S', 'U', X(modalidad == 'presencial'), False),
                    ('V', 'AE', Paragraph('REMOTA', lblc), True), ('AF', 'AH', X(modalidad == 'remota'), False),
                    ('AI', 'AR', Paragraph('HÍBRIDO', lblc), True), ('AS', 'AU', X(modalidad == 'hibrido'), False)]), sep()]
    story += [banda('3. EQUIPO AUDITOR'), sep()]
    for rot, rol in (('AUDITOR LÍDER', 'lider'), ('AUDITOR(ES)', 'auditor'), ('EXPERTO(S)', 'experto'), ('OBSERVADOR(ES)', 'observador')):
        nombre = (_nombre_lider(a) if rol == 'lider' else _equipo_por_rol(a, rol))
        story += [fila([('A', 'F', Paragraph(rot, lbls), True), ('G', 'AU', Paragraph(esc(nombre), val), False)]), sep()]
    story += [banda('4. CRONOGRAMA DE ENTREVISTAS'), sep()]

    # Cronograma: columnas A:C, D:F, G:K, L:P, Q:U, V:Z, AA:AE, AF:AI, AJ:AM, AN:AQ, AR:AU
    segs = [('A', 'C'), ('D', 'F'), ('G', 'K'), ('L', 'P'), ('Q', 'U'), ('V', 'Z'), ('AA', 'AE'),
            ('AF', 'AI'), ('AJ', 'AM'), ('AN', 'AQ'), ('AR', 'AU')]
    cw = [ancho(x, y) for x, y in segs]
    thc = ParagraphStyle('plth', parent=lblc, fontSize=f - 0.4, leading=(f - 0.4) * 1.15)
    tcc = ParagraphStyle('plcc', parent=val, alignment=TA_CENTER, fontSize=f, leading=f * 1.2)
    tcl = ParagraphStyle('plcl', parent=val, fontSize=f, leading=f * 1.2)
    MOD = {'presencial': 'In situ', 'remota': 'Remoto', 'hibrido': 'Híbrido'}
    REQS = ['req_9001', 'req_14001', 'req_45001', 'req_17025']
    cf = [[Paragraph('FECHA', thc), Paragraph('HORA', thc), Paragraph('PROCESO / ÁREA A EVALUAR', thc), Paragraph('REQUISITOS', thc), '', '', '',
           Paragraph('MODALIDAD DE AUDITORÍA', thc), Paragraph('TIC', thc), Paragraph('AUDITOR / EXPERTO TÉCNICO', thc), Paragraph('AUDITADO', thc)],
          ['', '', '', Paragraph('ISO 9001:2015', thc), Paragraph('ISO 14001:2015', thc), Paragraph('ISO 45001:2018', thc),
           Paragraph('NTP ISO/IEC 17025:2017', thc), '', '', '', ''],
          [''] * 11]
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 2), azul),
           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('SPAN', (3, 0), (6, 0)),
           ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
           ('LEFTPADDING', (0, 0), (-1, -1), 1.5), ('RIGHTPADDING', (0, 0), (-1, -1), 1.5)]
    for c in (0, 1, 2, 7, 8, 9, 10):
        est.append(('SPAN', (c, 0), (c, 2)))
    for c in (3, 4, 5, 6):
        est.append(('SPAN', (c, 1), (c, 2)))
    est += [('LEFTPADDING', (0, 3), (1, -1), 0.5), ('RIGHTPADDING', (0, 3), (1, -1), 0.5)]
    alturas = [rh(18.75)] * 3
    for e in (getattr(a, 'cronograma_entrevistas', None) or []):
        if not isinstance(e, dict):
            continue
        reqs = [Paragraph(esc(e.get(k_, '')), tcc) for k_ in REQS]
        legado = str(e.get('requisitos', '') or '')
        r = len(cf)
        if legado and not any(e.get(k_) for k_ in REQS):
            reqs = [Paragraph(esc(legado), tcc), '', '', '']
            est.append(('SPAN', (3, r), (6, r)))
        cf.append([Paragraph(esc(e.get('fecha', '')), ParagraphStyle('plfe', parent=tcc, fontSize=f - 1.2)),
                   Paragraph(_hora_ampm(e.get('hora', '')), ParagraphStyle('plho', parent=tcc, fontSize=f - 0.9)),
                   Paragraph(esc(e.get('area', '')), tcl)] + reqs +
                  [Paragraph(MOD.get(e.get('modalidad', ''), ''), tcc), Paragraph(esc(e.get('tic', '')), tcc),
                   Paragraph(esc(e.get('auditor', '')), tcl), Paragraph(esc(e.get('auditado', '')), tcl)])
        alturas.append(None)
    # Solo las entrevistas registradas; sin ninguna, una fila vacía.
    if len(cf) == 3:
        cf.append([''] * 11); alturas.append(rh(18.75))
    tc = Table(cf, colWidths=cw, rowHeights=alturas, repeatRows=3)
    tc.setStyle(TableStyle(est))
    story += [tc, sep()]

    story += [banda('5. OBSERVACIONES'), sep()]
    obs_p = Paragraph(esc(getattr(a, 'observaciones_plan', '')), val)
    obs = Table([[obs_p]], colWidths=[W])
    _, h_obs = obs_p.wrap(W - 6, 1000)
    obs._argH[0] = max(rh(18.75) * 5, h_obs + 6)
    obs.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(obs)

    # Firma del auditor líder (T88:AB88)
    firma_b = ParagraphStyle('plfb', parent=lbl, textColor=colors.black, alignment=TA_CENTER)
    firma_n = ParagraphStyle('plfn', parent=val, alignment=TA_CENTER)
    lider = _nombre_lider(a)
    pre = W * sum(anchos[:_col_idx('T')]) / tot
    fw = ancho('T', 'AB')
    firma = Table([['', ''], ['', Paragraph('AUDITOR LÍDER', firma_b)], ['', Paragraph(esc(lider), firma_n)]],
                  colWidths=[pre, fw], rowHeights=[rh(18.75) * 3, None, None], hAlign='LEFT')
    firma.setStyle(TableStyle([('LINEBELOW', (1, 0), (1, 0), 0.6, colors.black),
                               ('TOPPADDING', (0, 1), (-1, -1), 1), ('BOTTOMPADDING', (0, 1), (-1, -1), 1)]))
    story.append(firma)
    doc.build(story)
    return buf.getvalue()


def empresa_corta(cfg, vacio='LA EMPRESA'):
    """Nombre corto de la empresa para rótulos ("METRINDUST S.A.C."): la parte
    después del último " - " del nombre configurado, o el nombre completo."""
    n = empresa_nombre(cfg, vacio=vacio)
    return n.split(' - ')[-1].strip() if ' - ' in n else n


def _grilla_excel(W, anchos):
    """Anchos de columna en puntos a partir de los anchos de columna del Excel
    (en caracteres), escalados al ancho útil de la página."""
    total = float(sum(anchos))
    # Ancho real de una columna de Excel: 7 px por carácter + 5 px de margen
    # (0,75 pt por px). La página escala la hoja para que entre a lo ancho,
    # igual que al imprimirla; esa misma escala se aplica a altos y letras.
    total_pt = sum((a * 7 + 5) * 0.75 for a in anchos)
    return [W * a / total for a in anchos], W / total_pt


def generar_acta_pdf(acta) -> bytes:
    """Acta de reunión de apertura o de cierre de auditoría, con la grilla del
    formato en Excel: datos de la auditoría, 12 filas de participantes con la
    condición marcada con X, tres secciones con recuadro y firmas."""
    es_cierre = getattr(acta, 'tipo', '') == 'cierre'
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=10 * mm, bottomMargin=10 * mm, title='Acta de auditoría')
    W = doc.width
    cfg = _cargar_cfg()
    a = getattr(acta, 'auditoria', None)
    # Columnas A..L del formato
    cw, k = _grilla_excel(W, [11.43, 11.43, 7.86, 7.86, 7.71, 7.71, 7.71, 7.71, 7.86, 12.86, 12.86, 12.86])
    azul = colors.HexColor('#16365C')
    fs = 11 * k          # el tamaño 11 del Excel a la escala de la página
    lbl = ParagraphStyle('aclbl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2, textColor=colors.white)
    lblc = ParagraphStyle('aclblc', parent=lbl, alignment=TA_CENTER)
    valc = ParagraphStyle('acvalc', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER)
    th = ParagraphStyle('acth', fontName='Helvetica-Bold', fontSize=fs * 0.92, leading=fs * 1.1, alignment=TA_CENTER, textColor=colors.white)
    banda = ParagraphStyle('acband', fontName='Helvetica-Bold', fontSize=fs * 1.08, leading=fs * 1.3, textColor=colors.white)
    mini = ParagraphStyle('acmini', fontName='Helvetica', fontSize=fs * 0.56, leading=fs * 0.64, alignment=TA_CENTER)
    td = ParagraphStyle('actd', fontName='Helvetica', fontSize=fs * 0.95, leading=fs * 1.15)
    tdc = ParagraphStyle('actdc', parent=td, alignment=TA_CENTER, fontName='Helvetica-Bold')
    cuerpo = ParagraphStyle('accpo', fontName='Helvetica', fontSize=fs, leading=fs * 1.3)
    firma_b = ParagraphStyle('acfb', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER)
    firma_n = ParagraphStyle('acfn', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER)
    rh = lambda pt: pt * k          # alto de fila del Excel (puntos) a escala

    titulo = 'ACTA DE REUNIÓN DE CIERRE DE AUDITORÍA' if es_cierre else 'ACTA DE REUNIÓN DE APERTURA DE AUDITORÍA'
    codigo = COD_ACTA_CIERRE if es_cierre else COD_ACTA_APERTURA
    modalidad = getattr(a, 'modalidad', '') if a else ''
    fecha = (getattr(a, 'fecha_fin', None) if es_cierre else getattr(a, 'fecha_inicio', None)) if a else None
    if not fecha and getattr(acta, 'created_at', None):
        fecha = acta.created_at.date()

    story = [_cabecera_met12(W, titulo, codigo, cfg), Spacer(1, rh(7.5))]

    # Datos de la auditoría (filas 7 a 10)
    x = 'X'
    mod = {'presencial': 0, 'remota': 1, 'hibrido': 2}.get(modalidad, -1)
    datos = [
        [Paragraph('Auditoría Interna N°:', lbl), '', Paragraph(getattr(a, 'codigo', '') if a else '', valc)] + [''] * 9,
        [Paragraph('Fecha:', lbl), '', Paragraph(_f(fecha), valc)] + [''] * 9,
        [Paragraph('Tipo de Auditoría', lbl), '', Paragraph('In Situ', lblc), '', Paragraph(x if mod == 0 else '', valc), '',
         Paragraph('Remoto', lblc), '', Paragraph(x if mod == 1 else '', valc), '', Paragraph('Híbrido', lblc), Paragraph(x if mod == 2 else '', valc)],
        [Paragraph('Área(s) evaluada(s):', lbl), '', Paragraph(getattr(a, 'areas_procesos', '') if a else '', valc)] + [''] * 9,
    ]
    t = Table(datos, colWidths=cw, rowHeights=[rh(22.5), rh(22.5), rh(22.5), None])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 0), (1, 0)), ('SPAN', (2, 0), (11, 0)),
        ('SPAN', (0, 1), (1, 1)), ('SPAN', (2, 1), (11, 1)),
        ('SPAN', (0, 2), (1, 2)), ('SPAN', (2, 2), (3, 2)), ('SPAN', (4, 2), (5, 2)), ('SPAN', (6, 2), (7, 2)), ('SPAN', (8, 2), (9, 2)),
        ('SPAN', (0, 3), (1, 3)), ('SPAN', (2, 3), (11, 3)),
        ('BACKGROUND', (0, 0), (1, 3), azul), ('BACKGROUND', (2, 2), (3, 2), azul),
        ('BACKGROUND', (6, 2), (7, 2), azul), ('BACKGROUND', (10, 2), (10, 2), azul),
        ('TOPPADDING', (0, 3), (-1, 3), 5), ('BOTTOMPADDING', (0, 3), (-1, 3), 5),
    ]))
    story += [t, Spacer(1, rh(7.5))]

    # 1. Participantes: 12 filas (más si hay más participantes)
    parts = [p for p in (getattr(acta, 'participantes', None) or []) if isinstance(p, dict)]
    filas = [[Paragraph('1. PARTICIPANTES', banda)] + [''] * 11,
             [Paragraph('NOMBRE', th), '', '', '', Paragraph('CONDICIÓN (Marcar con una x)', th), '', '', '',
              Paragraph('CARGO', th), '', Paragraph('FIRMA', th), '']]
    for n in range(max(12, len(parts))):
        p = parts[n] if n < len(parts) else {}
        cond = str(p.get('condicion', '') or '').lower()
        filas.append([Paragraph(str(p.get('nombre', '') or ''), td), '', '', '',
                      Paragraph('X' if 'auditor' in cond else '', tdc), Paragraph('EQUIPO<br/>AUDITOR', mini),
                      Paragraph('X' if 'auditado' in cond else '', tdc), Paragraph('AUDITADO', mini),
                      Paragraph(str(p.get('cargo', '') or ''), td), '', '', ''])
    est = [('GRID', (0, 1), (-1, -1), 0.5, colors.black), ('BOX', (0, 0), (-1, 0), 0.5, colors.black),
           ('BACKGROUND', (0, 0), (-1, 1), azul), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('LEFTPADDING', (4, 2), (7, -1), 1), ('RIGHTPADDING', (4, 2), (7, -1), 1),
           ('SPAN', (0, 0), (11, 0)), ('SPAN', (0, 1), (3, 1)), ('SPAN', (4, 1), (7, 1)),
           ('SPAN', (8, 1), (9, 1)), ('SPAN', (10, 1), (11, 1))]
    for r in range(2, len(filas)):
        est += [('SPAN', (0, r), (3, r)), ('SPAN', (8, r), (9, r)), ('SPAN', (10, r), (11, r))]
    # Filas de participantes algo más bajas que en el Excel (30 pt) para que el
    # acta completa, con firmas, entre en una hoja.
    t = Table(filas, colWidths=cw, rowHeights=[rh(19.5), rh(22.5)] + [rh(25)] * (len(filas) - 2))
    t.setStyle(TableStyle(est))
    story.append(t)

    # Secciones 2 a 4: franja y recuadro de dos filas del formato
    if es_cierre:
        secciones = [('2. RESULTADOS', getattr(acta, 'contenido', '')),
                     ('3. OBSERVACIONES DEL EQUIPO AUDITOR', getattr(acta, 'seccion3', '')),
                     ('4. OBSERVACIONES DE ' + empresa_corta(cfg).upper(), getattr(acta, 'observaciones_auditado', ''))]
    else:
        secciones = [('2. PROPÓSITO DE LA AUDITORÍA', getattr(acta, 'contenido', '')),
                     ('3. CONSIDERACIONES DEL ÁREA AUDITADA', getattr(acta, 'seccion3', '')),
                     ('4. COMPROMISOS POR PARTE DEL ÁREA AUDITADA', getattr(acta, 'observaciones_auditado', ''))]
    for rotulo, texto in secciones:
        cont = Paragraph(str(texto or '').replace('&', '&amp;').replace('<', '&lt;').replace('\n', '<br/>'), cuerpo)
        sec = Table([[Paragraph(rotulo, banda)], [cont]], colWidths=[W], rowHeights=[rh(19.5), None])
        sec.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.5, colors.black), ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
                                 ('BACKGROUND', (0, 0), (-1, 0), azul), ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                                 ('VALIGN', (0, 1), (-1, 1), 'TOP'), ('TOPPADDING', (0, 1), (-1, 1), 4)]))
        # El recuadro tiene al menos el alto de las dos filas del formato.
        _, alto = cont.wrap(W - 12, 1000)
        sec._argH[1] = max(rh(62), alto + 10)
        story.append(sec)

    # Firmas (columnas C:E y I:J del formato)
    lider = _nombre_lider(a)
    # Representa a la empresa el responsable del sistema integrado de gestión (Configuración).
    representante = (getattr(cfg, 'responsable_sig', '') if cfg else '') or ''
    firmas = Table([
        ['', '', '', '', ''],
        ['', Paragraph(f'Representante de {empresa_corta(cfg)}', firma_b), '', Paragraph('Auditor Líder', firma_b), ''],
        ['', Paragraph(_xml(representante) or '(Nombre y Apellido)', firma_n), '',
         Paragraph(_xml(lider) or '(Nombre y Apellido)', firma_n), ''],
    ], colWidths=[sum(cw[0:2]), sum(cw[2:5]), sum(cw[5:8]), sum(cw[8:10]), sum(cw[10:12])], rowHeights=[rh(34), None, None])
    firmas.setStyle(TableStyle([('LINEBELOW', (1, 0), (1, 0), 0.6, colors.black), ('LINEBELOW', (3, 0), (3, 0), 0.6, colors.black),
                                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                ('TOPPADDING', (0, 1), (-1, -1), 1), ('BOTTOMPADDING', (0, 1), (-1, -1), 1)]))
    story += [Spacer(1, rh(4)), firmas]
    doc.build(story)
    return buf.getvalue()


def empresa_nombre(cfg, vacio='LA EMPRESA'):
    """Nombre de la empresa (Configuración → Identidad). Nunca cae al nombre
    del producto: un formato de la empresa no debe decir el nombre del sistema."""
    try:
        return (cfg.subtitulo or '').strip() or vacio if cfg else vacio
    except Exception:
        return vacio


# Azul de las celdas de título en los formatos de lista de verificación.
AZUL_LISTA = colors.HexColor('#16365C')
GRIS_ANEXO = colors.HexColor('#D9D9D9')


def _tw(W, *twips):
    """Anchos de columna según la grilla del formato Word (en twips). La escala
    es común a todas las tablas: la de requisitos (10207 twips) ocupa todo el ancho."""
    total = 10207.0
    return [W * t / total for t in twips]


def _cabecera_lab_auditoria(W, a, cfg):
    """Primera página de la lista de verificación, como el formato: datos del
    laboratorio, miembros del equipo evaluador y firma del líder."""
    lbl = ParagraphStyle('lvcl', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.white)
    lblc = ParagraphStyle('lvclc', parent=lbl, alignment=TA_CENTER)
    val = ParagraphStyle('lvcv', fontName='Helvetica', fontSize=10, leading=12)
    valc = ParagraphStyle('lvcvc', parent=val, alignment=TA_CENTER)
    firma_lbl = ParagraphStyle('lvcf', fontName='Helvetica', fontSize=11, leading=13, alignment=TA_CENTER)
    out = []
    fechas = ''
    if a:
        fi, ff = _f(getattr(a, 'fecha_inicio', None)), _f(getattr(a, 'fecha_fin', None))
        fechas = f'{fi} a {ff}' if (fi and ff and fi != ff) else (fi or ff or _f(getattr(a, 'fecha_programada', None)) or '')
    import datetime as _dt
    datos = [
        ('Tipo de Laboratorio:', 'Calibración', valc),
        ('Nombre del Laboratorio:', empresa_nombre(cfg, vacio=''), val),
        ('Dirección:', getattr(cfg, 'direccion', '') if cfg else '', val),
        ('Fechas de Auditoría:', fechas, val),
        ('Fecha de Emisión:', _f(_dt.date.today()), val),
    ]
    t = Table([[Paragraph(k, lbl), Paragraph(str(v or ''), st)] for k, v, st in datos],
              colWidths=_tw(W, 2929, 6710), rowHeights=[6.2 * mm] * 5)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (0, -1), AZUL_LISTA),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    out += [t, Spacer(1, 8 * mm)]

    # Miembros del equipo evaluador: filas fijas del formato; varios nombres
    # de un mismo rol van separados por coma.
    integrantes = list(getattr(a, 'equipo').all()) if (a and hasattr(a, 'equipo')) else []
    por_rol = {}
    for ig in integrantes:
        nom = _nom_u(getattr(ig, 'usuario', None)) or getattr(ig, 'nombre_externo', '') or ''
        if nom:
            por_rol.setdefault(getattr(ig, 'rol', ''), []).append(nom)
    roles = [('lider', 'Auditor Líder:'), ('auditor', 'Auditor:'), ('experto', 'Experto Técnico:')]
    if por_rol.get('observador'):
        roles.append(('observador', 'Observador:'))
    filas = [[Paragraph('Miembros del Equipo Evaluador', lblc), ''],
             [Paragraph('Función', lblc), Paragraph('Nombre Completo', lblc)]]
    for clave, etiqueta in roles:
        filas.append([Paragraph(etiqueta, lbl), Paragraph(', '.join(por_rol.get(clave, [])), valc)])
    te = Table(filas, colWidths=_tw(W, 2882, 6746), rowHeights=[6.2 * mm] * len(filas))
    te.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('SPAN', (0, 0), (1, 0)),
                            ('BACKGROUND', (0, 0), (1, 1), AZUL_LISTA), ('BACKGROUND', (0, 2), (0, -1), AZUL_LISTA),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    out += [te, Spacer(1, 26 * mm)]

    # Firma del líder del equipo y fecha: etiqueta y línea para firmar.
    firma = Table([[Paragraph('Firma del Líder del Equipo:', firma_lbl), ''],
                   [Paragraph('Fecha:', firma_lbl), '']], colWidths=_tw(W, 2978, 6945), rowHeights=[8 * mm, 8 * mm])
    firma.setStyle(TableStyle([('LINEBELOW', (1, 0), (1, 1), 0.6, colors.black),
                               ('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))
    out += [firma, Spacer(1, 16 * mm)]
    return out


_NOTAS_LISTA_17025 = ('Cuando se use esta lista de verificación: para mayores detalles se debe revisar la Norma '
                      'Técnica ISO/IEC 17025:2017 incluidas las Notas, debido a que esta lista no contiene detalles '
                      'de la norma. También debe revisar la Directriz DA-acr-06D y otras directrices, reglamentos, '
                      'procedimientos de INACAL-DA.')

_NOTA_ANEXO_17025 = ('Nota: si el laboratorio se encuentra acreditado o en vías de acreditación en una disciplina o '
                     'subdisciplina que no figura en esta tabla, esto no lo exime de participar en un programa de '
                     'ensayo de aptitud.')

# Anexo 1 del formato de lista 17025: disciplinas de calibración (tabla fija).
_ANEXO_CALIBRACION = [
    ('TEMPERATURA', 'TEMPERATURA', ['Temperatura', 'Temperatura de punto de rocío', 'Temperatura por simulación eléctrica', 'Caracterización de medios isotermos']),
    ('HUMEDAD', 'HUMEDAD', ['Humedad relativa', 'Caracterización de medios isotermos']),
    ('FUERZA y PAR', 'FUERZA y PAR', ['Fuerza: Cociente de tensiones', 'Fuerza: deformación', 'Fuerza: Fuerza', 'Par de torsión']),
    ('MASA', 'MASA', ['Masa', 'Instrumentos de pesaje']),
    ('PRESIÓN Y VACIO', 'PRESIÓN Y VACIO', ['Presión absoluta hidráulica', 'Presión absoluta neumática', 'Presión diferencial hidráulica', 'Presión diferencial neumática', 'Presión relativa hidráulica', 'Presión relativa neumática', 'Simulación de señal para trasmisores y transductores', 'Vacío']),
    ('CAUDAL', 'CAUDAL', ['Caudal en gas', 'Caudal en líquido']),
    ('VOLUMEN', 'VOLUMEN', ['Volumen de líquidos', 'Volumen de solidos', 'Volumen de gas']),
    ('ELECTRICIDAD', 'ELECTRICIDAD', ['Tensión AC y DC', 'Intensidad AC y DC', 'Resistencia AC y DC', 'Capacidad', 'Medidores de Energía']),
    ('TIEMPO Y FRECUENCIA', 'TIEMPO Y FRECUENCIA', ['Intervalo de tiempo', 'Frecuencia: Periodo', 'Frecuencia: Frecuencia']),
    ('ACÚSTICA', 'ACÚSTICA', ['Acústica']),
    ('DIMENSIONAL', 'DIMENSIONAL', ['Longitud: Longitud', 'Rugosidad', 'Ángulos', 'Formas: Cilindricidad; Esfericidad; Paralelismo; Parámetros de roscas; Perpendicularidad; Planitud; Rectitud; Redondez; Otras formas', 'Tamaño de partícula']),
    ('DUREZA', 'DUREZA', ['Dureza']),
    ('VISCOSIDAD', 'VISCOSIDAD', ['Viscosidad dinámica', 'Viscosidad cinemática']),
    ('DENSIDAD', 'DENSIDAD', ['Densidad']),
    ('ELECTROQUÍMICOS', 'POTENCIOMETRÍA', ['Potenciometría']),
    ('ELECTROQUÍMICOS', 'CONDUCTOMETRÍA', ['Conductometría']),
    ('RADIACIONES IONIZANTES', 'RADIACIONES IONIZANTES', ['Actividad de fuentes radioactivas', 'Magnitudes dosimétricas: Exposición; Kerma en el aire; Tasa de exposición; Tasa de kerma en el aire; Magnitudes radiométricas.', 'Magnitudes de radioprotección: Dosis equivalente ambiental; Dosis equivalente personal; Dosis equivalentes; Tasa de dosis equivalente; Tasa de dosis equivalente ambiental; Tasa de dosis equivalente personal; Tasa de tejido bajo un determinado espesor; Tasa de dosis absorbida en agua']),
    ('ÓPTICA', 'ÓPTICA', ['Colorimetría', 'Fibras ópticas', 'Magnitudes fotométricas', 'Magnitudes radiométricas', 'Propiedades de los sistemas ópticos']),
    ('CONCENTRACIÓN DE GASES', 'CONCENTRACIÓN DE GASES', ['Mezcla de gases', 'Analizadores de gases']),
    ('MAGNETISMO', 'MAGNETISMO', ['Densidad de flujo magnético', 'Inducción magnética', 'Propiedades de materiales magnéticos: Permeabilidad; Perdidas magnéticas']),
    ('VELOCIDAD DE AIRE', 'VELOCIDAD DE AIRE', ['Velocidad de aire']),
]


def _parrafos_formato(item, base, codigo_en_texto=False):
    """Párrafos del texto de un requisito con la presentación del formato
    (negritas, viñetas y sangrías). Sin formato guardado, usa el texto plano."""
    from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
    alin = {'both': TA_JUSTIFY, 'left': TA_LEFT, 'center': TA_CENTER, 'right': TA_RIGHT}
    formato = getattr(item, 'formato', None) or []
    if not formato:
        texto = (getattr(item, 'titulo', '') or '')
        texto = texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        formato = [{'t': linea} for linea in texto.split('\n')]
    out = []
    for n, par in enumerate(formato):
        t = par.get('t', '')
        ind = float(par.get('i', 0) or 0)
        lab = par.get('l', '')
        st = ParagraphStyle(f'lvf{n}', parent=base, alignment=alin.get(par.get('j', 'both'), TA_JUSTIFY),
                            leftIndent=ind, bulletIndent=max(ind - 14.5, 0), bulletFontName=base.fontName,
                            bulletFontSize=base.fontSize)
        if not t and not lab:
            out.append(Paragraph('&nbsp;', st))
        elif lab:
            out.append(Paragraph(t or '&nbsp;', st, bulletText=lab))
        else:
            out.append(Paragraph(t, st))
    return out


def _tabla_seguimiento(W, items):
    """Ítems para auditorías internas de seguimiento (lista 17025), con el
    encabezado de tres filas del formato."""
    th = ParagraphStyle('lvsth', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER, textColor=colors.white)
    tdb = ParagraphStyle('lvstd', fontName='Helvetica-Bold', fontSize=9, leading=11)
    tdc = ParagraphStyle('lvstdc', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER)
    td = ParagraphStyle('lvstdn', fontName='Helvetica', fontSize=8.5, leading=10.5)
    tdn = ParagraphStyle('lvstdnc', parent=td, alignment=TA_CENTER)
    filas = [
        [Paragraph('ÍTEM', th), Paragraph('REQUISITO', th), Paragraph('DOCUMENTO DE REFERENCIA', th), Paragraph('EVIDENCIAS / COMENTARIOS', th), ''],
        ['', '', '', Paragraph('EVALUACION', th), Paragraph('CONCLUSIÓN', th)],
        ['', '', '', '', Paragraph('C / NC / OBS / NA', th)],
    ]
    for it in items:
        filas.append([Paragraph(getattr(it, 'codigo', ''), tdc), _parrafos_formato(it, tdb),
                      Paragraph(getattr(it, 'documento_referencia', '') or '', td),
                      Paragraph(getattr(it, 'evidencia', '') or '', td),
                      Paragraph(_RESULTADOS_ITEM_LBL.get(getattr(it, 'resultado', ''), ''), tdn)])
    t = Table(filas, colWidths=_tw(W, 537, 2017, 1984, 3543, 1695), repeatRows=3)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 2), AZUL_LISTA),
        ('SPAN', (0, 0), (0, 2)), ('SPAN', (1, 0), (1, 2)), ('SPAN', (2, 0), (2, 2)),
        ('SPAN', (3, 0), (4, 0)), ('SPAN', (3, 1), (3, 2)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    t.hAlign = 'CENTER'
    return t


def _tabla_requisitos(W, items, titulo_bloque):
    """Requisitos de la norma con el encabezado del formato (título del bloque,
    y Documento de referencia / Evaluación como celdas combinadas en dos filas).
    Como en el formato, los títulos de capítulo y cláusula van en la misma fila
    que el primer numeral que los sigue (4 · 4.1 · 4.1.1 en una sola fila)."""
    th = ParagraphStyle('lvrth', fontName='Helvetica-Bold', fontSize=8.5, leading=10, alignment=TA_CENTER, textColor=colors.white)
    thp = ParagraphStyle('lvrthp', parent=th, fontSize=7.5, leading=9)
    base = ParagraphStyle('lvrtd', fontName='Helvetica', fontSize=8, leading=9.4)
    cod = ParagraphStyle('lvrcod', fontName='Helvetica-Bold', fontSize=8, leading=9.4, alignment=TA_CENTER)
    td = ParagraphStyle('lvrtdn', fontName='Helvetica', fontSize=8, leading=9.4)
    tdc = ParagraphStyle('lvrtdc', parent=td, alignment=TA_CENTER)
    blanco = Paragraph('&nbsp;', base)
    filas = [
        [Paragraph(titulo_bloque, th), '', Paragraph('DOCUMENTO DE REFERENCIA', th), Paragraph('EVALUACIÓN', th), Paragraph('CONCLUSIONES', thp)],
        [Paragraph('Nro.', th), Paragraph('DESCRIPCIÓN', th), '', '', Paragraph('C / NC / OBS / NA', thp)],
    ]
    pendientes = []   # títulos de capítulo/cláusula que esperan a su primer numeral

    ancho_desc = _tw(W, 3260)[0] - 6

    def _fila(secciones, it):
        codigos, textos = [], []
        for sec in secciones:
            titulo = (getattr(sec, 'titulo', '') or '').replace('&', '&amp;').replace('<', '&lt;')
            p_tit = Paragraph(f'<b>{titulo}</b>', base)
            # El número ocupa las mismas líneas que su subtítulo, para que el
            # siguiente numeral quede alineado con su texto.
            lineas = max(1, round(p_tit.wrap(ancho_desc, 1000)[1] / base.leading))
            codigos += [Paragraph(getattr(sec, 'codigo', '') + '<br/>&nbsp;' * (lineas - 1), cod), blanco]
            textos += [p_tit, blanco]
        if it is not None:
            codigos.append(Paragraph(getattr(it, 'codigo', ''), cod))
            textos += _parrafos_formato(it, base)
            return [codigos, textos, Paragraph(getattr(it, 'documento_referencia', '') or '', td),
                    Paragraph(getattr(it, 'evidencia', '') or '', td),
                    Paragraph(_RESULTADOS_ITEM_LBL.get(getattr(it, 'resultado', ''), ''), tdc)]
        return [codigos[:-1], textos[:-1], '', '', '']

    for it in items:
        if getattr(it, 'es_seccion', False):
            pendientes.append(it)
            continue
        filas.append(_fila(pendientes, it))
        pendientes = []
    if pendientes:
        filas.append(_fila(pendientes, None))
    if len(filas) == 2:
        filas.append([Paragraph('—', tdc), Paragraph('Genere la lista desde el catálogo de la norma.', td), '', '', ''])
    # Una fila no se parte entre páginas (como en el formato); solo si una fila
    # sola es más alta que la página se permite dividirla.
    t = Table(filas, colWidths=_tw(W, 709, 3260, 1418, 3686, 1134), repeatRows=2)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 1), AZUL_LISTA),
        ('SPAN', (0, 0), (1, 0)), ('SPAN', (2, 0), (2, 1)), ('SPAN', (3, 0), (3, 1)),
        ('VALIGN', (0, 0), (-1, 1), 'MIDDLE'), ('VALIGN', (0, 2), (-1, -1), 'TOP'),
        ('VALIGN', (4, 2), (4, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 2), (-1, -1), 2), ('BOTTOMPADDING', (0, 2), (-1, -1), 4),
    ]))
    return t


def generar_lista_verificacion_pdf(lista) -> bytes:
    """Lista de verificación igual al formato del procedimiento de auditoría
    interna: una para NTP-ISO/IEC 17025 (con ítems de seguimiento, notas y
    anexo de disciplinas) y otra para ISO 9001 / 14001 / 45001. El encabezado
    de control se repite en cada página, como en el formato."""
    cfg = _cargar_cfg()
    a = getattr(lista, 'auditoria', None)
    norma = getattr(lista, 'norma', '')
    es_17025 = norma == 'iso_17025'
    codigo = COD_LISTA_VERIF_17025 if es_17025 else COD_LISTA_VERIF_SIG
    if es_17025:
        titulo = 'LISTA DE VERIFICACIÓN DE AUDITORÍA NTP-ISO/IEC 17025'
        bloque_titulo = 'REQUISITOS DE LA NTP-ISO/IEC 17025:2017'
    elif norma == 'sig_integrado':
        titulo = 'LISTA DE VERIFICACIÓN DE AUDITORÍA ISO 9001, ISO 14001, ISO 45001'
        bloque_titulo = 'REQUISITOS DE LAS NORMAS ISO 9001:2015, ISO 14001:2015 E ISO 45001:2018'
    else:
        edicion = {'iso_9001': 'ISO 9001:2015', 'iso_14001': 'ISO 14001:2015', 'iso_45001': 'ISO 45001:2018'}
        titulo = f'LISTA DE VERIFICACIÓN DE AUDITORÍA {edicion.get(norma, _NORMAS_LBL.get(norma, norma))}'
        bloque_titulo = f'REQUISITOS DE LA NORMA {edicion.get(norma, _NORMAS_LBL.get(norma, norma))}'

    margen = 10 * mm
    W = A4[0] - 2 * margen
    cabecera = _cabecera_met12(W, titulo, codigo, cfg)
    _, alto_cab = cabecera.wrap(W, A4[1])

    def _encabezado(canvas, doc_):
        canvas.saveState()
        cabecera.drawOn(canvas, margen, A4[1] - margen - alto_cab)
        canvas.restoreState()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=margen, rightMargin=margen,
                            topMargin=margen + alto_cab + 4 * mm, bottomMargin=12 * mm, title='Lista de verificación')
    cuerpo = ParagraphStyle('lvcpo', fontName='Helvetica', fontSize=10, leading=12, alignment=4)
    nota = ParagraphStyle('lvnota', fontName='Helvetica', fontSize=8, leading=9.6, alignment=4)
    subt = ParagraphStyle('lvsub', fontName='Helvetica', fontSize=12, leading=14, leftIndent=W * 0.03)

    story = list(_cabecera_lab_auditoria(W, a, cfg))
    items = list(getattr(lista, 'items').all()) if hasattr(lista, 'items') else []
    seguimiento = [it for it in items if getattr(it, 'bloque', 'requisitos') == 'seguimiento']
    requisitos = [it for it in items if getattr(it, 'bloque', 'requisitos') != 'seguimiento']

    if es_17025:
        notas = Table([[[Paragraph('<b>NOTAS</b>', cuerpo), Paragraph(_NOTAS_LISTA_17025, cuerpo)]]],
                      colWidths=_tw(W, 9393))
        notas.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.6, colors.black),
                                   ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        notas.hAlign = 'CENTER'
        story += [notas, PageBreak(),
                  Paragraph('Ítems para considerar en las auditorías internas de seguimiento:', subt), Spacer(1, 4 * mm),
                  _tabla_seguimiento(W, seguimiento), Spacer(1, 4 * mm)]
    else:
        story.append(PageBreak())

    story.append(_tabla_requisitos(W, requisitos, bloque_titulo))

    if es_17025:
        anx_t = ParagraphStyle('lvanx', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_CENTER)
        anx_h = ParagraphStyle('lvanxh', fontName='Helvetica-Bold', fontSize=8.5, leading=10, alignment=TA_CENTER)
        anx_hl = ParagraphStyle('lvanxhl', parent=anx_h, alignment=TA_LEFT)
        anx_d = ParagraphStyle('lvanxd', fontName='Helvetica', fontSize=8, leading=9.6)
        story += [PageBreak(), Paragraph('ANEXO 1', anx_t), Spacer(1, 4 * mm),
                  Paragraph(_NOTA_ANEXO_17025, nota), Spacer(1, 3 * mm)]
        filas = [[Paragraph('LABORATORIOS DE CALIBRACIÓN', anx_h), '', ''],
                 [Paragraph('ÁREA', anx_h), Paragraph('Disciplina (MAGNITUD)', anx_hl), Paragraph('Subdisciplina', anx_hl)]]
        estilos = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 1), GRIS_ANEXO),
                   ('SPAN', (0, 0), (2, 0)), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                   ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
        inicio_area, area_previa = None, None
        for area, disc, subs in _ANEXO_CALIBRACION:
            r0 = len(filas)
            nueva_area = area != area_previa
            for k_, sub in enumerate(subs):
                filas.append([Paragraph(area if (k_ == 0 and nueva_area) else '', anx_d),
                              Paragraph(disc if k_ == 0 else '', anx_d), Paragraph(sub, anx_d)])
            if len(subs) > 1:
                estilos.append(('SPAN', (1, r0), (1, r0 + len(subs) - 1)))
            # Un área con varias disciplinas (Electroquímicos) es una sola celda.
            if nueva_area:
                inicio_area, area_previa = r0, area
            fin = len(filas) - 1
            if fin > inicio_area:
                estilos = [e for e in estilos if not (e[0] == 'SPAN' and e[1] == (0, inicio_area))]
                estilos.append(('SPAN', (0, inicio_area), (0, fin)))
        anexo = Table(filas, colWidths=_tw(W, 3261, 2126, 4820), repeatRows=2)
        anexo.setStyle(TableStyle(estilos))
        story.append(anexo)

    doc.build(story, onFirstPage=_encabezado, onLaterPages=_encabezado)
    return buf.getvalue()


def _pie_confidencial(canvas, doc_, cfg):
    """Pie de página de los formatos en Word: aviso de documento confidencial."""
    emp = empresa_corta(cfg)
    st = ParagraphStyle('piecf', fontName='Helvetica', fontSize=7, leading=8.6, alignment=TA_CENTER)
    p = Paragraph(f'<b>Documento Confidencial:</b> El contenido es propiedad intelectual de <b>{emp}</b><br/>'
                  'Toda copia impresa de este documento es considerada <b>"COPIA NO CONTROLADA"</b>.<br/>'
                  'El usuario es responsable de asegurar el uso de la versión vigente en consulta con el <b>Área SIG.</b>', st)
    ancho = A4[0] - 30 * mm
    _, alto = p.wrap(ancho, 100)
    p.drawOn(canvas, 15 * mm, 10 * mm)


def generar_informe_auditoria_pdf(a) -> bytes:
    """Informe de auditoría interna con la estructura del formato en Word:
    secciones numeradas (1 a 8) con sus literales a) a g), tabla de registro,
    tabla de resultados, firma del auditor líder y pie de documento confidencial.
    El encabezado de control se repite en cada página."""
    cfg = _cargar_cfg()
    margen_cab = 12 * mm
    Wc = A4[0] - 2 * margen_cab
    cabecera = _cabecera_met12(Wc, 'INFORME DE AUDITORÍA INTERNA', COD_INFORME_AUD, cfg)
    _, alto_cab = cabecera.wrap(Wc, A4[1])

    def _pagina(canvas, doc_):
        canvas.saveState()
        cabecera.drawOn(canvas, margen_cab, A4[1] - 10 * mm - alto_cab)
        _pie_confidencial(canvas, doc_, cfg)
        canvas.restoreState()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=18 * mm,
                            topMargin=10 * mm + alto_cab + 5 * mm, bottomMargin=24 * mm, title='Informe de auditoría')
    W = doc.width
    azul = colors.HexColor('#16365C')
    h1 = ParagraphStyle('ifh1', fontName='Helvetica-Bold', fontSize=9, leading=11, leftIndent=14, spaceBefore=8, spaceAfter=3)
    h2 = ParagraphStyle('ifh2', fontName='Helvetica-Bold', fontSize=9, leading=11, leftIndent=28, spaceBefore=6, spaceAfter=2)
    txt1 = ParagraphStyle('iftx1', fontName='Helvetica', fontSize=9, leading=12, leftIndent=28)
    txt2 = ParagraphStyle('iftx2', fontName='Helvetica', fontSize=9, leading=12, leftIndent=42)
    lbl = ParagraphStyle('iflbl', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.white)
    val = ParagraphStyle('ifval', fontName='Helvetica', fontSize=9, leading=11)
    th = ParagraphStyle('ifth', fontName='Helvetica-Bold', fontSize=8.5, leading=10.5, alignment=TA_CENTER, textColor=colors.white)
    td = ParagraphStyle('iftd', fontName='Helvetica', fontSize=8.5, leading=10.5)
    tdc = ParagraphStyle('iftdc', parent=td, alignment=TA_CENTER)
    nota = ParagraphStyle('ifnota', fontName='Helvetica', fontSize=8.5, leading=10.5)
    fbl = ParagraphStyle('iffbl', fontName='Helvetica-Bold', fontSize=9, leading=11)

    def esc(t):
        return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')

    def texto(t, estilo):
        return [Paragraph(esc(t) if (t or '').strip() else '—', estilo)]

    normas_cod = getattr(a, 'normas_aplicables', None) or []
    normas = ', '.join(_NORMAS_LBL.get(n, n) for n in normas_cod) or '—'
    responsable = getattr(cfg, 'responsable_sig', '') if cfg else ''
    auditados = []
    for ac in (getattr(a, 'actas').all() if hasattr(a, 'actas') else []):
        for p in (getattr(ac, 'participantes', None) or []):
            if isinstance(p, dict) and 'auditado' in str(p.get('condicion', '')).lower():
                nom = p.get('nombre', '')
                if nom and nom not in auditados:
                    auditados.append(nom)
    import datetime as _dt
    f_inf = getattr(a, 'fecha_informe', None)
    fecha_informe = f_inf.date() if f_inf else _dt.date.today()

    story = []
    # 1. Registro de auditoría
    story.append(Paragraph('1.&nbsp;&nbsp;REGISTRO DE AUDITORÍA', h1))
    reg = Table([
        [Paragraph('Fecha de Elaboración del Informe:', lbl), Paragraph(_f(fecha_informe), val)],
        [Paragraph('Auditoría Interna Nº:', lbl), Paragraph(esc(getattr(a, 'codigo', '')), val)],
        [Paragraph('Norma(s):', lbl), Paragraph(esc(normas), val)],
        [Paragraph('Responsable del Sistema Integrado de Gestión:', lbl), Paragraph(esc(responsable), val)],
    ], colWidths=[(W - 14) * 0.41, (W - 14) * 0.59])
    reg.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (0, -1), azul),
                             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    reg.hAlign = 'RIGHT'
    story.append(reg)

    # 2 y 3
    story.append(Paragraph('2.&nbsp;&nbsp;OBJETIVO DE LA AUDITORÍA', h1)); story += texto(getattr(a, 'objetivo', ''), txt1)
    story.append(Paragraph('3.&nbsp;&nbsp;ALCANCE DE LA AUDITORÍA', h1)); story += texto(getattr(a, 'alcance', ''), txt1)

    # 4. Detalles (a a g)
    story.append(Paragraph('4.&nbsp;&nbsp;DETALLES DE LA AUDITORÍA', h1))
    integrantes = []
    for rol, etiqueta in (('auditor', 'Auditor'), ('experto', 'Experto técnico')):
        for nom in [x.strip() for x in (_equipo_por_rol(a, rol) or '').split(',') if x.strip()]:
            integrantes.append(f'{nom} ({etiqueta})')
    lugar = getattr(a, 'lugar', '') or ''
    fi, ff = _f(getattr(a, 'fecha_inicio', None)), _f(getattr(a, 'fecha_fin', None))
    fechas = f'{fi} a {ff}' if (fi and ff and fi != ff) else (fi or ff)
    detalles = [
        ('a', 'AUDITOR LÍDER', _nombre_lider(a)),
        ('b', 'INTEGRANTES DEL EQUIPO AUDITOR (EN CASO CORRESPONDA)', ', '.join(integrantes)),
        ('c', 'OBSERVADOR (CUANDO APLIQUE)', _equipo_por_rol(a, 'observador')),
        ('d', 'REPRESENTANTE(S) DEL (DE LAS) ÁREA(S) AUDITADA(S)', ', '.join(auditados)),
        ('e', 'CRITERIOS DE AUDITORÍA', normas + (('\n' + getattr(a, 'criterios', '')) if getattr(a, 'criterios', '') else '')),
        ('f', 'LUGAR Y FECHA DONDE SE REALIZÓ LA AUDITORÍA', ' · '.join(x for x in (lugar, fechas) if x)),
        ('g', 'PERSONA(S) ENTREVISTADA(S)', getattr(a, 'personas_entrevistadas', '') or ', '.join(auditados)),
    ]
    for letra, rotulo, contenido in detalles:
        story.append(Paragraph(f'{letra}.&nbsp;&nbsp;{rotulo}', h2))
        story += texto(contenido, txt2)

    # 5. Fortalezas y debilidades
    story.append(Paragraph('5.&nbsp;&nbsp;FORTALEZAS Y DEBILIDADES', h1))
    story.append(Paragraph(f'<b>Fortalezas:</b> {esc(getattr(a, "fortalezas", "")) or "—"}', txt1))
    story.append(Paragraph(f'<b>Debilidades:</b> {esc(getattr(a, "debilidades", "")) or "—"}', txt1))

    # 6. Resultados
    story.append(Paragraph('6.&nbsp;&nbsp;RESULTADOS DE LA AUDITORÍA', h1))
    hallazgos = list(getattr(a, 'hallazgos').filter(is_active=True).order_by('id')) if hasattr(a, 'hallazgos') else []
    filas = [[Paragraph('N°', th), Paragraph('NORMA', th), Paragraph('REQUISITO', th), Paragraph('DESCRIPCIÓN', th),
              Paragraph('CLASIFICACIÓN<br/>DEL HALLAZGO (*)', th)]]
    for n, h in enumerate(hallazgos, 1):
        items = list(h.items_lista.select_related('lista').all()) if hasattr(h, 'items_lista') else []
        if items:
            # Norma y numeral reales del requisito (en la lista integrada el
            # Nro. es un correlativo y la referencia va en el texto).
            refs = [r for it in items for r in (
                it.referencias_norma() if it.lista.norma != 'iso_17025' and hasattr(it, 'referencias_norma')
                else [(_NORMAS_LBL.get(it.lista.norma, it.lista.norma), it.codigo)])]
            normas_h = list(dict.fromkeys(n for n, _ in refs))
            norma_h = ', '.join(normas_h)
            if len(normas_h) == 1:
                req_h = ', '.join(dict.fromkeys(c for _, c in refs))
            else:
                req_h = ' · '.join(dict.fromkeys(f'{n.replace("ISO ", "")}: {c}' for n, c in refs))
        else:
            req_h = getattr(h, 'requisito', '') or ''
            # Norma: la única de la auditoría o la que se nombra en el requisito.
            norma_h = _NORMAS_LBL.get(normas_cod[0], '') if len(normas_cod) == 1 else ''
            for clave, marca in (('iso_17025', '17025'), ('iso_9001', '9001'), ('iso_14001', '14001'), ('iso_45001', '45001')):
                if marca in req_h:
                    norma_h = _NORMAS_LBL.get(clave, '')
                    req_h = req_h.replace('NTP ISO/IEC', '').replace('ISO', '').replace(marca, '', 1).strip(' :-')
                    break
        filas.append([Paragraph(str(n), tdc), Paragraph(esc(norma_h), tdc), Paragraph(esc(req_h), tdc),
                      Paragraph(esc(getattr(h, 'descripcion', '')), td),
                      Paragraph(_TIPOS_HALLAZGO_LBL.get(getattr(h, 'tipo', ''), ''), tdc)])
    while len(filas) < 4:
        filas.append(['', '', '', '', ''])
    anchos = [35.45, 70.9, 77.7, 219.95, 97.0]
    tot = sum(anchos)
    res = Table(filas, colWidths=[W * x / tot for x in anchos], repeatRows=1)
    res.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), azul),
                             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white]),
                             ('TOPPADDING', (0, 1), (-1, -1), 3), ('BOTTOMPADDING', (0, 1), (-1, -1), 3)]))
    story.append(res)
    story.append(Paragraph('(*) No conformidad, Observación y oportunidad de mejora', nota))

    # 7. Conclusiones
    story.append(Paragraph('7.&nbsp;&nbsp;CONCLUSIONES DE LA AUDITORÍA', h1)); story += texto(getattr(a, 'conclusiones', ''), txt1)

    # 8. Nombre, fecha y firma del auditor líder (el título no se separa de la firma)
    titulo8 = Paragraph('8.&nbsp;&nbsp;NOMBRE, FECHA Y FIRMA DEL AUDITOR LÍDER', h1)
    lider = _nombre_lider(a)
    firma = Table([[''], ['']], colWidths=[W * 0.48], rowHeights=[22 * mm, 2])
    firma.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 0.7, colors.black)]))
    firma.hAlign = 'CENTER'
    datos_f = Table([[Paragraph('Nombre:', fbl), Paragraph(esc(lider), val)],
                     [Paragraph('Fecha:', fbl), Paragraph(_f(fecha_informe), val)]],
                    colWidths=[W * 0.15, W * 0.33])
    datos_f.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
    datos_f.hAlign = 'CENTER'
    from reportlab.platypus import KeepTogether
    story.append(KeepTogether([titulo8, firma, datos_f]))
    doc.build(story, onFirstPage=_pagina, onLaterPages=_pagina)
    return buf.getvalue()


def lblw_(_colors):
    return ParagraphStyle('iflblw', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=_colors.white)


class _TextoVertical(Flowable):
    """Texto girado 90° (rótulos de meses del programa anual, como en el Excel)."""

    def __init__(self, texto, fuente='Helvetica-Bold', tam=6.5, color=colors.white):
        super().__init__()
        self.texto, self.fuente, self.tam, self.color = texto, fuente, tam, color

    def wrap(self, aw, ah):
        self._aw, self._ah = aw, ah
        return aw, ah

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.color)
        c.setFont(self.fuente, self.tam)
        c.translate(self._aw / 2 + self.tam * 0.35, self._ah / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, self.texto)
        c.restoreState()


def generar_programa_anual_pdf(programa) -> bytes:
    """Programa anual de auditorías con la grilla del formato en Excel: bloques
    de elaborado/aprobado por, leyenda de colores, cuatro columnas de normas,
    proceso, estado (programado / reprogramado / ejecutado), doce meses con el
    nombre en vertical y observaciones. Se completan bloques vacíos hasta
    llenar la hoja, como el formato impreso."""
    from reportlab.lib.pagesizes import landscape
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=8 * mm, bottomMargin=8 * mm, title='Programa anual de auditorías')
    W = doc.width
    cfg = _cargar_cfg()
    azul = colors.HexColor('#16365C')
    COLOR_INTERNA = colors.HexColor('#9DB9DC')   # azul de la leyenda del formato
    COLOR_EXTERNA = colors.HexColor('#F2B233')   # ámbar de la leyenda del formato
    k = 0.67
    rh = lambda pt: pt * k
    f = 6.6
    lbl = ParagraphStyle('pglbl', fontName='Helvetica-Bold', fontSize=f, leading=f * 1.15, textColor=colors.white, alignment=TA_CENTER)
    td = ParagraphStyle('pgtd', fontName='Helvetica', fontSize=f, leading=f * 1.2)
    tdc = ParagraphStyle('pgtdc', parent=td, alignment=TA_CENTER)
    tdb = ParagraphStyle('pgtdb', fontName='Helvetica-Bold', fontSize=f, leading=f * 1.2, alignment=TA_CENTER)
    anio = getattr(programa, 'anio', '') or ''

    # Columnas del Excel en unidades (A=3,6; resto 13): normas A:D, E:H, I:L, M:P;
    # proceso Q:U; estado V:AA; meses de 2 columnas AB:AY; observaciones AZ:BF.
    unidades = [4, 4, 4, 4, 5, 6] + [2] * 12 + [7]
    tot = float(sum(unidades))
    cw = [W * u / tot for u in unidades]
    U = lambda u: W * u / tot

    story = [_cabecera_met12(W, 'PROGRAMA ANUAL DE AUDITORÍAS', COD_PROGRAMA_ANUAL, cfg), Spacer(1, rh(7.5))]

    # Elaborado / aprobado por (A:I + J:S), fechas (V:AD + AE:AJ) y leyenda (AN:AU + color, AX:BE + color)
    f_elab = getattr(programa, 'created_at', None)
    f_apro = getattr(programa, 'fecha_aprobacion', None)
    enc_cols = [U(9), U(10), U(2), U(9), U(6), U(3), U(8), U(1), U(2), U(8), U(1)]
    enc = Table([
        [Paragraph('ELABORADO POR', lbl), Paragraph(_nom_u(getattr(programa, 'created_by', None)), td), '',
         Paragraph('FECHA DE ELABORACIÓN', lbl), Paragraph(_f(f_elab.date()) if f_elab else '', tdc), '',
         Paragraph('AUDITORÍA INTERNA', tdc), '', '', Paragraph('AUDITORÍA EXTERNA', tdc), ''],
        [''] * 11,
        [Paragraph('APROBADO POR', lbl), Paragraph(_nom_u(getattr(programa, 'aprobado_por', None)), td), '',
         Paragraph('FECHA DE APROBACIÓN', lbl), Paragraph(_f(f_apro.date()) if f_apro else '', tdc), '', '', '', '', '', ''],
    ], colWidths=enc_cols, rowHeights=[rh(18.75), rh(7.5), rh(18.75)])
    enc.setStyle(TableStyle([
        ('BOX', (0, 0), (1, 0), 0.5, colors.black), ('LINEAFTER', (0, 0), (0, 0), 0.5, colors.black),
        ('BOX', (3, 0), (4, 0), 0.5, colors.black), ('LINEAFTER', (3, 0), (3, 0), 0.5, colors.black),
        ('BOX', (0, 2), (1, 2), 0.5, colors.black), ('LINEAFTER', (0, 2), (0, 2), 0.5, colors.black),
        ('BOX', (3, 2), (4, 2), 0.5, colors.black), ('LINEAFTER', (3, 2), (3, 2), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, 0), azul), ('BACKGROUND', (3, 0), (3, 0), azul),
        ('BACKGROUND', (0, 2), (0, 2), azul), ('BACKGROUND', (3, 2), (3, 2), azul),
        ('BOX', (6, 0), (7, 0), 0.5, colors.black), ('LINEAFTER', (6, 0), (6, 0), 0.5, colors.black), ('BACKGROUND', (7, 0), (7, 0), COLOR_INTERNA),
        ('BOX', (9, 0), (10, 0), 0.5, colors.black), ('LINEAFTER', (9, 0), (9, 0), 0.5, colors.black), ('BACKGROUND', (10, 0), (10, 0), COLOR_EXTERNA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    story.append(enc)
    rev = getattr(programa, 'revision', 0) or 0
    if rev:
        f_mod = getattr(programa, 'fecha_modificacion', None)
        txt = f'Revisión {rev} del programa'
        quien = _nom_u(getattr(programa, 'modificado_por', None))
        if quien or f_mod:
            txt += ' — modificado' + (f' por {quien}' if quien else '') + (f' el {_f(f_mod.date())}' if f_mod else '')
        if getattr(programa, 'motivo_modificacion', ''):
            txt += f': {programa.motivo_modificacion}'
        story.append(Paragraph(txt, ParagraphStyle('pgrev', fontName='Helvetica-Oblique', fontSize=6.5, leading=8)))
    story.append(Spacer(1, rh(7.5)))

    NORMAS_COL = [('iso_9001', 'ISO 9001:2015'), ('iso_14001', 'ISO 14001:2015'),
                  ('iso_45001', 'ISO 45001:2018'), ('iso_17025', 'NTP ISO/IEC 17025:2017')]
    MESES = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SETIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
    fila0 = [Paragraph('NORMA Y REQUISITOS A AUDITAR', lbl), '', '', '', Paragraph('PROCESO A AUDITAR', lbl),
             Paragraph(str(anio), lbl)] + [''] * 12 + [Paragraph('OBSERVACIONES', lbl)]
    fila1 = [Paragraph(n, lbl) for _, n in NORMAS_COL] + ['', Paragraph('ESTADO', lbl)] + \
            [_TextoVertical(m, tam=f - 0.6) for m in MESES] + ['']
    filas = [fila0, fila1]
    alturas = [rh(15.75), rh(75)]
    estilos = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 1), azul),
               ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
               ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
               ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
               ('SPAN', (0, 0), (3, 0)), ('SPAN', (4, 0), (4, 1)), ('SPAN', (5, 0), (17, 0)), ('SPAN', (18, 0), (18, 1))]
    auds = [a for a in (getattr(programa, 'auditorias').all() if hasattr(programa, 'auditorias') else []) if getattr(a, 'is_active', True)]
    bloques = max(9, len(auds))   # bloques preimpresos: llenan la primera hoja
    for n in range(bloques):
        ai = auds[n] if n < len(auds) else None
        reqs = (getattr(ai, 'requisitos_por_norma', None) or {}) if ai else {}
        color = COLOR_EXTERNA if (ai and getattr(ai, 'clase', 'interna') == 'externa') else COLOR_INTERNA
        fi = getattr(ai, 'fecha_inicio', None) if ai else None
        estados = [('PROGRAMADO', getattr(ai, 'mes_programado', None) if ai else None),
                   ('REPROGRAMADO', getattr(ai, 'mes_reprogramado', None) if ai else None),
                   ('EJECUTADO', fi.month if fi else None)]
        base = len(filas)
        for idx, (etq, mes_x) in enumerate(estados):
            if idx == 0 and ai:
                fila = [Paragraph(str(reqs.get(k_, '') or ''), tdc) for k_, _ in NORMAS_COL] + \
                       [Paragraph(getattr(ai, 'areas_procesos', '') or '', tdc), Paragraph(etq, tdb)] + [''] * 12 + \
                       [Paragraph(getattr(ai, 'observaciones_programa', '') or '', td)]
            else:
                fila = ['', '', '', '', '', Paragraph(etq, tdb)] + [''] * 12 + ['']
            filas.append(fila)
            alturas.append(rh(18.75) if not (idx == 0 and ai) else None)
            if mes_x and 1 <= mes_x <= 12:
                estilos.append(('BACKGROUND', (5 + mes_x, len(filas) - 1), (5 + mes_x, len(filas) - 1), color))
        for c in (0, 1, 2, 3, 4, 18):
            estilos.append(('SPAN', (c, base), (c, base + 2)))
    t = Table(filas, colWidths=cw, rowHeights=alturas, repeatRows=2)
    t.setStyle(TableStyle(estilos))
    story.append(t)
    doc.build(story)
    return buf.getvalue()


# ============================================================
# ACCIONES CORRECTIVAS — Solicitud y Seguimiento
# ============================================================

GRIS_ETIQUETA = colors.HexColor('#BFBFBF')     # celdas de etiqueta del formato (blanco al 75 %)


def esc_pdf(t):
    return (str(t if t is not None else '').replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('\n', '<br/>'))


def _p_ajustado(texto, estilo, ancho, minimo=4.6, una_linea=False, relleno=5):
    """Párrafo cuyo tamaño de letra se reduce lo necesario para que ninguna
    palabra se parta (o, con `una_linea`, para que todo entre en una línea) en
    las casillas angostas del formato. `relleno`: márgenes internos de la celda."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    texto = str(texto or '')
    fs = estilo.fontSize
    util = max(ancho - relleno, 1)
    palabras = [texto] if una_linea else (texto.split() or [''])
    mayor = max(stringWidth(w, estilo.fontName, fs) for w in palabras)
    if mayor > util:
        fs = max(minimo, fs * util / mayor)
    if fs == estilo.fontSize:
        return Paragraph(esc_pdf(texto), estilo)
    st = ParagraphStyle(f'{estilo.name}_{fs:.2f}', parent=estilo, fontSize=fs, leading=fs * 1.15)
    return Paragraph(esc_pdf(texto), st)


def _solo_fecha(v):
    """Fecha sin hora (las fechas de cierre y verificación son fecha y hora)."""
    if not v:
        return ''
    if hasattr(v, 'hour') and hasattr(v, 'date'):
        v = v.date()
    return _f(v)


def _logo_celda(cfg, ancho, alto):
    empresa = ''
    try:
        empresa = empresa_nombre(cfg, vacio='')
    except Exception:
        pass
    celda = Paragraph(empresa or 'EMPRESA', ParagraphStyle('sclogo', fontName='Helvetica-Bold', fontSize=8,
                                                           leading=10, alignment=TA_CENTER))
    try:
        _logo = (getattr(cfg, 'logo_empresa', None) or getattr(cfg, 'logo', None)) if cfg else None
        if _logo and _logo.path:
            im = Image(_logo.path)
            r = min(ancho / im.imageWidth, alto / im.imageHeight)
            im.drawWidth = im.imageWidth * r
            im.drawHeight = im.imageHeight * r
            im.hAlign = 'CENTER'
            celda = im
    except Exception:
        pass
    return celda


class _Grilla35:
    """Hoja de 35 columnas iguales (A a AI), como la plantilla en Excel de la
    Solicitud de Acción Correctiva. Cada fila se arma con tramos de columnas:
    etiqueta gris ('lbl'/'hdr'), casilla ('box', 'boxb' en negrita, 'boxl'
    con texto), franja azul ('band') o recuadro de texto a todo el ancho."""

    def __init__(self, W, fs):
        self.cw = [W / 35.0] * 35
        self.filas, self.altos, self.est, self.minimos = [], [], [], []
        self.lbl = ParagraphStyle('sclbl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
        self.val = ParagraphStyle('scval', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER)
        self.valb = ParagraphStyle('scvalb', parent=self.val, fontName='Helvetica-Bold')
        self.txt = ParagraphStyle('sctxt', fontName='Helvetica', fontSize=fs, leading=fs * 1.3)
        self.band = ParagraphStyle('scband', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2,
                                   textColor=colors.white)

    def espacio(self, alto):
        self.filas.append([''] * 35)
        self.altos.append(alto)

    def fila(self, alto, tramos):
        r = len(self.filas)
        fila = [''] * 35
        for a, b, cont, tipo in tramos:
            i, j = _col_idx(a), _col_idx(b)
            if isinstance(cont, str):
                estilo = {'lbl': self.lbl, 'hdr': self.lbl, 'band': self.band, 'boxb': self.valb}.get(tipo, self.val)
                cont = (Paragraph(esc_pdf(cont), estilo) if tipo == 'band'
                        else _p_ajustado(cont, estilo, sum(self.cw[i:j + 1]), una_linea=alto is not None))
            fila[i] = cont
            if j > i:
                self.est.append(('SPAN', (i, r), (j, r)))
            self.est.append(('BOX', (i, r), (j, r), 0.6, colors.black))
            if tipo in ('lbl', 'hdr'):
                self.est.append(('BACKGROUND', (i, r), (j, r), GRIS_ETIQUETA))
            if tipo == 'band':
                self.est.append(('BACKGROUND', (i, r), (j, r), AZUL_LISTA))
        self.filas.append(fila)
        self.altos.append(alto)

    def recuadro(self, alto_min, flowables):
        """Recuadro de texto a todo el ancho (A a AI); crece con el contenido."""
        r = len(self.filas)
        self.filas.append([flowables] + [''] * 34)
        self.altos.append(alto_min)
        self.est += [('SPAN', (0, r), (34, r)), ('BOX', (0, r), (34, r), 0.6, colors.black),
                     ('VALIGN', (0, r), (34, r), 'TOP'), ('TOPPADDING', (0, r), (34, r), 3)]
        self.minimos.append((r, alto_min))

    def tabla(self):
        ancho = sum(self.cw) - 6
        for r, minimo in self.minimos:
            alto = sum(p.wrap(ancho, 2000)[1] for p in self.filas[r][0]) + 8
            self.altos[r] = max(minimo, alto)
        t = Table(self.filas, colWidths=self.cw, rowHeights=self.altos)
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                               ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]
                              + self.est))
        return t


def _cabecera_sac(W, titulo, codigo, cfg, alto_fila, fs, titulo_fs):
    """Encabezado de la Solicitud: logo (A-D), título (E-AC) y caja de control
    (AD-AI: código, versión, fecha; elaborado, revisión y aprobado)."""
    _c = control_formato(codigo, cfg)
    u = W / 35.0
    lb = ParagraphStyle('schl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    vl = ParagraphStyle('schv', fontName='Helvetica', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    tit = ParagraphStyle('scht', fontName='Helvetica-Bold', fontSize=titulo_fs, leading=titulo_fs * 1.2,
                         alignment=TA_CENTER)
    a3, a2 = u * 3, u * 2
    data = [
        [_logo_celda(cfg, u * 4 - 6, alto_fila * 5 - 6), Paragraph(titulo, tit),
         _p_ajustado('Código:', lb, a3), '', '', _p_ajustado(_c['codigo'], vl, a3), '', ''],
        ['', '', _p_ajustado('Versión:', lb, a3), '', '', _p_ajustado(_c['version'], vl, a3), '', ''],
        ['', '', _p_ajustado('Fecha:', lb, a3), '', '', _p_ajustado(_c['fecha'], vl, a3), '', ''],
        ['', '', _p_ajustado('Elaborado:', lb, a2), '', _p_ajustado('Revisión:', lb, a2), '',
         _p_ajustado('Aprobado:', lb, a2), ''],
        ['', '', _p_ajustado(_c['elaborado'], vl, a2), '', _p_ajustado(_c['revisado'], vl, a2), '',
         _p_ajustado(_c['aprobado'], vl, a2), ''],
    ]
    t = Table(data, colWidths=[u * 4, u * 25] + [u] * 6, rowHeights=[alto_fila] * 5)
    est = [('BOX', (0, 0), (0, 4), 0.6, colors.black), ('BOX', (1, 0), (1, 4), 0.6, colors.black),
           ('GRID', (2, 0), (7, 4), 0.6, colors.black),
           ('SPAN', (0, 0), (0, 4)), ('SPAN', (1, 0), (1, 4)), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('ALIGN', (0, 0), (0, 4), 'CENTER'),
           ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
           ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]
    for r in range(3):
        est += [('SPAN', (2, r), (4, r)), ('SPAN', (5, r), (7, r))]
    for r in (3, 4):
        est += [('SPAN', (2, r), (3, r)), ('SPAN', (4, r), (5, r)), ('SPAN', (6, r), (7, r))]
    t.setStyle(TableStyle(est))
    return t


def _nombre_usuario(u):
    return (u.get_full_name() or u.username) if u else ''


def _lineas_porques(porques, estilo):
    """Cadena de porqués: «n. ¿pregunta?» y su respuesta. Acepta pares
    pregunta/respuesta o textos sueltos (registros anteriores)."""
    out = []
    for n, pq in enumerate(porques or [], 1):
        if isinstance(pq, dict):
            preg = esc_pdf(pq.get('pregunta') or '¿Por qué?')
            out.append(Paragraph(f'<b>{n}. {preg}</b> {esc_pdf(pq.get("respuesta", ""))}', estilo))
        else:
            out.append(Paragraph(f'{n}. ¿Por qué? {esc_pdf(pq)}', estilo))
    return out


def generar_sac_pdf(sac) -> bytes:
    """Solicitud de Acción Correctiva con la grilla de su plantilla (35
    columnas): procedencia, no conformidad, significancia, extensión,
    correcciones, análisis de causa (5 porqués), acciones correctivas,
    eficacia, actualizaciones y conformidad. Los ciclos de análisis no eficaces
    se imprimen antes del vigente."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=8 * mm, rightMargin=8 * mm,
                            topMargin=10 * mm, bottomMargin=10 * mm, title='Solicitud de acción correctiva')
    W = doc.width
    cfg = _cargar_cfg()
    fs = 6.6
    h = 12.5            # fila de 18,75 pt del Excel
    sp = 4.0            # fila espaciadora de 6 pt
    g = _Grilla35(W, fs)
    x = 'X'
    normas = set(getattr(sac, 'normas_aplicables', None) or [])
    fuente = getattr(sac, 'fuente', '')
    ciclo_actual = getattr(sac, 'ciclo', 1) or 1
    ciclos = list(getattr(sac, 'ciclos_anteriores', None) or [])
    acciones = list(sac.acciones.filter(is_active=True).order_by('ciclo', 'fecha_propuesta', 'id')) \
        if hasattr(sac, 'acciones') else []

    g.fila(h, [('F', 'J', 'Fecha de Registro', 'lbl'),
               ('K', 'N', _solo_fecha(getattr(sac, 'fecha_registro', None) or getattr(sac, 'created_at', None)), 'box'),
               ('V', 'Z', 'N° de Registro', 'lbl'), ('AA', 'AD', getattr(sac, 'codigo', ''), 'boxb')])
    g.espacio(sp)
    g.fila(h, [('A', 'AI', '1. PROCEDENCIA', 'band')])
    g.espacio(sp)
    g.fila(h, [('E', 'G', 'ISO 9001:2015', 'lbl'), ('H', 'H', x if 'iso_9001' in normas else '', 'boxb'),
               ('L', 'N', 'ISO 14001:2015', 'lbl'), ('O', 'O', x if 'iso_14001' in normas else '', 'boxb'),
               ('S', 'U', 'ISO 45001:2018', 'lbl'), ('V', 'V', x if 'iso_45001' in normas else '', 'boxb'),
               ('Z', 'AC', 'NTP-ISO/IEC 17025:2017', 'lbl'), ('AD', 'AD', x if 'iso_17025' in normas else '', 'boxb')])
    g.espacio(sp)
    g.espacio(sp)
    g.fila(h, [('C', 'E', 'Auditoría Interna', 'lbl'), ('F', 'F', x if fuente == 'auditoria_interna' else '', 'boxb'),
               ('I', 'K', 'Auditoría Externa', 'lbl'), ('L', 'L', x if fuente == 'auditoria_externa' else '', 'boxb'),
               ('O', 'R', 'Revisión por la Dirección', 'lbl'),
               ('S', 'S', x if fuente == 'revision_direccion' else '', 'boxb'),
               ('V', 'W', 'Queja', 'lbl'), ('X', 'X', x if fuente == 'queja' else '', 'boxb'),
               ('AA', 'AC', 'Otros', 'lbl'), ('AD', 'AD', x if fuente == 'otros' else '', 'boxb')])
    g.fila(h, [('AA', 'AC', 'Detallar', 'lbl'), ('AD', 'AG', getattr(sac, 'fuente_detalle', ''), 'box')])
    g.espacio(sp)
    g.fila(h, [('F', 'J', 'Personal/Entidad Auditor(a):', 'lbl'),
               ('K', 'P', getattr(sac, 'entidad_auditora', ''), 'box'),
               ('U', 'X', 'Requisito Auditado:', 'lbl'), ('Y', 'AD', getattr(sac, 'requisito_auditado', ''), 'box')])
    g.espacio(sp)
    g.fila(h, [('F', 'J', 'Auditor:', 'lbl'), ('K', 'P', getattr(sac, 'auditor', ''), 'box'),
               ('U', 'X', 'Auditado:', 'lbl'), ('Y', 'AD', getattr(sac, 'auditado', ''), 'box')])
    g.espacio(sp)
    g.fila(h, [('A', 'AI', '2. NO CONFORMIDAD', 'band')])
    g.espacio(sp)
    g.recuadro(h * 3, [Paragraph(esc_pdf(getattr(sac, 'descripcion_nc', '')), g.txt)])
    g.espacio(sp)
    g.fila(h, [('A', 'AI', '3. NIVEL DE SIGNIFICANCIA', 'band')])
    g.espacio(sp)
    sig = getattr(sac, 'significancia', '')
    g.fila(h, [('K', 'L', 'Bajo', 'lbl'), ('M', 'M', x if sig == 'bajo' else '', 'boxb'),
               ('W', 'X', 'Alto', 'lbl'), ('Y', 'Y', x if sig == 'alto' else '', 'boxb')])
    g.espacio(sp)
    g.fila(h, [('A', 'AI', '4. ANÁLISIS DE LA EXTENSIÓN DE LA NO CONFORMIDAD', 'band')])
    g.espacio(sp)
    g.recuadro(h * 3, [Paragraph(esc_pdf(getattr(sac, 'analisis_extension', '')), g.txt)])
    g.espacio(sp)

    def tabla_acciones(titulo_seccion, encabezado, lista):
        g.fila(h, [('A', 'AI', titulo_seccion, 'band')])
        g.espacio(sp)
        g.fila(h, [('A', 'N', encabezado, 'hdr'), ('O', 'R', 'FECHA PROPUESTA', 'hdr'),
                   ('S', 'U', 'RESPONSABLE', 'hdr'), ('V', 'AI', 'VERIFICACIÓN', 'hdr')])
        for i in range(max(2, len(lista))):
            a = lista[i] if i < len(lista) else None
            if a is None:
                g.fila(h, [('A', 'N', '', 'box'), ('O', 'R', '', 'box'), ('S', 'U', '', 'box'), ('V', 'AI', '', 'box')])
                continue
            # Solo lo completado (una acción reabierta aún no tiene verificación vigente).
            verif = (a.verificacion or '') if a.estado == 'completada' else ''
            if a.fecha_completada:
                verif = f'{_f(a.fecha_completada)}: {verif}' if verif else _f(a.fecha_completada)
            desc = a.descripcion if ciclo_actual == 1 else f'(Ciclo {a.ciclo}) {a.descripcion}'
            g.fila(None, [('A', 'N', Paragraph(esc_pdf(desc), g.txt), 'boxl'), ('O', 'R', _f(a.fecha_propuesta), 'box'),
                          ('S', 'U', _nombre_usuario(a.responsable), 'box'),
                          ('V', 'AI', Paragraph(esc_pdf(verif), g.txt), 'boxl')])
        g.espacio(sp)

    tabla_acciones('5. CORRECCIÓN (SOLO PARA CASOS QUE APLIQUE)', 'CORRECCIONES',
                   [a for a in acciones if a.tipo == 'correccion'])

    # 6. Análisis de causa (solo la cadena de porqués) y 7. Causa raíz, aparte.
    porques_vig = list(getattr(sac, 'porques', None) or [])
    causa_vig = (getattr(sac, 'causa_raiz', '') or '').strip()
    anterior = ciclos[-1] if ciclos else None
    porques_iguales = bool(anterior) and porques_vig == list(anterior.get('porques') or [])
    causa_igual = bool(anterior) and causa_vig == (anterior.get('causa_raiz') or '').strip()

    g.fila(h, [('A', 'AI', '6. ANÁLISIS DE CAUSA (5 PORQUÉ)', 'band')])
    g.espacio(sp)
    parrafos = []
    for c in ciclos:
        parrafos.append(Paragraph(f'<b>Ciclo {c.get("ciclo")} (no eficaz):</b>', g.txt))
        parrafos += _lineas_porques(c.get('porques'), g.txt)
    if ciclos:
        if porques_iguales and porques_vig:
            # Revisado el análisis, se confirmó la misma cadena: no se repite.
            parrafos.append(Paragraph(f'<b>Ciclo {ciclo_actual}:</b> se revisó y se confirma el análisis del '
                                      f'ciclo {anterior.get("ciclo")}.', g.txt))
        elif not porques_vig:
            parrafos.append(Paragraph(f'<b>Ciclo {ciclo_actual}:</b> pendiente.', g.txt))
        else:
            parrafos.append(Paragraph(f'<b>Ciclo {ciclo_actual}:</b>', g.txt))
    if not (ciclos and porques_iguales):
        parrafos += _lineas_porques(porques_vig, g.txt)
    g.recuadro(h * 3, parrafos or [Paragraph('', g.txt)])
    g.espacio(sp)

    g.fila(h, [('A', 'AI', '7. CAUSA RAÍZ', 'band')])
    g.espacio(sp)
    parrafos = [Paragraph(f'<b>Ciclo {c.get("ciclo")} (no eficaz):</b> {esc_pdf(c.get("causa_raiz", ""))}', g.txt)
                for c in ciclos]
    if ciclos:
        if causa_igual and causa_vig:
            texto = f'se confirma la causa raíz del ciclo {anterior.get("ciclo")}.'
        else:
            texto = esc_pdf(causa_vig) or 'pendiente.'
        parrafos.append(Paragraph(f'<b>Ciclo {ciclo_actual}:</b> {texto}', g.txt))
    elif causa_vig:
        parrafos.append(Paragraph(esc_pdf(causa_vig), g.txt))
    g.recuadro(h * 2, parrafos or [Paragraph('', g.txt)])
    g.espacio(sp)

    tabla_acciones('8. ACCIONES CORRECTIVAS', 'ACCIONES CORRECTIVAS', [a for a in acciones if a.tipo == 'correctiva'])

    g.fila(h, [('A', 'AI', '9. EVALUACIÓN DE LA EFICACIA', 'band')])
    g.espacio(sp)
    g.fila(h, [('A', 'AA', 'EVALUACIÓN', 'hdr'), ('AB', 'AE', 'FECHA', 'hdr'), ('AF', 'AI', 'RESPONSABLE', 'hdr')])
    evals = [(f'(Ciclo {c.get("ciclo")}, no eficaz) {c.get("evaluacion", "")}', (c.get('fecha') or '')[:10],
              c.get('verificado_por', '')) for c in ciclos]
    if getattr(sac, 'estado', '') == 'cerrada_conforme' and getattr(sac, 'evaluacion_eficacia', ''):
        evals.append((sac.evaluacion_eficacia, _solo_fecha(sac.fecha_verificacion), _verificador_real(sac)))
    for i in range(max(2, len(evals))):
        e = evals[i] if i < len(evals) else ('', '', '')
        g.fila(None if e[0] else h, [('A', 'AA', Paragraph(esc_pdf(e[0]), g.txt), 'boxl'), ('AB', 'AE', e[1], 'box'),
                                     ('AF', 'AI', e[2], 'box')])
    g.espacio(sp)

    g.fila(h, [('A', 'AI', '10. ACTUALIZACIONES Y CAMBIOS', 'band')])
    g.espacio(sp)
    g.fila(h, [('B', 'Q', '¿APLICA CAMBIOS AL SIG?', 'lbl'),
               ('S', 'AH', '¿APLICA ACTUALIZAR LA MATRIZ DE RIESGOS Y OPORTUNIDADES?', 'lbl')])
    g.espacio(sp)
    cs, ar = getattr(sac, 'aplica_cambios_sig', None), getattr(sac, 'aplica_actualizar_riesgos', None)
    g.fila(h, [('F', 'F', 'SI', 'lbl'), ('G', 'G', x if cs is True else '', 'boxb'),
               ('K', 'K', 'NO', 'lbl'), ('L', 'L', x if cs is False else '', 'boxb'),
               ('X', 'X', 'SI', 'lbl'), ('Y', 'Y', x if ar is True else '', 'boxb'),
               ('AC', 'AC', 'NO', 'lbl'), ('AD', 'AD', x if ar is False else '', 'boxb')])
    g.espacio(sp)
    g.fila(h, [('A', 'AI', '11. CONFORMIDAD', 'band')])
    g.espacio(sp)
    estado = getattr(sac, 'estado', '')
    conforme = estado in ('cerrada_conforme', 'cerrada_sin_ac')
    no_conforme = not conforme and bool(ciclos)
    g.fila(h, [('J', 'L', 'CONFORME', 'lbl'), ('M', 'M', x if conforme else '', 'boxb'),
               ('W', 'Y', 'NO CONFORME', 'lbl'), ('Z', 'Z', x if no_conforme else '', 'boxb')])
    g.espacio(sp)
    resp_cierre = responsable_cierre_sac(sac)
    g.fila(h, [('H', 'J', 'Fecha de Cierre:', 'lbl'), ('K', 'P', _solo_fecha(getattr(sac, 'fecha_cierre', None)), 'box'),
               ('T', 'V', 'Responsable:', 'lbl'), ('W', 'AB', resp_cierre, 'box')])

    story = [_cabecera_sac(W, 'SOLICITUD DE ACCIÓN CORRECTIVA', COD_SAC, cfg, h, fs, 15), Spacer(1, sp), g.tabla()]
    doc.build(story)
    return buf.getvalue()


def _verificador_real(sac):
    """Quien verificó la eficacia; en solicitudes anteriores a ese registro, el designado."""
    return _nombre_usuario(getattr(sac, 'verificado_por', None) or getattr(sac, 'verificador', None))


def responsable_cierre_sac(sac):
    """Responsable del cierre (conformidad): quien verificó la eficacia o, si solo
    requería corrección, el responsable de la implementación."""
    estado = getattr(sac, 'estado', '')
    if estado == 'cerrada_conforme':
        return _verificador_real(sac)
    if estado == 'cerrada_sin_ac':
        return _nombre_usuario(getattr(sac, 'responsable', None))
    return ''


def generar_seguimiento_sac_pdf(solicitudes, fecha_actualizacion=None) -> bytes:
    """Seguimiento a Solicitudes de Acciones Correctivas y No Conformidades,
    con las columnas de su plantilla: N° de solicitud, procedencia,
    descripción, responsable de la implementación, estado, fecha de cierre y
    clasificación."""
    import datetime as _dt
    buf = BytesIO()
    # Horizontal: con letra Arial 11 en toda la tabla (decisión de César), las
    # columnas de la hoja vertical no alcanzan para estados y fechas.
    from reportlab.lib.pagesizes import landscape
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=10 * mm, bottomMargin=10 * mm, title='Seguimiento de acciones correctivas')
    W = doc.width
    cfg = _cargar_cfg()
    proporcion = [92, 98, 216, 112, 92, 74, 101]
    cw = [W * a / sum(proporcion) for a in proporcion]
    fs = 7.2          # caja de control del encabezado
    ft = 11           # tabla: un solo tamaño (Arial 11; Helvetica tiene las mismas medidas)
    h = 13.0
    th = ParagraphStyle('ssth', fontName='Helvetica-Bold', fontSize=ft, leading=ft * 1.2, alignment=TA_CENTER,
                        textColor=colors.white)
    tdc = ParagraphStyle('sstdc', fontName='Helvetica', fontSize=ft, leading=ft * 1.2, alignment=TA_CENTER)
    td = ParagraphStyle('sstd', parent=tdc, alignment=TA_LEFT)
    tdb = ParagraphStyle('sstdb', parent=tdc, fontName='Helvetica-Bold')
    # Encabezado: logo (A), título (B a D) y control (E a G), en el orden de la
    # plantilla: código, fecha, versión.
    _c = control_formato(COD_SEGUIMIENTO_SAC, cfg)
    lb = ParagraphStyle('ssl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    vl = ParagraphStyle('ssv', fontName='Helvetica', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    tt = ParagraphStyle('sst', fontName='Helvetica-Bold', fontSize=12, leading=14.5, alignment=TA_CENTER)
    cab = [
        [_logo_celda(cfg, cw[0] - 6, h * 5 - 6),
         Paragraph('SEGUIMIENTO A SOLICITUDES DE ACCIONES CORRECTIVAS Y NO CONFORMIDADES', tt), '', '',
         Paragraph('Código:', lb), Paragraph(esc_pdf(_c['codigo']), vl), ''],
        ['', '', '', '', Paragraph('Fecha:', lb), Paragraph(esc_pdf(_c['fecha']), vl), ''],
        ['', '', '', '', Paragraph('Versión:', lb), Paragraph(esc_pdf(_c['version']), vl), ''],
        ['', '', '', '', _p_ajustado('Elaborado:', lb, cw[4], relleno=13), _p_ajustado('Revisado:', lb, cw[5], relleno=13),
         _p_ajustado('Aprobado:', lb, cw[6], relleno=13)],
        ['', '', '', '', _p_ajustado(_c['elaborado'], vl, cw[4], relleno=13), _p_ajustado(_c['revisado'], vl, cw[5], relleno=13),
         _p_ajustado(_c['aprobado'], vl, cw[6], relleno=13)],
    ]
    tc = Table(cab, colWidths=cw, rowHeights=[h] * 5)
    tc.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 4), 0.6, colors.black), ('BOX', (1, 0), (3, 4), 0.6, colors.black),
        ('GRID', (4, 0), (6, 4), 0.6, colors.black),
        ('SPAN', (0, 0), (0, 4)), ('SPAN', (1, 0), (3, 4)),
        ('SPAN', (5, 0), (6, 0)), ('SPAN', (5, 1), (6, 1)), ('SPAN', (5, 2), (6, 2)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (0, 4), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    fa = Table([[Paragraph('FECHA DE ACTUALIZACIÓN', th), '',
                 Paragraph(_f(fecha_actualizacion or _dt.date.today()), tdb), '', '', '', '']],
               colWidths=cw, rowHeights=[ft * 1.9])
    fa.setStyle(TableStyle([('SPAN', (0, 0), (1, 0)), ('SPAN', (2, 0), (6, 0)),
                            ('BACKGROUND', (0, 0), (1, 0), AZUL_LISTA),
                            ('BOX', (0, 0), (1, 0), 0.6, colors.black), ('BOX', (2, 0), (6, 0), 0.6, colors.black),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    filas = [[Paragraph(t, th) for t in (
        'N° SOLICITUD DE ACCIÓN CORRECTIVA', 'PROCEDENCIA', 'DESCRIPCIÓN', 'RESPONSABLE DE LA IMPLEMENTACIÓN',
        'ESTADO', 'FECHA DE CIERRE', 'CLASIFICACIÓN (AC)')]]
    altos = [None]
    for s_ in solicitudes:
        proc = s_.get_fuente_display()
        if getattr(s_, 'fuente_detalle', ''):
            proc = f'{proc}: {s_.fuente_detalle}'
        filas.append([Paragraph(esc_pdf(s_.codigo), tdb), Paragraph(esc_pdf(proc), tdc),
                      Paragraph(esc_pdf(s_.descripcion_nc), td),
                      Paragraph(esc_pdf(_nombre_usuario(getattr(s_, 'responsable', None))), tdc),
                      Paragraph(esc_pdf(s_.get_estado_display()), tdc),
                      Paragraph(esc_pdf(_solo_fecha(s_.fecha_cierre)), tdc),
                      Paragraph(esc_pdf(s_.clasificacion()), tdc)])
        altos.append(None)
    while len(filas) < 10:
        filas.append([''] * 7)
        altos.append(ft * 1.9)
    t = Table(filas, colWidths=cw, rowHeights=altos, repeatRows=1)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.6, colors.black), ('BACKGROUND', (0, 0), (-1, 0), AZUL_LISTA),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    doc.build([tc, Spacer(1, 4.5), fa, Spacer(1, 4.5), t])
    return buf.getvalue()
