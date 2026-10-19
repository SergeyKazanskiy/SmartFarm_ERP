from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.companies.api.serializers import (
    LoginSerializer, SwitchCompanySerializer, UserProfileSerializer,
)

# Эндпоинты аутентификации и профиля пользователя
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """POST /api/v1/auth/login/ — вход, возвращает JWT."""
    serializer = LoginSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    return Response(serializer.save(), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh(request):
    """POST /api/v1/auth/refresh/ — обновление access-токена."""
    token = request.data.get("refresh")
    if not token:
        return Response({"detail": "refresh required"}, status=400)
    try:
        refresh_token = RefreshToken(token)
        return Response({"access": str(refresh_token.access_token)})
    except Exception:
        return Response({"detail": "invalid token"}, status=401)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    """GET /api/v1/auth/profile/ — текущий пользователь."""
    return Response(UserProfileSerializer(request.user).data)

# Эндпоинт смены активной компании для пользователя
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def switch_company(request):
    """POST /api/v1/auth/switch-company/ — смена активной компании."""
    serializer = SwitchCompanySerializer(
        data=request.data, context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    request.user.current_company_id = serializer.validated_data["company_id"]
    request.user.save(update_fields=["current_company"])
    return Response(UserProfileSerializer(request.user).data)