from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from main.models import AccountTransaction
from main.serializers import TransactionSerializer
from common.mixins.response import StandardResponseView



class TransactionView(StandardResponseView ,generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return AccountTransaction.objects.exclude(transaction_type='fee').filter(account__owner=self.request.user).order_by('-created_at')
