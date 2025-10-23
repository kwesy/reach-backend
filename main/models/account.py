import secrets
import uuid
from decimal import Decimal, ROUND_DOWN
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum
from common.models.common import TimeStampedModel
import logging
from django.db import IntegrityError
from django.core.exceptions import ImproperlyConfigured


logger = logging.getLogger("transactions")

def generate_account_number():
    return ''.join(secrets.choice('0123456789') for _ in range(11))
        


class Account(models.Model):

    CURRENCY_DECIMAL_PLACES = {
        'USD': 2,
        'GHS': 2,
        'BTC': 18,
        'ETH': 18,
        'XRP': 6,
        'LTC': 8,
    }

    CURRENCY_CHOICES = (
        ('GHS', 'Ghana Cedi'),
        ('USD', 'US Dollar'),
        ('BTC', 'Bitcoin'),
        ('ETH', 'Ethereum'),
        ('XRP', 'Ripple'),
        ('LTC', 'Litecoin'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_number = models.CharField(max_length=11, unique=True, editable=False, default=generate_account_number)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="%(class)ss")
    balance = models.DecimalField(max_digits=40, decimal_places=18, default=0)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='USD')
    limit_per_transaction = models.DecimalField(max_digits=40, decimal_places=18, default=Decimal('2000'))  # max per single transaction
    daily_transfer_limit = models.DecimalField(max_digits=40, decimal_places=18, default=Decimal('5000'))
    monthly_transfer_limit = models.DecimalField(max_digits=40, decimal_places=18, default=Decimal('50000'))
    transfer_allowed = models.BooleanField(default=True)
    metadata = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["currency"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.owner} - {self.currency} - Balance: {self.balance}"
    
    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = generate_account_number()

        while True:
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                break  # Success! Exit the loop
            except IntegrityError:
                # Collision happened, generate a new account number and retry
                self.account_number = generate_account_number()

    def to_decimal(self, value):
        if not isinstance(value, Decimal):
            value = Decimal(value)
        return value

    def quantize(self, value):
        if not isinstance(value, Decimal):
            value = Decimal(value)
        decimal_places = self.CURRENCY_DECIMAL_PLACES.get(self.currency, 18)
        precision_str = '1.' + ('0' * decimal_places)
        precision = Decimal(precision_str)
        return value.quantize(precision, rounding=ROUND_DOWN)

    def add_balance(self, amount):
        """
        Safely locks an account row, updates balance,
        and returns the updated account.
        Must be called inside a transaction.atomic() block.
        """
        # Ensure we are inside an atomic transaction
        if not transaction.get_connection().in_atomic_block:
            raise ImproperlyConfigured(
                "add_balance() must be called inside a transaction.atomic() block."
            )
    
        amount = self.quantize(amount)
        # lock row for safe update
        locked_account = Account.objects.select_for_update().get(pk=self.pk)
        locked_account.balance = self.quantize(locked_account.balance + amount)
        locked_account.save()
        return locked_account.balance

    def subtract_balance(self, amount):
        """
        Safely locks an account row, updates balance,
        and returns the updated account.
        Must be called inside a transaction.atomic() block.
        """
        # Ensure we are inside an atomic transaction
        if not transaction.get_connection().in_atomic_block:
            raise ImproperlyConfigured(
                "subtract_balance() must be called inside a transaction.atomic() block."
            )
        
        amount = self.quantize(amount)
        # lock row for safe update
        locked_account = Account.objects.select_for_update().get(pk=self.pk)
        if locked_account.balance - amount < 0:
            raise ValueError("Balance cannot go negative.")
        locked_account.balance = self.quantize(locked_account.balance - amount)
        locked_account.save()
        return locked_account.balance

    def get_daily_transferred_amount(self):
        today = timezone.now().date()
        total = self.sent_transactions.filter(
            created_at__date=today,
            status='completed',
            transaction_type='transfer'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return self.quantize(total)

    def get_monthly_transferred_amount(self):
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        total = self.sent_transactions.filter(
            created_at__date__gte=start_of_month,
            status='completed',
            transaction_type='transfer'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return self.quantize(total)

    def can_transfer(self, amount):
        amount = self.quantize(amount)
        if not self.transfer_allowed or not self.is_active or not self.owner.is_active:
            return False

        if amount <= 0 or amount > self.balance:
            return False

        daily_total = self.get_daily_transferred_amount()
        monthly_total = self.get_monthly_transferred_amount()
        limit_per_txn = self.quantize(self.limit_per_transaction)

        if daily_total + amount > self.daily_transfer_limit:
            return False
        if monthly_total + amount > self.monthly_transfer_limit:
            return False
        if amount > limit_per_txn:
            return False

        return True

    def transfer(self, amount, destination_account, direction, performed_by=None, description="Transfer"):
        amount = self.quantize(amount)

        if not self.can_transfer(amount):
            raise ValueError("Transfer amount exceeds limits or insufficient balance or transfers disabled.")

        if not destination_account or not destination_account.is_active:
            raise ValueError("Invalid or inactive destination account.")

        if self.currency != destination_account.currency:
            raise ValueError("Currency mismatch between source and destination accounts.")

        try:
            # Ensure atomicity of balance updates and transaction creation
            with transaction.atomic():
                # Lock both accounts for update to avoid race conditions
                sender_account = Account.objects.select_for_update().get(pk=self.pk)
                recipient_account = Account.objects.select_for_update().get(pk=destination_account.pk)

                sender_account.subtract_balance(amount)
                sender_account.save()

                recipient_account.add_balance(amount)
                recipient_account.save()

                AccountTransaction.objects.create(
                    account=sender_account,
                    destination_account=recipient_account,
                    transaction_type='transfer',
                    amount=amount,
                    status='completed',
                    performed_by=performed_by,
                    description=description,
                    direction=direction,
                )
        except Exception as e:
            logger.error("Transfer failed: %s", str(e), exc_info=True)
            AccountTransaction.objects.create(
                account=sender_account,
                destination_account=recipient_account,
                transaction_type='transfer',
                amount=amount,
                status='failed',
                performed_by=performed_by,
                description=f"{description} - Failed: {str(e)}",
            )
            raise e

    def deposit(self, amount, direction, external_details=None, performed_by=None, description="Deposit"):
        amount = self.quantize(amount)
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")

        try:
            with transaction.atomic():
                self.add_balance(amount)
                self.save()

                AccountTransaction.objects.create(
                    account=self,
                    transaction_type='deposit',
                    amount=amount,
                    status='completed',
                    performed_by=performed_by,
                    external_party_details=external_details,
                    description=description,
                    direction=direction,
                )
        except:
            logger.error("Deposit failed for account %s", self.account_number, exc_info=True)
            AccountTransaction.objects.create(
                account=self,
                transaction_type='deposit',
                amount=amount,
                status='completed',
                performed_by=performed_by,
                external_party_details=external_details,
                description=description,
                direction=direction,
            )
            raise

    def withdraw(self, amount, direction, external_details=None, performed_by=None, description="Withdrawal", auto_complete=True):
        amount = self.quantize(amount)

        if not self.transfer_allowed or not self.is_active:
            raise ValueError("Withdrawals are not allowed for this account.")

        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero.")

        if amount > self.balance:
            raise ValueError("Insufficient balance.")

        daily_total = self.get_daily_transferred_amount()
        monthly_total = self.get_monthly_transferred_amount()
        limit_per_txn = self.quantize(self.limit_per_transaction)

        if daily_total + amount > self.daily_transfer_limit:
            raise ValueError("Daily transfer limit exceeded.")

        if monthly_total + amount > self.monthly_transfer_limit:
            raise ValueError("Monthly transfer limit exceeded.")

        if amount > limit_per_txn:
            raise ValueError("Withdrawal amount exceeds single transaction limit.")

        with transaction.atomic():
            
            if auto_complete:
                self.subtract_balance(amount)
                self.save()
                status = 'completed'
            else:
                status = 'pending'

            AccountTransaction.objects.create(
                account=self,
                transaction_type='withdrawal',
                amount=amount,
                status=status,
                performed_by=performed_by,
                external_party_details=external_details,
                description=description,
                direction=direction,
            )


class FiatAccount(Account):
    pass


class CryptoAccount(Account):
    wallet = models.CharField(max_length=255)
    blockchain_network = models.CharField(max_length=100)


class AccountTransaction(TimeStampedModel):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
        ('adjustment', 'Adjustment'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    TRANSACTION_DIRECTIONS = (
        ('bank_to_account', 'Bank to Account'),
        ('account_to_bank', 'Account to Bank'),
        ('account_to_mobile_money', 'Account to Mobile Money'),
        ('mobile_money_to_account', 'Mobile Money to Account'),
        ('wallet_to_wallet', 'Wallet to Wallet'),
        ('fiat_to_crypto', 'Fiat to Crypto'),
        ('crypto_to_fiat', 'Crypto to Fiat'),
        ('crypto_swap', 'Crypto Swap'),
    )

    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='sent_transactions')
    destination_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='received_transactions'
    )
    external_party_details = models.JSONField(null=True, blank=True)

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    direction = models.CharField(max_length=30, choices=TRANSACTION_DIRECTIONS, null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    performed_by = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='transactions')
    description = models.CharField(max_length=255, blank=True)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type.title()} of {self.amount} on {self.account} ({self.status})"
