from rest_framework import serializers
from main.models import AccountTransaction


class AdminTransactionSerializer(serializers.ModelSerializer):
    account = serializers.SerializerMethodField()
    destination_account = serializers.SerializerMethodField()
    performed_by = serializers.CharField(source='performed_by.email', read_only=True)
    
    def get_account(self, instance):
        return {
            "account_number": instance.account.account_number,
            "name:": instance.account.owner.get_full_name(),
            "email": instance.account.owner.email,
        }
    
    def get_destination_account(self, instance):
        return instance.destination_account and instance.destination_account.account_number
    
    class Meta:
        model = AccountTransaction
        fields = '__all__'
