# Third-party
from django.db import models
from rest_framework import serializers

# Local imports
from core.datetime_fields import UTCDateTimeField


class APIModelSerializer(serializers.ModelSerializer):
    """Use shared API field formatting for automatically generated model fields."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.DateTimeField: UTCDateTimeField,
    }