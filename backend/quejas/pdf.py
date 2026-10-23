"""
Formatos impresos de Quejas: Reporte de Quejas (una queja) y Registro de
Seguimiento de Quejas (el listado), con la disposición de sus plantillas.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import (AZUL_LISTA, CONTROL_FORMATOS, _cargar_cfg, _logo_celda, _nombre_usuario,
                                    _p_ajustado, _solo_fecha, control_formato, esc_pdf)

COD_REPORTE_QUEJAS = 'SIG-PRO-04-r01'
COD_SEGUIMIENTO_QUEJAS = 'SIG-PRO-04-r02'
# Respaldo de la caja de control (valores de las plantillas) mientras el
# formato no esté vinculado a su documento de la lista maestra.
CONTROL_FORMATOS.setdefault(COD_REPORTE_QUEJAS, ('00', '2025-10-13', 'ASIG', 'GSIG/GT', 'GG'))
CONTROL_FORMATOS.setdefault(COD_SEGUIMIENTO_QUEJAS, ('00', '2025-10-13', 'ASIG', 'GSIG/GT', 'GG'))

GRIS_BANDA = colors.HexColor('#A6A6A6')     # franjas grises con texto blanco de la plantilla
COLUMNAS = 'ABCDEFGHIJKLMNOPQRST'


def _col(letra):
    return COLUMNAS.index(letra)


class _Hoja:
    """Hoja de 20 columnas (A a T) como la plantilla del reporte. Cada fila se
    arma con tramos: etiqueta azul ('azul'), franja gris ('gris'), franja de
    sección ('seccion'), casilla ('box', 'boxb'), texto suelto ('txt') o
    recuadro de texto que crece con el contenido ('area')."""

    def __init__(self, W, fs):
        anchos = [7.14] + [8.43] * 19
        total = sum(anchos)
        self.cw = [W * a / total for a in anchos]
        self.filas, self.altos, self.est = [], [], []
        b = dict(fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2)
        self.azul = ParagraphStyle('qaz', alignment=TA_CENTER, textColor=colors.white, **b)
        self.gris = ParagraphStyle('qgr', alignment=TA_CENTER, textColor=colors.white, **b)
        self.seccion = ParagraphStyle('qse', alignment=TA_LEFT, textColor=colors.white, **b)
        self.etq = ParagraphStyle('qet', alignment=TA_CENTER, **b)
        self.val = ParagraphStyle('qva', fontName='Helvetica', fontSize=fs + 1, leading=(fs + 1) * 1.25,
                                  alignment=TA_CENTER)
        self.valb = ParagraphStyle('qvb', parent=self.val, fontName='Helvetica-Bold')
        self.texto = ParagraphStyle('qtx', fontName='Helvetica', fontSize=fs + 1, leading=(fs + 1) * 1.3)

    def espacio(self, alto):
        self.filas.append([''] * 20)
        self.altos.append(alto)

    def fila(self, alto, tramos):
        r = len(self.filas)
        fila = [''] * 20
        for a, b, cont, tipo in tramos:
            i, j = _col(a), _col(b)
            ancho = sum(self.cw[i:j + 1])
            if isinstance(cont, str):
                if tipo in ('area', 'txt_izq'):
                    cont = [Paragraph(esc_pdf(x) or '&nbsp;', self.texto) for x in (cont.split('\n') or [''])]
                elif tipo == 'azul':
                    # Todas las etiquetas con el mismo tamaño de letra: las largas
                    # pasan a dos líneas en lugar de achicarse.
                    cont = Paragraph(esc_pdf(cont), self.azul)
                elif tipo in ('gris', 'seccion'):
                    cont = Paragraph(esc_pdf(cont), {'gris': self.gris, 'seccion': self.seccion}[tipo])
                else:
                    estilo = {'boxb': self.valb, 'txt': self.etq}.get(tipo, self.val)
                    cont = _p_ajustado(cont, estilo, ancho - 4, una_linea=alto is not None)
            fila[i] = cont
            if j > i:
                self.est.append(('SPAN', (i, r), (j, r)))
            if tipo != 'txt':
                self.est.append(('BOX', (i, r), (j, r), 0.6, colors.black))
            if tipo == 'linea':
                self.est[-1] = ('LINEBELOW', (i, r), (j, r), 0.6, colors.black)
            if tipo in ('azul', 'seccion'):
                self.est.append(('BACKGROUND', (i, r), (j, r), AZUL_LISTA))
            if tipo == 'gris':
                self.est.append(('BACKGROUND', (i, r), (j, r), GRIS_BANDA))
            if tipo in ('area', 'txt_izq'):
                self.est.append(('VALIGN', (i, r), (j, r), 'TOP'))
        self.filas.append(fila)
        self.altos.append(alto)

    def tabla(self):
        # Las filas con recuadro de texto crecen con su contenido.
        for r, fila in enumerate(self.filas):
            minimo = self.altos[r]
            if not isinstance(minimo, tuple):
                continue
            alto = minimo[0]
            for i, celda in enumerate(fila):
                if isinstance(celda, list):
                    j = i
                    for e in self.est:
                        if e[0] == 'SPAN' and e[1] == (i, r):
                            j = e[2][0]
                    ancho = sum(self.cw[i:j + 1]) - 6
                    alto = max(alto, sum(p.wrap(ancho, 4000)[1] for p in celda) + 8)
            self.altos[r] = alto
        t = Table(self.filas, colWidths=self.cw, rowHeights=self.altos)
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                               ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
                              + self.est))
        return t


def _cabecera(W, cw, titulo, codigo, cfg, alto, fs, titulo_fs, col_logo, col_titulo):
    """Logo, título y caja de control (código, versión, fecha; elaborado, revisado, aprobado)."""
    _c = control_formato(codigo, cfg)
    lb = ParagraphStyle('qhl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    vl = ParagraphStyle('qhv', fontName='Helvetica', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    tit = ParagraphStyle('qht', fontName='Helvetica-Bold', fontSize=titulo_fs, leading=titulo_fs * 1.2,
                         alignment=TA_CENTER)
    w_logo, w_tit = sum(cw[:col_logo]), sum(cw[col_logo:col_titulo])
    resto = W - w_logo - w_tit
    c6 = [resto / 6.0] * 6
    data = [
        [_logo_celda(cfg, w_logo - 6, alto * 5 - 6), Paragraph(titulo, tit), Paragraph('Código:', lb), '', '',
         Paragraph(esc_pdf(_c['codigo']), vl), '', ''],
        ['', '', Paragraph('Versión:', lb), '', '', Paragraph(esc_pdf(_c['version']), vl), '', ''],
        ['', '', Paragraph('Fecha:', lb), '', '', Paragraph(esc_pdf(_c['fecha']), vl), '', ''],
        ['', '', _p_ajustado('Elaborado:', lb, c6[0] * 2 - 4), '', _p_ajustado('Revisado:', lb, c6[0] * 2 - 4), '',
         _p_ajustado('Aprobado:', lb, c6[0] * 2 - 4), ''],
        ['', '', Paragraph(esc_pdf(_c['elaborado']), vl), '', Paragraph(esc_pdf(_c['revisado']), vl), '',
         Paragraph(esc_pdf(_c['aprobado']), vl), ''],
    ]
    t = Table(data, colWidths=[w_logo, w_tit] + c6, rowHeights=[alto] * 5)
    est = [('BOX', (0, 0), (0, 4), 0.6, colors.black), ('BOX', (1, 0), (1, 4), 0.6, colors.black),
           ('GRID', (2, 0), (7, 4), 0.6, colors.black), ('SPAN', (0, 0), (0, 4)), ('SPAN', (1, 0), (1, 4)),
           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (0, 4), 'CENTER'),
           ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
           ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]
    for r in range(3):
        est += [('SPAN', (2, r), (4, r)), ('SPAN', (5, r), (7, r))]
    for r in (3, 4):
        est += [('SPAN', (2, r), (3, r)), ('SPAN', (4, r), (5, r)), ('SPAN', (6, r), (7, r))]
    t.setStyle(TableStyle(est))
    return t


def _si_no(v):
    return '' if v is None else ('Sí' if v else 'No')


def generar_reporte_queja_pdf(q) -> bytes:
    """Reporte de Quejas de una queja, con las cuatro secciones de su plantilla."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=10 * mm,
                            bottomMargin=10 * mm, title=f'Reporte de queja {q.codigo}')
    W = doc.width
    cfg = _cargar_cfg()
    fs, h, sp = 7.5, 14.0, 3.0
    g = _Hoja(W, fs)
    area = lambda n: (h * n,)   # noqa: E731  — alto mínimo de un recuadro de n filas

    h2 = h * 1.6   # filas con etiquetas de dos líneas
    g.fila(h2, [('A', 'F', 'N° DE QUEJA', 'azul'), ('G', 'M', q.codigo, 'boxb'),
               ('O', 'Q', 'FECHA DE RECEPCIÓN', 'azul'), ('R', 'T', _solo_fecha(q.fecha_recepcion), 'box')])
    g.espacio(sp)
    g.fila(h2, [('A', 'F', 'NOMBRE DEL PERSONAL QUE REGISTRA LA QUEJA', 'azul'),
               ('G', 'M', _nombre_usuario(q.created_by), 'box'),
               ('O', 'Q', 'FECHA DE VALIDACIÓN', 'azul'), ('R', 'T', _solo_fecha(q.fecha_validacion), 'box')])
    g.espacio(sp)
    g.fila(h, [('A', 'T', '1. DATOS DEL CLIENTE', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('A', 'E', 'NOMBRE DE LA EMPRESA', 'azul'), ('F', 'T', q.empresa, 'box')])
    g.espacio(sp)
    g.fila(h, [('A', 'G', 'REPRESENTANTE O PERSONA DE CONTACTO', 'azul'), ('H', 'T', q.contacto, 'box')])
    g.espacio(sp)
    g.fila(h, [('A', 'T', '2. DESCRIPCIÓN DE LA QUEJA', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('A', 'T', 'MEDIO DE RECEPCIÓN', 'gris')])
    g.espacio(sp)
    x = 'X'
    m = q.medio_recepcion
    g.fila(h, [('B', 'C', 'TELÉFONO:', 'txt'), ('D', 'D', x if m == 'telefono' else '', 'boxb'),
               ('F', 'G', 'E-MAIL:', 'txt'), ('H', 'H', x if m == 'email' else '', 'boxb'),
               ('J', 'K', 'PRESENCIAL:', 'txt'), ('L', 'L', x if m == 'presencial' else '', 'boxb'),
               ('N', 'O', 'OTROS:', 'txt'), ('P', 'S', q.medio_otro if m == 'otros' else '', 'linea')])
    g.espacio(sp)
    motivo = f'{q.get_origen_display()}: {q.motivo}'
    if q.desde_encuesta:
        motivo += '\n(Originada en una encuesta de satisfacción)'
    g.fila(h, [('A', 'T', 'MOTIVO DE LA QUEJA', 'gris')])
    g.espacio(sp)
    g.fila(area(3), [('A', 'T', motivo, 'area')])
    g.espacio(sp)
    g.fila(h, [('A', 'T', 'DESCRIPCIÓN DE LA QUEJA', 'gris')])
    g.espacio(sp)
    g.fila(area(3), [('A', 'T', q.descripcion, 'area')])
    g.espacio(sp)
    adjuntos = [a.descripcion or a.archivo.name.rsplit('/', 1)[-1] for a in q.adjuntos.filter(is_active=True)]
    g.fila(h, [('A', 'T', 'DOCUMENTO ADJUNTO', 'gris')])
    g.espacio(sp)
    g.fila(area(2), [('A', 'T', '\n'.join(adjuntos), 'area')])
    g.espacio(sp)
    g.fila(h, [('A', 'T', '3. EVALUACIÓN DE LA QUEJA', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('A', 'P', 'RESPONSABLES', 'gris'), ('Q', 'T', 'FECHA DE EVALUACIÓN', 'gris')])
    g.espacio(sp)
    responsables = ', '.join(_nombre_usuario(u) for u in q.responsables.all())
    g.fila(area(3), [('A', 'P', responsables, 'area'), ('Q', 'T', _solo_fecha(q.fecha_evaluacion), 'box')])
    g.espacio(sp)
    if q.resultado == 'no_relacionada':
        evaluacion = f'No relacionada con las actividades de la empresa: {q.motivo_validacion}'
    else:
        lineas = [q.evaluacion]
        if q.dentro_alcance is not None:
            lineas.append(f'¿Dentro del alcance acreditado? {_si_no(q.dentro_alcance)}')
        if q.resultado:
            lineas.append(f'Decisión: {q.get_resultado_display()}. {q.fundamento_decision}')
        evaluacion = '\n'.join(x for x in lineas if x)
    g.fila(h, [('A', 'T', 'EVALUACIÓN DE LA QUEJA', 'gris')])
    g.espacio(sp)
    g.fila(area(3), [('A', 'T', evaluacion, 'area')])
    g.espacio(sp)
    g.fila(h, [('A', 'T', 'INVESTIGACIÓN / ANÁLISIS DE CAUSAS', 'gris')])
    g.espacio(sp)
    g.fila(area(3), [('A', 'T', q.investigacion, 'area')])
    g.espacio(sp)
    acciones = [q.acciones]
    if q.responsable_acciones_id:
        acciones.append(f'Responsable: {_nombre_usuario(q.responsable_acciones)}')
    if q.hallazgo_id:
        acciones.append(f'Registrada como No Conformidad {q.hallazgo.codigo}'
                        + (f' (tratada en la {q.hallazgo.sac.codigo})' if q.hallazgo.sac_id else ''))
    if q.requiere_tnc:
        acciones.append('Tratada como trabajo no conforme.')
    if q.certificado_nuevo:
        acciones.append(f'Nuevo certificado {q.certificado_nuevo}, que reemplaza al {q.certificado_original}.')
    if q.seguimiento:
        acciones.append(f'Seguimiento ({_solo_fecha(q.fecha_seguimiento)}): {q.seguimiento}')
    g.fila(h, [('A', 'T', 'ACCIONES A REALIZAR', 'gris')])
    g.espacio(sp)
    g.fila(area(3), [('A', 'T', '\n'.join(x for x in acciones if x), 'area')])
    g.espacio(sp)
    g.fila(h, [('A', 'T', '4. CONFORMIDAD DEL CLIENTE', 'seccion')])
    g.espacio(sp)
    g.fila(h, [('A', 'P', 'COMUNICACIÓN AL CLIENTE', 'gris'), ('Q', 'T', 'FECHA DE CIERRE', 'gris')])
    g.espacio(sp)
    com = [q.comunicacion_cliente]
    if q.medio_cierre:
        com.append(f'Medio: {q.get_medio_cierre_display()}. Notificado por: {_nombre_usuario(q.notificado_por)}.')
    if q.conformidad_cliente:
        com.append(f'Conformidad del cliente: {q.get_conformidad_cliente_display()}.')
    g.fila(area(3), [('A', 'P', '\n'.join(x for x in com if x), 'area'),
                     ('Q', 'T', _solo_fecha(q.fecha_cierre), 'box')])

    cab = _cabecera(W, g.cw, 'REPORTE DE QUEJAS', COD_REPORTE_QUEJAS, cfg, h, fs, 16, 3, 14)
    doc.build([cab, Spacer(1, 6), g.tabla()])
    return buf.getvalue()


def generar_seguimiento_quejas_pdf(quejas) -> bytes:
    """Registro de Seguimiento de Quejas: una fila por queja, en Arial 11."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=10 * mm, bottomMargin=10 * mm, title='Registro de seguimiento de quejas')
    W = doc.width
    cfg = _cargar_cfg()
    # Anchos mínimos para que a 11 puntos ninguna palabra se parta (código, fecha,
    # «Observaciones», «Acreditado?»); el resto va al detalle de la queja.
    proporcion = [74, 64, 50, 80, 110, 68, 56, 68, 72, 56, 87]
    cw = [W * a / sum(proporcion) for a in proporcion]
    ft = 11
    th = ParagraphStyle('qsth', fontName='Helvetica-Bold', fontSize=ft, leading=ft * 1.2, alignment=TA_CENTER,
                        textColor=colors.white)
    tdc = ParagraphStyle('qstd', fontName='Helvetica', fontSize=ft, leading=ft * 1.2, alignment=TA_CENTER)
    td = ParagraphStyle('qstl', parent=tdc, alignment=TA_LEFT)
    tdb = ParagraphStyle('qstb', parent=tdc, fontName='Helvetica-Bold')
    filas = [[Paragraph(t, th) for t in (
        'N° de Queja', 'Fecha Recepción', 'N° Orden de Trabajo', 'Cliente', 'Detalle de la Queja',
        'Presentado por', 'Recibido por', 'Análisis de Aceptación de la Queja', '¿Dentro del Alcance Acreditado?',
        'Estado (Abierto / Cerrado)', 'Observaciones')]]
    altos = [None]
    for q in quejas:
        analisis = q.get_resultado_display() if q.resultado else ('Por validar' if q.estado == 'recibida'
                                                                 else 'En evaluación')
        obs = q.observaciones
        if q.hallazgo_id:
            obs = f'{obs}\n{q.hallazgo.codigo}'.strip()
        filas.append([Paragraph(esc_pdf(q.codigo), tdb), Paragraph(esc_pdf(_solo_fecha(q.fecha_recepcion)), tdc),
                      Paragraph(esc_pdf(q.orden_trabajo), tdc), Paragraph(esc_pdf(q.empresa), tdc),
                      Paragraph(esc_pdf(q.descripcion), td), Paragraph(esc_pdf(q.contacto), tdc),
                      Paragraph(esc_pdf(_nombre_usuario(q.recibido_por)), tdc), Paragraph(esc_pdf(analisis), tdc),
                      Paragraph(esc_pdf(_si_no(q.dentro_alcance)), tdc),
                      Paragraph('Cerrado' if q.estado == 'cerrada' else 'Abierto', tdc),
                      Paragraph(esc_pdf(obs).replace('\n', '<br/>'), tdc)])
        altos.append(None)
    while len(filas) < 9:
        filas.append([''] * 11)
        altos.append(ft * 2.6)
    t = Table(filas, colWidths=cw, rowHeights=altos, repeatRows=1)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.6, colors.black), ('BACKGROUND', (0, 0), (-1, 0), AZUL_LISTA),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    cab = _cabecera(W, [W * 0.15, W * 0.55], 'REGISTRO DE SEGUIMIENTO QUEJAS', COD_SEGUIMIENTO_QUEJAS, cfg,
                    13.0, 7.2, 16, 1, 2)
    doc.build([cab, Spacer(1, 6), t])
    return buf.getvalue()
