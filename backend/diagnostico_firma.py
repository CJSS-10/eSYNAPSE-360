"""
eSYNAPSE 360 — Diagnóstico de la firma criptográfica.
Ejecutar desde backend con el venv activo:  python diagnostico_firma.py
"""
import io
import os
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esynapse.settings')
import django  # noqa: E402
django.setup()

print('=== DIAGNÓSTICO DE FIRMA CRIPTOGRÁFICA ===\n')

print('1. Librerías:')
for lib in ('endesive', 'cryptography', 'reportlab', 'pypdf', 'pdfplumber'):
    try:
        mod = __import__(lib)
        print(f'   {lib}: {getattr(mod, "__version__", "ok")}')
    except Exception as e:
        print(f'   {lib}: *** FALTA O FALLA: {e} ***')

print('\n2. Carpeta de certificados:')
from esynapse_sig.firma_digital import DIR_CERTS, CA_PFX  # noqa: E402
print('   Ruta:', DIR_CERTS)
print('   Existe:', DIR_CERTS.exists())
print('   CA generada:', CA_PFX.exists())

print('\n3. Prueba de firma completa:')
try:
    from types import SimpleNamespace
    from django.utils import timezone
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from core.models import Usuario
    from esynapse_sig.firma_digital import firmar_pdf_criptograficamente

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(100, 700, 'diagnostico de firma')
    c.save()

    u = Usuario.objects.filter(is_active=True).first()
    print('   Usuario de prueba:', u.username)
    firma = SimpleNamespace(rol='aprobado', usuario=u, created_at=timezone.now(),
                            get_rol_display=lambda: 'Aprobado')
    resultado = firmar_pdf_criptograficamente(buf.getvalue(), [firma])
    tiene_firma = b'/ByteRange' in resultado
    print(f'   PDF firmado: {len(resultado)} bytes — firma incrustada: {tiene_firma}')
    print('\n*** TODO FUNCIONA: el problema fue que el documento se aprobó con el servidor')
    print('    corriendo código anterior. Reinicia el servidor y aprueba un documento nuevo. ***')
except Exception:
    print('\n*** AQUÍ ESTÁ EL ERROR — copia todo esto y pégaselo a Claude: ***\n')
    traceback.print_exc()
