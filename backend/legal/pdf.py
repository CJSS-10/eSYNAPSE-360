"""
Formatos impresos de requisitos legales: Lista de Requisitos Legales y Otros
Requisitos y Matriz de Evaluación de Cumplimiento Legal (una por ámbito), con la
disposición de sus plantillas: cabecera, fecha de actualización, filas agrupadas
por tema y, en la matriz, el % de cumplimiento de cada evaluación del año y el
resumen por tema.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _p_ajustado, _solo_fecha, esc_pdf
from quejas.pdf import _cabecera

from .models import AMBITOS, ActualizacionAmbito, Evaluacion, Obligacion, calificacion

COD_LISTA = 'SIG-PRO-09-r01'
COD_MATRIZ = 'SIG-PRO-09-r02'
# Respaldo de la caja de control mientras el formato no esté vinculado a la lista maestra
# (versión y fecha del procedimiento; firmas acordadas: elabora ASIG, revisa GSIG, aprueba GG).
for _cod in (COD_LISTA, COD_MATRIZ):
    CONTROL_FORMATOS.setdefault(_cod, ('01', '2026-01-02', 'ASIG', 'GSIG', 'GG'))

AZUL = colors.HexColor('#16365C')
AMARILLO = colors.HexColor('#FFFF00')
VERDE = colors.HexColor('#A9D08E')
ROJO = colors.HexColor('#FF7C80')
GRIS = colors.HexColor('#D9D9D9')
COLOR_CAL = {'bueno': VERDE, 'regular': colors.HexColor('#FFC000'), 'malo': ROJO}


def _doc(buf, titulo):
    return SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=8 * mm, rightMargin=8 * mm, topMargin=8 * mm,
                             bottomMargin=8 * mm, title=titulo)


def _estilos(fs):
    return {
        'th': ParagraphStyle('lth', fontName='Helvetica-Bold', fontSize=fs, leading=fs * 1.15, alignment=TA_CENTER,
                             textColor=colors.white),
        'td': ParagraphStyle('ltd', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_CENTER),
        'tdl': ParagraphStyle('ltl', fontName='Helvetica', fontSize=fs, leading=fs * 1.2, alignment=TA_LEFT),
        'sec': ParagraphStyle('lse', fontName='Helvetica-Bold', fontSize=fs + 0.5, leading=fs * 1.3,
                              alignment=TA_CENTER, textColor=colors.white),
    }


# Caracteres que las fuentes base del PDF no tienen (viñetas de Word, ligaduras, guiones especiales).
_REEMPLAZOS = {'\uf0b7': '•', '\uf0a7': '•', '\ufb01': 'fi', '\ufb02': 'fl', '\u2010': '-', '\u2011': '-',
               '\u00ad': '', '\u200b': ''}


def _limpio(texto):
    import unicodedata
    texto = unicodedata.normalize('NFC', str(texto or ''))
    for a, b in _REEMPLAZOS.items():
        texto = texto.replace(a, b)
    return texto


def _celda(texto, estilo, ancho):
    texto = _limpio(texto)
    if '\n' in texto:
        return Paragraph(esc_pdf(texto).replace('\n', '<br/>'), estilo)
    return _p_ajustado(texto, estilo, ancho - 3)


def _fecha_actualizacion(W, fecha, fs=8):
    lb = ParagraphStyle('lfa', fontName='Helvetica-Bold', fontSize=fs, alignment=TA_CENTER, textColor=colors.white)
    vl = ParagraphStyle('lfv', fontName='Helvetica-Bold', fontSize=fs, alignment=TA_CENTER)
    t = Table([[Paragraph('Fecha de Actualización:', lb), Paragraph(esc_pdf(_solo_fecha(fecha) if fecha else ''), vl)]],
              colWidths=[W * 0.16, W * 0.14], rowHeights=[16], hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), AZUL), ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
                           ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    return t


def _por_tema(items):
    """[(tema, [items])] respetando el orden de aparición."""
    grupos = []
    for it in items:
        if not grupos or grupos[-1][0] != it.tema:
            grupos.append((it.tema, []))
        grupos[-1][1].append(it)
    return grupos


def generar_lista_pdf(ambito, requisitos) -> bytes:
    """Lista de Requisitos Legales y Otros Requisitos de un ámbito."""
    buf = BytesIO()
    nombre_ambito = dict(AMBITOS)[ambito]
    doc = _doc(buf, f'Lista de requisitos legales - {nombre_ambito}')
    W = doc.width
    cfg = _cargar_cfg()
    es_ma = ambito == 'ma'
    anchos = [14.0, 22.0, 22.0, 93.8, 15.7, 22.0, 18.0]
    cw = [W * a / sum(anchos) for a in anchos]
    st = _estilos(7)
    titulos = ['Ítem', 'Tipo', 'Código', 'Nombre del Documento', 'Fecha de Aprobación',
               'Estado' if es_ma else 'Revisión', 'Observaciones']
    filas = [[_celda(t, st['th'], cw[i]) for i, t in enumerate(titulos)]]
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), AZUL),
           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 2),
           ('RIGHTPADDING', (0, 0), (-1, -1), 2)]
    n = 0
    for tema, reqs in _por_tema(requisitos):
        if tema:
            est += [('SPAN', (0, len(filas)), (-1, len(filas))), ('BACKGROUND', (0, len(filas)), (-1, len(filas)), AZUL)]
            filas.append([Paragraph(esc_pdf(tema), st['sec'])] + [''] * 6)
        for r in reqs:
            n += 1
            revision = r.get_estado_display() if es_ma else (r.modificatorias or '---')
            if r.estado == 'derogada' and not es_ma:
                revision = f'Derogada ({_solo_fecha(r.fecha_derogacion)})\n{r.modificatorias}'.strip()
            fila = [n, r.tipo, r.codigo or '-', r.nombre, r.fecha_aprobacion, revision, r.observaciones]
            filas.append([_celda(v, st['tdl'] if i in (3, 5) else st['td'], cw[i]) for i, v in enumerate(fila)])
            if r.estado == 'derogada':
                est.append(('TEXTCOLOR', (0, len(filas) - 1), (-1, len(filas) - 1), colors.HexColor('#808080')))
    if len(filas) == 1:
        filas.append([''] * 7)
    t = Table(filas, colWidths=cw, repeatRows=1, splitInRow=1)   # filas largas se parten entre páginas
    t.setStyle(TableStyle(est))
    act = ActualizacionAmbito.objects.filter(ambito=ambito).first()
    cab = _cabecera(W, [W * 0.14, W * 0.62], f'LISTA DE REQUISITOS LEGALES<br/>({nombre_ambito})', COD_LISTA, cfg,
                    13.0, 7, 13, 1, 2)
    doc.build([cab, Spacer(1, 6), _fecha_actualizacion(W, act.fecha_lista if act else None), Spacer(1, 6), t])
    return buf.getvalue()


def _valor(resultado):
    return {'cumple': '100 %', 'no_cumple': '0 %', 'no_aplica': 'N/A', 'pendiente': ''}.get(resultado, '')


def generar_matriz_pdf(ambito, anio) -> bytes:
    """Matriz de Evaluación de Cumplimiento Legal de un ámbito y año: una columna por evaluación del año."""
    buf = BytesIO()
    nombre_ambito = dict(AMBITOS)[ambito]
    doc = _doc(buf, f'Matriz de evaluación de cumplimiento legal - {nombre_ambito} {anio}')
    W = doc.width
    cfg = _cargar_cfg()
    evaluaciones = list(Evaluacion.objects.filter(ambito=ambito, anio=anio, is_active=True).order_by('orden', 'periodo'))
    resultados = {}
    for e in evaluaciones:
        for r in e.resultados.all():
            resultados[(e.id, r.obligacion_id)] = r
    ids = {oid for (_, oid) in resultados}
    obligaciones = list(Obligacion.objects.filter(ambito=ambito, is_active=True)
                        .filter(id__in=ids) | Obligacion.objects.filter(ambito=ambito, is_active=True, estado='vigente'))
    obligaciones = sorted(set(obligaciones), key=lambda o: (o.orden, o.id))
    n_ev = max(len(evaluaciones), 1)
    anchos = [30.0, 32.0, 14.0, 90.0, 13.0, 18.0, 15.0] + [13.0] * n_ev + [24.0]
    cw = [W * a / sum(anchos) for a in anchos]
    st = _estilos(6.2)
    cols = ['DOCUMENTO/REGISTRO', 'DOCUMENTO LEGAL ASOCIADO', 'N° ARTÍCULO', 'EXTRACTO DEL ARTÍCULO A CUMPLIR',
            'PROCESO / SEDE', 'RESPONSABLE', 'PERIODICIDAD DEL MONITOREO']
    cols += [f'% CUMPLIMIENTO {e.periodo.upper()}' for e in evaluaciones] or ['% CUMPLIMIENTO']
    cols += ['OBSERVACIONES']
    nc = len(cols)
    filas = [[_celda(t, st['th'], cw[i]) for i, t in enumerate(cols)]]
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), AZUL),
           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 2),
           ('RIGHTPADDING', (0, 0), (-1, -1), 2)]
    resumen = []
    for tema, obls in _por_tema(obligaciones):
        f0 = len(filas)
        est += [('SPAN', (0, f0), (-1, f0)), ('BACKGROUND', (0, f0), (-1, f0), AZUL)]
        filas.append([Paragraph(esc_pdf(tema or 'GENERAL'), st['sec'])] + [''] * (nc - 1))
        cumple = no_cumple = 0
        for o in obls:
            valores, obs = [], [o.observaciones] if o.observaciones else []
            for e in evaluaciones:
                r = resultados.get((e.id, o.id))
                valores.append(_valor(r.resultado) if r else '')
                if r and r.observaciones:
                    obs.append(r.observaciones if len(evaluaciones) == 1 else f'{e.periodo}: {r.observaciones}')
                if r and r.hallazgo_id:
                    obs.append(f'Hallazgo {r.hallazgo.codigo}')
            ultimo = next((resultados.get((e.id, o.id)) for e in reversed(evaluaciones)
                           if resultados.get((e.id, o.id)) and resultados[(e.id, o.id)].resultado != 'pendiente'), None)
            if ultimo and ultimo.resultado == 'cumple':
                cumple += 1
            elif ultimo and ultimo.resultado == 'no_cumple':
                no_cumple += 1
            fila = [o.evidencia_documento, o.documento_legal or o.documento, o.articulo, o.extracto, o.proceso_sede, o.responsable,
                    o.periodicidad] + (valores or ['']) + ['\n'.join(obs) or '---']
            filas.append([_celda(v, st['tdl'] if i == 3 else st['td'], cw[i]) for i, v in enumerate(fila)])
            fi = len(filas) - 1
            for k, v in enumerate(valores):
                if v == '0 %':
                    est.append(('BACKGROUND', (7 + k, fi), (7 + k, fi), ROJO))
            if o.estado == 'derogada':
                est.append(('TEXTCOLOR', (0, fi), (-1, fi), colors.HexColor('#808080')))
        evaluadas = cumple + no_cumple
        pct = round(100 * cumple / evaluadas, 1) if evaluadas else None
        resumen.append((tema or 'GENERAL', no_cumple, evaluadas, pct))
    if len(filas) == 1:
        filas.append([''] * nc)
    t = Table(filas, colWidths=cw, repeatRows=1, splitInRow=1)   # filas largas se parten entre páginas
    t.setStyle(TableStyle(est))
    ult = ActualizacionAmbito.objects.filter(ambito=ambito).first()
    cab = _cabecera(W, [W * 0.12, W * 0.66], f'MATRIZ DE EVALUACIÓN DE CUMPLIMIENTO LEGAL<br/>({nombre_ambito})',
                    COD_MATRIZ, cfg, 13.0, 7, 13, 1, 2)
    partes = [cab, Spacer(1, 6), _fecha_actualizacion(W, ult.fecha_matriz if ult else None), Spacer(1, 6), t]

    # Resumen por tema (hoja de gráficos de la plantilla), con la última evaluación de cada obligación.
    st2 = _estilos(7.5)
    rf = [[Paragraph(x, st2['th']) for x in ('Tipo de requisitos legales', 'Incumplimiento', 'Evaluados',
                                              'Porcentaje de cumplimiento', 'Calificación')]]
    rest = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), AZUL),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]
    tot_nc = tot_ev = 0
    for tema, nc_, ev, pct in resumen:
        tot_nc += nc_
        tot_ev += ev
        cal = calificacion(pct)
        rf.append([Paragraph(esc_pdf(tema), st2['tdl']), Paragraph(str(nc_), st2['td']), Paragraph(str(ev), st2['td']),
                   Paragraph(f'{pct} %' if pct is not None else '—', st2['td']),
                   Paragraph(cal.upper(), st2['td'])])
        if cal:
            rest.append(('BACKGROUND', (4, len(rf) - 1), (4, len(rf) - 1), COLOR_CAL[cal]))
    pct_t = round(100 * (tot_ev - tot_nc) / tot_ev, 1) if tot_ev else None
    rf.append([Paragraph('<b>TOTAL</b>', st2['tdl']), Paragraph(f'<b>{tot_nc}</b>', st2['td']),
               Paragraph(f'<b>{tot_ev}</b>', st2['td']),
               Paragraph(f'<b>{pct_t} %</b>' if pct_t is not None else '—', st2['td']),
               Paragraph(f'<b>{calificacion(pct_t).upper()}</b>', st2['td'])])
    if calificacion(pct_t):
        rest.append(('BACKGROUND', (4, len(rf) - 1), (4, len(rf) - 1), COLOR_CAL[calificacion(pct_t)]))
    tr = Table(rf, colWidths=[W * 0.40, W * 0.12, W * 0.12, W * 0.16, W * 0.12], repeatRows=1)
    tr.setStyle(TableStyle(rest))
    escala = Paragraph('Escala: BUENO &gt; 80 % · REGULAR de 70 % a 80 % · MALO &lt; 70 %. '
                       f'Evaluaciones de {anio}: ' + (', '.join(f'{e.periodo} ({e.get_estado_display().lower()})'
                                                          for e in evaluaciones) or 'ninguna') + '.',
                       ParagraphStyle('lesc', fontName='Helvetica', fontSize=7.5))
    partes += [PageBreak(), Paragraph(f'<b>RESUMEN DEL CUMPLIMIENTO LEGAL — {esc_pdf(nombre_ambito.upper())} {anio}</b>',
                                      ParagraphStyle('lrt', fontName='Helvetica-Bold', fontSize=10)),
               Spacer(1, 6), tr, Spacer(1, 6), escala]
    doc.build(partes)
    return buf.getvalue()
