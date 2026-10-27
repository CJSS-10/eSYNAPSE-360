"""
Formatos impresos de incidentes, accidentes, enfermedades ocupacionales y estadísticas de
SST, con la disposición de sus plantillas (registros oficiales de la R.M. 050-2013-TR e
informe de investigación de accidentes y emergencias).
"""
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _p_ajustado, _solo_fecha, esc_pdf
from legal.pdf import _limpio
from quejas.pdf import _cabecera

from .eventos import (ACTOS_SUBESTANDAR, CONDICIONES_SUBESTANDAR, FACTORES_PERSONALES, FACTORES_TRABAJO,
                      PARTES_CUERPO, TIPOS_ACCIDENTE, TIPOS_AMBIENTAL, TIPOS_EMERGENCIA, TIPOS_LESION)

COD_ACC, COD_ENF, COD_INC, COD_INF, COD_EST, COD_DAT = (f'SIG-PRO-10-r0{n}' for n in range(1, 7))
# Respaldo de la caja de control mientras el formato no esté vinculado a la lista maestra.
CONTROL_FORMATOS.setdefault(COD_ACC, ('0', '2025-05-08', 'ASIG', 'GSIG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_ENF, ('00', '2026-10-22', 'ASIG', 'GSIG', 'GG'))
for _c in (COD_INC, COD_INF, COD_EST, COD_DAT):
    CONTROL_FORMATOS.setdefault(_c, ('00', '2025-05-08', 'GSIG', 'GSIG', 'GG'))

GRIS = colors.HexColor('#D9D9D9')
AZUL = colors.HexColor('#DCE6F1')
FS = 7
TH = ParagraphStyle('eth', fontName='Helvetica-Bold', fontSize=FS, leading=FS * 1.2, alignment=TA_CENTER)
THL = ParagraphStyle('etl', fontName='Helvetica-Bold', fontSize=FS, leading=FS * 1.2, alignment=TA_LEFT)
TD = ParagraphStyle('etd', fontName='Helvetica', fontSize=FS, leading=FS * 1.25, alignment=TA_CENTER)
TDL = ParagraphStyle('etdl', fontName='Helvetica', fontSize=FS, leading=FS * 1.25, alignment=TA_LEFT)
NOTA = ParagraphStyle('enota', fontName='Helvetica-Oblique', fontSize=FS - 1, leading=(FS - 1) * 1.2,
                      alignment=TA_LEFT)


def _txt(v):
    return '' if v is None else (str(v) if isinstance(v, (int, float)) else v)


def P(texto, estilo=TD):
    return Paragraph(esc_pdf(_limpio(_txt(texto))), estilo)


def _doc(buf, titulo, horizontal=False):
    return SimpleDocTemplate(buf, pagesize=landscape(A4) if horizontal else A4, leftMargin=10 * mm,
                             rightMargin=10 * mm, topMargin=8 * mm, bottomMargin=8 * mm, title=titulo)


def _tabla(filas, anchos, W, extra=(), cabeceras=(), alturas=None, izquierda=False):
    t = Table(filas, colWidths=[W * a / sum(anchos) for a in anchos], rowHeights=alturas,
              hAlign='LEFT' if izquierda else 'CENTER')
    est = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
           ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3)]
    for r in cabeceras:
        est.append(('BACKGROUND', (0, r), (-1, r), GRIS))
    t.setStyle(TableStyle(est + list(extra)))
    return t


def _titulo_seccion(texto, W):
    return _tabla([[P(texto, TH)]], [1], W, cabeceras=[0])


def _empleador(cfg):
    from organizacion.models import Trabajador
    n = Trabajador.objects.filter(is_active=True, estado='activo', puesto__tipo='propio').count()
    return [getattr(cfg, 'razon_social', '') or getattr(cfg, 'subtitulo', ''), getattr(cfg, 'ruc', ''),
            getattr(cfg, 'direccion', ''), getattr(cfg, 'actividad_economica', ''), n or '']


def _bloque_empleador(W, cfg, titulo='DATOS DEL EMPLEADOR PRINCIPAL'):
    d = _empleador(cfg)
    return _tabla([[P(titulo, TH), '', '', '', ''],
                   [P('RAZÓN SOCIAL O DENOMINACIÓN SOCIAL', TH), P('RUC', TH),
                    P('DOMICILIO (dirección, distrito, departamento, provincia)', TH), P('TIPO DE ACTIVIDAD ECONÓMICA', TH),
                    P('N° TRABAJADORES EN EL CENTRO LABORAL', TH)],
                   [P(d[0]), P(d[1]), P(d[2]), P(d[3]), P(d[4])]],
                  [24, 10, 30, 20, 12], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1])


