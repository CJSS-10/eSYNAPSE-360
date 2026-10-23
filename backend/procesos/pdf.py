"""
Formatos impresos de Procesos: la Ficha de Caracterización de Procesos (con la
disposición de su plantilla en Excel) y el Mapa de Procesos, dibujado desde el
catálogo.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _logo_celda, control_formato, esc_pdf

COD_FICHA = 'SIG-M-01-r03'
COD_MAPA = 'SIG-M-01-r02'
# Caja de control de cada formato (versión y fecha del formato, no de la ficha):
# se toman de la lista maestra cuando el formato está vinculado; si no, estos
# valores, que son los de las plantillas.
CONTROL_FORMATOS.setdefault(COD_FICHA, ('01', '2025-02-22', 'ASIG', 'GSIG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_MAPA, ('00', '2025-01-10', 'ASIG', 'GSIG', 'GG'))

AZUL = colors.HexColor('#2F5496')          # franjas de títulos de la plantilla
CELESTE = colors.HexColor('#BDD6EE')       # casilla del nombre del proceso
CELESTE_SUB = colors.HexColor('#B4C6E7')   # subtítulos de sección
# Anchos de las columnas B a Q de la plantilla
ANCHOS = [11.57, 14.14, 16.43, 19.14, 17.43, 14.71, 13.57, 14, 17.29, 11.57, 15.14, 13.28, 15.57, 7.14, 8.43, 15.14]
COLS = 'BCDEFGHIJKLMNOPQ'


class _Grilla:
    """Tabla de 16 columnas (B a Q) como la ficha en Excel; las filas crecen con el texto."""

    def __init__(self, W, fs):
        total = sum(ANCHOS)
        self.cw = [W * a / total for a in ANCHOS]
        self.filas, self.minimos, self.est = [], [], []
        self.fs = fs
        base = dict(fontSize=fs, leading=fs * 1.25)
        self.st = {
            'azul': ParagraphStyle('pfaz', fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.white,
                                   **base),
            'sub': ParagraphStyle('pfsu', fontName='Helvetica-Bold', alignment=TA_CENTER, **base),
            'etq': ParagraphStyle('pfet', fontName='Helvetica-Bold', alignment=TA_CENTER, **base),
            'etql': ParagraphStyle('pfel', fontName='Helvetica-Bold', alignment=TA_LEFT, **base),
            'negc': ParagraphStyle('pfnc', fontName='Helvetica-Bold', alignment=TA_CENTER, **base),
            'negl': ParagraphStyle('pfnl', fontName='Helvetica-Bold', alignment=TA_LEFT, **base),
            'val': ParagraphStyle('pfva', fontName='Helvetica', alignment=TA_CENTER, **base),
            'vall': ParagraphStyle('pfvl', fontName='Helvetica', alignment=TA_LEFT, **base),
        }

    def _c(self, letra):
        return COLS.index(letra)

    def fila(self, minimo, tramos, filas=1):
        """tramos: (col_desde, col_hasta, texto, estilo, fondo). `filas` > 1: el
        primer tramo abarca varias filas (se completan con fila_vacia)."""
        r = len(self.filas)
        fila = [''] * 16
        for a, b, texto, estilo, fondo, *alto_filas in tramos:
            i, j = self._c(a), self._c(b)
            nf = alto_filas[0] if alto_filas else 1
            fila[i] = Paragraph(esc_pdf(texto) or '&nbsp;', self.st[estilo])
            if j > i or nf > 1:
                self.est.append(('SPAN', (i, r), (j, r + nf - 1)))
            if fondo is not None:
                self.est.append(('BACKGROUND', (i, r), (j, r + nf - 1), fondo))
        self.filas.append(fila)
        self.minimos.append(minimo)

    def tabla(self):
        # Alto de cada fila según el texto que contiene en el ancho de su tramo.
        altos = list(self.minimos)
        spans = {e[1]: e[2] for e in self.est if e[0] == 'SPAN'}
        for r, fila in enumerate(self.filas):
            for i, celda in enumerate(fila):
                if not isinstance(celda, Paragraph):
                    continue
                (j, r2) = spans.get((i, r), (i, r))
                ancho = sum(self.cw[i:j + 1]) - 6
                h = celda.wrap(ancho, 5000)[1] + 6
                nf = r2 - r + 1
                if nf == 1:
                    altos[r] = max(altos[r], h)
                else:
                    falta = h - sum(altos[r:r2 + 1])
                    if falta > 0:
                        altos[r2] += falta
        t = Table(self.filas, colWidths=self.cw, rowHeights=altos, repeatRows=0)
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.6, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                               ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
                              + self.est))
        return t


def _cabecera(W, cw_logo, cw_titulo, titulo, datos, cfg, alto, fs):
    """Logo, título y caja de control: código, versión, fecha; elaborado, revisado, aprobado."""
    lb = ParagraphStyle('pchl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    vl = ParagraphStyle('pchv', fontName='Helvetica', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER)
    tit = ParagraphStyle('pcht', fontName='Helvetica-Bold', fontSize=fs * 1.6, leading=fs * 1.9, alignment=TA_CENTER)
    resto = W - cw_logo - cw_titulo
    c = [resto * x for x in (0.30, 0.17, 0.20, 0.33)]
    data = [
        [_logo_celda(cfg, cw_logo - 6, alto * 5 - 6), Paragraph(titulo, tit), Paragraph('Código:', lb), '',
         Paragraph(esc_pdf(datos['codigo']), vl), ''],
        ['', '', Paragraph('Versión:', lb), '', Paragraph(esc_pdf(datos['version']), vl), ''],
        ['', '', Paragraph('Fecha:', lb), '', Paragraph(esc_pdf(datos['fecha']), vl), ''],
        ['', '', Paragraph('Elaborado:', lb), Paragraph('Revisado:', lb), '', Paragraph('Aprobado:', lb)],
        ['', '', Paragraph(esc_pdf(datos['elaborado']), vl), Paragraph(esc_pdf(datos['revisado']), vl), '',
         Paragraph(esc_pdf(datos['aprobado']), vl)],
    ]
    t = Table(data, colWidths=[cw_logo, cw_titulo] + c, rowHeights=[alto] * 5)
    est = [('BOX', (0, 0), (0, 4), 0.6, colors.black), ('BOX', (1, 0), (1, 4), 0.6, colors.black),
           ('GRID', (2, 0), (5, 4), 0.6, colors.black), ('SPAN', (0, 0), (0, 4)), ('SPAN', (1, 0), (1, 4)),
           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (0, 4), 'CENTER'),
           ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
           ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]
    for r in range(3):
        est += [('SPAN', (2, r), (3, r)), ('SPAN', (4, r), (5, r))]
    for r in (3, 4):
        est += [('SPAN', (3, r), (4, r))]
    t.setStyle(TableStyle(est))
    return t


def generar_ficha_pdf(f) -> bytes:
    """Ficha de Caracterización de Procesos de una versión."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=9 * mm, bottomMargin=9 * mm,
                            title=f'Ficha de caracterización {f.proceso.nombre} v{f.version}')
    W = doc.width
    cfg = _cargar_cfg()
    g = _Grilla(W, 7.2)
    h = 13
    blanco = None

    g.fila(h, [('B', 'E', 'NOMBRE DEL PROCESO', 'azul', AZUL), ('F', 'K', 'OBJETIVO DEL PROCESO', 'azul', AZUL),
               ('L', 'Q', 'RESPONSABLE', 'azul', AZUL)])
    g.fila(h * 2.5, [('B', 'E', f.proceso.nombre.upper(), 'negc', CELESTE), ('F', 'K', f.objetivo, 'negl', blanco),
                     ('L', 'Q', f.responsable.upper(), 'negc', blanco)])
    g.fila(h, [('B', 'K', 'ALCANCE', 'azul', AZUL), ('L', 'Q', 'TIPO DE PROCESO', 'azul', AZUL)])
    tipo = f.proceso.tipo
    marcas = [('Estratégico', 'estrategico'), ('Operativo', 'operativo'), ('Soporte', 'soporte')]
    for k, (etq, clave) in enumerate(marcas):
        tramos = [('L', 'M', etq, 'etq', blanco), ('N', 'Q', 'X' if tipo == clave else '', 'negc', blanco)]
        if k == 0:
            tramos.insert(0, ('B', 'K', f.alcance, 'negc', blanco, 3))
        g.fila(h, tramos)
    g.fila(h, [('B', 'E', 'ENTRADAS', 'azul', AZUL), ('F', 'K', 'DESCRIPCIÓN DEL PROCESO', 'azul', AZUL),
               ('L', 'Q', 'SALIDAS', 'azul', AZUL)])
    g.fila(h * 1.4, [('B', 'C', 'PROCESO', 'azul', AZUL), ('D', 'E', 'ENTRADA', 'azul', AZUL),
                     ('F', 'H', 'ACTIVIDAD', 'azul', AZUL), ('I', 'K', 'MEDIDAS DE CONTROL', 'azul', AZUL),
                     ('L', 'M', 'PROCESO', 'azul', AZUL), ('N', 'Q', 'SALIDAS', 'azul', AZUL)])
    for a in f.actividades.all():
        if a.seccion:
            g.fila(h * 1.2, [('B', 'Q', a.seccion.upper(), 'sub', CELESTE_SUB)])
        g.fila(h * 2.4, [('B', 'C', a.texto_proveedor(), 'val', blanco), ('D', 'E', a.entrada, 'val', blanco),
                         ('F', 'H', a.actividad, 'val', blanco), ('I', 'K', a.control, 'val', blanco),
                         ('L', 'M', a.texto_cliente(), 'val', blanco), ('N', 'Q', a.salida, 'val', blanco)])

    g.fila(h, [('B', 'E', 'DOCUMENTOS ASOCIADOS', 'azul', AZUL), ('F', 'K', 'RECURSOS', 'azul', AZUL),
               ('L', 'Q', 'REGISTROS', 'azul', AZUL)])
    docs = '\n'.join(d.texto() for d in f.documentos.all())
    regs = '\n'.join(r.descripcion for r in f.registros.all())
    g.fila(h * 1.3, [('B', 'E', 'DESCRIPCIÓN', 'etq', blanco), ('F', 'F', 'Humano', 'etql', blanco),
                     ('G', 'K', f.recurso_humano, 'negl', blanco), ('L', 'Q', regs, 'vall', blanco, 3)])
    g.fila(h * 1.3, [('B', 'E', docs, 'vall', blanco, 2), ('F', 'F', 'Económico', 'etql', blanco),
                     ('G', 'K', f.recurso_economico, 'negl', blanco)])
    g.fila(h * 1.3, [('F', 'F', 'Tecnológico', 'etql', blanco), ('G', 'K', f.recurso_tecnologico, 'negl', blanco)])
    g.fila(h, [('B', 'Q', 'SEGUIMIENTO Y MEDICIÓN DEL PROCESO', 'azul', AZUL)])
    g.fila(h, [('B', 'D', 'NOMBRE DEL INDICADOR', 'etq', blanco), ('E', 'I', 'FORMA DE CÁLCULO DEL INDICADOR', 'etq', blanco),
               ('J', 'K', 'META', 'etq', blanco), ('L', 'M', 'FRECUENCIA', 'etq', blanco),
               ('N', 'Q', 'RESPONSABLE', 'etq', blanco)])
    indicadores = list(f.indicadores.all())
    for i in indicadores or [None]:
        g.fila(h * 1.6, [('B', 'D', i.nombre if i else 'Ninguno', 'negc', blanco),
                         ('E', 'I', i.calculo if i else 'Ninguno', 'negc', blanco),
                         ('J', 'K', i.meta if i else 'Ninguno', 'negc', blanco),
                         ('L', 'M', i.get_frecuencia_display() if i else 'Ninguno', 'negc', blanco),
                         ('N', 'Q', i.responsable if i else 'Ninguno', 'negc', blanco)])

    datos = control_formato(COD_FICHA, cfg)
    cab = _cabecera(W, sum(g.cw[:2]), sum(g.cw[2:12]), 'FICHA DE CARACTERIZACIÓN DE PROCESOS', datos, cfg, 13, 7.5)
    elementos = [cab, Spacer(1, 6), g.tabla()]
    doc.build(elementos)
    return buf.getvalue()


