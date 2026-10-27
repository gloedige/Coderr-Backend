from rest_framework import serializers

from marketplace_app.models import OfferDetail, Order


class OrderReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            'id',
            'customer_user',
            'business_user',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
            'status',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    offer_detail_id = serializers.IntegerField(min_value=1)

    def create(self, validated_data):
        from django.db import transaction
        from rest_framework.exceptions import NotFound, ValidationError

        try:
            detail = OfferDetail.objects.select_related('offer', 'offer__user').get(
                pk=validated_data['offer_detail_id']
            )
        except OfferDetail.DoesNotExist as exc:
            raise NotFound('The requested offer detail was not found.') from exc

        customer = self.context['request'].user
        if detail.offer.user_id == customer.pk:
            raise ValidationError({'offer_detail_id': 'You cannot purchase your own offer.'})

        with transaction.atomic():
            return Order.objects.create(
                customer_user=customer,
                business_user=detail.offer.user,
                title=detail.title,
                revisions=detail.revisions,
                delivery_time_in_days=detail.delivery_time_in_days,
                price=detail.price,
                features=list(detail.features),
                offer_type=detail.offer_type,
            )


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)

    def validate(self, attrs):
        order = self.context['order']
        target_status = attrs['status']
        allowed_transitions = {
            Order.Status.IN_PROGRESS: {
                Order.Status.COMPLETED,
                Order.Status.CANCELLED,
            },
        }
        if target_status not in allowed_transitions.get(order.status, set()):
            raise serializers.ValidationError(
                {'status': 'This status transition is not allowed.'}
            )
        return attrs

    def update_status(self):
        from django.utils import timezone

        order = self.context['order']
        updated = Order.objects.filter(
            pk=order.pk,
            status=Order.Status.IN_PROGRESS,
        ).update(status=self.validated_data['status'], updated_at=timezone.now())
        if not updated:
            raise serializers.ValidationError(
                {'status': 'This status transition is not allowed.'}
            )
        order.refresh_from_db()
        return order
