"""
Lista de verificación integrada ISO 9001:2015, ISO 14001:2015 e ISO 45001:2018
completa: una pregunta por requisito auditable, cada una precedida por la
referencia exacta a los numerales de la(s) norma(s) que la exigen. Se ordena
por la estructura común de alto nivel (capítulos 4 a 10); donde una cláusula
existe solo en una norma, el título lo indica. Las preguntas están redactadas
como preguntas de auditoría (no reproducen el texto de las normas).

Reemplaza el catálogo resumido anterior (83 filas). Las listas ya generadas
conservan sus ítems.
"""
from django.db import migrations

N9, N14, N45 = 'ISO 9001', 'ISO 14001', 'ISO 45001'


def T(c9=None, c14=None, c45=None):
    """Referencias por norma; un argumento vacío = la norma no lo exige."""
    return [(n, c) for n, c in ((N9, c9), (N14, c14), (N45, c45)) if c]


def TODAS(c):
    return T(c, c, c)


# ('S', código, título) = capítulo o cláusula (fila de título)
# ('P', referencias, pregunta) = requisito a evaluar
LISTA = [
    ('S', '4', 'CONTEXTO DE LA ORGANIZACIÓN'),
    ('S', '4.1', 'Comprensión de la organización y de su contexto'),
    ('P', TODAS('4.1'), '¿Se han determinado las cuestiones externas e internas pertinentes para el propósito de la organización y que afectan su capacidad para lograr los resultados previstos del sistema de gestión?'),
    ('P', T('4.1'), '¿Se realiza el seguimiento y la revisión de la información sobre estas cuestiones externas e internas?'),
    ('P', T(c14='4.1'), '¿Entre las cuestiones se incluyen las condiciones ambientales capaces de afectar a la organización o de verse afectadas por ella?'),

    ('S', '4.2', 'Comprensión de las necesidades y expectativas de las partes interesadas (en ISO 45001: de los trabajadores y de otras partes interesadas)'),
    ('P', TODAS('4.2'), '¿Se han determinado las partes interesadas pertinentes al sistema de gestión (en SST, además de los trabajadores) y sus necesidades y expectativas pertinentes?'),
    ('P', T(c14='4.2', c45='4.2'), '¿Se ha determinado cuáles de esas necesidades y expectativas son, o podrían convertirse, en requisitos legales y otros requisitos (obligaciones de cumplimiento)?'),
    ('P', T('4.2'), '¿Se realiza el seguimiento y la revisión de la información sobre las partes interesadas y sus requisitos pertinentes?'),

    ('S', '4.3', 'Determinación del alcance del sistema de gestión'),
    ('P', TODAS('4.3'), '¿Se han determinado los límites y la aplicabilidad del sistema de gestión considerando las cuestiones externas e internas, los requisitos de las partes interesadas y, en calidad, los productos y servicios?'),
    ('P', T(c14='4.3', c45='4.3'), '¿El alcance considera las unidades, funciones y límites físicos, las actividades, productos y servicios (en SST, las actividades relacionadas con el trabajo planificadas o realizadas) y la autoridad y capacidad de la organización para ejercer control e influencia?'),
    ('P', T('4.3'), '¿Se justifica todo requisito de la norma determinado como no aplicable y se asegura que no afecta la capacidad de la organización para asegurar la conformidad de sus productos y servicios ni el aumento de la satisfacción del cliente?'),
    ('P', TODAS('4.3'), '¿El alcance está disponible y se mantiene como información documentada (en ambiental, disponible para las partes interesadas)?'),

    ('S', '4.4', 'Sistema de gestión y sus procesos'),
    ('P', T('4.4.1', '4.4', '4.4'), '¿Se ha establecido, implementado, mantenido y mejorado continuamente el sistema de gestión, incluidos los procesos necesarios y sus interacciones?'),
    ('P', T('4.4.1'), '¿Se han determinado para cada proceso: entradas y salidas, secuencia e interacción, criterios y métodos de control (incluido el seguimiento, la medición y los indicadores), recursos, responsabilidades y autoridades, riesgos y oportunidades, y cómo se evalúan y mejoran?'),
    ('P', T('4.4.2'), '¿Se mantiene información documentada para apoyar la operación de los procesos y se conserva la necesaria para tener confianza en que se realizan según lo planificado?'),
    ('P', T(c14='4.4'), '¿Se considera el conocimiento obtenido del contexto y de las partes interesadas al establecer y mantener el sistema de gestión ambiental?'),

    ('S', '5', 'LIDERAZGO (en ISO 45001: LIDERAZGO Y PARTICIPACIÓN DE LOS TRABAJADORES)'),
    ('S', '5.1', 'Liderazgo y compromiso'),
    ('P', T('5.1.1', '5.1', '5.1'), '¿La alta dirección asume la rendición de cuentas de la eficacia del sistema de gestión y asegura que la política y los objetivos se establecen y son compatibles con el contexto y la dirección estratégica de la organización?'),
    ('P', T(c45='5.1'), '¿La alta dirección asume la responsabilidad total y la rendición de cuentas de la prevención de lesiones y deterioro de la salud relacionados con el trabajo, y de la provisión de lugares y actividades de trabajo seguros y saludables?'),
    ('P', T('5.1.1', '5.1', '5.1'), '¿Asegura la integración de los requisitos del sistema de gestión en los procesos de negocio de la organización?'),
    ('P', T('5.1.1'), '¿Promueve el uso del enfoque a procesos y el pensamiento basado en riesgos?'),
    ('P', T('5.1.1', '5.1', '5.1'), '¿Asegura que los recursos necesarios para el sistema de gestión estén disponibles?'),
    ('P', T('5.1.1', '5.1', '5.1'), '¿Comunica la importancia de una gestión eficaz y de cumplir los requisitos del sistema de gestión?'),
    ('P', T('5.1.1', '5.1', '5.1'), '¿Asegura que el sistema logra los resultados previstos, dirige y apoya a las personas para que contribuyan a su eficacia, promueve la mejora continua y apoya a otros roles de dirección en sus áreas de responsabilidad?'),
    ('P', T(c45='5.1'), '¿Desarrolla, lidera y promueve una cultura que apoye los resultados del sistema de gestión de SST?'),
    ('P', T(c45='5.1'), '¿Protege a los trabajadores de represalias al informar incidentes, peligros, riesgos y oportunidades?'),
    ('P', T(c45='5.1'), '¿Asegura que se establecen e implementan procesos para la consulta y participación de los trabajadores, y apoya el funcionamiento del comité de seguridad y salud en el trabajo?'),
    ('P', T('5.1.2'), 'Enfoque al cliente: ¿se determinan, comprenden y cumplen regularmente los requisitos del cliente y los legales y reglamentarios aplicables?'),
    ('P', T('5.1.2'), 'Enfoque al cliente: ¿se determinan y consideran los riesgos y oportunidades que pueden afectar la conformidad de los productos y servicios y la capacidad de aumentar la satisfacción del cliente, y se mantiene el enfoque en aumentarla?'),

    ('S', '5.2', 'Política (de la calidad / ambiental / de SST)'),
    ('P', T('5.2.1', '5.2', '5.2'), '¿La política es apropiada al propósito y contexto de la organización (incluida la naturaleza, magnitud e impactos ambientales de sus actividades, y la naturaleza de sus riesgos y oportunidades para la SST) y apoya su dirección estratégica?'),
    ('P', T('5.2.1', '5.2', '5.2'), '¿Proporciona un marco de referencia para el establecimiento de los objetivos?'),
    ('P', T('5.2.1', '5.2', '5.2'), '¿Incluye el compromiso de cumplir los requisitos aplicables (en ambiental y SST, los requisitos legales y otros requisitos)?'),
    ('P', T('5.2.1', '5.2', '5.2'), '¿Incluye el compromiso de mejora continua del sistema de gestión (en ambiental, para mejorar el desempeño ambiental)?'),
    ('P', T(c14='5.2'), '¿Incluye el compromiso de proteger el medio ambiente, incluida la prevención de la contaminación, y otros compromisos pertinentes al contexto de la organización?'),
    ('P', T(c45='5.2'), '¿Incluye el compromiso de proporcionar condiciones de trabajo seguras y saludables para la prevención de lesiones y deterioro de la salud, y de eliminar los peligros y reducir los riesgos para la SST?'),
    ('P', T(c45='5.2'), '¿Incluye el compromiso de consulta y participación de los trabajadores y, cuando existan, de sus representantes?'),
    ('P', T('5.2.2', '5.2', '5.2'), '¿La política está disponible como información documentada, se comunica, se entiende y se aplica dentro de la organización, y está disponible para las partes interesadas pertinentes?'),

    ('S', '5.3', 'Roles, responsabilidades y autoridades en la organización'),
    ('P', TODAS('5.3'), '¿Se asignan, comunican y entienden dentro de la organización las responsabilidades y autoridades de los roles pertinentes (en SST, en todos los niveles, mantenidas como información documentada)?'),
    ('P', TODAS('5.3'), '¿Se ha asignado la responsabilidad y autoridad para asegurar que el sistema de gestión es conforme con los requisitos de la norma y para informar a la alta dirección sobre su desempeño?'),
    ('P', T('5.3'), '¿Se ha asignado la responsabilidad y autoridad para asegurar que los procesos generan las salidas previstas, se promueve el enfoque al cliente y se mantiene la integridad del sistema cuando se planifican e implementan cambios?'),
    ('P', T(c45='5.3'), '¿Los trabajadores de cada nivel asumen la responsabilidad de los aspectos del sistema de gestión de SST sobre los que tienen control?'),

    ('S', '5.4', 'Consulta y participación de los trabajadores (ISO 45001)'),
    ('P', T(c45='5.4'), '¿Se han establecido, implementado y mantenido procesos para la consulta y la participación de los trabajadores de todos los niveles y funciones aplicables, y de sus representantes, en el desarrollo, planificación, implementación, evaluación del desempeño y mejora del sistema de gestión de SST?'),
    ('P', T(c45='5.4'), '¿Se proporcionan los mecanismos, el tiempo, la formación y los recursos necesarios, y acceso oportuno a información clara, comprensible y pertinente sobre el sistema de gestión de SST?'),
    ('P', T(c45='5.4'), '¿Se determinan y eliminan los obstáculos o barreras para la participación y se minimizan los que no puedan eliminarse?'),
    ('P', T(c45='5.4'), '¿Se consulta a los trabajadores no directivos sobre: las necesidades de las partes interesadas, la política, los roles y responsabilidades, cómo cumplir los requisitos legales, los objetivos, los controles para contratación externa, compras y contratistas, qué requiere seguimiento y medición, el programa de auditoría y la mejora continua?'),
    ('P', T(c45='5.4'), '¿Se asegura la participación de los trabajadores no directivos en: la identificación de peligros y evaluación de riesgos y oportunidades, las acciones para eliminar peligros y reducir riesgos, las necesidades de competencia y formación, la comunicación, las medidas de control, y la investigación de incidentes y no conformidades con sus acciones correctivas?'),

    ('S', '6', 'PLANIFICACIÓN'),
    ('S', '6.1', 'Acciones para abordar riesgos y oportunidades'),
    ('P', T('6.1.1', '6.1.1', '6.1.1'), '¿Al planificar el sistema de gestión se consideran las cuestiones del contexto, los requisitos de las partes interesadas y el alcance, y se determinan los riesgos y oportunidades que es necesario abordar para asegurar los resultados previstos, prevenir o reducir efectos no deseados y lograr la mejora?'),
    ('P', T(c14='6.1.1'), '¿Se han determinado, dentro del alcance, las situaciones de emergencia potenciales, incluidas las que pueden tener un impacto ambiental?'),
    ('P', T(c14='6.1.1', c45='6.1.1'), '¿Se mantiene información documentada sobre los riesgos y oportunidades y sobre los procesos necesarios para abordarlos?'),
    ('P', T('6.1.2'), '¿Se planifican acciones para abordar los riesgos y oportunidades, proporcionales al impacto potencial en la conformidad de los productos y servicios, se integran en los procesos y se evalúa su eficacia?'),
    ('P', T(c14='6.1.2'), 'Aspectos ambientales: ¿se han determinado los aspectos ambientales de las actividades, productos y servicios que la organización puede controlar y de aquellos en los que puede influir, y sus impactos ambientales asociados, desde una perspectiva de ciclo de vida?'),
    ('P', T(c14='6.1.2'), '¿Al determinar los aspectos ambientales se tienen en cuenta los cambios (incluidos nuevos desarrollos o modificaciones), las condiciones anormales y las situaciones de emergencia razonablemente previsibles?'),
    ('P', T(c14='6.1.2'), '¿Se determinan los aspectos ambientales significativos mediante criterios establecidos, se comunican entre los diferentes niveles y funciones, y se mantiene información documentada de los aspectos, los criterios y los aspectos significativos?'),
    ('P', T(c45='6.1.2.1'), 'Identificación de peligros: ¿existe un proceso continuo y proactivo que tiene en cuenta la organización del trabajo y los factores sociales (carga de trabajo, horas de trabajo, acoso), las actividades y situaciones rutinarias y no rutinarias, la infraestructura, los equipos, los materiales y las condiciones del lugar de trabajo?'),
    ('P', T(c45='6.1.2.1'), '¿La identificación de peligros considera incidentes pasados, situaciones de emergencia potenciales, las personas (trabajadores, contratistas, visitantes y otros), cambios reales o propuestos, y cambios en el conocimiento sobre los peligros?'),
    ('P', T(c45='6.1.2.2'), 'Evaluación de riesgos: ¿se evalúan los riesgos para la SST a partir de los peligros identificados, considerando la eficacia de los controles existentes, y los otros riesgos relacionados con el sistema de gestión, con metodologías y criterios definidos, proactivos y sistemáticos, mantenidos como información documentada?'),
    ('P', T(c45='6.1.2.3'), 'Evaluación de oportunidades: ¿se evalúan las oportunidades para mejorar el desempeño de la SST (adaptar el trabajo a los trabajadores, eliminar peligros y reducir riesgos) y otras oportunidades para mejorar el sistema de gestión?'),
    ('P', T(c14='6.1.3', c45='6.1.3'), 'Requisitos legales y otros requisitos: ¿se determinan y se tiene acceso a los requisitos legales y otros requisitos actualizados aplicables a los aspectos ambientales, a los peligros y riesgos y al sistema de gestión, y se determina cómo se aplican y qué debe comunicarse?'),
    ('P', T(c14='6.1.3', c45='6.1.3'), '¿Estos requisitos se tienen en cuenta al establecer, implementar, mantener y mejorar el sistema de gestión, y se mantiene y actualiza como información documentada?'),
    ('P', T(c14='6.1.4', c45='6.1.4'), 'Planificación de acciones: ¿se planifican acciones para abordar los aspectos ambientales significativos, los riesgos y oportunidades, los requisitos legales y otros requisitos, y la preparación y respuesta ante emergencias?'),
    ('P', T(c14='6.1.4', c45='6.1.4'), '¿Se planifica cómo integrar e implementar esas acciones en los procesos del sistema o en otros procesos de negocio y cómo evaluar su eficacia, considerando la jerarquía de controles (en SST), las opciones tecnológicas y los requisitos financieros, operacionales y de negocio?'),

    ('S', '6.2', 'Objetivos y planificación para lograrlos'),
    ('P', T('6.2.1', '6.2.1', '6.2.1'), '¿Se han establecido objetivos para las funciones y niveles pertinentes, coherentes con la política, medibles (o evaluables), que tienen en cuenta los requisitos aplicables, sujetos a seguimiento, comunicados y actualizados según corresponda?'),
    ('P', T('6.2.1'), '¿Los objetivos de la calidad son pertinentes para la conformidad de los productos y servicios y para el aumento de la satisfacción del cliente?'),
    ('P', T(c14='6.2.1', c45='6.2.1'), '¿Los objetivos tienen en cuenta los aspectos ambientales significativos, los requisitos legales y otros requisitos, los riesgos y oportunidades y, en SST, los resultados de la consulta con los trabajadores?'),
    ('P', TODAS('6.2.2'), '¿Al planificar cómo lograr los objetivos se determina qué se va a hacer, qué recursos se requerirán, quién será responsable, cuándo se finalizará y cómo se evaluarán los resultados (incluidos los indicadores de seguimiento)?'),
    ('P', T(c14='6.2.2', c45='6.2.2'), '¿Las acciones para lograr los objetivos se integran en los procesos de negocio de la organización?'),
    ('P', T('6.2.1', '6.2.1', '6.2.2'), '¿Se mantiene y conserva información documentada sobre los objetivos y los planes para lograrlos?'),

    ('S', '6.3', 'Planificación de los cambios (ISO 9001)'),
    ('P', T('6.3'), '¿Los cambios en el sistema de gestión de la calidad se llevan a cabo de manera planificada, considerando su propósito y consecuencias potenciales, la integridad del sistema, la disponibilidad de recursos y la asignación o reasignación de responsabilidades y autoridades?'),

    ('S', '7', 'APOYO'),
    ('S', '7.1', 'Recursos'),
    ('P', T('7.1.1', '7.1', '7.1'), '¿Se determinan y proporcionan los recursos necesarios para establecer, implementar, mantener y mejorar continuamente el sistema de gestión, considerando las capacidades y limitaciones de los recursos internos y lo que se necesita obtener de proveedores externos?'),
    ('P', T('7.1.2'), 'Personas: ¿se determinan y proporcionan las personas necesarias para la implementación eficaz del sistema y para la operación y control de sus procesos?'),
    ('P', T('7.1.3'), 'Infraestructura: ¿se determina, proporciona y mantiene la infraestructura necesaria (edificios y servicios asociados, equipos incluidos hardware y software, transporte, tecnologías de la información y la comunicación)?'),
    ('P', T('7.1.4'), 'Ambiente para la operación de los procesos: ¿se determina, proporciona y mantiene el ambiente necesario, considerando factores sociales, psicológicos y físicos?'),
    ('P', T('7.1.5.1'), 'Recursos de seguimiento y medición: ¿son idóneos para el tipo de actividad de seguimiento y medición, se mantienen para asegurar su idoneidad continua y se conserva información documentada como evidencia?'),
    ('P', T('7.1.5.2'), 'Trazabilidad de las mediciones: ¿el equipo de medición se calibra o verifica a intervalos especificados, o antes de su uso, contra patrones trazables a patrones de medición internacionales o nacionales (o se registra la base usada), se identifica para determinar su estado y se protege contra ajustes, daño o deterioro?'),
    ('P', T('7.1.5.2'), '¿Cuando un equipo de medición resulta no apto, se determina si la validez de los resultados previos se ha visto afectada y se toman las acciones necesarias?'),
    ('P', T('7.1.6'), 'Conocimientos de la organización: ¿se determinan, mantienen y ponen a disposición los conocimientos necesarios para la operación de los procesos y la conformidad de los productos y servicios, y se considera cómo adquirir los adicionales ante necesidades y tendencias cambiantes?'),

    ('S', '7.2', 'Competencia'),
    ('P', TODAS('7.2'), '¿Se determina la competencia necesaria de las personas que realizan trabajos que afectan al desempeño y eficacia del sistema (en ambiental, que afectan al desempeño ambiental y a las obligaciones de cumplimiento; en SST, que afectan o pueden afectar al desempeño de la SST)?'),
    ('P', TODAS('7.2'), '¿Se asegura que estas personas sean competentes con base en la educación, formación o experiencia apropiadas (en SST, incluida la capacidad de identificar peligros)?'),
    ('P', T(c14='7.2'), '¿Se determinan las necesidades de formación asociadas con los aspectos ambientales y con el sistema de gestión ambiental?'),
    ('P', TODAS('7.2'), '¿Cuando es aplicable, se toman acciones para adquirir y mantener la competencia necesaria y se evalúa su eficacia?'),
    ('P', TODAS('7.2'), '¿Se conserva información documentada apropiada como evidencia de la competencia?'),

    ('S', '7.3', 'Toma de conciencia'),
    ('P', TODAS('7.3'), '¿Las personas que realizan el trabajo bajo el control de la organización toman conciencia de la política, de los objetivos pertinentes, de su contribución a la eficacia del sistema de gestión (incluidos los beneficios de una mejora del desempeño) y de las implicaciones de no cumplir sus requisitos?'),
    ('P', T(c14='7.3'), '¿Toman conciencia de los aspectos ambientales significativos y de los impactos ambientales reales o potenciales relacionados con su trabajo, y de las implicaciones de no cumplir las obligaciones de cumplimiento?'),
    ('P', T(c45='7.3'), '¿Los trabajadores toman conciencia de los incidentes y de los resultados de las investigaciones pertinentes para ellos, y de los peligros, riesgos para la SST y acciones determinadas que les conciernen?'),
    ('P', T(c45='7.3'), '¿Los trabajadores toman conciencia de su capacidad de alejarse de situaciones de trabajo que consideren que presentan un peligro inminente y serio para su vida o su salud, y de las disposiciones para protegerlos de consecuencias indebidas por hacerlo?'),

    ('S', '7.4', 'Comunicación'),
    ('P', T('7.4', '7.4.1', '7.4.1'), '¿Se han determinado las comunicaciones internas y externas pertinentes al sistema de gestión: qué comunicar, cuándo, a quién, cómo y quién comunica?'),
    ('P', T(c14='7.4.1', c45='7.4.1'), '¿Al establecer los procesos de comunicación se tienen en cuenta los requisitos legales y otros requisitos, los aspectos de diversidad (género, idioma, cultura, alfabetización, discapacidad) y las opiniones de las partes interesadas externas, y se asegura que la información comunicada es coherente y fiable?'),
    ('P', T(c14='7.4.1', c45='7.4.1'), '¿Se responde a las comunicaciones pertinentes sobre el sistema de gestión y se conserva información documentada como evidencia de las comunicaciones?'),
    ('P', T(c14='7.4.2', c45='7.4.2'), 'Comunicación interna: ¿se comunica la información pertinente del sistema entre los diversos niveles y funciones, incluidos sus cambios, y los procesos permiten que las personas contribuyan a la mejora continua?'),
    ('P', T(c14='7.4.3', c45='7.4.3'), 'Comunicación externa: ¿se comunica externamente la información pertinente al sistema de gestión según los procesos de comunicación establecidos y los requisitos legales y otros requisitos?'),

    ('S', '7.5', 'Información documentada'),
    ('P', TODAS('7.5.1'), '¿El sistema de gestión incluye la información documentada requerida por la norma (en SST y ambiental, también la necesaria para las obligaciones de cumplimiento) y la que la organización determina necesaria para su eficacia?'),
    ('P', TODAS('7.5.2'), 'Creación y actualización: ¿se asegura la identificación y descripción apropiadas (título, fecha, autor o número de referencia), el formato y medios de soporte, y la revisión y aprobación con respecto a la conveniencia y adecuación?'),
    ('P', T('7.5.3.1', '7.5.3', '7.5.3'), 'Control: ¿la información documentada está disponible e idónea para su uso donde y cuando se necesita, y está protegida adecuadamente (pérdida de confidencialidad, uso inadecuado o pérdida de integridad)?'),
    ('P', T('7.5.3.2', '7.5.3', '7.5.3'), '¿Se abordan la distribución, acceso, recuperación y uso; el almacenamiento y preservación (incluida la legibilidad); el control de cambios (por ejemplo, control de versiones); y la conservación y disposición?'),
    ('P', T('7.5.3.2', '7.5.3', '7.5.3'), '¿La información documentada de origen externo necesaria para el sistema se identifica y controla, y la información conservada como evidencia de la conformidad se protege contra modificaciones no intencionadas?'),

    ('S', '8', 'OPERACIÓN'),
    ('S', '8.1', 'Planificación y control operacional'),
    ('P', T('8.1', '8.1', '8.1.1'), '¿Se planifican, implementan, controlan y mantienen los procesos necesarios para cumplir los requisitos del sistema de gestión y para implementar las acciones determinadas en la planificación, estableciendo criterios de operación e implementando el control de los procesos de acuerdo con ellos?'),
    ('P', T('8.1'), '¿Se determinan los requisitos de los productos y servicios, los criterios de aceptación y los recursos necesarios para lograr su conformidad?'),
    ('P', T('8.1', '8.1', '8.1.1'), '¿Se mantiene y conserva la información documentada necesaria para tener confianza en que los procesos se han llevado a cabo según lo planificado?'),
    ('P', T('8.1', '8.1', '8.1.3'), '¿Se controlan los cambios planificados y se revisan las consecuencias de los cambios no previstos, tomando acciones para mitigar cualquier efecto adverso?'),
    ('P', T('8.1', '8.1', '8.1.4.3'), '¿Los procesos contratados externamente están controlados o se tiene influencia sobre ellos, y el tipo y grado de control está definido en el sistema de gestión y es coherente con los requisitos legales y otros requisitos?'),
    ('P', T(c14='8.1'), 'Perspectiva de ciclo de vida: ¿se establecen controles para que los requisitos ambientales se aborden en el proceso de diseño y desarrollo de los productos y servicios, considerando cada etapa de su ciclo de vida?'),
    ('P', T(c14='8.1'), '¿Se determinan los requisitos ambientales para la compra de productos y servicios y se comunican a los proveedores externos, incluidos los contratistas?'),
    ('P', T(c14='8.1'), '¿Se considera la necesidad de suministrar información acerca de los impactos ambientales significativos potenciales asociados con el transporte, la entrega, el uso, el tratamiento al fin de la vida y la disposición final de los productos y servicios?'),
    ('P', T(c45='8.1.1'), '¿Se adapta el trabajo a los trabajadores y, en lugares de trabajo con múltiples empleadores, se coordinan las partes pertinentes del sistema de gestión de SST con las otras organizaciones?'),
    ('P', T(c45='8.1.2'), 'Eliminar peligros y reducir riesgos: ¿se aplica la jerarquía de controles: eliminar el peligro, sustituir por procesos, operaciones, materiales o equipos menos peligrosos, controles de ingeniería y reorganización del trabajo, controles administrativos (incluida la formación) y equipos de protección personal adecuados?'),
    ('P', T(c45='8.1.3'), 'Gestión del cambio: ¿se implementan y controlan los cambios temporales y permanentes que impactan en el desempeño de la SST (nuevos productos, servicios y procesos, cambios en los lugares de trabajo, la organización del trabajo, las condiciones, los equipos, la fuerza de trabajo, los requisitos legales o el conocimiento sobre peligros y riesgos), revisando sus consecuencias?'),
    ('P', T(c45='8.1.4.1'), 'Compras: ¿se controla la compra de productos y servicios para asegurar su conformidad con el sistema de gestión de SST?'),
    ('P', T(c45='8.1.4.2'), 'Contratistas: ¿se coordinan los procesos de compras con los contratistas para identificar peligros y evaluar y controlar los riesgos derivados de sus actividades y operaciones, de las de la organización que les afectan y de las que afectan a otras partes interesadas?'),
    ('P', T(c45='8.1.4.2'), '¿Se asegura que los contratistas y sus trabajadores cumplen los requisitos del sistema de gestión de SST y se aplican criterios de SST para su selección?'),

    ('S', '8.2', 'Requisitos para los productos y servicios (ISO 9001) · Preparación y respuesta ante emergencias (ISO 14001, ISO 45001)'),
    ('P', T('8.2.1'), 'Comunicación con el cliente: ¿incluye la información relativa a los productos y servicios, la atención de consultas, contratos o pedidos y sus cambios, la retroalimentación de los clientes (incluidas las quejas), la manipulación o control de la propiedad del cliente y los requisitos para acciones de contingencia?'),
    ('P', T('8.2.2'), '¿Al determinar los requisitos de los productos y servicios que se ofrecen se definen los requisitos legales y reglamentarios aplicables y los que la organización considera necesarios, y la organización puede cumplir con lo que ofrece?'),
    ('P', T('8.2.3.1'), '¿Antes de comprometerse a suministrar se revisan los requisitos especificados por el cliente (incluidos los de entrega y posteriores a la entrega), los no establecidos pero necesarios para el uso previsto, los especificados por la organización y los legales y reglamentarios, y se resuelven las diferencias con lo expresado previamente?'),
    ('P', T('8.2.3.2'), '¿Se conserva información documentada de los resultados de la revisión y de cualquier requisito nuevo para los productos y servicios?'),
    ('P', T('8.2.4'), '¿Cuando cambian los requisitos para los productos y servicios, se modifica la información documentada pertinente y se informa a las personas pertinentes?'),
    ('P', T(c14='8.2', c45='8.2'), '¿Se han establecido, implementado y mantenido procesos para prepararse y responder ante situaciones de emergencia potenciales identificadas (en SST, incluida la prestación de primeros auxilios)?'),
    ('P', T(c14='8.2', c45='8.2'), '¿Se planifican acciones para prevenir o mitigar los impactos ambientales adversos y las consecuencias de las situaciones de emergencia, proporcionales a su magnitud e impacto potencial?'),
    ('P', T(c14='8.2', c45='8.2'), '¿Se ponen a prueba periódicamente las acciones de respuesta planificadas (simulacros), cuando sea factible, y se evalúan y revisan los procesos, en particular después de que ocurran situaciones de emergencia o pruebas?'),
    ('P', T(c14='8.2', c45='8.2'), '¿Se proporciona información y formación pertinentes sobre la preparación y respuesta ante emergencias a las partes interesadas (trabajadores, contratistas, visitantes, servicios de respuesta, autoridades y comunidad local, según corresponda)?'),
    ('P', T(c14='8.2', c45='8.2'), '¿Se mantiene información documentada sobre los procesos y los planes de respuesta ante situaciones de emergencia potenciales?'),

    ('S', '8.3', 'Diseño y desarrollo de los productos y servicios (ISO 9001)'),
    ('P', T('8.3.1'), '¿Se ha establecido, implementado y mantenido un proceso de diseño y desarrollo adecuado? (Si no aplica, ¿la exclusión está justificada en el alcance?)'),
    ('P', T('8.3.2'), 'Planificación: ¿se determinan las etapas y controles, incluidas las revisiones, verificaciones y validaciones, las responsabilidades y autoridades, los recursos internos y externos, las interfaces entre las personas involucradas y la participación de clientes y usuarios?'),
    ('P', T('8.3.3'), 'Entradas: ¿se determinan los requisitos funcionales y de desempeño, la información de diseños previos similares, los requisitos legales y reglamentarios, las normas o códigos de prácticas comprometidos y las consecuencias potenciales de fallar, y se resuelven las entradas contradictorias?'),
    ('P', T('8.3.4'), 'Controles: ¿se definen los resultados a lograr, se realizan revisiones, verificaciones y validaciones, se toman acciones sobre los problemas determinados y se conserva información documentada de estas actividades?'),
    ('P', T('8.3.5'), 'Salidas: ¿cumplen los requisitos de las entradas, son adecuadas para los procesos posteriores, incluyen o hacen referencia a los requisitos de seguimiento y medición y a los criterios de aceptación, y especifican las características esenciales para su uso seguro y correcto?'),
    ('P', T('8.3.6'), 'Cambios: ¿se identifican, revisan y controlan los cambios del diseño y desarrollo, conservando información documentada de los cambios, las revisiones, las autorizaciones y las acciones para prevenir impactos adversos?'),

    ('S', '8.4', 'Control de los procesos, productos y servicios suministrados externamente (ISO 9001)'),
    ('P', T('8.4.1'), '¿Se determinan los controles a aplicar a los procesos, productos y servicios suministrados externamente (lo que se incorpora a los propios, lo suministrado directamente al cliente y los procesos contratados externamente)?'),
    ('P', T('8.4.1'), '¿Se determinan y aplican criterios para la evaluación, la selección, el seguimiento del desempeño y la reevaluación de los proveedores externos, y se conserva información documentada de estas actividades y de las acciones que surjan?'),
    ('P', T('8.4.2'), '¿El tipo y alcance del control asegura que los procesos suministrados externamente permanecen bajo el control del sistema de gestión y no afectan la capacidad de entregar productos y servicios conformes, incluyendo la verificación necesaria?'),
    ('P', T('8.4.3'), 'Información para los proveedores externos: ¿se les comunican los requisitos de los procesos, productos y servicios, la aprobación y liberación, la competencia y calificación de las personas, sus interacciones con la organización, el control y seguimiento de su desempeño y las verificaciones o validaciones a realizar en sus instalaciones?'),

    ('S', '8.5', 'Producción y provisión del servicio (ISO 9001)'),
    ('P', T('8.5.1'), 'Control: ¿la prestación del servicio se realiza bajo condiciones controladas: información documentada de las características y resultados a alcanzar, recursos de seguimiento y medición adecuados, actividades de seguimiento y medición en las etapas apropiadas, e infraestructura y entorno adecuados?'),
    ('P', T('8.5.1'), '¿Se designan personas competentes, se validan y revalidan periódicamente los procesos cuyos resultados no pueden verificarse posteriormente, se implementan acciones para prevenir el error humano y se realizan las actividades de liberación, entrega y posteriores a la entrega?'),
    ('P', T('8.5.2'), 'Identificación y trazabilidad: ¿se identifican las salidas y su estado con respecto a los requisitos de seguimiento y medición, y se controla la identificación única y se conserva la información documentada necesaria cuando la trazabilidad es un requisito?'),
    ('P', T('8.5.3'), 'Propiedad de los clientes o proveedores externos: ¿se identifica, verifica, protege y salvaguarda (incluidos equipos, información y datos personales), y se informa al cliente o proveedor cuando se pierde, deteriora o se considera inadecuada para su uso, conservando información documentada?'),
    ('P', T('8.5.4'), 'Preservación: ¿se preservan las salidas durante la producción y prestación del servicio en la medida necesaria para asegurar la conformidad (identificación, manipulación, control de la contaminación, embalaje, almacenamiento, transporte y protección)?'),
    ('P', T('8.5.5'), 'Actividades posteriores a la entrega: ¿se cumplen los requisitos considerando los requisitos legales y reglamentarios, las consecuencias potenciales no deseadas, la naturaleza, el uso y la vida útil prevista, los requisitos y la retroalimentación del cliente?'),
    ('P', T('8.5.6'), 'Control de los cambios: ¿se revisan y controlan los cambios en la producción o prestación del servicio, y se conserva información documentada que describa los resultados de la revisión, las personas que autorizan el cambio y las acciones necesarias?'),

    ('S', '8.6', 'Liberación de los productos y servicios (ISO 9001)'),
    ('P', T('8.6'), '¿Se verifica en las etapas adecuadas que se cumplen los requisitos antes de liberar los productos y servicios al cliente (o con la aprobación de una autoridad pertinente o del cliente)?'),
    ('P', T('8.6'), '¿Se conserva información documentada con evidencia de la conformidad con los criterios de aceptación y la trazabilidad a las personas que autorizan la liberación?'),

    ('S', '8.7', 'Control de las salidas no conformes (ISO 9001)'),
    ('P', T('8.7.1'), '¿Las salidas no conformes se identifican y controlan para prevenir su uso o entrega no intencionada, y se toman las acciones adecuadas según su naturaleza y efecto (corrección, separación, contención, devolución o suspensión, información al cliente, autorización por concesión)?'),
    ('P', T('8.7.1'), '¿Se verifica la conformidad con los requisitos cuando se corrigen las salidas no conformes, incluidas las detectadas después de la entrega?'),
    ('P', T('8.7.2'), '¿Se conserva información documentada que describe la no conformidad, las acciones tomadas, las concesiones obtenidas y la autoridad que decide la acción?'),

    ('S', '9', 'EVALUACIÓN DEL DESEMPEÑO'),
    ('S', '9.1', 'Seguimiento, medición, análisis y evaluación'),
    ('P', TODAS('9.1.1'), '¿Se ha determinado qué necesita seguimiento y medición, los métodos para asegurar resultados válidos, cuándo se deben llevar a cabo y cuándo se deben analizar y evaluar los resultados?'),
    ('P', T(c14='9.1.1', c45='9.1.1'), '¿Se han determinado los criterios con los que se evalúa el desempeño ambiental y de la SST y los indicadores apropiados? ¿En SST, el seguimiento incluye el cumplimiento de los requisitos legales, las actividades relacionadas con los peligros y riesgos, el progreso hacia los objetivos y la eficacia de los controles operacionales?'),
    ('P', T(c14='9.1.1', c45='9.1.1'), '¿Los equipos de seguimiento y medición se calibran o verifican y se usan y mantienen según corresponda?'),
    ('P', TODAS('9.1.1'), '¿Se evalúa el desempeño y la eficacia del sistema de gestión, se comunica interna y externamente la información pertinente sobre el desempeño, y se conserva información documentada como evidencia de los resultados?'),
    ('P', T('9.1.2'), 'Satisfacción del cliente: ¿se realiza el seguimiento de las percepciones de los clientes del grado en que se cumplen sus necesidades y expectativas, y se han determinado los métodos para obtener, realizar el seguimiento y revisar esta información?'),
    ('P', T('9.1.3'), 'Análisis y evaluación: ¿se analizan y evalúan los datos para evaluar la conformidad de los productos y servicios, la satisfacción del cliente, el desempeño y eficacia del sistema, la eficacia de la planificación, la eficacia de las acciones sobre riesgos y oportunidades, el desempeño de los proveedores externos y la necesidad de mejoras?'),
    ('P', T(c14='9.1.2', c45='9.1.2'), 'Evaluación del cumplimiento: ¿se ha determinado la frecuencia y se evalúa el cumplimiento de los requisitos legales y otros requisitos, se toman acciones si es necesario, se mantiene el conocimiento y la comprensión del estado de cumplimiento, y se conserva información documentada de los resultados?'),

    ('S', '9.2', 'Auditoría interna'),
    ('P', TODAS('9.2.1'), '¿Se llevan a cabo auditorías internas a intervalos planificados para proporcionar información sobre si el sistema de gestión es conforme con los requisitos propios de la organización y con los de la norma, y si se implementa y mantiene eficazmente?'),
    ('P', TODAS('9.2.2'), '¿Se planifica, establece, implementa y mantiene un programa de auditoría (frecuencia, métodos, responsabilidades, requisitos de planificación y elaboración de informes) que tiene en cuenta la importancia de los procesos, los cambios que afectan a la organización y los resultados de las auditorías previas?'),
    ('P', TODAS('9.2.2'), '¿Se definen los criterios y el alcance de cada auditoría y se seleccionan los auditores y se llevan a cabo las auditorías para asegurar la objetividad e imparcialidad del proceso?'),
    ('P', TODAS('9.2.2'), '¿Se informan los resultados a la dirección pertinente (en SST, también a los trabajadores y sus representantes y a otras partes interesadas pertinentes), se realizan las correcciones y acciones correctivas oportunamente y se conserva información documentada de la implementación del programa y de los resultados?'),

    ('S', '9.3', 'Revisión por la dirección'),
    ('P', T('9.3.1', '9.3', '9.3'), '¿La alta dirección revisa el sistema de gestión a intervalos planificados para asegurar su conveniencia, adecuación y eficacia continuas, y su alineación con la dirección estratégica de la organización?'),
    ('P', T('9.3.2', '9.3', '9.3'), '¿Las entradas incluyen el estado de las acciones de revisiones previas, los cambios en las cuestiones externas e internas, en las necesidades y expectativas de las partes interesadas (incluidos los requisitos legales y otros requisitos) y en los riesgos y oportunidades, y el grado en que se han logrado los objetivos?'),
    ('P', T('9.3.2'), '¿Las entradas incluyen la satisfacción del cliente y la retroalimentación de las partes interesadas, el desempeño de los procesos y la conformidad de los productos y servicios, las no conformidades y acciones correctivas, los resultados de seguimiento y medición y de las auditorías, el desempeño de los proveedores externos, la adecuación de los recursos, la eficacia de las acciones sobre riesgos y oportunidades y las oportunidades de mejora?'),
    ('P', T(c14='9.3', c45='9.3'), '¿Las entradas incluyen la información sobre el desempeño ambiental y de la SST (incidentes, no conformidades y acciones correctivas, resultados de seguimiento y medición, evaluación del cumplimiento, auditorías, consulta y participación de los trabajadores), los aspectos ambientales significativos, las comunicaciones pertinentes de las partes interesadas (incluidas las quejas) y la adecuación de los recursos?'),
    ('P', T('9.3.3', '9.3', '9.3'), '¿Las salidas incluyen las decisiones relacionadas con las oportunidades de mejora, las necesidades de cambio en el sistema de gestión y de recursos, las acciones necesarias cuando no se logran los objetivos y, en ambiental y SST, las implicaciones para la dirección estratégica y la integración con otros procesos de negocio?'),
    ('P', T('9.3.3', '9.3', '9.3'), '¿Se conserva información documentada como evidencia de los resultados de las revisiones por la dirección y, en SST, se comunican los resultados pertinentes a los trabajadores y sus representantes?'),

    ('S', '10', 'MEJORA'),
    ('S', '10.1', 'Generalidades'),
    ('P', TODAS('10.1'), '¿Se determinan y seleccionan las oportunidades de mejora y se implementan las acciones necesarias para lograr los resultados previstos del sistema de gestión (mejorar productos y servicios, prevenir o reducir efectos no deseados, mejorar el desempeño y la eficacia)?'),

    ('S', '10.2', 'No conformidad y acción correctiva (en ISO 45001: Incidentes, no conformidades y acciones correctivas)'),
    ('P', T('10.2.1', '10.2', '10.2'), '¿Cuando ocurre una no conformidad (o un incidente), se reacciona de manera oportuna para controlarla y corregirla y se hace frente a las consecuencias, incluida la mitigación de impactos ambientales adversos?'),
    ('P', T(c45='10.2'), '¿Los incidentes se informan, investigan y analizan con la participación de los trabajadores y de otras partes interesadas pertinentes, para determinar sus causas?'),
    ('P', T('10.2.1', '10.2', '10.2'), '¿Se evalúa la necesidad de acciones para eliminar las causas, mediante la revisión y el análisis de la no conformidad, la determinación de sus causas y la determinación de si existen no conformidades similares o que potencialmente podrían ocurrir?'),
    ('P', T('10.2.1', '10.2', '10.2'), '¿Se implementan las acciones necesarias (en SST, aplicando la jerarquía de controles y la gestión del cambio y revisando las evaluaciones de riesgos existentes) y se revisa su eficacia?'),
    ('P', T('10.2.1', '10.2', '10.2'), '¿Si es necesario, se actualizan los riesgos y oportunidades determinados en la planificación y se hacen cambios al sistema de gestión? ¿Las acciones correctivas son apropiadas a los efectos o impactos de las no conformidades encontradas?'),
    ('P', T('10.2.2', '10.2', '10.2'), '¿Se conserva información documentada como evidencia de la naturaleza de las no conformidades (o incidentes), las acciones tomadas y sus resultados, incluida su eficacia, y en SST se comunica a los trabajadores pertinentes?'),

    ('S', '10.3', 'Mejora continua'),
    ('P', TODAS('10.3'), '¿Se mejora continuamente la conveniencia, adecuación y eficacia del sistema de gestión (y, en ambiental y SST, el desempeño)?'),
    ('P', T('10.3'), '¿Se consideran los resultados del análisis y la evaluación y las salidas de la revisión por la dirección para determinar si hay necesidades u oportunidades de mejora?'),
    ('P', T(c45='10.3'), '¿Se promueve una cultura que apoye el sistema de gestión de SST, se promueve la participación de los trabajadores en las acciones de mejora continua y se comunican los resultados pertinentes a los trabajadores y sus representantes?'),
]

