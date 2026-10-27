"""
Formatos impresos de EPP (matriz de EPP por puesto de trabajo y entrega de equipo de protección personal)
y de vigilancia médica (registro de exámenes médicos ocupacionales: solo aptitud, sin diagnóstico).
"""
from io import BytesIO

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, Spacer

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _solo_fecha, esc_pdf
from quejas.pdf import _cabecera

from .epp import APTITUDES, TIPOS_EMO, TIPOS_PROTECCION, CatalogoEPP, PerfilEPP
from .pdf_eventos import NOTA, TD, TDL, TH, THL, P, _doc, _empleador, _tabla, _texto

COD_MATRIZ, COD_ENTREGA, COD_EMO = 'SIG-PRO-27-r01', 'SIG-PRO-27-r02', 'SIG-PRO-06-r17'
CONTROL_FORMATOS.setdefault(COD_MATRIZ, ('01', '2026-02-12', 'ASIG', 'GSIG/GG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_ENTREGA, ('02', '2026-04-02', 'ASIG', 'GSIG/GG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_EMO, ('00', '2026-10-22', 'ASIG', 'GSIG', 'GG'))
TH6 = ParagraphStyle('epth6', parent=TH, fontSize=5.5, leading=6.5)
TD6 = ParagraphStyle('eptd6', parent=TD, fontSize=6, leading=7)


def _f(fecha):
    return fecha.strftime('%d/%m/%Y') if fecha else ''


def _firma_txt(f, campo='nombre'):
    if not f:
        return ''
    return f.get(campo, '') or ''


def _bloque_empleador(W, cfg, n=None):
    d = _empleador(cfg)
    return _tabla([[P('DATOS DEL EMPLEADOR', TH), '', '', '', ''],
                   [P('RAZÓN SOCIAL O DENOMINACIÓN SOCIAL', TH), P('RUC', TH),
                    P('DOMICILIO (dirección, distrito, departamento, provincia)', TH), P('ACTIVIDAD ECONÓMICA', TH),
                    P('N° TRABAJADORES EN EL CENTRO LABORAL', TH)],
                   [P(d[0]), P(d[1]), P(d[2]), P(d[3]), P(n if n is not None else d[4])]],
                  [24, 10, 30, 20, 12], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1])


# ===================================================================== matriz por puesto
def generar_matriz_epp_pdf() -> bytes:
    buf = BytesIO()
    doc = _doc(buf, 'Matriz de EPP por puesto de trabajo', horizontal=True)
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    perfiles = list(PerfilEPP.objects.filter(is_active=True).prefetch_related('requisitos', 'puestos'))
    usados = {r.epp_id for p in perfiles for r in p.requisitos.all()}
    epps = list(CatalogoEPP.objects.filter(is_active=True, pk__in=usados))
    filas = [[P('N°', TH), P('ÁREA', TH), P('PUESTO DE TRABAJO', TH)] + [P(esc_pdf(e.nombre), TH6) for e in epps],
             ['', '', P('CLASIFICACIÓN', TH6)] + [P('Básico' if e.clasificacion == 'basico' else 'Espec.', TD6) for e in epps],
             ['', '', P('TIEMPO DE VIDA', TH6)] + [P(f'{e.vida_util_meses} meses' if e.vida_util_meses else '—', TD6)
                                                   for e in epps]]
    extra = [('SPAN', (0, 0), (0, 2)), ('SPAN', (1, 0), (1, 2))]
    grupo, n, desde = None, 0, None
    for p in perfiles:
        req = {r.epp_id: r.nivel for r in p.requisitos.all()}
        if p.grupo != grupo:
            if desde is not None and len(filas) - 1 > desde:
                extra += [('SPAN', (0, desde), (0, len(filas) - 1)), ('SPAN', (1, desde), (1, len(filas) - 1))]
            grupo, n, desde = p.grupo, n + 1, len(filas)
            pref = [P(n), P(grupo, TD6)]
        else:
            pref = ['', '']
        filas.append(pref + [P(p.nombre, TD6)] + [P({'obligatorio': 'x', 'segun_tarea': 'x*'}.get(req.get(e.pk), ''),
                                                    TD6) for e in epps])
    if desde is not None and len(filas) - 1 > desde:
        extra += [('SPAN', (0, desde), (0, len(filas) - 1)), ('SPAN', (1, desde), (1, len(filas) - 1))]
    anchos = [1.2, 4, 9] + [1.7] * len(epps)
    story = [_cabecera(W, cw, 'MATRIZ DE EQUIPOS DE PROTECCIÓN PERSONAL POR PUESTO DE TRABAJO', COD_MATRIZ, cfg, 12, 7,
                       12, 4, 18), Spacer(1, 4), _tabla(filas, anchos, W, extra=extra, cabeceras=[0, 1, 2]),
             Spacer(1, 3), Paragraph('x: obligatorio · x*: según la tarea', NOTA)]
    doc.build(story)
    return buf.getvalue()