def _intermediacion(W):
    return _tabla([[P('DATOS DEL EMPLEADOR DE INTERMEDIACIÓN, TERCERIZACIÓN, CONTRATISTA, SUBCONTRATISTA U OTROS '
                      '(completar solo si contrata estos servicios)', TH), '', '', '', ''],
                   [P('RAZÓN SOCIAL O DENOMINACIÓN SOCIAL', TH), P('RUC', TH), P('DOMICILIO', TH),
                    P('TIPO DE ACTIVIDAD ECONÓMICA', TH), P('N° TRABAJADORES EN EL CENTRO LABORAL', TH)],
                   [P('-'), P('-'), P('-'), P('-'), P('-')]],
                  [24, 10, 30, 20, 12], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1])


def _trabajadores(W, afectados, titulo='DATOS DEL TRABAJADOR'):
    filas = [[P(titulo, TH)] + [''] * 9,
             [P('APELLIDOS Y NOMBRES', TH), '', '', P('N° DNI / CE', TH), P('EDAD', TH), P('ÁREA', TH),
              P('PUESTO DE TRABAJO', TH), P('ANTIGÜEDAD EN EL EMPLEO', TH), P('SEXO F/M', TH), P('TURNO D/T/N', TH)],
             ]
    for a in afectados or [None]:
        filas.append([P(a.nombre if a else '-', TDL), '', '', P(a.documento if a else ''), P(a.edad if a else ''),
                      P(a.area if a else ''), P(a.puesto if a else ''), P(a.antiguedad if a else ''),
                      P(a.sexo if a else ''), P(a.turno if a else '')])
    filas.append([P('TIPO DE CONTRATO', TH), '', '', P('TIEMPO DE EXPERIENCIA EN EL PUESTO', TH), '', '',
                  P('N° HORAS TRABAJADAS EN LA JORNADA (antes del evento)', TH), '', P('EMPRESA', TH), ''])
    for a in afectados or [None]:
        filas.append([P(a.tipo_contrato if a else ''), '', '', P(a.experiencia_puesto if a else ''), '', '',
                      P(a.horas_trabajadas if a and a.horas_trabajadas is not None else ''), '',
                      P((a.empresa or 'Metrindust') if a else ''), ''])
    n = len(afectados or [None])
    extra = [('SPAN', (0, 0), (-1, 0))]
    for r in range(1, 2 + n):
        extra.append(('SPAN', (0, r), (2, r)))
    for r in range(2 + n, 3 + 2 * n):
        extra += [('SPAN', (0, r), (2, r)), ('SPAN', (3, r), (5, r)), ('SPAN', (6, r), (7, r)), ('SPAN', (8, r), (9, r))]
    return _tabla(filas, [10, 6, 6, 9, 5, 12, 14, 9, 5, 6], W, extra=extra, cabeceras=[0, 1, 2 + n])


def _fechas(W, e, etq_fecha, etq_lugar):
    f = timezone.localtime(e.fecha_hora)
    fi = e.fecha_inicio_investigacion
    return _tabla([[P(etq_fecha, TH), '', '', '', P('FECHA DE INICIO DE LA INVESTIGACIÓN', TH), '', '',
                    P(etq_lugar, TH)],
                   [P('DÍA', TH), P('MES', TH), P('AÑO', TH), P('HORA', TH), P('DÍA', TH), P('MES', TH), P('AÑO', TH), ''],
                   [P(f.day), P(f.month), P(f.year), P(f.strftime('%H:%M')), P(fi.day if fi else ''),
                    P(fi.month if fi else ''), P(fi.year if fi else ''), P(e.lugar, TDL)]],
                  [5, 5, 6, 6, 5, 5, 6, 30], W,
                  extra=[('SPAN', (0, 0), (3, 0)), ('SPAN', (4, 0), (6, 0)), ('SPAN', (7, 0), (7, 1))],
                  cabeceras=[0, 1])


def _texto(W, titulo, texto, nota=None, alto=None):
    filas = [[P(titulo, TH)]]
    if nota:
        filas.append([P(nota, NOTA)])
    cuerpo = P(texto or ' ', TDL)
    filas.append([cuerpo])
    alturas = None
    if alto:
        # Alto mínimo del recuadro (como en la plantilla); crece si el texto es más largo.
        _, h = cuerpo.wrap(W - 6, 10000)
        alturas = [None] * (len(filas) - 1) + [max(alto, h + 8)]
    t = Table(filas, colWidths=[W], rowHeights=alturas, splitInRow=1)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('VALIGN', (0, len(filas) - 1), (0, len(filas) - 1), 'TOP'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                           ('BACKGROUND', (0, 0), (-1, 0), GRIS)]))
    return t


