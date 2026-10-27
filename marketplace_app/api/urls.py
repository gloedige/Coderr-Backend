from django.urls import include, path
from rest_framework.routers import SimpleRouter

from marketplace_app.api.order_views import (
	CompletedOrderCountView,
	OrderCountView,
	OrderViewSet,
)
from marketplace_app.api.offer_views import OfferDetailViewSet, OfferViewSet

app_name = 'marketplace_api'

router = SimpleRouter()
router.register('offers', OfferViewSet, basename='offer')
router.register('orders', OrderViewSet, basename='order')

urlpatterns = [
	path(
		'order-count/<int:business_user_id>/',
		OrderCountView.as_view(),
		name='order-count',
	),
	path(
		'completed-order-count/<int:business_user_id>/',
		CompletedOrderCountView.as_view(),
		name='completed-order-count',
	),
	path('', include(router.urls)),
	path(
		'offerdetails/<int:pk>/',
		OfferDetailViewSet.as_view({'get': 'retrieve'}),
		name='offerdetail-detail',
	),
]
