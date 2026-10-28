from django.shortcuts import get_object_or_404
from rest_framework import viewsets
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
from core.api.utils import internal_error_response


class ProfileDetailViewSet(viewsets.ViewSet):
    """Retrieve any profile and let owners partially update their own."""

    def get_profile(self, pk):
        """Return the profile of user `pk` or raise 404."""
        return get_object_or_404(Profile.objects.select_related('user'), user_id=pk)

    def retrieve(self, request, pk=None):
        """Return the serialized profile of user `pk`."""
        profile = self.get_profile(pk)
        try:
            data = ProfileDetailSerializer(profile).data
        except Exception:
            return internal_error_response('Profile read failed due to an internal error.')
        return Response(data)

    def partial_update(self, request, pk=None):
        """Update the requester's own profile and return the updated profile."""
        profile = self.get_profile(pk)
        if profile.user_id != request.user.pk:
            raise PermissionDenied('You may only update your own profile.')
        serializer = self.update_serializer(request, profile)
        return self.save_profile_update(serializer)

    def update_serializer(self, request, profile):
        """Return a validated update serializer for the request data."""
        serializer = ProfileUpdateSerializer(
            data=request.data,
            context={'profile': profile, 'user': request.user},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        return serializer

    def save_profile_update(self, serializer):
        """Persist the update and return profile data or a sanitized 500 response."""
        try:
            data = ProfileDetailSerializer(serializer.update_profile()).data
        except APIException:
            raise
        except Exception:
            return internal_error_response('Profile update failed due to an internal error.')
        return Response(data)


class ProfileCollectionViewSet(viewsets.ViewSet):
    """List business and customer profiles."""

    @action(detail=False, methods=['get'], url_path='business')
    def business(self, request):
        """Return all business profiles."""
        return self.list_profiles(
            User.UserType.BUSINESS,
            BusinessProfileListSerializer,
            'Business profile list failed due to an internal error.',
        )

    @action(detail=False, methods=['get'], url_path='customer')
    def customer(self, request):
        """Return all customer profiles."""
        return self.list_profiles(
            User.UserType.CUSTOMER,
            CustomerProfileListSerializer,
            'Customer profile list failed due to an internal error.',
        )

    def list_profiles(self, user_type, serializer_class, error_message):
        """Serialize all profiles of `user_type` or return a sanitized 500 response."""
        try:
            profiles = Profile.objects.select_related('user').filter(user__type=user_type)
            data = serializer_class(profiles, many=True).data
        except APIException:
            raise
        except Exception:
            return internal_error_response(error_message)
        return Response(data)
