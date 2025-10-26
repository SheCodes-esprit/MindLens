# visual/urls.py
from django.urls import path
from .views import (
    visual_list, visual_detail, visual_create, visual_delete,
    stats_page, api_posts_trend, api_emotions_distribution, api_top_objects ,
     stats_page, api_posts_trend, api_emotions_distribution , api_posts_trend_weekly ,
     api_visuals_filtered ,api_visuals_timeline ,api_generate_albums ,api_mood_story ,
     mood_prediction ,  personality_start ,personality_complete
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


    #new
    path('api/visuals/filtered/', api_visuals_filtered, name='api_visuals_filtered'),
    path('api/visuals/timeline/', api_visuals_timeline, name='api_visuals_timeline'),
    path('api/albums/', api_generate_albums, name='api_generate_albums'),
    path('api/mood_story/', api_mood_story, name='api_mood_story'),

    path('api/mood-prediction/', mood_prediction, name='api_mood_prediction'),

    path('api/personality-start/', personality_start, name='personality_start'),
    path('api/personality-complete/', personality_complete, name='personality_complete'),
]
