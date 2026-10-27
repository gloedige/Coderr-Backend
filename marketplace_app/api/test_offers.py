import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from marketplace_app.models import Offer


User = get_user_model()


class OfferEndpointTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_directory = TemporaryDirectory()
        cls.media_settings = override_settings(MEDIA_ROOT=cls.media_directory.name)
        cls.media_settings.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_settings.disable()
        cls.media_directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()
        self.customer = self.create_user('customerOffers', 'customer@example.com', 'customer')
        self.business = self.create_user('businessOffers', 'business@example.com', 'business')
        self.other_business = self.create_user(
            'otherBusiness', 'other-business@example.com', 'business'
        )

    def create_user(self, username, email, user_type):
        return User.objects.create_user(
            username=username,
            email=email,
            password='pass',
            type=user_type,
        )

    def detail_payload(self, offer_type, *, title=None, price=100, delivery=5):
        return {
            'title': title or f'{offer_type.title()} service',
            'revisions': 2,
            'delivery_time_in_days': delivery,
            'price': price,
            'features': ['Original work'],
            'offer_type': offer_type,
        }

    def offer_payload(self, title='Design Package', *, detail_prices=(100, 200, 300)):
        return {
            'title': title,
            'description': 'Professional services',
            'details': [
                self.detail_payload(tier, price=price)
                for tier, price in zip(('basic', 'standard', 'premium'), detail_prices)
            ],
        }

    def create_offer(self, *, creator=None, title='Design Package', detail_prices=(100, 200, 300)):
        self.client.force_authenticate(creator or self.business)
        response = self.client.post(
            '/api/offers/', self.offer_payload(title, detail_prices=detail_prices), format='json'
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def jpeg_upload(self, name='offer.jpg'):
        image_bytes = BytesIO()
        Image.new('RGB', (1, 1), color='blue').save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        image_bytes.name = name
        return image_bytes

    def test_list_is_public_paginated_and_returns_offer_summary(self):
        self.create_offer(title='First Design')
        self.create_offer(title='Second Design', detail_prices=(50, 200, 300))
        self.client.force_authenticate(None)

        response = self.client.get('/api/offers/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        first = response.data['results'][0]
        self.assertEqual(first['title'], 'Second Design')
        self.assertEqual(first['min_price'], Decimal('50.00'))
        self.assertEqual(first['min_delivery_time'], 5)
        self.assertEqual(len(first['details']), 3)
        self.assertEqual(first['user_details']['username'], 'businessOffers')

    def test_list_filters_search_ordering_and_page_size(self):
        self.create_offer(title='Alpha design', detail_prices=(100, 200, 300))
        self.create_offer(title='Beta illustration', detail_prices=(50, 150, 250))
        self.create_offer(title='Gamma branding', detail_prices=(250, 350, 450))
        self.client.force_authenticate(None)

        response = self.client.get(
            '/api/offers/?min_price=100&max_delivery_time=5&search=DESIGN&ordering=min_price&page_size=1'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Alpha design')

        paginated = self.client.get('/api/offers/?page_size=1')
        self.assertIsNotNone(paginated.data['next'])

        capped = self.client.get('/api/offers/?page_size=1000')
        self.assertEqual(capped.status_code, 200)
        self.assertLessEqual(len(capped.data['results']), 100)

    def test_list_rejects_invalid_and_unknown_query_parameters(self):
        self.client.force_authenticate(None)

        for query in ('?min_price=not-a-number', '?ordering=title', '?unknown=1'):
            with self.subTest(query=query):
                response = self.client.get(f'/api/offers/{query}')
                self.assertEqual(response.status_code, 400)

    def test_create_requires_authentication_and_business_role(self):
        payload = self.offer_payload()

        self.assertEqual(self.client.post('/api/offers/', payload, format='json').status_code, 401)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post('/api/offers/', payload, format='json').status_code, 403)

    def test_create_requires_exactly_one_of_each_tier_and_returns_nested_details(self):
        self.client.force_authenticate(self.business)
        payload = self.offer_payload()
        payload['details'][2]['offer_type'] = 'standard'

        invalid = self.client.post('/api/offers/', payload, format='json')
        self.assertEqual(invalid.status_code, 400)

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

    def test_create_validates_price_delivery_revision_title_and_description(self):
        self.client.force_authenticate(self.business)
        invalid_payloads = []

        payload = self.offer_payload()
        payload['title'] = ' '
        invalid_payloads.append(payload)

        payload = self.offer_payload()
        payload['description'] = 'd' * 501
        invalid_payloads.append(payload)

        payload = self.offer_payload()
        payload['details'][0]['price'] = 0
        invalid_payloads.append(payload)

        payload = self.offer_payload()
        payload['details'][0]['price'] = 100000.01
        invalid_payloads.append(payload)

        payload = self.offer_payload()
        payload['details'][0]['delivery_time_in_days'] = 366
        invalid_payloads.append(payload)

        payload = self.offer_payload()
        payload['details'][0]['revisions'] = 101
        invalid_payloads.append(payload)

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.client.post('/api/offers/', payload, format='json').status_code,
                    400,
                )

    def test_create_accepts_multipart_json_details_and_valid_image(self):
        self.client.force_authenticate(self.business)
        payload = self.offer_payload()
        payload['details'] = json.dumps(payload['details'])
        payload['image'] = self.jpeg_upload('catalog.jpg')

        response = self.client.post('/api/offers/', payload, format='multipart')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['image'], 'catalog.jpg')

    def test_patch_omitted_image_preserves_and_null_clears(self):
        created = self.create_offer()
        self.client.force_authenticate(self.business)
        image_update = self.client.patch(
            f"/api/offers/{created['id']}/",
            {'image': self.jpeg_upload('catalog.jpg')},
            format='multipart',
        )
        self.assertEqual(image_update.status_code, 200)
        self.assertTrue(image_update.data['image'].startswith('catalog'))
        stored_basename = image_update.data['image']
        stored_image_path = next(Path(self.media_directory.name).rglob(stored_basename))

        omitted = self.client.patch(
            f"/api/offers/{created['id']}/", {'title': 'Updated Package'}, format='json'
        )
        self.assertEqual(omitted.status_code, 200)
        self.assertEqual(omitted.data['image'], stored_basename)

        with self.captureOnCommitCallbacks(execute=True):
            cleared = self.client.patch(
                f"/api/offers/{created['id']}/", {'image': None}, format='json'
            )
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.data['image'])
        self.assertFalse(stored_image_path.exists())

    def test_patch_rejects_null_required_detail_fields(self):
        created = self.create_offer()
        self.client.force_authenticate(self.business)

        response = self.client.patch(
            f"/api/offers/{created['id']}/",
            {'details': [{'offer_type': 'basic', 'price': None}]},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_patch_returns_404_for_missing_offer(self):
        self.client.force_authenticate(self.business)

        response = self.client.patch(
            '/api/offers/999999/', {'title': 'Missing'}, format='json'
        )

        self.assertEqual(response.status_code, 404)

    def test_create_rejects_invalid_or_oversized_image(self):
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
        self.client.force_authenticate(self.customer)

        self.assertEqual(self.client.get('/api/offers/999999/').status_code, 404)
        self.assertEqual(self.client.get('/api/offerdetails/999999/').status_code, 404)

    def test_patch_is_owner_only_partial_preserves_detail_ids_and_missing_fields(self):
        created = self.create_offer()
        original_detail_ids = {item['offer_type']: item['id'] for item in created['details']}
        self.client.force_authenticate(self.other_business)
        denied = self.client.patch(
            f"/api/offers/{created['id']}/", {'title': 'Not mine'}, format='json'
        )
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(self.business)
        response = self.client.patch(
            f"/api/offers/{created['id']}/",
            {'details': [{'offer_type': 'basic', 'title': 'Updated Basic'}]},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        details = {item['offer_type']: item for item in response.data['details']}
        self.assertEqual(details['basic']['id'], original_detail_ids['basic'])
        self.assertEqual(details['basic']['title'], 'Updated Basic')
        self.assertEqual(details['basic']['price'], '100.00')
        self.assertEqual(details['standard']['id'], original_detail_ids['standard'])

    def test_delete_is_owner_only_and_returns_204(self):
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
        self.client.force_authenticate(self.business)

        response = self.client.delete('/api/offers/999999/')

        self.assertEqual(response.status_code, 404)

    def test_offer_detail_retrieve_requires_authentication(self):
        created = self.create_offer()
        detail_id = created['details'][0]['id']
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/api/offerdetails/{detail_id}/').status_code, 401)

        self.client.force_authenticate(self.customer)
        response = self.client.get(f'/api/offerdetails/{detail_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['offer_type'], 'basic')

    def test_documented_internal_errors_return_safe_500_details(self):
        created = self.create_offer()
        detail_id = created['details'][0]['id']

        with patch(
            'marketplace_app.api.views.OfferViewSet.get_queryset',
            side_effect=RuntimeError('sensitive list failure'),
        ):
            list_response = self.client.get('/api/offers/')
        self.assertEqual(list_response.status_code, 500)
        self.assertEqual(list_response.data, {'detail': 'Internal server error.'})

        with patch(
            'marketplace_app.api.serializers.OfferCreateSerializer.save',
            side_effect=RuntimeError('sensitive create failure'),
        ):
            create_response = self.client.post(
                '/api/offers/', self.offer_payload(), format='json'
            )
        self.assertEqual(create_response.status_code, 500)
        self.assertEqual(create_response.data, {'detail': 'Internal server error.'})

        with patch(
            'marketplace_app.api.serializers.OfferDetailReadOnlySerializer.data',
            new_callable=PropertyMock,
            side_effect=RuntimeError('sensitive retrieve failure'),
        ):
            retrieve_response = self.client.get(f"/api/offers/{created['id']}/")
        self.assertEqual(retrieve_response.status_code, 500)
        self.assertEqual(retrieve_response.data, {'detail': 'Internal server error.'})

        with patch(
            'marketplace_app.api.serializers.OfferUpdateSerializer.update_offer',
            side_effect=RuntimeError('sensitive update failure'),
        ):
            update_response = self.client.patch(
                f"/api/offers/{created['id']}/", {'title': 'Updated'}, format='json'
            )
        self.assertEqual(update_response.status_code, 500)
        self.assertEqual(update_response.data, {'detail': 'Internal server error.'})

        with patch(
            'marketplace_app.api.serializers.OfferUpdateResponseSerializer.data',
            new_callable=PropertyMock,
            side_effect=RuntimeError('sensitive patch response failure'),
        ):
            update_response_error = self.client.patch(
                f"/api/offers/{created['id']}/", {'title': 'Updated'}, format='json'
            )
        self.assertEqual(update_response_error.status_code, 500)
        self.assertEqual(update_response_error.data, {'detail': 'Internal server error.'})

        with patch(
            'marketplace_app.models.Offer.delete',
            side_effect=RuntimeError('sensitive delete failure'),
        ):
            delete_response = self.client.delete(f"/api/offers/{created['id']}/")
        self.assertEqual(delete_response.status_code, 500)
        self.assertEqual(delete_response.data, {'detail': 'Internal server error.'})

        with patch(
            'marketplace_app.api.serializers.OfferDetailReadSerializer.data',
            new_callable=PropertyMock,
            side_effect=RuntimeError('sensitive detail failure'),
        ):
            detail_response = self.client.get(f'/api/offerdetails/{detail_id}/')
        self.assertEqual(detail_response.status_code, 500)
        self.assertEqual(detail_response.data, {'detail': 'Internal server error.'})
