from django.urls import path, include

URL_PATTERNS = [
    path('search/', views.search, name='search'),
]