from rest_framework import serializers
from giftcards.models.giftcard import RedeemedGiftCard


class RedeemedGiftCardSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = RedeemedGiftCard
        fields = [
            'id',
            'giftcard_type',
            'code',
            'amount',
            'redeemed_at',
            'status',
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Hide amount if status is pending or failed
        if instance.status in ['pending', 'failed']:
            data.pop('amount', None)

        return data
