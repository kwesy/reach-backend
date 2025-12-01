from common.mixins.response import StandardResponseView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response



class DashboardView(StandardResponseView):
    permission_classes = [IsAuthenticated]
    success_message = "Dashboard data fetched successfully"
    
    def get(self, request):
        user_fiat_acc = request.user.account.fiat()
        user_btc_account = request.user.account.crypto()

        return Response({
            "fiat": {
                "account_number": user_fiat_acc.account_number,
                "balance": user_fiat_acc.balance,
                "currency": user_fiat_acc.currency,
                "daily_withdrawal_limit": user_fiat_acc.daily_transfer_limit - user_fiat_acc.get_daily_transferred_amount()
            },
            "crypto": [
                {
                    "account_number": user_btc_account.account_number,
                    "balance": user_btc_account.balance,
                    "currency": user_btc_account.currency,
                    "daily_withdrawal_limit": user_btc_account.daily_transfer_limit - user_btc_account.get_daily_transferred_amount()
                }
            ] if user_btc_account else []
        })
