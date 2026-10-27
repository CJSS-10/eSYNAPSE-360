"""
Matriz de evaluación del cumplimiento de requisitos (A4 horizontal), diseñada para el módulo de Cumplimiento:
1. Cabecera con la caja de control del formato (se completa al vincularlo con su documento de la lista maestra).
2. Datos de la emisión: alcance (SIG completo o una sede), normas, fecha y quién la emite.
3. Resumen: grado de cumplimiento y cobertura por norma; con el SIG completo, además el grado por sede.
4. Evidencia del sistema en alerta.
5. Una matriz por norma: requisito, proceso, estado (SIG y por sede), cómo se cumple y evidencia, documentos,
   hallazgo y última evaluación. Los estados van coloreados: cumple verde, parcial ámbar, no cumple rojo.
"""
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, esc_pdf
from quejas.pdf import _cabecera

from . import servicio
from .evidencias import ALERTA
from .models import NORMAS

COD_MATRIZ = 'POR ASIGNAR'
# Formato nuevo: hasta vincularlo con su documento en la lista maestra se imprime con estos datos de control.
CONTROL_FORMATOS.setdefault(COD_MATRIZ, ('00', timezone.localdate().isoformat(), 'ASIG', 'GSIG', 'GG'))

AZUL = colors.HexColor('#16365C')
GRIS_SECCION = colors.HexColor('#D9E1F2')
BLANCO = colors.white
FONDO_ESTADO = {
    'cumple': colors.HexColor('#C6EFCE'), 'parcial': colors.HexColor('#FFEB9C'),
    'no_cumple': colors.HexColor('#FFC7CE'), 'no_aplica': colors.HexColor('#EDEDED'),
    'sin_evaluar': colors.white,
}
CORTO = {'cumple': 'Cumple', 'parcial': 'Parcial', 'no_cumple': 'No cumple', 'no_aplica': 'No aplica',
         'sin_evaluar': 'Sin evaluar'}
LARGO_REQUISITO = 600


def _st():
    return {
        'banda': ParagraphStyle('cb', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_CENTER,
                                textColor=BLANCO),
        'th': ParagraphStyle('cth', fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=TA_CENTER,
                             textColor=BLANCO),
        'lbl': ParagraphStyle('cl', fontName='Helvetica-Bold', fontSize=7, leading=9, alignment=TA_LEFT),
        'v': ParagraphStyle('cv', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_LEFT),
        'vc': ParagraphStyle('cvc', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_CENTER),
        'vb': ParagraphStyle('cvb', fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=TA_CENTER),
        'sec': ParagraphStyle('cs', fontName='Helvetica-Bold', fontSize=7, leading=9, alignment=TA_LEFT),
        'nota': ParagraphStyle('cn', fontName='Helvetica-Oblique', fontSize=6, leading=7.5, alignment=TA_LEFT),
    }


def _P(t, st):
    return Paragraph(esc_pdf('' if t is None else str(t)), st)


def _pct(v):
    return '—' if v is None else f'{v:.1f} %'


def _tabla(filas, anchos, estilos, repetir=0):
    t = Table(filas, colWidths=anchos, repeatRows=repetir)
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 2.5),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 2.5), ('TOPPADDING', (0, 0), (-1, -1), 1.5),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
                           ('GRID', (0, 0), (-1, -1), 0.5, colors.black)] + estilos))
    return t


def _banda(W, texto, s):
    return _tabla([[_P(texto, s['banda'])]], [W], [('BACKGROUND', (0, 0), (-1, -1), AZUL)])


def _texto_req(f):
    t = ' '.join(f['titulo'].split())
    return t if len(t) <= LARGO_REQUISITO else t[:LARGO_REQUISITO].rsplit(' ', 1)[0] + '…'


