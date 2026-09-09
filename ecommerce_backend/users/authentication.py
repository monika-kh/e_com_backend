from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # First support the standard Authorization: Bearer <token> header.
        authenticated = super().authenticate(request)
        if authenticated is not None:
            return authenticated

        # Also support the application's JWT cookie naming conventions.
        raw_token = request.COOKIES.get("access_token") or request.COOKIES.get("access-token")
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
