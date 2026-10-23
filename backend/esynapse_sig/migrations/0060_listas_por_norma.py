"""
Listas de verificación de ISO 9001, ISO 14001 e ISO 45001 auditadas por
separado. Se derivan de la lista integrada: cada norma recibe solo las
preguntas que ella exige, con su propio numeral como referencia, los títulos de
cláusula con el nombre que usa esa norma y, en las preguntas comunes que en la
integrada aclaran "(en SST, …)" o "(en ambiental, …)", la redacción propia de
esa norma. La columna Nro. es un correlativo por lista.

Se guardan en el catálogo con bloque 'lista'; las filas 'requisitos' de esas
normas siguen siendo los títulos de cláusula de los selectores.
"""
import re

from django.db import migrations

CLAVE = {'ISO 9001': 'iso_9001', 'ISO 14001': 'iso_14001', 'ISO 45001': 'iso_45001'}
N9, N14, N45 = 'iso_9001', 'iso_14001', 'iso_45001'

# Títulos de capítulo / cláusula propios de cada norma (si no figura aquí, se
# usa el de la integrada sin las aclaraciones entre paréntesis).
TITULOS = {
    '4.2': {N9: 'Comprensión de las necesidades y expectativas de las partes interesadas',
            N14: 'Comprensión de las necesidades y expectativas de las partes interesadas',
            N45: 'Comprensión de las necesidades y expectativas de los trabajadores y de otras partes interesadas'},
    '4.3': {N9: 'Determinación del alcance del sistema de gestión de la calidad',
            N14: 'Determinación del alcance del sistema de gestión ambiental',
            N45: 'Determinación del alcance del sistema de gestión de la SST'},
    '4.4': {N9: 'Sistema de gestión de la calidad y sus procesos',
            N14: 'Sistema de gestión ambiental',
            N45: 'Sistema de gestión de la SST'},
    '5': {N9: 'LIDERAZGO', N14: 'LIDERAZGO', N45: 'LIDERAZGO Y PARTICIPACIÓN DE LOS TRABAJADORES'},
    '5.2': {N9: 'Política de la calidad', N14: 'Política ambiental', N45: 'Política de la SST'},
    '6.2': {N9: 'Objetivos de la calidad y planificación para lograrlos',
            N14: 'Objetivos ambientales y planificación para lograrlos',
            N45: 'Objetivos de la SST y planificación para lograrlos'},
    '8.2': {N9: 'Requisitos para los productos y servicios',
            N14: 'Preparación y respuesta ante emergencias',
            N45: 'Preparación y respuesta ante emergencias'},
    '10.2': {N9: 'No conformidad y acción correctiva', N14: 'No conformidad y acción correctiva',
             N45: 'Incidentes, no conformidades y acciones correctivas'},
}

