from django.urls import path
from superadmin.views import LoginView


app_name = 'superadmin'

urlpatterns = [
    path('login/', LoginView.as_view(), name='admin-login'),

]