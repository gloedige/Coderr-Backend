from django.urls import include, path
from rest_framework.routers import SimpleRouter

from accounts_app.api.profile_views import ProfileCollectionViewSet, ProfileDetailViewSet
from accounts_app.api.views import LoginView, RegistrationView

app_name = 'accounts_api'

profile_router = SimpleRouter()
profile_router.register(
	'profiles', ProfileCollectionViewSet, basename='profile-collection'
)

urlpatterns = [
	path('registration/', RegistrationView.as_view(), name='registration'),
	path('login/', LoginView.as_view(), name='login'),
	path(
		'profile/<int:pk>/',
		ProfileDetailViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}),
		name='profile-detail',
	),
	path('', include(profile_router.urls)),
]
