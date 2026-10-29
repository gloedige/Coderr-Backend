from django.urls import include, path
from rest_framework.routers import SimpleRouter

from offers_app.api.views import OfferDetailViewSet, OfferViewSet

app_name = 'offers_api'

router = SimpleRouter()
router.register('offers', OfferViewSet, basename='offer')

urlpatterns = [
	path('', include(router.urls)),
	path(
		'offerdetails/<int:pk>/',
		OfferDetailViewSet.as_view({'get': 'retrieve'}),
		name='offerdetail-detail',
	),
]
