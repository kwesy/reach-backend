from rest_framework import viewsets
from django.contrib.auth import get_user_model
from superadmin.serializers.user import AdminUserSerializer
from oauth.permissions import IsAdmin

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['email', 'is_active', 'role', 'phone_number']

    def destroy(self, request, *args, **kwargs):
        raise NotImplementedError("Users cannot be deleted via this viewset.")