def _medidas(W, acciones, titulo='MEDIDAS CORRECTIVAS'):
    filas = [[P(titulo, TH), '', '', '', '', ''],
             [P('DESCRIPCIÓN DE LA MEDIDA CORRECTIVA', TH), P('RESPONSABLE', TH), P('DÍA', TH), P('MES', TH),
              P('AÑO', TH), P('ESTADO DE LA IMPLEMENTACIÓN (realizada, pendiente, en ejecución)', TH)]]
    lista = (acciones or {}).get('acciones') or []
    for a in lista:
        fch = a['fecha']
        filas.append([P(a['descripcion'], TDL), P(a['responsable']), P(fch.day if fch else ''),
                      P(fch.month if fch else ''), P(fch.year if fch else ''), P(a['estado'])])
    if not lista:
        filas.append([P('Las medidas se registran en la solicitud de acción correctiva '
                        + ((acciones or {}).get('sac') or '(pendiente de registrar)') + '.', TDL), '', '', '', '', ''])
    extra = [('SPAN', (0, 0), (-1, 0))] + ([('SPAN', (0, 2), (-1, 2))] if not lista else [])
    return _tabla(filas, [40, 18, 5, 5, 6, 20], W, extra=extra, cabeceras=[0, 1])


def _firma_txt(f):
    if not f:
        return '', '', '', ''
    return f.get('nombre', ''), f.get('cargo', ''), _solo_fecha(f.get('fecha') or ''), 'Firmado electrónicamente'


def _responsables(W, firmas, titulo='RESPONSABLE DEL REGISTRO Y DE LA INVESTIGACIÓN'):
    filas = [[P(titulo, TH), '', '', '', '', '', '', '']]
    for f in firmas:
        n, c, d, s = _firma_txt(f)
        filas.append([P('Nombre:', THL), P(n, TDL), P('Cargo:', THL), P(c, TDL), P('Fecha:', THL), P(d),
                      P('Firma:', THL), P(s)])
    return _tabla(filas, [6, 22, 6, 18, 6, 10, 6, 16], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0])


def _x(v):
    return 'X' if v else ''


