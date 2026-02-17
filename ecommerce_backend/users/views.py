from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer


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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

from .serializers import LoginSerializer


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
            secure=True,          # True in production (HTTPS)
            samesite="Lax",
            max_age=60 * 5        # 5 minutes
        )

        # ✅ Refresh Token Cookie (long-lived)
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=60 * 60 * 24 * 7  # 7 days
        )

        return response


class ProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)


class LogoutAPIView(APIView):
    def post(self, request):
        response = Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK
        )
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response