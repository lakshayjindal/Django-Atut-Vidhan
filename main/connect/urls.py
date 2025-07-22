from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('<int:chat_with>/', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send_message'),
    path('fetch/', views.fetch_messages, name='fetch_messages'),
    path('connections/', views.connections_page, name='connection'),
    path('connect/send/<int:receiver_id>/', views.send_request, name='send_request'),
    path('connect/accept/<int:request_id>/', views.accept_request, name='accept_request'),
    path('cancel-request/<int:request_id>/', views.cancel_request, name='cancel_request'),
]
