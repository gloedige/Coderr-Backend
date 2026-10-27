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
        self.assertIn('type', User.REQUIRED_FIELDS)

    def test_database_restricts_user_role_values(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(
                username='invalid-role',
                email='invalid-role@example.com',
                type='admin',
            )

    def test_username_case_is_preserved_and_email_is_normalized(self):
        user = User.objects.create_user(
            username='  neuerNutzer  ',
            email='Mixed.Email@Example.com',
            password='pass',
            type=User.UserType.CUSTOMER,
        )

        self.assertEqual(user.username, 'neuerNutzer')
        self.assertEqual(user.email, 'mixed.email@example.com')

    def test_usernames_are_case_sensitive_but_exact_duplicates_are_rejected(self):
        from django.db import IntegrityError, transaction

        original = User.objects.create_user(
            username='UniqueName',
            email='unique@example.com',
            password='pass',
            type=User.UserType.CUSTOMER,
        )
        case_variant = User.objects.create_user(
            username='uniquename',
            email='case-variant@example.com',
            password='pass',
            type=User.UserType.BUSINESS,
        )

        self.assertEqual(original.username, 'UniqueName')
        self.assertEqual(case_variant.username, 'uniquename')

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                username='UniqueName',
                email='different@example.com',
                password='pass',
                type=User.UserType.BUSINESS,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                username='differentname',
                email='UNIQUE@example.com',
                password='pass',
                type=User.UserType.BUSINESS,
            )

    def test_profile_image_uses_uploads_directory(self):
        field = Profile._meta.get_field('file')

        self.assertEqual(field.upload_to, 'uploads/')