# --------------------------------------------------------------------------------------- registros
def generar_registro_pdf(e) -> bytes:
    """Registro de accidentes de trabajo (accidente) o de accidentes e incidentes peligrosos (incidentes)."""
    from .eventos_api import _acciones_de
    buf = BytesIO()
    accidente = e.tipo == 'accidente'
    titulo = 'REGISTRO DE ACCIDENTES DE TRABAJO' if accidente else 'REGISTRO DE ACCIDENTES E INCIDENTES PELIGROSOS'
    codigo = COD_ACC if accidente else COD_INC
    doc = _doc(buf, f'{titulo} {e.codigo}')
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    afectados = list(e.afectados.filter(is_active=True))
    story = [_cabecera(W, cw, titulo, codigo, cfg, 12, 7, 12, 4, 18), Spacer(1, 4),
             _tabla([[P('N° REGISTRO', TH), P(e.codigo)]], [1, 3], W * 0.35, izquierda=True), Spacer(1, 4),
             _bloque_empleador(W, cfg), Spacer(1, 3)]
    if accidente:
        story += [_tabla([[P('COMPLETAR SOLO EN CASO QUE LAS ACTIVIDADES DEL EMPLEADOR SEAN CONSIDERADAS DE ALTO RIESGO',
                             TH), '', ''],
                          [P('N° DE TRABAJADORES AFILIADOS AL SCTR', TH), P('N° DE TRABAJADORES NO AFILIADOS AL SCTR', TH),
                           P('NOMBRE DE LA ASEGURADORA', TH)],
                          [P(len([a for a in afectados if a.sctr]) or '-'), P(len([a for a in afectados if a.sctr is False]) or '-'),
                           P(getattr(cfg, 'aseguradora_sctr', '') or '-')]],
                         [1, 1, 1], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1]), Spacer(1, 3)]
    story += [_intermediacion(W), Spacer(1, 3),
              _trabajadores(W, afectados, 'DATOS DEL TRABAJADOR' + ('' if accidente else ' (completar solo si el '
                                                                                         'evento afecta a trabajadores)')),
              Spacer(1, 3)]
    if accidente:
        story += [_fechas(W, e, 'FECHA Y HORA DE OCURRENCIA DEL ACCIDENTE', 'LUGAR EXACTO DONDE OCURRIÓ EL ACCIDENTE'),
                  Spacer(1, 3)]
        g, gr = e.gravedad, e.grado_incapacidad
        story.append(_tabla(
            [[P('MARCAR CON (X) GRAVEDAD DEL ACCIDENTE DE TRABAJO', TH), '', '',
              P('MARCAR CON (X) GRADO DEL ACCIDENTE INCAPACITANTE (de ser el caso)', TH), '', '', '',
              P('N° DE DÍAS DE DESCANSO MÉDICO', TH), P('N° DE TRABAJADORES AFECTADOS', TH)],
             [P('ACCIDENTE LEVE', TH), P('ACCIDENTE INCAPACITANTE', TH), P('MORTAL', TH), P('TOTAL TEMPORAL', TH),
              P('PARCIAL TEMPORAL', TH), P('PARCIAL PERMANENTE', TH), P('TOTAL PERMANENTE', TH), '', ''],
             [P(_x(g == 'leve')), P(_x(g == 'incapacitante')), P(_x(g == 'mortal')), P(_x(gr == 'total_temporal')),
              P(_x(gr == 'parcial_temporal')), P(_x(gr == 'parcial_permanente')), P(_x(gr == 'total_permanente')),
              P(e.dias_perdidos), P(len(afectados))]],
            [1] * 9, W, extra=[('SPAN', (0, 0), (2, 0)), ('SPAN', (3, 0), (6, 0)), ('SPAN', (7, 0), (7, 1)),
                               ('SPAN', (8, 0), (8, 1))], cabeceras=[0, 1]))
        partes = sorted({p for a in afectados for p in a.partes_cuerpo})
        story += [Spacer(1, 3), _tabla([[P('DESCRIBIR PARTE DEL CUERPO LESIONADO (de ser el caso):', THL),
                                         P(', '.join(partes) or '-', TDL)]], [1, 2], W),
                  Spacer(1, 3),
                  _texto(W, 'DESCRIPCIÓN DEL ACCIDENTE DE TRABAJO', e.descripcion,
                         'Describe solo los hechos, sin información subjetiva que no pueda ser comprobada.', 60)]
    else:
        pel = e.tipo == 'incidente_peligroso'
        story += [_tabla([[P('INVESTIGACIÓN DEL INCIDENTE PELIGROSO O INCIDENTE', TH), '', '', ''],
                          [P('INCIDENTE PELIGROSO:', THL), P(_x(pel)), P('INCIDENTE:', THL), P(_x(not pel))],
                          [P('N° TRABAJADORES POTENCIALMENTE AFECTADOS:', THL), P(e.potencialmente_afectados or '-'),
                           P('DETALLAR TIPO DE ATENCIÓN EN PRIMEROS AUXILIOS (de ser el caso):', THL),
                           P(e.primeros_auxilios or '-', TDL)],
                          [P('N° POBLADORES POTENCIALMENTE AFECTADOS:', THL), P(e.pobladores_afectados or '-'), '', '']],
                         [3, 1, 3, 4], W, extra=[('SPAN', (0, 0), (-1, 0)), ('SPAN', (2, 2), (2, 3)),
                                                 ('SPAN', (3, 2), (3, 3))], cabeceras=[0]),
                  Spacer(1, 3),
                  _fechas(W, e, 'FECHA Y HORA EN QUE OCURRIÓ EL HECHO', 'LUGAR EXACTO DONDE OCURRIÓ EL HECHO'),
                  Spacer(1, 3),
                  _texto(W, 'DESCRIPCIÓN DEL INCIDENTE PELIGROSO O INCIDENTE', e.descripcion,
                         'Describe solo los hechos, sin información subjetiva que no pueda ser comprobada.', 50)]
    causas = '\n'.join(x for x in (('Causas inmediatas: ' + e.causas_inmediatas) if e.causas_inmediatas else '',
                                   ('Causas básicas: ' + e.causas_basicas) if e.causas_basicas else '') if x)
    story += [Spacer(1, 3),
              _texto(W, 'DESCRIPCIÓN DE LAS CAUSAS QUE ORIGINARON EL ' + ('ACCIDENTE DE TRABAJO' if accidente else
                                                                         'INCIDENTE PELIGROSO O INCIDENTE'), causas,
                     'Análisis con el modelo de causalidad del informe de investigación.', 40),
              Spacer(1, 3), KeepTogether([_medidas(W, _acciones_de(e.hallazgo)), Spacer(1, 3),
                                          _responsables(W, [e.firma_elaborado, e.firma_revisado])])]
    doc.build(story)
    return buf.getvalue()


def _casillas(opciones, marcadas, cols, W, titulo=None, otros=True):
    """Lista de opciones con su casilla marcada (X) en varias columnas."""
    marcadas = list(marcadas or [])
    extra_txt = [m[5:].strip() for m in marcadas if str(m).startswith('Otro:')]
    items = [f'[{"X" if o in marcadas else "  "}] {o}' for o in opciones]
    if otros:
        items.append(f'[{"X" if extra_txt else "  "}] Otros: {", ".join(extra_txt)}')
    filas = []
    for i in range(0, len(items), cols):
        fila = [P(t, TDL) for t in items[i:i + cols]]
        filas.append(fila + [''] * (cols - len(fila)))
    if titulo:
        filas.insert(0, [P(titulo, TH)] + [''] * (cols - 1))
    return _tabla(filas, [1] * cols, W, extra=[('SPAN', (0, 0), (-1, 0))] if titulo else [],
                  cabeceras=[0] if titulo else [])


