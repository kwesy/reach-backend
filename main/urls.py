from django.urls import path
from main.views import DepositView, DepositWebHookView, TransactionView, WithdrawView



app_name = 'oauth'

urlpatterns = [
    # path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('accounts/deposit', DepositView.as_view(), name='deposit'),
    path('accounts/withdraw', WithdrawView.as_view(), name='withdraw'),
    path('transactions/', TransactionView.as_view(), name='transactions'),
    
    
    #  Webhooks
    path('webhooks/bulkclix/gc/<uuid:transaction_id>', DepositWebHookView.as_view(), name='confirm-deposit-wh')
]