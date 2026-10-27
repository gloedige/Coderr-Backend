from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts_app.models import Profile


User = get_user_model()


class AuthenticationEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registration_creates_user_profile_and_token_atomically(self):
        response = self.client.post(
            '/api/registration/',
            {
                'username': '  neuerNutzer  ',
                'email': '  User@Example.com  ',
                'password': 'pass',
                'repeated_password': 'pass',
                'type': 'customer',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='neuerNutzer')
        self.assertEqual(user.email, 'user@example.com')
        self.assertEqual(user.type, User.UserType.CUSTOMER)
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(Token.objects.get(user=user).key, response.data['token'])
        self.assertEqual(
            response.data,
            {
                'token': Token.objects.get(user=user).key,
                'username': 'neuerNutzer',
                'email': 'user@example.com',
                'user_id': user.pk,
            },
        )

    def test_registration_allows_username_with_different_case(self):
        User.objects.create_user(
            username='neuerNutzer',
            email='existing@example.com',
            password='pass',
            type=User.UserType.CUSTOMER,
        )

        response = self.client.post(
            '/api/registration/',
            {
                'username': 'NEUERnutzer',
                'email': 'new@example.com',
                'password': 'pass',
                'repeated_password': 'pass',
                'type': 'business',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['username'], 'NEUERnutzer')
        self.assertTrue(User.objects.filter(username='NEUERnutzer').exists())

    def test_registration_rejects_invalid_role(self):
        response = self.client.post(
            '/api/registration/',
            {
                'username': 'valid-user',
                'email': 'valid@example.com',
                'password': 'pass',
                'repeated_password': 'pass',
                'type': 'admin',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('type', response.data)
        self.assertFalse(User.objects.filter(username='valid-user').exists())

    def test_registration_rejects_short_or_mismatched_password(self):
        for password, repeated_password, expected_field in (
            ('abc', 'abc', 'password'),
            ('pass', 'different', 'repeated_password'),
        ):
            with self.subTest(expected_field=expected_field):
                response = self.client.post(
                    '/api/registration/',
                    {
                        'username': f'valid-user-{expected_field}',
                        'email': f'{expected_field}@example.com',
                        'password': password,
                        'repeated_password': repeated_password,
                        'type': 'customer',
                    },
                    format='json',
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn(expected_field, response.data)
                self.assertFalse(
                    User.objects.filter(username=f'valid-user-{expected_field}').exists()
                )

    def test_registration_rolls_back_user_profile_and_token_on_server_error(self):
        with patch.object(Profile.objects, 'create', side_effect=RuntimeError('sensitive internals')):
            response = self.client.post(
                '/api/registration/',
                {
                    'username': 'atomic-user',
                    'email': 'atomic@example.com',
                    'password': 'pass',
                    'repeated_password': 'pass',
                    'type': 'customer',
                },
                format='json',
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {'detail': 'Internal server error.'})
        self.assertFalse(User.objects.filter(username='atomic-user').exists())
        self.assertFalse(Token.objects.filter(user__username='atomic-user').exists())

    def test_login_requires_exact_username_case(self):
        user = User.objects.create_user(
            username='neuerNutzer',
            email='login@example.com',
            password='pass',
            type=User.UserType.BUSINESS,
        )

        response = self.client.post(
            '/api/login/',
            {'username': 'neuerNutzer', 'password': 'pass'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'neuerNutzer')
        self.assertEqual(response.data['email'], 'login@example.com')
        self.assertEqual(response.data['user_id'], user.pk)
        self.assertEqual(Token.objects.get(user=user).key, response.data['token'])

        wrong_case_response = self.client.post(
            '/api/login/',
            {'username': 'NEUERnutzer', 'password': 'pass'},
            format='json',
        )
        self.assertEqual(wrong_case_response.status_code, 400)
        self.assertEqual(
            wrong_case_response.data,
            {'detail': ['Invalid username or password.']},
        )

    def test_login_returns_same_generic_validation_error_for_invalid_credentials(self):
        User.objects.create_user(
            username='known-user',
            email='known@example.com',
            password='pass',
            type=User.UserType.CUSTOMER,
        )

        for credentials in (
            {'username': 'missing-user', 'password': 'pass'},
            {'username': 'known-user', 'password': 'wrong'},
        ):
            with self.subTest(credentials=credentials):
                response = self.client.post(
                    '/api/login/', credentials, format='json'
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data,
                    {'detail': ['Invalid username or password.']},
                )

    def test_login_rejects_missing_fields(self):
        response = self.client.post('/api/login/', {}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)
        self.assertIn('password', response.data)
