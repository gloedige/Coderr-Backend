from datetime import datetime, timedelta, timezone

from django.db import models
from django.test import SimpleTestCase
from rest_framework import serializers

from accounts_app.api.profile_serializers import (
    CustomerProfileListSerializer,
    ProfileDetailSerializer,
)
from core.api.datetime_fields import UTCDateTimeField
from marketplace_app.api.offer_serializers import (
    OfferDetailReadOnlySerializer,
    OfferListSerializer,
)
from marketplace_app.api.order_serializers import OrderReadSerializer
from marketplace_app.api.review_serializers import ReviewReadSerializer


class UTCDateTimeFieldTests(SimpleTestCase):
    """Verify the timestamp format shared by API model serializers."""

    def test_representation_uses_utc_and_two_fractional_digits(self):
        """Render timezone-aware values in UTC and truncate after hundredths."""
        value = datetime(
            2026, 10, 28, 12, 51, 58, 269876, tzinfo=timezone(timedelta(hours=2))
        )

        self.assertEqual(
            UTCDateTimeField().to_representation(value),
            '2026-10-28T10:51:58.26Z',
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