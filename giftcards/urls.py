from django.urls import path

from giftcards.views import BuyGiftCardView, GiftCardTypesListView, GiftCardsListView, RedeemGiftCardView, RedeemedGiftCardListView


app_name = 'giftcards'

urlpatterns = [
    path('', GiftCardsListView.as_view(), name='user-owned-gift-cards-list'),
    path('types', GiftCardTypesListView.as_view(), name='gift-card-types-list'),
    path('purchase', BuyGiftCardView.as_view(), name='buy-gift-card'),
    path('redeem/', RedeemGiftCardView.as_view(), name='redeem-gift-card'),
    path('redeemed/', RedeemedGiftCardListView.as_view(), name='redeemed-gift-card'),
]
