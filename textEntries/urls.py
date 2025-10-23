from django.urls import path
from . import views

urlpatterns = [
    path('', views.entry_list, name='entry_list'),
    path('add/', views.add_entry, name='add_entry'),
    path('update/<int:entry_id>/', views.update_entry, name='update_entry'),
    path('delete/<int:entry_id>/', views.delete_entry, name='delete_entry'),
    path('detail/<int:entry_id>/', views.entry_detail, name='entry_detail'),

]