# ------------------------------------------------------------------ mapa
VERDE_CLIENTE = colors.HexColor('#92D050')
VERDE_FRANJA = colors.HexColor('#00B050')
ROJO_ETIQUETA = colors.HexColor('#C00000')
AZUL_LINEA = colors.HexColor('#2F5496')
AZUL_ESTRATEGICO = colors.HexColor('#8DA9DB')
AZUL_OSCURO = colors.HexColor('#1F4E79')
AZUL_SOPORTE = colors.HexColor('#2E75B6')
NARANJA = colors.HexColor('#F4B183')
VERDE_CAL = colors.HexColor('#A9D18E')
AMARILLO = colors.HexColor('#FFC000')
FONDO_BANDA = colors.HexColor('#FDF3F3')


class _Mapa(Flowable):
    """Dibujo del mapa: clientes a los lados y las tres bandas de procesos."""

    def __init__(self, ancho, alto, bandas):
        super().__init__()
        self.width, self.height, self.bandas = ancho, alto, bandas

    def _caja(self, c, x, y, w, h, texto, fondo, color_texto=colors.black, fs=7.5, sub=''):
        c.setFillColor(fondo)
        c.setStrokeColor(AZUL_LINEA)
        c.setLineWidth(0.6)
        c.rect(x, y, w, h, fill=1, stroke=1)
        st = ParagraphStyle('mc', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER,
                            textColor=color_texto)
        partes = [Paragraph(esc_pdf(texto), st)]
        if sub:
            partes.append(Paragraph(esc_pdf(sub), ParagraphStyle('ms', parent=st, fontSize=fs * 0.72,
                                                                  leading=fs * 0.9,
                                                                  textColor=colors.HexColor('#1F3864'))))
        alturas = [p.wrap(w - 6, h)[1] for p in partes]
        yy = y + (h + sum(alturas)) / 2
        for p, a in zip(partes, alturas):
            yy -= a
            p.drawOn(c, x + 3, yy)

    def _flecha(self, c, x1, y, x2):
        c.setStrokeColor(colors.HexColor('#ED7D31'))
        c.setLineWidth(0.8)
        c.line(x1, y, x2, y)
        c.setFillColor(colors.HexColor('#ED7D31'))
        p = c.beginPath()
        p.moveTo(x2, y)
        p.lineTo(x2 - 4, y + 2.2)
        p.lineTo(x2 - 4, y - 2.2)
        p.close()
        c.drawPath(p, fill=1, stroke=0)

    def _flecha_bloque(self, c, x, y, arriba):
        c.setFillColor(AMARILLO)
        c.setStrokeColor(AZUL_LINEA)
        c.setLineWidth(0.4)
        w, h = 14, 11
        p = c.beginPath()
        if arriba:
            p.moveTo(x, y + h)
            p.lineTo(x - w / 2, y + h * 0.45)
            p.lineTo(x - w / 4, y + h * 0.45)
            p.lineTo(x - w / 4, y)
            p.lineTo(x + w / 4, y)
            p.lineTo(x + w / 4, y + h * 0.45)
            p.lineTo(x + w / 2, y + h * 0.45)
        else:
            p.moveTo(x, y)
            p.lineTo(x - w / 2, y + h * 0.55)
            p.lineTo(x - w / 4, y + h * 0.55)
            p.lineTo(x - w / 4, y + h)
            p.lineTo(x + w / 4, y + h)
            p.lineTo(x + w / 4, y + h * 0.55)
            p.lineTo(x + w / 2, y + h * 0.55)
        p.close()
        c.drawPath(p, fill=1, stroke=1)

    def _cliente(self, c, x, y, w, h, titulo, lineas):
        c.setFillColor(VERDE_CLIENTE)
        c.roundRect(x, y, w, h, 8, fill=1, stroke=0)
        st = ParagraphStyle('mcl', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER,
                            textColor=colors.white)
        sl = ParagraphStyle('mcs', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_CENTER,
                            textColor=colors.white)
        partes = [Paragraph(titulo, st)] + [Paragraph(esc_pdf(t), sl) for t in lineas]
        alturas = [p.wrap(w - 6, h)[1] + 6 for p in partes]
        yy = y + (h + sum(alturas)) / 2
        for p, a in zip(partes, alturas):
            yy -= a
            p.drawOn(c, x + 3, yy + 3)

    def _banda(self, c, x, y, w, h, etiqueta):
        c.setFillColor(FONDO_BANDA)
        c.setStrokeColor(AZUL_LINEA)
        c.setDash(4, 2)
        c.setLineWidth(1)
        c.rect(x, y, w, h, fill=1, stroke=1)
        c.setDash()
        c.setFillColor(ROJO_ETIQUETA)
        c.rect(x, y + h - 11, 120, 11, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 6.5)
        c.drawString(x + 6, y + h - 8, etiqueta)

    def draw(self):
        c = self.canv
        W, H = self.width, self.height
        cw = 62
        self._cliente(c, 0, 0, cw, H, 'CLIENTE', ['Contexto interno y externo', 'Partes interesadas',
                                                  'Requisitos del cliente'])
        self._cliente(c, W - cw, 0, cw, H, 'CLIENTE', ['Satisfacción del cliente', 'Resultados previstos del SIG'])
        x0, x1 = cw + 10, W - cw - 10
        ancho = x1 - x0
        gap = 14
        alturas = {'estrategico': 0.27, 'operativo': 0.42, 'soporte': 0.25}
        disp = H - 2 * gap
        y = H
        centros = []
        for banda in self.bandas:
            bh = disp * alturas[banda['tipo']]
            y -= bh
            self._banda(c, x0, y, ancho, bh, banda['etiqueta'])
            self._dibujar_banda(c, banda, x0 + 8, y + 6, ancho - 16, bh - 22)
            centros.append(y)
            y -= gap
        # flechas entre bandas (izquierda baja, derecha sube)
        for k in range(len(centros) - 1):
            yb = centros[k] - gap + 1
            self._flecha_bloque(c, x0 + ancho * 0.2, yb, arriba=False)
            self._flecha_bloque(c, x0 + ancho * 0.6, yb, arriba=True)

    def _dibujar_banda(self, c, banda, x, y, w, h):
        procesos = banda['procesos']
        if not procesos:
            return
        tipo = banda['tipo']
        if tipo == 'estrategico':
            pesos = [2 if p['subprocesos'] else 1 for p in procesos]
            sep = 30
            unidad = (w - sep * (len(procesos) - 1)) / sum(pesos)
            xx = x
            bh = min(h * 0.75, 52)
            yy = y + (h - bh) / 2
            for k, p in enumerate(procesos):
                bw = unidad * pesos[k]
                sub = ' · '.join(s['nombre'] for s in p['subprocesos'])
                titulo = p['nombre'] + (f'\n({p["detalle_mapa"]})' if p['detalle_mapa'] else '')
                self._caja(c, xx, yy, bw, bh, titulo, AZUL_ESTRATEGICO, colors.white, 8, sub)
                if k:
                    self._flecha(c, xx - sep, yy + bh / 2, xx)
                xx += bw + sep
        elif tipo == 'operativo':
            sep = 18
            n = len(procesos)
            pesos = [3 if p['detalle_mapa'] else 1 for p in procesos]
            unidad = (w - sep * (n - 1)) / sum(pesos)
            xx = x
            for k, p in enumerate(procesos):
                bw = unidad * pesos[k]
                if p['detalle_mapa']:
                    self._proceso_con_etapas(c, p, xx, y, bw, h)
                else:
                    bh = 34
                    self._caja(c, xx, y + (h - bh) / 2, bw, bh, p['nombre'], AZUL_OSCURO, colors.white, 8)
                if k:
                    self._flecha(c, xx - sep, y + h / 2, xx)
                xx += bw + sep
        else:
            sep = 14
            n = len(procesos)
            bw = (w - sep * (n - 1)) / n
            bh = min(h * 0.7, 34)
            yy = y + (h - bh) / 2
            for k, p in enumerate(procesos):
                xx = x + k * (bw + sep)
                self._caja(c, xx, yy, bw, bh, p['nombre'], AZUL_SOPORTE, colors.white, 7.5)
                if k:
                    self._flecha(c, xx - sep, yy + bh / 2, xx)

    def _proceso_con_etapas(self, c, p, x, y, w, h):
        """Proceso cuyas etapas se muestran dentro de su recuadro (p. ej. Metrología)."""
        c.setStrokeColor(colors.HexColor('#F4B183'))
        c.setDash(3, 2)
        c.rect(x, y, w, h, fill=0, stroke=1)
        c.setDash()
        c.setFillColor(colors.black)
        c.setFont('Helvetica-Bold', 7.5)
        c.drawString(x + 6, y + h - 10, p['nombre'])
        etapas = [e.strip() for e in p['detalle_mapa'].split('→') if e.strip()]
        n = len(etapas)
        sep = 16
        bw = (w - 12 - sep * (n - 1)) / n
        bh = min(h * 0.5, 34)
        yy = y + (h - 12 - bh) / 2
        fondos = [NARANJA, VERDE_CAL, AZUL_OSCURO]
        for k, e in enumerate(etapas):
            xx = x + 6 + k * (bw + sep)
            fondo = fondos[k % 3] if n == 3 else (VERDE_CAL if 0 < k < n - 1 else NARANJA)
            self._caja(c, xx, yy, bw, bh, e, fondo, colors.white if fondo == AZUL_OSCURO else colors.black, 7.5)
            if k:
                self._flecha(c, xx - sep, yy + bh / 2, xx)


