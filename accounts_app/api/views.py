import logging

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts_app.api.serializers import LoginSerializer, RegistrationSerializer


logger = logging.getLogger(__name__)
PUBLIC_PERMISSIONS = (AllowAny,)


def authentication_response(user, token):
    return {
        'token': token.key,
        'username': user.username,
        'email': user.email,
        'user_id': user.pk,
    }


class RegistrationView(APIView):
    permission_classes = PUBLIC_PERMISSIONS

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user, token = serializer.save()
        except APIException:
            raise
        except Exception:
            logger.exception('Registration failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            authentication_response(user, token),
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = PUBLIC_PERMISSIONS

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user, token = serializer.save()
        return Response(authentication_response(user, token))
