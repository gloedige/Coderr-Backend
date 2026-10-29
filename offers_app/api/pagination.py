from rest_framework.pagination import PageNumberPagination


class OfferPagination(PageNumberPagination):
    """Paginate offers with a default of 3 and a maximum of 100 per page."""

    page_size = 3
    page_size_query_param = 'page_size'
    max_page_size = 100
