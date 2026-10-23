"""Carga del catálogo de EPP (formato de entrega de EPP, con las marcas de la matriz) y de la matriz de EPP
por puesto de trabajo, y registro de los formatos impresos de EPP y de exámenes médicos ocupacionales."""
from django.db import migrations

# (nombre, tipo, clasificación, marca / modelo, descartable)
CATALOGO = [
    ('Casco tipo I', 'cabeza', 'especifico', '3M', False),
    ('Casco tipo II', 'cabeza', 'especifico', '', False),
    ('Goggles', 'visual', 'especifico', '1623AF - 3M', False),
    ('Lentes de seguridad luna clara', 'visual', 'basico', 'Startec Pro - 3M', False),
    ('Sobrelentes luna clara', 'visual', 'especifico', '', False),
    ('Sobrelentes luna oscura', 'visual', 'especifico', '', False),
    ('Orejeras adaptables al casco', 'auditiva', 'especifico', '', False),
    ('Tapones de oído', 'auditiva', 'especifico', '3M 22 dB 1270', False),
    ('Guantes de nitrilo descartables', 'manos', 'especifico', '', True),
    ('Guantes de nitrilo', 'manos', 'especifico', '13" 15 MIL Steelpro', False),
    ('Guantes anticorte', 'manos', 'basico', 'Multiflex', False),
    ('Guantes dieléctricos', 'manos', 'especifico', '', False),
    ('Guantes resistentes al calor', 'manos', 'especifico', '250 °C', False),
    ('Guantes de carnaza', 'manos', 'especifico', 'Cuero carnaza / badana', False),
    ('Guantes de PVC', 'manos', 'especifico', '', False),
    ('Botas de jebe', 'pies', 'especifico', '', False),
    ('Botas de seguridad punta de acero', 'pies', 'basico', '', False),
    ('Botas de seguridad dieléctricas', 'pies', 'especifico', '', False),
    ('Respirador media cara', 'respiratoria', 'especifico', '6200 - 3M', False),
    ('Respirador descartable', 'respiratoria', 'especifico', '', True),
    ('Filtros', 'respiratoria', 'especifico', '', True),
    ('Cartuchos para gases y vapores', 'respiratoria', 'especifico', '60926 - 3M', True),
    ('Arnés', 'caidas', 'especifico', '', False),
    ('Línea de anclaje', 'caidas', 'especifico', '', False),
    ('Guardapolvo', 'ropa', 'basico', '', False),
    ('Mameluco', 'ropa', 'especifico', '', False),
    ('Chaleco', 'ropa', 'especifico', '', False),
    ('Camisa', 'uniforme', 'basico', '', False),
    ('Polo', 'uniforme', 'basico', '', False),
]
# Columnas de la matriz → EPP del catálogo.
COL = {'I': 'Camisa', 'M': 'Polo', 'Q': 'Guardapolvo', 'U': 'Chaleco', 'Y': 'Mameluco', 'AC': 'Respirador media cara',
       'AG': 'Cartuchos para gases y vapores', 'AK': 'Casco tipo I', 'AO': 'Goggles',
       'AS': 'Lentes de seguridad luna clara', 'AW': 'Botas de seguridad punta de acero',
       'BA': 'Botas de seguridad dieléctricas', 'BE': 'Botas de jebe', 'BI': 'Tapones de oído',
       'BM': 'Guantes anticorte', 'BQ': 'Guantes de nitrilo', 'BU': 'Guantes de nitrilo descartables',
       'BY': 'Guantes de carnaza', 'CC': 'Guantes de PVC', 'CG': 'Guantes dieléctricos',
       'CK': 'Guantes resistentes al calor'}
ADMIN = ['Gerente General', 'Gerente SIG', 'Asistente SIG', 'Gerente Comercial y Marketing', 'Asistente Comercial',
         'Ejecutivo de Ventas', 'Coordinador de Marketing', 'Diseñador Gráfico', 'Gerente de Administración',
         'Coordinador Administrativo', 'Asistente Administrativo', 'Analista Contable', 'Encargado de Compras',
         'Encargado de Recursos Humanos', 'Gerente de I+D+i', 'Soporte de TI']
