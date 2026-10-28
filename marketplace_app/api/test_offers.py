import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from marketplace_app.models import Offer, OfferDetail


User = get_user_model()


class OfferEndpointTests(TestCase):
    """Endpoint tests for offers and offer details."""

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
        """Create an API client plus customer and business users."""
        self.client = APIClient()
        self.customer = self.create_user('customerOffers', 'customer@example.com', 'customer')
        self.business = self.create_user('businessOffers', 'business@example.com', 'business')
        self.other_business = self.create_user(
            'otherBusiness', 'other-business@example.com', 'business'
        )

    def create_user(self, username, email, user_type):
        """Return a new user of the given type."""
        return User.objects.create_user(
            username=username,
            email=email,
            password='pass',
            type=user_type,
        )

    def detail_payload(self, offer_type, *, title=None, price=100, delivery=5):
        """Return a valid offer detail payload for the given tier."""
        return {
            'title': title or f'{offer_type.title()} service',
            'revisions': 2,
            'delivery_time_in_days': delivery,
            'price': price,
            'features': ['Original work'],
            'offer_type': offer_type,
        }

    def offer_payload(self, title='Design Package', *, detail_prices=(100, 200, 300)):
        """Return a valid offer payload with all three tiers."""
        return {
            'title': title,
            'description': 'Professional services',
            'details': [
                self.detail_payload(tier, price=price)
                for tier, price in zip(('basic', 'standard', 'premium'), detail_prices)
            ],
        }

    def create_offer(self, *, creator=None, title='Design Package', detail_prices=(100, 200, 300)):
        """Create an offer via the API and return the response data."""
        self.client.force_authenticate(creator or self.business)
        response = self.client.post(
            '/api/offers/', self.offer_payload(title, detail_prices=detail_prices), format='json'
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def jpeg_upload(self, name='offer.jpg'):
        """Return an in-memory 1x1 JPEG upload with the given name."""
        image_bytes = BytesIO()
        Image.new('RGB', (1, 1), color='blue').save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        image_bytes.name = name
        return image_bytes

    def assert_offer_summary(self, first):
        """Assert the newest list entry has the expected summary fields."""
        self.assertEqual(first['title'], 'Second Design')
        self.assertEqual(first['min_price'], Decimal('50.00'))
        self.assertEqual(first['min_delivery_time'], 5)
        self.assertEqual(len(first['details']), 3)
        self.assertEqual(first['user_details']['username'], 'businessOffers')

    def test_list_is_public_paginated_and_returns_offer_summary(self):
        """Anonymous list returns a paginated offer summary."""
        self.create_offer(title='First Design')
        self.create_offer(title='Second Design', detail_prices=(50, 200, 300))
        self.client.force_authenticate(None)

        response = self.client.get('/api/offers/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assert_offer_summary(response.data['results'][0])

    def assert_page_size_behavior(self):
        """Assert page_size paginates and is capped at 100 results."""
        paginated = self.client.get('/api/offers/?page_size=1')
        self.assertIsNotNone(paginated.data['next'])

        capped = self.client.get('/api/offers/?page_size=1000')
        self.assertEqual(capped.status_code, 200)
        self.assertLessEqual(len(capped.data['results']), 100)

    def test_list_filters_search_ordering_and_page_size(self):
        """List supports filters, search, ordering and page size."""
        self.create_offer(title='Alpha design', detail_prices=(100, 200, 300))
        self.create_offer(title='Beta illustration', detail_prices=(50, 150, 250))
        self.create_offer(title='Gamma branding', detail_prices=(250, 350, 450))
        self.client.force_authenticate(None)
        query = 'min_price=100&max_delivery_time=5&search=DESIGN&ordering=min_price&page_size=1'

        response = self.client.get(f'/api/offers/?{query}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Alpha design')
        self.assert_page_size_behavior()

    def test_list_rejects_invalid_and_unknown_query_parameters(self):
        """Invalid or unknown query parameters yield 400."""
        self.client.force_authenticate(None)

        for query in ('?min_price=not-a-number', '?ordering=title', '?unknown=1'):
            with self.subTest(query=query):
                response = self.client.get(f'/api/offers/{query}')
                self.assertEqual(response.status_code, 400)

    def test_create_requires_authentication_and_business_role(self):
        """Create needs authentication (401) and business role (403)."""
        payload = self.offer_payload()

        self.assertEqual(self.client.post('/api/offers/', payload, format='json').status_code, 401)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post('/api/offers/', payload, format='json').status_code, 403)

    def assert_invalid_tier_sets_rejected(self):
        """Assert duplicate and incomplete tier sets are rejected with 400."""
        payload = self.offer_payload()
        payload['details'][2]['offer_type'] = 'standard'
        invalid = self.client.post('/api/offers/', payload, format='json')
        self.assertEqual(invalid.status_code, 400)

        incomplete_payload = self.offer_payload()
        incomplete_payload['details'] = incomplete_payload['details'][:2]
        incomplete = self.client.post('/api/offers/', incomplete_payload, format='json')
        self.assertEqual(incomplete.status_code, 400)
        self.assertFalse(Offer.objects.filter(title='Design Package').exists())

    def test_create_requires_exactly_one_of_each_tier_and_returns_nested_details(self):
        """Create requires one detail per tier and returns nested details."""
        self.client.force_authenticate(self.business)
        self.assert_invalid_tier_sets_rejected()

        valid = self.client.post('/api/offers/', self.offer_payload(), format='json')
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(
            set(valid.data), {'id', 'title', 'image', 'description', 'details'}
        )
        self.assertEqual(Offer.objects.get(pk=valid.data['id']).user_id, self.business.pk)
        self.assertEqual(
            {item['offer_type'] for item in valid.data['details']},
            {'basic', 'standard', 'premium'},
        )
        self.assertTrue(all('id' in item for item in valid.data['details']))

    def invalid_create_payloads(self):
        """Return payloads each violating one create validation rule."""
        payloads = [self.offer_payload() for _ in range(6)]
        payloads[0]['title'] = ' '
        payloads[1]['description'] = 'd' * 501
        payloads[2]['details'][0]['price'] = 0
        payloads[3]['details'][0]['price'] = 100000.01
        payloads[4]['details'][0]['delivery_time_in_days'] = 366
        payloads[5]['details'][0]['revisions'] = 101
        return payloads

    def test_create_validates_price_delivery_revision_title_and_description(self):
        """Create rejects out-of-range or blank fields with 400."""
        self.client.force_authenticate(self.business)

        for payload in self.invalid_create_payloads():
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.client.post('/api/offers/', payload, format='json').status_code,
                    400,
                )

    def test_database_constraint_rejects_negative_revisions_on_bulk_insert(self):
        """The database rejects negative revisions even on bulk insert."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            offer = Offer.objects.create(user=self.business, title='Constraint check')
            invalid_detail = OfferDetail(
                offer=offer,
                title='Negative revisions',
                revisions=-1,
                delivery_time_in_days=5,
                price=Decimal('10.00'),
                features=[],
                offer_type=OfferDetail.OfferType.BASIC,
            )
            OfferDetail.objects.bulk_create([invalid_detail])

    def test_create_accepts_multipart_json_details_and_valid_image(self):
        """Multipart create accepts JSON-encoded details and a valid image."""
        self.client.force_authenticate(self.business)
        payload = self.offer_payload()
        payload['details'] = json.dumps(payload['details'])
        payload['image'] = self.jpeg_upload('catalog.jpg')

        response = self.client.post('/api/offers/', payload, format='multipart')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['image'], 'catalog.jpg')

    def upload_offer_image(self, offer_id):
        """PATCH an image onto the offer; return (stored basename, stored path)."""
        image_update = self.client.patch(
            f"/api/offers/{offer_id}/",
            {'image': self.jpeg_upload('catalog.jpg')},
            format='multipart',
        )
        self.assertEqual(image_update.status_code, 200)
        self.assertTrue(image_update.data['image'].startswith('catalog'))
        stored_basename = image_update.data['image']
        return stored_basename, next(Path(self.media_directory.name).rglob(stored_basename))

    def assert_omitted_image_preserved(self, offer_id, stored_basename):
        """Assert a PATCH without image keeps the stored image."""
        omitted = self.client.patch(
            f"/api/offers/{offer_id}/", {'title': 'Updated Package'}, format='json'
        )
        self.assertEqual(omitted.status_code, 200)
        self.assertEqual(omitted.data['image'], stored_basename)

    def assert_null_image_clears(self, offer_id, stored_image_path):
        """Assert PATCH image=null clears the image and deletes the file."""
        with self.captureOnCommitCallbacks(execute=True):
            cleared = self.client.patch(
                f"/api/offers/{offer_id}/", {'image': None}, format='json'
            )
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.data['image'])
        self.assertFalse(stored_image_path.exists())

    def test_patch_omitted_image_preserves_and_null_clears(self):
        """PATCH keeps the image when omitted and clears it when null."""
        created = self.create_offer()
        self.client.force_authenticate(self.business)
        stored_basename, stored_image_path = self.upload_offer_image(created['id'])

        self.assert_omitted_image_preserved(created['id'], stored_basename)
        self.assert_null_image_clears(created['id'], stored_image_path)

    def test_patch_rejects_null_required_detail_fields(self):
        """PATCH with null required detail fields yields 400."""
        created = self.create_offer()
        self.client.force_authenticate(self.business)

        response = self.client.patch(
            f"/api/offers/{created['id']}/",
            {'details': [{'offer_type': 'basic', 'price': None}]},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_patch_returns_404_for_missing_offer(self):
        """PATCH on a missing offer yields 404."""
        self.client.force_authenticate(self.business)

        response = self.client.patch(
            '/api/offers/999999/', {'title': 'Missing'}, format='json'
        )

        self.assertEqual(response.status_code, 404)

    def test_create_rejects_invalid_or_oversized_image(self):
        """Create rejects non-image and oversized uploads with 400."""
        self.client.force_authenticate(self.business)
        invalid = self.offer_payload()
        invalid['image'] = BytesIO(b'not an image')
        invalid['image'].name = 'bad.jpg'
        response = self.client.post('/api/offers/', invalid, format='multipart')
        self.assertEqual(response.status_code, 400)

        oversized = self.offer_payload()
        oversized['image'] = BytesIO(b'0' * (5 * 1024 * 1024 + 1))
        oversized['image'].name = 'large.jpg'
        response = self.client.post('/api/offers/', oversized, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_retrieve_requires_authentication_and_returns_detail_urls(self):
        """Retrieve needs authentication and returns detail URLs."""
        created = self.create_offer()
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(f"/api/offers/{created['id']}/").status_code, 401
        )

        self.client.force_authenticate(self.customer)
        response = self.client.get(f"/api/offers/{created['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['details']), 3)
        self.assertTrue(all('/api/offerdetails/' in item['url'] for item in response.data['details']))

    def test_retrieve_and_detail_retrieve_return_404_for_missing_records(self):
        """Retrieving missing offers or details yields 404."""
        self.client.force_authenticate(self.customer)

        self.assertEqual(self.client.get('/api/offers/999999/').status_code, 404)
        self.assertEqual(self.client.get('/api/offerdetails/999999/').status_code, 404)

    def assert_patched_details(self, response, original_detail_ids):
        """Assert a partial detail PATCH kept ids and untouched fields."""
        self.assertEqual(response.status_code, 200, response.data)
        details = {item['offer_type']: item for item in response.data['details']}
        self.assertEqual(details['basic']['id'], original_detail_ids['basic'])
        self.assertEqual(details['basic']['title'], 'Updated Basic')
        self.assertEqual(details['basic']['price'], '100.00')
        self.assertEqual(details['standard']['id'], original_detail_ids['standard'])

    def test_patch_is_owner_only_partial_preserves_detail_ids_and_missing_fields(self):
        """PATCH is owner-only, partial, and keeps detail ids and fields."""
        created = self.create_offer()
        original_detail_ids = {item['offer_type']: item['id'] for item in created['details']}
        self.client.force_authenticate(self.other_business)
        denied = self.client.patch(f"/api/offers/{created['id']}/", {'title': 'Not mine'})
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(self.business)
        response = self.client.patch(
            f"/api/offers/{created['id']}/",
            {'details': [{'offer_type': 'basic', 'title': 'Updated Basic'}]},
            format='json',
        )
        self.assert_patched_details(response, original_detail_ids)

    def test_delete_is_owner_only_and_returns_204(self):
        """DELETE is owner-only and returns 204."""
        created = self.create_offer()
        self.client.force_authenticate(self.other_business)
        self.assertEqual(
            self.client.delete(f"/api/offers/{created['id']}/").status_code, 403
        )

        self.client.force_authenticate(self.business)
        response = self.client.delete(f"/api/offers/{created['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertEqual(self.client.get(f"/api/offers/{created['id']}/").status_code, 404)

    def test_patch_and_delete_require_authentication(self):
        """PATCH and DELETE need authentication (401)."""
        created = self.create_offer()
        self.client.force_authenticate(None)

        self.assertEqual(
            self.client.patch(f"/api/offers/{created['id']}/", {'title': 'X'}).status_code,
            401,
        )
        self.assertEqual(
            self.client.delete(f"/api/offers/{created['id']}/").status_code,
            401,
        )

    def test_delete_returns_404_for_missing_offer(self):
        """DELETE on a missing offer yields 404."""
        self.client.force_authenticate(self.business)

        response = self.client.delete('/api/offers/999999/')

        self.assertEqual(response.status_code, 404)

    def test_offer_detail_retrieve_requires_authentication(self):
        """Offer detail retrieve needs authentication."""
        created = self.create_offer()
        detail_id = created['details'][0]['id']
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/api/offerdetails/{detail_id}/').status_code, 401)

        self.client.force_authenticate(self.customer)
        response = self.client.get(f'/api/offerdetails/{detail_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['offer_type'], 'basic')

    def read_error_cases(self, offer_id, detail_id):
        """Return (target, is_property, method, url, data) 500 read scenarios."""
        serializers = 'marketplace_app.api.offer_serializers.'
        return [
            ('marketplace_app.api.offer_views.OfferViewSet.get_queryset',
             False, 'get', '/api/offers/', None),
            (serializers + 'OfferDetailReadOnlySerializer.data',
             True, 'get', f'/api/offers/{offer_id}/', None),
            (serializers + 'OfferDetailReadSerializer.data',
             True, 'get', f'/api/offerdetails/{detail_id}/', None),
        ]

    def write_error_cases(self, offer_id):
        """Return (target, is_property, method, url, data) 500 write scenarios."""
        serializers = 'marketplace_app.api.offer_serializers.'
        offer_url = f'/api/offers/{offer_id}/'
        update = {'title': 'Updated'}
        return [
            (serializers + 'OfferCreateSerializer.save',
             False, 'post', '/api/offers/', self.offer_payload()),
            (serializers + 'OfferUpdateSerializer.update_offer',
             False, 'patch', offer_url, update),
            (serializers + 'OfferUpdateResponseSerializer.data',
             True, 'patch', offer_url, update),
            ('marketplace_app.models.Offer.delete', False, 'delete', offer_url, None),
        ]

    def send_request(self, method, url, data):
        """Send a request, using JSON format only when a body is given."""
        request = getattr(self.client, method)
        return request(url) if data is None else request(url, data, format='json')

    def assert_safe_500(self, case):
        """Patch the target to raise and assert the safe 500 response."""
        target, is_property, method, url, data = case
        options = {'new_callable': PropertyMock} if is_property else {}
        with patch(target, side_effect=RuntimeError('sensitive failure'), **options):
            response = self.send_request(method, url, data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {'detail': 'Internal server error.'})

    def test_documented_internal_errors_return_safe_500_details(self):
        """Internal failures return a generic 500 without leaking details."""
        created = self.create_offer()
        detail_id = created['details'][0]['id']
        cases = self.read_error_cases(created['id'], detail_id)
        cases += self.write_error_cases(created['id'])

        for case in cases:
            with self.subTest(target=case[0]):
                self.assert_safe_500(case)
