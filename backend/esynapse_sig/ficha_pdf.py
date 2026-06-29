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
            Paragraph(_mk(equipo.clasificacion == clave), valc),
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
        lv('Marca', equipo.marca) + lv('Intervalo de Indicación / Valor Nominal', equipo.intervalo_indicacion),
        lv('Modelo', equipo.modelo) + lv('División de Escala (d) / Verificación (e)', equipo.division_escala),
        lv('Nº de Serie', equipo.serie) + lv('Clase de Exactitud', equipo.clase_exactitud),
        lv('Procedencia', equipo.procedencia) + lv('Alcance / Cantidad', equipo.cantidad),
        lv('Tipo de Indicación', equipo.tipo_indicacion) + lv('Material', equipo.material),
        lv('Ubicación', equipo.laboratorio) + lv('Resolución', equipo.resolucion),
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
            story.append(img)
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
