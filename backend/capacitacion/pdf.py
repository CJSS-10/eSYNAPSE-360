"""
Formatos impresos de Capacitación e inducción, con la disposición de sus plantillas: Lista de asistencia, Programa
anual de capacitación (con el pie del Comité de SST) e Inducción al personal (una hoja por parte).
"""
from django.utils import timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _solo_fecha, esc_pdf
from quejas.pdf import _cabecera

from .models import PARTES_INDUCCION, TEMAS_ASISTENCIA, TIPOS_ACTIVIDAD

COD_INDUCCION, COD_LISTA, COD_PROGRAMA = 'TH-PRO-01-r05', 'TH-PRO-01-r06', 'TH-PRO-01-r09'
# Respaldo de la caja de control mientras el formato no esté vinculado a la lista maestra.
CONTROL_FORMATOS.setdefault(COD_INDUCCION, ('00', '2025-11-28', 'ASIG', 'GSIG/GG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_LISTA, ('02', '2026-05-15', 'CADM', 'GSIG/GG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_PROGRAMA, ('02', '2026-02-13', 'ASIG', 'GSIG/GT', 'GG'))

AZUL = colors.HexColor('#1F3864')
CELESTE = colors.HexColor('#DCE6F1')
GRIS = colors.HexColor('#D9D9D9')
VERDE = colors.HexColor('#C6EFCE')
AMBAR = colors.HexColor('#FFEB9C')
MESES = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SET', 'OCT', 'NOV', 'DIC']
METODO = {'usuario': 'Firmado con su usuario', 'pin': 'Firmado con PIN', 'papel': 'Firma en lista adjunta',
          'carga': 'Firmado en el formato original'}


def _estilos(fs):
    return {'th': ParagraphStyle('cth', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER,
                                 textColor=colors.white),
            'thn': ParagraphStyle('cthn', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2,
                                  alignment=TA_CENTER),
            'thl': ParagraphStyle('cthl', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.2, alignment=TA_LEFT),
            'td': ParagraphStyle('ctd', fontName='Helvetica', fontSize=fs, leading=fs * 1.25, alignment=TA_CENTER),
            'tdl': ParagraphStyle('ctdl', fontName='Helvetica', fontSize=fs, leading=fs * 1.25, alignment=TA_LEFT),
            'fi': ParagraphStyle('cfi', fontName='Helvetica-Oblique', fontSize=fs - 0.5, leading=fs * 1.2,
                                 alignment=TA_CENTER, textColor=colors.HexColor('#1F4E79'))}


def _P(t, st):
    return Paragraph(esc_pdf('' if t is None else str(t)).replace('\n', '<br/>'), st)


def _grid(t, extra=()):
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                           ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)] + list(extra)))
    return t


def _firma_txt(f):
    if not f:
        return ''
    txt = METODO.get(f.get('metodo'), 'Firmado')
    return f'{txt}<br/>{_solo_fecha(f.get("fecha") or "")}' if f.get('fecha') else txt


def _hora(h):
    return h.strftime('%I:%M %p').lower().lstrip('0').replace('am', 'a.m.').replace('pm', 'p.m.') if h else ''


