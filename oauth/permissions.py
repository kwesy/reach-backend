from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """
    Custom permission to only allow admin users.
    You can modify the logic as needed.
    """
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and (user.role == 'admin' or user.is_superuser)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        # Allow read for everyone
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # Only admin users can write
        return request.user and request.user.is_authenticated and (request.user.role == 'admin' or request.user.is_superuser)