def generar_mapa_pdf() -> bytes:
    """Mapa de Procesos, armado desde el catálogo vigente."""
    from .models import TIPOS_PROCESO, Proceso  # noqa: F401
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=9 * mm, bottomMargin=9 * mm, title='Mapa de procesos')
    W = doc.width
    cfg = _cargar_cfg()
    bandas = []
    for t, nombre in TIPOS_PROCESO:
        procs = []
        for p in Proceso.objects.filter(is_active=True, padre__isnull=True, tipo=t):
            procs.append({'nombre': p.nombre, 'detalle_mapa': p.detalle_mapa,
                          'subprocesos': [{'nombre': s.nombre} for s in p.subprocesos.filter(is_active=True)]})
        bandas.append({'tipo': t, 'procesos': procs,
                       'etiqueta': {'estrategico': 'PROCESOS ESTRATÉGICOS', 'operativo': 'PROCESOS PRINCIPALES',
                                    'soporte': 'PROCESOS DE SOPORTE'}[t]})
    datos = control_formato(COD_MAPA, cfg)
    cab = _cabecera(W, W * 0.13, W * 0.55, 'MAPA DE PROCESOS', datos, cfg, 13, 7.5)
    franja = Table([[Paragraph('Secuencia e Interacción de procesos',
                               ParagraphStyle('mfr', fontName='Helvetica-Bold', fontSize=10, leading=12,
                                              alignment=TA_CENTER, textColor=colors.white))]],
                   colWidths=[W], rowHeights=[16])
    franja.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), VERDE_FRANJA), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    alto = doc.height - 5 * 13 - 16 - 48
    leyenda = Paragraph('<font color="#2F5496">■</font> Procesos contemplados en el alcance del SIG',
                        ParagraphStyle('mly', fontName='Helvetica', fontSize=7, leading=9))
    doc.build([cab, Spacer(1, 5), franja, Spacer(1, 6), _Mapa(W, alto, bandas), Spacer(1, 4), leyenda])
    return buf.getvalue()
