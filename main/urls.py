from django.urls import path
from main.views import DepositView, DepositWebHookView



app_name = 'oauth'

urlpatterns = [
    # path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('accounts/deposit', DepositView.as_view(), name='deposit'),
    
    
    #  Webhooks
    path('webhooks/bulkclix/gc/<uuid:transaction_id>', DepositWebHookView.as_view(), name='confirm-deposit-wh')
]