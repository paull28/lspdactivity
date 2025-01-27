
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'), #Homepage
    path('refresh', views.refresh, name='refresh'), #refresh data
]