# ------------------------------------------------------------------------------- lista de asistencia
def generar_lista_asistencia_pdf(s) -> bytes:
    from sst.pdf_eventos import _empleador
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm, topMargin=8 * mm,
                            bottomMargin=8 * mm, title=f'Lista de asistencia {s.codigo}')
    W, cfg = doc.width, _cargar_cfg()
    st = _estilos(7)
    th, td, tdl, fi = st['th'], st['td'], st['tdl'], st['fi']
    emp = _empleador(cfg)
    asist = list(s.asistentes.filter(is_active=True).select_related('trabajador__puesto'))
    n = 24
    cw = [W / n] * n
    story = [_cabecera(W, cw, 'LISTA DE ASISTENCIA', COD_LISTA, cfg, 12, 7, 13, 5, 17), Spacer(1, 5)]

    def barra(celdas, anchos, azules):
        t = Table([[(_P(c, th) if k in azules else _P(c, tdl)) for k, c in enumerate(celdas)]],
                  colWidths=[W * a for a in anchos])
        return _grid(t, [('BACKGROUND', (k, 0), (k, 0), AZUL) for k in azules])
    capacitador = s.capacitador + (f' ({s.entidad})' if s.externo and s.entidad else '')
    story += [barra(['CAPACITADOR:', capacitador, 'FIRMA:', '', 'FECHA:', _solo_fecha(s.fecha.isoformat())],
                    [0.16, 0.34, 0.08, 0.2, 0.08, 0.14], [0, 2, 4]), Spacer(1, 4),
              barra(['RAZÓN SOCIAL:', emp[0], 'RUC:', emp[1]], [0.16, 0.5, 0.1, 0.24], [0, 2]),
              barra(['ACTIVIDAD ECONÓMICA:', emp[3], 'DIRECCIÓN:', emp[2]], [0.16, 0.34, 0.12, 0.38], [0, 2])]
    # Desde / hasta / trabajadores, tipo y temas (cuadrícula del formato)
    tipos = dict(TIPOS_ACTIVIDAD)
    orden_tipo = [['induccion', 'difusion'], ['reunion_inicio', 'simulacro'], ['curso', 'capacitacion'],
                  ['reunion', 'entrenamiento'], ['sensibilizacion', 'otros']]
    temas = dict(TEMAS_ASISTENCIA)

    def marca(k, sel):
        return 'X' if k in sel else ''
    sel_t = {s.tipo_actividad}
    sel_m = set(s.temas or [])
    filas = []
    duracion = f'{s.duracion_horas:g} h'.replace('.', ',') if s.duracion_horas else ''
    izq = [[_P('DESDE:', th), _P('HASTA:', th), _P('N° TRABAJADORES:', th)],
           [_P(_hora(s.hora_desde), td), _P(_hora(s.hora_hasta), td), _P(len(asist), td)],
           [_P('DURACIÓN (HORAS/MINUTOS):', th), '', _P(duracion, td)],
           ['', '', ''], ['', '', '']]
    for r in range(5):
        a, b = orden_tipo[r]
        tema = list(temas)[r] if r < len(temas) else None
        etq_a = tipos[a] + (f': {s.get_tipo_actividad_display()}' if a == 'otros' and s.tipo_actividad == 'otros'
                            else '')
        etq_b = tipos[b]
        if b == 'otros':
            etq_b = 'OTROS:'
        fila = izq[r] + [Paragraph('T<br/>I<br/>P<br/>O' if r == 0 else '', th), _P(etq_a.upper(), td), _P(marca(a, sel_t), td),
                         _P(etq_b.upper(), td), _P(marca(b, sel_t), td), Paragraph('T<br/>E<br/>M<br/>A<br/>S' if r == 0 else '', th)]
        if tema:
            etq = temas[tema].upper() if tema != 'otros' else f'OTROS: {s.otros_temas}'.upper()
            fila += [_P(etq, td), _P(marca(tema, sel_m), td)]
        else:
            fila += ['', '']
        filas.append(fila)
    anchos = [0.09, 0.09, 0.1, 0.035, 0.19, 0.035, 0.19, 0.035, 0.035, 0.17, 0.035]
    t = Table(filas, colWidths=[W * a / sum(anchos) for a in anchos])
    story.append(_grid(t, [('BACKGROUND', (0, 0), (2, 0), AZUL), ('BACKGROUND', (0, 2), (1, 2), AZUL),
                           ('SPAN', (0, 2), (1, 2)), ('SPAN', (0, 3), (2, 4)),
                           ('SPAN', (3, 0), (3, 4)), ('BACKGROUND', (3, 0), (3, 4), AZUL),
                           ('SPAN', (8, 0), (8, 4)), ('BACKGROUND', (8, 0), (8, 4), AZUL)]))
    story += [barra(['MATERIAL ENTREGADO:', s.material_entregado], [0.2, 0.8], [0]), Spacer(1, 4),
              barra(['TEMA TRATADO:', s.tema_tratado], [0.16, 0.84], [0]), Spacer(1, 4)]
    cab = [_P(x, th) for x in ('N°', 'APELLIDOS Y NOMBRES', 'DNI/CE', 'CARGO', 'FIRMA')]
    if s.con_evaluacion:
        cab.insert(4, _P('NOTA', th))
    filas = [cab]
    for k, a in enumerate(asist, 1):
        fila = [_P(k, td), _P(a.trabajador.nombre_completo, tdl), _P(a.trabajador.documento, td),
                _P(a.trabajador.puesto.nombre, td), Paragraph(_firma_txt(a.firma), fi)]
        if s.con_evaluacion:
            fila.insert(4, _P('' if a.nota is None else f'{a.nota:g}', td))
        filas.append(fila)
    for k in range(len(asist) + 1, max(len(asist) + 1, 26)):
        filas.append([_P(k, td), '', '', '', ''] + ([''] if s.con_evaluacion else []))
    anchos = [0.05, 0.38, 0.14, 0.2, 0.08, 0.15] if s.con_evaluacion else [0.05, 0.42, 0.15, 0.2, 0.18]
    t = Table(filas, colWidths=[W * a for a in anchos], repeatRows=1)
    story += [_grid(t, [('BACKGROUND', (0, 0), (-1, 0), AZUL)]), Spacer(1, 6)]
    fr = s.firma_registro or {}
    obs = Table([[_P('OBSERVACIONES/ANOTACIONES:', th), _P('RESPONSABLE DEL REGISTRO:', th), ''],
                 [_P(s.observaciones, tdl), _P('NOMBRE:', th), _P(fr.get('nombre', ''), tdl)],
                 ['', _P('CARGO:', th), _P(fr.get('cargo', ''), tdl)],
                 ['', _P('FECHA:', th), _P(_solo_fecha(fr.get('fecha') or ''), tdl)],
                 ['', _P('FIRMA:', th), Paragraph('Firmado con su usuario' if fr else '', fi)]],
                colWidths=[W * 0.6, W * 0.1, W * 0.3])
    story.append(KeepTogether(_grid(obs, [('SPAN', (1, 0), (2, 0)), ('SPAN', (0, 1), (0, 4)),
                                          ('BACKGROUND', (0, 0), (-1, 0), AZUL),
                                          ('BACKGROUND', (1, 1), (1, 4), AZUL), ('VALIGN', (0, 1), (0, 4), 'TOP')])))
    doc.build(story)
    return buf.getvalue()


