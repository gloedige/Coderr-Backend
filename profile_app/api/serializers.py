from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from profile_app.models import Profile
from core.serializers import APIModelSerializer
from core.utils import (
    file_basename,
    null_text_to_none,
    schedule_replaced_file_deletion,
    validate_image_upload,
)


User = get_user_model()


class ProfileBaseSerializer(APIModelSerializer):
    """Shared read-only user fields and file basename for profile responses."""

    user = serializers.IntegerField(source='user_id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    type = serializers.CharField(source='user.type', read_only=True)
    file = serializers.SerializerMethodField()

    def get_file(self, obj):
        """Return the profile image base name or None."""
        return file_basename(obj.file)


class ProfileDetailSerializer(ProfileBaseSerializer):
    """Serialize the complete profile including email and creation time."""

    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        """Expose the full profile field set."""

        model = Profile
        fields = (
            'user', 'username', 'first_name', 'last_name', 'file', 'location',
            'tel', 'description', 'working_hours', 'type', 'email', 'created_at',
        )


class ProfileUpdateSerializer(serializers.Serializer):
    """Validate partial profile updates and apply them atomically."""

    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)
    tel = serializers.CharField(max_length=50, required=False, allow_blank=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    working_hours = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(max_length=254, required=False, allow_blank=True)
    file = serializers.FileField(required=False, allow_null=True)

    def to_internal_value(self, data):
        """Treat the multipart text 'null' for `file` as a request to clear the image."""
        return super().to_internal_value(null_text_to_none(data, 'file'))

    def validate_email(self, value):
        """Normalize the email and reject addresses used by another account."""
        normalized_email = value.strip().lower()
        user = self.context['user']
        if User.objects.filter(email__iexact=normalized_email).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('This email is already in use.')
        return normalized_email

    def validate_file(self, value):
        """Accept only JPEG/PNG images up to 5 MB, or None to clear."""
        return validate_image_upload(value)

    def update_profile(self):
        """Apply validated changes atomically and return the updated profile."""
        profile = self.context['profile']
        user = profile.user
        data = dict(self.validated_data)
        print(f"Validated data: {data}")
        email = data.pop('email', None)
        print(f"Email: {email}")
        file_value = data.pop('file', serializers.empty)
        previous_file = profile.file
        try:
            with transaction.atomic():
                self.apply_changes(profile, user, data, email, file_value)
                schedule_replaced_file_deletion(previous_file, profile.file)
        except IntegrityError as exc:
            raise serializers.ValidationError({'email': 'This email is already in use.'}) from exc
        return profile

    def apply_changes(self, profile, user, data, email, file_value):
        """Persist the email, text fields, and image change for one profile update."""
        if email is not None:
            user.email = email
            user.save(update_fields=['email'])
        for field, value in data.items():
            setattr(profile, field, value)
        self.apply_file(profile, file_value)
        profile.save()

    def apply_file(self, profile, file_value):
        """Set or clear the profile image unless the field was omitted."""
        if file_value is serializers.empty:
            return
        profile.file = file_value
        if file_value is not None:
            profile.uploaded_at = timezone.now()


class BusinessProfileListSerializer(ProfileBaseSerializer):
    """Serialize business profiles for the business list endpoint."""

    class Meta:
        """Expose the business list field set."""

        model = Profile
        fields = (
            'user', 'username', 'first_name', 'last_name', 'file', 'location',
            'tel', 'description', 'working_hours', 'type',
        )


class CustomerProfileListSerializer(ProfileBaseSerializer):
    """Serialize customer profiles including the last image upload time."""

    class Meta:
        """Expose the customer list field set."""

        model = Profile
        fields = (
            'user', 'username', 'first_name', 'last_name', 'file', 'uploaded_at', 'type',
        )
