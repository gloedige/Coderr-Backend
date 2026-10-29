from django.urls import path

from base_app.api.views import BaseInfoView

app_name = 'base_api'

urlpatterns = [path('base-info/', BaseInfoView.as_view(), name='base-info')]