# ------------------------------------------------------------------------------- programa anual
def generar_programa_pdf(p) -> bytes:
    from sst.pdf_eventos import _empleador
    from .views import _indicadores
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A3), leftMargin=8 * mm, rightMargin=8 * mm, topMargin=8 * mm,
                            bottomMargin=8 * mm, title=f'Programa anual de capacitación {p.anio}')
    W, cfg = doc.width, _cargar_cfg()
    st = _estilos(7)
    th, thn, td, tdl = st['th'], st['thn'], st['td'], st['tdl']
    n = 40
    cw = [W / n] * n
    story = [_cabecera(W, cw, f'PROGRAMA ANUAL DE CAPACITACIÓN {p.anio}', COD_PROGRAMA, cfg, 13, 7.5, 15, 6, 28),
             Spacer(1, 5)]
    ind = _indicadores(p)
    hoy_txt = _solo_fecha(str(timezone.localtime(p.modificado_en).date() if p.modificado_en else timezone.localtime(p.updated_at).date()))
    res = Table([[_P('Fecha de actualización:', thn), _P(hoy_txt, td), '', _P('LEYENDA', thn), _P('P', td),
                  _P('Programado', tdl)],
                 [_P('N° Programadas', thn), _P(ind['programadas'], td), _P('% Avance del programa', thn),
                  _P(f'{ind["avance"] or 0} %', td), _P('R', td), _P('Realizado', tdl)],
                 [_P('N° Realizadas', thn), _P(ind['realizadas'], td), _P('Año', thn), _P(p.anio, td), _P('RP', td),
                  _P('Reprogramado', tdl)]],
                colWidths=[W * 0.1, W * 0.07, W * 0.1, W * 0.07, W * 0.03, W * 0.08], hAlign='LEFT')
    story += [_grid(res, [('BACKGROUND', (0, 0), (0, -1), CELESTE), ('BACKGROUND', (2, 1), (2, 2), CELESTE),
                          ('BACKGROUND', (4, 1), (4, 1), VERDE), ('BACKGROUND', (4, 2), (4, 2), AMBAR)]),
              Spacer(1, 5)]
    cab1 = [_P(x, th) for x in ('Capacitación', 'Responsable capacitación', 'Personal a capacitar', 'Fecha programada',
                                'Fecha realizada', 'Horas', 'Tipo', 'Estado')]
    cab1 += sum([[_P(m, th), ''] for m in MESES], []) + [_P('V°B°', th)]
    cab2 = [''] * 8 + sum([[_P('P', th), _P('R', th)] for _ in MESES], []) + ['']
    filas, est = [cab1, cab2], []
    for c in range(8):
        est.append(('SPAN', (c, 0), (c, 1)))
    for k in range(12):
        est.append(('SPAN', (8 + 2 * k, 0), (9 + 2 * k, 0)))
    est.append(('SPAN', (32, 0), (32, 1)))
    ESTADO = {'realizado': 'Realizado', 'programado': 'Programado', 'reprogramado': 'Reprogramado',
              'atrasado': 'Atrasado', 'cancelado': 'Cancelado'}
    items = list(p.items.filter(is_active=True).prefetch_related('areas', 'puestos'))
    from .views import ItemSerializer
    totales = [[0, 0] for _ in MESES]
    horas = 0
    for i in items:
        r = len(filas)
        dirigido = ItemSerializer().get_dirigido(i)
        fila = [_P(i.tema, tdl), _P(i.responsable, td), _P(dirigido, td), _P(_solo_fecha(i.fecha_programada.isoformat()), td),
                _P(_solo_fecha(i.fecha_realizada.isoformat()) if i.fecha_realizada else '', td),
                _P(f'{i.horas:g}', td), _P(i.get_tipo_display(), td), _P(ESTADO.get(i.estado, ''), td)]
        celdas = [''] * 24
        mp = i.fecha_programada.month - 1
        celdas[2 * mp] = 'P'
        totales[mp][0] += 1
        if i.cancelado:
            celdas[2 * mp + 1] = '—'
        elif i.fecha_realizada:
            if i.reprogramaciones:
                celdas[2 * mp + 1] = 'RP'
                est.append(('BACKGROUND', (9 + 2 * mp, r), (9 + 2 * mp, r), AMBAR))
            mr = i.fecha_realizada.month - 1
            celdas[2 * mr + 1] = 'R'
            totales[mr][1] += 1
            est.append(('BACKGROUND', (9 + 2 * mr, r), (9 + 2 * mr, r), VERDE))
            horas += float(i.horas)
        elif i.reprogramaciones:
            celdas[2 * mp + 1] = 'RP'
            est.append(('BACKGROUND', (9 + 2 * mp, r), (9 + 2 * mp, r), AMBAR))
            fv = i.fecha_vigente
            if fv.month - 1 != mp and fv.year == p.anio:
                celdas[2 * (fv.month - 1)] = 'P'
        filas.append(fila + [_P(x, td) for x in celdas] + [_P(i.vb, td)])
    filas.append(['', '', _P('TOTAL', thn), '', '', _P(f'{sum(float(i.horas) for i in items if not i.cancelado):g}', thn),
                  '', ''] + sum([[_P(a, thn), _P(b, thn)] for a, b in totales], []) + [''])
    anchos = [5.2, 2.2, 2.2, 1.5, 1.5, 0.8, 1.3, 1.5] + [0.55] * 24 + [0.9]
    t = Table(filas, colWidths=[W * a / sum(anchos) for a in anchos], repeatRows=2)
    story += [_grid(t, est + [('BACKGROUND', (0, 0), (-1, 1), AZUL), ('BACKGROUND', (0, -1), (-1, -1), CELESTE)]),
              Spacer(1, 8)]
    # Pie: empleador y aprobación del Comité de SST
    emp = _empleador(cfg)
    e = Table([[_P(x, th) for x in ('RAZÓN SOCIAL O DENOMINACIÓN SOCIAL:', 'RUC:', 'DOMICILIO (Dirección, distrito, '
                                    'departamento, provincia)', 'ACTIVIDAD ECONÓMICA',
                                    'N° TRABAJADORES EN EL CENTRO LABORAL')],
               [_P(x, td) for x in emp]], colWidths=[W * x for x in (0.2, 0.1, 0.38, 0.2, 0.12)])
    ap = p.aprobacion or {}
    pendiente = p.estado_aprobacion in ('pendiente', 'sin_aprobar')
    from sst.comite_pdf import bloque_firmas_comite
    nota = ('PENDIENTE DE APROBACIÓN DEL COMITÉ DE SST' + (
        f': el programa cambió después de su aprobación del {_solo_fecha(ap.get("fecha", ""))}.'
        if ap.get('fecha') else '.')) if pendiente else None
    pie = [_grid(e, [('BACKGROUND', (0, 0), (-1, 0), AZUL)]), Spacer(1, 3)] + bloque_firmas_comite(
        W, ap.get('firmas', []), fecha=ap.get('fecha'), nota=nota)
    el = p.elaborado or {}
    pie += [Spacer(1, 3), _grid(Table([[_P('ELABORADO POR', th), _P(f"{el.get('nombre', '')} — {el.get('cargo', '')}",
                                                                      tdl)]], colWidths=[W * 0.12, W * 0.4],
                                      hAlign='LEFT'), [('BACKGROUND', (0, 0), (0, 0), AZUL)])]
    story.append(KeepTogether(pie))
    doc.build(story)
    return buf.getvalue()


