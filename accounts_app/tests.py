from django.conf import settings
from django.test import TestCase, override_settings

from accounts_app.models import Profile, User


@override_settings(MEDIA_ROOT=settings.BASE_DIR / 'test-media')
class AccountFoundationTests(TestCase):
    def test_user_supports_customer_and_business_roles(self):
        customer = User.objects.create_user(
            username='customer-one',
            email='customer@example.com',
            password='pass',
            type=User.UserType.CUSTOMER,
        )
        business = User.objects.create_user(
            username='business-one',
            email='business@example.com',
            password='pass',
            type=User.UserType.BUSINESS,
        )

        self.assertEqual(customer.type, 'customer')
        self.assertEqual(business.type, 'business')

    def test_profile_is_one_to_one_with_user(self):
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

    def test_role_is_required_and_limited_to_documented_values(self):
        field = User._meta.get_field('type')

        self.assertEqual(field.max_length, 10)
        self.assertEqual(
            set(field.choices),
            {('customer', 'Customer'), ('business', 'Business')},
        )

    def test_usernames_and_emails_have_case_insensitive_database_constraints(self):
        constraints = {constraint.name for constraint in User._meta.constraints}

        self.assertIn('accounts_user_username_ci_unique', constraints)
        self.assertIn('accounts_user_email_ci_unique', constraints)

    def test_profile_image_uses_uploads_directory(self):
        field = Profile._meta.get_field('file')

        self.assertEqual(field.upload_to, 'uploads/')
