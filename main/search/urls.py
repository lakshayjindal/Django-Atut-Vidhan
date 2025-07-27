# search/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.search_page, name='search_page'),
    path('results/', views.search_results, name='search_results'),
]
