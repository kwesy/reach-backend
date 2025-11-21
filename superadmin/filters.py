# filters.py
import django_filters
from giftcards.models.giftcard import RedeemedGiftCard
from main.models import AccountTransaction
from main.models.account import Account

class TransactionFilter(django_filters.FilterSet):
    # Exact match for the account number field (assumes a field path)
    status = django_filters.CharFilter(
        field_name="status", 
        lookup_expr='exact'
    )

    # Case-insensitive contains search for transaction_type
    type = django_filters.CharFilter(
        field_name="transaction_type", 
        # lookup_expr='icontains'
        lookup_expr='exact'
    )

    class Meta:
        model = AccountTransaction
        fields = ['status', 'type']

class AdminAccountFilter(django_filters.FilterSet):
    active = django_filters.BooleanFilter(field_name="is_active")
    transfer_allowed = django_filters.BooleanFilter(field_name="transfer_allowed")

    category = django_filters.CharFilter(
        field_name="account_role", 
        lookup_expr='exact'
    )

    class Meta:
        model = Account
        fields = ['active', 'category', 'transfer_allowed']

class GiftcardOrdersFilter(django_filters.FilterSet):
    type = django_filters.CharFilter(field_name="giftcard_type")
    status = django_filters.CharFilter(
        field_name="status", 
        lookup_expr='exact'
    )

    class Meta:
        model = RedeemedGiftCard
        fields = ['type', 'status']
