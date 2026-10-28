from datetime import timezone

from rest_framework import serializers


class UTCDateTimeField(serializers.DateTimeField):
    """Render API timestamps in UTC with exactly two fractional-second digits."""

    def to_representation(self, value):
        """Return a UTC ISO-8601 timestamp truncated to hundredths of a second."""
        value = self.enforce_timezone(value).astimezone(timezone.utc)
        timestamp = value.strftime('%Y-%m-%dT%H:%M:%S.%f')
        return f'{timestamp[:-4]}Z'