"""
Firma de una aprobación por el Comité de SST ("realizado y aprobado por"), común a los registros que el comité
aprueba (matriz IPERC, programa anual de capacitación…).

- En pantalla: firman todos los titulares, cada uno con la contraseña de su usuario o, si no tiene usuario, con su
  PIN. Se validan todas las credenciales antes de guardar nada.
- En papel: se adjunta el acta firmada, se marcan los titulares que firmaron y quien registra firma con su contraseña.
"""
import json

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response


def lista_de(v):
    """Lista desde JSON, texto separado por comas o lista."""
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            v = [x for x in v.split(',') if x.strip()]
    return list(v or [])


def cargo_comite(m):
    if m.cargo == 'presidente':
        return 'Presidente del Comité de SST'
    if m.cargo == 'secretario':
        return 'Secretario(a) del Comité de SST'
    return f'Miembro {m.get_condicion_display().lower()} del Comité de SST'


def comite_vigente(fecha=None):
    from .comite import ComiteSST
    fecha = fecha or timezone.localdate()
    return ComiteSST.objects.filter(is_active=True, fecha_instalacion__lte=fecha, fecha_fin__gte=fecha).first()


def titulares_para_firmar(fecha=None):
    """Titulares del comité vigente y cómo firma cada uno (usuario / estado del PIN)."""
    from .epp_api import _estado_pin
    c = comite_vigente(fecha)
    titulares = [{'id': m.pk, 'nombre': m.trabajador.nombre_completo, 'cargo': cargo_comite(m),
                  'representacion': m.get_representacion_display(), 'firma': _estado_pin(m.trabajador)}
                 for m in (c.titulares().select_related('trabajador__usuario') if c else [])]
    return c, titulares


def firmas_del_comite(request, fecha, todos=True):
    """Valida y arma las firmas del comité. Devuelve (datos, None) con {firmas, reunion, papel} o (None, error).
    Regla de Metrindust (César, 2026-10-24): todo lo que aprueba el Comité lo firman TODOS sus titulares (IPERC,
    programa de capacitación, matriz de aspectos ambientales, Programa SSOMA). todos=False deja la mitad más uno."""
    from .comite import ReunionComite
    from .epp_api import firma_persona

    def err(texto):
        return None, Response({'detail': texto}, status=status.HTTP_400_BAD_REQUEST)
    if fecha > timezone.localdate():
        return err('La fecha de aprobación no puede ser futura.')
    c = comite_vigente(fecha)
    if not c:
        return err('No hay un Comité de SST vigente en esa fecha.')
    titulares = {m.pk: m for m in c.titulares(fecha).select_related('trabajador__usuario')}
    if not titulares:
        return err('El comité vigente no tiene titulares registrados.')
    quorum = len(titulares) if todos else len(titulares) // 2 + 1
    regla = 'todos los titulares' if todos else 'mitad más uno'
    reunion = None
    if request.data.get('reunion'):
        reunion = ReunionComite.objects.filter(pk=request.data['reunion'], comite=c, is_active=True).first()
        if not reunion:
            return err('Reunión no encontrada en el comité vigente.')
        if reunion.estado == 'cancelada':
            return err('La reunión indicada está cancelada.')
    papel = bool(request.FILES.get('archivo'))
    firmas = []
    if papel:
        ids = [int(x) for x in lista_de(request.data.get('firmantes')) if str(x).isdigit()]
        if [i for i in ids if i not in titulares] or len(set(ids)) < quorum:
            return err(f'Marque a los titulares que firmaron el acta (al menos {quorum}: {regla}).')
        password = request.data.get('password') or ''
        if not password:
            return err('Confirme con su contraseña para firmar el registro de la aprobación.')
        if not request.user.check_password(password):
            return err('Contraseña incorrecta. No se registró la aprobación.')
        for i in dict.fromkeys(ids):
            m = titulares[i]
            firmas.append({'miembro_id': m.pk, 'trabajador_id': m.trabajador_id, 'nombre': m.trabajador.nombre_completo,
                           'cargo': cargo_comite(m), 'metodo': 'papel', 'fecha': fecha.isoformat()})
    else:
        datos = lista_de(request.data.get('firmas'))
        if any(not isinstance(f, dict) or not str(f.get('miembro') or '').isdigit() for f in datos):
            return err('Firmas mal formadas: cada firma indica el miembro que firma.')
        ids = [int(f['miembro']) for f in datos]
        if any(i not in titulares for i in ids) or len(ids) != len(set(ids)):
            return err('Solo firman los miembros titulares del comité, una vez cada uno.')
        if len(ids) < quorum:
            return err(f'Se requiere la firma de al menos {quorum} titular(es) ({regla}); firmaron {len(ids)}.')
        # Primero se validan todas las credenciales; los PIN nuevos se guardan solo si todas son válidas.
        nuevos = []
        for f in datos:
            m = titulares[int(f['miembro'])]
            fm, error = firma_persona(request, m.trabajador, datos=f, clave='clave', crear_pin=False)
            if error:
                return None, error
            if fm['metodo'] == 'pin' and f.get('pin_nuevo'):
                nuevos.append((m, f))
            firmas.append({**fm, 'miembro_id': m.pk, 'cargo': cargo_comite(m)})
        for m, f in nuevos:
            _, error = firma_persona(request, m.trabajador, datos=f, clave='clave')
            if error:
                return None, error
    return {'firmas': firmas, 'reunion': reunion, 'papel': papel}, None