def generar_informe_pdf(e) -> bytes:
    """Informe de investigación de accidentes y emergencias."""
    buf = BytesIO()
    doc = _doc(buf, f'Informe de investigación {e.codigo}')
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    afectados = list(e.afectados.filter(is_active=True))
    f = timezone.localtime(e.fecha_hora)
    es_emerg = e.tipo == 'emergencia'
    story = [_cabecera(W, cw, 'INFORME DE INVESTIGACIÓN DE ACCIDENTES Y EMERGENCIAS', COD_INF, cfg, 12, 7, 11, 4, 18),
             Spacer(1, 4),
             _tabla([[P('Tipo de incidente:', THL), P(f'[{_x(not es_emerg)}] Accidente ({e.get_tipo_display()})'),
                      P(f'[{_x(es_emerg)}] Emergencia'), P('Informe N°', THL), P(e.codigo)]], [3, 4, 3, 2, 3], W),
             Spacer(1, 3), _titulo_seccion('DATOS DEL ACCIDENTE O EMERGENCIA', W),
             _tabla([[P('Lugar del accidente o emergencia:', THL), P(e.lugar, TDL), P('Fecha:', THL),
                      P(_solo_fecha(f.date())), P('Hora:', THL), P(f.strftime('%H:%M'))],
                     [P('Proyecto / servicio:', THL), P(' · '.join(x for x in (e.cliente, e.actividad) if x) or '-', TDL),
                      '', '', '', '']],
                    [6, 14, 3, 5, 3, 4], W, extra=[('SPAN', (1, 1), (-1, 1))])]
    filas = [[P('Personal involucrado en el accidente o emergencia', TH), '', '', '', ''],
             [P('Nombre', TH), P('Edad', TH), P('Cargo', TH), P('Área', TH), P('SCTR', TH)]]
    for a in afectados or [None]:
        filas.append([P(a.nombre if a else '-', TDL), P(a.edad if a else ''), P(a.puesto if a else ''),
                      P(a.area if a else ''), P(('Sí' if a.sctr else 'No' if a.sctr is False else '') if a else '')])
    story += [_tabla(filas, [12, 3, 9, 9, 3], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1]),
              _texto(W, 'Descripción del accidente o emergencia', e.descripcion, alto=45),
              _titulo_seccion('Identificación de pérdidas (seguridad, salud y medio ambiente)', W),
              _casillas(PARTES_CUERPO, sorted({p for a in afectados for p in a.partes_cuerpo}), 6, W,
                        'Parte del cuerpo lesionada'),
              _casillas(TIPOS_LESION, sorted({p for a in afectados for p in a.tipos_lesion}), 5, W, 'Tipo de lesión'),
              _casillas(TIPOS_ACCIDENTE, e.tipos_accidente, 5, W, 'Tipo de accidente'),
              _casillas(TIPOS_EMERGENCIA, e.tipos_emergencia, 4, W, 'Tipo de emergencia'),
              _casillas(TIPOS_AMBIENTAL, e.tipos_ambiental, 4, W, 'Tipo de accidente ambiental'),
              _texto(W, 'Acciones inmediatas', e.acciones_inmediatas, alto=30),
              _tabla([[P('Nombre y firma del supervisor reportante', THL),
                       P(f'{e.reportado_por.get_full_name() or e.reportado_por.username} — reportado el '
                         f'{_solo_fecha(timezone.localtime(e.fecha_reporte).date())}' if e.reportado_por_id else '', TDL)]],
                     [1, 2], W)]
    filas = [[P('Nombre de testigos', TH), P('Cargo', TH), P('Empresa', TH), P('Edad', TH)]]
    for t in e.testigos or [{}]:
        filas.append([P(t.get('nombre', '-'), TDL), P(t.get('cargo', '')), P(t.get('empresa', '')), P(t.get('edad', ''))])
    story += [_tabla(filas, [12, 8, 8, 3], W, cabeceras=[0]), PageBreak(),
              _titulo_seccion('ANÁLISIS DEL INCIDENTE', W),
              _casillas(ACTOS_SUBESTANDAR, e.actos_subestandar, 3, W, 'Actos subestándar'),
              _casillas(CONDICIONES_SUBESTANDAR, e.condiciones_subestandar, 3, W, 'Condiciones subestándar'),
              _texto(W, 'Describir actos o condiciones subestándar existentes', e.detalle_actos_condiciones, alto=30),
              _casillas(FACTORES_TRABAJO, e.factores_trabajo, 3, W,
                        '¿Qué factores de trabajo condujeron a la condición subestándar? — Factores de trabajo'),
              _texto(W, 'Explicación', e.detalle_factores_trabajo),
              _casillas(FACTORES_PERSONALES, e.factores_personales, 3, W,
                        '¿Qué factores personales condujeron al acto subestándar? — Factores personales'),
              _texto(W, 'Explicación', e.detalle_factores_personales),
              _titulo_seccion(f'ANÁLISIS DE CAUSAS ({e.get_metodo_analisis_display()})', W)]
    filas = [[P('Ítem', TH), P('Descripción', TH)], [P('¿Qué sucedió?', THL), P(e.que_sucedio, TDL)]]
    for pq in (e.porques or []) + [''] * max(0, 4 - len(e.porques or [])):
        filas.append([P('¿Por qué?', THL), P(pq, TDL)])
    filas += [[P('Causas inmediatas', THL), P(e.causas_inmediatas, TDL)],
              [P('Causas básicas', THL), P(e.causas_basicas, TDL)]]
    from .eventos_api import _acciones_de
    acc = _acciones_de(e.hallazgo)
    story += [_tabla(filas, [1, 4], W, cabeceras=[0]),
              _texto(W, 'Conclusiones', e.conclusiones, alto=40),
              _tabla([[P('Número de acción correctiva / preventiva relacionada:', THL),
                       P((acc or {}).get('sac') or '-', TDL)]], [2, 3], W),
              Spacer(1, 6)]
    fe, fr = e.firma_elaborado or {}, e.firma_revisado or {}

    def nf(fx):
        return f'{fx.get("nombre", "")}\n{fx.get("cargo", "")}\nFirmado electrónicamente' if fx else ''

    story.append(_tabla([[P('', TH), P('Elaborado por', TH), P('Revisado por', TH), P('V°B° Comité SST', TH)],
                         [P('Nombre / firma', THL), P(nf(fe)), P(nf(fr)), P('')],
                         [P('D.N.I.', THL), P(''), P(''), P('')],
                         [P('Lugar y fecha', THL), P(f'Lima, {_solo_fecha(fe.get("fecha") or "")}' if fe else ''),
                          P(f'Lima, {_solo_fecha(fr.get("fecha") or "")}' if fr else ''), P('')]],
                        [3, 4, 4, 4], W, cabeceras=[0], alturas=[None, 34, 14, 14]))
    doc.build(story)
    return buf.getvalue()


