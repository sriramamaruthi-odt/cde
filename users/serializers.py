from rest_framework import serializers

from .models import PhoneOTP, UserProfile

PHONE_NUMBER_REGEX = r"^\d{10}$"
OTP_CODE_REGEX = r"^\d{6}$"


class OTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(PHONE_NUMBER_REGEX)


class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.RegexField(PHONE_NUMBER_REGEX)
    code = serializers.RegexField(OTP_CODE_REGEX)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "name",
            "gender",
            "age",
            "phone_number",
            "location",
            "education",
            "languages",
            "photograph",
            "organization",
            "occupation",
            "no_of_projects",
            "no_of_households_touched",
            "skills",
            "key_projects",
            "impact_stories_count",
            "trust_level_notes",
            "audio_intro",
            "is_phone_verified",
            "created_at",
        ]
        read_only_fields = ["is_phone_verified", "created_at"]

    def validate_phone_number(self, value):
        if not PhoneOTP.objects.filter(phone_number=value, is_verified=True).exists():
            raise serializers.ValidationError("This phone number has not been verified via OTP.")
        return value

    def create(self, validated_data):
        validated_data["is_phone_verified"] = True
        return super().create(validated_data)
