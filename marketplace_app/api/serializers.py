import json
from decimal import Decimal

from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from marketplace_app.models import Offer, OfferDetail


MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG'}
OFFER_TYPES = {choice[0] for choice in OfferDetail.OfferType.choices}


def image_basename(image):
    return image.name.rsplit('/', 1)[-1] if image else None


class OfferDetailWriteSerializer(serializers.Serializer):
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


class OfferCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, allow_blank=False)
    image = serializers.FileField(required=False, allow_null=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    details = serializers.ListField(child=serializers.DictField(), min_length=3, max_length=3)

    def to_internal_value(self, data):
        if hasattr(data, 'getlist'):
            data = data.dict()
        if hasattr(data, 'get') and data.get('image') == 'null':
            data = dict(data)
            data['image'] = None
        if hasattr(data, 'get') and isinstance(data.get('details'), str):
            copied_data = dict(data)
            try:
                copied_data['details'] = json.loads(copied_data['details'])
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError(
                    {'details': 'Expected a JSON-encoded array of three detail objects.'}
                ) from exc
            data = copied_data
        return super().to_internal_value(data)

    def validate_image(self, value):
        return validate_offer_image(value)

    def validate_details(self, details):
        detail_serializer = OfferDetailWriteSerializer(data=details, many=True)
        detail_serializer.is_valid(raise_exception=True)
        offer_types = [item['offer_type'] for item in detail_serializer.validated_data]
        if len(set(offer_types)) != 3 or set(offer_types) != OFFER_TYPES:
            raise serializers.ValidationError(
                'Exactly one detail for each of basic, standard, and premium is required.'
            )
        for item in detail_serializer.validated_data:
            missing = {'title', 'revisions', 'delivery_time_in_days', 'price'} - item.keys()
            if missing:
                raise serializers.ValidationError(
                    f"Detail '{item['offer_type']}' is missing required fields: {', '.join(sorted(missing))}."
                )
            item.setdefault('features', [])
        return detail_serializer.validated_data

    def create(self, validated_data):
        from django.db import IntegrityError, transaction
        from rest_framework.exceptions import ValidationError

        details = validated_data.pop('details')
        image = validated_data.pop('image', None)
        try:
            with transaction.atomic():
                offer = Offer.objects.create(
                    user=self.context['request'].user,
                    image=image,
                    **validated_data,
                )
                OfferDetail.objects.bulk_create(
                    [OfferDetail(offer=offer, **detail) for detail in details]
                )
        except IntegrityError as exc:
            raise ValidationError({'detail': 'The offer data violates a uniqueness or data constraint.'}) from exc
        return offer


class OfferDetailReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferDetail
        fields = (
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        )


class OfferListSerializer(serializers.ModelSerializer):
    user = serializers.IntegerField(source='user_id', read_only=True)
    image = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    min_delivery_time = serializers.SerializerMethodField()
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = (
            'id', 'user', 'title', 'image', 'description', 'created_at',
            'updated_at', 'details', 'min_price', 'min_delivery_time', 'user_details',
        )

    def get_image(self, obj):
        return image_basename(obj.image)

    def get_details(self, obj):
        return [
            {'id': detail.pk, 'url': f'/api/offerdetails/{detail.pk}/'}
            for detail in obj.details.all()
        ]

    def get_min_price(self, obj):
        return min((detail.price for detail in obj.details.all()), default=None)

    def get_min_delivery_time(self, obj):
        return min(
            (detail.delivery_time_in_days for detail in obj.details.all()),
            default=None,
        )

    def get_user_details(self, obj):
        profile = getattr(obj.user, 'profile', None)
        return {
            'first_name': profile.first_name if profile else '',
            'last_name': profile.last_name if profile else '',
            'username': obj.user.username,
        }


class OfferDetailLinkSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        request = self.context.get('request')
        path = f'/api/offerdetails/{obj.pk}/'
        return request.build_absolute_uri(path) if request else path


class OfferDetailReadOnlySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    details = OfferDetailLinkSerializer(many=True, read_only=True)
    min_price = serializers.SerializerMethodField()
    min_delivery_time = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = (
            'id', 'user', 'title', 'image', 'description', 'created_at',
            'updated_at', 'details', 'min_price', 'min_delivery_time',
        )

    def get_image(self, obj):
        return image_basename(obj.image)

    def get_min_price(self, obj):
        return min((detail.price for detail in obj.details.all()), default=None)

    def get_min_delivery_time(self, obj):
        return min(
            (detail.delivery_time_in_days for detail in obj.details.all()),
            default=None,
        )


class OfferCreateResponseSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    details = OfferDetailReadSerializer(many=True, read_only=True)

    class Meta:
        model = Offer
        fields = ('id', 'title', 'image', 'description', 'details')

    def get_image(self, obj):
        return image_basename(obj.image)


class OfferUpdateResponseSerializer(OfferCreateResponseSerializer):
    pass


class OfferUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, required=False, allow_blank=False)
    image = serializers.FileField(required=False, allow_null=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    details = serializers.ListField(child=serializers.DictField(), required=False)

    def to_internal_value(self, data):
        if hasattr(data, 'getlist'):
            data = data.dict()
        if hasattr(data, 'get') and data.get('image') == 'null':
            data = dict(data)
            data['image'] = None
        if hasattr(data, 'get') and isinstance(data.get('details'), str):
            copied_data = dict(data)
            try:
                copied_data['details'] = json.loads(copied_data['details'])
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError({'details': 'Expected a JSON-encoded array.'}) from exc
            data = copied_data
        return super().to_internal_value(data)

    def validate_image(self, value):
        return validate_offer_image(value)

    def validate_details(self, details):
        detail_serializer = OfferDetailWriteSerializer(data=details, many=True, partial=True)
        detail_serializer.is_valid(raise_exception=True)
        offer_types = [item['offer_type'] for item in detail_serializer.validated_data]
        if len(offer_types) != len(set(offer_types)):
            raise serializers.ValidationError('Each offer_type may be updated only once.')
        return detail_serializer.validated_data

    def update_offer(self):
        from django.db import IntegrityError, transaction
        from rest_framework.exceptions import NotFound, ValidationError

        offer = self.context['offer']
        data = dict(self.validated_data)
        details = data.pop('details', serializers.empty)
        image = data.pop('image', serializers.empty)
        old_image = offer.image
        old_image_name = old_image.name if old_image else None
        try:
            with transaction.atomic():
                for field, value in data.items():
                    setattr(offer, field, value)
                if image is not serializers.empty:
                    offer.image = image
                if data or image is not serializers.empty:
                    offer.save()
                if details is not serializers.empty:
                    for validated_detail_data in details:
                        detail_data = dict(validated_detail_data)
                        offer_type = detail_data.pop('offer_type')
                        try:
                            detail = offer.details.get(offer_type=offer_type)
                        except OfferDetail.DoesNotExist as exc:
                            raise NotFound(f"Offer detail '{offer_type}' was not found.") from exc
                        for field, value in detail_data.items():
                            setattr(detail, field, value.copy() if isinstance(value, list) else value)
                        if detail_data:
                            detail.save()
                    offer._prefetched_objects_cache.pop('details', None)
                if (
                    image is not serializers.empty
                    and old_image_name
                    and old_image_name != (offer.image.name if offer.image else None)
                ):
                    transaction.on_commit(lambda: old_image.storage.delete(old_image_name))
        except IntegrityError as exc:
            raise ValidationError({'detail': 'The offer data violates a uniqueness or data constraint.'}) from exc
        return offer


def validate_offer_image(value):
    if value is None:
        return value
    if value.size > MAX_IMAGE_SIZE:
        raise serializers.ValidationError('Image must not exceed 5 MB.')
    try:
        image = Image.open(value)
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise serializers.ValidationError('Only valid JPEG and PNG images are accepted.') from exc
    if image.format not in ALLOWED_IMAGE_FORMATS:
        raise serializers.ValidationError('Only JPEG and PNG images are accepted.')
    value.seek(0)
    return value
