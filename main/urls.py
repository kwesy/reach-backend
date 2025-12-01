from django.urls import path
from main.views import DepositView, DepositWebHookView, TransactionView, WithdrawView
from main.views.dashboard import DashboardView



app_name = 'oauth'

urlpatterns = [
    path('assets', DashboardView.as_view(), name='dashboard'),
    path('accounts/deposit', DepositView.as_view(), name='deposit'),
    path('accounts/withdraw', WithdrawView.as_view(), name='withdraw'),
    path('transactions/', TransactionView.as_view(), name='transactions'),
    
    
    #  Webhooks
    path('webhooks/bulkclix/gc/<uuid:transaction_id>', DepositWebHookView.as_view(), name='confirm-deposit-wh')
]