from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts_app.models import Profile


User = get_user_model()


class AuthenticationEndpointTests(TestCase):
    """Checks the registration and login endpoints."""

    def setUp(self):
        """Create an API client."""
        self.client = APIClient()

    def register(self, **overrides):
        """POST a valid registration payload updated by overrides; return the response."""
        payload = {
            'username': 'valid-user',
            'email': 'valid@example.com',
            'password': 'pass',
            'repeated_password': 'pass',
            'type': 'customer',
        }
        payload.update(overrides)
        return self.client.post('/api/registration/', payload, format='json')

    def create_user(self, username, email, user_type):
        """Create and return a user with password 'pass'."""
        return User.objects.create_user(
            username=username,
            email=email,
            password='pass',
            type=user_type,
        )

    def login(self, username, password):
        """POST login credentials and return the response."""
        return self.client.post(
            '/api/login/',
            {'username': username, 'password': password},
            format='json',
        )

    def assert_generic_login_error(self, response):
        """Assert the response is the generic invalid-credentials 400 error."""
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {'detail': ['Invalid username or password.']},
        )

    def assert_registered_user(self, response):
        """Assert user, profile, token and response body of a successful registration."""
        user = User.objects.get(username='neuerNutzer')
        token = Token.objects.get(user=user).key
        self.assertEqual(user.email, 'user@example.com')
        self.assertEqual(user.type, User.UserType.CUSTOMER)
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(token, response.data['token'])
        self.assertEqual(response.data, {
            'token': token,
            'username': 'neuerNutzer',
            'email': 'user@example.com',
            'user_id': user.pk,
        })

    def assert_password_rejected(self, password, repeated_password, expected_field):
        """Assert registration with these passwords fails with an error on expected_field."""
        username = f'valid-user-{expected_field}'
        response = self.register(
            username=username,
            email=f'{expected_field}@example.com',
            password=password,
            repeated_password=repeated_password,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(expected_field, response.data)
        self.assertFalse(User.objects.filter(username=username).exists())

    def test_registration_creates_user_profile_and_token_atomically(self):
        """Registration creates user, profile and token and returns them."""
        response = self.register(
            username='  neuerNutzer  ', email='  User@Example.com  '
        )

        self.assertEqual(response.status_code, 201)
        self.assert_registered_user(response)

    def test_registration_allows_username_with_different_case(self):
        """A username differing only in case can still register."""
        self.create_user('neuerNutzer', 'existing@example.com', User.UserType.CUSTOMER)

        response = self.register(
            username='NEUERnutzer', email='new@example.com', type='business'
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['username'], 'NEUERnutzer')
        self.assertTrue(User.objects.filter(username='NEUERnutzer').exists())

    def test_registration_returns_400_for_concurrent_duplicate_insert(self):
        """A race on the unique constraint yields a 400 response."""
        with patch(
            'accounts_app.api.serializers.User.objects.create_user',
            side_effect=IntegrityError('unique constraint race'),
        ):
            response = self.register(username='racing-user', email='racing@example.com')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {'detail': 'A user with this username or email already exists.'},
        )
        self.assertFalse(User.objects.filter(username='racing-user').exists())

    def test_registration_rejects_invalid_role(self):
        """An unknown role is rejected with a type error."""
        response = self.register(type='admin')

        self.assertEqual(response.status_code, 400)
        self.assertIn('type', response.data)
        self.assertFalse(User.objects.filter(username='valid-user').exists())

    def test_registration_rejects_short_or_mismatched_password(self):
        """Short or mismatched passwords are rejected on the matching field."""
        for password, repeated_password, expected_field in (
            ('abc', 'abc', 'password'),
            ('pass', 'different', 'repeated_password'),
        ):
            with self.subTest(expected_field=expected_field):
                self.assert_password_rejected(password, repeated_password, expected_field)

    def test_registration_rolls_back_user_profile_and_token_on_server_error(self):
        """A server error rolls back user, profile and token creation."""
        with patch.object(Profile.objects, 'create', side_effect=RuntimeError('sensitive internals')):
            response = self.register(username='atomic-user', email='atomic@example.com')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {'detail': 'Internal server error.'})
        self.assertFalse(User.objects.filter(username='atomic-user').exists())
        self.assertFalse(Token.objects.filter(user__username='atomic-user').exists())

    def test_login_requires_exact_username_case(self):
        """Login succeeds with exact username case and fails otherwise."""
        user = self.create_user('neuerNutzer', 'login@example.com', User.UserType.BUSINESS)

        response = self.login('neuerNutzer', 'pass')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'neuerNutzer')
        self.assertEqual(response.data['email'], 'login@example.com')
        self.assertEqual(response.data['user_id'], user.pk)
        self.assertEqual(Token.objects.get(user=user).key, response.data['token'])
        self.assert_generic_login_error(self.login('NEUERnutzer', 'pass'))

    def test_login_returns_same_generic_validation_error_for_invalid_credentials(self):
        """Unknown users and wrong passwords yield the same generic error."""
        self.create_user('known-user', 'known@example.com', User.UserType.CUSTOMER)

        for username, password in (
            ('missing-user', 'pass'),
            ('known-user', 'wrong'),
        ):
            with self.subTest(username=username):
                self.assert_generic_login_error(self.login(username, password))

    def test_login_rejects_missing_fields(self):
        """Login without fields reports both missing fields."""
        response = self.client.post('/api/login/', {}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)
        self.assertIn('password', response.data)
