# Third-party
from django.urls import path

# Local imports
from profile_app.api.views import (
    BusinessProfileListView,
    CustomerProfileListView,
    ProfileDetailView,
)

app_name = 'profile_api'

urlpatterns = [
    path('profile/<int:pk>/', ProfileDetailView.as_view(), name='profile-detail'),
    path(
        'profiles/business/',
        BusinessProfileListView.as_view(),
        name='profile-collection-business',
    ),
    path(
        'profiles/customer/',
        CustomerProfileListView.as_view(),
        name='profile-collection-customer',
    ),
]
