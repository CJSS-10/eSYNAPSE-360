"""
Formatos impresos de Cambios: Solicitud de Cambios, Planificación de Cambios
(una por cambio) y Seguimiento de Cambios (el listado), con la disposición de
sus plantillas.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import (AZUL_LISTA, CONTROL_FORMATOS, _cargar_cfg, _nombre_usuario, _p_ajustado,
                                    _solo_fecha, esc_pdf)
from quejas.pdf import _cabecera

COD_SOLICITUD = 'SIG-PRO-23-r01'
COD_PLANIFICACION = 'SIG-PRO-23-r02'
COD_SEGUIMIENTO = 'SIG-PRO-23-r03'
# Respaldo de la caja de control (valores de las plantillas) mientras el
# formato no esté vinculado a su documento de la lista maestra.
for _cod in (COD_SOLICITUD, COD_PLANIFICACION, COD_SEGUIMIENTO):
    CONTROL_FORMATOS.setdefault(_cod, ('00', '2026-02-23', 'ASIG', 'GSIG/GG', 'GG'))

GRIS_BANDA = colors.HexColor('#A6A6A6')
LETRAS = [chr(65 + i) for i in range(22)]          # A … V
# Anchos de columna de las plantillas; la A, algo más ancha para que «01» se lea.
ANCHOS = [7.5] + [13.0] * 21


class _Hoja:
    """Hoja de 22 columnas (A a V) como las plantillas de cambios. Cada fila se
    arma con tramos (desde, hasta, contenido, tipo): etiqueta azul ('azul'),
    franja gris ('gris'), franja de sección ('seccion'), casilla ('box', 'boxb'),
    texto suelto ('txt', 'txt_izq'), recuadro que crece ('area') o imagen ('img')."""

    def __init__(self, W, fs):
        total = sum(ANCHOS)
        self.cw = [W * a / total for a in ANCHOS]
        self.filas, self.altos, self.est = [], [], []
        b = dict(fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2)
        self.azul = ParagraphStyle('caz', alignment=TA_CENTER, textColor=colors.white, **b)
        self.seccion = ParagraphStyle('cse', alignment=TA_LEFT, textColor=colors.white, **b)
        self.etq = ParagraphStyle('cet', alignment=TA_LEFT, **b)
        self.val = ParagraphStyle('cva', fontName='Helvetica', fontSize=fs, leading=fs * 1.25, alignment=TA_CENTER)
        self.valb = ParagraphStyle('cvb', parent=self.val, fontName='Helvetica-Bold')
        self.texto = ParagraphStyle('ctx', fontName='Helvetica', fontSize=fs, leading=fs * 1.3)

    def ancho(self, a, b):
        return sum(self.cw[LETRAS.index(a):LETRAS.index(b) + 1])

    def espacio(self, alto):
        self.filas.append([''] * 22)
        self.altos.append(alto)

    def fila(self, alto, tramos, filas=1):
        r = len(self.filas)
        fila = [''] * 22
        for a, b, cont, tipo in tramos:
            i, j = LETRAS.index(a), LETRAS.index(b)
            ancho = sum(self.cw[i:j + 1])
            if tipo == 'img':
                pass
            elif tipo == 'area':
                cont = [Paragraph(esc_pdf(x) or '&nbsp;', self.texto) for x in (str(cont or '').split('\n') or [''])]
            elif tipo in ('azul', 'gris'):
                cont = _p_ajustado(cont, self.azul, ancho - 4)
            elif tipo == 'seccion':
                cont = Paragraph(esc_pdf(cont), self.seccion)
            elif tipo in ('txt', 'txt_izq'):
                cont = _p_ajustado(cont, self.etq, ancho - 4)
            else:
                cont = _p_ajustado(str(cont or ''), self.valb if tipo == 'boxb' else self.val, ancho - 4)
            fila[i] = cont
            if j > i or filas > 1:
                self.est.append(('SPAN', (i, r), (j, r + filas - 1)))
            if tipo not in ('txt', 'txt_izq'):
                self.est.append(('BOX', (i, r), (j, r + filas - 1), 0.6, colors.black))
            if tipo == 'linea':
                self.est[-1] = ('LINEBELOW', (i, r), (j, r), 0.6, colors.black)
            if tipo in ('azul', 'seccion'):
                self.est.append(('BACKGROUND', (i, r), (j, r + filas - 1), AZUL_LISTA))
            if tipo == 'gris':
                self.est.append(('BACKGROUND', (i, r), (j, r + filas - 1), GRIS_BANDA))
            if tipo == 'area':
                self.est.append(('VALIGN', (i, r), (j, r + filas - 1), 'TOP'))
            if tipo == 'img':
                self.est.append(('ALIGN', (i, r), (j, r + filas - 1), 'CENTER'))
        self.filas.append(fila)
        self.altos.append(alto)
        for _ in range(filas - 1):
            self.filas.append([''] * 22)
            self.altos.append(alto)

    def tabla(self):
        # Los recuadros de texto crecen con su contenido.
        spans = {e[1]: e[2] for e in self.est if e[0] == 'SPAN'}
        for r, fila in enumerate(self.filas):
            for i, celda in enumerate(fila):
                if not isinstance(celda, list):
                    continue
                j, r2 = spans.get((i, r), (i, r))
                ancho = sum(self.cw[i:j + 1]) - 6
                alto = sum(p.wrap(ancho, 4000)[1] for p in celda) + 8
                falta = alto - sum(self.altos[r:r2 + 1])
                if falta > 0:
                    self.altos[r2] += falta
        t = Table(self.filas, colWidths=self.cw, rowHeights=self.altos)
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                               ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
                              + self.est))
        return t


def _doc(buf, titulo, horizontal=False):
    return SimpleDocTemplate(buf, pagesize=landscape(A4) if horizontal else A4, leftMargin=12 * mm,
                             rightMargin=12 * mm, topMargin=8 * mm, bottomMargin=8 * mm, title=titulo)


def _x(cond):
    return 'X' if cond else ''


def _cargo(u):
    return (getattr(u, 'cargo', '') or '') if u else ''


def generar_solicitud_pdf(c) -> bytes:
    """Solicitud de Cambios: solicitud, evaluación, plan de ejecución y resolución."""
    from .models import IMPACTOS
    buf = BytesIO()
    doc = _doc(buf, f'Solicitud de cambio {c.codigo}')
    W = doc.width
    cfg = _cargar_cfg()
    fs, h, sp = 7.2, 12.0, 2.6
    g = _Hoja(W, fs)
    g.fila(h, [('A', 'V', '1. SOLICITUD DE CAMBIO', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('A', 'C', 'SOLICITANTE', 'azul'), ('D', 'N', _nombre_usuario(c.solicitante), 'box'),
               ('O', 'R', 'N° DE SOLICITUD', 'azul'), ('S', 'V', c.codigo, 'boxb')])
    g.espacio(sp)
    g.fila(h, [('A', 'E', 'PROCESO SOLICITANTE', 'azul'),
               ('F', 'N', c.proceso_solicitante.nombre if c.proceso_solicitante_id else '', 'box'),
               ('O', 'R', 'FECHA DE SOLICITUD', 'azul'), ('S', 'V', _solo_fecha(c.fecha_solicitud), 'box')])
    g.espacio(sp)
    g.fila(h, [('E', 'I', 'PRIORIDAD DE CAMBIO', 'gris'), ('J', 'K', 'ALTO', 'gris'),
               ('L', 'L', _x(c.prioridad == 'alta'), 'boxb'), ('M', 'N', 'MEDIO', 'gris'),
               ('O', 'O', _x(c.prioridad == 'media'), 'boxb'), ('P', 'Q', 'BAJO', 'gris'),
               ('R', 'R', _x(c.prioridad == 'baja'), 'boxb')])
    g.espacio(sp)
    origen = f'{c.get_origen_display()}: {c.motivo_origen}' if c.motivo_origen else ''
    g.fila(h, [('A', 'V', 'DESCRIPCIÓN DEL CAMBIO', 'gris')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', '\n'.join(x for x in (c.descripcion, f'Origen: {origen}' if origen else '') if x), 'area')],
           filas=2)
    g.espacio(sp)
    g.fila(h, [('A', 'V', 'JUSTIFICACIÓN DEL CAMBIO', 'gris')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', c.justificacion, 'area')], filas=2)
    g.espacio(sp)

    g.fila(h, [('A', 'V', '2. EVALUACIÓN DEL CAMBIO (LLENADO POR EL ÁREA SIG)', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('A', 'H', 'FACTIBILIDAD TÉCNICA', 'gris'), ('I', 'O', 'ASPECTOS OPERATIVOS', 'gris'),
               ('P', 'V', 'ASPECTOS FINANCIEROS', 'gris')])
    g.fila(h, [('A', 'H', c.factibilidad_tecnica, 'area'), ('I', 'O', c.aspectos_operativos, 'area'),
               ('P', 'V', c.aspectos_financieros, 'area')], filas=3)
    g.espacio(sp)
    procesos = ', '.join(p.nombre for p in c.procesos_afectados.all())
    g.fila(h, [('A', 'V', 'ALCANCE DEL CAMBIO (PROCESOS AFECTADOS Y/O INVOLUCRADOS)', 'gris')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', '\n'.join(x for x in (procesos, c.alcance) if x), 'area')], filas=2)
    g.espacio(sp)
    g.fila(h, [('A', 'V', 'BENEFICIOS DEL CAMBIO', 'gris')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', c.beneficios, 'area')], filas=2)
    g.espacio(sp)
    impactos = dict(IMPACTOS)
    clas = [c.get_clasificacion_display()] if c.clasificacion else []
    if c.es_tecnico:
        clas.append('cambio técnico')
    if c.afecta_clientes:
        clas.append('afecta a clientes o actividades acreditadas')
    lineas = []
    if clas:
        lineas.append('Clasificación: ' + ', '.join(clas) + '.')
    if c.impactos:
        lineas.append('Impactos evaluados: ' + '; '.join(impactos[k].split(':')[0] for k in c.impactos if k in impactos)
                      + '.')
    lineas.append(c.riesgos)
    g.fila(h, [('A', 'V', 'RIESGOS E IMPACTOS IDENTIFICADOS', 'gris')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', '\n'.join(x for x in lineas if x), 'area')], filas=2)
    g.espacio(sp)
    g.fila(h, [('A', 'V', 'CONTROLES ESTABLECIDOS', 'gris')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', c.controles, 'area')], filas=2)
    g.espacio(sp)
    g.fila(h, [('A', 'V', 'CONSECUENCIAS DE NO REALIZARLO', 'gris')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', c.consecuencias, 'area')], filas=2)
    g.espacio(sp)
    g.fila(h, [('A', 'O', 'RESPONSABLE DEL EQUIPO EVALUADOR', 'gris'), ('P', 'V', 'CARGO', 'gris')])
    g.fila(h, [('A', 'O', _nombre_usuario(c.responsable_evaluador), 'box'),
               ('P', 'V', _cargo(c.responsable_evaluador), 'box')])
    g.fila(h, [('A', 'V', 'EQUIPO EVALUADOR', 'gris')])
    equipo = [_nombre_usuario(u) for u in c.equipo_evaluador.all()] + [''] * 4
    g.fila(h, [('A', 'A', '01', 'gris'), ('B', 'K', equipo[0], 'box'), ('L', 'L', '03', 'gris'),
               ('M', 'V', equipo[2], 'box')])
    g.fila(h, [('A', 'A', '02', 'gris'), ('B', 'K', equipo[1], 'box'), ('L', 'L', '04', 'gris'),
               ('M', 'V', equipo[3], 'box')])
    g.espacio(sp)

    g.fila(h, [('A', 'V', '3. PLAN DE EJECUCIÓN DEL CAMBIO', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('A', 'H', 'ACTIVIDADES', 'gris'), ('I', 'L', 'RESPONSABLE', 'gris'), ('M', 'Q', 'RECURSOS', 'gris'),
               ('R', 'V', 'PLAZO DE IMPLEMENTACIÓN', 'gris')])
    acts = list(c.actividades.filter(is_active=True))
    for a in acts + [None] * max(0, 5 - len(acts)):
        g.fila(h, [('A', 'H', a.actividad if a else '', 'area'),
                   ('I', 'L', _nombre_usuario(a.responsable) if a else '', 'box'),
                   ('M', 'Q', a.recursos if a else '', 'box'), ('R', 'V', _solo_fecha(a.plazo) if a else '', 'box')])
    g.espacio(sp)

    g.fila(h, [('A', 'V', '4. RESOLUCIÓN DEL CAMBIO', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('F', 'H', 'APROBADO', 'gris'), ('I', 'I', _x(c.resultado == 'aprobado'), 'boxb'),
               ('N', 'P', 'RECHAZADO', 'gris'), ('Q', 'Q', _x(c.resultado == 'rechazado'), 'boxb')])
    g.espacio(sp)
    g.fila(h, [('A', 'H', 'APROBADO POR', 'gris'), ('I', 'O', 'FIRMA', 'gris'), ('P', 'V', 'FECHA', 'gris')])
    firma = ''
    if c.firma_resolucion:
        f = c.firma_resolucion
        firma = f'Firmado electrónicamente por {f.get("nombre", "")}' + (f' ({f["sigla"]})' if f.get('sigla') else '')
    resolucion = _nombre_usuario(c.resuelto_por)
    if c.motivo_resolucion:
        resolucion = f'{resolucion}\n{c.motivo_resolucion}'
    g.fila(h, [('A', 'H', resolucion, 'area'), ('I', 'O', firma, 'box'),
               ('P', 'V', _solo_fecha(c.fecha_resolucion), 'box')], filas=4)

    cab = _cabecera(W, g.cw, 'SOLICITUD DE CAMBIOS', COD_SOLICITUD, cfg, h, fs, 16, 4, 16)
    doc.build([cab, Spacer(1, 6), g.tabla()])
    return buf.getvalue()


def _imagen(archivo, ancho, alto):
    try:
        im = Image(archivo.path)
        r = min(ancho / im.imageWidth, alto / im.imageHeight)
        im.drawWidth, im.drawHeight = im.imageWidth * r, im.imageHeight * r
        return im
    except Exception:
        return ''


def generar_planificacion_pdf(c) -> bytes:
    """Planificación de Cambios."""
    from .models import FUENTES_PLANIFICACION
    buf = BytesIO()
    doc = _doc(buf, f'Planificación de cambio {c.codigo}')
    W = doc.width
    cfg = _cargar_cfg()
    fs, h, sp = 7.5, 14.0, 4.0
    g = _Hoja(W, fs)
    g.fila(h, [('A', 'V', '1. IDENTIFICACION Y REGISTRO', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('C', 'G', 'FECHA DE PLANIFICACIÓN', 'azul'), ('H', 'J', _solo_fecha(c.fecha_planificacion), 'box'),
               ('N', 'Q', 'N° DE SOLICITUD', 'azul'), ('R', 'T', c.codigo, 'boxb')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', 'TIPO DE CAMBIO', 'gris')])
    g.espacio(sp)
    g.fila(h, [('D', 'F', 'PREVISTO', 'gris'), ('G', 'G', _x(c.prevision == 'previsto'), 'boxb'),
               ('H', 'J', 'NO PREVISTO', 'gris'), ('K', 'K', _x(c.prevision == 'no_previsto'), 'boxb'),
               ('L', 'N', 'TEMPORAL', 'gris'), ('O', 'O', _x(c.temporalidad == 'temporal'), 'boxb'),
               ('P', 'R', 'PERMANENTE', 'gris'), ('S', 'S', _x(c.temporalidad == 'permanente'), 'boxb')])
    g.espacio(sp)
    descripcion = c.descripcion
    if c.temporalidad == 'temporal' and c.fecha_reversion:
        descripcion += f'\nCambio temporal: fin previsto el {_solo_fecha(c.fecha_reversion)}'
        if c.prorrogas:
            descripcion += f' (prorrogado; inicialmente el {c.prorrogas[0].get("fecha_anterior", "")})'
        descripcion += '.'
        if c.fin_temporal_fecha:
            descripcion += f' Terminó el {_solo_fecha(c.fin_temporal_fecha)}: {c.fin_temporal_detalle}'
    g.fila(h, [('A', 'V', 'DESCRIPCIÓN DEL CAMBIO', 'gris')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', descripcion, 'area')], filas=2)
    g.espacio(sp)
    g.fila(h, [('A', 'V', 'FUENTE U ORIGEN DEL CAMBIO', 'gris')])
    g.espacio(sp)
    fuentes = list(FUENTES_PLANIFICACION)
    izquierda, derecha = fuentes[:5], fuentes[5:]
    for (k1, t1), (k2, t2) in zip(izquierda, derecha):
        g.fila(h * 1.2, [('B', 'B', _x(k1 in c.fuentes), 'boxb'), ('C', 'K', t1, 'txt'),
                         ('L', 'L', _x(k2 in c.fuentes), 'boxb'), ('M', 'V', t2, 'txt')])
        g.espacio(sp)
    g.fila(h * 1.2, [('B', 'B', _x(bool(c.fuente_otro)), 'boxb'), ('C', 'D', 'Otros', 'txt'),
                     ('E', 'U', c.fuente_otro, 'linea')])
    g.espacio(sp * 2)

    g.fila(h, [('A', 'V', '2. IMPLEMENTACION, SEGUIMIENTO Y CONTROL', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('A', 'K', 'RESPONSABLE DEL EQUIPO DE IMPLEMENTACIÓN', 'gris'), ('L', 'Q', 'CARGO', 'gris'),
               ('R', 'V', 'PLAZO DE IMPLEMENTACIÓN', 'gris')])
    g.fila(h, [('A', 'K', _nombre_usuario(c.responsable_implementacion), 'box'),
               ('L', 'Q', _cargo(c.responsable_implementacion), 'box'),
               ('R', 'V', _solo_fecha(c.plazo_implementacion), 'box')])
    g.fila(h, [('A', 'V', 'EQUIPO DE IMPLEMENTACIÓN', 'gris')])
    equipo = [_nombre_usuario(u) for u in c.equipo_implementacion.all()] + [''] * 4
    g.fila(h, [('A', 'A', '01', 'gris'), ('B', 'K', equipo[0], 'box'), ('L', 'L', '03', 'gris'),
               ('M', 'V', equipo[2], 'box')])
    g.fila(h, [('A', 'A', '02', 'gris'), ('B', 'K', equipo[1], 'box'), ('L', 'L', '04', 'gris'),
               ('M', 'V', equipo[3], 'box')])
    g.espacio(sp)
    g.fila(h, [('A', 'I', 'ACTIVIDADES', 'gris'), ('J', 'N', 'RESPONSABLES', 'gris'), ('O', 'R', 'RECURSOS', 'gris'),
               ('S', 'V', 'SEGUIMIENTO', 'gris')])
    acts = list(c.actividades.filter(is_active=True))
    for n, a in enumerate(acts + [None] * max(0, 4 - len(acts)), 1):
        seguimiento = ''
        if a:
            seguimiento = a.seguimiento or (f'Plazo: {_solo_fecha(a.plazo)}' if a.plazo else '')
            if a.completada:
                seguimiento = f'{seguimiento}\nCompletada el {_solo_fecha(a.fecha_completada)}'.strip()
        g.fila(h, [('A', 'A', f'{n:02d}', 'gris'), ('B', 'I', a.actividad if a else '', 'area'),
                   ('J', 'N', _nombre_usuario(a.responsable) if a else '', 'box'),
                   ('O', 'R', a.recursos if a else '', 'box'), ('S', 'V', seguimiento, 'area')])
    g.espacio(sp)
    g.fila(h, [('A', 'V', 'REGISTRO FOTOGRÁFICO', 'gris')])
    g.fila(h, [('A', 'H', 'ANTES DEL CAMBIO', 'gris'), ('I', 'O', 'DURANTE EL CAMBIO', 'gris'),
               ('P', 'V', 'DESPUÉS DEL CAMBIO', 'gris')])
    alto_fotos = h * 6
    fotos = {m: c.fotos.filter(is_active=True, momento=m).first() for m in ('antes', 'durante', 'despues')}
    tramos = []
    for (a, b), m in zip((('A', 'H'), ('I', 'O'), ('P', 'V')), ('antes', 'durante', 'despues')):
        img = _imagen(fotos[m].archivo, g.ancho(a, b) - 8, alto_fotos - 8) if fotos[m] else ''
        tramos.append((a, b, img, 'img'))
    g.fila(alto_fotos, tramos)
    g.est.append(('BOX', (0, len(g.filas) - 1), (7, len(g.filas) - 1), 0.6, colors.black))
    g.est.append(('BOX', (8, len(g.filas) - 1), (14, len(g.filas) - 1), 0.6, colors.black))
    g.est.append(('BOX', (15, len(g.filas) - 1), (21, len(g.filas) - 1), 0.6, colors.black))

    cab = _cabecera(W, g.cw, 'PLANIFICACIÓN DE CAMBIOS', COD_PLANIFICACION, cfg, h, fs, 16, 4, 16)
    doc.build([cab, Spacer(1, 6), g.tabla()])
    return buf.getvalue()


def _si_no(v):
    return '' if v is None else ('Sí' if v else 'No')


def generar_seguimiento_pdf(cambios) -> bytes:
    """Seguimiento de Cambios: una fila por cambio."""
    buf = BytesIO()
    doc = _doc(buf, 'Seguimiento de cambios', horizontal=True)
    W = doc.width
    cfg = _cargar_cfg()
    # Grupos de columnas de la plantilla (A:B, C:D, E:H, …); código y fecha
    # algo más anchos para que no se partan.
    proporcion = [31, 27, 40, 44, 54, 54, 46, 44, 38, 32, 44, 28]
    cw = [W * a / sum(proporcion) for a in proporcion]
    ft = 8
    th = ParagraphStyle('csth', fontName='Helvetica-Bold', fontSize=ft, leading=ft * 1.15, alignment=TA_CENTER,
                        textColor=colors.white)
    td = ParagraphStyle('cstd', fontName='Helvetica', fontSize=ft, leading=ft * 1.2, alignment=TA_CENTER)
    tdl = ParagraphStyle('cstl', parent=td, alignment=TA_LEFT)
    tdb = ParagraphStyle('cstb', parent=td, fontName='Helvetica-Bold')
    def P(t, s=td):
        # Texto y estilo; la celda se arma después, con el ancho de su columna.
        return (str(t or ''), s)

    def ajustar(fila, encabezado=False):
        """Ninguna palabra se parte: se reduce la letra de la celda lo necesario."""
        salida = []
        for k, celda in enumerate(fila):
            if isinstance(celda, tuple):
                ancho = cw[k] * (2 if encabezado and k == 4 else 4 if encabezado and k == 8 else 1)
                celda = _p_ajustado(celda[0], celda[1], ancho - 4)
            salida.append(celda)
        return salida
    filas = [
        [P('N° DE SOLICITUD', th), P('FECHA DE SOLICITUD', th), P('SOLICITANTE', th), P('ÁREA', th),
         P('DESCRIPCIÓN DEL CAMBIO', th), '', P('RESPONSABLES DE LA IMPLEMENTACIÓN', th),
         P('RESPONSABLE DE LA APROBACIÓN', th), P('CIERRE DEL CAMBIO', th), '', '', ''],
        ['', '', '', '', P('CAMBIOS INTERNOS', th), P('CAMBIOS EXTERNOS', th), '', '', P('¿SE IMPLEMENTÓ?', th),
         P('¿FUE EFICAZ?', th), P('CERRADO POR', th), P('FECHA', th)],
    ]
    for c in cambios:
        responsables = [_nombre_usuario(c.responsable_implementacion)] if c.responsable_implementacion_id else []
        responsables += [_nombre_usuario(u) for u in c.equipo_implementacion.all()]
        interno = c.descripcion if c.origen == 'interno' else ''
        externo = c.descripcion if c.origen == 'externo' else ''
        filas.append([P(c.codigo, tdb), P(_solo_fecha(c.fecha_solicitud)), P(_nombre_usuario(c.solicitante)),
                      P(c.proceso_solicitante.nombre if c.proceso_solicitante_id else ''), P(interno, tdl),
                      P(externo, tdl), P('\n'.join(dict.fromkeys(responsables))),
                      P(_nombre_usuario(c.resuelto_por) if c.resultado == 'aprobado' else
                        (f'Rechazado: {_nombre_usuario(c.resuelto_por)}' if c.resultado == 'rechazado' else '')),
                      P(_si_no(c.se_implemento)), P(_si_no(c.fue_eficaz)), P(_nombre_usuario(c.cerrado_por)),
                      P(_solo_fecha(c.fecha_cierre))])
    filas = [ajustar(f, i == 0) for i, f in enumerate(filas)]
    while len(filas) < 21:
        filas.append([''] * 12)
    t = Table(filas, colWidths=cw, repeatRows=2,
              rowHeights=[None, None] + [None if isinstance(f[0], Paragraph) else 15 for f in filas[2:]])
    est = [('GRID', (0, 0), (-1, -1), 0.6, colors.black), ('BACKGROUND', (0, 0), (-1, 1), AZUL_LISTA),
           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
           ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
           ('SPAN', (4, 0), (5, 0)), ('SPAN', (8, 0), (11, 0))]
    for col in (0, 1, 2, 3, 6, 7):
        est.append(('SPAN', (col, 0), (col, 1)))
    t.setStyle(TableStyle(est))
    cab = _cabecera(W, [W * 0.075, W * 0.775], 'SEGUIMIENTO DE CAMBIOS', COD_SEGUIMIENTO, cfg, 12.0, 6.5, 16, 1, 2)
    doc.build([cab, Spacer(1, 6), t])
    return buf.getvalue()
