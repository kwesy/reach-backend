from django.urls import path
from django.urls import include
from rest_framework.routers import DefaultRouter
from superadmin.views import LoginView, GiftCardTypeViewSet, GiftCardViewSet
from superadmin.views.giftcard import RedeemedGiftCardView
from superadmin.views.user import AdminUserViewSet
from superadmin.views.account import AdminAllCryptoAccountViewSet, AdminAllFiatAccountViewSet
from superadmin.views.dashboard import AdminDashboardView
from superadmin.views.transactions import AdminTransactionView


app_name = 'superadmin'
router = DefaultRouter()

router.register(r'giftcard-types', GiftCardTypeViewSet, basename='admin-giftcardtype')
router.register(r'giftcards', GiftCardViewSet, basename='admin-giftcard')
router.register(r'users', AdminUserViewSet, basename='admin-user')
router.register(r'fiataccounts', AdminAllFiatAccountViewSet, basename='admin-fiataccount')
router.register(r'cryptoaccounts', AdminAllCryptoAccountViewSet, basename='admin-cryptoaccount')

urlpatterns = [
    path('login/', LoginView.as_view(), name='admin-login'),
    path('', include(router.urls)),

    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('transactions/', AdminTransactionView.as_view(), name='admin-transactions'),

    # redeem gift cards 
    path('redeemed-giftcards-orders', RedeemedGiftCardView.as_view(), name='admin-redeem-giftcards-orders'), # view all user redeemed gift cards
    path('redeem/<uuid:pk>', RedeemedGiftCardView.as_view(), name='admin-approve/reject-giftcards'), # admin to approve/reject
]