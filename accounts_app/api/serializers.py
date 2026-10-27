from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from accounts_app.models import Profile


User = get_user_model()


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    repeated_password = serializers.CharField(write_only=True, trim_whitespace=False)
    type = serializers.ChoiceField(choices=User.UserType.choices)

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already in use.')
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already in use.')
        return value

    def validate(self, attrs):
        if len(attrs['password']) < 4:
            raise serializers.ValidationError(
                {'password': 'Password must be at least 4 characters long.'}
            )
        if attrs['password'] != attrs['repeated_password']:
            raise serializers.ValidationError(
                {'repeated_password': 'Passwords must match.'}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('repeated_password')
        password = validated_data.pop('password')
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    password=password,
                    **validated_data,
                )
                Profile.objects.create(user=user)
                token = Token.objects.create(user=user)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {'detail': 'A user with this username or email already exists.'}
            ) from exc
        return user, token


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context.get('request')
        user = authenticate(
            request=request,
            username=attrs['username'].strip(),
            password=attrs['password'],
        )
        if user is None:
            raise serializers.ValidationError(
                {'detail': 'Invalid username or password.'}
            )
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        user = validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return user, token
