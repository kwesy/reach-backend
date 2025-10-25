from giftcards.models.giftcard import RedeemedGiftCard
from superadmin.serializers.giftcard import RedeemedGiftCardSerializer
from rest_framework import viewsets, generics
from giftcards.models import GiftCard, GiftCardType
from superadmin.serializers import GiftCardSerializer, GiftCardTypeSerializer
from oauth.permissions import IsAdmin, IsAdminOrReadOnly
from common.mixins.response import StandardResponseView

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
