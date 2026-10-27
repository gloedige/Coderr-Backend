from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from marketplace_app.models import Offer, OfferDetail, Order


User = get_user_model()


class ReviewEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = self.create_user('reviewCustomer', 'customer@example.com', 'customer')
        self.other_customer = self.create_user('otherCustomer', 'other@example.com', 'customer')
        self.business = self.create_user('reviewBusiness', 'business@example.com', 'business')
        self.other_business = self.create_user('otherBusiness', 'otherbiz@example.com', 'business')
        self.detail = self.create_completed_order()

    def create_user(self, username, email, user_type):
        return User.objects.create_user(
            username=username,
            email=email,
            password='pass',
            type=user_type,
        )

    def create_completed_order(self, customer=None, business=None, status=Order.Status.COMPLETED):
        customer = customer or self.customer
        business = business or self.business
        offer = Offer.objects.create(user=business, title='Reviewed service')
        detail_specs = (
            (OfferDetail.OfferType.BASIC, 'Completed basic package', 2, 5, '99.00'),
            (OfferDetail.OfferType.STANDARD, 'Completed standard package', 5, 7, '199.00'),
            (OfferDetail.OfferType.PREMIUM, 'Completed premium package', 10, 10, '299.00'),
        )
        details = [
            OfferDetail.objects.create(
                offer=offer,
                title=title,
                revisions=revisions,
                delivery_time_in_days=delivery_time,
                price=Decimal(price),
                features=['delivery'],
                offer_type=offer_type,
            )
            for offer_type, title, revisions, delivery_time, price in detail_specs
        ]
        detail = details[0]
        Order.objects.create(
            customer_user=customer,
            business_user=business,
            title=detail.title,
            revisions=detail.revisions,
            delivery_time_in_days=detail.delivery_time_in_days,
            price=detail.price,
            features=detail.features,
            offer_type=detail.offer_type,
            status=status,
        )
        return detail

    def test_completed_order_offer_fixture_has_all_three_detail_tiers(self):
        offer = self.detail.offer

        self.assertEqual(offer.details.count(), 3)
        self.assertEqual(
            set(offer.details.values_list('offer_type', flat=True)),
            {'basic', 'standard', 'premium'},
        )

    def create_review(self, customer=None, business=None, rating=4, description='Great service'):
        customer = customer or self.customer
        business = business or self.business
        self.client.force_authenticate(customer)
        response = self.client.post(
            '/api/reviews/',
            {
                'business_user': business.pk,
                'rating': rating,
                'description': description,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_list_requires_auth_and_supports_filters_and_ordering(self):
        self.create_completed_order(customer=self.other_customer)
        first = self.create_review(rating=3, description='First')
        second = self.create_review(
            customer=self.other_customer,
            rating=5,
            description='Second',
        )
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/reviews/').status_code, 401)

        self.client.force_authenticate(self.business)
        response = self.client.get(
            f'/api/reviews/?business_user_id={self.business.pk}&ordering=-rating'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [second['id'], first['id']])
        self.assertTrue(all(item['business_user'] == self.business.pk for item in response.data))

        reviewer_filter = self.client.get(
            f'/api/reviews/?reviewer_id={self.customer.pk}'
        )
        self.assertEqual([item['id'] for item in reviewer_filter.data], [first['id']])

    def test_list_rejects_invalid_and_unknown_query_parameters(self):
        self.client.force_authenticate(self.customer)

        for query in ('?business_user_id=nope', '?ordering=created_at', '?unknown=1'):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f'/api/reviews/{query}').status_code, 400)

    def test_create_requires_customer_and_completed_order_for_same_business(self):
        payload = {'business_user': self.business.pk, 'rating': 4, 'description': 'Good'}
        self.assertEqual(self.client.post('/api/reviews/', payload, format='json').status_code, 401)

        self.client.force_authenticate(self.other_business)
        self.assertEqual(self.client.post('/api/reviews/', payload, format='json').status_code, 403)

        self.client.force_authenticate(self.other_customer)
        no_order = self.client.post('/api/reviews/', payload, format='json')
        self.assertEqual(no_order.status_code, 400)

        create_completed = self.create_completed_order(
            customer=self.other_customer,
            business=self.other_business,
            status=Order.Status.IN_PROGRESS,
        )
        self.client.force_authenticate(self.other_customer)
        not_completed = self.client.post(
            '/api/reviews/',
            {'business_user': self.other_business.pk, 'rating': 4, 'description': 'Good'},
            format='json',
        )
        self.assertEqual(not_completed.status_code, 400)

        self.assertIsNotNone(create_completed.pk)

    def test_create_requires_matching_completed_order_and_returns_review(self):
        self.client.force_authenticate(self.other_customer)
        response = self.client.post(
            '/api/reviews/',
            {'business_user': self.other_business.pk, 'rating': 4, 'description': 'Good'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

        created = self.create_review(rating=5, description='Excellent')
        self.assertEqual(created['business_user'], self.business.pk)
        self.assertEqual(created['reviewer'], self.customer.pk)
        self.assertEqual(created['rating'], 5)
        self.assertEqual(created['description'], 'Excellent')

    def test_create_rejects_duplicate_active_review_and_invalid_fields(self):
        self.create_review()
        duplicate = self.client.post(
            '/api/reviews/',
            {'business_user': self.business.pk, 'rating': 4, 'description': 'Again'},
            format='json',
        )
        self.assertEqual(duplicate.status_code, 400)

        for rating, description in ((0, 'bad'), (6, 'bad'), (4, ''), (4, 'x' * 501)):
            with self.subTest(rating=rating, description_length=len(description)):
                self.client.force_authenticate(self.other_customer)
                invalid = self.client.post(
                    '/api/reviews/',
                    {
                        'business_user': self.business.pk,
                        'rating': rating,
                        'description': description,
                    },
                    format='json',
                )
                self.assertEqual(invalid.status_code, 400)

    def test_deleted_review_can_be_recreated_and_survives_order_deletion(self):
        review = self.create_review()
        self.client.force_authenticate(self.customer)
        deleted = self.client.delete(f"/api/reviews/{review['id']}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b'')

        recreated = self.create_review(description='Replacement review')
        self.assertNotEqual(recreated['id'], review['id'])
        Order.objects.all().delete()
        self.assertEqual(self.client.get('/api/reviews/').status_code, 200)

    def test_patch_and_delete_are_reviewer_only_and_patch_is_partial(self):
        review = self.create_review(rating=3, description='Initial')
        review_url = f"/api/reviews/{review['id']}/"

        self.client.force_authenticate(self.other_customer)
        self.assertEqual(self.client.patch(review_url, {'rating': 5}).status_code, 403)
        self.assertEqual(self.client.delete(review_url).status_code, 403)

        self.client.force_authenticate(self.customer)
        updated = self.client.patch(review_url, {'rating': 5}, format='json')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['rating'], 5)
        self.assertEqual(updated.data['description'], 'Initial')
        self.assertEqual(
            self.client.patch(review_url, {'business_user': self.other_business.pk}, format='json').status_code,
            400,
        )
        self.assertEqual(self.client.patch('/api/reviews/999999/', {'rating': 4}).status_code, 404)
        self.assertEqual(self.client.delete('/api/reviews/999999/').status_code, 404)

    def test_documented_internal_errors_return_safe_500_details(self):
        self.create_review()
        self.client.force_authenticate(self.customer)
        with patch(
            'marketplace_app.api.review_views.ReviewViewSet.filtered_reviews',
            side_effect=RuntimeError('sensitive review list failure'),
        ):
            list_response = self.client.get('/api/reviews/')
        self.assertEqual(list_response.status_code, 500)
        self.assertEqual(list_response.data, {'detail': 'Internal server error.'})

        self.create_completed_order(customer=self.other_customer)
        self.client.force_authenticate(self.other_customer)
        with patch(
            'marketplace_app.api.review_serializers.ReviewCreateSerializer.create',
            side_effect=RuntimeError('sensitive review create failure'),
        ):
            create_response = self.client.post(
                '/api/reviews/',
                {'business_user': self.business.pk, 'rating': 5, 'description': 'Excellent'},
                format='json',
            )
        self.assertEqual(create_response.status_code, 500)
        self.assertEqual(create_response.data, {'detail': 'Internal server error.'})
