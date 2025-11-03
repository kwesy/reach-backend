from common.mixins.response import StandardResponseView
from giftcards.models.giftcard import GiftCard, RedeemedGiftCard
from main.models.account import Account, AccountTransaction
from oauth.permissions import IsAdmin
from rest_framework.response import Response
from django.contrib.auth import get_user_model



class AdminDashboardView(StandardResponseView):
    permission_classes = [IsAdmin]
    success_message = "Dashboard fetched successfully"

    def get(self, request):
        total_users = get_user_model().objects.count()
        total_transactions = AccountTransaction.objects.count()
        total_giftcard_sold = GiftCard.objects.filter(is_redeemed=True).count()
        total_giftcard_redeemed = RedeemedGiftCard.objects.filter(status='redeemed').count()
        total_revenue = Account.get_sys_revenue_account().balance

        recent_users = get_user_model().objects.values('first_name','last_name', 'email', 'is_active', 'role')[:5]
        recent_tx = (
            AccountTransaction.objects
            .order_by('-created_at')
            .values(
                'account__account_number',
                'account__owner__first_name', 
                'account__owner__last_name', 
                'description',
                'amount',
                'status'
            )[:5]
        )

        # Clean up field names
        simplified_txs = [
            {
                "account_number": tx["account__account_number"],
                "user": f'{tx["account__owner__first_name"]} {tx["account__owner__last_name"]}',
                "description": tx["description"],
                "amount": tx["amount"],
                "status": tx["status"],
            }
            for tx in recent_tx
        ]

        return Response({
            "total_users": total_users,
            "total_transactions": total_transactions,
            "total_giftcard_sold": total_giftcard_sold,
            "total_giftcard_redeemed": total_giftcard_sold,
            "total_revenue": total_revenue,
            "recent_transactions": simplified_txs,
            "recent_users": recent_users
        })

