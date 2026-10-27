"""
Acta de reunión del Comité de SST (borrador para imprimir y firmar, con la estructura del formato de actas) y
Programa anual de seguridad, salud ocupacional y medio ambiente.
"""
from io import BytesIO

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph, Spacer

from esynapse_sig.ficha_pdf import CONTROL_FORMATOS, _cargar_cfg, _solo_fecha, esc_pdf
from quejas.pdf import _cabecera

from .pdf_eventos import TD, TDL, TH, THL, P, _doc, _empleador, _tabla

COD_ACTA, COD_PROGRAMA = 'SIG-PRO-13-r08', 'SIG-PL-01-r01'
CONTROL_FORMATOS.setdefault(COD_ACTA, ('01', '2025-05-08', 'ASIG', 'GSIG', 'GG'))
CONTROL_FORMATOS.setdefault(COD_PROGRAMA, ('01', '2026-02-13', 'ASIG', 'GSIG / GG', 'GG'))
MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']
MESES_LARGO = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'setiembre', 'octubre',
               'noviembre', 'diciembre']
TXT = ParagraphStyle('actxt', fontName='Helvetica', fontSize=9, leading=12, alignment=TA_JUSTIFY)
TXB = ParagraphStyle('actxb', parent=TXT, fontName='Helvetica-Bold')


def _fecha_larga(f):
    return f'{f.day} de {MESES_LARGO[f.month - 1]} de {f.year}' if f else '[fecha]'


