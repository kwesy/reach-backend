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
from django.core.exceptions import ImproperlyConfigured, ValidationError

from oauth.models.user import User


logger = logging.getLogger("transactions")

def generate_account_number():
    return ''.join(secrets.choice('0123456789') for _ in range(11))

class AccountManager(models.Manager):
    def fiat(self, currency='USD'):
        """Returns the first fiat account associated with the user."""
        return self.filter(fiataccount__isnull=False, currency=currency).first()

    def crypto(self, currency='BTC'):
        """Returns the first crypto account associated with the user."""
        return self.filter(cryptoaccount__isnull=False, currency=currency).first()
    

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

    ACCOUNT_ROLE = (
        ('asset', 'Asset'), # platform's cash accounts are assets
        ('user', 'User (Liability)'), # users' balances are liabilities to the platform
        ('revenue', 'Revenue'), # platform's revenue accounts
        ('expenses', 'Expenses'), # platform's expense accounts
        ('suspense', 'Suspense'), # temporary holding accounts
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_number = models.CharField(max_length=11, unique=True, editable=False, default=generate_account_number)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="%(class)s")
    balance = models.DecimalField(max_digits=40, decimal_places=18, default=0)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    limit_per_transaction = models.DecimalField(max_digits=40, decimal_places=18, default=Decimal('2000'))  # max per single transaction
    daily_transfer_limit = models.DecimalField(max_digits=40, decimal_places=18, default=Decimal('5000'))
    monthly_transfer_limit = models.DecimalField(max_digits=40, decimal_places=18, default=Decimal('50000'))
    transfer_allowed = models.BooleanField(default=True)
    metadata = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    account_role = models.CharField(max_length=10, choices=ACCOUNT_ROLE, default='user')

    class Meta:
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["currency"]),
            models.Index(fields=["is_active"]),
        ]

    objects = AccountManager()

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

    @classmethod
    def get_sys_account(cls, currency='USD'):
        """Returns the platform's main account for the specified currency."""
        return cls.objects.filter(fiataccount__isnull=False, currency=currency, owner__role='sys', account_role='asset').first()
    
    @classmethod
    def get_sys_revenue_account(cls, currency='USD'):
        """Returns the platform's revenue account for the specified currency."""
        return cls.objects.filter(fiataccount__isnull=False, currency=currency, owner__role='sys', account_role='revenue').first()
    
    @classmethod
    def get_sys_suspense_account(cls, currency='USD'):
        """Returns the platforms's suspense account for the specified currency."""
        return cls.objects.filter(fiataccount__isnull=False, currency=currency, owner__role='sys', account_role='suspense').first()

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
        self.refresh_from_db(fields=['balance'])
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
        self.refresh_from_db(fields=['balance'])
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
    
    def credit_account(self, amount, description="adjust-up", performed_by=None):
        """Credits the account with the specified amount and records the transaction."""
        amount = self.quantize(amount)
        if amount <= 0:
            raise ValueError("Credit amount must be positive.")

        try:
            with transaction.atomic():
                self.add_balance(amount)

                AccountTransaction.objects.record(
                    account=self,
                    destination_account=self,
                    transaction_type='adjustment',
                    amount=amount,
                    status='completed',
                    performed_by=performed_by,
                    description=description,
                    direction=None,
                    currency=self.currency,
                    metadata={},
                    fee=Decimal('0'),
                )
        except Exception as e:
            logger.error("Credit failed for account %s: %s", self.account_number, str(e), exc_info=True)
            AccountTransaction.objects.create(
                account=self,
                destination_account=self,
                transaction_type='adjustment',
                amount=amount,
                status='failed',
                performed_by=performed_by,
                description=f"{description} - Failed: {str(e)}",
                direction=None,
                currency=self.currency,
                metadata={},
                fee=Decimal('0'),
            )
            raise e
        
    def debit_account(self, amount, description="adjust-down", performed_by=None):
        """Debits the account with the specified amount and records the transaction."""
        amount = self.quantize(amount)
        if amount <= 0:
            raise ValueError("Debit amount must be positive.")

        if amount > self.balance:
            raise ValueError("Insufficient balance for debit.")

        try:
            with transaction.atomic():
                self.subtract_balance(amount)

                AccountTransaction.objects.record(
                    account=self,
                    destination_account=self,
                    transaction_type='adjustment',
                    amount=-amount, # negative amount for debit
                    status='completed',
                    performed_by=performed_by,
                    description=description,
                    direction=None,
                    currency=self.currency,
                    metadata={},
                    fee=Decimal('0'),
                )
        except Exception as e:
            logger.error("Debit failed for account %s: %s", self.account_number, str(e), exc_info=True)
            AccountTransaction.objects.create(
                account=self,
                destination_account=self,
                transaction_type='adjustment',
                amount=amount,
                status='failed',
                performed_by=performed_by,
                description=f"{description} - Failed: {str(e)}",
                direction=None,
                currency=self.currency,
                metadata={},
                fee=Decimal('0'),
            )
            raise e
        
    def charge_fee(self, fee_amount, description="Withdrawal Fee", performed_by=None) -> 'AccountTransaction':
        """Charges a fee from the account and credits it to the platform revenue account."""
        fee_amount = self.quantize(fee_amount)
        if fee_amount <= 0:
            raise ValueError("Fee amount must be positive.")

        if fee_amount > self.balance:
            raise ValueError("Insufficient balance to charge fee.")

        revenue_account = Account.get_sys_revenue_account(currency=self.currency)
        if not revenue_account:
            raise ValueError("Platform revenue account not found.")

        try:
            with transaction.atomic():
                self.subtract_balance(fee_amount)

                revenue_account.add_balance(fee_amount)

                tx = AccountTransaction.objects.record(
                    account=self,
                    destination_account=revenue_account,
                    transaction_type='fee',
                    amount=fee_amount,
                    status='completed',
                    performed_by=performed_by,
                    description=description,
                    direction=None,
                    currency=self.currency,
                    metadata={},
                    fee=Decimal('0'),
                )
                return tx
            
        except Exception as e:
            logger.error("Fee charge failed for account %s: %s", self.account_number, str(e), exc_info=True)
            raise e

    def transfer(self, amount, destination_account, performed_by=None, description="Transfer"):
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

                recipient_account.add_balance(amount)

                AccountTransaction.objects.record(
                    account=sender_account,
                    destination_account=recipient_account,
                    transaction_type='transfer',
                    amount=amount,
                    status='completed',
                    performed_by=performed_by,
                    description=description,
                    direction='wallet_to_wallet',
                    currency=self.currency,
                    metadata={},
                    fee=Decimal('0'),
                    external_party_details={},
                )
        except Exception as e:
            logger.error("Transfer failed for %s: %s", self.account_number, str(e), exc_info=True)
            AccountTransaction.objects.create(
                account=sender_account,
                destination_account=recipient_account,
                transaction_type='transfer',
                amount=amount,
                status='failed',
                performed_by=performed_by,
                description=f"{description} - Failed: {str(e)}",
                direction='wallet_to_wallet',
                currency=self.currency,
                metadata=None,
                fee=Decimal('0'),
                external_party_details=None,
            )
            raise e

    def deposit(self, amount, direction, external_details=None, performed_by=None, description="Deposit", metadata={}, auto_complete=False):
        amount = self.quantize(amount)
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")

        try:
            with transaction.atomic():
                self.add_balance(amount)

                AccountTransaction.objects.record(
                    account=self,
                    destination_account=self,
                    transaction_type='deposit',
                    amount=amount,
                    status='completed' if auto_complete else 'pending',
                    performed_by=performed_by,
                    external_party_details=external_details,
                    description=description,
                    direction=direction,
                    currency=self.currency,
                    metadata=metadata,
                    fee=Decimal('0'),
                )
        except Exception as e:
            logger.error("Deposit failed for account %s: %s", self.account_number, str(e), exc_info=True)
            AccountTransaction.objects.create(
                account=self,
                destination_account=self,
                transaction_type='deposit',
                amount=amount,
                status='failed',
                performed_by=performed_by,
                external_party_details=external_details,
                description=description,
                direction=direction,
                currency=self.currency,
                metadata={},
                fee=Decimal('0'),

            )
            raise e

    def withdraw(self, amount, direction, fee=0.01, external_details=None, performed_by=None, description="Withdrawal", auto_complete=True):
        amount = self.quantize(amount)
        fee = self.quantize(fee)
        external_fee = self.quantize(amount * 0.01) #TODO: calculate external fee properly

        if not self.transfer_allowed or not self.is_active:
            raise ValueError("Withdrawals are not allowed for this account.")

        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero.")

        if amount > self.balance:
            raise ValueError("Insufficient balance.")

        daily_total = self.get_daily_transferred_amount()
        monthly_total = self.get_monthly_transferred_amount()
        limit_per_txn = self.quantize(self.limit_per_transaction)

        if daily_total + (amount + fee + external_fee) > self.daily_transfer_limit:
            raise ValueError("Daily transfer limit exceeded.")

        if monthly_total + (amount + fee + external_fee) > self.monthly_transfer_limit:
            raise ValueError("Monthly transfer limit exceeded.")

        if (amount + fee + external_fee) > limit_per_txn:
            raise ValueError("Withdrawal amount exceeds single transaction limit.")

        try:
            with transaction.atomic():

                # Initialize fee_tx to None
                fee_tx = None
                
                if auto_complete:
                    self.subtract_balance(amount + external_fee)
                    status = 'completed'
                else:
                    status = 'pending'

                if fee > 0: # credit internal fee to platform revenue account
                    fee_tx = self.charge_fee(fee)

                AccountTransaction.objects.record(
                    account=self,
                    destination_account=None,
                    transaction_type='withdrawal',
                    amount=amount,
                    status=status,
                    performed_by=performed_by,
                    external_party_details=external_details,
                    description=description,
                    direction=direction,
                    currency=self.currency,
                    metadata={
                        'external_fee': str(external_fee),
                        **(
                            {'fee_tx': fee_tx.id} if fee > 0 else {} # include fee_tx only if fee was charged
                        )
                    },
                    fee=fee,
                )
        except Exception as e:
            logger.error("Withdrawal failed for account %s: %s", self.account_number, str(e), exc_info=True)
            AccountTransaction.objects.create(
                account=self,
                destination_account=None,
                transaction_type='withdrawal',
                amount=amount,
                status='failed',
                performed_by=performed_by,
                external_party_details=external_details,
                description=f"{description} - Failed: {str(e)}",
                direction=direction,
                currency=self.currency,
                metadata={},
                fee=fee,
            )
            raise e

    def get_account_type(self, obj):
        if hasattr(obj, "fiataccount"):
            return "fiat"
        return "crypto"

