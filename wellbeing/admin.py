from django.contrib import admin
from .models import WellbeingRecord, RoutineRecommendation

@admin.register(WellbeingRecord)
class WellbeingRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'mood_score', 'energy_level', 'sleep_hours', 'productivity_score']
    list_filter = ['date', 'mood_score', 'productivity_score']
    search_fields = ['user__username', 'ai_summary']
    date_hierarchy = 'date'
    readonly_fields = ['date']

@admin.register(RoutineRecommendation)
class RoutineRecommendationAdmin(admin.ModelAdmin):
    list_display = ['wellbeing_record', 'type', 'ai_generated', 'efficiency_score', 'created_at']
    list_filter = ['type', 'ai_generated', 'created_at']
    search_fields = ['description', 'wellbeing_record__user__username']
    readonly_fields = ['created_at']