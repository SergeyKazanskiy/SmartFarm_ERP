from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.companies.models import User


class LoginSerializer(serializers.Serializer):
    """Логин по email + password. Возвращает access + refresh."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Неверный email или пароль")
        if not user.is_active:
            raise serializers.ValidationError("Пользователь деактивирован")
        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserProfileSerializer(user).data,
        }


class UserProfileSerializer(serializers.ModelSerializer):
    companies = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "hr_employee_id",
            "current_company", "companies", "preferred_language",
        ]
        read_only_fields = fields

    def get_companies(self, obj):
        return [
            {"id": c.id, "name": c.name, "short_name": c.short_name}
            for c in obj.companies.all()
        ]


class SwitchCompanySerializer(serializers.Serializer):
    company_id = serializers.IntegerField()

    def validate_company_id(self, value):
        user = self.context["request"].user
        if not user.companies.filter(pk=value).exists():
            raise serializers.ValidationError("Компания недоступна")
        return value