# Redacción propia por norma de las preguntas comunes de la integrada (clave:
# N.° de la pregunta en la lista integrada).
VARIANTES = {
    5: {N14: '¿Se ha determinado cuáles de esas necesidades y expectativas se convierten en obligaciones de cumplimiento?',
        N45: '¿Se ha determinado cuáles de esas necesidades y expectativas son, o podrían convertirse, en requisitos legales y otros requisitos?'},
    4: {N9: '¿Se han determinado las partes interesadas pertinentes al sistema de gestión de la calidad y sus requisitos pertinentes?',
        N14: '¿Se han determinado las partes interesadas pertinentes al sistema de gestión ambiental y sus necesidades y expectativas pertinentes?',
        N45: '¿Se han determinado, además de los trabajadores, las otras partes interesadas pertinentes al sistema de gestión de la SST y sus necesidades y expectativas pertinentes?'},
    7: {N9: '¿Se han determinado los límites y la aplicabilidad del sistema de gestión de la calidad considerando las cuestiones externas e internas, los requisitos de las partes interesadas y los productos y servicios de la organización?',
        N14: '¿Se han determinado los límites y la aplicabilidad del sistema de gestión ambiental considerando las cuestiones externas e internas y las obligaciones de cumplimiento?',
        N45: '¿Se han determinado los límites y la aplicabilidad del sistema de gestión de la SST considerando las cuestiones externas e internas y los requisitos de los trabajadores y de otras partes interesadas?'},
    8: {N14: '¿El alcance considera las unidades, funciones y límites físicos de la organización, sus actividades, productos y servicios, y su autoridad y capacidad para ejercer control e influencia?',
        N45: '¿El alcance incluye las actividades, productos y servicios bajo el control o la influencia de la organización que pueden afectar al desempeño de la SST, considerando las actividades relacionadas con el trabajo planificadas o realizadas?'},
    10: {N9: '¿El alcance está disponible y se mantiene como información documentada?',
         N14: '¿El alcance se mantiene como información documentada y está disponible para las partes interesadas?',
         N45: '¿El alcance está disponible como información documentada?'},
    27: {N9: '¿La política de la calidad es apropiada al propósito y contexto de la organización y apoya su dirección estratégica?',
         N14: '¿La política ambiental es apropiada al propósito y contexto de la organización, incluida la naturaleza, magnitud e impactos ambientales de sus actividades, productos y servicios?',
         N45: '¿La política de la SST es apropiada al propósito, tamaño y contexto de la organización y a la naturaleza específica de sus riesgos y oportunidades para la SST?'},
    29: {N9: '¿Incluye el compromiso de cumplir los requisitos aplicables?',
         N14: '¿Incluye el compromiso de cumplir con sus obligaciones de cumplimiento?',
         N45: '¿Incluye el compromiso de cumplir los requisitos legales y otros requisitos?'},
    30: {N9: '¿Incluye el compromiso de mejora continua del sistema de gestión de la calidad?',
         N14: '¿Incluye el compromiso de mejora continua del sistema de gestión ambiental para la mejora del desempeño ambiental?',
         N45: '¿Incluye el compromiso de mejora continua del sistema de gestión de la SST?'},
    35: {N9: '¿Se asignan, comunican y entienden dentro de la organización las responsabilidades y autoridades de los roles pertinentes?',
         N14: '¿Se asignan, comunican y entienden dentro de la organización las responsabilidades y autoridades de los roles pertinentes?',
         N45: '¿Se asignan y comunican las responsabilidades y autoridades de los roles pertinentes dentro del sistema de gestión de la SST en todos los niveles, y se mantienen como información documentada?'},
    55: {N14: 'Obligaciones de cumplimiento: ¿se determinan y se tiene acceso a las obligaciones de cumplimiento relacionadas con los aspectos ambientales, y se determina cómo se aplican a la organización?',
         N45: 'Requisitos legales y otros requisitos: ¿se determinan y se tiene acceso a los requisitos legales y otros requisitos actualizados aplicables a los peligros, a los riesgos para la SST y al sistema de gestión, y se determina cómo se aplican y qué debe comunicarse?'},
    57: {N14: 'Planificación de acciones: ¿se planifican acciones para abordar los aspectos ambientales significativos, las obligaciones de cumplimiento y los riesgos y oportunidades, y para prepararse y responder ante situaciones de emergencia?',
         N45: 'Planificación de acciones: ¿se planifican acciones para abordar los riesgos y oportunidades, los requisitos legales y otros requisitos, y para prepararse y responder ante situaciones de emergencia?'},
    58: {N14: '¿Se planifica cómo integrar e implementar esas acciones en los procesos del sistema de gestión ambiental o en otros procesos de negocio y cómo evaluar su eficacia, considerando las opciones tecnológicas y los requisitos financieros, operacionales y de negocio?',
         N45: '¿Se planifica cómo integrar e implementar esas acciones en los procesos del sistema de gestión de la SST o en otros procesos de negocio y cómo evaluar su eficacia, considerando la jerarquía de controles, las mejores prácticas, las opciones tecnológicas y los requisitos financieros, operacionales y de negocio?'},
    61: {N14: '¿Los objetivos ambientales tienen en cuenta los aspectos ambientales significativos, las obligaciones de cumplimiento y los riesgos y oportunidades?',
         N45: '¿Los objetivos de la SST tienen en cuenta los requisitos aplicables, los resultados de la evaluación de riesgos y oportunidades y los resultados de la consulta con los trabajadores y sus representantes?'},
    74: {N9: '¿Se determina la competencia necesaria de las personas que realizan, bajo su control, un trabajo que afecta al desempeño y eficacia del sistema de gestión de la calidad?',
         N14: '¿Se determina la competencia necesaria de las personas que realizan, bajo su control, un trabajo que afecta a su desempeño ambiental y a su capacidad para cumplir sus obligaciones de cumplimiento?',
         N45: '¿Se determina la competencia necesaria de los trabajadores que afecta o puede afectar al desempeño de la SST?'},
    75: {N9: '¿Se asegura que estas personas sean competentes con base en la educación, formación o experiencia apropiadas?',
         N14: '¿Se asegura que estas personas sean competentes con base en la educación, formación o experiencia apropiadas?',
         N45: '¿Se asegura que los trabajadores sean competentes, incluida la capacidad de identificar los peligros, con base en la educación, formación o experiencia apropiadas?'},
    88: {N9: '¿El sistema de gestión de la calidad incluye la información documentada requerida por la norma y la que la organización determina necesaria para su eficacia?',
         N14: '¿El sistema de gestión ambiental incluye la información documentada requerida por la norma y la que la organización determina necesaria para su eficacia?',
         N45: '¿El sistema de gestión de la SST incluye la información documentada requerida por la norma y la que la organización determina necesaria para su eficacia?'},
    112: {N14: '¿Se han establecido, implementado y mantenido procesos para prepararse y responder ante situaciones de emergencia potenciales identificadas en la planificación?',
          N45: '¿Se han establecido, implementado y mantenido procesos para prepararse y responder ante situaciones de emergencia potenciales identificadas, incluida la prestación de primeros auxilios?'},
    113: {N14: '¿Se planifican acciones para prevenir o mitigar los impactos ambientales adversos de las situaciones de emergencia, apropiadas a su magnitud e impacto potencial?',
          N45: '¿Se planifica una respuesta a las situaciones de emergencia, apropiada a su magnitud y a sus consecuencias potenciales?'},
    115: {N14: '¿Se proporciona información y formación pertinentes sobre la preparación y respuesta ante emergencias a las partes interesadas pertinentes, incluidas las personas que trabajan bajo el control de la organización?',
          N45: '¿Se proporciona formación a todos los trabajadores para la preparación y respuesta ante emergencias, y se comunica la información pertinente a contratistas, visitantes, servicios de respuesta ante emergencias, autoridades y la comunidad local, según corresponda?'},
    140: {N14: '¿Se han determinado los criterios con los que se evalúa el desempeño ambiental y los indicadores apropiados?',
          N45: '¿Se han determinado los criterios para evaluar el desempeño de la SST, y el seguimiento incluye el cumplimiento de los requisitos legales y otros requisitos, las actividades relacionadas con los peligros y riesgos, el progreso hacia los objetivos y la eficacia de los controles operacionales y de otro tipo?'},
    149: {N9: '¿Se informan los resultados de las auditorías a la dirección pertinente, se realizan las correcciones y acciones correctivas oportunamente y se conserva información documentada de la implementación del programa y de los resultados?',
          N14: '¿Se informan los resultados de las auditorías a la dirección pertinente, se toman las acciones necesarias y se conserva información documentada de la implementación del programa y de los resultados?',
          N45: '¿Se informan los resultados de las auditorías a la dirección pertinente, a los trabajadores y, cuando existan, a sus representantes y a otras partes interesadas pertinentes, se toman las acciones necesarias y se conserva información documentada de la implementación del programa y de los resultados?'},
    153: {N14: '¿Las entradas incluyen los aspectos ambientales significativos, las obligaciones de cumplimiento, la información sobre el desempeño ambiental (no conformidades y acciones correctivas, resultados de seguimiento y medición, cumplimiento de las obligaciones de cumplimiento, auditorías), las comunicaciones pertinentes de las partes interesadas (incluidas las quejas), la adecuación de los recursos y las oportunidades de mejora continua?',
          N45: '¿Las entradas incluyen la información sobre el desempeño de la SST (incidentes, no conformidades, acciones correctivas, resultados de seguimiento y medición, evaluación del cumplimiento, auditorías, consulta y participación de los trabajadores, riesgos y oportunidades), la adecuación de los recursos, las comunicaciones pertinentes con las partes interesadas y las oportunidades de mejora continua?'},
    154: {N9: '¿Las salidas incluyen las decisiones relacionadas con las oportunidades de mejora, cualquier necesidad de cambio en el sistema de gestión de la calidad y las necesidades de recursos?',
          N14: '¿Las salidas incluyen las conclusiones sobre la conveniencia, adecuación y eficacia del sistema, las decisiones sobre oportunidades de mejora continua, las necesidades de cambio y de recursos, las acciones cuando no se logran los objetivos ambientales, las oportunidades de mejorar la integración con otros procesos de negocio y las implicaciones para la dirección estratégica?',
          N45: '¿Las salidas incluyen las conclusiones sobre la conveniencia, adecuación y eficacia del sistema, las oportunidades de mejora continua, las necesidades de cambio y de recursos, las acciones necesarias, las oportunidades de mejorar la integración con otros procesos de negocio y las implicaciones para la dirección estratégica?'},
    155: {N9: '¿Se conserva información documentada como evidencia de los resultados de las revisiones por la dirección?',
          N14: '¿Se conserva información documentada como evidencia de los resultados de las revisiones por la dirección?',
          N45: '¿Se comunican los resultados pertinentes de la revisión por la dirección a los trabajadores y, cuando existan, a sus representantes, y se conserva información documentada como evidencia de los resultados?'},
    156: {N14: '¿Se determinan las oportunidades de mejora y se implementan las acciones necesarias para lograr los resultados previstos del sistema de gestión ambiental?',
          N45: '¿Se determinan las oportunidades de mejora y se implementan las acciones necesarias para lograr los resultados previstos del sistema de gestión de la SST?'},
    157: {N9: '¿Cuando ocurre una no conformidad, incluida cualquiera originada por quejas, se reacciona para controlarla y corregirla y se hace frente a las consecuencias?',
          N14: '¿Cuando ocurre una no conformidad, se reacciona para controlarla y corregirla y se hace frente a las consecuencias, incluida la mitigación de los impactos ambientales adversos?',
          N45: '¿Cuando ocurre un incidente o una no conformidad, se reacciona de manera oportuna para controlarlo y corregirlo y se hace frente a las consecuencias?'},
    160: {N9: '¿Se implementan las acciones necesarias y se revisa la eficacia de las acciones correctivas tomadas?',
          N14: '¿Se implementan las acciones necesarias y se revisa la eficacia de las acciones correctivas tomadas?',
          N45: '¿Se implementan las acciones necesarias según la jerarquía de controles y la gestión del cambio, se revisan las evaluaciones de riesgos existentes y se revisa la eficacia de las acciones tomadas?'},
    162: {N9: '¿Se conserva información documentada como evidencia de la naturaleza de las no conformidades, las acciones tomadas y sus resultados?',
          N14: '¿Se conserva información documentada como evidencia de la naturaleza de las no conformidades, las acciones tomadas y sus resultados?',
          N45: '¿Se conserva información documentada como evidencia de la naturaleza de los incidentes o no conformidades, las acciones tomadas, sus resultados y su eficacia, y se comunica a los trabajadores pertinentes y, cuando existan, a sus representantes?'},
    163: {N9: '¿Se mejora continuamente la conveniencia, adecuación y eficacia del sistema de gestión de la calidad?',
          N14: '¿Se mejora continuamente la conveniencia, adecuación y eficacia del sistema de gestión ambiental para mejorar el desempeño ambiental?',
          N45: '¿Se mejora continuamente la conveniencia, adecuación y eficacia del sistema de gestión de la SST para mejorar el desempeño de la SST?'},
}

