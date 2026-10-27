from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from marketplace_app.models import Offer, OfferDetail, Order, Review


User = get_user_model()


class ReviewEndpointTests(TestCase):
    def setUp(self):
        """Prepare review API client and customer/business fixtures for each test."""
        self.client = APIClient()
        self.create_test_users()
        self.detail = self.create_completed_order()

    def create_test_users(self):
        """Create the two customer and two business users used in authorization tests."""
        self.customer = self.create_user('reviewCustomer', 'customer@example.com', 'customer')
        self.other_customer = self.create_user('otherCustomer', 'other@example.com', 'customer')
        self.business = self.create_user('reviewBusiness', 'business@example.com', 'business')
        self.other_business = self.create_user('otherBusiness', 'otherbiz@example.com', 'business')

    def create_user(self, username, email, user_type):
        """Create a user with the requested username, email, and role."""
        return User.objects.create_user(
            username=username,
            email=email,
            password='pass',
            type=user_type,
        )

    def create_completed_order(self, customer=None, business=None, status=Order.Status.COMPLETED):
        """Create an offer with all three tiers and an order snapshot for its basic tier."""
        customer = customer or self.customer
        business = business or self.business
        offer = Offer.objects.create(user=business, title='Reviewed service')
        details = self.create_offer_details(offer)
        detail = details[OfferDetail.OfferType.BASIC]
        self.create_order_snapshot(customer, business, detail, status)
        return detail

    def create_offer_details(self, offer):
        """Create and return exactly one database detail for each offer tier."""
        return {
            offer_type: self.create_offer_detail(offer, offer_type, detail_values)
            for offer_type, detail_values in self.offer_detail_specs()
        }

    def offer_detail_specs(self):
        """Return title, revision, delivery, and price fixtures for all three tiers."""
        return (
            (OfferDetail.OfferType.BASIC, ('Basic package', 2, 5, '99.00')),
            (OfferDetail.OfferType.STANDARD, ('Standard package', 5, 7, '199.00')),
            (OfferDetail.OfferType.PREMIUM, ('Premium package', 10, 10, '299.00')),
        )

    def create_offer_detail(self, offer, offer_type, values):
        """Create one offer detail using its tier-specific fixture values."""
        title, revisions, delivery, price = values
        return OfferDetail.objects.create(
            offer=offer, title=title, revisions=revisions,
            delivery_time_in_days=delivery, price=Decimal(price),
            features=['delivery'], offer_type=offer_type,
        )

    def create_order_snapshot(self, customer, business, detail, status):
        """Create a review-eligibility order snapshot from the basic detail."""
        return Order.objects.create(
            customer_user=customer, business_user=business, title=detail.title,
            revisions=detail.revisions, delivery_time_in_days=detail.delivery_time_in_days,
            price=detail.price, features=detail.features, offer_type=detail.offer_type,
            status=status,
        )

    def test_completed_order_offer_fixture_has_all_three_detail_tiers(self):
        """Ensure review fixtures keep the offer's three-tier invariant."""
        offer = self.detail.offer

        self.assertEqual(offer.details.count(), 3)
        self.assertEqual(
            set(offer.details.values_list('offer_type', flat=True)),
            {'basic', 'standard', 'premium'},
        )

    def create_review(self, customer=None, business=None, rating=4, description='Great service'):
        """Create a review through the public HTTP endpoint and return its response data."""
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

    def create_two_reviews(self):
        """Create two eligible reviews with different ratings for list sorting tests."""
        self.create_completed_order(customer=self.other_customer)
        first = self.create_review(rating=3, description='First')
        second = self.create_review(customer=self.other_customer, rating=5, description='Second')
        return first, second

    def assert_review_list_sorted(self, response, first, second):
        """Assert business filter results are ordered by descending rating."""
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [second['id'], first['id']])
        self.assertTrue(all(item['business_user'] == self.business.pk for item in response.data))

    def assert_reviewer_filter(self, review):
        """Assert reviewer filtering returns the requested author's review only."""
        response = self.client.get(f'/api/reviews/?reviewer_id={self.customer.pk}')
        self.assertEqual([item['id'] for item in response.data], [review['id']])

    def test_list_requires_auth_and_supports_filters_and_ordering(self):
        """Allow authenticated listing with business/reviewer filters and rating ordering."""
        first, second = self.create_two_reviews()
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/reviews/').status_code, 401)
        self.client.force_authenticate(self.business)
        response = self.client.get(
            f'/api/reviews/?business_user_id={self.business.pk}&ordering=-rating'
        )
        self.assert_review_list_sorted(response, first, second)
        self.assert_reviewer_filter(first)

    def test_list_rejects_invalid_and_unknown_query_parameters(self):
        """Reject malformed IDs, unsupported ordering, and undocumented filters."""
        self.client.force_authenticate(self.customer)

        for query in ('?business_user_id=nope', '?ordering=created_at', '?unknown=1'):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f'/api/reviews/{query}').status_code, 400)

    def test_create_requires_authentication_and_customer_role(self):
        """Require authentication and a customer account before review creation."""
        payload = {'business_user': self.business.pk, 'rating': 4, 'description': 'Good'}
        self.assertEqual(self.client.post('/api/reviews/', payload, format='json').status_code, 401)
        self.client.force_authenticate(self.other_business)
        self.assertEqual(self.client.post('/api/reviews/', payload, format='json').status_code, 403)

    def test_create_requires_completed_order_with_same_business(self):
        """Reject reviews without a completed order connecting the customer and business."""
        self.client.force_authenticate(self.other_customer)
        no_order = self.client.post(
            '/api/reviews/',
            {'business_user': self.other_business.pk, 'rating': 4, 'description': 'Good'},
            format='json',
        )
        self.assertEqual(no_order.status_code, 400)
        self.create_completed_order(
            customer=self.other_customer,
            business=self.other_business,
            status=Order.Status.IN_PROGRESS,
        )
        self.assert_uncompleted_order_cannot_be_reviewed()

    def assert_uncompleted_order_cannot_be_reviewed(self):
        """Assert an in-progress order does not grant review eligibility."""
        response = self.client.post(
            '/api/reviews/',
            {'business_user': self.other_business.pk, 'rating': 4, 'description': 'Good'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_create_requires_matching_completed_order_and_returns_review(self):
        """Only permit creating a review for the business on a matching completed order."""
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

    def test_create_rejects_duplicate_active_review(self):
        """Reject a second active review for the same customer-business pair."""
        self.create_review()
        self.create_completed_order(customer=self.other_customer)
        duplicate = self.client.post(
            '/api/reviews/',
            {'business_user': self.business.pk, 'rating': 4, 'description': 'Again'},
            format='json',
        )
        self.assertEqual(duplicate.status_code, 400)

    def test_database_constraint_rejects_out_of_range_ratings(self):
        """Ensure direct bulk inserts cannot persist ratings outside the 1–5 range."""
        for rating in (0, 6):
            with self.subTest(rating=rating):
                self.assert_database_rejects_rating(rating)

    def assert_database_rejects_rating(self, rating):
        """Attempt a direct bulk insert and assert the database check rejects its rating."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.bulk_create([
                Review(
                    business_user=self.business,
                    reviewer=self.customer,
                    rating=rating,
                    description='Direct database test',
                )
            ])

    def test_create_rejects_rating_and_description_out_of_range(self):
        """Reject ratings outside one to five and descriptions outside 1-500 characters."""
        self.assert_invalid_review_fields()

    def assert_invalid_review_fields(self):
        """Exercise invalid rating and description examples through the public endpoint."""
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
        """Allow recreation after review deletion and retain reviews after order deletion."""
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
        """Restrict mutations to the review author and permit partial editable-field updates."""
        review = self.create_review(rating=3, description='Initial')
        review_url = f"/api/reviews/{review['id']}/"
        self.assert_non_owner_cannot_mutate(review_url)
        self.assert_owner_can_patch_rating(review_url)
        self.assert_review_identity_is_immutable(review_url)

    def assert_non_owner_cannot_mutate(self, review_url):
        """Assert another customer cannot PATCH or DELETE the review."""
        self.client.force_authenticate(self.other_customer)
        self.assertEqual(self.client.patch(review_url, {'rating': 5}).status_code, 403)
        self.assertEqual(self.client.delete(review_url).status_code, 403)

    def assert_owner_can_patch_rating(self, review_url):
        """Assert owner PATCH updates rating and retains omitted description."""
        self.client.force_authenticate(self.customer)
        updated = self.client.patch(review_url, {'rating': 5}, format='json')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['rating'], 5)
        self.assertEqual(updated.data['description'], 'Initial')

    def assert_review_identity_is_immutable(self, review_url):
        """Reject changing the review target and return 404 for absent reviews."""
        forbidden = self.client.patch(
            review_url, {'business_user': self.other_business.pk}, format='json'
        )
        self.assertEqual(forbidden.status_code, 400)
        self.assertEqual(self.client.patch('/api/reviews/999999/', {'rating': 4}).status_code, 404)
        self.assertEqual(self.client.delete('/api/reviews/999999/').status_code, 404)

    def test_documented_internal_errors_return_safe_500_details(self):
        """Ensure unexpected list failure returns the documented safe error response."""
        self.create_review()
        self.client.force_authenticate(self.customer)
        with patch(
            'marketplace_app.api.review_views.ReviewViewSet.filtered_reviews',
            side_effect=RuntimeError('sensitive review list failure'),
        ):
            list_response = self.client.get('/api/reviews/')
        self.assertEqual(list_response.status_code, 500)
        self.assertEqual(list_response.data, {'detail': 'Internal server error.'})

    def test_review_create_internal_error_returns_safe_500_detail(self):
        """Ensure unexpected review persistence failure never exposes exception details."""
        self.assert_review_create_internal_error()

    def assert_review_create_internal_error(self):
        """Simulate create failure after validation and assert the generic 500 response."""
        self.create_completed_order(customer=self.other_customer)
        self.client.force_authenticate(self.other_customer)
        response = self.post_review_with_internal_failure()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {'detail': 'Internal server error.'})

    def post_review_with_internal_failure(self):
        """POST a valid review while substituting a controlled persistence exception."""
        with patch(
            'marketplace_app.api.review_serializers.ReviewCreateSerializer.create',
            side_effect=RuntimeError('sensitive review create failure'),
        ):
            return self.client.post(
                '/api/reviews/',
                {'business_user': self.business.pk, 'rating': 5, 'description': 'Excellent'},
                format='json',
            )
