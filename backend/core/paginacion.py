"""Paginación del API: 25 por página por omisión; el cliente puede pedir hasta 1000 con ?page_size=N."""
from rest_framework.pagination import PageNumberPagination


class PaginacionSIG(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 1000
