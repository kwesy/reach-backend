# filters.py
import django_filters
from main.models import AccountTransaction

class TransactionFilter(django_filters.FilterSet):
    # Exact match for the account number field (assumes a field path)
    account_number = django_filters.CharFilter(
        field_name="account__account_number", 
        lookup_expr='exact'
    )

    # Case-insensitive contains search for transaction_type
    type = django_filters.CharFilter(
        field_name="transaction_type", 
        lookup_expr='icontains'
    )

    class Meta:
        model = AccountTransaction
        fields = ['account_number', 'type']
