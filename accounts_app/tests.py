from django.conf import settings
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from accounts_app.models import Profile, User


@override_settings(MEDIA_ROOT=settings.BASE_DIR / 'test-media')
class AccountFoundationTests(TestCase):
    """Checks the user and profile model foundations."""

    def create_user(self, username, email, user_type):
        """Create and return a user with password 'pass' and the given role."""
        return User.objects.create_user(
            username=username,
            email=email,
            password='pass',
            type=user_type,
        )

    def assert_create_rejected(self, username, email):
        """Assert that creating a business user with these values violates uniqueness."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_user(username, email, User.UserType.BUSINESS)

    def test_user_supports_customer_and_business_roles(self):
        """Users can be customers or businesses."""
        customer = self.create_user(
            'customer-one', 'customer@example.com', User.UserType.CUSTOMER
        )
        business = self.create_user(
            'business-one', 'business@example.com', User.UserType.BUSINESS
        )

        self.assertEqual(customer.type, 'customer')
        self.assertEqual(business.type, 'business')

    def test_profile_is_one_to_one_with_user(self):
        """A profile belongs one-to-one to its user with blank defaults."""
        user = self.create_user(
            'profile-owner', 'profile-owner@example.com', User.UserType.CUSTOMER
        )
        profile = Profile.objects.create(user=user)

        self.assertEqual(user.profile, profile)
        self.assertFalse(profile.file)
        self.assertEqual(profile.first_name, '')

    def test_role_is_required_and_limited_to_documented_values(self):
        """The role field is required and limited to the documented choices."""
        field = User._meta.get_field('type')

        self.assertEqual(field.max_length, 10)
        self.assertEqual(
            set(field.choices),
            {('customer', 'Customer'), ('business', 'Business')},
        )
        self.assertIn('type', User.REQUIRED_FIELDS)

    def test_database_restricts_user_role_values(self):
        """The database rejects unknown role values."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(
                username='invalid-role',
                email='invalid-role@example.com',
                type='admin',
            )

    def test_username_case_is_preserved_and_email_is_normalized(self):
        """Usernames are stripped but keep case; emails are lowercased."""
        user = self.create_user(
            '  neuerNutzer  ', 'Mixed.Email@Example.com', User.UserType.CUSTOMER
        )

        self.assertEqual(user.username, 'neuerNutzer')
        self.assertEqual(user.email, 'mixed.email@example.com')

    def test_usernames_are_case_sensitive_but_exact_duplicates_are_rejected(self):
        """Case variants of usernames are allowed; exact duplicates are not."""
        original = self.create_user(
            'UniqueName', 'unique@example.com', User.UserType.CUSTOMER
        )
        case_variant = self.create_user(
            'uniquename', 'case-variant@example.com', User.UserType.BUSINESS
        )

        self.assertEqual(original.username, 'UniqueName')
        self.assertEqual(case_variant.username, 'uniquename')
        self.assert_create_rejected('UniqueName', 'different@example.com')
        self.assert_create_rejected('differentname', 'UNIQUE@example.com')

    def test_profile_image_uses_uploads_directory(self):
        """Profile images are stored in the uploads directory."""
        field = Profile._meta.get_field('file')

        self.assertEqual(field.upload_to, 'uploads/')
