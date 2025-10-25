from rest_framework import serializers
from django.contrib.auth import get_user_model


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            'id', 
            'email', 
            'first_name', 
            'last_name',
            'phone_number',
            'is_active',
            'email_verified',
            'created_at',
            'updated_at',
            'mfa_enabled',
            'role',
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at']

    def create(self, validated_data):
        raise NotImplementedError("User creation is not handled via this serializer.")

    def delete(self, instance):
        raise NotImplementedError("Users cannot be deleted via this serializer.")
