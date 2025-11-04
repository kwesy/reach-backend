import uuid
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from oauth.models.user import User
from main.models.account import (
    Account,
    AccountTransaction,
    FiatAccount,
    Ledger,
    InsufficientFundsError,
    TransfersNotAllowedError,
    TransferLimitExceededError,
    SystemAccountError,
)
import logging

logger = logging.getLogger('error')

# ---------------------------
# Common fixture for all tests
# ---------------------------
@pytest.fixture
def setup_users_and_accounts():
    # Create users
    sys_user = User.objects.create_system_user()
    admin_user = User.objects.create_superuser(
        email="admin@example.com", password="admin123"
    )
    regular_user_A = User.objects.create_user(
        email="user_a@example.com", password="user123", phone_number="1234567890"
    )
    regular_user_B = User.objects.create_user(
        email="user_b@example.com", password="user123", phone_number="1234567890"
    )

    # Create accounts
    sys_asset_account = FiatAccount.objects.create(
        owner=sys_user, currency="USD", account_role="asset", balance=Decimal("100000")
    )
    sys_asset_account_GHS = FiatAccount.objects.create(
        owner=sys_user, currency="GHS", account_role="asset", balance=Decimal("100000")
    )

    sys_revenue_account = FiatAccount.objects.create(
        owner=sys_user, currency="USD", account_role="revenue", balance=Decimal("0")
    )
    sys_revenue_account_GHS = FiatAccount.objects.create(
        owner=sys_user, currency="GHS", account_role="revenue", balance=Decimal("0")
    )

    sys_suspense_account = FiatAccount.objects.create(
        owner=sys_user, currency="USD", account_role="suspense", balance=Decimal("0")
    )
    sys_suspense_account_GHS = FiatAccount.objects.create(
        owner=sys_user, currency="GHS", account_role="suspense", balance=Decimal("0")
    )

    user_account_A = FiatAccount.objects.create(
        owner=regular_user_A, currency="USD", account_role="user", balance=Decimal("500")
    )

    user_account_B = FiatAccount.objects.create(
        owner=regular_user_B, currency="USD", account_role="user", balance=Decimal("500")
    )

    return {
        "sys_user": sys_user,
        "admin_user": admin_user,
        "regular_user_a": regular_user_A,
        "regular_user_b": regular_user_B,
        "sys_asset_account": sys_asset_account,
        "sys_revenue_account": sys_revenue_account,
        "sys_suspense_account": sys_suspense_account,
        "user_account_a": user_account_A,
        "user_account_b": user_account_B,
    }


