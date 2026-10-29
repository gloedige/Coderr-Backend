from django.urls import path

from auth_app.api.views import LoginView, RegistrationView

app_name = 'auth_api'

urlpatterns = [
	path('registration/', RegistrationView.as_view(), name='registration'),
	path('login/', LoginView.as_view(), name='login'),
]