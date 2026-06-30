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
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
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
    return d.isoformat() if d else ''


def _anio(d):
    return str(d.year) if d else ''


def _mk(v):
    return 'X' if v else ''


def generar_ficha_pdf(equipo) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=8 * mm, bottomMargin=8 * mm,
        title=f'Hoja de Vida {equipo.codigo}',
    )
    W = doc.width

    lbl = ParagraphStyle('lbl', fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.white)
    val = ParagraphStyle('val', fontName='Helvetica', fontSize=8.5, leading=10)
    valc = ParagraphStyle('valc', parent=val, alignment=TA_CENTER)
    valbig = ParagraphStyle('valbig', fontName='Helvetica-Bold', fontSize=11, leading=13, alignment=TA_CENTER)
    band = ParagraphStyle('band', fontName='Helvetica-Bold', fontSize=9.5, leading=11, alignment=TA_CENTER, textColor=colors.white)
    title = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=18, leading=20, alignment=TA_CENTER)
    name = ParagraphStyle('name', fontName='Helvetica-Bold', fontSize=11, leading=13, alignment=TA_CENTER, textColor=colors.white)
    mini = ParagraphStyle('mini', fontName='Helvetica', fontSize=6.8, leading=8.5)
    minib = ParagraphStyle('minib', fontName='Helvetica-Bold', fontSize=6.8, leading=8.5)
    minic = ParagraphStyle('minic', parent=mini, alignment=TA_CENTER)
    minibc = ParagraphStyle('minibc', parent=minib, alignment=TA_CENTER)
    small = ParagraphStyle('small', fontName='Helvetica', fontSize=7, leading=9, textColor=colors.HexColor('#6B7785'))

    # Marca / logo de la empresa
    cfg = None
    empresa = ''
    try:
        from core.models import ConfiguracionSistema
        cfg = ConfiguracionSistema.cargar()
        empresa = (cfg.subtitulo or cfg.nombre_sistema or '').strip()
    except Exception:
        pass

    # Metadatos del formato: jalan de la lista maestra de Documentos (M6) si está
    # configurado el documento; si no, usan las constantes por defecto.
    codigo_fmt, version_fmt, fecha_fmt = CODIGO_FORMATO, VERSION_FORMATO, FECHA_FORMATO
    elaborado_s, revisado_s, aprobado_s = '', '', ''
    try:
        if cfg:
            elaborado_s = getattr(cfg, 'formato_hv_elaborado', '') or ''
            revisado_s = getattr(cfg, 'formato_hv_revisado', '') or ''
            aprobado_s = getattr(cfg, 'formato_hv_aprobado', '') or ''
            cod = getattr(cfg, 'formato_hv_codigo', '') or ''
            if cod:
                from .models import Documento
                docfmt = Documento.objects.filter(codigo=cod, is_active=True).first()
                if docfmt:
                    codigo_fmt = docfmt.codigo
                    vv = docfmt.version_vigente
                    if vv:
                        version_fmt = vv.version or version_fmt
                        f = vv.fecha_vigencia or vv.fecha_aprobacion
                        if f:
                            fecha_fmt = f.date().isoformat() if hasattr(f, 'date') else f.isoformat()
    except Exception:
        pass
    elaborado_s = elaborado_s or FIRMAS[0][1]
    revisado_s = revisado_s or FIRMAS[1][1]
    aprobado_s = aprobado_s or FIRMAS[2][1]

    story = []

    # ===================== CABECERA =====================
    # Logo (si hay) o nombre de la empresa
    logo_cell = Paragraph(empresa or 'EMPRESA', ParagraphStyle('logo', fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=TA_CENTER))
    try:
        _logo = (getattr(cfg, 'logo_empresa', None) or getattr(cfg, 'logo', None)) if cfg else None
        if _logo and _logo.path:
            im = Image(_logo.path)
            r = min((W * 0.18) / im.imageWidth, (22 * mm) / im.imageHeight)
            im.drawWidth = im.imageWidth * r
            im.drawHeight = im.imageHeight * r
            im.hAlign = 'CENTER'
            logo_cell = im
    except Exception:
        pass

    # Encabezado como UNA sola tabla. La caja derecha usa 6 subcolumnas para que
    # la división etiqueta|valor (50%) caiga en el centro de "Revisado".
    c6 = W * 0.28 / 6.0
    hdr_data = [
        [logo_cell, Paragraph('HOJA DE VIDA', title), Paragraph('Código:', minibc), '', '', Paragraph(codigo_fmt, minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(version_fmt, minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(fecha_fmt, minic), '', ''],
        ['', '', Paragraph('Elaborado', minibc), '', Paragraph('Revisado', minibc), '', Paragraph('Aprobado', minibc), ''],
        ['', '', Paragraph(elaborado_s, minic), '', Paragraph(revisado_s, minic), '', Paragraph(aprobado_s, minic), ''],
    ]
    hdr = Table(hdr_data, colWidths=[W * 0.20, W * 0.52, c6, c6, c6, c6, c6, c6], rowHeights=[4.8 * mm] * 5)
    hdr.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('SPAN', (0, 0), (0, 4)),   # logo
        ('SPAN', (1, 0), (1, 4)),   # título
        ('SPAN', (2, 0), (4, 0)), ('SPAN', (5, 0), (7, 0)),   # Código: etiqueta | valor
        ('SPAN', (2, 1), (4, 1)), ('SPAN', (5, 1), (7, 1)),   # Versión
        ('SPAN', (2, 2), (4, 2)), ('SPAN', (5, 2), (7, 2)),   # Fecha
        ('SPAN', (2, 3), (3, 3)), ('SPAN', (4, 3), (5, 3)), ('SPAN', (6, 3), (7, 3)),   # Elaborado/Revisado/Aprobado
        ('SPAN', (2, 4), (3, 4)), ('SPAN', (4, 4), (5, 4)), ('SPAN', (6, 4), (7, 4)),   # valores de firmas
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 4), 'CENTER'), ('ALIGN', (2, 0), (7, 4), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 4))

    # ===================== NOMBRE DEL EQUIPO + FECHA DE MODIFICACIÓN =====================
    story.append(Table([[Paragraph((equipo.nombre or '').upper(), name)]], colWidths=[W],
                       style=TableStyle([
                           ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
                           ('BACKGROUND', (0, 0), (-1, -1), BANDA),
                           ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                       ])))
    fmod = _f(equipo.updated_at.date() if equipo.updated_at else None)
    story.append(Table([[Paragraph('Fecha de Actualización', lbl), Paragraph(fmod, valc)]],
                       colWidths=[W * 0.30, W * 0.70],
                       style=TableStyle([
                           ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
                           ('BACKGROUND', (0, 0), (0, 0), LABEL),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 4),
                           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                       ])))
    story.append(Spacer(1, 4))

    # ===================== DATOS GENERALES =====================
    story.append(_banda('DATOS GENERALES', W, band))
    filas = []
    for i, (clave, nombre) in enumerate(CLASIFICACIONES):
        clas = 'Clasificación' if i == 0 else ''
        if i == 0:
            rlbl, rval = 'Inicio de Servicio', _anio(equipo.inicio_servicio)
        elif i == 2:
            rlbl, rval = 'Código de Identificación', equipo.codigo
        else:
            rlbl, rval = '', ''
        filas.append([
            Paragraph(clas, lbl), Paragraph(nombre, val),
            Paragraph(_mk(equipo.clasificacion == nombre), valc),
            Paragraph(rlbl, lbl), Paragraph(rval or '', valbig),
        ])
    t = Table(filas, colWidths=[W * 0.16, W * 0.28, W * 0.06, W * 0.26, W * 0.24],
              rowHeights=[9 * mm] * 4)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('SPAN', (0, 0), (0, 3)),
        ('SPAN', (3, 0), (3, 1)), ('SPAN', (4, 0), (4, 1)),   # Inicio de Servicio (label/val) ocupan 2 filas
        ('SPAN', (3, 2), (3, 3)), ('SPAN', (4, 2), (4, 3)),   # Código (label/val) ocupan 2 filas
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, 0), LABEL),
        ('BACKGROUND', (3, 0), (3, 3), LABEL),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 4))

    # ===================== ESPECIFICACIONES TÉCNICAS =====================
    story.append(_banda('ESPECIFICACIONES TÉCNICAS', W, band))

    def lv(label, value):
        return [Paragraph(label, lbl), Paragraph(str(value or ''), valc)]

    grid = [
        lv('Marca', equipo.marca) + lv('Modelo', equipo.modelo),
        lv('Nº de Serie', equipo.serie) + lv('Procedencia', equipo.procedencia),
        lv('Tipo de Indicación', equipo.tipo_indicacion) + lv('Ubicación', equipo.laboratorio),
        lv('Alcance / Valor Nominal', equipo.cantidad) + lv('Resolución / División de Escala (d) / Verificación (e)', equipo.resolucion),
        lv('Clase de Exactitud', equipo.clase_exactitud) + lv('Cantidad', equipo.cantidad_unidades),
        lv('Material', equipo.material) + lv('Estado', equipo.get_estado_display()),
        lv('Instructivo', _mk(equipo.instructivo)) + lv('Manual', _mk(equipo.manual)),
    ]
    te = Table(grid, colWidths=[W * 0.16, W * 0.34, W * 0.26, W * 0.24])
    te.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, -1), LABEL), ('BACKGROUND', (2, 0), (2, -1), LABEL),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(te)
    story.append(Table(
        [[Paragraph('Criterio de Aceptación', lbl), Paragraph(equipo.criterio_aceptacion or '', val)]],
        colWidths=[W * 0.16, W * 0.84], rowHeights=[10 * mm],
        style=TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
            ('BACKGROUND', (0, 0), (0, 0), LABEL),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4), ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]),
    ))

    # Foto del equipo (grande, centrada)
    try:
        if equipo.imagen and equipo.imagen.path:
            story.append(Spacer(1, 8))
            img = Image(equipo.imagen.path)
            r = min((W * 0.7) / img.imageWidth, (90 * mm) / img.imageHeight)
            img.drawWidth = img.imageWidth * r
            img.drawHeight = img.imageHeight * r
            img.hAlign = 'CENTER'
            marco = Table([[img]], colWidths=[img.drawWidth + 8])
            marco.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.8, LINEA),
                ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            marco.hAlign = 'CENTER'
            story.append(marco)
    except Exception:
        pass

    doc.build(story)
    return buf.getvalue()


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


