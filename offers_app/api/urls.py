from django.urls import include, path
from rest_framework.routers import SimpleRouter

from offers_app.api.views import OfferDetailView, OfferViewSet

app_name = 'offers_api'

router = SimpleRouter()
router.register('offers', OfferViewSet, basename='offer')

urlpatterns = [
	path('', include(router.urls)),
	path(
		'offerdetails/<int:pk>/',
		OfferDetailView.as_view(),
		name='offerdetail-detail',
	),
]
