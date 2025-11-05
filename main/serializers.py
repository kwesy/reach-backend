from decimal import Decimal
from rest_framework import serializers
from django.db import transaction
from .models import FiatAccount, AccountTransaction


NETWORK_CHOICES = (
    ('MTN', 'MTN'),
    ('TELECEL', 'Telecel'),
    ('AIRTELTIGO', 'AirtelTigo')
)

class DepositFundsSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        required=True,
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.10"),
        help_text="Amount to deposit"
    )
    phone_number = serializers.CharField(
        required=True,
        max_length=15,
    )
    network = serializers.ChoiceField(
        required=True,
        choices=NETWORK_CHOICES
    )

    def validate(self, attrs):
        account = self.context.get("account")
        if not account:
            raise serializers.ValidationError("Account not provided or does not exist")
        if account.account_role not in ["user", "asset"]:
            raise serializers.ValidationError("Invalid account type for deposit.")
        return attrs

    def create(self, validated_data):
        account = self.context["account"]
        user = self.context["user"]

        amount = validated_data["amount"]
        validated_data["amount"] = str(amount)

        tx = account.deposit(
            amount=amount,
            direction="mobile_money_to_account",
            performed_by=user,
            metadata= {'customer': validated_data}
        )

        # DRF expects this to be a model instance (or equivalent)
        return tx

class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = AccountTransaction
        fields = [
            'reference_id',
            'transaction_type',
            'direction',
            'amount',
            'status',
            'currency',
            'description',
            'created_at',
        ]
        read_only_fields = fields
