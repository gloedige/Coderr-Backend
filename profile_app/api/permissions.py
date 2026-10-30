# Third-party
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsProfileOwnerOrReadOnly(BasePermission):
    """Allow reads for everyone and modifications only for the profile owner."""

    message = 'You may only update your own profile.'

    def has_object_permission(self, request, view, obj):
        """Return True for safe methods or when the requester owns `obj`."""
        if request.method in SAFE_METHODS:
            return True
        return obj.user_id == request.user.pk