class FiatAccount(Account):
    pass


class CryptoAccount(Account):
    wallet = models.CharField(max_length=255)
    blockchain_network = models.CharField(max_length=100)


class TransactionManager(models.Manager):
    """Custom manager that encapsulates all ledger recording logic."""

    @transaction.atomic
    def record(
        self,
        account: str,
        destination_account: str,
        transaction_type: str,
        amount: Decimal,
        performed_by: User,
        description: str,
        direction: str,
        currency: str,
        fee: Decimal = Decimal('0'),
        metadata: dict = {},
        external_party_details: dict = {},
        status:str = 'pending',
    ):
        """Creates a double-entry transaction ledger validation."""

        # Create the transaction record
        tx = self.create(
                account=account,
                destination_account=destination_account,
                transaction_type=transaction_type,
                amount=amount,
                status=status,
                performed_by=performed_by,
                external_party_details=external_party_details,
                description=description,
                direction=direction,
                fee=fee,
                metadata=metadata or {},
                currency=currency,
            )
        
        sys_account = Account.get_sys_account(currency=currency)
        sys_revenue_account = Account.get_sys_revenue_account(currency=currency)
        sys_suspense_account = Account.get_sys_suspense_account(currency=currency)

        # Build ledger entries
        entries = []

        # Define the fee amount for clarity (assuming it's passed in metadata if applicable)
        external_fee_amount = metadata.get('external_fee', 0)
        principal_amount = amount # 'amount' is generally the principal/base amount

        # --- SCENARIO 1: Fee Transaction (TXN-B) ---
        if transaction_type == 'fee':
            # This assumes a standalone transaction for the internal fee.
            # Debit: Decrease Liability to User (User's balance goes down)
            entries.append(Ledger(
                transaction=tx, account=account, entry_type="debit", amount=principal_amount
            ))
            # Credit: Increase Revenue (Platform earns income)
            entries.append(Ledger(
                transaction=tx, account=sys_revenue_account, entry_type="credit", amount=principal_amount
            ))

        # --- SCENARIO 2: Deposit ---
        elif transaction_type == 'deposit':
            # Deposit (User deposits into their own account, usually identified by type)
            # Debit: Increase Platform Cash (Asset)
            entries.append(Ledger(
                transaction=tx, account=sys_account, entry_type="debit", amount=principal_amount
            )) 
            # Credit: Increase Liability to User (Liability)
            entries.append(Ledger(
                transaction=tx, account=destination_account, entry_type="credit", amount=principal_amount
            )) 
            # Note: If a deposit fee exists, it must be handled in a separate 'fee' transaction (Scenario 1).

        # --- SCENARIO 3: Withdrawal (TXN-A) ---
        elif transaction_type == 'withdrawal':
            # Withdrawal logic handles principal + external fee paid by user (if applicable)
            total_cash_outflow = principal_amount + external_fee_amount
            
            # Debit: Decrease Liability to User (User's balance goes down by cash out + external fee)
            entries.append(Ledger(
                transaction=tx, account=account, entry_type="debit", amount=total_cash_outflow
            )) 
            # Credit: Decrease Platform Cash (Asset goes down)
            entries.append(Ledger(
                transaction=tx, account=sys_account, entry_type="credit", amount=total_cash_outflow
            )) 
            # Note: The internal fee must be handled by a separate 'fee' transaction (Scenario 1).

        # --- SCENARIO 4: Transfer (User A to User B) ---
        elif transaction_type == 'transfer':
            # Debit: Decrease Liability to Sender (Liability)
            entries.append(Ledger(
                transaction=tx, account=account, entry_type="debit", amount=principal_amount
            )) 
            # Credit: Increase Liability to Receiver (Liability)
            entries.append(Ledger(
                transaction=tx, account=destination_account, entry_type="credit", amount=principal_amount
            ))

        # --- SCENARIO 5: Adjustment (UP or DOWN) ---
        elif transaction_type == 'adjustment':
            # Adjustment MUST be balanced. Assuming adjustment account is provided or inferred.
            # We use a Suspense account (4999) for generic platform adjustments.
            sys_suspense_account = Account.get_sys_suspense_account() # Assumed function/variable

            # If the user balance needs to increase (e.g., reversing an error)
            if amount > 0:
                # Debit: Suspense (Temporary Asset/Expense) | Credit: User Liability (Increase user balance)
                entries.append(Ledger(transaction=tx, account=sys_suspense_account, entry_type="debit", amount=principal_amount))
                entries.append(Ledger(transaction=tx, account=destination_account, entry_type="credit", amount=principal_amount))
            # If the user balance needs to decrease (e.g., recovering an overpayment)
            else:
                # Debit: User Liability (Decrease user balance) | Credit: Suspense (Temporary Liability/Revenue)
                entries.append(Ledger(transaction=tx, account=account, entry_type="debit", amount=abs(principal_amount)))
                entries.append(Ledger(transaction=tx, account=sys_suspense_account, entry_type="credit", amount=abs(principal_amount)))
            
        else:
            raise ValidationError("Invalid transaction type.")


        # --- VALIDATION ---
        # Validate double-entry
        debit_sum = sum(e.amount for e in entries if e.entry_type == "debit")
        credit_sum = sum(e.amount for e in entries if e.entry_type == "credit")
        if debit_sum != credit_sum:
            # Use a try/finally block around bulk_create and validation in a real ORM setup
            raise ValidationError(f"Ledger imbalance: debits={debit_sum}, credits={credit_sum}. Transaction {tx.pk} is invalid.")

        # Save entries
        Ledger.objects.bulk_create(entries)

        return tx

class AccountTransaction(TimeStampedModel):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
        ('adjustment', 'Adjustment'),
        ('fee', 'Fee'),
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
        ('gift_card_to_account', 'Gift Card to Account'),
    )

    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_transactions')
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
    amount = models.DecimalField(max_digits=40, decimal_places=18)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    performed_by = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='transactions')
    description = models.CharField(max_length=255, blank=True)
    fee = models.DecimalField(max_digits=40, decimal_places=18, default=0)
    metadata = models.JSONField(null=True, blank=True)
    currency = models.CharField(max_length=3, choices=Account.CURRENCY_CHOICES)

    objects = TransactionManager()
    
    def __str__(self):
        return f"{self.transaction_type.title()} of {self.amount} on {self.account} ({self.status})"

class Ledger(models.Model):
    ENTRY_TYPES = [("debit", "Debit"), ("credit", "Credit")]

    transaction = models.ForeignKey(AccountTransaction, on_delete=models.CASCADE, related_name="entries")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="entries")
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    amount = models.DecimalField(max_digits=40, decimal_places=18)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.entry_type.upper()} {self.amount} {self.account.currency} → {self.account}"