def generar_enfermedad_pdf(o) -> bytes:
    from .eventos_api import _acciones_de
    buf = BytesIO()
    doc = _doc(buf, f'Registro de enfermedad ocupacional {o.codigo}')
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    story = [_cabecera(W, cw, 'REGISTRO DE ENFERMEDADES OCUPACIONALES', COD_ENF, cfg, 12, 7, 12, 4, 18), Spacer(1, 4),
             _tabla([[P('N° REGISTRO', TH), P(o.codigo)]], [1, 3], W * 0.35, izquierda=True), Spacer(1, 4),
             _bloque_empleador(W, cfg, 'DATOS DEL EMPLEADOR'), Spacer(1, 3),
             _tabla([[P('DATOS DE LA ENFERMEDAD OCUPACIONAL', TH), '', '', '', '', ''],
                     [P('NOMBRE DE LA ENFERMEDAD OCUPACIONAL', TH), P('N° DE TRABAJADORES AFECTADOS', TH), P('ÁREA', TH),
                      P('N° DE VECES QUE SE PRESENTÓ LA ENFERMEDAD EN EL ÁREA', TH),
                      P('AGENTE / FACTOR DE RIESGO', TH), P('DETALLE DE LAS CAUSAS QUE GENERAN LA ENFERMEDAD', TH)],
                     [P(o.nombre), P(o.trabajadores_afectados), P(o.unidad.nombre if o.unidad_id else '-'),
                      P(o.veces_en_area),
                      P(f'{o.get_agente_display()}{": " + o.agente_detalle if o.agente_detalle else ""}'),
                      P(o.causas, TDL)]],
                    [16, 8, 12, 9, 12, 25], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1]),
             Paragraph('Registro sin datos personales de salud: el diagnóstico individual se conserva en la historia '
                       'clínica ocupacional bajo custodia del médico ocupacional.', NOTA),
             Spacer(1, 3), _medidas(W, _acciones_de(o.hallazgo)), Spacer(1, 3),
             _responsables(W, [o.firma_registro], 'RESPONSABLE DEL REGISTRO')]
    doc.build(story)
    return buf.getvalue()


# ------------------------------------------------------------------------------------ estadísticas
MES_CORTO = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']


def _num(v, dec=False):
    if v is None:
        return '-'
    return f'{v:,.2f}' if dec else f'{v:,}'


