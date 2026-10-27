import logging

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts_app.models import User
from marketplace_app.api.order_serializers import (
    OrderCreateSerializer,
    OrderReadSerializer,
    OrderStatusUpdateSerializer,
)
from marketplace_app.models import Order


logger = logging.getLogger(__name__)


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrderReadSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    def get_queryset(self):
        queryset = Order.objects.select_related('customer_user', 'business_user')
        if self.action == 'destroy' and self.request.user.is_staff:
            return queryset
        if self.action == 'partial_update':
            return queryset
        return queryset.filter(
            Q(customer_user_id=self.request.user.pk)
            | Q(business_user_id=self.request.user.pk)
        )

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsCustomerUser()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsAdminUser()]
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            order = serializer.save()
            data = OrderReadSerializer(order).data
        except APIException:
            raise
        except Exception:
            logger.exception('Order creation failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset()).order_by(
                '-created_at', '-pk'
            )
            return Response(OrderReadSerializer(queryset, many=True).data)
        except APIException:
            raise
        except Exception:
            logger.exception('Order list failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        order = self.get_object()
        if order.business_user_id != request.user.pk or request.user.type != User.UserType.BUSINESS:
            raise PermissionDenied('Only the assigned business user may update this order.')
        serializer = OrderStatusUpdateSerializer(
            data=request.data,
            context={'order': order},
        )
        serializer.is_valid(raise_exception=True)
        try:
            order = serializer.update_status()
            data = OrderReadSerializer(order).data
        except APIException:
            raise
        except Exception:
            logger.exception('Order status update failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            order.delete()
        except Exception:
            logger.exception('Order deletion failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class IsCustomerUser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.type == User.UserType.CUSTOMER


class OrderCountView(APIView):
    permission_classes = (IsAuthenticated,)
    count_field = 'order_count'
    order_status = Order.Status.IN_PROGRESS

    def get(self, request, business_user_id):
        business_user = get_object_or_404(
            User,
            pk=business_user_id,
            type=User.UserType.BUSINESS,
        )
        try:
            count = Order.objects.filter(
                business_user=business_user,
                status=self.order_status,
            ).count()
        except Exception:
            logger.exception('Order count failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({self.count_field: count})


class CompletedOrderCountView(OrderCountView):
    count_field = 'completed_order_count'
    order_status = Order.Status.COMPLETED
