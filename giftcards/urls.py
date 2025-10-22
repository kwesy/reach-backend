from django.urls import path

from giftcards.views import RedeemGiftCardView, RedeemedGiftCardListView


app_name = 'giftcards'

urlpatterns = [
    path('redeem/', RedeemGiftCardView.as_view(), name='redeem-gift-card'),
    path('redeemed/', RedeemedGiftCardListView.as_view(), name='redeemed-gift-card'),
]
