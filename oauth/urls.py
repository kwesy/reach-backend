from django.urls import path
from oauth.views import EmailOTPVerificationView, LoginView, LogoutView, RegisterView, ResendOTPView


app_name = 'oauth'

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/register/otp-verify', EmailOTPVerificationView.as_view(), name='verify-otp'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    # path('auth/update/', UpdateUserView.as_view(), name='update-user'),
    # path('auth/me/', MeView.as_view(), name='me'),
    # path('auth/request-password-reset/', RequestPasswordReset.as_view(), name='request-password-reset'),
    # path('auth/confirm-password-reset/', ConfirmPasswordReset.as_view(), name='confirm-password-reset'),
]