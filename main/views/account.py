import logging
from common.mixins.ip_blocker import IPBlockerMixin
from common.mixins.response import StandardResponseView
from main.serializers import DepositFundsSerializer, WithdrawFundsSerializer
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError
from django.shortcuts import get_object_or_404
from main.models import AccountTransaction
from services.services import charge_mobile_money, send_mobile_money
from rest_framework.views import APIView
from decouple import config
import secrets


logger = logging.getLogger('error')

def generate_reference_number(length):
    return ''.join(secrets.choice('0123456789') for _ in range(length))

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

ALLOWED_DEPOSIT_ENDPOINT_IPS = config('ALLOWED_DEPOSIT_ENDPOINT_IPS', cast=lambda v: [ip.strip() for ip in v.split(',')])

class DepositWebHookView(IPBlockerMixin, APIView):
    permission_class = [permissions.AllowAny]
    WHITELIST_IPS = ALLOWED_DEPOSIT_ENDPOINT_IPS
    ENFORCE_WHITELIST = True

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
    
class WithdrawView(StandardResponseView):
    permission_classes = [permissions.IsAuthenticated]
    success_message = "Withdrawal successfull"
    
    def post(self, request):
        account = request.user.account.fiat()

        if not account:
            raise ValidationError({"detail":"Account not provided or does not exist"})
        if account.account_role not in ["user"]:
            raise ValidationError({"detail":"Account type not allowed to perform withdrawals."})

        serializer = WithdrawFundsSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        amount = data["amount"]
        data["amount"] = str(amount)

        try:
            if data['channel'] == 'mobile_money':
                client_reference = generate_reference_number(15)
                res = send_mobile_money(amount=data['amount'], phone_number=data['account_number'], provider=data['network'], account_name='doe', client_reference=client_reference)

                tx = account.withdraw(
                    amount=amount,
                    direction="account_to_mobile_money",
                    performed_by=request.user,
                    metadata= {
                        "channel": data['channel'],
                        "provider": data['network'],
                        "client_reference": client_reference,
                        "external_ref_id": res.get('transaction_id', ''),
                        "account_number": data['account_number'],
                        "account_name": "doe"
                    }
                )
            else:
                raise APIException("Withdrawal channel not supported.")
        except Exception as e:
            logger.error("Withdrawal failed for account %s: %s", account.account_number, str(e), exc_info=True)
            raise APIException("Withdrawal failed. Please try again later.")   

        return Response(status=status.HTTP_201_CREATED)
