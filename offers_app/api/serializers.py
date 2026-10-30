# Standard library
from decimal import Decimal

# Third-party
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

# Local imports
from core.serializers import APIModelSerializer
from core.utils import (
    decode_json_field,
    file_basename,
    null_text_to_none,
    schedule_replaced_file_deletion,
    validate_image_upload,
)
from offers_app.models import Offer, OfferDetail


OFFER_TYPES = {choice[0] for choice in OfferDetail.OfferType.choices}
REQUIRED_DETAIL_FIELDS = {'title', 'revisions', 'delivery_time_in_days', 'price'}
CONSTRAINT_ERROR = {'detail': 'The offer data violates a uniqueness or data constraint.'}


def validated_detail_items(details, partial):
    """Validate raw detail dicts and return the validated list."""
    serializer = OfferDetailWriteSerializer(data=details, many=True, partial=partial)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class OfferDetailWriteSerializer(serializers.Serializer):
    """Validate one offer detail submitted for creation or update."""

    offer_type = serializers.ChoiceField(choices=OfferDetail.OfferType.choices)
    title = serializers.CharField(max_length=150, required=False, allow_blank=False)
    revisions = serializers.IntegerField(min_value=0, max_value=100, required=False)
    delivery_time_in_days = serializers.IntegerField(min_value=1, max_value=365, required=False)
    price = serializers.DecimalField(
        max_digits=8, decimal_places=2, min_value=Decimal('0.01'),
        max_value=Decimal(100000), required=False,
    )
    features = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False, allow_empty=True
    )

    def validate(self, attrs):
        """Require offer_type even in partial mode, which skips required checks."""
        if 'offer_type' not in attrs:
            raise serializers.ValidationError({'offer_type': 'This field is required.'})
        return attrs


class OfferMultipartSerializer(serializers.Serializer):
    """Base for offer write serializers accepting JSON or multipart input."""

    details_error_message = 'Expected a JSON-encoded array.'

    def to_internal_value(self, data):
        """Normalize multipart input: text 'null' image clears it, details is JSON text."""
        data = null_text_to_none(data, 'image')
        data = decode_json_field(data, 'details', self.details_error_message)
        return super().to_internal_value(data)

    def validate_image(self, value):
        """Accept only JPEG/PNG images up to 5 MB, or None."""
        return validate_image_upload(value)


