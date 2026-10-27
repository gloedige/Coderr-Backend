from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import serializers

from marketplace_app.models import Order, Review


User = get_user_model()


class ReviewReadSerializer(serializers.ModelSerializer):
    class Meta:
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
    business_user = serializers.IntegerField(min_value=1)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    description = serializers.CharField(min_length=1, max_length=500, allow_blank=False)

    def validate_business_user(self, value):
        try:
            business = User.objects.get(pk=value, type=User.UserType.BUSINESS)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError('A valid business user is required.') from exc
        return business

    def validate(self, attrs):
        customer = self.context['request'].user
        business = attrs['business_user']
        eligible = Order.objects.filter(
            customer_user=customer,
            business_user=business,
            status=Order.Status.COMPLETED,
        ).exists()
        if not eligible:
            raise serializers.ValidationError(
                {'business_user': 'A completed order with this business user is required.'}
            )
        if Review.objects.filter(reviewer=customer, business_user=business).exists():
            raise serializers.ValidationError(
                {'business_user': 'You have already reviewed this business user.'}
            )
        return attrs

    def create(self, validated_data):
        business = validated_data.pop('business_user')
        customer = self.context['request'].user
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


class ReviewUpdateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    description = serializers.CharField(
        min_length=1,
        max_length=500,
        allow_blank=False,
        required=False,
    )

    def validate(self, attrs):
        unexpected_fields = set(self.initial_data) - {'rating', 'description'}
        if unexpected_fields:
            raise serializers.ValidationError(
                {
                    field: 'This field cannot be updated.'
                    for field in sorted(unexpected_fields)
                }
            )
        if not attrs:
            raise serializers.ValidationError('At least one editable field is required.')
        return attrs

    def update_review(self):
        review = self.context['review']
        for field, value in self.validated_data.items():
            setattr(review, field, value)
        review.save(update_fields=[*self.validated_data, 'updated_at'])
        return review
