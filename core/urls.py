from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='core_index'),
    path('robots.txt', views.robots_txt)
]