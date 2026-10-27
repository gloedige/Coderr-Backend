from django.urls import path

from core.api.base_info_views import BaseInfoView

app_name = 'core_api'

urlpatterns = [path('base-info/', BaseInfoView.as_view(), name='base-info')]