def generar_acta_pdf(r) -> bytes:
    """Acta de la reunión con los datos registrados, para imprimir, firmar y adjuntar."""
    buf = BytesIO()
    doc = _doc(buf, f'Acta {r.codigo}')
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    c = r.comite
    asis = set(r.asistentes.values_list('pk', flat=True))
    miembros = list(c.miembros.filter(is_active=True, fecha_baja__isnull=True).select_related('trabajador__puesto'))
    hora = r.hora.strftime('%H:%M') if r.hora else '[hora]'
    story = [_cabecera(W, cw, f'ACTA DE REUNIÓN DEL COMITÉ DE SEGURIDAD Y SALUD EN EL TRABAJO', COD_ACTA, cfg, 12, 7, 11,
                       4, 18), Spacer(1, 8),
             Paragraph(f'<b>ACTA Nº {esc_pdf(r.codigo)}</b> — Reunión {esc_pdf(r.get_tipo_display().lower())}',
                       TXT), Spacer(1, 6),
             Paragraph(esc_pdf(f'De acuerdo con lo regulado por la Ley Nº 29783, Ley de Seguridad y Salud en el Trabajo, '
                               f'y su Reglamento, aprobado por el Decreto Supremo Nº 005-2012-TR, siendo las {hora} '
                               f'horas del {_fecha_larga(r.fecha)}, en {r.lugar or "[lugar]"} de '
                               f'{_empleador(cfg)[0]}, se reunieron los miembros del Comité de Seguridad y Salud en '
                               f'el Trabajo del periodo {c.periodo}:'), TXT), Spacer(1, 4)]
    for rep, rep_n in (('empleador', 'del empleador'), ('trabajadores', 'de los trabajadores')):
        for cond, cond_n in (('titular', 'titulares'), ('suplente', 'suplentes')):
            lista = [m for m in miembros if m.representacion == rep and m.condicion == cond]
            if not lista:
                continue
            story.append(Paragraph(f'<b>Miembros {cond_n} {rep_n}:</b>', TXT))
            for n, m in enumerate(lista, 1):
                presente = 'asistió' if m.pk in asis else 'no asistió'
                cargo = f' — {m.get_cargo_display()}' if m.cargo != 'miembro' else ''
                story.append(Paragraph(esc_pdf(f'{n}.- {m.trabajador.nombre_completo}, DNI {m.trabajador.documento or "—"}, '
                                               f'{m.trabajador.puesto.nombre}{cargo} ({presente})'), TXT))
            story.append(Spacer(1, 3))
    if r.invitados:
        story += [Paragraph(f'<b>Invitados:</b> {esc_pdf(r.invitados)}', TXT), Spacer(1, 3)]
    q = r.quorum()
    story += [Paragraph(esc_pdf(f'Asisten {q["presentes"]} de {q["titulares"]} miembros titulares; quórum requerido: '
                                f'{q["requerido"]} (artículo 69 del Decreto Supremo Nº 005-2012-TR). '
                                + ('Habiéndose verificado el quórum, se inicia la sesión.' if q['hay_quorum'] else
                                   'NO HAY QUÓRUM.')), TXT), Spacer(1, 6),
              Paragraph('<b>AGENDA:</b>', TXT)]
    story += [Paragraph(esc_pdf(f'{n}. {a}'), TXT) for n, a in enumerate(r.agenda or [], 1)] or \
        [Paragraph('—', TXT)]
    story += [Spacer(1, 6), Paragraph('<b>DESARROLLO DE LA REUNIÓN</b>', TXT),
              Paragraph(esc_pdf(r.desarrollo or '—').replace('\n', '<br/>'), TXT), Spacer(1, 6),
              Paragraph('<b>ACUERDOS</b>', TXT)]
    acuerdos = list(r.acuerdos.filter(is_active=True).select_related('responsable'))
    if acuerdos:
        filas = [[P('N°', TH), P('ACUERDO', TH), P('RESPONSABLE', TH), P('PLAZO', TH)]]
        for a in acuerdos:
            filas.append([P(a.orden), P(a.descripcion, TDL), P(a.responsable.nombre_completo if a.responsable_id else ''),
                          P(_solo_fecha(a.plazo.isoformat()) if a.plazo else '')])
        story.append(_tabla(filas, [1.2, 14, 6, 3.5], W, cabeceras=[0]))
    else:
        story.append(Paragraph('Sin acuerdos.', TXT))
    if r.proxima_reunion:
        story += [Spacer(1, 4), Paragraph(esc_pdf(f'Se cita a la siguiente reunión para el {_fecha_larga(r.proxima_reunion)}.'),
                                          TXT)]
    story += [Spacer(1, 6), Paragraph('Se da por concluida la reunión, firmando los asistentes en señal de conformidad.',
                                      TXT), Spacer(1, 16)]
    firmas = [[P('Representantes del empleador', TH), P('Representantes de los trabajadores', TH)]]
    emp = [m for m in miembros if m.representacion == 'empleador' and m.pk in asis]
    trab = [m for m in miembros if m.representacion == 'trabajadores' and m.pk in asis]
    for i in range(max(len(emp), len(trab), 1)):
        celda = lambda m: Paragraph(  # noqa
            f'<br/><br/>_____________________________<br/>{esc_pdf(m.trabajador.nombre_completo)}<br/>'
            f'{esc_pdf(m.get_cargo_display() if m.cargo != "miembro" else "Miembro " + m.get_condicion_display().lower())}',
            TD) if m else ''
        firmas.append([celda(emp[i] if i < len(emp) else None), celda(trab[i] if i < len(trab) else None)])
    story.append(KeepTogether(_tabla(firmas, [1, 1], W, cabeceras=[0])))
    doc.build(story)
    return buf.getvalue()


