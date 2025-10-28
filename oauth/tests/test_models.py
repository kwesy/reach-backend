import pytest
from django.utils import timezone
from datetime import timedelta
from ..models.otp import OTP, generate_otp, hash_otp, create_otp
from ..models.user import User


@pytest.mark.django_db
class TestOTPModel:
    def test_generate_otp(self):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_hash_otp(self):
        code = "123456"
        hashed_code = hash_otp(code)
        assert hashed_code != code
        assert len(hashed_code) == 64  # SHA-256 hash length

    def test_create_otp(self):
        user = "test@example.com"
        purpose = "signup"
        code, otp = create_otp(user, purpose)
        assert otp.user == user
        assert otp.purpose == purpose
        assert otp.is_used is False
        assert otp.attempts == 0
        assert otp.meta == {}
        assert hash_otp(code) == otp.code_hash

    def test_otp_is_valid(self):
        otp = OTP.objects.create(
            user="test@example.com",
            code_hash=hash_otp("123456"),
            purpose="signup",
            updated_at=timezone.now(),
        )
        assert otp.is_valid() is True

        # Test expired OTP
        otp.updated_at = timezone.now() - timedelta(minutes=6)
        # otp.save() # Not needed as we are not changing the DB state and save() will reset the updated_at
        assert otp.is_valid() is False

        # Test used OTP
        otp.updated_at = timezone.now()
        otp.is_used = True
        otp.save()
        assert otp.is_valid() is False

        # Test max attempts
        otp.is_used = False
        otp.attempts = 5
        otp.save()
        assert otp.is_valid() is False

    def test_otp_verify(self):
        otp = OTP.objects.create(
            user="test@example.com",
            code_hash=hash_otp("123456"),
            purpose="signup",
        )
        assert otp.verify("123456") is True
        assert otp.is_used is True

        # Test invalid code
        otp = OTP.objects.create(
            user="test@example.com",
            code_hash=hash_otp("123456"),
            purpose="signup",
        )
        assert otp.verify("654321") is False
        assert otp.attempts == 1

@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            phone_number="1234567890",
        )
        assert user.email == "test@example.com"
        assert user.check_password("password123") is True
        assert user.phone_number == "1234567890"
        assert user.is_active is True
        assert user.email_verified is False
        assert user.role == "user"

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpassword",
            phone_number="1234567890",
        )
        assert user.email == "admin@example.com"
        assert user.check_password("adminpassword") is True
        assert user.is_superuser is True
        assert user.is_active is True
        assert user.email_verified is True
        assert user.mfa_enabled is True
        assert user.role == "admin"

    def test_user_str(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            phone_number="1234567890",
        )
        assert str(user) == "test@example.com"

    def test_user_email_otp_relationship(self):
        otp = OTP.objects.create(
            user="test@example.com",
            code_hash=hash_otp("123456"),
            purpose="email_verification",
        )
        user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            phone_number="1234567890",
            email_otp=otp,
        )
        assert user.email_otp == otp

    def test_user_defaults(self):
        user = User.objects.create_user(
            email="defaultuser@example.com",
            password="password123",
            phone_number="1234567890",
        )
        assert user.is_active is True
        assert user.email_verified is False
        assert user.mfa_enabled is False
        assert user.first_name == ""
        assert user.last_name == ""
        assert user.role == "user"
        assert user.created_at is not None
