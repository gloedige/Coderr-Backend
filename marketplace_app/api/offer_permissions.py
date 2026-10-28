from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsBusinessUser(BasePermission):
    """Allow only authenticated users with the business role."""

    message = 'Only business users may create offers.'

    def has_permission(self, request, view):
        """Return True for authenticated business users."""
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.type == 'business'
        )


class IsOfferOwnerOrReadOnly(BasePermission):
    """Allow reads for everyone and modifications only for the offer creator."""

    message = 'Only the offer creator may modify or delete this offer.'

    def has_object_permission(self, request, view, obj):
        """Return True for safe methods or when the requester owns `obj`."""
        if request.method in SAFE_METHODS:
            return True
        return obj.user_id == request.user.pk
