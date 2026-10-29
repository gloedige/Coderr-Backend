from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from profile_app.models import Profile


User = get_user_model()


class ProfileEndpointTests(TestCase):
    """Checks the profile detail, update and list endpoints."""

    @classmethod
    def setUpClass(cls):
        """Redirect MEDIA_ROOT to a temporary directory."""
        super().setUpClass()
        cls.media_directory = TemporaryDirectory()
        cls.media_settings = override_settings(MEDIA_ROOT=cls.media_directory.name)
        cls.media_settings.enable()

    @classmethod
    def tearDownClass(cls):
        """Restore settings and remove the temporary media directory."""
        cls.media_settings.disable()
        cls.media_directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        """Create a client plus a customer and a filled-in business user."""
        self.client = APIClient()
        User.objects.filter(username__startswith='guest_').delete()
        self.customer = self.create_user('customerProfile', 'customer@example.com', 'customer')
        self.business = self.create_user('businessProfile', 'business@example.com', 'business')
        self.customer_profile = self.customer.profile
        self.business_profile = self.business.profile
        self.fill_business_profile()

    def fill_business_profile(self):
        """Populate the business profile with sample data."""
        self.business_profile.first_name = 'Max'
        self.business_profile.last_name = 'Mustermann'
        self.business_profile.location = 'Berlin'
        self.business_profile.tel = '123456789'
        self.business_profile.description = 'Business profile'
        self.business_profile.working_hours = '9-17'
        self.business_profile.save()

    def create_user(self, username, email, user_type):
        """Create and return a user of the given type with an attached profile."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password='pass',
            type=user_type,
        )
        Profile.objects.create(user=user)
        return user

    def jpeg_upload(self, name='profile.jpg'):
        """Return an in-memory 1x1 JPEG file with the given name."""
        image_bytes = BytesIO()
        Image.new('RGB', (1, 1), color='red').save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        image_bytes.name = name
        return image_bytes

    def patch_profile(self, pk, data, data_format='json'):
        """PATCH the profile with the given pk and return the response."""
        return self.client.patch(f'/api/profile/{pk}/', data, format=data_format)

    def expected_customer_detail(self, created_at):
        """Return the expected untouched customer detail payload."""
        return {
            'user': self.customer.pk,
            'username': 'customerProfile',
            'first_name': '',
            'last_name': '',
            'file': None,
            'location': '',
            'tel': '',
            'description': '',
            'working_hours': '',
            'type': 'customer',
            'email': 'customer@example.com',
            'created_at': created_at,
        }

    def expected_business_list(self):
        """Return the expected business list projection."""
        return [{
            'user': self.business.pk,
            'username': 'businessProfile',
            'first_name': 'Max',
            'last_name': 'Mustermann',
            'file': None,
            'location': 'Berlin',
            'tel': '123456789',
            'description': 'Business profile',
            'working_hours': '9-17',
            'type': 'business',
        }]

    def expected_customer_list(self):
        """Return the expected customer list projection."""
        return [{
            'user': self.customer.pk,
            'username': 'customerProfile',
            'first_name': '',
            'last_name': '',
            'file': None,
            'uploaded_at': None,
            'type': 'customer',
        }]

    def test_get_profile_returns_documented_detail_schema_and_blank_strings(self):
        """Profile detail returns the documented schema with blank strings."""
        self.client.force_authenticate(self.customer)

        response = self.client.get(f'/api/profile/{self.customer.pk}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            self.expected_customer_detail(response.data['created_at']),
        )
        self.assertIsInstance(response.data['created_at'], str)

    def test_get_profile_requires_authentication_and_returns_404_for_missing(self):
        """Profile detail needs authentication and 404s for unknown profiles."""
        response = self.client.get(f'/api/profile/{self.customer.pk}/')
        self.assertEqual(response.status_code, 401)

        self.client.force_authenticate(self.customer)
        response = self.client.get('/api/profile/999999/')
        self.assertEqual(response.status_code, 404)

    def test_patch_updates_owner_profile_and_email_but_not_username_or_type(self):
        """PATCH updates profile fields and email but never username or type."""
        self.client.force_authenticate(self.customer)

        response = self.patch_profile(self.customer.pk, {
            'first_name': 'Jane',
            'location': 'Hamburg',
            'email': '  New.Email@Example.com  ',
            'username': 'changedUsername',
            'type': 'business',
        })

        self.assertEqual(response.status_code, 200)
        self.assert_owner_updated()

    def assert_owner_updated(self):
        """Assert the customer's PATCH changed only allowed fields."""
        self.customer.refresh_from_db()
        self.customer_profile.refresh_from_db()
        self.assertEqual(self.customer.username, 'customerProfile')
        self.assertEqual(self.customer.type, 'customer')
        self.assertEqual(self.customer.email, 'new.email@example.com')
        self.assertEqual(self.customer_profile.first_name, 'Jane')
        self.assertEqual(self.customer_profile.location, 'Hamburg')

    def test_patch_is_owner_only_and_requires_authentication(self):
        """PATCH requires authentication and ownership."""
        response = self.patch_profile(self.customer.pk, {'first_name': 'Nope'})
        self.assertEqual(response.status_code, 401)

        self.client.force_authenticate(self.business)
        response = self.patch_profile(self.customer.pk, {'first_name': 'Nope'})
        self.assertEqual(response.status_code, 403)

    def test_patch_returns_404_for_missing_profile(self):
        """PATCH of an unknown profile returns 404."""
        self.client.force_authenticate(self.customer)

        response = self.patch_profile(999999, {'first_name': 'Missing'})

        self.assertEqual(response.status_code, 404)

    def test_patch_returns_safe_500_detail_on_internal_error(self):
        """Internal PATCH errors return a generic 500 detail."""
        self.client.force_authenticate(self.customer)

        with patch(
            'profile_app.api.serializers.ProfileUpdateSerializer.update_profile',
            side_effect=RuntimeError('sensitive update failure'),
        ):
            response = self.patch_profile(self.customer.pk, {'first_name': 'Updated'})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {'detail': 'Internal server error.'})

    def test_patch_rejects_case_insensitive_duplicate_email(self):
        """PATCH rejects an email already used in any letter case."""
        self.client.force_authenticate(self.customer)

        response = self.patch_profile(self.customer.pk, {'email': 'BUSINESS@example.com'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, 'customer@example.com')

    def test_customer_can_update_description_and_working_hours(self):
        """Customers can update description and working hours on their profile."""
        self.client.force_authenticate(self.customer)

        response = self.patch_profile(
            self.customer.pk,
            {'description': 'Available for consulting', 'working_hours': '10-18'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['description'], 'Available for consulting')
        self.assertEqual(response.data['working_hours'], '10-18')
        self.customer_profile.refresh_from_db()
        self.assertEqual(self.customer_profile.description, 'Available for consulting')
        self.assertEqual(self.customer_profile.working_hours, '10-18')

    def test_business_and_customer_lists_return_their_documented_projections(self):
        """Business and customer lists return their documented projections."""
        self.client.force_authenticate(self.customer)

        business_response = self.client.get('/api/profiles/business/')
        customer_response = self.client.get('/api/profiles/customer/')

        self.assertEqual(business_response.status_code, 200)
        self.assertEqual(business_response.data, self.expected_business_list())
        self.assertEqual(customer_response.status_code, 200)
        self.assertEqual(customer_response.data, self.expected_customer_list())

    def test_profile_lists_require_authentication(self):
        """Profile lists return 401 for anonymous users."""
        for path in ('/api/profiles/business/', '/api/profiles/customer/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)

    def test_profile_lists_return_safe_500_details_on_internal_errors(self):
        """Internal list errors return a generic 500 detail."""
        self.client.force_authenticate(self.customer)

        with patch(
            'profile_app.api.views.Profile.objects.select_related',
            side_effect=RuntimeError('sensitive database failure'),
        ):
            for path in ('/api/profiles/business/', '/api/profiles/customer/'):
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 500)
                    self.assertEqual(response.data, {'detail': 'Internal server error.'})

    def test_profile_detail_returns_safe_500_detail_on_internal_error(self):
        """Internal detail errors return a generic 500 detail."""
        self.client.force_authenticate(self.customer)

        with patch(
            'profile_app.api.views.ProfileDetailSerializer.data',
            new_callable=PropertyMock,
            side_effect=RuntimeError('sensitive serialization failure'),
        ):
            response = self.client.get(f'/api/profile/{self.customer.pk}/')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {'detail': 'Internal server error.'})

    def test_patch_uploads_valid_jpeg_and_returns_basename_and_upload_time(self):
        """A valid JPEG upload returns its basename and sets uploaded_at."""
        self.client.force_authenticate(self.customer)

        response = self.patch_profile(
            self.customer.pk,
            {'file': self.jpeg_upload('avatar.jpg')},
            'multipart',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['file'], 'avatar.jpg')
        self.customer_profile.refresh_from_db()
        self.assertIsNotNone(self.customer_profile.uploaded_at)

    def test_patch_omitted_file_preserves_existing_and_null_clears(self):
        """Omitting the file keeps it; sending null clears it."""
        self.client.force_authenticate(self.customer)
        self.customer_profile.file.save('original.jpg', self.jpeg_upload('original.jpg'))

        unchanged = self.patch_profile(self.customer.pk, {'location': 'Rome'})
        self.assertEqual(unchanged.status_code, 200)
        self.assertEqual(unchanged.data['file'], 'original.jpg')

        with self.captureOnCommitCallbacks(execute=True):
            cleared = self.patch_profile(self.customer.pk, {'file': None})
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.data['file'])
        self.assertFalse(self.customer_profile.file.storage.exists('uploads/original.jpg'))

    def test_patch_rejects_non_image_and_oversized_uploads(self):
        """Non-image and oversized uploads are rejected with 400."""
        self.client.force_authenticate(self.customer)
        bad_file = BytesIO(b'not an image')
        bad_file.name = 'bad.jpg'
        too_big = BytesIO(b'0' * (5 * 1024 * 1024 + 1))
        too_big.name = 'large.jpg'

        for upload in (bad_file, too_big):
            response = self.patch_profile(self.customer.pk, {'file': upload}, 'multipart')
            self.assertEqual(response.status_code, 400)