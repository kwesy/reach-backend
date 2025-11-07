from rest_framework import generics, filters
from main.models import AccountTransaction
from superadmin.filters import TransactionFilter
from superadmin.pagination import StandardResultsSetPagination
from superadmin.serializers import AdminTransactionSerializer
from common.mixins.response import StandardResponseView
from oauth.permissions import IsAdmin
import django_filters.rest_framework 


class AdminTransactionView(StandardResponseView ,generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminTransactionSerializer

    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter
    ]
    filterset_class = TransactionFilter 
    # Define the fields to search using the 'search' query parameter
    search_fields = [
        'reference_id', 
        'account__account_number',
        'destination_account__account_number',
    ]

    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return AccountTransaction.objects.all()
