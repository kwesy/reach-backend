from rest_framework import serializers
from giftcards.models.giftcard import GiftCard, GiftCardType, RedeemedGiftCard


class RedeemedGiftCardSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = RedeemedGiftCard
        fields = [
            'id',
            'giftcard_type',
            'code',
            'amount_claimed',
            'amount_confirmed',
            'exchange_rate',
            'redeemed_at',
            'status',
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Hide amount if status is pending or failed
        if instance.status in ['pending', 'failed']:
            data.pop('amount_confirmed', None)

        if instance.redeemed_by:
            data['redeemed_by'] = {
                'id': str(instance.redeemed_by.id),
                'email': instance.redeemed_by.email,
            }

        return data
    

class GiftCardsSerializer(serializers.ModelSerializer):
    giftcard_type = serializers.SerializerMethodField()

    def get_giftcard_type(self, obj):
        return {
            'id': str(obj.giftcard_type.id),
            'name': obj.giftcard_type.name,
        }

    class Meta:
        model = GiftCard
        fields = [
            'id',
            'giftcard_type',
            'code',
            'amount',
            'redeemed_at',
        ]


class GiftCardTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCardType
        fields = [
            'id',
            'name',
            'desc',
            'denominations',
            'category',
            'is_active',
            'exchange_rate',
        ]
