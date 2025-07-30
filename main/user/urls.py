from django.urls import path, include
from . import views

urlpatterns = [
    # path('login', views.entry_user, name='homepage'),
    # path('auth/', include('user.urls')),
    path('', views.login_user, name='login'),
    path('signup', views.signup_user, name='signup'),
    path('complete', views.complete_user, name="complete_profile"),
    path('logout', views.logout_user, name='logout'),
    path('profile/', views.view_profile, name='view_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('search/', views.search_view, name="search"),
    path('profile/<int:profile_id>/', views.profile_detail, name='profile_detail'),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("reset/<uidb64>/<token>/", views.reset_password_view, name="reset_password"),
]
