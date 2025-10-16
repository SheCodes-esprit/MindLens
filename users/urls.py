# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('signin/', views.signin_view, name='signin'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('admin/dashboard/', views.admin_dashboard_view, name='dashboard'),
    path('journalist/dashboard/', views.journalist_dashboard_view, name='journalist_dashboard'),
    path('profile/', views.profile_view, name='profile'),

    path('profile/delete/', views.delete_account_view, name='delete_account'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),

    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password_view, name='reset_password'),
    path('admin/users/', views.list_users_view, name='list_users'),
    path('admin/users/add/', views.add_user_view, name='add_user'),
    path('admin/users/delete/<int:user_id>/', views.delete_user_view, name='delete_user'),
    path('admin/users/edit/<int:user_id>/', views.edit_user_view, name='edit_user'),

    path('enable-2fa/', views.enable_2fa_view, name='enable_2fa'),
    path('verify-2fa-setup/', views.verify_2fa_setup, name='verify_2fa_setup'),
    path('disable-2fa/', views.disable_2fa_view, name='disable_2fa'),
    path('verify-2fa-login/', views.verify_2fa_login, name='verify_2fa_login'),
]