from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('<int:chat_with>/', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send_message'),
    path('fetch/', views.fetch_messages, name='fetch_messages'),
]
