"""
Bloque de aprobación del Comité de SST en los formatos impresos (decisión de César del 24-10-2026: todo lo que firma
el Comité lleva esta forma). Una fila «REALIZADO Y APROBADO POR» con el nombre y cargo de cada titular y cómo firmó,
y debajo la fecha de cada firma. Lo usan la matriz IPERC, el programa anual de capacitación, la matriz de aspectos
ambientales y el Programa SSOMA.
"""
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

from esynapse_sig.ficha_pdf import _solo_fecha, esc_pdf

AZUL = colors.HexColor('#16365C')
METODO_FIRMA = {'usuario': 'Firmado con su usuario', 'pin': 'Firmado con PIN', 'papel': 'Firma en el acta adjunta',
                'carga': 'Firmado en el formato original'}


def _titulares_vigentes():
    from .comite_firmas import titulares_para_firmar
    _, tit = titulares_para_firmar()
    return [{'nombre': t['nombre'], 'cargo': t['cargo']} for t in tit]


def bloque_firmas_comite(W, firmas=None, fecha=None, nota=None):
    """Flowables del bloque de aprobación. «firmas»: [{nombre, cargo, metodo, fecha}] de la aprobación vigente;
    «fecha»: la de la aprobación, para las firmas que no traen la suya. Sin firmas (o con «nota» de pendiente) imprime
    a los titulares vigentes con las casillas de firma y fecha en blanco, para firmar."""
    lista = list(firmas or []) if not nota else []
    if not lista:
        lista = _titulares_vigentes() or [{}] * 4
    td = ParagraphStyle('cpd', fontName='Helvetica', fontSize=7, leading=8.5, alignment=TA_CENTER)
    thb = ParagraphStyle('cpb', parent=td, fontName='Helvetica-Bold', textColor=colors.white)
    fi = ParagraphStyle('cpi', parent=td, fontName='Helvetica-Oblique', fontSize=6.5,
                        textColor=colors.HexColor('#1F4E79'))
    n = len(lista)
    w0 = W * 0.11
    wn, wf = (W - w0) / n * 0.66, (W - w0) / n * 0.34
    fila1 = [Paragraph('REALIZADO Y APROBADO POR:', thb)]
    fila2 = [Paragraph('FECHA', thb)]
    for f in lista:
        fila1 += [Paragraph(f'{esc_pdf(f.get("nombre", ""))}<br/>{esc_pdf(f.get("cargo", ""))}', td),
                  Paragraph(esc_pdf(METODO_FIRMA.get(f.get('metodo'), '')), fi)]
        fecha_f = f.get('fecha') or (str(fecha) if f.get('metodo') and fecha else '')
        fila2 += [Paragraph(esc_pdf(_solo_fecha(fecha_f) if fecha_f else ''), td), '']
    # La fila de firmas crece con el texto (nombres largos en hojas A4); su relleno le da el alto de la casilla.
    t = Table([fila1, fila2], colWidths=[w0] + [wn, wf] * n, rowHeights=[None, 14])
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.6, colors.black), ('BACKGROUND', (0, 0), (0, -1), AZUL),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, 0), 6),
                           ('BOTTOMPADDING', (0, 0), (-1, 0), 6)]
                          + [('SPAN', (1 + 2 * i, 1), (2 + 2 * i, 1)) for i in range(n)]))
    partes = [t]
    if nota:
        partes.append(Paragraph(esc_pdf(nota), ParagraphStyle('cpn', fontName='Helvetica-Bold', fontSize=7,
                                                              textColor=colors.HexColor('#C00000'), spaceBefore=3)))
    return partes
