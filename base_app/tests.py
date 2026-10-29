from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from profile_app.models import Profile
from offers_app.models import Offer
from reviews_app.models import Review



User = get_user_model()


class BaseInfoEndpointTests(TestCase):
    """Test the public aggregate information endpoint contract."""

    def setUp(self):
        """Create an API client and a business with its profile."""
        self.client = APIClient()
        self.business = self.create_user('business', 'business@example.com', 'business')
        Profile.objects.create(user=self.business)

    def create_user(self, username, email, user_type):
        """Create a user with the requested API role."""
        return User.objects.create_user(
            username=username, email=email, password='pass', type=user_type
        )

    def test_base_info_is_public_and_returns_zero_average_without_reviews(self):
        """Return public counts and numeric zero average when no reviews exist."""
        response = self.client.get('/api/base-info/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'review_count': 0,
            'average_rating': 0.0,
            'business_profile_count': 2,
            'offer_count': 0,
        })

    def test_base_info_aggregates_counts_and_rounds_average(self):
        """Count businesses, offers and reviews while rounding rating to one decimal."""
        self.create_aggregate_fixtures()

        response = self.client.get('/api/base-info/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'review_count': 3,
            'average_rating': 4.3,
            'business_profile_count': 3,
            'offer_count': 2,
        })

    def create_aggregate_fixtures(self):
        """Create a second business, two offers and reviews averaging 4.33."""
        second_business = self.create_user('business2', 'business2@example.com', 'business')
        Profile.objects.create(user=second_business)
        Offer.objects.create(user=self.business, title='First offer')
        Offer.objects.create(user=second_business, title='Second offer')
        self.create_reviews_with_unique_customers()

    def create_reviews_with_unique_customers(self):
        """Create three valid reviews to produce a 4.33 average."""
        for number, rating in enumerate((4, 4, 5)):
            customer = self.create_user(
                f'customer{number}', f'customer{number}@example.com', 'customer'
            )
            Review.objects.create(
                business_user=self.business,
                reviewer=customer,
                rating=rating,
                description='Service review',
            )

    def test_base_info_hides_unexpected_internal_errors(self):
        """Return a generic 500 response without exposing aggregate failure details."""
        with patch(
            'base_app.api.views.base_info_data',
            side_effect=RuntimeError('sensitive aggregate failure'),
        ):
            response = self.client.get('/api/base-info/')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {'detail': 'Internal server error.'})
