"""
eSYNAPSE 360 — Limpieza de datos de prueba del módulo Documentos.
Borra TODOS los documentos, versiones, firmas, observaciones y verificaciones.
Conserva: usuarios, roles, permisos, hallazgos y el log de auditoría.

EJECUTAR CON EL SERVIDOR APAGADO, desde backend con el venv activo:
    python limpiar_documentos_prueba.py
"""
import os
import shutil
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esynapse.settings')
import django  # noqa: E402
django.setup()

from esynapse_sig.models import (  # noqa: E402
    Documento, FirmaVersion, ObservacionVersion, VerificacionExterna, VersionDocumento,
)

print('=== LIMPIEZA DE DOCUMENTOS DE PRUEBA ===\n')
conteos = {
    'Firmas': FirmaVersion.objects.count(),
    'Observaciones': ObservacionVersion.objects.count(),
    'Verificaciones externas': VerificacionExterna.objects.count(),
    'Versiones': VersionDocumento.objects.count(),
    'Documentos': Documento.objects.count(),
}
for k, v in conteos.items():
    print(f'  {k}: {v}')

if sum(conteos.values()) == 0:
    print('\nNo hay nada que limpiar.')
    raise SystemExit(0)

# Respaldo de la base de datos (consistente: el servidor está apagado)
fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
os.makedirs('backups', exist_ok=True)
shutil.copy('db.sqlite3', f'backups/db_antes_limpieza_{fecha}.sqlite3')
print(f'\nRespaldo creado: backups/db_antes_limpieza_{fecha}.sqlite3')

respuesta = input('\n¿Eliminar TODOS los datos de documentos? Escriba SI para confirmar: ')
if respuesta.strip().upper() != 'SI':
    print('Cancelado. No se eliminó nada.')
    raise SystemExit(0)

# Orden correcto: hijos primero (las FK son PROTECT)
FirmaVersion.objects.all().delete()
ObservacionVersion.objects.all().delete()
VerificacionExterna.objects.all().delete()
VersionDocumento.objects.all().delete()
Documento.objects.all().delete()

print('\n✔ Módulo Documentos limpio. Usuarios, roles, hallazgos y log intactos.')
print('Reinicia el servidor y empieza con tus datos reales.')
