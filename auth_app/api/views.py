from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.api.serializers import LoginSerializer, RegistrationSerializer
from core.utils import internal_error_response


PUBLIC_PERMISSIONS = (AllowAny,)


def authentication_response(user, token):
    """Return the token response body for `user` and `token`."""
    return {
        'token': token.key,
        'username': user.username,
        'email': user.email,
        'user_id': user.pk,
    }


class RegistrationView(APIView):
    """Register a new customer or business account."""

    permission_classes = PUBLIC_PERMISSIONS

    def post(self, request):
        """Create the account and return 201 with token data or a sanitized 500."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user, token = serializer.save()
        except APIException:
            raise
        except Exception:
            return internal_error_response('Registration failed due to an internal error.')
        return Response(authentication_response(user, token), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Authenticate a user and return a token."""

    permission_classes = PUBLIC_PERMISSIONS

    def post(self, request):
        """Validate credentials and return the token response."""
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user, token = serializer.save()
        return Response(authentication_response(user, token))
