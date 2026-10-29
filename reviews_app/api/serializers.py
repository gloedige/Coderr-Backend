from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import serializers

from core.serializers import APIModelSerializer
from orders_app.models import Order
from reviews_app.models import Review


User = get_user_model()


def has_completed_order(customer, business):
    """Return whether the customer has a completed order with this business."""
    return Order.objects.filter(
        customer_user=customer,
        business_user=business,
        status=Order.Status.COMPLETED,
    ).exists()


def review_exists(customer, business):
    """Return whether this customer-business pair already has an active review."""
    return Review.objects.filter(reviewer=customer, business_user=business).exists()


def get_business_user(user_id):
    """Resolve a user ID to a business account or raise a field validation error."""
    try:
        return User.objects.get(pk=user_id, type=User.UserType.BUSINESS)
    except User.DoesNotExist as exc:
        raise serializers.ValidationError('A valid business user is required.') from exc


def validate_review_eligibility(customer, business):
    """Require a completed matching order and no existing active review."""
    if not has_completed_order(customer, business):
        raise serializers.ValidationError(
            {'business_user': 'A completed order with this business user is required.'}
        )
    if review_exists(customer, business):
        raise serializers.ValidationError(
            {'business_user': 'You have already reviewed this business user.'}
        )


def create_review(customer, business, validated_data):
    """Atomically create a review, translating concurrent duplicates to validation errors."""
    try:
        with transaction.atomic():
            return Review.objects.create(
                reviewer=customer,
                business_user=business,
                **validated_data,
            )
    except IntegrityError as exc:
        raise serializers.ValidationError(
            {'business_user': 'You have already reviewed this business user.'}
        ) from exc


class ReviewReadSerializer(APIModelSerializer):
    """Serialize review fields returned by list, create, and update endpoints."""

    class Meta:
        """Expose all review fields as read-only."""

        model = Review
        fields = (
            'id',
            'business_user',
            'reviewer',
            'rating',
            'description',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ReviewCreateSerializer(serializers.Serializer):
    """Validate and create reviews from eligible customer accounts."""

    business_user = serializers.IntegerField(min_value=1)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    description = serializers.CharField(min_length=1, max_length=500, allow_blank=False)

    def validate_business_user(self, value):
        """Resolve the requested ID to an existing business account."""
        return get_business_user(value)

    def validate(self, attrs):
        """Require a completed order and reject duplicate customer-business reviews."""
        customer = self.context['request'].user
        business = attrs['business_user']
        validate_review_eligibility(customer, business)
        return attrs

    def create(self, validated_data):
        """Persist the validated review for the authenticated customer."""
        business = validated_data.pop('business_user')
        customer = self.context['request'].user
        return create_review(customer, business, validated_data)


class ReviewUpdateSerializer(serializers.Serializer):
    """Validate and apply partial reviewer edits to rating and description."""

    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    description = serializers.CharField(
        min_length=1,
        max_length=500,
        allow_blank=False,
        required=False,
    )

    def validate(self, attrs):
        """Reject unsupported fields and empty PATCH requests."""
        self.reject_unexpected_fields()
        self.require_editable_value(attrs)
        return attrs

    def reject_unexpected_fields(self):
        """Reject PATCH keys outside the editable review fields."""
        unexpected_fields = set(self.initial_data) - {'rating', 'description'}
        if unexpected_fields:
            raise serializers.ValidationError(
                {
                    field: 'This field cannot be updated.'
                    for field in sorted(unexpected_fields)
                }
            )

    def require_editable_value(self, attrs):
        """Require at least one editable field in the PATCH payload."""
        if not attrs:
            raise serializers.ValidationError('At least one editable field is required.')

    def update_review(self):
        """Apply validated fields to the target review and update its timestamp."""
        review = self.context['review']
        self.apply_changes(review)
        review.save(update_fields=[*self.validated_data, 'updated_at'])
        return review

    def apply_changes(self, review):
        """Assign only fields accepted by the update serializer."""
        for field, value in self.validated_data.items():
            setattr(review, field, value)
