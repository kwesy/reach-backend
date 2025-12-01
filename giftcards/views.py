from django.shortcuts import render
from common.pagination import StandardResultsSetPagination
from giftcards.models.giftcard import GiftCard, GiftCardType, RedeemedGiftCard
from giftcards.serializers import GiftCardTypeSerializer, GiftCardsSerializer, RedeemedGiftCardSerializer
from main.models.account import Account
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.exceptions import ValidationError
from common.mixins.response import StandardResponseView
from django.utils import timezone
import logging
from services.services import send_email
from decouple import config
from django.shortcuts import get_object_or_404


logger = logging.getLogger("error")

class RedeemGiftCardView(StandardResponseView):
    """
    API view to redeem a gift card.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        gift_card_code = request.data.get('code')
        gift_card_type = request.data.get('type')
        amount = request.data.get('amount')

        if not gift_card_code:
            raise ValidationError({'detail': 'Gift card code is required.'})
        
        gc_type = get_object_or_404(GiftCardType, pk=gift_card_type)

        if not gc_type or not gc_type.is_active:
            raise ValidationError({'detail': 'Invalid or inactive gift card type.'})

        # Check if the gift card exists and is not already redeemed or denied
        is_redeemed = RedeemedGiftCard.objects.filter(code=gift_card_code).exists()
        if is_redeemed:
            raise ValidationError({'detail': 'This gift card has already been redeemed or is invalid.'})
        
        # add to the gift card order table
        card = RedeemedGiftCard.objects.create(
            giftcard_type=gc_type,
            code=gift_card_code,
            amount_claimed=amount,  # Amount will be set by admin after successfully redeeming card
            amount_confirmed=0,
            redeemed_by=request.user,
            redeemed_at=timezone.now(),
            exchange_rate=gc_type.exchange_rate,
            status='pending'
        )

        # Send email notification to user about order being processed
        try:
            send_email.delay(
                subject="Processing Order",
                template_name="emails/giftcard_redemption_order_placed.html",
                context={"order_id": card.id, "type": gc_type.name, "amount_claim":amount},
                recipient_list=[request.user.email],
            )
        except Exception as e:
            logger.error(f"Error sending notification email: {e}", exc_info=True)

        #nofity admin for manual verification
        try:
            send_email.delay(
                subject="New Gift Card Redemption Request",
                template_name="emails/admin_giftcardredemption.html",
                context={"order_id": card.id, "type": gc_type.name},
                recipient_list=[config("EMAIL_HOST_USER")],
            )
        except Exception as e:
            logger.error(f"Error sending admin notification for gift card redemption: {e}", exc_info=True)

        return Response('Please wait, the gift card is being verified.', status=status.HTTP_200_OK)

class RedeemedGiftCardListView(StandardResponseView, generics.ListAPIView):
    """
    API view to list all redeemed gift cards for the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RedeemedGiftCardSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return RedeemedGiftCard.objects.filter(redeemed_by=self.request.user).order_by('-redeemed_at')


class GiftCardsListView(StandardResponseView, generics.ListAPIView):
    """
    API view to list all active gift card types.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = GiftCardsSerializer  # You may want to create a separate serializer for GiftCardType
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return GiftCard.objects.filter(redeemed_by=self.request.user.email).order_by('redeemed_at')


class GiftCardTypesListView(StandardResponseView, generics.ListAPIView):
    """
    API view to list all active gift card types.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = GiftCardTypeSerializer  # You may want to create a separate serializer for GiftCardType
    # pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return GiftCardType.objects.filter(is_active=True).order_by('name')
    

class BuyGiftCardView(StandardResponseView):
    """
    API view to buy a gift card.
    """
    permission_classes = [IsAuthenticated]
    success_message = "Gift card purchase successful."

    def post(self, request, *args, **kwargs):
        gift_card_type_id = request.data.get('type')
        amount = request.data.get('amount')

        # payment info
        channel = request.data.get('channel')
        account_number = request.data.get('account_number')

        if not gift_card_type_id:
            raise ValidationError({'detail': 'Gift card type is required.'})
        
        gc_type = get_object_or_404(GiftCardType, pk=gift_card_type_id)

        if not gc_type or not gc_type.is_active:
            raise ValidationError({'detail': 'Invalid or inactive gift card type.'})

        if amount not in gc_type.denominations:
            raise ValidationError({'detail': 'Invalid denomination for selected gift card type.'})

        if channel not in ['wallet']: # 'mobile_money'
            raise ValidationError({'detail': 'Invalid payment channel.'})
        
        if channel == 'mobile_money' and not account_number:
            raise ValidationError({'detail': 'Account number is required for mobile money payments.'})

        # Check for available gift cards of the selected type and amount
        gift_card = GiftCard.objects.filter(
            giftcard_type=gc_type,
            amount=amount,
            is_redeemed=False
        ).first()

        if not gift_card:
            raise ValidationError({'detail': 'No available gift cards for the selected type and amount.'})

        # Process payment
        if channel == 'wallet':
            # Check if user has sufficient balance in wallet
            wallet_account = request.user.account.fiat()
            if not wallet_account or wallet_account.balance < amount:
                raise ValidationError({'detail': 'Insufficient balance in wallet.'})
            # Deduct amount from wallet
            wallet_account.transfer(
                destination_account=Account.get_sys_revenue_account(),
                amount=amount,
                performed_by=request.user,
                description={f'Purchase of {gc_type.name} gift card'}
            )

        # Mark the gift card as redeemed
        gift_card.is_redeemed = True
        gift_card.redeemed_by = request.user.email
        gift_card.redeemed_at = timezone.now()
        gift_card.save()

        serializer = GiftCardsSerializer(instance=gift_card)
        print( serializer.data)
        return Response( serializer.data, status=status.HTTP_200_OK)
