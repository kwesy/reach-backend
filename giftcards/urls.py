from django.urls import path

from giftcards.views import GiftCardsListView, RedeemGiftCardView, RedeemedGiftCardListView


app_name = 'giftcards'

urlpatterns = [
    path('', GiftCardsListView.as_view(), name='user-owned-gift-cards-list'),
    path('redeem/', RedeemGiftCardView.as_view(), name='redeem-gift-card'),
    path('redeemed/', RedeemedGiftCardListView.as_view(), name='redeemed-gift-card'),
]