LETRAS = 'abcdefghijklmnopqrstuvwxyz'


def filas():
    """(codigo, titulo, es_seccion, formato, orden) en el orden de la lista."""
    out, clausula, n, orden = [], '', 0, 0
    for fila in LISTA:
        orden += 1
        if fila[0] == 'S':
            _, codigo, titulo = fila
            if '.' in codigo:
                clausula, n = codigo, 0
            out.append((codigo, titulo, True, [], orden))
            continue
        _, refs, pregunta = fila
        codigo = f'{clausula}.{LETRAS[n]}'
        n += 1
        ref = ' · '.join(f'{norma}: {c}' for norma, c in refs)
        # En el impreso cada referencia no se parte entre líneas.
        ref_html = ' · '.join(f'{norma}: {c}'.replace(' ', '&nbsp;') for norma, c in refs)
        out.append((codigo, f'{ref}\n{pregunta}', False,
                    [{'t': f'<b>{ref_html}</b>', 'j': 'left'}, {'t': pregunta}], orden))
    return out


def cargar(apps, schema_editor):
    RequisitoNorma = apps.get_model('esynapse_sig', 'RequisitoNorma')
    RequisitoNorma.objects.filter(norma='sig_integrado').delete()
    RequisitoNorma.objects.bulk_create([
        RequisitoNorma(norma='sig_integrado', bloque='requisitos', codigo=c, titulo=t,
                       es_seccion=s, formato=f, orden=o)
        for c, t, s, f, o in filas()])


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0055_lider_desde_equipo'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
