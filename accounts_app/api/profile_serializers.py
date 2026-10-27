from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from accounts_app.models import Profile


User = get_user_model()
MAX_PROFILE_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_PROFILE_IMAGE_FORMATS = {'JPEG', 'PNG'}


class ProfileDetailSerializer(serializers.ModelSerializer):
    user = serializers.IntegerField(source='user_id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    type = serializers.CharField(source='user.type', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    file = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
            'email',
            'created_at',
        )

    def get_file(self, obj):
        return obj.file.name.rsplit('/', 1)[-1] if obj.file else None


class ProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)
    tel = serializers.CharField(max_length=50, required=False, allow_blank=True)
    email = serializers.EmailField(max_length=254, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    working_hours = serializers.CharField(max_length=255, required=False, allow_blank=True)
    file = serializers.FileField(required=False, allow_null=True)

    def to_internal_value(self, data):
        if data.get('file') == 'null':
            data = data.copy()
            data['file'] = None
        return super().to_internal_value(data)

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        user = self.context['user']
        if User.objects.filter(email__iexact=normalized_email).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('This email is already in use.')
        return normalized_email

    def validate_file(self, value):
        if value is None:
            return value
        if value.size > MAX_PROFILE_IMAGE_SIZE:
            raise serializers.ValidationError('Image must not exceed 5 MB.')
        try:
            image = Image.open(value)
            image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise serializers.ValidationError('Only valid JPEG and PNG images are accepted.') from exc
        if image.format not in ALLOWED_PROFILE_IMAGE_FORMATS:
            raise serializers.ValidationError('Only JPEG and PNG images are accepted.')
        value.seek(0)
        return value

    def validate(self, attrs):
        profile = self.context['profile']
        if profile.user.type != User.UserType.BUSINESS:
            forbidden = {'description', 'working_hours'} & attrs.keys()
            if forbidden:
                raise serializers.ValidationError(
                    {field: 'This field is only editable for business profiles.' for field in forbidden}
                )
        return attrs

    def update_profile(self):
        profile = self.context['profile']
        user = self.context['user']
        data = dict(self.validated_data)
        email = data.pop('email', None)
        file_value = data.pop('file', serializers.empty)
        previous_file = profile.file
        previous_file_name = previous_file.name if previous_file else None

        try:
            with transaction.atomic():
                if email is not None:
                    user.email = email
                    user.save(update_fields=['email'])
                for field, value in data.items():
                    setattr(profile, field, value)
                if file_value is not serializers.empty:
                    profile.file = file_value
                    if file_value is not None:
                        profile.uploaded_at = timezone.now()
                profile.save()
                if (
                    file_value is not serializers.empty
                    and previous_file_name
                    and previous_file_name != (profile.file.name if profile.file else None)
                ):
                    transaction.on_commit(
                        lambda: previous_file.storage.delete(previous_file_name)
                    )
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {'email': 'This email is already in use.'}
            ) from exc
        return profile


class BusinessProfileListSerializer(serializers.ModelSerializer):
    user = serializers.IntegerField(source='user_id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    type = serializers.CharField(source='user.type', read_only=True)
    file = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
        )

    def get_file(self, obj):
        return obj.file.name.rsplit('/', 1)[-1] if obj.file else None


class CustomerProfileListSerializer(serializers.ModelSerializer):
    user = serializers.IntegerField(source='user_id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    type = serializers.CharField(source='user.type', read_only=True)
    file = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'uploaded_at',
            'type',
        )

    def get_file(self, obj):
        return obj.file.name.rsplit('/', 1)[-1] if obj.file else None