# ======================================================================== entrega de EPP
def _bloque_entregas(W, cfg, t, par, epps):
    """Una hoja del formato: datos del trabajador y hasta dos entregas en columnas."""
    a = par[0]
    items = [{it.epp_id: it for it in e.items.filter(is_active=True)} for e in par]
    cab = [P('TIPO', TH), P('Cant.', TH), P('Talla', TH), P('EPP', TH)]
    sub = ['', '', '', '']
    for e in par + [None] * (2 - len(par)):
        cab += [P(f'N° de entrega: {e.codigo if e else "_____"}', TH), '', '', '', P('Observaciones', TH)]
        sub += [P('Fecha de entrega', TH6), P('Firma trabajador', TH6), P('Responsable de entrega', TH6),
                P('Firma de responsable', TH6), '']
    filas = [cab, sub]
    extra = [('SPAN', (c, 0), (c, 1)) for c in range(4)] + [('SPAN', (4, 0), (7, 0)), ('SPAN', (8, 0), (8, 1)),
                                                             ('SPAN', (9, 0), (12, 0)), ('SPAN', (13, 0), (13, 1))]
    tipos = dict(TIPOS_PROTECCION)
    tipo_prev, desde = None, None
    for epp in epps:
        it0 = next((d[epp.pk] for d in items if epp.pk in d), None)
        fila = [P(tipos[epp.tipo], TD6) if epp.tipo != tipo_prev else '', P(it0.cantidad if it0 else ''),
                P(it0.talla if it0 else ''), P(epp.nombre, ParagraphStyle('epl', parent=TDL, fontSize=6.5, leading=7.5))]
        for i in range(2):
            e = par[i] if i < len(par) else None
            it = items[i].get(epp.pk) if e else None
            if it:
                ft, fr = e.firma_trabajador or {}, e.firma_responsable or {}
                firma_t = {'pin': 'Firmado con PIN', 'usuario': 'Firmado con su usuario', 'papel': 'Cargo en papel adjunto'}.get(ft.get('metodo'), '') if ft else ''
                fila += [P(_f(e.fecha), TD6), P(firma_t, TD6), P(_firma_txt(fr), TD6),
                         P('Firma electrónica' if fr else '', TD6), P(it.observaciones, TD6)]
            else:
                fila += ['', '', '', '', '']
        if epp.tipo != tipo_prev:
            if desde is not None and len(filas) - 1 > desde:
                extra.append(('SPAN', (0, desde), (0, len(filas) - 1)))
            tipo_prev, desde = epp.tipo, len(filas)
        filas.append(fila)
    if desde is not None and len(filas) - 1 > desde:
        extra.append(('SPAN', (0, desde), (0, len(filas) - 1)))
    datos = _tabla([[P('DATOS DEL TRABAJADOR', TH), '', '', '', '', '', '', ''],
                    [P('NOMBRE:', THL), P(t.nombre_completo, TDL), P('DNI:', THL), P(t.documento, TDL),
                     P('ÁREA:', THL), P(a.area, TDL), P('PUESTO DE TRABAJO:', THL), P(a.puesto, TDL)]],
                   [5, 14, 3, 6, 4, 12, 7, 12], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0])
    tabla = _tabla(filas, [6, 2.4, 2.2, 10] + [3.2, 3.6, 4, 3.6, 5] * 2, W, cabeceras=[0, 1],
                   extra=extra + [('TOPPADDING', (0, 2), (-1, -1), 1), ('BOTTOMPADDING', (0, 2), (-1, -1), 1)])
    return [datos, Spacer(1, 3), tabla]


def generar_entregas_pdf(trabajador, entregas) -> bytes:
    buf = BytesIO()
    doc = _doc(buf, f'Entrega de EPP {trabajador.nombre_completo}', horizontal=True)
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    epps = list(CatalogoEPP.objects.filter(is_active=True).order_by('orden', 'nombre'))
    orden_tipo = [k for k, _ in TIPOS_PROTECCION]
    epps.sort(key=lambda e: (orden_tipo.index(e.tipo), e.orden, e.nombre))
    story = []
    pares = [entregas[i:i + 2] for i in range(0, len(entregas), 2)] or [[]]
    for n, par in enumerate(pares):
        if n:
            story.append(PageBreak())
        story += [_cabecera(W, cw, 'ENTREGA DE EQUIPO DE PROTECCIÓN PERSONAL', COD_ENTREGA, cfg, 12, 7, 12, 4, 18),
                  Spacer(1, 4),
                  _tabla([[P('N° REGISTRO:', TH), P(', '.join(e.codigo for e in par))]], [1, 3], W * 0.35,
                         izquierda=True), Spacer(1, 3), _bloque_empleador(W, cfg), Spacer(1, 3)]
        if par:
            story += _bloque_entregas(W, cfg, trabajador, par, epps)
            obs = ' · '.join(f'{e.codigo}: {e.get_tipo_display()}' + (f' ({e.get_motivo_display()})' if e.motivo else '')
                             + (f' — {e.observaciones}' if e.observaciones else '') for e in par)
            story += [Spacer(1, 3), Paragraph(esc_pdf(obs), NOTA)]
        else:
            story.append(Paragraph('El trabajador no tiene entregas firmadas.', TDL))
    doc.build(story)
    return buf.getvalue()


