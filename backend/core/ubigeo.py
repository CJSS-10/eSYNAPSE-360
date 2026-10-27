"""API del catálogo de ubigeos del Perú: lista compacta para los selectores encadenados departamento → provincia →
distrito (la pantalla la descarga una vez y filtra en el navegador)."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ubigeo


class UbigeoView(APIView):
    """GET → [[codigo, departamento, provincia, distrito], …] de los ubigeos vigentes."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filas = Ubigeo.objects.filter(is_active=True).values_list('codigo', 'departamento', 'provincia', 'distrito')
        resp = Response([list(f) for f in filas])
        resp['Cache-Control'] = 'private, max-age=86400'
        return resp
