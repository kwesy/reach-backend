from main.models.account import AccountTransaction, CryptoAccount, FiatAccount
from rest_framework import serializers
from main.models import Account


class AdminAccountSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)  # or serializers.PrimaryKeyRelatedField(read_only=True)
    account_type = serializers.SerializerMethodField()

    def get_account_type(self, obj):
        return obj.get_account_type()
    
    class Meta:
        model = Account
        fields = [
            # "id",
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
            "account_type",
        ]
        # read_only_fields = ["id", "account_number", "owner", "balance", "currency", "wallet", "blockchain_network", "metadata", "created_at", "updated_at"]
        read_only_fields = fields # nothing can be changed via this serializers

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
    
    def update(self, instance, validated_data):
        # Since all fields are read-only, we prevent updates
        raise NotImplementedError("Accounts cannot be updated via this serializer.")

    def delete(self, instance):
        raise NotImplementedError("Accounts cannot be deleted via this serializer.")
    

class AdminFiatAccountSerializer(AdminAccountSerializer):
    account_type = serializers.CharField(default="fiat")

    class Meta(AdminAccountSerializer.Meta):
        model = FiatAccount
        fields = AdminAccountSerializer.Meta.fields


class AdminCryptoAccountSerializer(AdminAccountSerializer):
    account_type = serializers.CharField(default="crypto")

    class Meta(AdminAccountSerializer.Meta):
        model = CryptoAccount
        fields = AdminAccountSerializer.Meta.fields + ["wallet", "blockchain_network"]


class AdminAccountPolymorphicSerializer(serializers.Serializer):
    def to_representation(self, instance):
        if hasattr(instance, "fiataccount"):
            return AdminFiatAccountSerializer(instance.fiataccount).data
        
        return AdminCryptoAccountSerializer(instance.cryptoaccount).data


class AdminTransactionSerializer(serializers.ModelSerializer):
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

    # def validate_amount(self, value):
    #     if value <= 0:
    #         raise serializers.ValidationError("Transaction amount must be positive.")
    #     return value

    # def validate_fee(self, value):
    #     if value < 0:
    #         raise serializers.ValidationError("Fee cannot be negative.")
    #     return value

    # def validate(self, attrs):
    #     account = attrs.get("account")
    #     dest_account = attrs.get("destination_account")
    #     currency = attrs.get("currency")

    #     if dest_account and account == dest_account:
    #         raise serializers.ValidationError("Source and destination accounts cannot be the same.")

    #     # Optional: Check if the currency matches account currency
    #     if account and currency != account.currency:
    #         raise serializers.ValidationError("Transaction currency must match source account currency.")

    #     if dest_account and dest_account.currency != currency:
    #         # This allows cross-currency but you might enforce rules if needed
    #         raise serializers.ValidationError("Transaction currency must match source account currency.")

    #     return attrs
    
    def create(self, validated_data):
        # Ensure that transactions are created via business logic, not directly
        raise NotImplementedError("Direct creation of transactions is not allowed. Use account methods instead.")
    
    def update(self, instance, validated_data):
        # Transactions are immutable; prevent updates
        raise NotImplementedError("Transactions cannot be updated once created.")
    
    def delete(self, instance):
        # Transactions cannot be deleted
        raise NotImplementedError("Transactions cannot be deleted.")
    