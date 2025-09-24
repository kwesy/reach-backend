import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import secrets
import hashlib
from datetime import timedelta


class OTP(models.Model):
    PURPOSE_CHOICES = [
        ('signup', 'Signup'),
        ('login', 'Login'),
        ('mfa', 'MFA'),
        ('transaction', 'Transaction'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.CharField(max_length=255)  # Can store email or phone number
    code_hash = models.CharField(max_length=128)  # Store OTP hash, not OTP
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    meta = models.JSONField(blank=True, null=True)  # to store tx_id, etc.
    attempts = models.IntegerField(default=0)

    def is_valid(self):
        return (
            not self.is_used
            and timezone.now() < self.expires_at
            and self.attempts < 5
        )
    
    def verify(self, code: str):

        if not self.is_valid():
            return False

        # Check if OTP is valid
        if self.code_hash != hash_otp(code):
            self.attempts += 1
            self.save(update_fields=["attempts"])
            return False

        self.is_used = True
        self.save(update_fields=["is_used"])
        return True

    
def generate_otp(length=6):
    return ''.join(secrets.choice('0123456789') for _ in range(length))

def hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

def create_otp(user, purpose: str, expires_in=300, meta=None):
    code = generate_otp()
    otp = OTP.objects.create(
        user=user,
        code_hash=hash_otp(code),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(seconds=expires_in),
        meta=meta or {},
    )
    return code, otp
