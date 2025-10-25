from rest_framework import serializers
from giftcards.models.giftcard import GiftCard, GiftCardType, RedeemedGiftCard
from django.db import models


class GiftCardTypeSerializer(serializers.ModelSerializer):
    revenue = serializers.SerializerMethodField(read_only=True)
    codes_available = serializers.SerializerMethodField(read_only=True)
    codes_redeemed = serializers.SerializerMethodField(read_only=True)

    def get_revenue(self, obj):
        return obj.giftcards.filter(is_redeemed=True).aggregate(total=models.Sum('amount'))['total'] or 0
    
    def get_codes_available(self, obj):
        return obj.giftcards.filter(is_redeemed=False).count()
    
    def get_codes_redeemed(self, obj):
        return obj.giftcards.filter(is_redeemed=True).count()

    class Meta:
        model = GiftCardType
        # fields = [
        #     'id',
        #     'name',
        #     'desc',
        #     'denominations',  # JSONField: list of values
        #     'category',
        #     'is_active',
        #     'created_at',
        #     'updated_at',
        #     'revenue',
        #     'codes_available',
        #     'codes_redeemed',
        # ]
        fields = '__all__'
        read_only_fields = ['id']

class GiftCardSerializer(serializers.ModelSerializer):
    giftcard_type = serializers.SerializerMethodField(read_only=True)
    giftcard_type_id = serializers.PrimaryKeyRelatedField(
        queryset=GiftCardType.objects.all(),
        source='giftcard_type',
        write_only=True
    )

    def get_giftcard_type(self, obj):
        return {
            'id': str(obj.giftcard_type.id),
            'name': obj.giftcard_type.name,
            'desc': obj.giftcard_type.desc,
            'category': obj.giftcard_type.category,
            'is_active': obj.giftcard_type.is_active,
        }

    class Meta:
        model = GiftCard
        fields = [
            'id',
            'giftcard_type',
            'giftcard_type_id',
            'code',
            'amount',
            'is_redeemed',
            'redeemed_by',
            'redeemed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'giftcard_type']

    def validate(self, data):
        giftcard_type = data.get('giftcard_type') or self.instance.giftcard_type
        amount = data.get('amount')

        if not giftcard_type.is_active:
            raise serializers.ValidationError({
                'giftcard_type': "The selected gift card type is inactive."
            })

        if giftcard_type and amount is not None:
            valid_denominations = giftcard_type.denominations
            # Convert to float or decimal if necessary to match amount type
            if float(amount) not in [float(d) for d in valid_denominations]:
                raise serializers.ValidationError({
                    'amount': f"Amount must be one of the allowed denominations: {valid_denominations}"
                })

        return data

class RedeemedGiftCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedeemedGiftCard
        fields = '__all__'

    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        instance.amount_confirmed = validated_data.get('amount_confirmed', instance.amount_confirmed)
        instance.save()
        return instance
