from django.shortcuts import render
from giftcards.models.giftcard import GiftCard, GiftCardType, RedeemedGiftCard
from giftcards.serializers import RedeemedGiftCardSerializer
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
            amount=0,  # Amount will be set by admin after successfully redeeming card
            redeemed_by=request.user,
            redeemed_at=timezone.now(),
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

    def get_queryset(self):
        return RedeemedGiftCard.objects.filter(redeemed_by=self.request.user).order_by('-redeemed_at')
