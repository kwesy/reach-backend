from django.urls import path
from django.urls import include
from rest_framework.routers import DefaultRouter
from superadmin.views import LoginView, GiftCardTypeViewSet, GiftCardViewSet
from superadmin.views.giftcard import RedeemedGiftCardView
from superadmin.views.user import AdminUserViewSet
from superadmin.views.account import AdminAllCryptoAccountViewSet, AdminAllFiatAccountViewSet

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

    # redeem gift cards 
    path('redeemed-giftcards', RedeemedGiftCardView.as_view(), name='admin-redeemed-giftcards'),
    path('redeemed-giftcards/<uuid:pk>', RedeemedGiftCardView.as_view(), name='admin-redeemed-giftcards'),
]