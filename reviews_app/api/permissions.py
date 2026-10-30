# Third-party
from rest_framework.permissions import SAFE_METHODS, BasePermission

# Local imports
from auth_app.models import User


class IsCustomerUser(BasePermission):
    """Allow only authenticated users with the customer role."""

    message = 'Only customer users may create reviews.'

    def has_permission(self, request, view):
        """Return True for authenticated customers."""
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.type == User.UserType.CUSTOMER
        )


class IsReviewCreatorOrReadOnly(BasePermission):
    """Allow reads for everyone and modifications only for the review creator."""

    message = 'Only the review creator may modify this review.'

    def has_object_permission(self, request, view, obj):
        """Return True for safe methods or when the requester wrote `obj`."""
        if request.method in SAFE_METHODS:
            return True
        return obj.reviewer_id == request.user.pk