_PARENTESIS_NORMA = re.compile(r'\s*\((?:en )?ISO[^)]*\)')


def titulo_seccion(codigo, titulo, norma):
    return TITULOS.get(codigo, {}).get(norma) or _PARENTESIS_NORMA.sub('', titulo).split(' · ')[0].strip()


def filas_norma(integrada, norma):
    """`integrada`: [(codigo, titulo, es_seccion)] de la lista integrada en orden.
    Devuelve [(codigo, titulo, es_seccion, formato)] de la lista de `norma`."""
    preguntas, secciones_pend, out, n = [], [], [], 0
    for codigo, titulo, es_seccion in integrada:
        if es_seccion:
            # Un capítulo reinicia los títulos pendientes; una cláusula se
            # acumula detrás de su capítulo hasta que aparezca una pregunta.
            if '.' not in codigo:
                secciones_pend = [(codigo, titulo)]
            else:
                secciones_pend = [s for s in secciones_pend if '.' not in s[0]] + [(codigo, titulo)]
            continue
        primera, pregunta = (titulo.split('\n', 1) + [''])[:2]
        refs = [(CLAVE[m[0]], m[1]) for m in re.findall(r'(ISO \d+): ([\d.]+)', primera)]
        propios = [c for k, c in refs if k == norma]
        if not propios:
            continue
        for sc, st in secciones_pend:
            out.append((sc, titulo_seccion(sc, st, norma), True, []))
        secciones_pend = []
        n += 1
        texto = VARIANTES.get(int(codigo), {}).get(norma, pregunta)
        etiqueta = {N9: 'ISO 9001', N14: 'ISO 14001', N45: 'ISO 45001'}[norma]
        ref = ' · '.join(f'{etiqueta}: {c}' for c in propios)
        ref_html = ' · '.join(f'{etiqueta}: {c}'.replace(' ', '&nbsp;') for c in propios)
        out.append((str(n), f'{ref}\n{texto}', False, [{'t': f'<b>{ref_html}</b>', 'j': 'left'}, {'t': texto}]))
    return out


def cargar(apps, schema_editor):
    RequisitoNorma = apps.get_model('esynapse_sig', 'RequisitoNorma')
    integrada = list(RequisitoNorma.objects.filter(norma='sig_integrado').order_by('orden')
                     .values_list('codigo', 'titulo', 'es_seccion'))
    for norma in (N9, N14, N45):
        RequisitoNorma.objects.filter(norma=norma, bloque='lista').delete()
        RequisitoNorma.objects.bulk_create([
            RequisitoNorma(norma=norma, bloque='lista', codigo=c, titulo=t, es_seccion=s, formato=f, orden=o)
            for o, (c, t, s, f) in enumerate(filas_norma(integrada, norma), start=1)])


def descargar(apps, schema_editor):
    apps.get_model('esynapse_sig', 'RequisitoNorma').objects.filter(bloque='lista').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0059_bloque_lista_por_norma'),
    ]

    operations = [
        migrations.RunPython(cargar, descargar),
    ]
