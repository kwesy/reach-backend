from django.utils import timezone
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .otp import OTP

ROLE_CHOICES = (
    ('user', 'User'),
    ('admin', 'Admin'),
    ('manager', 'Manager'),
)

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "user")

        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("mfa_enabled", True)
        extra_fields.setdefault("email_verified", True)
        extra_fields.setdefault("role", "admin")

        # if extra_fields.get("is_staff") is not True:
        #     raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transfer_allowed = models.BooleanField(default=True)
    transfer_limit = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    email_otp = models.ForeignKey(OTP, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    mfa_enabled = models.BooleanField(default=False)
    role = models.CharField(choices=ROLE_CHOICES, default='user')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number']

    objects = UserManager()

    def __str__(self):
        return self.email
    