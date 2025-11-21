from giftcards.models.giftcard import RedeemedGiftCard
from main.models.account import Account
from superadmin.filters import GiftcardOrdersFilter
from superadmin.serializers.giftcard import RedeemedGiftCardSerializer
from rest_framework import viewsets, generics, filters
from giftcards.models import GiftCard, GiftCardType
from superadmin.serializers import GiftCardSerializer, GiftCardTypeSerializer
from oauth.permissions import IsAdmin, IsAdminOrReadOnly
from common.mixins.response import StandardResponseView
from django.db import transaction
import logging
from rest_framework.exceptions import ValidationError
from common.pagination import StandardResultsSetPagination
import django_filters.rest_framework


logger = logging.getLogger('transactions')

class GiftCardTypeViewSet(viewsets.ModelViewSet):
    queryset = GiftCardType.objects.all()
    serializer_class = GiftCardTypeSerializer
    permission_classes = [IsAdmin]

class GiftCardViewSet(viewsets.ModelViewSet):
    queryset = GiftCard.objects.all()
    serializer_class = GiftCardSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['giftcard_type', 'redeemed_by']

class RedeemedGiftCardView(StandardResponseView, generics.ListAPIView, generics.UpdateAPIView):
    queryset = RedeemedGiftCard.objects.all()
    serializer_class = RedeemedGiftCardSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['giftcard_type', 'status', 'redeemed_by']

    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter
    ]
    filterset_class = GiftcardOrdersFilter 
    # Define the fields to search using the 'search' query parameter
    search_fields = [
        'redeemed_by__email', 
    ]

    pagination_class = StandardResultsSetPagination

    def perform_update(self, serializer):
        amount_confirmed = serializer.validated_data.get('amount_confirmed', 0)
        redeemed_by = serializer.instance.redeemed_by
        external_ref_id = serializer.validated_data.get('external_ref_id', '')
        source = serializer.validated_data.get('source', '')

        if not external_ref_id or not source:
            raise ValidationError({"detail":"Both external_ref_id and source are required to process the gift card."})

        if serializer.instance.status in ['redeemed', 'failed']:
            # No action needed if already redeemed or failed
            raise ValidationError({"detail":"This gift card has already been processed."})
        
         # If no user is associated or amount confirmed is zero or status is not redeemed, just save without processing
        if not redeemed_by or amount_confirmed <= 0 or serializer.validated_data.get('status') != 'redeemed':
            serializer.save()
            return

        sys_account = Account.get_sys_account()
        sys_revenue_acc = Account.get_sys_revenue_account()
        user_fiat_acc = redeemed_by.account.fiat()
        exchange_rate = serializer.instance.exchange_rate

        try:   
            with transaction.atomic():
                # credit the admin's fiat account if the gift card is approved
                sys_account.deposit(
                    amount=amount_confirmed,
                    direction="gift_card_to_account",
                    description=f"Deposit with {serializer.instance.giftcard_type.name} Gift Card",
                    metadata={
                        "channel": "gift_card",
                        "provider": source,
                        "external_ref_id": external_ref_id,
                        "account_number": "",
                        },
                    performed_by=self.request.user,
                    auto_complete=True,
                    )
                
                # credit the user's fiat account with thier share
                user_fiat_acc.credit_account(amount_confirmed * exchange_rate, performed_by=self.request.user, description=f"Gift Card Redemption ID: {str(serializer.instance.id)}")
                if exchange_rate < 1: # if the plaform get a share
                    sys_account.transfer(amount_confirmed * (1-exchange_rate), sys_revenue_acc, performed_by=self.request.user, description=f"Gift Card Redemption ID: {str(serializer.instance.id)}")

        except Exception as e:
            logger.error("Credit failed for account %s: %s", user_fiat_acc.account_number, str(e), exc_info=True)
            raise e

        serializer.save()
