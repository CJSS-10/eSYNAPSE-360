"""
Lista de verificación INTEGRADA de las normas de sistemas de gestión
(ISO 9001:2015, ISO 14001:2015 e ISO 45001:2018), en una sola lista combinada.

Añade:
- la norma 'sig_integrado' a las listas de verificación y al catálogo,
- el campo 'documento de referencia' en los ítems de la lista,
- amplía el largo de los requisitos (las preguntas integradas son extensas),
- carga el contenido de la lista integrada por cláusula del Anexo SL.

Los ítems marcados (9001) / (14001) / (45001) aplican solo a esa norma; el
resto es común a las tres. El contenido se gestiona desde el catálogo.
"""
from django.db import migrations, models


# (codigo, titulo, es_seccion)
CATALOGO_SIG = [
    ('4', 'CONTEXTO DE LA ORGANIZACIÓN', True),
    ('4.1', 'Comprensión de la organización y de su contexto', True),
    ('4.1.a', '¿La organización ha determinado las cuestiones externas e internas pertinentes para su propósito y dirección estratégica, y que afectan su capacidad para lograr los resultados previstos del sistema de gestión?', False),
    ('4.1.b', '(14001) ¿Se han considerado las condiciones ambientales que pueden afectar o verse afectadas por la organización?', False),
    ('4.2', 'Comprensión de las necesidades y expectativas de las partes interesadas', True),
    ('4.2.a', '¿Se han determinado las partes interesadas pertinentes y sus necesidades y expectativas (requisitos)?', False),
    ('4.2.b', '(45001) ¿Se ha determinado cuáles de esas necesidades y expectativas se convierten en requisitos legales y otros requisitos, incluyendo los de los trabajadores?', False),
    ('4.3', 'Determinación del alcance del sistema de gestión', True),
    ('4.3.a', '¿El alcance del sistema de gestión está determinado, documentado y disponible, considerando las cuestiones, los requisitos y los productos/servicios?', False),
    ('4.4', 'Sistema de gestión y sus procesos', True),
    ('4.4.a', '¿Se han establecido, implementado, mantenido y mejorado los procesos necesarios y sus interacciones?', False),

    ('5', 'LIDERAZGO', True),
    ('5.1', 'Liderazgo y compromiso', True),
    ('5.1.a', '¿La alta dirección demuestra liderazgo y compromiso con el sistema de gestión (rendición de cuentas, integración en los procesos, disponibilidad de recursos)?', False),
    ('5.1.b', '(9001) ¿La alta dirección demuestra liderazgo y compromiso con el enfoque al cliente?', False),
    ('5.1.c', '(45001) ¿La alta dirección protege a los trabajadores de represalias al informar incidentes, peligros y riesgos, y promueve la mejora continua?', False),
    ('5.2', 'Política', True),
    ('5.2.a', '¿La política (de calidad / ambiental / de SST) está establecida, es apropiada, incluye los compromisos aplicables, está documentada y comunicada?', False),
    ('5.2.b', '(14001) ¿La política ambiental incluye el compromiso de protección del medio ambiente y prevención de la contaminación?', False),
    ('5.2.c', '(45001) ¿La política de SST incluye el compromiso de proporcionar condiciones de trabajo seguras y saludables y de eliminar peligros y reducir riesgos?', False),
    ('5.3', 'Roles, responsabilidades y autoridades en la organización', True),
    ('5.3.a', '¿Se han asignado, comunicado y entendido las responsabilidades y autoridades para los roles pertinentes?', False),
    ('5.4', 'Consulta y participación de los trabajadores (45001)', True),
    ('5.4.a', '(45001) ¿Existen mecanismos para la consulta y participación de los trabajadores y sus representantes en el sistema de gestión de SST?', False),

    ('6', 'PLANIFICACIÓN', True),
    ('6.1', 'Acciones para abordar riesgos y oportunidades', True),
    ('6.1.a', '¿Se han determinado los riesgos y oportunidades que es necesario abordar y se han planificado acciones para ello?', False),
    ('6.1.b', '(14001) ¿Se han identificado y evaluado los aspectos ambientales y sus impactos, y determinado los significativos?', False),
    ('6.1.c', '(14001/45001) ¿Se han determinado los requisitos legales y otros requisitos aplicables y cómo se aplican?', False),
    ('6.1.d', '(45001) ¿Se han identificado los peligros y evaluado los riesgos para la SST (IPERC), considerando rutina/no rutina, incidentes y cambios?', False),
    ('6.2', 'Objetivos y planificación para lograrlos', True),
    ('6.2.a', '¿Se han establecido objetivos (de calidad / ambientales / de SST) medibles, coherentes con la política, y planes con recursos, responsables y plazos?', False),
    ('6.3', 'Planificación de los cambios (9001)', True),
    ('6.3.a', '(9001) ¿Los cambios en el sistema de gestión de la calidad se llevan a cabo de manera planificada?', False),

    ('7', 'APOYO', True),
    ('7.1', 'Recursos', True),
    ('7.1.a', '¿Se han determinado y proporcionado los recursos necesarios (personas, infraestructura, ambiente para la operación de los procesos)?', False),
    ('7.1.b', '(9001) ¿Los recursos de seguimiento y medición son adecuados y se asegura la trazabilidad metrológica cuando es un requisito?', False),
    ('7.2', 'Competencia', True),
    ('7.2.a', '¿Se determina la competencia necesaria, se asegura mediante educación/formación/experiencia y se conservan evidencias?', False),
    ('7.3', 'Toma de conciencia', True),
    ('7.3.a', '¿El personal es consciente de la política, los objetivos, su contribución y las implicaciones de no cumplir los requisitos?', False),
    ('7.3.b', '(45001) ¿Los trabajadores toman conciencia de los peligros, riesgos y acciones, y de su capacidad de alejarse de situaciones de peligro grave?', False),
    ('7.4', 'Comunicación', True),
    ('7.4.a', '¿Se ha determinado la comunicación interna y externa pertinente (qué, cuándo, a quién, cómo)?', False),
    ('7.5', 'Información documentada', True),
    ('7.5.a', '¿La información documentada requerida está controlada (creación, actualización, distribución, acceso, conservación)?', False),

    ('8', 'OPERACIÓN', True),
    ('8.1', 'Planificación y control operacional', True),
    ('8.1.a', '¿Se planifican, implementan y controlan los procesos necesarios para cumplir los requisitos y las acciones de la cláusula 6?', False),
    ('8.1.b', '(45001) ¿Se eliminan peligros y reducen riesgos de SST según la jerarquía de controles, y se gestiona el cambio?', False),
    ('8.1.c', '(45001) ¿Se controlan las compras, los contratistas y la contratación externa en lo relativo a la SST?', False),
    ('8.2', 'Requisitos para los productos y servicios (9001)', True),
    ('8.2.a', '(9001) ¿Se determinan y revisan los requisitos para los productos y servicios y la comunicación con el cliente?', False),
    ('8.3', 'Diseño y desarrollo (9001)', True),
    ('8.3.a', '(9001) ¿El proceso de diseño y desarrollo está planificado y controlado (entradas, controles, salidas, cambios), cuando aplica?', False),
    ('8.4', 'Control de procesos, productos y servicios suministrados externamente (9001)', True),
    ('8.4.a', '(9001) ¿Se controlan los proveedores externos y se evalúan/seleccionan/reevalúan según criterios?', False),
    ('8.5', 'Producción y provisión del servicio (9001)', True),
    ('8.5.a', '(9001) ¿La producción/prestación se realiza bajo condiciones controladas (identificación, trazabilidad, propiedad del cliente, preservación)?', False),
    ('8.6', 'Liberación de los productos y servicios (9001)', True),
    ('8.6.a', '(9001) ¿Se verifica el cumplimiento de los requisitos antes de la liberación y se conservan evidencias?', False),
    ('8.7', 'Control de las salidas no conformes (9001)', True),
    ('8.7.a', '(9001) ¿Las salidas no conformes se identifican y controlan para prevenir su uso o entrega no intencionada?', False),
    ('8.2e', 'Preparación y respuesta ante emergencias (14001/45001)', True),
    ('8.2e.a', '(14001/45001) ¿Se han establecido procesos para prepararse y responder ante situaciones de emergencia potenciales?', False),

    ('9', 'EVALUACIÓN DEL DESEMPEÑO', True),
    ('9.1', 'Seguimiento, medición, análisis y evaluación', True),
    ('9.1.a', '¿Se ha determinado qué, cómo y cuándo medir y analizar, y se evalúa el desempeño y la eficacia del sistema de gestión?', False),
    ('9.1.b', '(9001) ¿Se realiza el seguimiento de la satisfacción del cliente?', False),
    ('9.1.c', '(14001/45001) ¿Se evalúa periódicamente el cumplimiento de los requisitos legales y otros requisitos?', False),
    ('9.2', 'Auditoría interna', True),
    ('9.2.a', '¿Se planifican y realizan auditorías internas a intervalos planificados, con programa, criterios, alcance y auditores objetivos e imparciales?', False),
    ('9.3', 'Revisión por la dirección', True),
    ('9.3.a', '¿La alta dirección revisa el sistema de gestión considerando las entradas requeridas y genera salidas con decisiones y acciones?', False),

    ('10', 'MEJORA', True),
    ('10.1', 'Generalidades', True),
    ('10.1.a', '¿Se determinan y seleccionan oportunidades de mejora y se implementan acciones para cumplir requisitos y aumentar la satisfacción/desempeño?', False),
    ('10.2', 'No conformidad y acción correctiva', True),
    ('10.2.a', '¿Ante una no conformidad se reacciona, se evalúan causas, se implementan acciones correctivas y se verifica su eficacia?', False),
    ('10.2.b', '(45001) ¿Los incidentes se investigan para determinar causas y acciones, con participación de los trabajadores?', False),
    ('10.3', 'Mejora continua', True),
    ('10.3.a', '¿Se mejora continuamente la conveniencia, adecuación y eficacia del sistema de gestión?', False),
]