# ----------------------------------------------------------------------------------- inducción
def generar_induccion_pdf(ind) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=8 * mm,
                            bottomMargin=8 * mm, title=f'Inducción {ind.codigo}')
    W, cfg = doc.width, _cargar_cfg()
    st = _estilos(7)
    th, thn, td, tdl, fi = st['th'], st['thn'], st['td'], st['tdl'], st['fi']
    t = ind.trabajador
    area = t.area_efectiva.nombre if t.area_efectiva else ''
    story = []
    for n, (clave, nombre) in enumerate(PARTES_INDUCCION):
        p = ind.ultima(clave)
        if not p:
            continue
        if story:
            story.append(PageBreak())
        cw = [W / 24] * 24
        story += [_cabecera(W, cw, 'INDUCCIÓN AL PERSONAL', COD_INDUCCION, cfg, 12, 7, 14, 5, 17), Spacer(1, 6)]
        x = 'X'
        cab = Table([[_P('NOMBRE DEL COLABORADOR', th), _P(t.nombre_completo, tdl), _P('ÁREA', th), _P(area, tdl)],
                     [_P('TIPO', th), _P(f'RE-INDUCCIÓN [{x if ind.tipo == "reinduccion" else " "}]   '
                                         f'INDUCCIÓN [{x if ind.tipo == "induccion" else " "}]', tdl),
                      _P('CARGO', th), _P(t.puesto.nombre, tdl)]],
                    colWidths=[W * 0.2, W * 0.4, W * 0.1, W * 0.3])
        story += [_grid(cab, [('BACKGROUND', (0, 0), (0, -1), AZUL), ('BACKGROUND', (2, 0), (2, -1), AZUL)]),
                  Spacer(1, 4)]
        titulo = {'organizacional': '1. INDUCCIÓN ORGANIZACIONAL', 'sig': '1. INDUCCIÓN DEL SISTEMA INTEGRADO DE GESTIÓN',
                  'especifica': '1. INDUCCIÓN ESPECÍFICA AL CARGO'}[clave]
        intento = f'  (intento {p.intento})' if p.intento > 1 else ''

        def seccion(txt):
            return _grid(Table([[_P(txt, th)]], colWidths=[W]), [('BACKGROUND', (0, 0), (-1, -1), AZUL),
                                                                 ('ALIGN', (0, 0), (-1, -1), 'LEFT')])
        story += [seccion(titulo + intento), Spacer(1, 2),
                  _grid(Table([[_P('RESPONSABLE', th), _P(p.responsable, tdl), _P('FECHA', th),
                                _P(_solo_fecha(p.fecha.isoformat()) if p.fecha else '', td)],
                               [_P('TIEMPO DE INDUCCIÓN — INICIO', th), _P(_hora(p.hora_inicio), td), _P('FIN', th),
                                _P(_hora(p.hora_fin), td)]], colWidths=[W * 0.25, W * 0.35, W * 0.15, W * 0.25]),
                        [('BACKGROUND', (0, 0), (0, -1), AZUL), ('BACKGROUND', (2, 0), (2, -1), AZUL)]),
                  Spacer(1, 3)]
        if clave == 'organizacional':
            filas = [[_P('TEMA', th), _P('DESCRIPCIÓN', th), _P('CÓDIGO', th), _P('(X)', th)]]
            filas += [[_P(q.get('tema'), td), _P(q.get('descripcion'), td), _P(q.get('codigo') or '-', td),
                       _P('X' if q.get('incluido') else '', td)] for q in p.temas]
            story += [_grid(Table(filas, colWidths=[W * 0.3, W * 0.5, W * 0.12, W * 0.08]),
                            [('BACKGROUND', (0, 0), (-1, 0), AZUL)]), Spacer(1, 4)]
        else:
            filas, est, grupo = [[_P('TEMA / DOCUMENTO', th), _P('CÓDIGO', th), _P('MARCAR (X)', th)]], [], None
            for q in p.temas:
                if q.get('grupo') and q.get('grupo') != grupo:
                    grupo = q['grupo']
                    est += [('SPAN', (0, len(filas)), (-1, len(filas))), ('BACKGROUND', (0, len(filas)), (-1, len(filas)),
                                                                          CELESTE)]
                    filas.append([_P(grupo, st['thl']), '', ''])
                filas.append([_P(q.get('tema'), tdl), _P(q.get('codigo') or '—', td), _P('X' if q.get('incluido') else '', td)])
            story += [_grid(Table(filas, colWidths=[W * 0.68, W * 0.18, W * 0.14]),
                            est + [('BACKGROUND', (0, 0), (-1, 0), AZUL)]), Spacer(1, 4)]
        if p.documentos:
            if clave == 'organizacional':
                story.append(seccion('2. ENTREGA DE DOCUMENTOS'))
                filas = [[_P('DOCUMENTO', th), _P('CÓDIGO', th), _P('ENTREGADO (X)', th)]]
                filas += [[_P(d.get('documento'), td), _P(d.get('codigo') or '-', td), _P('X' if d.get('entregado') else '', td)]
                          for d in p.documentos]
                story += [_grid(Table(filas, colWidths=[W * 0.5, W * 0.3, W * 0.2]),
                                [('BACKGROUND', (0, 0), (-1, 0), AZUL)]), Spacer(1, 4)]
            else:
                story += [_P(('[X] ' if d.get('entregado') else '[  ] ') + f"Se entregó {d.get('documento')}", tdl)
                          for d in p.documentos] + [Spacer(1, 4)]
        num = {'organizacional': '3', 'sig': '2', 'especifica': '2'}[clave]
        story.append(seccion(f'{num}. EVALUACIÓN — {nombre.upper()}'))
        story.append(_P('Instrucciones: Califique de 0 a 20. Nota aprobatoria ≥ 14.', st['thl']))
        story.append(_grid(Table([[_P('EVALUADOR', th), _P(p.evaluador, tdl), _P('FECHA DE EVALUACIÓN', th),
                                   _P(_solo_fecha(p.fecha_evaluacion.isoformat()) if p.fecha_evaluacion else '', td)]],
                                 colWidths=[W * 0.15, W * 0.45, W * 0.2, W * 0.2]),
                           [('BACKGROUND', (0, 0), (0, 0), AZUL), ('BACKGROUND', (2, 0), (2, 0), AZUL)]))
        nota = '' if p.nota is None else f'{p.nota:g}'
        if p.preguntas:
            filas = [[_P('PREGUNTA', th), _P('PUNTOS', th), _P('CALIFICACIÓN', th)]]
            filas += [[_P(q.get('pregunta'), tdl), _P(q.get('puntos'), td),
                       _P('' if q.get('calificacion') in (None, '') else q.get('calificacion'), td)] for q in p.preguntas]
            filas.append([_P('NOTA FINAL (sobre 20):', thn), '', _P(nota, thn)])
            story.append(_grid(Table(filas, colWidths=[W * 0.7, W * 0.1, W * 0.2]),
                               [('BACKGROUND', (0, 0), (-1, 0), AZUL), ('SPAN', (0, -1), (1, -1)),
                                ('BACKGROUND', (0, -1), (-1, -1), GRIS)]))
        else:
            story.append(_grid(Table([[_P('URL DE EVALUACIÓN', th), _P('NOTA FINAL', th)],
                                      [_P(p.evaluacion_url, tdl), _P(nota, thn)]], colWidths=[W * 0.8, W * 0.2]),
                               [('BACKGROUND', (0, 0), (-1, 0), AZUL)]))
        resultado = {'aprobada': 'APROBADA', 'desaprobada': 'DESAPROBADA (se repite esta parte)'}.get(p.estado, '')
        if resultado:
            story.append(_P(f'Resultado: {resultado}', st['thl']))
        story += [Spacer(1, 4), seccion(f'{int(num) + 1}. OBSERVACIONES'),
                  _grid(Table([[_P(p.observaciones, tdl)]], colWidths=[W], rowHeights=[30])), Spacer(1, 8)]
        fr, fc = p.firma_responsable or {}, p.firma_colaborador or {}
        firmas = Table([[_P('FIRMA DEL RESPONSABLE DE LA INDUCCIÓN', th), '', _P('FIRMA DEL COLABORADOR', th)],
                        [Paragraph(_firma_txt(fr), fi), '', Paragraph(_firma_txt(fc), fi)],
                        [_P(f"NOMBRE: {fr.get('nombre', p.responsable)}", tdl), '',
                         _P(f'NOMBRE: {t.nombre_completo}', tdl)],
                        [_P(f"FECHA: {_solo_fecha(fr.get('fecha') or '')}", tdl), '',
                         _P(f"FECHA: {_solo_fecha(fc.get('fecha') or '')}", tdl)]],
                       colWidths=[W * 0.42, W * 0.16, W * 0.42], rowHeights=[None, 34, None, None])
        story.append(KeepTogether(_grid(firmas, [('BACKGROUND', (0, 0), (0, 0), AZUL),
                                                 ('BACKGROUND', (2, 0), (2, 0), AZUL),
                                                 ('LINEBEFORE', (1, 0), (1, -1), 0, colors.white),
                                                 ('LINEAFTER', (1, 0), (1, -1), 0, colors.white),
                                                 ('LINEABOVE', (1, 0), (1, -1), 0, colors.white),
                                                 ('LINEBELOW', (1, 0), (1, -1), 0, colors.white)])))
    doc.build(story)
    return buf.getvalue()