def _areas(lst):
    return ', '.join(lst) if lst else '---'


def generar_estadisticas_pdf(anio, meses, informe) -> bytes:
    """Registro de estadísticas de SST: análisis firmado, estadística de accidentes e incidentes, enfermedades."""
    buf = BytesIO()
    doc = _doc(buf, f'Registro de estadísticas SST {anio}', horizontal=True)
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    titulo = 'REGISTRO DE ESTADÍSTICAS DE SEGURIDAD Y SALUD EN EL TRABAJO'
    story = [_cabecera(W, cw, titulo, COD_EST, cfg, 12, 7, 12, 4, 18), Spacer(1, 4),
             _tabla([[P('N° REGISTRO', TH), P(f'EST-{anio}')]], [1, 3], W * 0.3, izquierda=True), Spacer(1, 4),
             _bloque_empleador(W, cfg), Spacer(1, 3),
             _texto(W, 'DESCRIBIR LOS RESULTADOS ESTADÍSTICOS (comparar con los objetivos del sistema de gestión de '
                       'SST' + (f' · {informe.periodo}' if informe else '') + ')',
                    informe.resultados if informe else '', alto=60),
             _texto(W, 'ANÁLISIS DE LAS CAUSAS QUE ORIGINARON LAS DESVIACIONES',
                    informe.causas_desviaciones if informe else '', alto=50),
             _texto(W, 'CONCLUSIONES Y RECOMENDACIONES', informe.conclusiones if informe else '', alto=50),
             Spacer(1, 3), _responsables(W, [informe.firma if informe else {}], 'RESPONSABLE DEL REGISTRO'),
             PageBreak(), _cabecera(W, cw, titulo, COD_EST, cfg, 12, 7, 12, 4, 18), Spacer(1, 4)]
    cab = [P('Información', TH), ''] + [P(m, TH) for m in MES_CORTO] + [P('Total', TH)]
    a = 'areas_'

    def fila(etq, clave, total=True, dec=False, areas=False, sub=False):
        valores = [None if m['futuro'] else m[clave] for m in meses]
        if areas:
            return [P('Área / sede', THL), ''] + [P('' if v is None else _areas(v), TD) for v in valores] + [P('')]
        tot = sum(v or 0 for v in valores) if total else ''
        return [P(etq, THL), ''] + [P('' if v is None else _num(v, dec)) for v in valores] + [P(_num(tot, dec) if total else '')]

    filas = [[P(f'ESTADÍSTICA DE ACCIDENTES, INCIDENTES E INCIDENTES PELIGROSOS — {anio}', TH)] + [''] * 14, cab,
             fila('N° total de trabajadores', 'trabajadores', total=False),
             fila('N° accidentes mortales', 'mortales'), fila('', a + 'mortales', areas=True),
             fila('N° accidentes de trabajo leves', 'leves'), fila('', a + 'leves', areas=True),
             fila('N° accidentes incapacitantes', 'incapacitantes'), fila('', a + 'incapacitantes', areas=True),
             fila('Horas-hombre trabajadas (HH)', 'horas_hombre'),
             fila('Índice de frecuencia (IF)', 'indice_frecuencia', total=False, dec=True),
             fila('N° días perdidos', 'dias_perdidos'),
             fila('Índice de gravedad (IG)', 'indice_gravedad', total=False, dec=True),
             fila('Índice de accidentabilidad (IA)', 'indice_accidentabilidad', total=False, dec=True),
             fila('N° de incidentes', 'incidentes'), fila('', a + 'incidentes', areas=True),
             fila('N° de incidentes peligrosos', 'incidentes_peligrosos'), fila('', a + 'peligrosos', areas=True)]
    extra = [('SPAN', (0, 0), (-1, 0))] + [('SPAN', (0, r), (1, r)) for r in range(1, len(filas))]
    story += [_tabla(filas, [6, 4] + [3] * 12 + [3], W, extra=extra, cabeceras=[0, 1]),
              Paragraph('IF = N° accidentes incapacitantes × 1 000 000 / HH · IG = N° días perdidos × 1 000 000 / HH · '
                        'IA = IF × IG / 1000 (R.M. 050-2013-TR).', NOTA), Spacer(1, 6)]
    filas = [[P('ESTADÍSTICA DE ENFERMEDADES OCUPACIONALES Y DESCANSOS MÉDICOS', TH)] + [''] * 14, cab,
             fila('N° enfermedades ocupacionales', 'enfermedades'), fila('', a + 'enfermedades', areas=True),
             fila('N° trabajadores expuestos al agente', 'expuestos'),
             fila('Tasa de incidencia', 'tasa_incidencia', total=False, dec=True),
             fila('N° trabajadores con cáncer profesional', 'cancer'),
             fila('N° trabajadores con descanso médico', 'trabajadores_dm'),
             fila('Días de descanso médico (calendario)', 'dias_dm_calendario'),
             fila('Días de descanso médico (laborables)', 'dias_dm_laborales'),
             fila('Horas-hombre con descanso médico', 'hh_dm')]
    extra = [('SPAN', (0, 0), (-1, 0))] + [('SPAN', (0, r), (1, r)) for r in range(1, len(filas))]
    story.append(_tabla(filas, [6, 4] + [3] * 12 + [3], W, extra=extra, cabeceras=[0, 1]))
    doc.build(story)
    return buf.getvalue()


