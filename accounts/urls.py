# accounts/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    # Dashboard (home)
    path('', views.dashboard_view, name='dashboard'),

    # Auth views
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Password reset
    path('password_reset/', views.send_reset_code, name='password_reset'),

    # Route for confirming the password reset code and setting the new password (step 2)
    path('password_reset_confirm/', views.password_reset_confirm, name='password_reset_confirm'),

    # Profile page
    path("account/profile/", views.profile_view, name="profile"),

    # VTU Services Hub
    path('services/', views.vtu_services_view, name='vtu_services'),
]
