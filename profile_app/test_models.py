# Third-party
from django.test import TestCase

# Local imports
from auth_app.models import User
from profile_app.models import Profile


class ProfileModelTests(TestCase):
    """Checks the profile model foundations."""

    def test_profile_is_one_to_one_with_user(self):
        """A profile belongs one-to-one to its user with blank defaults."""
        user = User.objects.create_user(
            username='profile-owner',
            email='profile-owner@example.com',
            password='pass',
            type=User.UserType.CUSTOMER,
        )
        profile = Profile.objects.create(user=user)

        self.assertEqual(user.profile, profile)
        self.assertFalse(profile.file)
        self.assertEqual(profile.first_name, '')

    def test_profile_image_uses_uploads_directory(self):
        """Profile images are stored in the uploads directory."""
        field = Profile._meta.get_field('file')

        self.assertEqual(field.upload_to, 'uploads/')

    def test_seed_migration_creates_guest_users_with_profile_and_token(self):
        """The seed migration provides guest accounts with profile and token."""
        for username in ('guest_customer', 'guest_business'):
            user = User.objects.get(username=username)
            self.assertTrue(user.check_password('guest1234'))
            self.assertTrue(Profile.objects.filter(user=user).exists())
            self.assertTrue(user.auth_token.key)
