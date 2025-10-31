import logging
from common.mixins.response import StandardResponseView
from main.serializers import DepositFundsSerializer
from rest_framework import permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from main.models import AccountTransaction
from services.services import charge_mobile_money


logger = logging.getLogger('error')

class DepositView(StandardResponseView):
    permission_classes = [permissions.IsAuthenticated]
    success_message = "Deposit Initiated successfully"
    
    def post(self, request):
        account = request.user.account.fiat()
        serializer = DepositFundsSerializer(
            data=request.data,
            context={"account": account, "user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        tx = serializer.save()

        try:
            charge_mobile_money(amount=serializer.validated_data['amount'], phone_number=serializer.validated_data['phone_number'], provider=serializer.validated_data['network'], transaction_id=tx.reference_id, dynamic_id=tx.id)
        except Exception as e:
            logger.error("Deposit Fialed: %s", str(e), exc_info=True)
            raise e

        return Response(status=status.HTTP_201_CREATED)

class DepositWebHookView(StandardResponseView):
    permission_class = [permissions.AllowAny]

    def post(self, request, transaction_id):
        data = request.data
        transaction_status = data['status']
        amount = data['amount']
        reference_id = data['transaction_id']
        ext_transaction_id = data['ext_transaction_id']

        # Find transaction
        tx = get_object_or_404(
            AccountTransaction, pk=transaction_id, transaction_type="deposit"
        )

        # Get related account
        account = tx.account.fiataccount

        # Confirm deposit
        tx = account.deposit_confirm(
            transaction_id=transaction_id,
            status=transaction_status,
            amount=amount,
            metadata= {'ext_transaction_id': ext_transaction_id, 'reference_id': reference_id},
        )

        return Response(status=status.HTTP_200_OK)