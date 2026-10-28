from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

from marketplace_app.models import OfferDetail, Order


ALLOWED_STATUS_TRANSITIONS = {
    Order.Status.IN_PROGRESS: {Order.Status.COMPLETED, Order.Status.CANCELLED},
}


def order_snapshot(detail):
    """Return the order field values copied from an offer detail at purchase time."""
    return {
        'title': detail.title,
        'revisions': detail.revisions,
        'delivery_time_in_days': detail.delivery_time_in_days,
        'price': detail.price,
        'features': list(detail.features),
        'offer_type': detail.offer_type,
    }


class OrderReadSerializer(serializers.ModelSerializer):
    """Serialize orders for list, create, and status-update responses."""

    class Meta:
        """Expose all order fields as read-only."""

        model = Order
        fields = (
            'id', 'customer_user', 'business_user', 'title', 'revisions',
            'delivery_time_in_days', 'price', 'features', 'offer_type',
            'status', 'created_at', 'updated_at',
        )
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    """Create an order snapshot from an offer detail."""

    offer_detail_id = serializers.IntegerField(min_value=1)

    def get_offer_detail(self, detail_id):
        """Return the offer detail with its offer owner or raise 404."""
        try:
            return OfferDetail.objects.select_related('offer', 'offer__user').get(pk=detail_id)
        except OfferDetail.DoesNotExist as exc:
            raise NotFound('The requested offer detail was not found.') from exc

    def create(self, validated_data):
        """Create the order for the requesting customer, rejecting self-purchases."""
        detail = self.get_offer_detail(validated_data['offer_detail_id'])
        customer = self.context['request'].user
        if detail.offer.user_id == customer.pk:
            raise ValidationError({'offer_detail_id': 'You cannot purchase your own offer.'})
        with transaction.atomic():
            return Order.objects.create(
                customer_user=customer,
                business_user=detail.offer.user,
                **order_snapshot(detail),
            )


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Validate and apply an order status transition."""

    status = serializers.ChoiceField(choices=Order.Status.choices)

    def validate(self, attrs):
        """Reject extra fields and transitions that are not allowed."""
        unexpected_fields = set(self.initial_data) - {'status'}
        if unexpected_fields:
            raise serializers.ValidationError(
                {field: 'This field cannot be updated.' for field in sorted(unexpected_fields)}
            )
        order = self.context['order']
        if attrs['status'] not in ALLOWED_STATUS_TRANSITIONS.get(order.status, set()):
            raise self.transition_error()
        return attrs

    def transition_error(self):
        """Return the validation error used for disallowed transitions."""
        return serializers.ValidationError({'status': 'This status transition is not allowed.'})

    def update_status(self):
        """Atomically move an in-progress order to the validated status and return it."""
        order = self.context['order']
        updated = Order.objects.filter(
            pk=order.pk, status=Order.Status.IN_PROGRESS
        ).update(status=self.validated_data['status'], updated_at=timezone.now())
        if not updated:
            raise self.transition_error()
        order.refresh_from_db()
        return order
