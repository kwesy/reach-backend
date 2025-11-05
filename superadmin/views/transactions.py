from rest_framework import generics
from main.models import AccountTransaction
from superadmin.serializers import AdminTransactionSerializer
from common.mixins.response import StandardResponseView
from oauth.permissions import IsAdmin


class AdminTransactionView(StandardResponseView ,generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminTransactionSerializer

    def get_queryset(self):
        return AccountTransaction.objects.all()
