# Standard library
from decimal import Decimal
from unittest.mock import PropertyMock, patch

# Third-party
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

# Local imports
from offers_app.models import Offer, OfferDetail
from orders_app.models import Order


User = get_user_model()

BASIC = OfferDetail.OfferType.BASIC
STANDARD = OfferDetail.OfferType.STANDARD
PREMIUM = OfferDetail.OfferType.PREMIUM

# (title, revisions, delivery_time_in_days, price, features, offer_type)
LOGO_SPECS = (
    ('Basic Logo', 3, 5, '150.00', ['Logo', 'Business card'], BASIC),
    ('Standard Logo', 5, 7, '250.00', ['Logo', 'Business card', 'Letterhead'], STANDARD),
    ('Premium Logo', 10, 10, '500.00', ['Logo', 'Business card', 'Letterhead', 'Flyer'], PREMIUM),
)
OWN_SPECS = (
    ('Own Basic', 1, 3, '25.00', [], BASIC),
    ('Own Standard', 2, 5, '50.00', [], STANDARD),
    ('Own Premium', 3, 7, '75.00', [], PREMIUM),
)
SAFE_500 = {'detail': 'Internal server error.'}


class OrderEndpointTests(TestCase):
    """Endpoint tests for the order API."""

    def setUp(self):
        """Prepare API client, users and a business offer with three details."""
        self.client = APIClient()
        self.create_users()
        self.offer = Offer.objects.create(user=self.business, title='Logo Design')
        self.detail, self.standard_detail, _ = self.create_offer_details(
            self.offer, LOGO_SPECS
        )

    def create_users(self):
        """Create the customer and business users used by the tests."""
        self.customer = self.create_user('orderCustomer', 'customer@example.com', 'customer')
        self.business = self.create_user('orderBusiness', 'business@example.com', 'business')
        self.other_customer = self.create_user('otherCustomer', 'other@example.com', 'customer')
        self.other_business = self.create_user('otherBusiness', 'otherbiz@example.com', 'business')

    def create_user(self, username, email, user_type):
        """Return a new user with the given username, email and type."""
        return User.objects.create_user(
            username=username, email=email, password='pass', type=user_type
        )

    def create_staff(self, username, email):
        """Return a new superuser with the given username and email."""
        return User.objects.create_superuser(
            username=username, email=email, password='pass', type='business'
        )

    def create_offer_details(self, offer, specs):
        """Create one OfferDetail per spec tuple and return them in order."""
        return [
            OfferDetail.objects.create(
                offer=offer, title=title, revisions=revisions,
                delivery_time_in_days=days, price=Decimal(price),
                features=features, offer_type=offer_type,
            )
            for title, revisions, days, price, features, offer_type in specs
        ]

    def post_order(self, detail_id):
        """POST an order for the given offer detail id and return the response."""
        return self.client.post('/api/orders/', {'offer_detail_id': detail_id}, format='json')

    def patch_status(self, order_id, status, **extra):
        """PATCH an order's status (plus optional extra fields) and return the response."""
        return self.client.patch(
            f'/api/orders/{order_id}/', {'status': status, **extra}, format='json'
        )

    def create_order(self, customer=None, detail=None):
        """Create an order as the given customer and return the response data."""
        self.client.force_authenticate(customer or self.customer)
        response = self.post_order((detail or self.detail).pk)
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def assert_business_list_has_three(self):
        """Assert the business sees all three orders addressed to it."""
        self.client.force_authenticate(self.business)
        business_response = self.client.get('/api/orders/')
        self.assertEqual(len(business_response.data), 3)
        self.assertTrue(all(item['business_user'] == self.business.pk for item in business_response.data))

    def assert_snapshot_fields(self, response_data):
        """Assert the created order data snapshots the basic offer detail."""
        self.assertEqual(response_data['customer_user'], self.customer.pk)
        self.assertEqual(response_data['business_user'], self.business.pk)
        self.assertEqual(response_data['title'], 'Basic Logo')
        self.assertEqual(response_data['price'], '150.00')
        self.assertEqual(response_data['features'], ['Logo', 'Business card'])
        self.assertEqual(response_data['status'], 'in_progress')

    def assert_listed_snapshot_unchanged(self):
        """Assert the customer's first listed order still has the original snapshot."""
        self.client.force_authenticate(self.customer)
        listed = self.client.get('/api/orders/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]['title'], 'Basic Logo')
        self.assertEqual(listed.data[0]['price'], '150.00')
        self.assertEqual(listed.data[0]['features'], ['Logo', 'Business card'])

    def assert_status_forbidden(self, order_id):
        """Assert the customer and an unrelated business cannot change the status."""
        for user in (self.customer, self.other_business):
            self.client.force_authenticate(user)
            self.assertEqual(self.patch_status(order_id, 'completed').status_code, 403)

    def assert_counts_for_customer(self):
        """Assert the customer sees one ongoing and one completed order for the business."""
        self.client.force_authenticate(self.customer)
        ongoing_count = self.client.get(f'/api/order-count/{self.business.pk}/')
        completed_count = self.client.get(f'/api/completed-order-count/{self.business.pk}/')
        self.assertEqual(ongoing_count.status_code, 200)
        self.assertEqual(ongoing_count.data, {'order_count': 1})
        self.assertEqual(completed_count.status_code, 200)
        self.assertEqual(completed_count.data, {'completed_order_count': 1})

    def assert_internal_error(self, user, patcher, method, url, **kwargs):
        """Perform a request under a failing patch and assert the safe 500 response."""
        self.client.force_authenticate(user)
        with patcher:
            response = getattr(self.client, method)(url, **kwargs)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, SAFE_500)

    def scenario_list(self):
        """Return the failing order-list scenario as (name, user, patcher, method, url, kwargs)."""
        patcher = patch(
            'orders_app.api.views.OrderViewSet.get_queryset',
            side_effect=RuntimeError('sensitive order list error'),
        )
        return [('list', self.customer, patcher, 'get', '/api/orders/', {})]

    def scenario_create(self):
        """Return the failing order-create scenario."""
        patcher = patch(
            'orders_app.api.serializers.OrderCreateSerializer.create',
            side_effect=RuntimeError('sensitive order create error'),
        )
        kwargs = {'data': {'offer_detail_id': self.detail.pk}, 'format': 'json'}
        return [('create', self.customer, patcher, 'post', '/api/orders/', kwargs)]

    def scenario_patch(self, order):
        """Return the failing order-status-update scenario for the given order."""
        patcher = patch(
            'orders_app.api.serializers.OrderReadSerializer.data',
            new_callable=PropertyMock,
            side_effect=RuntimeError('sensitive order response error'),
        )
        kwargs = {'data': {'status': 'completed'}, 'format': 'json'}
        return [('patch', self.business, patcher, 'patch', f"/api/orders/{order['id']}/", kwargs)]

    def scenario_delete(self, order):
        """Return the failing staff order-delete scenario for the given order."""
        staff = self.create_staff('errorStaff', 'error-staff@example.com')
        patcher = patch.object(Order, 'delete', side_effect=RuntimeError('sensitive delete error'))
        return [('delete', staff, patcher, 'delete', f"/api/orders/{order['id']}/", {})]

    def failing_filter(self, message):
        """Return a patch making Order.objects.filter raise RuntimeError(message)."""
        return patch(
            'orders_app.api.views.Order.objects.filter',
            side_effect=RuntimeError(message),
        )

    def scenario_counts(self):
        """Return the failing ongoing and completed order-count scenarios."""
        base = f'/{self.business.pk}/'
        return [
            ('count', self.customer, self.failing_filter('sensitive count error'),
             'get', '/api/order-count' + base, {}),
            ('completed count', self.customer,
             self.failing_filter('sensitive completed count error'),
             'get', '/api/completed-order-count' + base, {}),
        ]

    def test_list_requires_auth_and_returns_only_requesters_orders_newest_first(self):
        """Orders list only the requester's orders, newest first."""
        first = self.create_order()
        second = self.create_order(detail=self.standard_detail)
        self.create_order(customer=self.other_customer)

        self.client.force_authenticate(self.customer)
        response = self.client.get('/api/orders/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [second['id'], first['id']])
        self.assertTrue(all(item['customer_user'] == self.customer.pk for item in response.data))
        self.assert_business_list_has_three()

    def test_list_returns_401_without_authentication(self):
        """Listing orders anonymously returns 401."""
        response = self.client.get('/api/orders/')

        self.assertEqual(response.status_code, 401)

    def test_create_requires_customer_role_and_valid_detail(self):
        """Creating requires a customer, a body and an existing offer detail."""
        self.assertEqual(self.post_order(self.detail.pk).status_code, 401)
        self.client.force_authenticate(self.business)
        self.assertEqual(self.post_order(self.detail.pk).status_code, 403)

        self.client.force_authenticate(self.customer)
        missing_body = self.client.post('/api/orders/', {}, format='json')
        self.assertEqual(missing_body.status_code, 400)
        missing_detail = self.post_order(999999)
        self.assertEqual(missing_detail.status_code, 404)

    def test_customer_cannot_purchase_own_offer(self):
        """A customer ordering from their own offer gets 400 and no order is created."""
        own_offer = Offer.objects.create(user=self.customer, title='My own service')
        own_detail = self.create_offer_details(own_offer, OWN_SPECS)[0]
        self.client.force_authenticate(self.customer)

        response = self.post_order(own_detail.pk)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.filter(customer_user=self.customer).exists())

    def test_create_persists_snapshot_and_default_status(self):
        """Created orders snapshot the detail and survive later detail/offer changes."""
        self.assert_snapshot_fields(self.create_order())

        self.detail.title = 'Changed later'
        self.detail.price = Decimal('999.00')
        self.detail.features = ['Changed']
        self.detail.save()
        self.offer.delete()

        self.assert_listed_snapshot_unchanged()

    def test_order_snapshot_survives_offer_deletion(self):
        """Deleting the offer keeps the order snapshot and business user."""
        order_data = self.create_order()
        order = Order.objects.get(pk=order_data['id'])

        self.assertEqual(order.title, 'Basic Logo')
        self.offer.delete()

        order.refresh_from_db()
        self.assertEqual(order.title, 'Basic Logo')
        self.assertEqual(order.business_user_id, self.business.pk)

    def test_status_changes_only_by_assigned_business_with_allowed_transitions(self):
        """Only the assigned business may change status, with valid transitions and fields."""
        order = self.create_order()
        self.assert_status_forbidden(order['id'])

        self.client.force_authenticate(self.business)
        completed = self.patch_status(order['id'], 'completed')
        self.assertEqual(completed.status_code, 200, completed.data)
        self.assertEqual(completed.data['status'], 'completed')
        self.assertEqual(self.patch_status(order['id'], 'in_progress').status_code, 400)
        self.assertEqual(self.patch_status(order['id'], 'unknown').status_code, 400)
        fresh_order = self.create_order(detail=self.standard_detail)
        self.client.force_authenticate(self.business)
        extra_field = self.patch_status(fresh_order['id'], 'completed', price='1.00')
        self.assertEqual(extra_field.status_code, 400)

    def test_status_can_transition_to_cancelled_and_missing_order_is_404(self):
        """Status can become cancelled; unknown orders return 404."""
        order = self.create_order()
        self.client.force_authenticate(self.business)

        cancelled = self.patch_status(order['id'], 'cancelled')
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.data['status'], 'cancelled')
        missing = self.patch_status(999999, 'completed')
        self.assertEqual(missing.status_code, 404)

    def test_delete_is_staff_only_and_returns_204(self):
        """Only staff may delete an order; success returns an empty 204."""
        order = self.create_order()
        order_url = f"/api/orders/{order['id']}/"

        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.delete(order_url).status_code, 403)

        self.client.force_authenticate(self.create_staff('staffAdmin', 'staff@example.com'))
        deleted = self.client.delete(order_url)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b'')
        self.assertEqual(self.client.get(order_url).status_code, 405)

    def test_delete_requires_authentication_and_missing_order_is_404(self):
        """Deleting needs authentication and unknown orders return 404."""
        response = self.client.delete('/api/orders/999999/')
        self.assertEqual(response.status_code, 401)

        self.client.force_authenticate(self.create_staff('staffAgain', 'staff2@example.com'))
        self.assertEqual(self.client.delete('/api/orders/999999/').status_code, 404)

    def test_order_count_endpoints_are_authenticated_and_return_counts(self):
        """Count endpoints require authentication and return ongoing/completed counts."""
        ongoing = self.create_order()
        completed = self.create_order(detail=self.standard_detail)
        self.client.force_authenticate(self.business)
        self.patch_status(completed['id'], 'completed')
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(f'/api/order-count/{self.business.pk}/').status_code, 401
        )

        self.assert_counts_for_customer()
        self.assertNotEqual(ongoing['id'], completed['id'])

    def test_count_endpoints_return_404_for_missing_business(self):
        """Count endpoints return 404 for an unknown business user."""
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get('/api/order-count/999999/').status_code, 404)
        self.assertEqual(
            self.client.get('/api/completed-order-count/999999/').status_code, 404
        )

    def test_documented_internal_errors_return_safe_500_details(self):
        """Unexpected errors in every order endpoint return a safe 500 body."""
        order = self.create_order()
        scenarios = [
            *self.scenario_list(),
            *self.scenario_create(),
            *self.scenario_patch(order),
            *self.scenario_delete(order),
            *self.scenario_counts(),
        ]
        for name, user, patcher, method, url, kwargs in scenarios:
            with self.subTest(name):
                self.assert_internal_error(user, patcher, method, url, **kwargs)