# ================================================================== exámenes médicos
def generar_emo_pdf(ev) -> bytes:
    buf = BytesIO()
    doc = _doc(buf, f'Registro de exámenes médicos ocupacionales {ev.codigo}')
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    rs = list(ev.resultados.filter(is_active=True).select_related('trabajador'))
    apt = dict(APTITUDES)
    filas = [[P('N°', TH), P('APELLIDOS Y NOMBRES', TH), P('N° DNI / CE', TH), P('PUESTO DE TRABAJO', TH),
              P('ÁREA', TH), P('RESULTADO DE APTITUD', TH), P('RESTRICCIONES / RECOMENDACIONES (sin diagnóstico)', TH),
              P('FECHA DEL PRÓXIMO EXAMEN', TH)]]
    for n, r in enumerate(rs, 1):
        filas.append([P(n), P(r.trabajador.nombre_completo, TDL), P(r.trabajador.documento), P(r.puesto, TD6),
                      P(r.area, TD6), P(apt.get(r.aptitud, '')), P(r.restricciones, TDL), P(_f(r.fecha_proximo))])
    if not rs:
        filas.append([''] * 8)
    tot = {k: sum(1 for r in rs if r.aptitud == k) for k, _ in APTITUDES}
    medidas = [[P('MEDIDAS CORRECTIVAS', TH), '', '', ''],
               [P('DESCRIPCIÓN DE LA MEDIDA CORRECTIVA', TH), P('NOMBRE DEL RESPONSABLE', TH),
                P('FECHA DE EJECUCIÓN', TH), P('ESTADO (realizada, pendiente, en ejecución)', TH)]]
    for m in ev.medidas or []:
        medidas.append([P(m.get('descripcion'), TDL), P(m.get('responsable')), P(_solo_fecha(m.get('fecha') or '')),
                        P(m.get('estado'))])
    if not ev.medidas:
        medidas.append(['', '', '', ''])
    f = ev.firma_registro or {}
    story = [
        _cabecera(W, cw, 'REGISTRO DE EXÁMENES MÉDICOS OCUPACIONALES', COD_EMO, cfg, 12, 7, 12, 4, 18), Spacer(1, 4),
        _tabla([[P('N° REGISTRO', TH), P(ev.codigo)]], [1, 2], W * 0.35, izquierda=True), Spacer(1, 3),
        _bloque_empleador(W, cfg), Spacer(1, 3),
        _tabla([[P('DATOS DE LA EVALUACIÓN MÉDICA', TH), '', '', ''],
                [P('TIPO DE EXAMEN', TH), P('FECHA DE LA EVALUACIÓN', TH), P('CENTRO MÉDICO / IPRESS', TH),
                 P('MÉDICO OCUPACIONAL RESPONSABLE (CMP)', TH)],
                [P(dict(TIPOS_EMO).get(ev.tipo)), P(_f(ev.fecha)), P(ev.centro_medico),
                 P(f'{ev.medico}' + (f' (CMP {ev.cmp})' if ev.cmp else ''))]],
               [10, 8, 14, 16], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1]), Spacer(1, 3),
        _tabla(filas, [1.8, 11, 4.5, 7, 6, 5, 11, 5], W, cabeceras=[0]), Spacer(1, 3),
        Paragraph(esc_pdf(f'Total de trabajadores evaluados: {len(rs)} · Aptos: {tot["apto"]} · Aptos con '
                          f'restricciones: {tot["apto_restricciones"]} · No aptos: {tot["no_apto"]} · Observados: '
                          f'{tot["observado"]}'), TDL),
        Paragraph('Solo se registra la aptitud. Los resultados clínicos y diagnósticos son confidenciales y los '
                  'custodia el médico ocupacional.', NOTA), Spacer(1, 4),
        _tabla(medidas, [24, 10, 6, 10], W, extra=[('SPAN', (0, 0), (-1, 0))], cabeceras=[0, 1]), Spacer(1, 4),
        KeepTogether(_tabla([[P('RESPONSABLE DEL REGISTRO', TH), ''],
                             [P('Nombre:', THL), P(f.get('nombre', ''), TDL)],
                             [P('Cargo:', THL), P(f.get('cargo', ''), TDL)],
                             [P('Fecha:', THL), P(_solo_fecha(f.get('fecha') or ''), TDL)],
                             [P('Firma:', THL), P('Firmado electrónicamente' if f else '', TDL)]],
                            [8, 30], W * 0.6, extra=[('SPAN', (0, 0), (1, 0))], cabeceras=[0], izquierda=True)),
    ]
    if ev.observaciones:
        story[-1:-1] = [_texto(W, 'OBSERVACIONES', ev.observaciones), Spacer(1, 4)]
    doc.build(story)
    return buf.getvalue()

