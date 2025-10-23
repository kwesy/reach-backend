from django.urls import path
from oauth.views import DashboardView


app_name = 'oauth'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]