class OfferCreateSerializer(OfferMultipartSerializer):
    """Validate and create an offer with exactly three detail tiers."""

    details_error_message = 'Expected a JSON-encoded array of three detail objects.'
    title = serializers.CharField(max_length=150, allow_blank=False)
    image = serializers.FileField(required=False, allow_null=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    details = serializers.ListField(child=serializers.DictField(), min_length=3, max_length=3)

    def validate_details(self, details):
        """Require one complete detail for each of basic, standard, and premium."""
        items = validated_detail_items(details, partial=False)
        offer_types = [item['offer_type'] for item in items]
        if len(set(offer_types)) != 3 or set(offer_types) != OFFER_TYPES:
            raise serializers.ValidationError(
                'Exactly one detail for each of basic, standard, and premium is required.'
            )
        for item in items:
            self.complete_detail(item)
        return items

    def complete_detail(self, item):
        """Reject a detail with missing required fields and default its features."""
        missing = REQUIRED_DETAIL_FIELDS - item.keys()
        if missing:
            raise serializers.ValidationError(
                f"Detail '{item['offer_type']}' is missing required fields: "
                f"{', '.join(sorted(missing))}."
            )
        item.setdefault('features', [])

    def create(self, validated_data):
        """Create the offer and its details atomically and return the offer."""
        details = validated_data.pop('details')
        image = validated_data.pop('image', None)
        try:
            with transaction.atomic():
                offer = Offer.objects.create(
                    user=self.context['request'].user, image=image, **validated_data
                )
                OfferDetail.objects.bulk_create(
                    [OfferDetail(offer=offer, **detail) for detail in details]
                )
        except IntegrityError as exc:
            raise ValidationError(CONSTRAINT_ERROR) from exc
        return offer


class OfferDetailReadSerializer(APIModelSerializer):
    """Serialize a single offer detail."""

    class Meta:
        """Expose the offer detail fields."""

        model = OfferDetail
        fields = (
            'id', 'title', 'revisions', 'delivery_time_in_days',
            'price', 'features', 'offer_type',
        )


class OfferSummaryMixin(serializers.Serializer):
    """Shared image, minimum price, and minimum delivery time fields."""

    image = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    min_delivery_time = serializers.SerializerMethodField()

    def get_image(self, obj):
        """Return the offer image base name or None."""
        return file_basename(obj.image)

    def get_min_price(self, obj):
        """Return the lowest detail price or None."""
        return min((detail.price for detail in obj.details.all()), default=None)

    def get_min_delivery_time(self, obj):
        """Return the shortest detail delivery time or None."""
        return min((detail.delivery_time_in_days for detail in obj.details.all()), default=None)


class OfferListSerializer(OfferSummaryMixin, APIModelSerializer):
    """Serialize offers for the paginated list."""

    user = serializers.IntegerField(source='user_id', read_only=True)
    details = serializers.SerializerMethodField()
    user_details = serializers.SerializerMethodField()

    class Meta:
        """Expose the offer list field set."""

        model = Offer
        fields = (
            'id', 'user', 'title', 'image', 'description', 'created_at',
            'updated_at', 'details', 'min_price', 'min_delivery_time', 'user_details',
        )

    def get_details(self, obj):
        """Return id and relative URL for every detail."""
        return [
            {'id': detail.pk, 'url': f'/api/offerdetails/{detail.pk}/'}
            for detail in obj.details.all()
        ]

    def get_user_details(self, obj):
        """Return the creator's first name, last name, and username."""
        profile = getattr(obj.user, 'profile', None)
        return {
            'first_name': profile.first_name if profile else '',
            'last_name': profile.last_name if profile else '',
            'username': obj.user.username,
        }


class OfferDetailLinkSerializer(serializers.Serializer):
    """Serialize a detail id with its absolute URL."""

    id = serializers.IntegerField()
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        """Return the absolute detail URL when a request is available, else the path."""
        request = self.context.get('request')
        path = f'/api/offerdetails/{obj.pk}/'
        return request.build_absolute_uri(path) if request else path


class OfferDetailReadOnlySerializer(OfferSummaryMixin, APIModelSerializer):
    """Serialize a single offer with detail links."""

    details = OfferDetailLinkSerializer(many=True, read_only=True)

    class Meta:
        """Expose the single-offer field set."""

        model = Offer
        fields = (
            'id', 'user', 'title', 'image', 'description', 'created_at',
            'updated_at', 'details', 'min_price', 'min_delivery_time',
        )


class OfferCreateResponseSerializer(APIModelSerializer):
    """Serialize a created or updated offer with full detail data."""

    image = serializers.SerializerMethodField()
    details = OfferDetailReadSerializer(many=True, read_only=True)

    class Meta:
        """Expose the create/update response field set."""

        model = Offer
        fields = ('id', 'title', 'image', 'description', 'details')

    def get_image(self, obj):
        """Return the offer image base name or None."""
        return file_basename(obj.image)


class OfferUpdateResponseSerializer(OfferCreateResponseSerializer):
    """Serialize an updated offer using the create response format."""


class OfferUpdateSerializer(OfferMultipartSerializer):
    """Validate partial offer updates and apply them atomically."""

    title = serializers.CharField(max_length=150, required=False, allow_blank=False)
    image = serializers.FileField(required=False, allow_null=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    details = serializers.ListField(child=serializers.DictField(), required=False)

    def validate_details(self, details):
        """Validate partial detail updates with at most one entry per offer type."""
        items = validated_detail_items(details, partial=True)
        offer_types = [item['offer_type'] for item in items]
        if len(offer_types) != len(set(offer_types)):
            raise serializers.ValidationError('Each offer_type may be updated only once.')
        return items

    def update_offer(self):
        """Apply the validated changes atomically and return the updated offer."""
        offer = self.context['offer']
        data = dict(self.validated_data)
        details = data.pop('details', serializers.empty)
        image = data.pop('image', serializers.empty)
        old_image = offer.image
        try:
            with transaction.atomic():
                self.apply_offer_fields(offer, data, image)
                if details is not serializers.empty:
                    self.apply_details(offer, details)
                schedule_replaced_file_deletion(old_image, offer.image)
        except IntegrityError as exc:
            raise ValidationError(CONSTRAINT_ERROR) from exc
        return offer

    def apply_offer_fields(self, offer, data, image):
        """Set and save the top-level offer fields and image when provided."""
        for field, value in data.items():
            setattr(offer, field, value)
        if image is not serializers.empty:
            offer.image = image
        if data or image is not serializers.empty:
            offer.save()

    def apply_details(self, offer, details):
        """Update the existing details identified by offer_type and reset the prefetch cache."""
        for item in details:
            self.apply_detail(offer, dict(item))
        getattr(offer, '_prefetched_objects_cache', {}).pop('details', None)

    def apply_detail(self, offer, detail_data):
        """Update the offer's detail of the given offer_type or raise 404."""
        offer_type = detail_data.pop('offer_type')
        try:
            detail = offer.details.get(offer_type=offer_type)
        except OfferDetail.DoesNotExist as exc:
            raise NotFound(f"Offer detail '{offer_type}' was not found.") from exc
        for field, value in detail_data.items():
            setattr(detail, field, list(value) if isinstance(value, list) else value)
        if detail_data:
            detail.save()
