from django.urls import include, path
from rest_framework.routers import SimpleRouter

from orders_app.api.views import (
	CompletedOrderCountView,
	OrderCountView,
	OrderViewSet,
)

app_name = 'orders_api'

router = SimpleRouter()
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
	path('', include(router.urls))
]
