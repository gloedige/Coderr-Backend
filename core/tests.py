from django.conf import settings
from django.test import SimpleTestCase
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings


class ProjectFoundationTests(SimpleTestCase):
    def test_rest_framework_uses_token_authentication_by_default(self):
        authenticators = api_settings.DEFAULT_AUTHENTICATION_CLASSES

        self.assertEqual(
            [authenticator.__name__ for authenticator in authenticators],
            ['TokenAuthentication'],
        )

    def test_rest_framework_requires_authentication_by_default(self):
        self.assertEqual(api_settings.DEFAULT_PERMISSION_CLASSES, [IsAuthenticated])

    def test_media_configuration_matches_project_contract(self):
        self.assertEqual(settings.MEDIA_URL, '/media/')
        self.assertEqual(settings.MEDIA_ROOT, str(settings.BASE_DIR / 'media'))

    def test_account_and_marketplace_apps_are_installed(self):
        self.assertIn('accounts_app', settings.INSTALLED_APPS)
        self.assertIn('marketplace_app', settings.INSTALLED_APPS)

