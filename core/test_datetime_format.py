# Standard library
from datetime import datetime, timedelta, timezone

# Third-party
from django.db import models
from django.test import SimpleTestCase
from rest_framework import serializers

# Local imports
from core.datetime_fields import UTCDateTimeField
from offers_app.api.serializers import (
    OfferDetailReadOnlySerializer,
    OfferListSerializer,
)
from orders_app.api.serializers import OrderReadSerializer
from profile_app.api.serializers import (
    CustomerProfileListSerializer,
    ProfileDetailSerializer,
)
from reviews_app.api.serializers import ReviewReadSerializer


class UTCDateTimeFieldTests(SimpleTestCase):
    """Verify the timestamp format shared by API model serializers."""

    def test_representation_uses_utc_and_omits_fractional_seconds(self):
        """Render timezone-aware values in UTC without fractional seconds."""
        value = datetime(
            2026, 10, 28, 12, 51, 58, 269876, tzinfo=timezone(timedelta(hours=2))
        )

        self.assertEqual(
            UTCDateTimeField().to_representation(value),
            '2026-10-28T10:51:58Z',
        )

    def test_all_datetime_response_fields_use_the_shared_field(self):
        """Ensure every API response model serializer maps date fields consistently."""
        serializer_classes = (
            ProfileDetailSerializer, CustomerProfileListSerializer, OfferListSerializer,
            OfferDetailReadOnlySerializer, OrderReadSerializer, ReviewReadSerializer,
        )
        for serializer_class in serializer_classes:
            self.assert_datetime_fields_use_shared_field(serializer_class)

    def assert_datetime_fields_use_shared_field(self, serializer_class):
        """Assert generated DateTimeFields use UTCDateTimeField for one serializer."""
        fields = serializer_class().fields.values()
        for field in fields:
            if isinstance(field, serializers.DateTimeField):
                self.assertIsInstance(field, UTCDateTimeField)