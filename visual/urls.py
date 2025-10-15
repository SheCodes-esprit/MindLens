# visual/urls.py
from django.urls import path
from .views import (
    visual_list, visual_detail, visual_create, visual_delete,
    stats_page, api_posts_trend, api_emotions_distribution, api_top_objects , stats_page, api_posts_trend, api_emotions_distribution , api_posts_trend_weekly
)

urlpatterns = [
    path('list/', visual_list, name='visual_list'),
    path('create/', visual_create, name='visual_create'),
    path('<int:pk>/', visual_detail, name='visual_detail'),
    path('delete/<int:pk>/', visual_delete, name='visual_delete'),

    # Stats
    path('api/stats/posts-trend-weekly/', api_posts_trend_weekly, name='api_posts_trend_weekly'),
    path('stats/', stats_page, name='visual_stats_page'),
    path('api/stats/posts-trend/', api_posts_trend, name='api_posts_trend'),
    path('api/stats/emotions-distribution/', api_emotions_distribution, name='api_emotions_distribution'),
    path('api/stats/top-objects/', api_top_objects, name='api_top_objects'),
]
