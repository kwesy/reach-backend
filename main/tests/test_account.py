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
    sys_revenue_account = FiatAccount.objects.create(
        owner=sys_user, currency="USD", account_role="revenue", balance=Decimal("0")
    )
    sys_suspense_account = FiatAccount.objects.create(
        owner=sys_user, currency="USD", account_role="suspense", balance=Decimal("0")
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

    def test_deposit_method(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]
        system_account = acc["sys_asset_account"]

        user_account.deposit(
            amount=Decimal("100"),
            direction="bank_to_account",
            performed_by=acc["regular_user_a"],
            description="Deposit test",
        )

        transactions = AccountTransaction.objects.filter(account=user_account, transaction_type="deposit")

        assert user_account.balance == Decimal("600")
        assert transactions.count() == 1
        assert transactions.first().transaction_type == "deposit"
        assert Ledger.objects.filter(account=system_account).count() == 1
        assert Ledger.objects.filter(account=user_account).count() == 1
        assert Ledger.objects.filter(transaction=transactions.first()).count() == 2
        assert Ledger.objects.filter(entry_type="debit").first().account.fiataccount == system_account
        assert Ledger.objects.filter(entry_type="credit").first().account.fiataccount == user_account
        assert transactions.first().status == "pending"

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
        user_account.credit_account(
            amount=Decimal("50"),
            description="Positive adjustment",
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
        
        user_account.debit_account(
            amount=Decimal("50"),
            description="Negative adjustment",
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

    # ---------------------
    # Model-level transaction tests (AccountTransaction.record)
    # ---------------------

    def test_deposit_record(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]

        tx = AccountTransaction.objects.record(
            account=user_account,
            destination_account=user_account,
            transaction_type="deposit",
            amount=Decimal("100"),
            performed_by=acc["regular_user_a"],
            description="Deposit via record",
            direction="bank_to_account",
            currency="USD",
        )

        assert tx.status == "pending"
        assert tx.amount == Decimal("100")
        assert Ledger.objects.filter(transaction=tx).count() == 2

    def test_invalid_transaction_type(self, setup_users_and_accounts):
        acc = setup_users_and_accounts
        user_account = acc["user_account_a"]

        with pytest.raises(ValidationError, match="Invalid transaction type."):
            AccountTransaction.objects.record(
                account=user_account,
                destination_account=None,
                transaction_type="invalid_type",
                amount=Decimal("100"),
                performed_by=acc["regular_user_a"],
                description="Invalid transaction test",
                direction=None,
                currency="USD",
            )
