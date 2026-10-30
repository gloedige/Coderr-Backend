# Third-party
from django.urls import include, path
from rest_framework.routers import SimpleRouter

# Local imports
from reviews_app.api.views import ReviewViewSet

app_name = 'reviews_api'

router = SimpleRouter()
router.register('reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls))
]