# --------------------------------------------------
# Unified tests for AccountTransaction and Account methods
# --------------------------------------------------
@pytest.mark.django_db
class TestAccountTransactions:

    # ---------------------
    # Account class methods
    # ---------------------

    def test_get_sys_account(self, setup_users_and_accounts):
        sys_account_USD_asset = Account.get_sys_account()
        sys_account_GHS_asset = Account.get_sys_account(currency='GHS')

        assert sys_account_USD_asset.account_role == 'asset'
        assert sys_account_USD_asset.owner.role == 'sys'
        assert sys_account_USD_asset.currency == 'USD'

        assert sys_account_GHS_asset.account_role == 'asset'
        assert sys_account_GHS_asset.owner.role == 'sys'
        assert sys_account_GHS_asset.currency == 'GHS'

    def test_get_sys_revenue_account(self, setup_users_and_accounts):
        sys_account_USD_revenue = Account.get_sys_revenue_account()
        sys_account_GHS_revenue = Account.get_sys_revenue_account(currency='GHS')

        assert sys_account_USD_revenue.account_role == 'revenue'
        assert sys_account_USD_revenue.owner.role == 'sys'
        assert sys_account_USD_revenue.currency == 'USD'

        assert sys_account_GHS_revenue.account_role == 'revenue'
        assert sys_account_GHS_revenue.owner.role == 'sys'
        assert sys_account_GHS_revenue.currency == 'GHS'

    def test_get_sys_suspense_account(self, setup_users_and_accounts):
        sys_account_USD_suspense = Account.get_sys_suspense_account()
        sys_account_GHS_suspense = Account.get_sys_suspense_account(currency='GHS')

        assert sys_account_USD_suspense.account_role == 'suspense'
        assert sys_account_USD_suspense.owner.role == 'sys'
        assert sys_account_USD_suspense.currency == 'USD'

        assert sys_account_GHS_suspense.account_role == 'suspense'
        assert sys_account_GHS_suspense.owner.role == 'sys'
        assert sys_account_GHS_suspense.currency == 'GHS'

    # ---------------------
    # Account instance methods
    # ---------------------

    def test_quantize(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user = acc['regular_user_a']
        amount = 5
        currencies = ['USD', 'GHS', 'BTC', 'ETH', 'XRP', 'LTC']
        excepted_output = ['5.00', '5.00', '5.00000000', '5.000000000000000000', '5.000000', '5.00000000']

        for i, c in enumerate(currencies):
            account = Account.objects.create(owner=user, currency=c)
            assert account.quantize(amount) == account.to_decimal(excepted_output[i]) 

    def test_deposit_method_with_auto_complete(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        system_account = acc["sys_asset_account"]

        transaction = user_account.deposit(
            amount=Decimal("100"),
            direction="bank_to_account",
            performed_by=acc["regular_user_a"],
            description="Deposit test",
            auto_complete=True
        )

        assert transaction is not None
        assert transaction.account == user_account
        assert user_account.balance == Decimal("600")
        assert transaction.transaction_type == "deposit"
        assert Ledger.objects.filter(account=system_account).count() == 1
        assert Ledger.objects.filter(account=user_account).count() == 1
        assert Ledger.objects.filter(transaction=transaction).count() == 2
        assert Ledger.objects.filter(entry_type="debit").first().account.fiataccount == system_account
        assert Ledger.objects.filter(entry_type="credit").first().account.fiataccount == user_account
        assert transaction.status == "success"

    def test_withdraw_method(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        system_account = acc["sys_asset_account"]
        system_revenue = acc["sys_revenue_account"]

        user_account.withdraw(
            amount=Decimal("100"),
            direction="account_to_bank",
            performed_by=acc["regular_user_a"],
            description="Withdraw test",
        )

        transactions = AccountTransaction.objects.filter(account=user_account)

        assert user_account.balance == Decimal("398") # default external_fee_rate=0.01, fee_rate=0.01
        assert transactions.count() == 2 # one for fee and other for the withdrawal
        assert transactions.filter(transaction_type="withdrawal").count() == 1
        assert transactions.filter(transaction_type="fee").count() == 1
        assert transactions.filter(transaction_type="withdrawal").first().status == "success" # auto completed by default

        assert Ledger.objects.all().count() == 4
        assert Ledger.objects.filter(account=system_account).filter(entry_type="credit").count() == 1
        assert Ledger.objects.filter(account=user_account).filter(entry_type="debit").filter(transaction__transaction_type="withdrawal").count() == 1
        assert Ledger.objects.filter(account=user_account).filter(entry_type="debit").filter(transaction__transaction_type="fee").count() == 1
        assert Ledger.objects.filter(account=system_revenue).filter(entry_type="credit").count() == 1
        assert Ledger.objects.filter(transaction=transactions.first()).count() == 2

    def test_transfer_method(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account_a = acc["user_account_a"]
        user_account_b = acc["user_account_b"]

        assert user_account_a.balance == Decimal('500')
        assert user_account_b.balance == Decimal('500')

        user_account_a.transfer(
            amount=Decimal('200'),
            destination_account=user_account_b,
            performed_by=acc["regular_user_a"],
            description="Transfer test",
        )

        transactions = AccountTransaction.objects.filter(transaction_type="transfer")

        user_account_a.refresh_from_db()
        user_account_b.refresh_from_db()

        assert transactions.first().account.fiataccount == user_account_a
        assert transactions.first().destination_account.fiataccount == user_account_b
        assert user_account_a.balance == Decimal("300")
        assert user_account_b.balance == Decimal("700")
        assert transactions.count() == 1
        assert transactions.first().transaction_type == "transfer"
        assert Ledger.objects.filter(account=user_account_a).count() == 1
        assert Ledger.objects.filter(account=user_account_b).count() == 1
        assert Ledger.objects.filter(transaction=transactions.first()).count() == 2
        assert Ledger.objects.filter(entry_type="debit").first().account.fiataccount == user_account_a # Debit source
        assert Ledger.objects.filter(entry_type="credit").first().account.fiataccount == user_account_b # Credit receiver
        assert transactions.first().status == "success"

    def test_adjustment_positive(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        sys_suspense_account = acc["sys_suspense_account"]

        assert sys_suspense_account.balance == Decimal('0')
        user_account.adjustment(
            amount=50,
            performed_by=acc["admin_user"],
        )

        transactions = AccountTransaction.objects.filter(transaction_type="adjustment")
        user_account.refresh_from_db()
        sys_suspense_account.refresh_from_db()

        assert user_account.balance == Decimal("550")
        assert sys_suspense_account.balance == Decimal("-50")
        assert transactions.count() == 1
        assert Ledger.objects.filter(account=user_account).count() == 1
        assert Ledger.objects.filter(account=sys_suspense_account).count() == 1
        assert Ledger.objects.filter(transaction=transactions.first()).count() == 2
        assert Ledger.objects.filter(entry_type="debit").first().account.fiataccount == sys_suspense_account # Debit suspense account
        assert Ledger.objects.filter(entry_type="credit").first().account.fiataccount == user_account # credit user account
        assert transactions.first().status == "success"

    def test_adjustment_negative(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        sys_suspense_account = acc["sys_suspense_account"]

        # Ensure the suspense account starts with a balance of 0
        assert sys_suspense_account.balance == Decimal("0")
        
        user_account.adjustment(
            amount=-50,
            performed_by=acc["admin_user"],
        )

        transactions = AccountTransaction.objects.filter(transaction_type="adjustment")
        user_account.refresh_from_db()
        sys_suspense_account.refresh_from_db()

        assert user_account.balance == Decimal("450")
        assert sys_suspense_account.balance == Decimal("50")
        assert transactions.count() == 1
        assert Ledger.objects.filter(account=user_account).count() == 1
        assert Ledger.objects.filter(account=sys_suspense_account).count() == 1
        assert Ledger.objects.filter(transaction=transactions.first()).count() == 2
        assert Ledger.objects.filter(entry_type="credit").first().account.fiataccount == sys_suspense_account # Debit suspense account
        assert Ledger.objects.filter(entry_type="debit").first().account.fiataccount == user_account # credit user account
        assert transactions.first().status == "success"

    def test_charge_fee_method(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        sys_revenue_account = acc["sys_revenue_account"]

        user_account.charge_fee(
            fee_amount=Decimal("10"),
            description="Fee test",
            performed_by=acc["admin_user"],
        )
        user_account.refresh_from_db()
        sys_revenue_account.refresh_from_db()

        assert user_account.balance == Decimal("490")
        assert sys_revenue_account.balance == Decimal("10")
        assert AccountTransaction.objects.filter(transaction_type="fee").count() == 1
        assert Ledger.objects.filter(account=user_account).count() == 1
        assert Ledger.objects.filter(account=sys_revenue_account).count() == 1

    # ---------------------
    # Error handling tests
    # ---------------------

    def test_insufficient_funds_withdraw(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]

        with pytest.raises(InsufficientFundsError):
            user_account.withdraw(
                amount=Decimal("1000"),
                direction="account_to_bank",
                performed_by=acc["regular_user_a"],
                description="Insufficient funds test",
            )

    def test_transfer_insufficient_balance(self, setup_users_and_accounts):
            acc = setup_users_and_accounts
            user_account_a = acc["user_account_a"]
            user_account_b = acc["user_account_b"]

            # Attempt to transfer more than the available balance
            with pytest.raises(TransfersNotAllowedError):
                user_account_a.transfer(
                    amount=Decimal("600"),
                    destination_account=user_account_b,
                    performed_by=acc["regular_user_a"],
                    description="Transfer insufficient balance test",
                )

    def test_transfer_limit_exceeded(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        user_account.limit_per_transaction = Decimal("100")
        user_account.save()

        with pytest.raises(TransfersNotAllowedError):
            user_account.transfer(
                amount=Decimal("200"),
                destination_account=acc["sys_asset_account"],
                performed_by=acc["regular_user_a"],
                description="Transfer limit exceeded test",
            )

    def test_currency_mismatch_transfer(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        btc_account = Account.objects.create(
            owner=acc["sys_user"], currency="BTC", account_role="asset", balance=Decimal("100")
        )

        with pytest.raises(TransfersNotAllowedError):
            user_account.transfer(
                amount=Decimal("50"),
                destination_account=btc_account,
                performed_by=acc["regular_user_a"],
                description="Currency mismatch test",
            )


@pytest.mark.django_db
class TestAccountDeposit:
    """Tests for Account.deposit() and Account.deposit_confirm() methods."""

    def test_deposit_creates_pending_transaction(self, setup_users_and_accounts):
        """Deposit should create a pending transaction and not yet update balance."""
        account = setup_users_and_accounts["user_account_a"]
        sys_account = Account.get_sys_account("USD").fiataccount

        initial_balance = account.balance
        sys_initial_balance = sys_account.balance

        # Perform deposit
        tx = account.deposit(
            amount=Decimal("200.00"),
            performed_by=account.owner,
            description="Initial deposit",
            direction="mobile_money_to_account",
            metadata={}
        )

        # Refresh from DB
        account.refresh_from_db()
        sys_account.refresh_from_db()
        tx.refresh_from_db()

        # Assertions
        assert isinstance(tx, AccountTransaction)
        assert tx.account.fiataccount == account
        assert tx.transaction_type == "deposit"
        assert tx.status == "pending"
        assert tx.amount == Decimal("200.00")
        assert account.balance == initial_balance  # not yet applied
        assert sys_account.balance == sys_initial_balance  # not yet applied
        assert "Initial deposit" in tx.description
        assert Ledger.objects.count() == 0

    def test_deposit_confirm_success_updates_balance(self, setup_users_and_accounts):
        """Confirming a pending deposit should update balance and mark success."""
        user_account = setup_users_and_accounts["user_account_a"]
        system_account = setup_users_and_accounts["sys_asset_account"]

        initial_balance = user_account.balance
        sys_initial_balance = system_account.balance

        # Step 1: create a pending deposit
        tx = user_account.deposit(
            amount=Decimal("100.00"),
            performed_by=user_account.owner,
            description="Test deposit",
            direction="mobile_money_to_account",
            metadata={}
        )

        # Step 2: confirm deposit as successful
        confirmed_tx = user_account.deposit_confirm(
            transaction_id=tx.id,
            status="success",
            amount=Decimal("100.00"),
            metadata={"bank_ref": "XYZ123"},
        )

        # Reload objects
        user_account.refresh_from_db()
        system_account.refresh_from_db()
        confirmed_tx.refresh_from_db()

        # Assertions
        assert confirmed_tx.status == "success"
        assert confirmed_tx.metadata == {"bank_ref": "XYZ123"}
        assert user_account.balance == initial_balance + Decimal("100.00")
        assert system_account.balance == sys_initial_balance + Decimal("100.00")
        assert confirmed_tx.account.owner == user_account.owner
        assert confirmed_tx.transaction_type == "deposit"
        assert Ledger.objects.filter(account=system_account).count() == 1
        assert Ledger.objects.filter(account=user_account).count() == 1
        assert Ledger.objects.filter(transaction=confirmed_tx).count() == 2
        assert Ledger.objects.filter(entry_type="debit").first().account.fiataccount == system_account
        assert Ledger.objects.filter(entry_type="credit").first().account.fiataccount == user_account


    def test_deposit_confirm_failed_does_not_affect_balance_and_ledger(self, setup_users_and_accounts):
        """Failed deposit confirmation should not alter balance."""
        account = setup_users_and_accounts["user_account_a"]
        system_account = setup_users_and_accounts["sys_asset_account"]

        initial_balance = account.balance
        sys_initial_balance = system_account.balance

        # Create deposit transaction
        tx = account.deposit(
            amount=Decimal("150.00"),
            performed_by=account.owner,
            description="Deposit to fail",
            direction="mobile_money_to_account",
            metadata={}
        )

        # Confirm as failed
        failed_tx = account.deposit_confirm(
            transaction_id=tx.id,
            status="failed",
            amount=Decimal("150.00"),
            metadata={"reason": "Bank declined"},
        )

        account.refresh_from_db()
        system_account.refresh_from_db()
        failed_tx.refresh_from_db()

        # Assertions
        assert failed_tx.status == "failed"
        assert account.balance == initial_balance
        assert system_account.balance == sys_initial_balance
        assert Ledger.objects.count() == 0

    def test_deposit_confirm_cannot_process_twice(self, setup_users_and_accounts):
        """Deposit cannot be confirmed more than once."""
        account = setup_users_and_accounts["user_account_a"]

        tx = account.deposit(
            amount=Decimal("50.00"),
            performed_by=account.owner,
            description="Double confirm test",
            direction="mobile_money_to_account",
            metadata={}
        )

        # First confirmation succeeds
        account.deposit_confirm(
            transaction_id=tx.id,
            status="success",
            amount=Decimal("50.00"),
            metadata={},
        )

        account.refresh_from_db()
        first_update_balance = account.balance

        # Second confirmation should fail
        with pytest.raises(ValidationError, match="already been processed"):
            account.deposit_confirm(
                transaction_id=tx.id,
                status="success",
                amount=Decimal("50.00"),
                metadata={},
            )

        account.refresh_from_db()
        assert account.balance == first_update_balance
        Ledger.objects.count() == 2


    def test_deposit_confirm_raises_if_amount_too_low(self, setup_users_and_accounts):
        """Deposit confirmation fails if confirmed amount < original."""
        account = setup_users_and_accounts["user_account_a"]

        tx = account.deposit(
            amount=Decimal("200.00"),
            performed_by=account.owner,
            description="Insufficient confirm test",
            direction="mobile_money_to_account",
            metadata={}
        )

        with pytest.raises(ValidationError, match="less than the original amount"):
            account.deposit_confirm(
                transaction_id=tx.id,
                status="success",
                amount=Decimal("150.00"),
                metadata={},
            )
        assert Ledger.objects.count() == 0


    def test_deposit_confirm_raises_404_for_nonexistent_tx(self, setup_users_and_accounts):
        """Should raise 404 if transaction does not exist."""
        account = setup_users_and_accounts["user_account_a"]
        fake_id = uuid.uuid4()

        with pytest.raises(Exception):  # Django's Http404
            account.deposit_confirm(
                transaction_id=fake_id,
                status="success",
                amount=Decimal("100.00"),
                metadata={},
            )
        assert Ledger.objects.count() == 0


# | Scenario     | Debit        | Credit         | Validation               |
# | ------------ | ------------ | -------------- | ------------------------ |
# | Fee          | User         | System Revenue | Balanced                 |
# | Deposit      | System Asset | User           | Balanced                 |
# | Withdrawal   | User         | System Asset   | Includes external fee    |
# | Transfer     | Sender       | Receiver       | Balanced                 |
# | Adjustment + | Suspense     | User           | Balanced                 |
# | Adjustment - | User         | Suspense       | Balanced                 |
# | Invalid Type | —            | —              | Raises `ValidationError` |
# | Imbalance    | —            | —              | Raises `ValidationError` |

@pytest.mark.django_db
class TestLedgerManagerRecord:
    """Tests for LedgerManager.record() covering all transaction scenarios."""

    def setup_method(self):
        """Optionally clear ledgers before each test (safety)."""
        Ledger.objects.all().delete()

    def _create_tx(self, account, tx_type, amount=Decimal("100.00")):
        """Helper to quickly create a base AccountTransaction."""
        return AccountTransaction.objects.create(
            account=account,
            performed_by=account.owner,
            transaction_type=tx_type,
            amount=amount,
            status="success",
        )

    def test_fee_transaction_creates_correct_entries(self, setup_users_and_accounts):
        user_account = setup_users_and_accounts["user_account_a"]
        sys_revenue_account = Account.get_sys_revenue_account("USD").fiataccount

        tx = self._create_tx(user_account, "fee")

        Ledger.objects.record(
            tx=tx,
            account=user_account,
            destination_account=None,
            transaction_type="fee",
            amount=Decimal("25.00"),
            currency="USD",
        )

        entries = Ledger.objects.filter(transaction=tx)
        assert entries.count() == 2

        debit = entries.get(entry_type="debit")
        credit = entries.get(entry_type="credit")

        assert debit.account.fiataccount == user_account
        assert credit.account.fiataccount == sys_revenue_account
        assert debit.amount == credit.amount == Decimal("25.00")

    def test_deposit_creates_correct_double_entry(self, setup_users_and_accounts):
        sys_account = Account.get_sys_account("USD").fiataccount
        user_account = setup_users_and_accounts["user_account_a"]

        tx = self._create_tx(user_account, "deposit")

        Ledger.objects.record(
            tx=tx,
            account=sys_account,
            destination_account=user_account,
            transaction_type="deposit",
            amount=Decimal("200.00"),
            currency="USD",
        )

        entries = Ledger.objects.filter(transaction=tx)
        assert entries.count() == 2

        debit = entries.get(entry_type="debit")
        credit = entries.get(entry_type="credit")

        assert debit.account.fiataccount == sys_account
        assert credit.account.fiataccount == user_account
        assert debit.amount == credit.amount == Decimal("200.00")

    def test_withdrawal_creates_correct_double_entry_with_external_fee(self, setup_users_and_accounts):
        user_account = setup_users_and_accounts["user_account_a"]
        sys_account = Account.get_sys_account("USD").fiataccount

        tx = self._create_tx(user_account, "withdrawal")

        Ledger.objects.record(
            tx=tx,
            account=user_account,
            destination_account=None,
            transaction_type="withdrawal",
            amount=Decimal("100.00"),
            currency="USD",
            metadata={"external_fee": "5.00"},
        )

        entries = Ledger.objects.filter(transaction=tx)
        assert entries.count() == 2

        debit = entries.get(entry_type="debit")
        credit = entries.get(entry_type="credit")

        # Total withdrawal amount should include external fee
        assert debit.amount == credit.amount == Decimal("105.00")
        assert debit.account.fiataccount == user_account
        assert credit.account.fiataccount == sys_account

    def test_transfer_creates_balanced_entries(self, setup_users_and_accounts):
        sender = setup_users_and_accounts["user_account_a"]
        receiver = setup_users_and_accounts["user_account_b"]

        tx = self._create_tx(sender, "transfer")

        Ledger.objects.record(
            tx=tx,
            account=sender,
            destination_account=receiver,
            transaction_type="transfer",
            amount=Decimal("50.00"),
            currency="USD",
        )

        entries = Ledger.objects.filter(transaction=tx)
        assert entries.count() == 2

        debit = entries.get(entry_type="debit")
        credit = entries.get(entry_type="credit")

        assert debit.account.fiataccount == sender
        assert credit.account.fiataccount == receiver
        assert debit.amount == credit.amount == Decimal("50.00")

    def test_adjustment_positive_creates_correct_entries(self, setup_users_and_accounts):
        sys_suspense = Account.get_sys_suspense_account("USD").fiataccount
        user_account = setup_users_and_accounts["user_account_a"]

        tx = self._create_tx(user_account, "adjustment", Decimal("25.00"))

        Ledger.objects.record(
            tx=tx,
            account=None,
            destination_account=user_account,
            transaction_type="adjustment",
            amount=Decimal("25.00"),
            currency="USD",
        )

        entries = Ledger.objects.filter(transaction=tx)
        assert entries.count() == 2

        debit = entries.get(entry_type="debit")
        credit = entries.get(entry_type="credit")

        assert debit.account.fiataccount == sys_suspense
        assert credit.account.fiataccount == user_account
        assert debit.amount == credit.amount == Decimal("25.00")

    def test_adjustment_negative_creates_correct_entries(self, setup_users_and_accounts):
        sys_suspense = Account.get_sys_suspense_account("USD").fiataccount
        user_account = setup_users_and_accounts["user_account_a"]

        tx = self._create_tx(user_account, "adjustment", Decimal("-30.00"))

        Ledger.objects.record(
            tx=tx,
            account=user_account,
            destination_account=None,
            transaction_type="adjustment",
            amount=Decimal("-30.00"),
            currency="USD",
        )

        entries = Ledger.objects.filter(transaction=tx)
        assert entries.count() == 2

        debit = entries.get(entry_type="debit")
        credit = entries.get(entry_type="credit")

        assert debit.account.fiataccount == user_account
        assert credit.account.fiataccount == sys_suspense
        assert debit.amount == credit.amount == Decimal("30.00")

    def test_invalid_transaction_type_raises_validation_error(self, setup_users_and_accounts):
        user_account = setup_users_and_accounts["user_account_a"]
        tx = self._create_tx(user_account, "invalid_type")

        with pytest.raises(ValidationError, match="Invalid transaction type"):
            Ledger.objects.record(
                tx=tx,
                account=user_account,
                destination_account=None,
                transaction_type="nonsense",
                amount=Decimal("10.00"),
                currency="USD",
            )

    def test_unbalanced_entries_raise_validation_error(self, setup_users_and_accounts, monkeypatch):
        """Simulate imbalance before validation occurs."""
        user_account = setup_users_and_accounts["user_account_a"]
        tx = self._create_tx(user_account, "deposit")

        original_init = Ledger.__init__

        def fake_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # Introduce imbalance in debit entries
            if kwargs.get("entry_type") == "debit":
                self.amount = self.amount + Decimal("1.00")

        monkeypatch.setattr(Ledger, "__init__", fake_init)

        with pytest.raises(ValidationError, match="Ledger imbalance"):
            Ledger.objects.record(
                tx=tx,
                account=user_account,
                destination_account=user_account,
                transaction_type="deposit",
                amount=Decimal("10.00"),
                currency="USD",
            )

@pytest.mark.django_db
class TestAccountCreditDebit:
    """Tests for Account.credit_account() and Account.debit_account() methods."""

    def test_credit_account_success(self, setup_users_and_accounts):
        """Test successful crediting of an account."""
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        sys_account = acc["sys_asset_account"]

        initial_balance = user_account.balance
        initial_sys_balance = sys_account.balance

        user_account.credit_account(
            amount=Decimal("100.00"),
            description="Test credit",
            performed_by=acc["admin_user"],
        )

        user_account.refresh_from_db()
        sys_account.refresh_from_db()

        # Assertions
        assert user_account.balance == initial_balance + Decimal("100.00")
        assert sys_account.balance == initial_sys_balance
        assert AccountTransaction.objects.filter(transaction_type="credit").count() == 1
        transaction = AccountTransaction.objects.filter(transaction_type="credit").first()
        assert transaction.status == "success"
        assert transaction.amount == Decimal("100.00")
        assert transaction.description == "Test credit"
        assert Ledger.objects.count() == 2
        assert Ledger.objects.filter(account=user_account).count() == 1  # Debit and Credit entries
        assert Ledger.objects.filter(transaction=transaction).count() == 2
        assert Ledger.objects.filter(account=sys_account).first().entry_type == 'debit'
        assert Ledger.objects.filter(account=user_account).first().entry_type == 'credit'

    def test_credit_account_negative_amount(self, setup_users_and_accounts):
        """Test that crediting a negative amount raises an error."""
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]

        initial_balance = user_account.balance

        with pytest.raises(ValueError, match="Credit amount must be positive."):
            user_account.credit_account(
                amount=Decimal("-50.00"),
                description="Invalid credit",
                performed_by=acc["admin_user"],
            )

        user_account.refresh_from_db()

        # Ensure no transactions or ledger entries were created
        assert initial_balance == user_account.balance
        assert AccountTransaction.objects.filter(transaction_type="credit").count() == 0
        assert Ledger.objects.filter(account=user_account).count() == 0

    def test_credit_account_failure_logs_transaction(self, setup_users_and_accounts, monkeypatch):
        """Test that a failed credit logs a failed transaction."""
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]

        # Simulate an error during the credit process
        def mock_add_balance_safe(*args, **kwargs):
            raise Exception("Simulated failure")

        monkeypatch.setattr(user_account, "add_balance_safe", mock_add_balance_safe)

        with pytest.raises(Exception, match="Simulated failure"):
            user_account.credit_account(
                amount=Decimal("100.00"),
                description="Test credit failure",
                performed_by=acc["admin_user"],
            )

        # Ensure a failed transaction was logged
        assert AccountTransaction.objects.filter(transaction_type="credit", status="failed").count() == 1
        failed_transaction = AccountTransaction.objects.filter(transaction_type="credit", status="failed").first()
        assert failed_transaction.description.startswith("Test credit failure - Failed")

    def test_debit_account_success(self, setup_users_and_accounts):
        """Test successful debiting of an account."""
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        sys_account = acc["sys_asset_account"]

        initial_balance = user_account.balance
        initial_sys_balance = sys_account.balance

        user_account.debit_account(
            amount=Decimal("50.00"),
            description="Test debit",
            performed_by=acc["admin_user"],
        )

        user_account.refresh_from_db()
        sys_account .refresh_from_db()

        # Assertions
        assert user_account.balance == initial_balance - Decimal("50.00")
        assert sys_account.balance == initial_sys_balance
        assert AccountTransaction.objects.filter(transaction_type="debit").count() == 1
        transaction = AccountTransaction.objects.filter(transaction_type="debit").first()
        assert transaction.status == "success"
        assert transaction.amount == Decimal("50.00")
        assert transaction.description == "Test debit"
        assert Ledger.objects.count() == 2
        assert Ledger.objects.filter(account=user_account).count() == 1
        assert Ledger.objects.filter(transaction=transaction).count() == 2
        assert Ledger.objects.filter(account=user_account).first().entry_type == 'debit'
        assert Ledger.objects.filter(account=sys_account).first().entry_type == 'credit'

    def test_debit_account_insufficient_funds(self, setup_users_and_accounts):
        """Test that debiting more than the balance raises an error."""
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]

        initial_balance = user_account.balance

        with pytest.raises(InsufficientFundsError, match="Insufficient balance for debit."):
            user_account.debit_account(
                amount=Decimal("1000.00"),
                description="Test insufficient funds",
                performed_by=acc["admin_user"],
            )

        user_account.refresh_from_db()

        # Ensure no transactions or ledger entries were created
        assert initial_balance == user_account.balance
        assert AccountTransaction.objects.filter(transaction_type="debit").count() == 0
        assert Ledger.objects.filter(account=user_account).count() == 0

    def test_debit_account_negative_amount(self, setup_users_and_accounts):
        """Test that debiting a negative amount raises an error."""
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]

        initial_balance = user_account.balance

        with pytest.raises(ValueError, match="Debit amount must be positive."):
            user_account.debit_account(
                amount=Decimal("-50.00"),
                description="Invalid debit",
                performed_by=acc["admin_user"],
            )

        user_account.refresh_from_db()

        # Ensure no transactions or ledger entries were created
        assert initial_balance == user_account.balance
        assert AccountTransaction.objects.filter(transaction_type="debit").count() == 0
        assert Ledger.objects.filter(account=user_account).count() == 0

    def test_debit_account_failure_logs_transaction(self, setup_users_and_accounts, monkeypatch):
        """Test that a failed debit logs a failed transaction."""
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]

        # Simulate an error during the debit process
        def mock_subtract_balance_safe(*args, **kwargs):
            raise Exception("Simulated failure")

        monkeypatch.setattr(user_account, "subtract_balance_safe", mock_subtract_balance_safe)

        with pytest.raises(Exception, match="Simulated failure"):
            user_account.debit_account(
                amount=Decimal("50.00"),
                description="Test debit failure",
                performed_by=acc["admin_user"],
            )

        # Ensure a failed transaction was logged
        assert AccountTransaction.objects.filter(transaction_type="debit", status="failed").count() == 1
        failed_transaction = AccountTransaction.objects.filter(transaction_type="debit", status="failed").first()
        assert failed_transaction.description.startswith("Test debit failure - Failed")


# TODO:
# test transfer between user and system account not possible eg. asset to user A or vice-versa
# test transfer between non user role and system account is possible eg. asset to revenue
# test deposit on system asset doesn't cause double balance update