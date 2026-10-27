from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsBusinessUser(BasePermission):
    message = 'Only business users may create offers.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.type == 'business'
        )


class IsOfferOwnerOrReadOnly(BasePermission):
    message = 'Only the offer creator may modify or delete this offer.'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user_id == request.user.pk
