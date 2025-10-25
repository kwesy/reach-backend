from rest_framework import serializers
from .models.user import User

PAYMENT_METHOD_CHOICES = [('momo', 'Mobile Money'), ('card', 'Card'), ('bank', 'Bank')]
PROVIDER_CHOICES = [('mtn', 'MTN'), ('airtel', 'Airtel'), ('telecel', 'Telecel')]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'first_name', 'last_name', 'email_verified', 'is_active', 'role'] #'transfer_allowed', 'transfer_limit',

    def update(self, instance, validated_data):
        
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()
        return instance
    
    def create(self, validated_data):
        raise NotImplementedError("User creation is not handled via this serializer.")
    
    def delete(self, instance):
        raise NotImplementedError("Users cannot be deleted via this serializer.")

# OTP Serializer for verifying OTP codes and resending OTPs
class EmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6 , max_length=6)

    class Meta:
        model = None
        fields = [
            'code', 'email'
        ]

class ResendOTPSerializer(serializers.Serializer):
    token = serializers.UUIDField()

    class Meta:
        model = None
        fields = ['token']


