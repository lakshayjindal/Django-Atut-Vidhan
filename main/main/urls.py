"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http.response import HttpResponse
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings
from django.http import HttpResponseNotFound
from django.urls import path, re_path


def healthcheck(request):
    return HttpResponse('OK', status=200)


urlpatterns = [
                  path('health/', healthcheck),
                  path('siteadmin/', admin.site.urls, name='siteadmin'),
                  path('', views.entry_user, name='homepage'),
                  path('customMadeAdmin/', include('siteadmin.urls')),
                  path('auth/', include('user.urls')),
                  path('user_dashboard', views.redirect_user_dashboard, name="user_dashboard"),
                  path('chat/', include("connect.urls")),
                  path('plans/', include("plans.urls")),
                  path('search/', include("search.urls")),
                  path('privacy/', views.privacy, name='privacy_policy'),
                  path('terms/', views.terms, name='terms_conditions'),
                  path('about/', views.about, name='about'),
                  path('contact/', views.contact, name='contact'),
                  path('faq/', views.faq, name='help'),
                  # re_path(r'.*/auth/.*', views.auth_fallback),
                  # re_path(r'^.*$', views.custom_404_view),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
