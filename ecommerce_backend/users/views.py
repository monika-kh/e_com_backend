from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer, AddressSerializer
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from .models import Address
from django.shortcuts import get_object_or_404


class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            serializer = RegisterSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "User registered successfully"},
                    status=status.HTTP_201_CREATED
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# class LoginAPIView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def post(self, request):
#         try:
#             serializer = LoginSerializer(data=request.data)
#             serializer.is_valid(raise_exception=True)

#             user = serializer.validated_data["user"]
#             refresh = RefreshToken.for_user(user)

#             return Response({
#                 "access": str(refresh.access_token),
#                 "refresh": str(refresh),
#                 "user": {
#                     "id": user.id,
#                     "email": user.email,
#                     "username": user.username,
#                 }
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response(
#                 {"error": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST
#             )


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        response = Response(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                }
            },
            status=status.HTTP_200_OK
        )

        # ✅ Access Token Cookie (short-lived)
        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,
            secure=request.is_secure(),  # don't block cookies on http:// in dev
            samesite="Lax",
            max_age=60 * 60       # 60 minutes (align with SIMPLE_JWT)
        )

        # ✅ Refresh Token Cookie (long-lived)
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=request.is_secure(),
            samesite="Lax",
            max_age=60 * 60 * 24 * 7  # 7 days
        )

        return response


class ProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        try:
            serializer = ProfileSerializer(
                instance=request.user,
                data=request.data,
            )
            if not serializer.is_valid():
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutAPIView(APIView):
    def post(self, request):
        response = Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK
        )
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


class RefreshAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token") or request.COOKIES.get("refresh-token")
        if not refresh_token:
            return Response({"error": "Refresh token missing"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
        except Exception:
            return Response({"error": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        response = Response({"message": "Token refreshed"}, status=status.HTTP_200_OK)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=request.is_secure(),
            samesite="Lax",
            max_age=60 * 60,
        )
        return response


class UserAddressListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            qs = Address.objects.filter(user=request.user).order_by("-id")
            serializer = AddressSerializer(qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        try:
            serializer = AddressSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            address = serializer.save(user=request.user)
            return Response(
                AddressSerializer(address).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserAddressDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, address_id: int):
        try:
            address = get_object_or_404(Address, id=address_id, user=request.user)
            address.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserAddressUpdateAPIView(APIView):
    """
    Update an existing address for the authenticated user.
    Only the owner can update. Supports partial updates via PATCH.
    """

    permission_classes = [IsAuthenticated]

    def put(self, request, address_id: int):
        return self._update(request, address_id, partial=False)

    def patch(self, request, address_id: int):
        return self._update(request, address_id, partial=True)

    def _update(self, request, address_id: int, partial: bool):
        try:
            address = get_object_or_404(Address, id=address_id, user=request.user)

            serializer = AddressSerializer(address, data=request.data, partial=partial)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )