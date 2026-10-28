from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts_app.models import User
from core.api.utils import handle_internal_errors
from marketplace_app.api.order_serializers import (
    OrderCreateSerializer,
    OrderReadSerializer,
    OrderStatusUpdateSerializer,
)
from marketplace_app.models import Order


class IsCustomerUser(IsAuthenticated):
    """Allow only authenticated users with the customer role."""

    def has_permission(self, request, view):
        """Return True for authenticated customers."""
        return super().has_permission(request, view) and request.user.type == User.UserType.CUSTOMER


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """List, create, update the status of, and delete orders."""

    serializer_class = OrderReadSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    def get_queryset(self):
        """Return orders visible for the action: all for staff delete/patch, else own orders."""
        queryset = Order.objects.select_related('customer_user', 'business_user')
        if self.action == 'destroy' and self.request.user.is_staff:
            return queryset
        if self.action == 'partial_update':
            return queryset
        return queryset.filter(
            Q(customer_user_id=self.request.user.pk) | Q(business_user_id=self.request.user.pk)
        )

    def get_permissions(self):
        """Return role-specific permissions for create and destroy."""
        if self.action == 'create':
            return [IsAuthenticated(), IsCustomerUser()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsAdminUser()]
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        """Create an order from an offer detail for the requesting customer."""
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return self.save_order(serializer)

    @handle_internal_errors('Order creation failed due to an internal error.')
    def save_order(self, serializer):
        """Persist the order and return 201 with its data."""
        data = OrderReadSerializer(serializer.save()).data
        return Response(data, status=status.HTTP_201_CREATED)

    @handle_internal_errors('Order list failed due to an internal error.')
    def list(self, request, *args, **kwargs):
        """Return the requester's orders, newest first."""
        queryset = self.filter_queryset(self.get_queryset()).order_by('-created_at', '-pk')
        return Response(OrderReadSerializer(queryset, many=True).data)

    def partial_update(self, request, *args, **kwargs):
        """Update an order status as its assigned business user."""
        order = self.get_object()
        if order.business_user_id != request.user.pk or request.user.type != User.UserType.BUSINESS:
            raise PermissionDenied('Only the assigned business user may update this order.')
        serializer = OrderStatusUpdateSerializer(data=request.data, context={'order': order})
        serializer.is_valid(raise_exception=True)
        return self.save_status(serializer)

    @handle_internal_errors('Order status update failed due to an internal error.')
    def save_status(self, serializer):
        """Persist the status change and return the updated order."""
        return Response(OrderReadSerializer(serializer.update_status()).data)

    def destroy(self, request, *args, **kwargs):
        """Delete the order (staff only) and return 204."""
        return self.delete_order(self.get_object())

    @handle_internal_errors('Order deletion failed due to an internal error.')
    def delete_order(self, order):
        """Delete `order` and return an empty 204 response."""
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderCountView(APIView):
    """Return the number of in-progress orders for a business user."""

    permission_classes = (IsAuthenticated,)
    count_field = 'order_count'
    order_status = Order.Status.IN_PROGRESS

    def get(self, request, business_user_id):
        """Return the count for an existing business user or 404."""
        business_user = get_object_or_404(
            User, pk=business_user_id, type=User.UserType.BUSINESS
        )
        return self.count_response(business_user)

    @handle_internal_errors('Order count failed due to an internal error.')
    def count_response(self, business_user):
        """Return the order count of `business_user` for this view's status."""
        count = Order.objects.filter(business_user=business_user, status=self.order_status).count()
        return Response({self.count_field: count})


class CompletedOrderCountView(OrderCountView):
    """Return the number of completed orders for a business user."""

    count_field = 'completed_order_count'
    order_status = Order.Status.COMPLETED