LAB = ['Encargado de Laboratorio', 'Supervisor de Laboratorio', 'Metrólogo']
METRO = 'METROLOGÍA (encargados por laboratorio)'
# (grupo, nombre en la matriz, puestos, área, en campo, columnas «x», columnas «x*»)
MATRIZ = [
    ('ADMINISTRATIVOS', 'Trabajadores administrativos (contabilidad, SIG, recursos humanos, administración, comercial, '
     'marketing, servicios generales*)', ADMIN, None, False, 'I M', 'AS BE'),
    ('LOGÍSTICA', 'Conductor de minivan', ['Conductor / Operador Logístico'], None, False, 'I M U BI', 'AK AW'),
    ('LOGÍSTICA', 'Motorizado', [], None, False, 'I M U BI', 'AK AW'),
    ('LOGÍSTICA', 'Auxiliar logístico', ['Auxiliar Logístico'], None, False, 'I M BM', ''),
    ('LOGÍSTICA', 'Coordinador logístico', ['Coordinador Logístico'], None, False, 'I M BM', ''),
    (METRO, 'Análisis Químico', LAB, 'Laboratorio de Análisis Químico', False, 'I M Q AC AG AO AW BI BQ', ''),
    (METRO, 'Electricidad y Potencia', LAB, 'Laboratorio de Electricidad y Potencia', False,
     'I M Q AS BA BI BM BY CG', ''),
    (METRO, 'Masa y Volumen', LAB, 'Laboratorio de Masa y Volumen', False, 'I M Q AC AG AS AW BI BM BU', ''),
    (METRO, 'Temperatura y Humedad', LAB, 'Laboratorio de Temperatura y Humedad', False, 'I M Q AO AW BM CK', ''),
    (METRO, 'Longitud y Ángulo', LAB, 'Laboratorio de Longitud y Ángulo', False, 'I M Q AW BM BU', ''),
    (METRO, 'Fuerza y Presión', LAB, 'Laboratorio de Fuerza y Presión', False, 'I M Q Y AK AS AW BI BY CC', ''),
    (METRO, 'Grandes volúmenes', LAB, 'Laboratorio de Grandes Volúmenes', False, 'I M Q AS AW', ''),
    ('CAMPO', 'Sector industrial', [], None, True, 'I M U AK AS AW BI BM', 'Y BU BY CC CG'),
    ('CAMPO', 'Sector minero', [], None, True, 'I M U AK AS AW', 'Y BA BI CG'),
]
FORMATOS = [
    ('sst_matriz_epp', 'Matriz de EPP por puesto de trabajo', 'SIG-PRO-27-r01', 140),
    ('sst_entrega_epp', 'Entrega de equipo de protección personal', 'SIG-PRO-27-r02', 141),
    ('sst_examenes_medicos', 'Registro de exámenes médicos ocupacionales', 'SIG-PRO-06-r17', 142),
]


def cargar(apps, schema_editor):
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    Documento = apps.get_model('esynapse_sig', 'Documento')
    for clave, nombre, codigo, orden in FORMATOS:
        f, _ = FormatoImpreso.objects.update_or_create(
            clave=clave, defaults={'nombre': nombre, 'modulo': 'sst', 'codigo_sgc': codigo, 'orden': orden})
        if not f.documento_id:
            doc = Documento.objects.filter(codigo=codigo, is_active=True).first()
            if doc:
                f.documento = doc
                f.save(update_fields=['documento'])
    Catalogo = apps.get_model('sst', 'CatalogoEPP')
    Perfil = apps.get_model('sst', 'PerfilEPP')
    Requisito = apps.get_model('sst', 'RequisitoEPP')
    Puesto = apps.get_model('organizacion', 'Puesto')
    Area = apps.get_model('organizacion', 'Area')
    if Catalogo.objects.exists():
        return
    epp = {}
    for n, (nombre, tipo, clas, marca, desc) in enumerate(CATALOGO, 1):
        epp[nombre] = Catalogo.objects.create(nombre=nombre, tipo=tipo, clasificacion=clas, marca_modelo=marca,
                                              descartable=desc, orden=n)
    for n, (grupo, nombre, puestos, area, campo, oblig, tarea) in enumerate(MATRIZ, 1):
        p = Perfil.objects.create(grupo=grupo, nombre=nombre, en_campo=campo, orden=n,
                                  area=Area.objects.filter(nombre=area).first() if area else None)
        p.puestos.set(Puesto.objects.filter(nombre__in=puestos))
        for cols, nivel in ((oblig, 'obligatorio'), (tarea, 'segun_tarea')):
            for c in cols.split():
                Requisito.objects.get_or_create(perfil=p, epp=epp[COL[c]], defaults={'nivel': nivel})


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0012_epp_y_vigilancia_medica'),
        ('organizacion', '0003_corrige_tipo_areas_propuestas'),
        ('esynapse_sig', '0071_alter_hallazgo_fuente'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
