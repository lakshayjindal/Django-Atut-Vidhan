from django.urls import path, include
from . import views
urlpatterns = [
    path('', views.premium_plans, name='premium_plans'),
    path("subscribe_plan/<int:plan_id>", views.subscribe_plan, name='subscribe_plan'),
]