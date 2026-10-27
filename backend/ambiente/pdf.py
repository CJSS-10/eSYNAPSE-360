"""
Formatos impresos de Medio ambiente, con la disposición de sus plantillas:
- Matriz de identificación de aspectos y evaluación de impactos ambientales (horizontal, por lugar como las hojas del
  libro original; bloques de situación, generación, clase, evaluación de la significancia y control operacional).
- Pesaje de residuos sólidos (vertical: no peligrosos por tacho, peligrosos, RAEE, firma).
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _solo_fecha, esc_pdf
from quejas.pdf import _cabecera

COD_MATRIZ, COD_PESAJE = 'SIG-PRO-14-r01', 'SIG-PRO-19-r01'
# Respaldo de la caja de control mientras el formato no esté vinculado a la lista maestra.
CONTROL_FORMATOS.setdefault(COD_MATRIZ, ('00', '2025-01-10', 'GSIG', 'GSIG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_PESAJE, ('02', '2026-03-19', 'ASIG', 'GSIG/GG', 'GG'))

AZUL_OSC = colors.HexColor('#244061')
LILA = colors.HexColor('#CCC0D9')
CELESTE = colors.HexColor('#95B3D7')
GRIS = colors.HexColor('#D9D9D9')
ROJO = colors.HexColor('#FF0000')
VERDE = colors.HexColor('#008000')


def _st(fs):
    return {'th': ParagraphStyle('ath', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15,
                                 alignment=TA_CENTER, textColor=colors.white),
            'thn': ParagraphStyle('athn', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15,
                                  alignment=TA_CENTER),
            'thl': ParagraphStyle('athl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15),
            'td': ParagraphStyle('atd', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER),
            'tdl': ParagraphStyle('atdl', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_LEFT)}


def _P(t, st):
    return Paragraph(esc_pdf('' if t is None else str(t)).replace('\n', '<br/>'), st)


def _num(v):
    if v in (None, ''):
        return ''
    s = f'{float(v):.2f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',')


# ======================================================================================== matriz de aspectos
def _grupos(aspectos):
    """Agrupa por lugar en el orden de las hojas del libro: toda la empresa, oficinas, laboratorios, cada área."""
    orden = {'empresa': 0, 'oficinas': 1, 'laboratorios': 2, 'areas': 3, 'otro': 4}
    grupos = {}
    for a in aspectos:
        clave = (orden.get(a.alcance, 9), a.lugar_texto)
        grupos.setdefault(clave, []).append(a)
    return [(k[1], v) for k, v in sorted(grupos.items())]


def generar_matriz_pdf(aspectos, aprobacion=None, estado='sin_aprobar') -> bytes:
    cfg = _cargar_cfg()
    buf = BytesIO()
    pag = landscape(A4)
    margen = 7 * mm
    W = pag[0] - 2 * margen
    doc = SimpleDocTemplate(buf, pagesize=pag, leftMargin=margen, rightMargin=margen, topMargin=margen,
                            bottomMargin=margen, title='Matriz de aspectos e impactos ambientales')
    s = _st(5.4)
    # Anchos (mm): proceso, actividad, aspecto, impacto, N A E, D I, + -, controles, A..E, res, sig, control, registro,
    # responsable
    mmw = [20, 26, 24, 24, 7, 7, 7, 8, 8, 8, 8, 22, 7, 7, 7, 7, 7, 9, 10, 32, 20, 18]
    esc = W / (sum(mmw) * mm)
    cw = [x * mm * esc for x in mmw]
    story = [_cabecera(W, cw, 'MATRIZ DE IDENTIFICACIÓN DE ASPECTOS Y EVALUACIÓN DE IMPACTOS AMBIENTALES (IAIA)',
                       COD_MATRIZ, cfg, 7 * mm, 6.5, 10, 2, 19), Spacer(1, 2 * mm)]
    actualizado = max((a.updated_at for a in aspectos), default=None)
    revision = aprobacion.fecha if aprobacion else None
    info = Table([[_P('Fecha de actualización:', s['thl']), _P(_solo_fecha(actualizado) if actualizado else '', s['tdl']),
                   '', _P('Fecha de revisión (aprobación del Comité de SST):', s['thl']),
                   _P(_solo_fecha(revision) if revision else 'Sin aprobar', s['tdl'])]],
                 colWidths=[W * 0.14, W * 0.16, W * 0.30, W * 0.24, W * 0.16])
    info.setStyle(TableStyle([('GRID', (0, 0), (1, 0), 0.5, colors.black), ('GRID', (3, 0), (4, 0), 0.5, colors.black),
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story += [info, Spacer(1, 2 * mm)]

    def cab():
        h1 = ['PROCESO', 'ACTIVIDAD', 'ASPECTO', 'IMPACTO', 'SITUACIÓN', '', '', 'GENERACIÓN', '', 'CLASE', '',
              'CONTROLES EXISTENTES', 'EVALUACIÓN DE LA SIGNIFICANCIA', '', '', '', '', '', '', 'CONTROL OPERACIONAL',
              '', '']
        h2 = ['', '', '', '', 'NORMAL', 'ANORMAL', 'EMERG.', 'DIRECTA', 'INDIRECTA', 'POSITIVO', 'NEGATIVO', '',
              'CUMPL. LEGAL (A)', 'SEVERIDAD (B)', 'PARTES INTER. (C)', 'ESCALA (D)', 'FRECUENCIA (E)',
              'RESULTADO (A+B+C+D+E)', 'SIGNIFI-CANCIA', 'DESCRIPCIÓN DEL CONTROL', 'REGISTRO ASOCIADO', 'RESPONSABLE']
        chico = ParagraphStyle('athc', parent=s['th'], fontSize=4.4, leading=5)
        chico_n = ParagraphStyle('athcn', parent=s['thn'], fontSize=4.4, leading=5)
        return [[_P(x, s['th']) if i < 12 or i > 18 else _P(x, s['thn']) for i, x in enumerate(h1)],
                [_P(x, chico if 4 <= i <= 10 else (chico_n if 12 <= i <= 18 else s['th'])) for i, x in enumerate(h2)]]

    est_cab = [('SPAN', (c, 0), (c, 1)) for c in (0, 1, 2, 3, 11)] + [
        ('SPAN', (4, 0), (6, 0)), ('SPAN', (7, 0), (8, 0)), ('SPAN', (9, 0), (10, 0)), ('SPAN', (12, 0), (18, 0)),
        ('SPAN', (19, 0), (21, 0)), ('BACKGROUND', (0, 0), (11, 1), AZUL_OSC),
        ('BACKGROUND', (12, 0), (18, 1), LILA), ('BACKGROUND', (19, 0), (21, 1), CELESTE)]
    for lugar, lista in _grupos(aspectos):
        filas = cab()
        estilos = list(est_cab)
        for a in lista:
            sig = a.significativo
            res = a.resultado
            control = a.control_operacional or ''
            if sig and a.plazo:
                control += f'\n(Plazo: {_solo_fecha(a.plazo)})'
            x = lambda c: 'X' if c else ''  # noqa: E731
            filas.append([
                _P(a.proceso.nombre if a.proceso_id else 'Todos los procesos', s['tdl']), _P(a.actividad, s['tdl']),
                _P(a.aspecto, s['tdl']), _P(a.impacto, s['tdl']),
                _P(x('N' in a.situaciones), s['td']), _P(x('A' in a.situaciones), s['td']),
                _P(x('E' in a.situaciones), s['td']),
                _P(x(a.generacion == 'directa'), s['td']), _P(x(a.generacion == 'indirecta'), s['td']),
                _P(x(a.clase == 'positivo'), s['td']), _P(x(a.clase == 'negativo'), s['td']),
                _P(a.controles_existentes, s['tdl']),
                *[_P(getattr(a, c) if a.evaluable else '—', s['td'])
                  for c in ('legal', 'severidad', 'partes', 'escala', 'frecuencia')],
                _P(res if res is not None else '—', s['td']),
                Paragraph(f'<font color="{"#FF0000" if sig else "#008000"}"><b>{"SI" if sig else "NO"}</b></font>'
                          if a.evaluable else '—', s['td']),
                _P(control, s['tdl']), _P(a.registro_asociado, s['tdl']),
                _P(a.responsable.nombre if a.responsable_id else '', s['tdl'])])
        banda = Table([[_P(f'LUGAR: {lugar.upper()}', s['th'])]], colWidths=[W])
        banda.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), AZUL_OSC)]))
        t = Table(filas, colWidths=cw, repeatRows=2)
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 1.5), ('RIGHTPADDING', (0, 0), (-1, -1), 1.5),
                               ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)] + estilos))
        story += [banda, t, Spacer(1, 3 * mm)]
    # Pie: aprobación del Comité de SST (bloque común de todo lo que aprueba el Comité)
    from reportlab.platypus import KeepTogether

    from sst.comite_pdf import bloque_firmas_comite
    if aprobacion and estado == 'aprobada':
        bloque = bloque_firmas_comite(W, aprobacion.firmas, fecha=aprobacion.fecha)
    else:
        bloque = bloque_firmas_comite(W, nota=(
            'PENDIENTE DE APROBACIÓN DEL COMITÉ DE SST: la matriz cambió después de su aprobación del '
            f'{_solo_fecha(aprobacion.fecha)}.' if aprobacion else 'PENDIENTE DE APROBACIÓN DEL COMITÉ DE SST.'))
    story.append(KeepTogether(bloque))
    doc.build(story)
    return buf.getvalue()


# ======================================================================================== pesaje de residuos
def generar_pesaje_pdf(p) -> bytes:
    cfg = _cargar_cfg()
    buf = BytesIO()
    margen = 12 * mm
    W = A4[0] - 2 * margen
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=margen, rightMargin=margen, topMargin=margen,
                            bottomMargin=margen, title=f'Pesaje de residuos sólidos {p.codigo}')
    s = _st(7.5)
    cw = [W / 26.0] * 26
    story = [_cabecera(W, cw, 'PESAJE DE RESIDUOS SÓLIDOS', COD_PESAJE, cfg, 7.5 * mm, 7, 12, 4, 18),
             Spacer(1, 3 * mm)]
    r = p.responsable
    datos = Table([[_P('CÓDIGO', s['th']), _P('RESPONSABLE DEL PESAJE', s['th']), _P('CARGO', s['th']),
                    _P('FECHA', s['th']), _P('HORA', s['th'])],
                   [_P(p.codigo, s['td']), _P(r.nombre_completo if r else '', s['td']),
                    _P(r.puesto.nombre if r and r.puesto_id else '', s['td']), _P(_solo_fecha(p.fecha), s['td']),
                    _P(p.hora.strftime('%H:%M') if p.hora else '', s['td'])]],
                  colWidths=[W * 0.15, W * 0.35, W * 0.2, W * 0.15, W * 0.15])
    datos.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), AZUL_OSC),
                               ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story += [datos, Spacer(1, 1.5 * mm),
              _P(f'Tipo de pesaje: {p.get_tipo_display()}', s['tdl']), Spacer(1, 2 * mm)]
    items = p.items or []
    tot = p.totales()

    def de(cat):
        return [i for i in items if i.get('categoria') == cat]

    def seccion(titulo):
        t = Table([[_P(titulo, s['th'])]], colWidths=[W])
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), AZUL_OSC)]))
        return t

    def tabla(filas, anchos, extra=()):
        t = Table(filas, colWidths=anchos)
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                               ('BACKGROUND', (0, 0), (-1, 0), GRIS)] + list(extra)))
        return t

    story.append(seccion('RESIDUOS SÓLIDOS NO PELIGROSOS'))
    for cat, nombre in (('azul', 'Tacho AZUL (kg)'), ('blanco', 'Tacho BLANCO (kg)')):
        filas = [[_P(nombre, s['thl']), '', ''],
                 [_P('Tipos específicos', s['thn']), _P('Observaciones', s['thn']), _P('kg', s['thn'])]]
        for i in de(cat) or [{}]:
            filas.append([_P(i.get('tipo'), s['tdl']), _P(i.get('observaciones'), s['tdl']), _P(_num(i.get('kg')), s['td'])])
        filas.append(['', _P('Subtotal', s['thl']), _P(_num(tot['por_categoria'][cat]['kg']), s['thn'])])
        story += [Spacer(1, 1.5 * mm), tabla(filas, [W * 0.3, W * 0.55, W * 0.15], [('SPAN', (0, 0), (-1, 0))])]
    story += [Spacer(1, 1.5 * mm), Paragraph(f'<b>Total generado (kg): {_num(tot["no_peligrosos_kg"])}</b>', s['tdl']),
              Spacer(1, 3 * mm), seccion('RESIDUOS SÓLIDOS PELIGROSOS — Tacho ROJO')]
    filas = [[_P('Tipos específicos (A)*', s['thn']), _P('L', s['thn']), _P('Observaciones', s['thn']),
              _P('Tipo específico (B)*', s['thn']), _P('kg', s['thn'])]]
    liq, sol = de('rojo_liquido'), de('rojo_solido')
    for k in range(max(len(liq), len(sol), 1)):
        a = liq[k] if k < len(liq) else {}
        b = sol[k] if k < len(sol) else {}
        obs = ' / '.join(x for x in (a.get('observaciones'), b.get('observaciones')) if x)
        filas.append([_P(a.get('tipo'), s['tdl']), _P(_num(a.get('litros')), s['td']), _P(obs, s['tdl']),
                      _P(b.get('tipo'), s['tdl']), _P(_num(b.get('kg')), s['td'])])
    filas.append([_P('Total (L)', s['thl']), _P(_num(tot['peligrosos_litros']), s['thn']), '',
                  _P('Total (kg)', s['thl']), _P(_num(tot['por_categoria']['rojo_solido']['kg']), s['thn'])])
    story += [Spacer(1, 1.5 * mm), tabla(filas, [W * 0.25, W * 0.1, W * 0.3, W * 0.22, W * 0.13]),
              Spacer(1, 3 * mm), seccion('RESIDUOS DE APARATOS ELÉCTRICOS Y ELECTRÓNICOS (RAEE)')]
    filas = [[_P('Descripción', s['thn']), _P('Cantidad', s['thn']), _P('kg', s['thn']), _P('Observaciones', s['thn'])]]
    for i in de('raee') or [{}]:
        filas.append([_P(i.get('tipo'), s['tdl']), _P(i.get('cantidad'), s['td']), _P(_num(i.get('kg')), s['td']),
                      _P(i.get('observaciones'), s['tdl'])])
    filas.append([_P('Total', s['thl']), '', _P(_num(tot['por_categoria']['raee']['kg']), s['thn']), ''])
    story += [Spacer(1, 1.5 * mm), tabla(filas, [W * 0.35, W * 0.12, W * 0.13, W * 0.4])]
    if p.observaciones:
        story += [Spacer(1, 2 * mm), _P(f'Observaciones: {p.observaciones}', s['tdl'])]
    f = p.firma or {}
    firma = (f'Firmado electrónicamente por {f.get("nombre", "")} el {_solo_fecha(f.get("fecha") or "")}'
             if f else ('Anulado: ' + p.motivo_anulacion if p.estado == 'anulado' else 'Pendiente de firma'))
    ft = Table([[_P('Firma', s['thl']), _P(firma, s['tdl'])],
                [_P('Responsable:', s['thl']), _P(r.nombre_completo if r else '', s['tdl'])]],
               colWidths=[W * 0.2, W * 0.5], hAlign='RIGHT')
    ft.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story += [Spacer(1, 5 * mm), ft, Spacer(1, 3 * mm),
              _P('(*) Tipo A: solo envases con residuos líquidos peligrosos del laboratorio (litros). '
                 'Tipo B: residuos peligrosos en kg.', s['tdl']),
              _P('(**) Las pilas se almacenan en contenedores por laboratorio y/o área.', s['tdl'])]
    doc.build(story)
    return buf.getvalue()
