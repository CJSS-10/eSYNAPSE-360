"""Carga inicial del catálogo de procesos y de las 18 fichas de caracterización
revisadas por César (2026-10-21). Las fichas entran como versión 01 en
elaboración para que pasen por las firmas. Además vincula al catálogo los
procesos escritos a mano en Documentos y Hallazgos y registra los formatos."""
import json
from pathlib import Path

from django.db import migrations

ARCHIVO = Path(__file__).resolve().parent.parent / 'datos' / 'carga_inicial.json'
ALIAS = {'sig': 'Sistema Integrado de Gestión', 'alta dirección': 'Gestión Estratégica',
         'alta direccion': 'Gestión Estratégica'}
FORMATOS = [
    ('procesos_ficha', 'Ficha de caracterización de procesos', 'procesos', 'SIG-M-01-r03', 60),
    ('procesos_mapa', 'Mapa de procesos', 'procesos', 'SIG-M-01-r02', 61),
]


def cargar(apps, schema_editor):
    Proceso = apps.get_model('procesos', 'Proceso')
    Ficha = apps.get_model('procesos', 'Ficha')
    Actividad = apps.get_model('procesos', 'Actividad')
    DocumentoFicha = apps.get_model('procesos', 'DocumentoFicha')
    RegistroFicha = apps.get_model('procesos', 'RegistroFicha')
    Indicador = apps.get_model('procesos', 'Indicador')
    Documento = apps.get_model('esynapse_sig', 'Documento')
    Hallazgo = apps.get_model('esynapse_sig', 'Hallazgo')
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')

    datos = json.loads(ARCHIVO.read_text(encoding='utf-8'))
    if not Proceso.objects.exists():
        por_nombre = {}
        for c in datos['catalogo']:
            por_nombre[c['nombre']] = Proceso.objects.create(
                nombre=c['nombre'], tipo=c['tipo'], padre=por_nombre.get(c['padre']),
                responsable_cargo=c['responsable_cargo'], detalle_mapa=c['detalle_mapa'], orden=c['orden'])
        docs = {d.titulo.strip().lower(): d for d in Documento.objects.filter(is_active=True)}
        frecuencias = {'mensual', 'trimestral', 'semestral', 'anual'}
        for f in datos['fichas']:
            ficha = Ficha.objects.create(
                proceso=por_nombre[f['proceso']], version='01', estado='borrador', motivo_cambio='',
                objetivo=f['objetivo'], responsable=f['responsable'], alcance=f['alcance'],
                recurso_humano=f['recurso_humano'], recurso_economico=f['recurso_economico'],
                recurso_tecnologico=f['recurso_tecnologico'])
            for i, a in enumerate(f['actividades'], 1):
                act = Actividad.objects.create(
                    ficha=ficha, orden=i, seccion=a['seccion'], proveedor_otro=a['proveedor_otro'],
                    entrada=a['entrada'], actividad=a['actividad'], control=a['control'],
                    cliente_otro=a['cliente_otro'], salida=a['salida'])
                act.proveedores.set([por_nombre[n] for n in a['proveedores']])
                act.clientes.set([por_nombre[n] for n in a['clientes']])
            for i, texto in enumerate(f['documentos'], 1):
                titulo = texto.lower().replace('procedimiento de ', '', 1)
                doc = docs.get(texto.lower()) or docs.get(titulo)
                DocumentoFicha.objects.create(ficha=ficha, orden=i, documento=doc,
                                              descripcion='' if doc else texto)
            for i, texto in enumerate(f['registros'], 1):
                RegistroFicha.objects.create(ficha=ficha, orden=i, descripcion=texto)
            for i, ind in enumerate(f['indicadores'], 1):
                Indicador.objects.create(ficha=ficha, orden=i, nombre=ind['nombre'], calculo=ind['calculo'],
                                         meta=ind['meta'], responsable=ind['responsable'],
                                         frecuencia=ind['frecuencia'] if ind['frecuencia'] in frecuencias
                                         else 'mensual')

    catalogo = {p.nombre.lower(): p for p in Proceso.objects.filter(is_active=True)}
    for modelo in (Documento, Hallazgo):
        for obj in modelo.objects.filter(proceso_catalogo__isnull=True).exclude(proceso=''):
            t = obj.proceso.strip().lower()
            p = catalogo.get(ALIAS.get(t, t).lower())
            if p:
                obj.proceso_catalogo = p
                obj.proceso = p.nombre
                obj.save(update_fields=['proceso_catalogo', 'proceso'])

    for clave, nombre, modulo, codigo, orden in FORMATOS:
        fi, _ = FormatoImpreso.objects.update_or_create(
            clave=clave, defaults={'nombre': nombre, 'modulo': modulo, 'codigo_sgc': codigo, 'orden': orden})
        if not fi.documento_id:
            doc = Documento.objects.filter(codigo=codigo, is_active=True).first()
            if doc:
                fi.documento = doc
                fi.save(update_fields=['documento'])


class Migration(migrations.Migration):

    dependencies = [
        ('procesos', '0001_initial'),
        ('esynapse_sig', '0069_documento_proceso_catalogo_hallazgo_proceso_catalogo'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