def generar_bitacora_pdf(equipo, tipo, titulo, registros) -> bytes:
    """PDF de una bitácora de la Hoja de Vida (mismo encabezado que la Ficha Técnica)."""
    es_suceso = tipo == 'suceso'
    term = TERMINOS_COL_BIT.get(tipo, 'Actividad')
    titulo_band = TITULOS_BIT.get(tipo, (titulo or 'BITÁCORA').upper())

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=8 * mm, bottomMargin=8 * mm,
        title=f'{titulo_band} {equipo.codigo}',
    )
    W = doc.width

    lbl = ParagraphStyle('blbl', fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.white)
    valc = ParagraphStyle('bvalc', fontName='Helvetica', fontSize=8.5, leading=10, alignment=TA_CENTER)
    band = ParagraphStyle('bband', fontName='Helvetica-Bold', fontSize=9.5, leading=11, alignment=TA_CENTER, textColor=colors.white)
    title = ParagraphStyle('btitle', fontName='Helvetica-Bold', fontSize=18, leading=20, alignment=TA_CENTER)
    name = ParagraphStyle('bname', fontName='Helvetica-Bold', fontSize=11, leading=13, alignment=TA_CENTER, textColor=colors.white)
    minic = ParagraphStyle('bminic', fontName='Helvetica', fontSize=6.8, leading=8.5, alignment=TA_CENTER)
    minibc = ParagraphStyle('bminibc', fontName='Helvetica-Bold', fontSize=6.8, leading=8.5, alignment=TA_CENTER)
    th = ParagraphStyle('bth', fontName='Helvetica-Bold', fontSize=7, leading=8.5, alignment=TA_CENTER, textColor=colors.white)
    td = ParagraphStyle('btd', fontName='Helvetica', fontSize=7.5, leading=9, alignment=TA_CENTER)
    tdl = ParagraphStyle('btdl', fontName='Helvetica', fontSize=7.5, leading=9, alignment=TA_LEFT)

    cfg = None
    empresa = ''
    try:
        from core.models import ConfiguracionSistema
        cfg = ConfiguracionSistema.cargar()
        empresa = (cfg.subtitulo or cfg.nombre_sistema or '').strip()
    except Exception:
        pass
    codigo_fmt, version_fmt, fecha_fmt = CODIGO_FORMATO, VERSION_FORMATO, FECHA_FORMATO
    elaborado_s, revisado_s, aprobado_s = '', '', ''
    try:
        if cfg:
            elaborado_s = getattr(cfg, 'formato_hv_elaborado', '') or ''
            revisado_s = getattr(cfg, 'formato_hv_revisado', '') or ''
            aprobado_s = getattr(cfg, 'formato_hv_aprobado', '') or ''
            cod = getattr(cfg, 'formato_hv_codigo', '') or ''
            if cod:
                from .models import Documento
                docfmt = Documento.objects.filter(codigo=cod, is_active=True).first()
                if docfmt:
                    codigo_fmt = docfmt.codigo
                    vv = docfmt.version_vigente
                    if vv:
                        version_fmt = vv.version or version_fmt
                        f = vv.fecha_vigencia or vv.fecha_aprobacion
                        if f:
                            fecha_fmt = f.date().isoformat() if hasattr(f, 'date') else f.isoformat()
    except Exception:
        pass
    elaborado_s = elaborado_s or FIRMAS[0][1]
    revisado_s = revisado_s or FIRMAS[1][1]
    aprobado_s = aprobado_s or FIRMAS[2][1]

    story = []

    logo_cell = Paragraph(empresa or 'EMPRESA', ParagraphStyle('blogo', fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=TA_CENTER))
    try:
        _logo = (getattr(cfg, 'logo_empresa', None) or getattr(cfg, 'logo', None)) if cfg else None
        if _logo and _logo.path:
            im = Image(_logo.path)
            r = min((W * 0.18) / im.imageWidth, (22 * mm) / im.imageHeight)
            im.drawWidth = im.imageWidth * r
            im.drawHeight = im.imageHeight * r
            im.hAlign = 'CENTER'
            logo_cell = im
    except Exception:
        pass

    c6 = W * 0.28 / 6.0
    hdr_data = [
        [logo_cell, Paragraph('HOJA DE VIDA', title), Paragraph('Código:', minibc), '', '', Paragraph(codigo_fmt, minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(version_fmt, minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(fecha_fmt, minic), '', ''],
        ['', '', Paragraph('Elaborado', minibc), '', Paragraph('Revisado', minibc), '', Paragraph('Aprobado', minibc), ''],
        ['', '', Paragraph(elaborado_s, minic), '', Paragraph(revisado_s, minic), '', Paragraph(aprobado_s, minic), ''],
    ]
    hdr = Table(hdr_data, colWidths=[W * 0.20, W * 0.52, c6, c6, c6, c6, c6, c6], rowHeights=[4.8 * mm] * 5)
    hdr.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('SPAN', (0, 0), (0, 4)),
        ('SPAN', (1, 0), (1, 4)),
        ('SPAN', (2, 0), (4, 0)), ('SPAN', (5, 0), (7, 0)),
        ('SPAN', (2, 1), (4, 1)), ('SPAN', (5, 1), (7, 1)),
        ('SPAN', (2, 2), (4, 2)), ('SPAN', (5, 2), (7, 2)),
        ('SPAN', (2, 3), (3, 3)), ('SPAN', (4, 3), (5, 3)), ('SPAN', (6, 3), (7, 3)),
        ('SPAN', (2, 4), (3, 4)), ('SPAN', (4, 4), (5, 4)), ('SPAN', (6, 4), (7, 4)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 4), 'CENTER'), ('ALIGN', (2, 0), (7, 4), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 4))

    story.append(Table([[Paragraph((equipo.nombre or '').upper(), name)]], colWidths=[W],
                       style=TableStyle([
                           ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
                           ('BACKGROUND', (0, 0), (-1, -1), BANDA),
                           ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                       ])))
    story.append(Table([[Paragraph('Código de Identificación', lbl), Paragraph(equipo.codigo or '', valc)]],
                       colWidths=[W * 0.30, W * 0.70],
                       style=TableStyle([
                           ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
                           ('BACKGROUND', (0, 0), (0, 0), LABEL),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 4),
                           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                       ])))
    story.append(Spacer(1, 4))

    story.append(_banda(titulo_band, W, band))

    if es_suceso:
        encabezados = ['N°', 'Sucesos', 'Fecha del Suceso', 'Fecha de Solución', 'Observaciones', 'Firma V°B°']
        anchos = [W * 0.05, W * 0.30, W * 0.13, W * 0.13, W * 0.27, W * 0.12]
        obs_idx = 4
    else:
        encabezados = ['N°', f'Frecuencia de {term}', f'N° de Informe de {term}', f'F. de {term}', f'F. de Próx. {term}', 'Observaciones', 'Firma V°B°']
        anchos = [W * 0.05, W * 0.14, W * 0.17, W * 0.12, W * 0.12, W * 0.28, W * 0.12]
        obs_idx = 5

    filas = [[Paragraph(h, th) for h in encabezados]]
    for i, r in enumerate(registros):
        if es_suceso:
            celdas = [str(i + 1), r.descripcion or '', _f(r.fecha), _f(r.fecha_proxima), r.observaciones or '', r.vb or '']
        else:
            celdas = [str(i + 1), r.frecuencia or '', r.numero_documento or '', _f(r.fecha), _f(r.fecha_proxima), r.observaciones or '', r.vb or '']
        filas.append([Paragraph(str(c), tdl if j == obs_idx else td) for j, c in enumerate(celdas)])
    for _ in range(max(2, 6 - len(registros))):
        filas.append([Paragraph('', td) for _ in encabezados])

    tb = Table(filas, colWidths=anchos)
    tb.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('BACKGROUND', (0, 0), (-1, 0), BANDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(tb)

    doc.build(story)
    return buf.getvalue()


def generar_inventario_pdf(equipos, laboratorio='') -> bytes:
    """PDF horizontal del Inventario de Equipos."""
    from reportlab.lib.pagesizes import landscape
    from django.utils import timezone
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=8 * mm, rightMargin=8 * mm, topMargin=8 * mm, bottomMargin=8 * mm,
        title='Inventario de Equipos',
    )
    W = doc.width

    title = ParagraphStyle('ivtitle', fontName='Helvetica-Bold', fontSize=16, leading=18, alignment=TA_CENTER)
    minic = ParagraphStyle('ivminic', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_CENTER)
    minibc = ParagraphStyle('ivminibc', fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=TA_CENTER)
    lblw = ParagraphStyle('ivlblw', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_CENTER, textColor=colors.white)
    valc = ParagraphStyle('ivvalc', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_CENTER)
    band = ParagraphStyle('ivband', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER, textColor=colors.white)
    th = ParagraphStyle('ivth', fontName='Helvetica-Bold', fontSize=6, leading=7, alignment=TA_CENTER, textColor=colors.white)
    td = ParagraphStyle('ivtd', fontName='Helvetica', fontSize=6, leading=7, alignment=TA_CENTER)
    tdb = ParagraphStyle('ivtdb', fontName='Helvetica-Bold', fontSize=6, leading=7, alignment=TA_CENTER)

    cfg = None
    empresa = ''
    try:
        from core.models import ConfiguracionSistema
        cfg = ConfiguracionSistema.cargar()
        empresa = (cfg.subtitulo or cfg.nombre_sistema or '').strip()
    except Exception:
        pass
    elaborado_s = (getattr(cfg, 'formato_hv_elaborado', '') if cfg else '') or FIRMAS[0][1]
    revisado_s = (getattr(cfg, 'formato_hv_revisado', '') if cfg else '') or FIRMAS[1][1]
    aprobado_s = (getattr(cfg, 'formato_hv_aprobado', '') if cfg else '') or FIRMAS[2][1]

    story = []
    logo_cell = Paragraph(empresa or 'EMPRESA', ParagraphStyle('ivlogo', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER))
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
        [logo_cell, Paragraph('INVENTARIO DE EQUIPOS', title), Paragraph('Código:', minibc), '', '', Paragraph('MET-PRO-04-r02', minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(VERSION_FORMATO, minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(FECHA_FORMATO, minic), '', ''],
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
    fechas_upd = [e.updated_at for e in equipos if getattr(e, 'updated_at', None)]
    fecha_act = (max(fechas_upd).date() if fechas_upd else hoy)
    info = Table([[Paragraph('FECHA DE ACTUALIZACIÓN', lblw), Paragraph(fecha_act.isoformat(), valc),
                   Paragraph('LABORATORIO:', lblw), Paragraph(laboratorio or '', valc)]],
                 colWidths=[W * 0.20, W * 0.20, W * 0.18, W * 0.42], rowHeights=[7 * mm])
    info.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('BACKGROUND', (0, 0), (0, 0), BANDA), ('BACKGROUND', (2, 0), (2, 0), BANDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(info)
    story.append(Spacer(1, 6))
    story.append(_banda('EQUIPOS', W, band))

    VERDE = colors.HexColor('#C6EFCE')
    AMBAR = colors.HexColor('#FFEB9C')
    ROJO = colors.HexColor('#FFC7CE')
    encabezados = ['Código', 'Descripción', 'Clasificación', 'Marca', 'Modelo', 'N° Serie',
                   'Alcance / Valor Nominal', 'Clase / Exactitud', 'Resolución / División de Escala (d) / Verificación (e)', 'N° de Certificado de Calibración',
                   'Periodicidad (Días)', 'Fecha de la Última Calibración', 'Fecha de Próxima Calibración',
                   'Estado', 'Proveedor de Calibración', 'Observaciones']
    fracs = [0.045, 0.095, 0.055, 0.065, 0.055, 0.05, 0.065, 0.05, 0.075, 0.075, 0.04, 0.055, 0.055, 0.06, 0.08, 0.08]
    anchos = [W * f for f in fracs]
    filas = [[Paragraph(h, th) for h in encabezados]]
    estilos = [
        ('GRID', (0, 0), (-1, -1), 0.5, LINEA),
        ('BACKGROUND', (0, 0), (-1, 0), BANDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]
    for i, e in enumerate(equipos, start=1):
        req = e.requiere_calibracion
        estado_txt = 'Instrumento Calibrado' if req else 'No Aplica'
        prox = e.fecha_proxima_calibracion
        ult = e.fecha_ultima_calibracion
        celdas = [
            e.codigo or '', e.nombre or '', e.clasificacion or '', e.marca or '', e.modelo or '', e.serie or '',
            e.cantidad or '', e.clase_exactitud or '', e.resolucion or '', e.n_certificado or '',
            str(e.periodicidad_dias or ''), (ult.isoformat() if ult else 'No aplica'),
            (prox.isoformat() if prox else 'No aplica'), estado_txt, e.proveedor_calibracion or '', e.observaciones or '',
        ]
        filas.append([Paragraph(str(c), tdb if j == 0 else td) for j, c in enumerate(celdas)])
        estilos.append(('BACKGROUND', (13, i), (13, i), VERDE if req else AMBAR))
        if req and prox and prox < hoy:
            estilos.append(('BACKGROUND', (12, i), (12, i), ROJO))

    tb = Table(filas, colWidths=anchos, repeatRows=1)
    tb.setStyle(TableStyle(estilos))
    story.append(tb)

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
    lblw = ParagraphStyle('pglblw', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_CENTER, textColor=colors.white)
    valc = ParagraphStyle('pgvalc', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_CENTER)
    band = ParagraphStyle('pgband', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER, textColor=colors.white)
    th = ParagraphStyle('pgth', fontName='Helvetica-Bold', fontSize=5.2, leading=6, alignment=TA_CENTER, textColor=colors.white)
    td = ParagraphStyle('pgtd', fontName='Helvetica', fontSize=5.2, leading=6, alignment=TA_CENTER)
    tdb = ParagraphStyle('pgtdb', fontName='Helvetica-Bold', fontSize=5.2, leading=6, alignment=TA_CENTER)
    thm = ParagraphStyle('pgthm', fontName='Helvetica-Bold', fontSize=4.6, leading=5.5, alignment=TA_CENTER, textColor=colors.white)

    cfg = None
    empresa = ''
    try:
        from core.models import ConfiguracionSistema
        cfg = ConfiguracionSistema.cargar()
        empresa = (cfg.subtitulo or cfg.nombre_sistema or '').strip()
    except Exception:
        pass
    elaborado_s = (getattr(cfg, 'formato_hv_elaborado', '') if cfg else '') or FIRMAS[0][1]
    revisado_s = (getattr(cfg, 'formato_hv_revisado', '') if cfg else '') or FIRMAS[1][1]
    aprobado_s = (getattr(cfg, 'formato_hv_aprobado', '') if cfg else '') or FIRMAS[2][1]

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
        [logo_cell, Paragraph('PROGRAMA DE MANTENIMIENTO, CALIBRACIÓN, COMPROBACIÓN INTERMEDIA, COMPROBACIÓN FUNCIONAL Y CARACTERIZACIÓN', title), Paragraph('Código:', minibc), '', '', Paragraph('MET-PRO-04-r03', minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(VERSION_FORMATO, minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(FECHA_FORMATO, minic), '', ''],
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
    info = Table([[Paragraph('FECHA DE ACTUALIZACIÓN', lblw), Paragraph(hoy.isoformat(), valc),
                   Paragraph('LABORATORIO:', lblw), Paragraph(laboratorio or '', valc),
                   Paragraph('AÑO:', lblw), Paragraph(str(anio), valc)]],
                 colWidths=[W * 0.18, W * 0.16, W * 0.14, W * 0.30, W * 0.08, W * 0.14], rowHeights=[7 * mm])
    info.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('BACKGROUND', (0, 0), (0, 0), BANDA), ('BACKGROUND', (2, 0), (2, 0), BANDA), ('BACKGROUND', (4, 0), (4, 0), BANDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(info)
    story.append(Spacer(1, 6))

    # ---- Matriz ----
    eq_cols = ['Equipo / Instrumento', 'Código', 'Alcance / Valor Nominal', 'Clase', 'Marca', 'Modelo', 'Serie']
    n_eq = len(eq_cols)
    fila0 = [Paragraph(h, th) for h in eq_cols]
    fila1 = ['' for _ in eq_cols]
    for titulo_bloque, _tipos in BLOQUES_PROGRAMA:
        fila0.append(Paragraph(titulo_bloque, th))
        fila0 += [''] * 12
        fila1.append(Paragraph('Frec.', th))
        fila1 += [Paragraph(m, thm) for m in MESES_PROGRAMA]
    filas = [fila0, fila1]

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

    eq_w = [W * 0.05, W * 0.035, W * 0.04, W * 0.027, W * 0.04, W * 0.035, W * 0.035]
    bloque_w = [W * 0.03] + [W * 0.018] * 12
    anchos = eq_w + bloque_w * 3

    estilos = [
        ('GRID', (0, 0), (-1, -1), 0.4, LINEA),
        ('BACKGROUND', (0, 0), (-1, 1), BANDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 1), ('RIGHTPADDING', (0, 0), (-1, -1), 1),
    ]
    for j in range(n_eq):
        estilos.append(('SPAN', (j, 0), (j, 1)))
    for b in range(3):
        ini = n_eq + b * 13
        estilos.append(('SPAN', (ini, 0), (ini + 12, 0)))

    tb = Table(filas, colWidths=anchos, repeatRows=2)
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
        empresa = (cfg.subtitulo or cfg.nombre_sistema or '').strip()
    except Exception:
        pass
    elaborado_s = (getattr(cfg, 'formato_hv_elaborado', '') if cfg else '') or FIRMAS[0][1]
    revisado_s = (getattr(cfg, 'formato_hv_revisado', '') if cfg else '') or FIRMAS[1][1]
    aprobado_s = (getattr(cfg, 'formato_hv_aprobado', '') if cfg else '') or FIRMAS[2][1]

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
        [logo_cell, Paragraph('CARTA DE TRAZABILIDAD', title), Paragraph('Código:', minibc), '', '', Paragraph('MET-PRO-04-r04', minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(VERSION_FORMATO, minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(FECHA_FORMATO, minic), '', ''],
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

    def lineas_nodo(n):
        ls = []
        innerw = bw - 2 * PADX
        if n.get('descripcion'):
            for L in wrap(n['descripcion'], 'Helvetica-Bold', 5.6, innerw):
                ls.append(('Helvetica-Bold', 5.6, L))
        if n.get('codigo'):
            ls.append(('Helvetica', 5.2, 'Cód. Identificación: ' + n['codigo']))
        if n.get('procedimiento'):
            for L in wrap(n['procedimiento'], 'Helvetica', 4.9, innerw):
                ls.append(('Helvetica', 4.9, L))
        if n.get('nota'):
            for L in wrap(n['nota'], 'Helvetica', 4.9, innerw):
                ls.append(('Helvetica', 4.9, L))
        if n.get('certificado'):
            for L in wrap('Certificado de Calib.: ' + n['certificado'], 'Helvetica', 5.0, innerw):
                ls.append(('Helvetica', 5.0, L))
        if n.get('incertidumbre'):
            ls.append(('Helvetica-Bold', 5.4, n['incertidumbre']))
        return ls

    node_lines = {nid: lineas_nodo(by_id[nid]) for nid in ids_all}
    node_h = {nid: HEADH + 5 + max(1, len(node_lines[nid])) * line_h for nid in ids_all}

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

        # Flechas de cada padre hacia cada hijo (pueden converger / cruzarse)
        for pid, hijos in kids.items():
            for hid in hijos:
                flecha(cx(pid), ytop(pid) - node_h[pid], cx(hid), ytop(hid))

        # Flecha desde la banda hacia las cajas del nivel superior (pegada, sin espacio)
        for nid in por_nivel[niveles[0]]:
            flecha(cx(nid), total_h, cx(nid), ytop(nid))

        for nid in ids_all:
            n = by_id[nid]
            fill, hd = box_color(n)
            x0 = cx(nid) - bw / 2
            yt = ytop(nid)
            h = node_h[nid]
            cv.setFillColor(fill); cv.setStrokeColor(hd); cv.setLineWidth(1)
            cv.rect(x0, yt - h, bw, h, fill=1, stroke=1)
            cv.setFillColor(hd); cv.rect(x0, yt - HEADH, bw, HEADH, fill=1, stroke=0)
            cv.setFillColor(colors.white); cv.setFont('Helvetica-Bold', 5.6)
            cab = (n.get('entidad') or n.get('codigo') or '')
            cv.drawCentredString(cx(nid), yt - HEADH + 2.7, cab[:int(bw / 3.0)])
            ty = yt - HEADH - line_h + 1
            cv.setFillColor(colors.black)
            for fn, fs, txt in node_lines[nid]:
                cv.setFont(fn, fs)
                cv.drawString(x0 + PADX, ty, txt)
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
    PDF del Intervalo de Calibración (MET-PRO-04-r08): encabezado del formato,
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
        empresa = (cfg.subtitulo or cfg.nombre_sistema or '').strip()
    except Exception:
        pass
    elaborado_s = (getattr(cfg, 'formato_hv_elaborado', '') if cfg else '') or FIRMAS[0][1]
    revisado_s = (getattr(cfg, 'formato_hv_revisado', '') if cfg else '') or FIRMAS[1][1]
    aprobado_s = (getattr(cfg, 'formato_hv_aprobado', '') if cfg else '') or FIRMAS[2][1]

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
        [logo_cell, Paragraph('INTERVALO DE CALIBRACIÓN', title), Paragraph('Código:', minibc), '', '', Paragraph('MET-PRO-04-r08', minic), '', ''],
        ['', '', Paragraph('Versión:', minibc), '', '', Paragraph(VERSION_FORMATO, minic), '', ''],
        ['', '', Paragraph('Fecha:', minibc), '', '', Paragraph(FECHA_FORMATO, minic), '', ''],
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

    info = Table([[Paragraph('PATRÓN:', lblw), Paragraph(f'{equipo.codigo} — {equipo.nombre}', valc),
                   Paragraph('FECHA DE ACTUALIZACIÓN:', lblw), Paragraph(timezone.now().date().isoformat(), valc),
                   Paragraph('LABORATORIO:', lblw), Paragraph(equipo.laboratorio or '', valc)]],
                 colWidths=[W * 0.08, W * 0.2534, W * 0.16, W * 0.1733, W * 0.11, W * 0.2233], rowHeights=[6.5 * mm])
    info.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, LINEA),
        ('BACKGROUND', (0, 0), (0, 0), BANDA), ('BACKGROUND', (2, 0), (2, 0), BANDA), ('BACKGROUND', (4, 0), (4, 0), BANDA),
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
        filas = [[Paragraph(x, th) for x in ['AÑO', 'RESULTADO', 'INCERT.', 'EMP', 'DERIVA']]]
        for r in rs:
            d = deriv.get(r['anio'])
            filas.append([
                Paragraph(str(r['anio']), td), Paragraph(fnum(r.get('resultado')), td),
                Paragraph(fnum(r.get('incertidumbre')), td), Paragraph(fnum(r.get('emp')), td),
                Paragraph('---' if d is None else fnum(d), td),
            ])
        cw5 = cw / 5.0
        tabla = Table(filas, colWidths=[cw5] * 5)
        tabla.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, LINEA),
            ('BACKGROUND', (0, 0), (-1, 0), BANDA),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        # resumen
        per = cal.get('periodo')
        per_txt = 'DERIVA 0' if per is None else f'{per:.1f} años'
        res = Table([
            [Paragraph('EMP', tlbl), Paragraph(fnum(cal.get('emp')), tval), Paragraph('Umáx', tlbl), Paragraph(fnum(cal.get('umax')), tval)],
            [Paragraph('Tolerancia', tlbl), Paragraph(fnum(cal.get('tolerancia')), tval), Paragraph('Deriva máx.', tlbl), Paragraph(fnum(cal.get('deriva_maxima')), tval)],
            [Paragraph('Periodo OIML D10', tlbl), Paragraph(per_txt, tval), '', ''],
        ], colWidths=[cw * 0.30, cw * 0.20, cw * 0.30, cw * 0.20])
        res.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, LINEA),
            ('SPAN', (1, 2), (3, 2)),
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
