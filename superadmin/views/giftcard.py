from rest_framework import viewsets
from superadmin.models import GiftCard, GiftCardType
from superadmin.serializers import GiftCardSerializer, GiftCardTypeSerializer
from oauth.permissions import IsAdmin, IsAdminOrReadOnly

class GiftCardTypeViewSet(viewsets.ModelViewSet):
    queryset = GiftCardType.objects.all()
    serializer_class = GiftCardTypeSerializer
    permission_classes = [IsAdmin]

class GiftCardViewSet(viewsets.ModelViewSet):
    queryset = GiftCard.objects.all()
    serializer_class = GiftCardSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['giftcard_type', 'redeemed_by']
