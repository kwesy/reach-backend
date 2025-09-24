from oauth.models.otp import OTP, create_otp, generate_otp, hash_otp
from rest_framework import status, permissions, filters, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import NotFound, ValidationError, AuthenticationFailed
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta

from services.services import send_email
from .models.user import User
from .serializers import EmailOTPSerializer, ResendOTPSerializer, UserSerializer
from common.mixins.response import StandardResponseView
import logging

logger = logging.getLogger("error")

class RegisterView(StandardResponseView):
    permission_classes = [permissions.AllowAny]
    success_message = "User registered successfully"

    def post(self, request):
        data = request.data
        required_fields = ['email', 'password', 'phone_number', 'first_name']

        for field in required_fields:
            if field not in data:
                raise ValidationError({"detial": f'{field}: This field is required.'})

        if User.objects.filter(email=data['email']).exists():
            raise ValidationError({'detail': 'User with this email already exists.'})

        code, otp_obj = create_otp(user=data['email'], purpose='signup', expires_in=600)
        user = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            email_otp = otp_obj
        )

        # Send OTP to email
        try:
            send_email(
                subject="Reach Signup Verification",
                template_name="emails/email_verification.html",
                context={"name": user.first_name, "otp_code": code},
                recipient_list=[user.email],
            )
            
        except Exception as e:
            user.delete()
            logger.error(f"Error sending OTP email: {e}", exc_info=True)
            raise ValidationError({'detail': 'Failed to send OTP email. Please try again later.'})
        
        return Response({'email': user.email, 'token': otp_obj.id}, status=201)
    
# Email OTP confirmation view
class EmailOTPVerificationView(StandardResponseView, generics.CreateAPIView):
    serializer_class = EmailOTPSerializer
    permission_classes = []

    def post(self, request):
        self.success_message = "OTP confirmed successfully"
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        email = serializer.validated_data.get('email')
        code = serializer.validated_data.get('code')

        try:
            user = get_user_model().objects.get(email=email)

            # Verify the OTP code
            if user and not user.email_verified and user.email_otp.verify(code):
                user.email_verified = True
                user.save()

                try:
                    send_email(
                        subject="Welcome to Reach",
                        template_name="emails/welcome.html",
                        context={
                            "name": user.first_name,
                            "dashboard_url": "https://reach.com/dashboard",
                            "year": 2025,
                        },
                        recipient_list=[user.email],
                    )
                    
                except Exception as e:
                    logger.error(f"Error sending Welcome email: {e}", exc_info=True)
                    #TODO: Handle email sending failure (optional)
                
                return Response({"detail": "OTP confirmed successfully"}, status=status.HTTP_200_OK)
            
            raise ValidationError({"detail": "Invalid OTP code or Expired"})
            
        except get_user_model().DoesNotExist:
            return NotFound({"detail": "User not found"})
        
#Unauthenticated OTP Resend View
class ResendOTPView(StandardResponseView):
    permission_classes = []
    serializer_class = ResendOTPSerializer

    def post(self, request):
        self.success_message = "OTP resent successfully."
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            raise ValidationError({'detail': serializer.errors})
        
        token = serializer.validated_data.get('token')
        otp = get_object_or_404(OTP, id=token, is_used=False)
        
        # limit resend interval
        if (timezone.now() - otp.updated_at) < timedelta(minutes=1):
            raise ValidationError({'detail': f'OTP can only be resent after {timedelta(minutes=1).seconds-(timezone.now() - otp.updated_at).seconds} Seconds.'})
        
        # Generate new OTP code
        code = generate_otp(6)
        otp.code_hash = hash_otp(code)
        otp.save()

        # Send OTP to email
        try:
            send_email(
                subject="OTP Verification",
                template_name="emails/email_verification.html",
                context={"name": "", "otp_code": code},
                recipient_list=[otp.user],
            )
            
        except Exception as e:
            logger.error(f"Error sending OTP email: {e}", exc_info=True)
            raise ValidationError({'detail': 'Failed to send OTP email. Please try again later.'})

        #TODO: Integrate with SMS service to send the OTP code to the user's email or phone number
        return Response(status=status.HTTP_205_RESET_CONTENT)

class LoginView( StandardResponseView):
    permission_classes = [permissions.AllowAny]
    success_message = "User logged in successfully"

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)

        if not user:
            raise AuthenticationFailed({'detail': 'Invalid credentials'})
        
        if not user.email_verified:
            raise PermissionDenied("Please verify your account to continue.")

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })

class LogoutView(StandardResponseView):
    permission_classes = [permissions.IsAuthenticated]
    success_message = "User logged out successfully"
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            raise ValidationError({'detail': 'Invalid token'})  
    
class UpdateUserView(StandardResponseView):
    permission_classes = [permissions.IsAuthenticated]
    success_message = "User updated successfully"

    def patch(self, request):
        user = request.user
        data = request.data
        
        if 'organization_name' in data:
            user.organization_name = data['organization_name']
        
        user.save()
        return Response(UserSerializer(user).data)

class MeView(StandardResponseView):
    permission_classes = [permissions.IsAuthenticated]
    success_message = {"GET": "User details fetched successfully"}

    def get(self, request):
        return Response(UserSerializer(request.user).data)


#Password Reset via Token (Simple Version)
#For now, assume we send the reset link manually (or via a separate email service).


from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model

class RequestPasswordReset(StandardResponseView):
    permission_classes = [permissions.AllowAny]
    success_message = {"POST": "Password reset token generated successfully"}

    def post(self, request):
        email = request.data.get('email')
        user = get_user_model().objects.filter(email=email).first()
        if user:
            token = default_token_generator.make_token(user)
            return Response({
                "uid": user.pk,
                "token": token
            })
        raise NotFound({'detail': 'User not found'})

class ConfirmPasswordReset(StandardResponseView):
    permission_classes = [permissions.AllowAny]
    # success_message = "Password reset successful"

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        try:
            user = get_user_model().objects.get(pk=uid)
            if not default_token_generator.check_token(user, token):
                raise ValidationError({'detail': 'Invalid token'})

            user.set_password(new_password)
            user.save()
            return Response({'detail': 'Password reset successful'}, status=200)
        except Exception:
            raise ValidationError({'detail': 'Invalid request'})
