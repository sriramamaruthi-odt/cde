from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PhoneOTP
from .serializers import OTPRequestSerializer, OTPVerifySerializer, UserProfileSerializer


class RequestOTPView(APIView):
    """POST {phone_number} -> issues a fresh OTP for that number."""

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]

        otp = PhoneOTP.issue(phone_number)
        # TODO: send `otp.code` via SMS gateway once a provider is chosen.

        return Response(
            {"detail": "OTP sent.", "expires_at": otp.expires_at},
            status=status.HTTP_201_CREATED,
        )


class VerifyOTPView(APIView):
    """POST {phone_number, code} -> marks the pending OTP for that number verified."""

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        code = serializer.validated_data["code"]

        otp = (
            PhoneOTP.objects.filter(phone_number=phone_number, is_verified=False)
            .order_by("-created_at")
            .first()
        )
        if otp is None:
            return Response(
                {"detail": "No pending OTP for this number."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not otp.verify(code):
            return Response(
                {"detail": "Incorrect or expired code."}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"detail": "Phone number verified."}, status=status.HTTP_200_OK)


class UserProfileCreateView(generics.CreateAPIView):
    """POST the full registration form. Requires phone_number to already be OTP-verified."""

    serializer_class = UserProfileSerializer
