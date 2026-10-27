from decimal import Decimal
from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from marketplace_app.models import Offer, OfferDetail, Order


User = get_user_model()


class OrderEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = self.create_user('orderCustomer', 'customer@example.com', 'customer')
        self.business = self.create_user('orderBusiness', 'business@example.com', 'business')
        self.other_customer = self.create_user('otherCustomer', 'other@example.com', 'customer')
        self.other_business = self.create_user('otherBusiness', 'otherbiz@example.com', 'business')
        self.offer = Offer.objects.create(user=self.business, title='Logo Design')
        self.detail = OfferDetail.objects.create(
            offer=self.offer,
            title='Basic Logo',
            revisions=3,
            delivery_time_in_days=5,
            price=Decimal('150.00'),
            features=['Logo', 'Business card'],
            offer_type=OfferDetail.OfferType.BASIC,
        )
        self.standard_detail = OfferDetail.objects.create(
            offer=self.offer,
            title='Standard Logo',
            revisions=5,
            delivery_time_in_days=7,
            price=Decimal('250.00'),
            features=['Logo', 'Business card', 'Letterhead'],
            offer_type=OfferDetail.OfferType.STANDARD,
        )
        OfferDetail.objects.create(
            offer=self.offer,
            title='Premium Logo',
            revisions=10,
            delivery_time_in_days=10,
            price=Decimal('500.00'),
            features=['Logo', 'Business card', 'Letterhead', 'Flyer'],
            offer_type=OfferDetail.OfferType.PREMIUM,
        )

    def create_user(self, username, email, user_type):
        return User.objects.create_user(
            username=username, email=email, password='pass', type=user_type
        )

    def create_order(self, customer=None, detail=None):
        self.client.force_authenticate(customer or self.customer)
        response = self.client.post(
            '/api/orders/',
            {'offer_detail_id': (detail or self.detail).pk},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_list_requires_auth_and_returns_only_requesters_orders_newest_first(self):
        first = self.create_order()
        second = self.create_order(detail=self.standard_detail)
        self.create_order(customer=self.other_customer)

        self.client.force_authenticate(self.customer)
        response = self.client.get('/api/orders/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [second['id'], first['id']])
        self.assertTrue(all(item['customer_user'] == self.customer.pk for item in response.data))

        self.client.force_authenticate(self.business)
        business_response = self.client.get('/api/orders/')
        self.assertEqual(len(business_response.data), 3)
        self.assertTrue(all(item['business_user'] == self.business.pk for item in business_response.data))

    def test_list_returns_401_without_authentication(self):
        response = self.client.get('/api/orders/')

        self.assertEqual(response.status_code, 401)

    def test_create_requires_customer_role_and_valid_detail(self):
        self.assertEqual(
            self.client.post('/api/orders/', {'offer_detail_id': self.detail.pk}, format='json').status_code,
            401,
        )
        self.client.force_authenticate(self.business)
        self.assertEqual(
            self.client.post('/api/orders/', {'offer_detail_id': self.detail.pk}, format='json').status_code,
            403,
        )

        self.client.force_authenticate(self.customer)
        missing_body = self.client.post('/api/orders/', {}, format='json')
        self.assertEqual(missing_body.status_code, 400)
        missing_detail = self.client.post(
            '/api/orders/', {'offer_detail_id': 999999}, format='json'
        )
        self.assertEqual(missing_detail.status_code, 404)

    def test_customer_cannot_purchase_own_offer(self):
        own_offer = Offer.objects.create(user=self.customer, title='My own service')
        own_detail = OfferDetail.objects.create(
            offer=own_offer,
            title='Own Basic',
            revisions=1,
            delivery_time_in_days=3,
            price=Decimal('25.00'),
            features=[],
            offer_type=OfferDetail.OfferType.BASIC,
        )
        OfferDetail.objects.create(
            offer=own_offer,
            title='Own Standard',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('50.00'),
            features=[],
            offer_type=OfferDetail.OfferType.STANDARD,
        )
        OfferDetail.objects.create(
            offer=own_offer,
            title='Own Premium',
            revisions=3,
            delivery_time_in_days=7,
            price=Decimal('75.00'),
            features=[],
            offer_type=OfferDetail.OfferType.PREMIUM,
        )
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            '/api/orders/', {'offer_detail_id': own_detail.pk}, format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.filter(customer_user=self.customer).exists())

    def test_create_persists_snapshot_and_default_status(self):
        response_data = self.create_order()

        self.assertEqual(response_data['customer_user'], self.customer.pk)
        self.assertEqual(response_data['business_user'], self.business.pk)
        self.assertEqual(response_data['title'], 'Basic Logo')
        self.assertEqual(response_data['price'], '150.00')
        self.assertEqual(response_data['features'], ['Logo', 'Business card'])
        self.assertEqual(response_data['status'], 'in_progress')

        self.detail.title = 'Changed later'
        self.detail.price = Decimal('999.00')
        self.detail.features = ['Changed']
        self.detail.save()
        self.offer.delete()

        self.client.force_authenticate(self.customer)
        listed = self.client.get('/api/orders/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]['title'], 'Basic Logo')
        self.assertEqual(listed.data[0]['price'], '150.00')
        self.assertEqual(listed.data[0]['features'], ['Logo', 'Business card'])

    def test_order_snapshot_survives_offer_deletion(self):
        order_data = self.create_order()
        order = Order.objects.get(pk=order_data['id'])

        self.assertEqual(order.title, 'Basic Logo')
        self.offer.delete()

        order.refresh_from_db()
        self.assertEqual(order.title, 'Basic Logo')
        self.assertEqual(order.business_user_id, self.business.pk)

    def test_status_changes_only_by_assigned_business_with_allowed_transitions(self):
        order = self.create_order()
        order_url = f"/api/orders/{order['id']}/"

        self.client.force_authenticate(self.customer)
        forbidden = self.client.patch(order_url, {'status': 'completed'}, format='json')
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_authenticate(self.other_business)
        forbidden_other = self.client.patch(order_url, {'status': 'completed'}, format='json')
        self.assertEqual(forbidden_other.status_code, 403)

        self.client.force_authenticate(self.business)
        completed = self.client.patch(order_url, {'status': 'completed'}, format='json')
        self.assertEqual(completed.status_code, 200, completed.data)
        self.assertEqual(completed.data['status'], 'completed')
        terminal_transition = self.client.patch(
            order_url, {'status': 'in_progress'}, format='json'
        )
        self.assertEqual(terminal_transition.status_code, 400)
        invalid_status = self.client.patch(order_url, {'status': 'unknown'}, format='json')
        self.assertEqual(invalid_status.status_code, 400)
        extra_field = self.client.patch(
            order_url, {'status': 'completed', 'price': '1.00'}, format='json'
        )
        self.assertEqual(extra_field.status_code, 400)

    def test_status_can_transition_to_cancelled_and_missing_order_is_404(self):
        order = self.create_order()
        self.client.force_authenticate(self.business)

        cancelled = self.client.patch(
            f"/api/orders/{order['id']}/", {'status': 'cancelled'}, format='json'
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.data['status'], 'cancelled')
        missing = self.client.patch('/api/orders/999999/', {'status': 'completed'}, format='json')
        self.assertEqual(missing.status_code, 404)

    def test_delete_is_staff_only_and_returns_204(self):
        order = self.create_order()
        order_url = f"/api/orders/{order['id']}/"

        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.delete(order_url).status_code, 403)

        staff = User.objects.create_superuser(
            username='staffAdmin', email='staff@example.com', password='pass', type='business'
        )
        self.client.force_authenticate(staff)
        deleted = self.client.delete(order_url)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b'')
        self.assertEqual(self.client.get(order_url).status_code, 405)

    def test_delete_requires_authentication_and_missing_order_is_404(self):
        response = self.client.delete('/api/orders/999999/')
        self.assertEqual(response.status_code, 401)

        staff = User.objects.create_superuser(
            username='staffAgain', email='staff2@example.com', password='pass', type='business'
        )
        self.client.force_authenticate(staff)
        self.assertEqual(self.client.delete('/api/orders/999999/').status_code, 404)

    def test_order_count_endpoints_are_authenticated_and_return_counts(self):
        ongoing = self.create_order()
        completed = self.create_order(detail=self.standard_detail)
        self.client.force_authenticate(self.business)
        self.client.patch(f"/api/orders/{completed['id']}/", {'status': 'completed'}, format='json')
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(f'/api/order-count/{self.business.pk}/').status_code, 401
        )

        self.client.force_authenticate(self.customer)
        ongoing_count = self.client.get(f'/api/order-count/{self.business.pk}/')
        completed_count = self.client.get(f'/api/completed-order-count/{self.business.pk}/')
        self.assertEqual(ongoing_count.status_code, 200)
        self.assertEqual(ongoing_count.data, {'order_count': 1})
        self.assertEqual(completed_count.status_code, 200)
        self.assertEqual(completed_count.data, {'completed_order_count': 1})
        self.assertNotEqual(ongoing['id'], completed['id'])

    def test_count_endpoints_return_404_for_missing_business(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get('/api/order-count/999999/').status_code, 404)
        self.assertEqual(
            self.client.get('/api/completed-order-count/999999/').status_code, 404
        )

    def test_documented_internal_errors_return_safe_500_details(self):
        order = self.create_order()
        self.client.force_authenticate(self.customer)

        with patch(
            'marketplace_app.api.order_views.OrderViewSet.get_queryset',
            side_effect=RuntimeError('sensitive order list error'),
        ):
            list_response = self.client.get('/api/orders/')
        self.assertEqual(list_response.status_code, 500)
        self.assertEqual(list_response.data, {'detail': 'Internal server error.'})

        with patch(
            'marketplace_app.api.order_serializers.OrderCreateSerializer.create',
            side_effect=RuntimeError('sensitive order create error'),
        ):
            create_response = self.client.post(
                '/api/orders/', {'offer_detail_id': self.detail.pk}, format='json'
            )
        self.assertEqual(create_response.status_code, 500)
        self.assertEqual(create_response.data, {'detail': 'Internal server error.'})

        self.client.force_authenticate(self.business)
        with patch(
            'marketplace_app.api.order_serializers.OrderReadSerializer.data',
            new_callable=PropertyMock,
            side_effect=RuntimeError('sensitive order response error'),
        ):
            patch_response = self.client.patch(
                f"/api/orders/{order['id']}/", {'status': 'completed'}, format='json'
            )
        self.assertEqual(patch_response.status_code, 500)
        self.assertEqual(patch_response.data, {'detail': 'Internal server error.'})

        staff = User.objects.create_superuser(
            username='errorStaff',
            email='error-staff@example.com',
            password='pass',
            type='business',
        )
        self.client.force_authenticate(staff)
        with patch.object(Order, 'delete', side_effect=RuntimeError('sensitive delete error')):
            delete_response = self.client.delete(f"/api/orders/{order['id']}/")
        self.assertEqual(delete_response.status_code, 500)
        self.assertEqual(delete_response.data, {'detail': 'Internal server error.'})

        self.client.force_authenticate(self.customer)
        with patch(
            'marketplace_app.api.order_views.Order.objects.filter',
            side_effect=RuntimeError('sensitive count error'),
        ):
            count_response = self.client.get(f'/api/order-count/{self.business.pk}/')
        self.assertEqual(count_response.status_code, 500)
        self.assertEqual(count_response.data, {'detail': 'Internal server error.'})

        with patch(
            'marketplace_app.api.order_views.Order.objects.filter',
            side_effect=RuntimeError('sensitive completed count error'),
        ):
            completed_count_response = self.client.get(
                f'/api/completed-order-count/{self.business.pk}/'
            )
        self.assertEqual(completed_count_response.status_code, 500)
        self.assertEqual(
            completed_count_response.data,
            {'detail': 'Internal server error.'},
        )
