"""
eSYNAPSE 360 — Motor de firma electrónica de documentos.

- hash_sha256: huella digital del archivo
- convertir_a_pdf: Word/Excel → PDF vía LibreOffice (si está instalado)
- localizar_cajas: encuentra los recuadros ELABORADO/REVISADO/APROBADO
- dibujar_sellos_caratula: sellos visuales (respaldo si no hay firma criptográfica)
- generar_pdf_firmado: hoja de control de firmas + coordinación del estampado
"""
import hashlib
import io
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.utils import timezone

LOGO_FIRMA = Path(__file__).resolve().parent / 'recursos' / 'logo_firma.png'

RUTAS_SOFFICE = [
    'soffice',
    r'C:\Program Files\LibreOffice\program\soffice.exe',
    r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
]

ROL_ETIQUETA = {'elaborado': 'ELABORADO', 'revisado': 'REVISADO', 'aprobado': 'APROBADO'}


def hash_sha256(filefield_o_bytes) -> str:
    h = hashlib.sha256()
    if isinstance(filefield_o_bytes, bytes):
        h.update(filefield_o_bytes)
    else:
        filefield_o_bytes.open('rb')
        for chunk in filefield_o_bytes.chunks():
            h.update(chunk)
        filefield_o_bytes.close()
    return h.hexdigest()


def buscar_soffice():
    for ruta in RUTAS_SOFFICE:
        encontrado = shutil.which(ruta) if not Path(ruta).is_absolute() else (ruta if Path(ruta).exists() else None)
        if encontrado:
            return encontrado
    return None


def convertir_a_pdf(contenido: bytes, extension: str) -> bytes | None:
    """Convierte Word/Excel a PDF con LibreOffice. None si no está disponible."""
    soffice = buscar_soffice()
    if not soffice:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        origen = Path(tmp) / f'documento{extension}'
        origen.write_bytes(contenido)
        try:
            subprocess.run(
                [soffice, '--headless', '--convert-to', 'pdf', '--outdir', tmp, str(origen)],
                capture_output=True, timeout=120, check=True,
            )
        except (subprocess.SubprocessError, OSError):
            return None
        pdf = origen.with_suffix('.pdf')
        return pdf.read_bytes() if pdf.exists() else None


def localizar_cajas(pdf_base: bytes, firmas) -> dict:
    """
    Busca las etiquetas ELABORADO / REVISADO / APROBADO en la primera página
    (plantilla estándar del Anexo 1) y devuelve el recuadro de
    firma de cada rol: {rol: (x1, y1, x2, y2)}. Vacío si no hay plantilla.
    """
    import pdfplumber
    from reportlab.lib.units import mm

    try:
        with pdfplumber.open(io.BytesIO(pdf_base)) as pdf:
            pagina = pdf.pages[0]
            alto = float(pagina.height)
            palabras = pagina.extract_words()
    except Exception:
        return {}

    anclas = {}
    for w in palabras:
        texto = w['text'].strip().upper().rstrip(':')
        if texto in ROL_ETIQUETA.values() and texto not in anclas:
            anclas[texto] = w
    if len(anclas) < 3:
        return {}

    cajas = {}
    for firma in firmas:
        w = anclas.get(ROL_ETIQUETA.get(firma.rol))
        if not w:
            continue
        centro_x = (float(w['x0']) + float(w['x1'])) / 2
        y_base = alto - float(w['top']) + 4 * mm
        cajas[firma.rol] = (centro_x - 26 * mm, y_base - 3 * mm,
                            centro_x + 26 * mm, y_base + 17 * mm)
    return cajas


