from django.urls import path
from django.urls import include
from rest_framework.routers import DefaultRouter
from superadmin.views import LoginView, GiftCardTypeViewSet, GiftCardViewSet


app_name = 'superadmin'
router = DefaultRouter()

router.register(r'giftcard-types', GiftCardTypeViewSet, basename='giftcardtype')
router.register(r'giftcards', GiftCardViewSet, basename='giftcard')

urlpatterns = [
    path('login/', LoginView.as_view(), name='admin-login'),

    # gift cards
    path('', include(router.urls)),
]