def generar_datos_estadisticas_pdf(anio, meses) -> bytes:
    """Datos para el registro de estadísticas: una fila por mes."""
    buf = BytesIO()
    doc = _doc(buf, f'Datos para estadísticas SST {anio}', horizontal=True)
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    fs = ParagraphStyle('dts', parent=TD, fontSize=6, leading=7)
    fh = ParagraphStyle('dth', parent=TH, fontSize=5.6, leading=6.6)

    def h(t):
        return Paragraph(esc_pdf(t), fh)

    def c(t):
        return Paragraph(esc_pdf(_limpio(_txt(t))), fs)

    filas = [[h('MES'), h('N° ACCIDENTES MORTALES'), h('ÁREA / SEDE'), h('N° ACCIDENTES LEVES'), h('ÁREA / SEDE'),
              h('SOLO PARA ACCIDENTES INCAPACITANTES'), '', '', '', '', '', '', h('ENFERMEDAD OCUPACIONAL'), '', '', '',
              '', h('N° INCIDENTES PELIGROSOS'), h('ÁREA / SEDE'), h('N° INCIDENTES'), h('ÁREA / SEDE')],
             ['', '', '', '', '', h('N° ACCIDENTES INCAPACITANTES'), h('ÁREA / SEDE'), h('TOTAL HORAS-HOMBRE'),
              h('ÍNDICE DE FRECUENCIA'), h('N° DÍAS PERDIDOS'), h('ÍNDICE DE GRAVEDAD'), h('ÍNDICE DE ACCIDENTABILIDAD'),
              h('N° ENFERMEDADES OCUPACIONALES'), h('ÁREA / SEDE'), h('N° TRABAJADORES EXPUESTOS'),
              h('TASA DE INCIDENCIA'), h('N° CON CÁNCER PROFESIONAL'), '', '', '', '']]
    for m in meses:
        if m['futuro']:
            filas.append([c(m['nombre'].upper())] + [''] * 20)
            continue
        filas.append([c(m['nombre'].upper()), c(m['mortales']), c(_areas(m['areas_mortales'])), c(m['leves']),
                      c(_areas(m['areas_leves'])), c(m['incapacitantes']), c(_areas(m['areas_incapacitantes'])),
                      c(_num(m['horas_hombre'])), c(_num(m['indice_frecuencia'], True)), c(m['dias_perdidos']),
                      c(_num(m['indice_gravedad'], True)), c(_num(m['indice_accidentabilidad'], True)),
                      c(m['enfermedades']), c(_areas(m['areas_enfermedades'])), c(m['expuestos']),
                      c(_num(m['tasa_incidencia'], True)), c(m['cancer']), c(m['incidentes_peligrosos']),
                      c(_areas(m['areas_peligrosos'])), c(m['incidentes']), c(_areas(m['areas_incidentes']))])
    anchos = [6, 4, 6, 4, 6, 4, 6, 5, 4, 4, 4, 4, 4, 6, 4, 4, 4, 4, 6, 4, 6]
    extra = [('SPAN', (5, 0), (11, 0)), ('SPAN', (12, 0), (16, 0))] + [
        ('SPAN', (i, 0), (i, 1)) for i in (0, 1, 2, 3, 4, 17, 18, 19, 20)]
    story = [_cabecera(W, cw, 'DATOS PARA REGISTRO DE ESTADÍSTICAS DE SEGURIDAD Y SALUD EN EL TRABAJO', COD_DAT, cfg,
                       12, 7, 11, 4, 18), Spacer(1, 4),
             _tabla([[P('FECHA DE ACTUALIZACIÓN:', THL), P(_solo_fecha(timezone.localdate()))]], [1, 1], W * 0.35,
                    izquierda=True),
             Spacer(1, 4), _tabla(filas, anchos, W, extra=extra, cabeceras=[0, 1]),
             Paragraph('Índices según la R.M. 050-2013-TR: IF = incapacitantes × 1 000 000 / HH; IG = días perdidos × '
                       '1 000 000 / HH; IA = IF × IG / 1000; tasa de incidencia = enfermedades × 1 000 000 / expuestos.',
                       NOTA)]
    doc.build(story)
    return buf.getvalue()
