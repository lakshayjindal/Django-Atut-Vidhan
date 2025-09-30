from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("", views.login_user, name="login"),
    path("signup/", views.signup_user, name="signup"),
    path("logout/", views.logout_user, name="logout"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("magic-login/<uidb64>/<token>/", views.magic_login, name="magic_login"),

    # Password reset
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("reset/<uidb64>/<token>/", views.reset_password_view, name="reset_password"),

    # Profile
    path("complete/", views.complete_user, name="complete_profile"),
    path("profile/", views.view_profile, name="view_profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<int:profile_id>/", views.profile_detail, name="profile_detail"),

    path("profile/delete/picture/<int:picture_id>/", views.delete_picture, name="delete-picture"),
    # Search
    path("search/", views.search_view, name="search"),
]
