from datetime import timezone

from rest_framework import serializers


class UTCDateTimeField(serializers.DateTimeField):
    """Render API timestamps in UTC without fractional seconds."""

    def to_representation(self, value):
        """Return a UTC ISO-8601 timestamp with whole seconds and a Z suffix."""
        value = self.enforce_timezone(value).astimezone(timezone.utc)
        return value.strftime('%Y-%m-%dT%H:%M:%SZ')