from django.urls import path
from . import views
from .excel_export import export_wellbeing_excel

app_name = 'wellbeing'

urlpatterns = [
    path('', views.wellbeing_list, name='wellbeing_list'),
    path('create/', views.wellbeing_create, name='wellbeing_create'),
    path('<int:pk>/', views.wellbeing_detail, name='wellbeing_detail'),
    path('<int:pk>/update/', views.wellbeing_update, name='wellbeing_update'),
    path('<int:pk>/delete/', views.wellbeing_delete, name='wellbeing_delete'),
    path('<int:wellbeing_pk>/recommendation/create/', views.recommendation_create, name='recommendation_create'),
    path('analytics/', views.wellbeing_analytics, name='wellbeing_analytics'),
    path('analytics/export/', export_wellbeing_excel, name='export_excel'),
    
]