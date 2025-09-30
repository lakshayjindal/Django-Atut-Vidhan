# plans/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Public / User views
    path('', views.plans_list, name='plans_list'),
    path('payment/<int:plan_id>/', views.make_payment, name='make_payment'),
    path('my-subscription/', views.my_subscription, name='my_subscription'),

    # Admin / Staff views
    path('verify-payment/<int:payment_id>/<str:action>/', views.verify_payment, name='verify_payment'),
]
