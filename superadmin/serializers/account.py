from main.models.account import AccountTransaction
from rest_framework import serializers
from decimal import Decimal
from .models import Account

class AccountSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)  # or serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Account
        fields = [
            "id",
            "account_number",
            "owner",
            "balance",
            "currency",
            "limit_per_transaction",
            "daily_transfer_limit",
            "monthly_transfer_limit",
            "transfer_allowed",
            "metadata",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "account_number", "owner", "balance", "currency", "metadata", "created_at", "updated_at"]

    def validate_limit_per_transaction(self, value):
        if value <= 0:
            raise serializers.ValidationError("Limit per transaction must be positive.")
        return value

    def validate_daily_transfer_limit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Daily transfer limit must be positive.")
        return value

    def validate_monthly_transfer_limit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Monthly transfer limit must be positive.")
        return value

    def validate(self, attrs):
        # Ensure limits make sense
        daily = attrs.get("daily_transfer_limit", getattr(self.instance, "daily_transfer_limit", None))
        monthly = attrs.get("monthly_transfer_limit", getattr(self.instance, "monthly_transfer_limit", None))
        if daily and monthly and daily > monthly:
            raise serializers.ValidationError("Daily transfer limit cannot exceed monthly transfer limit.")
        return attrs


class TransactionSerializer(serializers.ModelSerializer):
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    destination_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), required=False, allow_null=True
    )
    performed_by = serializers.StringRelatedField(read_only=True)  # Or PrimaryKeyRelatedField if you prefer
    currency = serializers.ChoiceField(choices=Account.CURRENCY_CHOICES)
    
    class Meta:
        model = AccountTransaction
        fields = [
            "id",
            "account",
            "destination_account",
            "external_party_details",
            "transaction_type",
            "direction",
            "amount",
            "status",
            "performed_by",
            "description",
            "fee",
            "metadata",
            "currency",
        ]
        read_only_fields = fields

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Transaction amount must be positive.")
        return value

    def validate_fee(self, value):
        if value < 0:
            raise serializers.ValidationError("Fee cannot be negative.")
        return value

    def validate(self, attrs):
        account = attrs.get("account")
        dest_account = attrs.get("destination_account")
        currency = attrs.get("currency")

        if dest_account and account == dest_account:
            raise serializers.ValidationError("Source and destination accounts cannot be the same.")

        # Optional: Check if the currency matches account currency
        if account and currency != account.currency:
            raise serializers.ValidationError("Transaction currency must match source account currency.")

        if dest_account and dest_account.currency != currency:
            # This allows cross-currency but you might enforce rules if needed
            raise serializers.ValidationError("Transaction currency must match source account currency.")

        return attrs
    
    def create(self, validated_data):
        # Ensure that transactions are created via business logic, not directly
        raise NotImplementedError("Direct creation of transactions is not allowed. Use account methods instead.")
    
    def update(self, instance, validated_data):
        # Transactions are immutable; prevent updates
        raise NotImplementedError("Transactions cannot be updated once created.")
    
    def delete(self, instance):
        # Transactions cannot be deleted
        raise NotImplementedError("Transactions cannot be deleted.")
    