def cargar(apps, schema_editor):
    RequisitoNorma = apps.get_model('esynapse_sig', 'RequisitoNorma')
    for orden, (codigo, titulo, es_seccion) in enumerate(CATALOGO_SIG, start=1):
        RequisitoNorma.objects.update_or_create(
            norma='sig_integrado', codigo=codigo,
            defaults={'titulo': titulo, 'es_seccion': es_seccion, 'orden': orden},
        )


def borrar(apps, schema_editor):
    apps.get_model('esynapse_sig', 'RequisitoNorma').objects.filter(norma='sig_integrado').delete()


class Migration(migrations.Migration):

    dependencies = [('esynapse_sig', '0036_solicitud_modulo')]

    operations = [
        migrations.AlterField(
            model_name='requisitonorma',
            name='norma',
            field=models.CharField(
                choices=[('iso_9001', 'ISO 9001'), ('iso_14001', 'ISO 14001'),
                         ('iso_45001', 'ISO 45001 / Ley 29783'), ('iso_17025', 'NTP ISO/IEC 17025'),
                         ('sig_integrado', 'Sistema Integrado (ISO 9001 · 14001 · 45001)')],
                max_length=20, verbose_name='Norma'),
        ),
        migrations.AlterField(
            model_name='requisitonorma',
            name='titulo',
            field=models.CharField(max_length=600, verbose_name='Título'),
        ),
        migrations.AlterField(
            model_name='listaverificacion',
            name='norma',
            field=models.CharField(
                choices=[('iso_9001', 'ISO 9001'), ('iso_14001', 'ISO 14001'),
                         ('iso_45001', 'ISO 45001 / Ley 29783'), ('iso_17025', 'NTP ISO/IEC 17025'),
                         ('sig_integrado', 'Sistema Integrado (ISO 9001 · 14001 · 45001)')],
                max_length=20, verbose_name='Norma'),
        ),
        migrations.AlterField(
            model_name='itemverificacion',
            name='titulo',
            field=models.CharField(max_length=500, verbose_name='Requisito'),
        ),
        migrations.AddField(
            model_name='itemverificacion',
            name='documento_referencia',
            field=models.TextField(blank=True, verbose_name='Documento de referencia'),
        ),
        migrations.RunPython(cargar, borrar),
    ]
