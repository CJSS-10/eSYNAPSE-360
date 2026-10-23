"""Lista integrada ISO 9001 / 14001 / 45001: la columna Nro. de cada pregunta
pasa a ser un correlativo (1, 2, 3…). La numeración anterior (4.1.a, 4.1.b…)
parecía un numeral de la norma que no existe; la referencia real a la norma va
en negrita al inicio de cada pregunta. Los títulos de cláusula conservan su
numeral (4, 4.1…). Las listas ya generadas conservan sus ítems."""
from django.db import migrations


def correlativo(apps, schema_editor):
    RequisitoNorma = apps.get_model('esynapse_sig', 'RequisitoNorma')
    preguntas = RequisitoNorma.objects.filter(norma='sig_integrado', es_seccion=False).order_by('orden')
    # Primero códigos temporales para no chocar con los finales.
    for p in preguntas:
        RequisitoNorma.objects.filter(pk=p.pk).update(codigo=f'tmp-{p.pk}')
    for n, p in enumerate(preguntas.order_by('orden'), start=1):
        RequisitoNorma.objects.filter(pk=p.pk).update(codigo=str(n))


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0057_numeracion_secciones_aparte'),
    ]

    operations = [
        migrations.RunPython(correlativo, migrations.RunPython.noop),
    ]