def dibujar_sellos_caratula(pdf_base: bytes, firmas, cajas: dict) -> bytes:
    """
    Sellos visuales dibujados sobre la carátula (RESPALDO: se usa solo si la
    firma criptográfica no está disponible; con ella, la apariencia la dibuja
    el propio campo de firma y es clicable).
    """
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    if not cajas:
        return pdf_base

    lector = PdfReader(io.BytesIO(pdf_base))
    pagina1 = lector.pages[0]
    ancho = float(pagina1.mediabox.width)
    alto = float(pagina1.mediabox.height)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(ancho, alto))
    hay_logo = LOGO_FIRMA.exists()
    for firma in firmas:
        caja = cajas.get(firma.rol)
        if not caja:
            continue
        x1, y1, x2, y2 = caja
        centro_x = (x1 + x2) / 2
        y_base = y1 + 3 * mm
        nombre = firma.usuario.get_full_name() or firma.usuario.username
        fecha_local = timezone.localtime(firma.created_at).strftime('%Y-%m-%d %H:%M')
        lineas = [
            ('Helvetica', 6.5, 'Firmado electrónicamente por:'),
            ('Helvetica-Bold', 8, nombre),
            ('Helvetica', 7, firma.cargo or ''),
            ('Helvetica', 6.5, f'{fecha_local} · eSYNAPSE 360°'),
        ]
        alto_bloque = sum(3.6 * mm for _ in lineas)
        if hay_logo:
            texto_x = centro_x - 6 * mm
            try:
                c.drawImage(str(LOGO_FIRMA), centro_x - 26 * mm, y_base - 2 * mm,
                            width=19 * mm, height=alto_bloque + 4 * mm, preserveAspectRatio=True,
                            anchor='c', mask='auto')
            except Exception:
                texto_x = None
            y = y_base + alto_bloque - 3.6 * mm
            for fuente, tamano, texto in lineas:
                if texto:
                    c.setFont(fuente, tamano)
                    if texto_x is not None:
                        c.drawString(texto_x, y, texto)
                    else:
                        c.drawCentredString(centro_x, y, texto)
                y -= 3.6 * mm
        else:
            y = y_base + alto_bloque - 3.6 * mm
            for fuente, tamano, texto in lineas:
                if texto:
                    c.setFont(fuente, tamano)
                    c.drawCentredString(centro_x, y, texto)
                y -= 3.6 * mm
    c.save()
    buf.seek(0)

    base = PdfReader(io.BytesIO(pdf_base))
    sello = PdfReader(buf).pages[0]
    salida = PdfWriter()
    primera = base.pages[0]
    primera.merge_page(sello)
    salida.add_page(primera)
    for pagina in base.pages[1:]:
        salida.add_page(pagina)
    resultado = io.BytesIO()
    salida.write(resultado)
    return resultado.getvalue()


def generar_pdf_firmado(pdf_base: bytes, documento, version, firmas, con_sellos=True):
    """
    Anexa la hoja de control de firmas electrónicas al final del PDF.
    Si con_sellos=True, además dibuja los sellos visuales en la carátula
    (modo respaldo). Devuelve (pdf_bytes, cajas).
    """
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    cajas = localizar_cajas(pdf_base, firmas)
    if con_sellos:
        pdf_base = dibujar_sellos_caratula(pdf_base, firmas, cajas)

    hash_base = hashlib.sha256(pdf_base).hexdigest()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ancho, alto = A4
    y = alto - 30 * mm

    if LOGO_FIRMA.exists():
        try:
            c.drawImage(str(LOGO_FIRMA), 20 * mm, alto - 38 * mm, width=22 * mm, height=18 * mm,
                        preserveAspectRatio=True, anchor='nw', mask='auto')
        except Exception:
            pass
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(ancho / 2, y, 'HOJA DE CONTROL DE FIRMAS ELECTRÓNICAS')
    y -= 8 * mm
    c.setFont('Helvetica', 10)
    c.drawCentredString(ancho / 2, y, 'eSYNAPSE 360° — Metrindust S.A.C.')
    y -= 14 * mm

    c.setFont('Helvetica-Bold', 11)
    c.drawString(25 * mm, y, f'{documento.codigo} — {documento.titulo}')
    y -= 6 * mm
    c.setFont('Helvetica', 10)
    c.drawString(25 * mm, y, f'Versión: {version.version}   ·   Tipo: {documento.get_tipo_display()}')
    y -= 12 * mm

    for f in firmas:
        c.setFont('Helvetica-Bold', 10)
        c.drawString(25 * mm, y, f.get_rol_display().upper())
        y -= 5.5 * mm
        c.setFont('Helvetica', 10)
        nombre = f.usuario.get_full_name() or f.usuario.username
        c.drawString(30 * mm, y, f'{nombre} — {f.cargo or "—"}')
        y -= 5 * mm
        fecha_local = timezone.localtime(f.created_at).strftime('%Y-%m-%d %H:%M:%S')
        c.drawString(30 * mm, y, f'Firmado electrónicamente el {fecha_local}  ·  IP {f.ip or "—"}')
        y -= 5 * mm
        c.setFont('Helvetica', 8)
        c.drawString(30 * mm, y, f'Huella del archivo al firmar (SHA-256): {f.hash_archivo}')
        y -= 10 * mm

    y -= 4 * mm
    c.setFont('Helvetica', 8)
    c.drawString(25 * mm, y, f'Huella del documento publicado (SHA-256): {hash_base}')
    y -= 5 * mm
    c.drawString(25 * mm, y, 'Las firmas fueron confirmadas con contraseña personal y registradas en el log de auditoría inmutable del eSYNAPSE 360°.')
    y -= 5 * mm
    c.drawString(25 * mm, y, 'Toda copia impresa de este documento es COPIA NO CONTROLADA.')
    c.save()
    buf.seek(0)

    salida = PdfWriter()
    for pagina in PdfReader(io.BytesIO(pdf_base)).pages:
        salida.add_page(pagina)
    salida.add_page(PdfReader(buf).pages[0])
    resultado = io.BytesIO()
    salida.write(resultado)
    return resultado.getvalue(), cajas
