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


]