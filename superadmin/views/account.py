from main.models.account import CryptoAccount
from rest_framework import viewsets
from main.models import FiatAccount
from superadmin.serializers.account import AdminCryptoAccountSerializer, AdminFiatAccountSerializer
from oauth.permissions import IsAdmin


class AdminAllFiatAccountViewSet(viewsets.ModelViewSet):
    queryset = FiatAccount.objects.all()
    permission_classes = [IsAdmin]
    serializer_class = AdminFiatAccountSerializer
    filterset_fields = ['currency', 'is_active', 'transfer_allowed', 'owner__email']
    lookup_field = 'account_number'

    def destroy(self, request, *args, **kwargs):
        raise NotImplementedError("Fiat accounts cannot be deleted via this viewset.")


class AdminAllCryptoAccountViewSet(viewsets.ModelViewSet):
    queryset = CryptoAccount.objects.all()
    permission_classes = [IsAdmin]
    serializer_class = AdminCryptoAccountSerializer
    filterset_fields = ['currency', 'is_active', 'transfer_allowed', 'owner__email']
    lookup_field = 'account_number'
    
    def destroy(self, request, *args, **kwargs):
        raise NotImplementedError("Crypto accounts cannot be deleted via this viewset.")