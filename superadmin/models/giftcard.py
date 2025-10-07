from django.db import models

from common.models.common import TimeStampedModel
import uuid

# Create your models here.

CATEGORY_CHOICES = [
    ('ELECTRONICS', 'Electronics'),
    ('FASHION', 'Fashion'),
    ('GROCERY', 'Grocery'),
    ('TRAVEL', 'Travel'),
    ('ENTERTAINMENT', 'Entertainment'),
    ('HEALTH', 'Health & Wellness'),
    ('FOOD', 'Food & Dining'),
    ('HOME', 'Home & Living'),
    ('SPORTS', 'Sports & Outdoors'),
    ('BEAUTY', 'Beauty & Personal Care'),
    ('E-COMMERCE', 'E-commerce'),
]

class GiftCardType(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    desc = models.CharField(max_length=255)
    denominations = models.JSONField(default=list)  # List of available denominations
    category = models.CharField(choices=CATEGORY_CHOICES)
    exchange_rate = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    is_active = models.BooleanField(default=True)


class GiftCard(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    giftcard_type = models.ForeignKey(GiftCardType, on_delete=models.CASCADE, related_name='giftcards')
    code = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_redeemed = models.BooleanField(default=False)
    redeemed_by = models.EmailField(null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Giftcard {self.code} - Amount: {self.amount} - Redeemed: {self.is_redeemed}"