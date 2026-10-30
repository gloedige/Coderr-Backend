from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from profile_app.api.serializers import (
    BusinessProfileListSerializer,
    CustomerProfileListSerializer,
    ProfileDetailSerializer,
    ProfileUpdateSerializer,
)
from auth_app.models import User
from profile_app.models import Profile
from core.utils import handle_internal_errors


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve any profile and let owners partially update their own."""

    serializer_class = ProfileDetailSerializer
    lookup_field = 'user_id'
    lookup_url_kwarg = 'pk'
    http_method_names = ('get', 'patch', 'head', 'options')

    def get_queryset(self):
        """Return all profiles with their users preloaded."""
        return Profile.objects.select_related('user')

    def retrieve(self, request, *args, **kwargs):
        """Return the serialized profile of user `pk`."""
        return self.profile_response(self.get_object())

    @handle_internal_errors('Profile read failed due to an internal error.')
    def profile_response(self, profile):
        """Serialize `profile`."""
        return Response(self.get_serializer(profile).data)

    def partial_update(self, request, *args, **kwargs):
        """Update the requester's own profile and return the updated profile."""
        profile = self.get_object()
        if profile.user_id != request.user.pk:
            raise PermissionDenied('You may only update your own profile.')
        serializer = ProfileUpdateSerializer(
            data=request.data,
            context={'profile': profile, 'user': request.user},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        return self.save_profile_update(serializer)

    @handle_internal_errors('Profile update failed due to an internal error.')
    def save_profile_update(self, serializer):
        """Persist the update and return the updated profile."""
        return Response(ProfileDetailSerializer(serializer.update_profile()).data)


class ProfileListView(generics.ListAPIView):
    """Base view listing the profiles of one user type."""

    user_type = None
    error_message = 'Profile list failed due to an internal error.'

    def get_queryset(self):
        """Return the profiles whose user has `user_type`."""
        return Profile.objects.select_related('user').filter(user__type=self.user_type)

    def list(self, request, *args, **kwargs):
        """Return all profiles of `user_type`, sanitizing unexpected failures."""
        return handle_internal_errors(self.error_message)(super().list)(request, *args, **kwargs)


class BusinessProfileListView(ProfileListView):
    """List all business profiles."""

    user_type = User.UserType.BUSINESS
    serializer_class = BusinessProfileListSerializer
    error_message = 'Business profile list failed due to an internal error.'


class CustomerProfileListView(ProfileListView):
    """List all customer profiles."""

    user_type = User.UserType.CUSTOMER
    serializer_class = CustomerProfileListSerializer
    error_message = 'Customer profile list failed due to an internal error.'
