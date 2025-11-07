from common.mixins.response import StandardResponseView
from main.models.account import AccountTransaction, CryptoAccount
from rest_framework import viewsets, filters, generics
from main.models import FiatAccount
from superadmin.filters import AdminAccountFilter, TransactionFilter
from common.pagination import StandardResultsSetPagination
from superadmin.serializers.account import AdminCryptoAccountSerializer, AdminFiatAccountSerializer
from oauth.permissions import IsAdmin
import django_filters.rest_framework
from superadmin.serializers.transactions import AdminTransactionSerializer



class AdminAllFiatAccountViewSet(StandardResponseView, viewsets.ModelViewSet):
    queryset = FiatAccount.objects.all()
    permission_classes = [IsAdmin]
    serializer_class = AdminFiatAccountSerializer
    filterset_fields = ['currency', 'is_active', 'transfer_allowed', 'owner__email']
    lookup_field = 'account_number'

    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter
    ]
    filterset_class = AdminAccountFilter 
    # Define the fields to search using the 'search' query parameter
    search_fields = [
        'owner__email', 
        'account_number',
    ]

    pagination_class = StandardResultsSetPagination

    def destroy(self, request, *args, **kwargs):
        raise NotImplementedError("Fiat accounts cannot be deleted via this viewset.")


class AdminAllCryptoAccountViewSet(StandardResponseView, viewsets.ModelViewSet):
    queryset = CryptoAccount.objects.all()
    permission_classes = [IsAdmin]
    serializer_class = AdminCryptoAccountSerializer
    filterset_fields = ['currency', 'is_active', 'transfer_allowed', 'owner__email']
    lookup_field = 'account_number'
    
    def destroy(self, request, *args, **kwargs):
        raise NotImplementedError("Crypto accounts cannot be deleted via this viewset.")
    

class AdminAccountTransactionView(StandardResponseView ,generics.ListAPIView):
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
        'destination_account__account_number',
    ]

    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return AccountTransaction.objects.filter(account__account_number=self.kwargs.get('account_number'))
