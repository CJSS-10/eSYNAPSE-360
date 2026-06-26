"""
eSYNAPSE 360 — Capa criptográfica de firma (PAdES con endesive).

El SIGE actúa como Autoridad Certificadora interna de Metrindust:
- Genera una vez el certificado raíz de la empresa (CA eSYNAPSE 360).
- Emite automáticamente un certificado personal a cada usuario firmante.
- Aplica firmas criptográficas incrementales al PDF publicado: Adobe y otros
  lectores muestran el Panel de firma y verifican la integridad del documento.

Si un usuario tiene certificado acreditado propio (.pfx comprado, ej. RENIEC),
se usa el suyo: colocar el archivo en certificados/usuarios/<username>.pfx y
su contraseña en la variable de entorno CERT_PASS_<USERNAME en mayúsculas>.
"""
import datetime
import hashlib
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from django.conf import settings

DIR_CERTS = Path(settings.BASE_DIR) / 'certificados'
DIR_USUARIOS = DIR_CERTS / 'usuarios'
CA_PFX = DIR_CERTS / 'ca_esynapse360.pfx'


def _password_interna() -> bytes:
    """Contraseña de los certificados internos, derivada del SECRET_KEY del proyecto."""
    return hashlib.sha256(('esynapse-ca-' + settings.SECRET_KEY).encode()).hexdigest()[:32].encode()


def _crear_ca():
    """Genera el certificado raíz de Metrindust (una sola vez, 10 años)."""
    DIR_CERTS.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'PE'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'METRINDUST S.A.C.'),
        x509.NameAttribute(NameOID.COMMON_NAME, 'CA eSYNAPSE 360 Metrindust'),
    ])
    ahora = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nombre).issuer_name(nombre)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora)
        .not_valid_after(ahora + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=True,
            crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
        .sign(key, hashes.SHA256())
    )
    datos = pkcs12.serialize_key_and_certificates(
        b'ca-esynapse360', key, cert, None,
        serialization.BestAvailableEncryption(_password_interna()),
    )
    CA_PFX.write_bytes(datos)
    # Certificado público de la CA (.cer) para instalarlo como confiable
    # en las computadoras de Metrindust (doble clic → Instalar certificado)
    (DIR_CERTS / 'ca_esynapse360_publico.cer').write_bytes(
        cert.public_bytes(serialization.Encoding.DER))
    return key, cert


def _cargar_ca():
    if not CA_PFX.exists():
        return _crear_ca()
    key, cert, _ = pkcs12.load_key_and_certificates(CA_PFX.read_bytes(), _password_interna())
    return key, cert


