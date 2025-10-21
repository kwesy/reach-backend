from django.urls import path

from giftcards.views import RedeemGiftCardView


app_name = 'superadmin'

urlpatterns = [
    path('redeem/', RedeemGiftCardView.as_view(), name='redeem-gift-card'),
]