def generar_programa_ssoma_pdf(p) -> bytes:
    buf = BytesIO()
    doc = _doc(buf, f'Programa anual SSOMA {p.anio}', horizontal=True)
    W, cfg = doc.width, _cargar_cfg()
    cw = [W / 24] * 24
    d = _empleador(cfg)
    objetivos = list(p.objetivos.filter(is_active=True))
    filas = [[P('ITEM', TH), P('ACTIVIDAD', TH), P('RESPONSABLE', TH), P('ESTADO', TH), P(str(p.anio), TH)]
             + [''] * 11 + [P('AVANCE %', TH)],
             ['', '', '', ''] + [P(m, TH) for m in MESES] + ['']]
    extra = [('SPAN', (4, 0), (15, 0))] + [('SPAN', (c, 0), (c, 1)) for c in (0, 1, 2, 3, 16)]
    from reportlab.lib import colors
    verde, gris = colors.HexColor('#C6EFCE'), colors.HexColor('#E7E6E6')
    romanos = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']
    n = 0
    for i, o in enumerate(objetivos):
        filas.append([P(romanos[i] if i < len(romanos) else i + 1, TH), P(f'{o.codigo} {o.descripcion}', THL)]
                     + [''] * 15)
        extra += [('SPAN', (1, len(filas) - 1), (16, len(filas) - 1)),
                  ('BACKGROUND', (0, len(filas) - 1), (-1, len(filas) - 1), gris)]
        for a in o.actividades.filter(is_active=True).select_related('responsable'):
            n += 1
            r1 = len(filas)
            filas.append([P(n), P(a.descripcion, TDL), P(a.responsable.nombre if a.responsable_id else ''),
                          P('Programado')] + [P('P') if m in (a.meses or []) else '' for m in range(1, 13)]
                         + [P(f'{a.avance}%')])
            filas.append(['', '', '', P('Ejecutado')] + [P('E') if m in (a.meses_ejecutados or []) else ''
                                                         for m in range(1, 13)] + [''])
            extra += [('SPAN', (0, r1), (0, r1 + 1)), ('SPAN', (1, r1), (1, r1 + 1)), ('SPAN', (2, r1), (2, r1 + 1)),
                      ('SPAN', (16, r1), (16, r1 + 1))]
            for m in a.meses_ejecutados or []:
                extra.append(('BACKGROUND', (3 + m, r1 + 1), (3 + m, r1 + 1), verde))
    obj_txt = '<br/>'.join(esc_pdf(f'{o.codigo} {o.descripcion}') for o in objetivos)
    datos = _tabla([[P('RAZÓN SOCIAL', TH), P('RUC', TH), P('DOMICILIO', TH), P('AÑO', TH), P('ACTIVIDAD ECONÓMICA', TH),
                     P('NÚMERO DE TRABAJADORES', TH)],
                    [P(d[0]), P(d[1]), P(d[2]), P(p.anio), P(d[3]), P(d[4])]], [20, 8, 28, 5, 18, 8], W, cabeceras=[0])
    cab2 = _tabla([[P('OBJETIVOS', THL), Paragraph(obj_txt, TDL)],
                   [P('FECHA', THL), P(_solo_fecha(p.fecha.isoformat()) if p.fecha else '', TDL)],
                   [P('RECURSOS', THL), P(p.recursos, TDL)]], [4, 30], W)
    from .comite_pdf import bloque_firmas_comite
    el, rv = p.elaborado or {}, p.revisado or {}
    pie = [_tabla([[P('Elaborado por', TH), P('Revisado por', TH), P('Fecha de actualización', TH)],
                   [P(esc_pdf(f'{el.get("nombre", "")} · {el.get("cargo", "")} · {_solo_fecha(el.get("fecha") or "")}')),
                    P(esc_pdf(f'{rv.get("nombre", "")} · {rv.get("cargo", "")} · {_solo_fecha(rv.get("fecha") or "")}')),
                    P(_solo_fecha(p.fecha_actualizacion.isoformat()) if p.fecha_actualizacion else '')]],
                  [10, 10, 5], W, cabeceras=[0]), Spacer(1, 3)]
    if p.estado == 'aprobado':
        pie += bloque_firmas_comite(W, p.aprobado or [], fecha=p.fecha_actualizacion)
    else:
        pie += bloque_firmas_comite(W, nota=f'PENDIENTE DE APROBACIÓN DEL COMITÉ DE SST (versión {p.version}).')
    story = [_cabecera(W, cw, 'PROGRAMA ANUAL DE SEGURIDAD, SALUD OCUPACIONAL Y MEDIO AMBIENTE', COD_PROGRAMA, cfg, 12,
                       7, 11, 4, 18), Spacer(1, 4), datos, Spacer(1, 3), cab2, Spacer(1, 4),
             _tabla(filas, [1.6, 16, 6, 3.6] + [1.3] * 12 + [2.6], W, extra=extra, cabeceras=[0, 1]), Spacer(1, 4),
             Paragraph(f'Leyenda: P programado · E ejecutado · Versión {p.version}', TDL), Spacer(1, 4),
             KeepTogether(pie)]
    doc.build(story)
    return buf.getvalue()
