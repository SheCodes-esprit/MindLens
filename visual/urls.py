from django.urls import path
from .views import visual_list, visual_detail, visual_create,visual_delete

urlpatterns = [
    path('list/', visual_list, name='visual_list'),
    path('create/', visual_create, name='visual_create'),
    path('<int:pk>/', visual_detail, name='visual_detail'),
    path('delete/<int:pk>/',visual_delete, name='visual_delete'),
]