def _emitir_certificado_usuario(usuario):
    """Emite el certificado personal del usuario, firmado por la CA interna (3 años)."""
    DIR_USUARIOS.mkdir(parents=True, exist_ok=True)
    ca_key, ca_cert = _cargar_ca()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre_completo = usuario.get_full_name() or usuario.username
    email = usuario.email or f'{usuario.username}@metrindust.local'
    sujeto = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'PE'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'METRINDUST S.A.C.'),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, usuario.area or 'SIG'),
        x509.NameAttribute(NameOID.COMMON_NAME, nombre_completo),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS, email),
    ])
    ahora = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(sujeto).issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora)
        .not_valid_after(ahora + datetime.timedelta(days=1095))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=True, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=False,
            crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.RFC822Name(email)]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([
            x509.oid.ExtendedKeyUsageOID.EMAIL_PROTECTION,
            x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
        ]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    datos = pkcs12.serialize_key_and_certificates(
        usuario.username.encode(), key, cert, [ca_cert],
        serialization.BestAvailableEncryption(_password_interna()),
    )
    (DIR_USUARIOS / f'{usuario.username}.esynapse.pfx').write_bytes(datos)
    return datos


def _obtener_pfx_usuario(usuario):
    """
    Devuelve (bytes_pfx, password) del usuario:
    1. Si existe <username>.pfx (certificado acreditado propio) y su contraseña
       en la variable de entorno CERT_PASS_<USERNAME>, se usa ese.
    2. Si no, se usa (o emite) el certificado interno emitido por la CA eSYNAPSE 360.
    """
    propio = DIR_USUARIOS / f'{usuario.username}.pfx'
    env_pass = os.environ.get(f'CERT_PASS_{usuario.username.upper()}')
    if propio.exists() and env_pass:
        return propio.read_bytes(), env_pass.encode()
    interno = DIR_USUARIOS / f'{usuario.username}.esynapse.pfx'
    if not interno.exists():
        _emitir_certificado_usuario(usuario)
    return interno.read_bytes(), _password_interna()


def _logo_para_sello():
    """Versión reducida del logo para las apariencias de firma (evita
    incrustar la imagen a resolución completa en cada sello)."""
    from .firmas import LOGO_FIRMA
    if not LOGO_FIRMA.exists():
        return None
    reducido = LOGO_FIRMA.with_name('logo_firma_sello.png')
    if not reducido.exists() or reducido.stat().st_mtime < LOGO_FIRMA.stat().st_mtime:
        try:
            from PIL import Image
            img = Image.open(LOGO_FIRMA)
            img.thumbnail((220, 220))
            img.save(reducido)
        except Exception:
            return str(LOGO_FIRMA)
    return str(reducido)


def firmar_pdf_criptograficamente(pdf_bytes: bytes, firmas, cajas=None) -> bytes:
    """
    Aplica una firma criptográfica incremental (PAdES) por cada firma del flujo,
    en orden: Elaborado → Revisado → Aprobado. Cada una con el certificado
    personal del firmante. Las firmas son invisibles (los sellos visuales ya
    están estampados); Adobe las muestra en su Panel de firma.
    """
    from endesive import pdf as endesive_pdf
    from django.utils import timezone as djtz

    resultado = pdf_bytes
    for indice, firma in enumerate(firmas, 1):
        clave_pfx, password = _obtener_pfx_usuario(firma.usuario)
        key, cert, extras = pkcs12.load_key_and_certificates(clave_pfx, password)
        fecha_acto = djtz.localtime(firma.created_at).strftime('%Y-%m-%d %H:%M:%S')
        ahora = datetime.datetime.now(datetime.timezone.utc)
        dct = {
            'sigflags': 3,
            'sigfield': f'FirmaSIGE_{indice}_{firma.rol}',
            'contact': firma.usuario.email or '',
            'location': 'Lima, Perú',
            'signingdate': ahora.strftime('D:%Y%m%d%H%M%S+00\'00\''),
            'reason': f'{firma.get_rol_display()} el {fecha_acto} (registro eSYNAPSE 360°)',
        }
        caja = (cajas or {}).get(firma.rol)
        if caja:
            # Sello = campo de firma: la apariencia (logo + texto) la dibuja
            # el propio campo, así el clic abre la validación (como INACAL).
            from .firmas import LOGO_FIRMA
            logo_sello = _logo_para_sello()
            x1, y1, x2, y2 = caja
            w, h = x2 - x1, y2 - y1
            nombre = firma.usuario.get_full_name() or firma.usuario.username
            fecha_corta = djtz.localtime(firma.created_at).strftime('%Y-%m-%d %H:%M')
            texto = (f'Firmado electrónicamente por:\n{nombre}\n'
                     f'{firma.cargo or ""}\n{fecha_corta} · eSYNAPSE 360°')
            dct['signaturebox'] = caja
            dct['sigpage'] = 0
            comandos = []
            if logo_sello:
                dct['manual_images'] = {'logo': logo_sello}
                ancho_logo = min(58, w * 0.38)
                comandos.append(['image', 'logo', 2, 2, ancho_logo, h - 4, False, True])
                texto_x = ancho_logo + 6
            else:
                texto_x = 4
            comandos += [
                ['fill_colour', 0, 0, 0],
                ['font', 'default', 7],
                ['text_box', texto, 'default', texto_x, 2, w - texto_x - 4, h - 4,
                 7, True, 'left', 'middle', 1.25],
            ]
            dct['signature_manual'] = comandos
        else:
            dct['signature'] = ''  # sin plantilla: firma invisible
        resultado = resultado + endesive_pdf.cms.sign(resultado, dct, key, cert, extras or [], 'sha256')
    return resultado
