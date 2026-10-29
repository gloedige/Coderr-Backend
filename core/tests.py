from django.conf import settings
from django.test import SimpleTestCase
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings


class ProjectFoundationTests(SimpleTestCase):
    """Checks project-wide settings contracts."""

    def test_rest_framework_uses_token_authentication_by_default(self):
        """Token authentication is the only default authenticator."""
        authenticators = api_settings.DEFAULT_AUTHENTICATION_CLASSES

        self.assertEqual(
            [authenticator.__name__ for authenticator in authenticators],
            ['TokenAuthentication'],
        )

    def test_rest_framework_requires_authentication_by_default(self):
        """IsAuthenticated is the default permission class."""
        self.assertEqual(api_settings.DEFAULT_PERMISSION_CLASSES, [IsAuthenticated])

    def test_media_configuration_matches_project_contract(self):
        """Media URL and root match the project contract."""
        self.assertEqual(settings.MEDIA_URL, '/media/')
        self.assertEqual(settings.MEDIA_ROOT, str(settings.BASE_DIR / 'media'))

    def test_domain_apps_are_installed(self):
        """All domain apps are in INSTALLED_APPS."""
        for app in ('auth_app', 'profile_app', 'offers_app', 'orders_app', 'reviews_app', 'base_app'):
            self.assertIn(app, settings.INSTALLED_APPS)



