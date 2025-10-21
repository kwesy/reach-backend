from django.shortcuts import render

from common.mixins.response import StandardResponseView
from django.contrib.auth import authenticate
from oauth.models.otp import create_otp
from oauth.models.user import User
from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from oauth.serializers import UserSerializer
from services.services import send_email
import logging

logger = logging.getLogger("error")

# Create your views here.
class LoginView( StandardResponseView):
    permission_classes = [permissions.AllowAny]
    success_message = "Admin logged in successfully"

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if User.objects.filter(email=email, role='admin').count() == 0:
            raise AuthenticationFailed({'detail': 'Invalid credentials'})
        
        user = authenticate(request, email=email, password=password)

        if not user or not user.is_active:
            raise AuthenticationFailed({'detail': 'Invalid credentials'})
        
        if not user.email_verified:
            raise PermissionDenied("Please verify your account to continue")
        
        if user.mfa_enabled:
            code, otp_obj = create_otp(user=user.email, purpose='mfa')
            user.email_otp = otp_obj
            user.save(update_fields=['email_otp'])

            try:
                send_email.delay(
                    subject="MFA Verification",
                    template_name="emails/mfa_verification.html",
                    context={"name": user.first_name, "otp_code": code},
                    recipient_list=[user.email],
                )
            except Exception as e:
                logger.error(f"Error sending MFA email: {e}", exc_info=True)
                raise ValidationError({'detail': 'Failed to send MFA email. Please try again later.'})
            
            return Response({'mfa_required': user.mfa_enabled, 'token': otp_obj.id}, status=200)


        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'mfa_required': user.mfa_enabled
        })
    