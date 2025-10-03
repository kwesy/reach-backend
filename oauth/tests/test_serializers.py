import pytest
from ..models.user import User
from ..models.otp import OTP, hash_otp
from ..serializers import UserSerializer, EmailOTPSerializer, ResendOTPSerializer


@pytest.mark.django_db
class TestUserSerializer:
    def test_user_serializer(self):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="password123",
            phone_number="1234567890",
            first_name="John",
            last_name="Doe",
            email_verified=True,
            is_active=True,
            balance=500.00,
        )
        serializer = UserSerializer(user)
        data = serializer.data

        assert data["id"] == user.id
        assert data["email"] == "testuser@example.com"
        assert data["phone_number"] == "1234567890"
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["email_verified"] is True
        assert data["is_active"] is True
        assert data["balance"] == "500.00"  # Decimal fields are serialized as strings

    def test_user_serializer_update(self):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="password123",
            phone_number="1234567890",
            first_name="John",
            last_name="Doe",
        )
        serializer = UserSerializer(
            user, data={
                "first_name": "Jane", "last_name": "Smith", # updateble fields
                "balance":500, "email": "change@example.com", "phone_number": "0200000000", "mfa_enabled":True}, # update forbidden fields
                partial=True
        )
        assert serializer.is_valid()
        updated_user = serializer.save()

        # Check updated fields
        assert updated_user.first_name == "Jane"
        assert updated_user.last_name == "Smith"

        # Forbidden fields should remain unchanged
        assert updated_user.balance == 0
        assert updated_user.email == "testuser@example.com"
        assert updated_user.phone_number == "1234567890"
        assert updated_user.mfa_enabled is False


@pytest.mark.django_db
class TestEmailOTPSerializer:
    def test_email_otp_serializer_valid(self):
        data = {"email": "test@example.com", "code": "123456"}
        serializer = EmailOTPSerializer(data=data)
        assert serializer.is_valid()

    def test_email_otp_serializer_invalid(self):
        data = {"email": "invalid-email", "code": "123"}
        serializer = EmailOTPSerializer(data=data)
        assert not serializer.is_valid()
        assert "email" in serializer.errors
        assert "code" in serializer.errors


@pytest.mark.django_db
class TestResendOTPSerializer:
    def test_resend_otp_serializer_valid(self):
        otp = OTP.objects.create(
            user="test@example.com",
            code_hash=hash_otp("123456"),
            purpose="email_verification",
        )
        data = {"token": otp.id}
        serializer = ResendOTPSerializer(data=data)
        assert serializer.is_valid()

    def test_resend_otp_serializer_invalid(self):
        data = {"token": "invalid-uuid"}
        serializer = ResendOTPSerializer(data=data)
        assert not serializer.is_valid()
        assert "token" in serializer.errors
