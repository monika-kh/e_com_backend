from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Address


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("email", "username", "phone", "password")

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "Mobile number already registered"
            )
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            phone=validated_data.get("phone"),
            password=validated_data["password"],
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            email=data["email"],
            password=data["password"]
        )

        if not user:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")

        data["user"] = user
        return data

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "phone", "first_name", "last_name"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "full_name",
            "phone",
            "address_line",
            "city",
            "state",
            "pincode",
            "is_default",
        ]
        read_only_fields = ["id"]

    def validate_full_name(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Full name is required.")
        if len(v) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters.")
        return v

    def validate_phone(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Phone is required.")
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) != 10:
            raise serializers.ValidationError("Phone must be exactly 10 digits.")
        return digits

    def validate_address_line(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Address line is required.")
        return v

    def validate_city(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("City is required.")
        return v

    def validate_state(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("State is required.")
        return v

    def validate_pincode(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Pincode is required.")
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 5:
            raise serializers.ValidationError("Pincode must contain at least 5 digits.")
        return v