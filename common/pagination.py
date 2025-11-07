# pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.pagination import LimitOffsetPagination


# Option A: Standard Page Numbers (e.g., ?page=3)
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10 # Sets this specific view to 5 items per page
    page_size_query_param = 'page_size' # Allows client to specify page size like ?page_size=20
    max_page_size = 100

# Option B: Limit/Offset (e.g., ?limit=10&offset=30)
class LimitOffsetResultsSetPagination(LimitOffsetPagination):
    default_limit = 10
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 50
