import logging

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.response import Response

from accounts_app.api.profile_serializers import (
    BusinessProfileListSerializer,
    CustomerProfileListSerializer,
    ProfileDetailSerializer,
    ProfileUpdateSerializer,
)
from accounts_app.models import Profile, User


logger = logging.getLogger(__name__)


class ProfileDetailViewSet(viewsets.ViewSet):
    def get_profile(self, pk):
        return get_object_or_404(
            Profile.objects.select_related('user'),
            user_id=pk,
        )

    def retrieve(self, request, pk=None):
        profile = self.get_profile(pk)
        try:
            data = ProfileDetailSerializer(profile).data
        except Exception:
            logger.exception('Profile read failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)

    def partial_update(self, request, pk=None):
        profile = self.get_profile(pk)
        if profile.user_id != request.user.pk:
            raise PermissionDenied('You may only update your own profile.')

        serializer = ProfileUpdateSerializer(
            data=request.data,
            context={'profile': profile, 'user': request.user},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        try:
            profile = serializer.update_profile()
            data = ProfileDetailSerializer(profile).data
        except APIException:
            raise
        except Exception:
            logger.exception('Profile update failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)


class ProfileCollectionViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='business')
    def business(self, request):
        try:
            profiles = Profile.objects.select_related('user').filter(
                user__type=User.UserType.BUSINESS
            )
            data = BusinessProfileListSerializer(profiles, many=True).data
        except APIException:
            raise
        except Exception:
            logger.exception('Business profile list failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)


    @action(detail=False, methods=['get'], url_path='customer')
    def customer(self, request):
        try:
            profiles = Profile.objects.select_related('user').filter(
                user__type=User.UserType.CUSTOMER
            )
            data = CustomerProfileListSerializer(profiles, many=True).data
        except APIException:
            raise
        except Exception:
            logger.exception('Customer profile list failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)
