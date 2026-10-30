# Third-party
from rest_framework.permissions import BasePermission, IsAuthenticated

# Local imports
from auth_app.models import User


class IsCustomerUser(IsAuthenticated):
    """Allow only authenticated users with the customer role."""

    def has_permission(self, request, view):
        """Return True for authenticated customers."""
        return super().has_permission(request, view) and request.user.type == User.UserType.CUSTOMER


class IsAssignedBusinessUser(BasePermission):
    """Allow only the business user an order is assigned to."""

    message = 'Only the assigned business user may update this order.'

    def has_object_permission(self, request, view, obj):
        """Return True when the requester is the order's business user."""
        return (
            obj.business_user_id == request.user.pk
            and request.user.type == User.UserType.BUSINESS
        )