def generar_matriz_pdf(normas, sede=None, usuario=None) -> bytes:
    """normas: lista de claves de norma; sede: organizacion.Sede o None (SIG completo)."""
    cfg = _cargar_cfg()
    s = _st()
    buf = BytesIO()
    pagina = landscape(A4)
    doc = SimpleDocTemplate(buf, pagesize=pagina, leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm,
                            bottomMargin=10 * mm, title='Matriz de evaluación del cumplimiento de requisitos')
    W = doc.width
    sedes = servicio.sedes_activas()
    columnas_sede = [] if sede else sedes
    nombre_norma = dict(NORMAS)
    ahora = timezone.localtime()

    story = [_cabecera(W, [W * 0.17, W * 0.53, W * 0.30], 'MATRIZ DE EVALUACIÓN DEL CUMPLIMIENTO DE REQUISITOS',
                       COD_MATRIZ, cfg, 5.2 * mm, 6.5, 11, 1, 2), Spacer(1, 3 * mm)]

    # Datos de la emisión
    emisor = ''
    if usuario:
        t = getattr(usuario, 'trabajador', None)
        emisor = t.nombre_completo if t else (usuario.get_full_name() or usuario.username)
        if t and t.puesto_id:
            emisor += f' — {t.puesto.nombre}'
    alcance = f'{sede.nombre}' if sede else 'SIG completo (' + ', '.join(x.nombre for x in sedes) + ')'
    story.append(_tabla([
        [_P('Alcance:', s['lbl']), _P(alcance, s['v']), _P('Fecha de emisión:', s['lbl']),
         _P(ahora.strftime('%Y-%m-%d %H:%M'), s['v'])],
        [_P('Normas:', s['lbl']), _P(', '.join(nombre_norma[n] for n in normas), s['v']), _P('Emitido por:', s['lbl']),
         _P(emisor, s['v'])],
    ], [W * 0.09, W * 0.51, W * 0.12, W * 0.28], []))
    story.append(Spacer(1, 3 * mm))

    # Matrices y resumen
    evid = servicio.Evidencias()
    matrices = [(n, servicio.matriz(n, evid)) for n in normas]
    sede_id = sede.id if sede else None
    filas = [[_P(x, s['th']) for x in ('Norma', 'Requisitos', 'Evaluados', 'Cumple', 'Parcial', 'No cumple',
                                       'No aplica', 'En riesgo', 'Cobertura', 'Cumplimiento')]]
    for n, fs in matrices:
        r = servicio.resumen(fs, sede_id)
        filas.append([_P(nombre_norma[n], s['v'])] + [_P(v, s['vc']) for v in (
            r['total'], r['evaluados'], r['cumple'], r['parcial'], r['no_cumple'], r['no_aplica'], r['en_riesgo'],
            _pct(r['cobertura']))] + [_P(_pct(r['porcentaje']), s['vb'])])
    resumen = [_banda(W, 'RESUMEN DEL CUMPLIMIENTO' + (f' — {sede.nombre.upper()}' if sede else ' — SIG COMPLETO'), s),
               _tabla(filas, [W * 0.22] + [W * 0.0867] * 9, [('BACKGROUND', (0, 0), (-1, 0), AZUL)])]
    if columnas_sede:
        fsed = [[_P('Norma', s['th'])] + [_P(f'{x.nombre}', s['th']) for x in columnas_sede]]
        for n, fs in matrices:
            fsed.append([_P(nombre_norma[n], s['v'])] + [_P(_pct(servicio.resumen(fs, x.id)['porcentaje']), s['vc'])
                                                         for x in columnas_sede])
        resumen += [Spacer(1, 2 * mm), _banda(W, 'CUMPLIMIENTO POR SEDE', s),
                    _tabla(fsed, [W * 0.22] + [W * 0.78 / len(columnas_sede)] * len(columnas_sede),
                           [('BACKGROUND', (0, 0), (-1, 0), AZUL)])]
    resumen.append(_P('Grado de cumplimiento: cumple = 100, parcial = 50, no cumple = 0; no aplica se excluye. '
                      'Cobertura: requisitos evaluados o justificados como no aplicables. El SIG completo y cada sede '
                      'tienen su propia evaluación.', s['nota']))
    story += [KeepTogether(resumen), Spacer(1, 3 * mm)]

    alertas = [evid.resultado(c) for c in servicio.evidencias_claves()]
    alertas = [e for e in alertas if e['nivel'] == ALERTA]
    if alertas:
        story += [_banda(W, 'EVIDENCIA DEL SISTEMA EN ALERTA', s),
                  _tabla([[_P(e['titulo'], s['lbl']), _P(e['texto'], s['v'])] for e in alertas],
                         [W * 0.22, W * 0.78], []), Spacer(1, 3 * mm)]

    # Una matriz por norma
    n_sede = len(columnas_sede)
    ancho_sede = W * 0.055
    resto = W - ancho_sede * n_sede
    anchos = [resto * x for x in (0.05, 0.30, 0.09, 0.07, 0.25, 0.08, 0.07, 0.09)]
    anchos = anchos[:4] + [ancho_sede] * n_sede + anchos[4:]
    col_estado = 3
    for n, fs in matrices:
        r = servicio.resumen(fs, sede_id)
        cab = ['N.°', 'Requisito', 'Proceso', 'Estado' + ('' if sede else ' SIG')] + \
              [x.codigo or x.nombre for x in columnas_sede] + \
              ['Cómo se cumple y evidencia', 'Documentos', 'Hallazgo', 'Evaluación']
        data = [[_P(c, s['th']) for c in cab]]
        estilos = [('BACKGROUND', (0, 0), (-1, 0), AZUL)]
        for f in fs:
            fila = len(data)
            if f['tipo'] == 'seccion':
                data.append([_P(f'{f["codigo"]} {f["titulo"]}'.strip(), s['sec'])] + [''] * (len(cab) - 1))
                estilos += [('SPAN', (0, fila), (-1, fila)), ('BACKGROUND', (0, fila), (-1, fila), GRIS_SECCION)]
                continue
            ev = f['evaluacion'] or {}
            est = servicio.estado_en(f, sede_id)
            texto = ' '.join(x for x in (ev.get('como_se_cumple', ''), ev.get('evidencia', '')) if x)
            if est == 'no_aplica' and ev.get('justificacion'):
                texto = f'No aplica: {ev["justificacion"]}'
            ev_sede = (ev.get('sedes') or {}).get(str(sede_id), {}) if sede_id else {}
            if sede_id:
                # Vista de una sede: su propia evaluación.
                texto = ev_sede.get('observacion', '')
            riesgo = ' (en riesgo)' if servicio.riesgo_en(f, sede_id) else ''
            celdas = [_P(f['codigo'], s['vb']), _P(_texto_req(f) + (f' [{f["referencia"]}]' if f.get('referencia')
                                                                   else ''), s['v']),
                      _P(ev.get('proceso_nombre', ''), s['vc']), _P(CORTO[est] + riesgo, s['vb'])]
            estilos.append(('BACKGROUND', (col_estado, fila), (col_estado, fila), FONDO_ESTADO[est]))
            for i, x in enumerate(columnas_sede):
                es = servicio.estado_en(f, x.id)
                celdas.append(_P(CORTO[es], s['vc']))
                estilos.append(('BACKGROUND', (col_estado + 1 + i, fila), (col_estado + 1 + i, fila), FONDO_ESTADO[es]))
            evaluacion = ''
            if sede_id:
                if ev_sede.get('fecha_evaluacion'):
                    evaluacion = str(ev_sede['fecha_evaluacion'])
            elif ev.get('fecha_evaluacion'):
                evaluacion = f'{ev["fecha_evaluacion"]} · {ev.get("evaluado_por", "")}'
            celdas += [_P(texto, s['v']), _P(', '.join(d['codigo'] for d in ev.get('documentos', [])), s['vc']),
                       _P(ev.get('hallazgo_codigo', ''), s['vc']), _P(evaluacion, s['vc'])]
            data.append(celdas)
        story += [_banda(W, f'{nombre_norma[n].upper()} — CUMPLIMIENTO {_pct(r["porcentaje"])} · COBERTURA '
                            f'{_pct(r["cobertura"])}', s), _tabla(data, anchos, estilos, repetir=1)]
        story.append(Spacer(1, 4 * mm))

    doc.build(story)
    return buf.getvalue()
