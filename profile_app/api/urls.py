from django.urls import include, path
from rest_framework.routers import SimpleRouter

from profile_app.api.views import ProfileCollectionViewSet, ProfileDetailViewSet

app_name = 'profile_api'

profile_router = SimpleRouter()
profile_router.register(
	'profiles', ProfileCollectionViewSet, basename='profile-collection'
)

urlpatterns = [
	path(
		'profile/<int:pk>/',
		ProfileDetailViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}),
		name='profile-detail',
	),
	path('', include(profile_router.urls)),
]