from rest_framework import generics
from main.models import AccountTransaction
from superadmin.filters import TransactionFilter
from superadmin.serializers import AdminTransactionSerializer
from common.mixins.response import StandardResponseView
from oauth.permissions import IsAdmin
import django_filters.rest_framework 


class AdminTransactionView(StandardResponseView ,generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminTransactionSerializer

    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = TransactionFilter 


    def get_queryset(self):
        return AccountTransaction.objects.all()
