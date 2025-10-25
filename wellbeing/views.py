from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import WellbeingRecord, RoutineRecommendation
from .forms import WellbeingRecordForm, RoutineRecommendationForm
from datetime import date
from django.db.models import Avg
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Max, Min, Q
from django.utils import timezone
from datetime import timedelta
from .models import WellbeingRecord, RoutineRecommendation
from .analytics_utils import (
    UserSegmentation, CorrelationAnalysis, PredictiveTrends, HeatmapData
)
# Import your AI utilities
from .ai_prompts import generate_summary_and_recommendations

# ✅ FIXED: Use get_user_model() instead of importing User directly
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
def wellbeing_list(request):
    """List the user's wellbeing records with monthly statistics."""
    # Get month/year filters from URL (defaults to current month/year)
    today = date.today()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    # Filter user's records by selected month/year
    records = WellbeingRecord.objects.filter(
        user=request.user,
        date__year=year,
        date__month=month
    ).order_by('-date')

    # Calculate monthly statistics
    stats = records.aggregate(
        mood_avg=Avg('mood_score'),
        energy_avg=Avg('energy_level'),
        sleep_avg=Avg('sleep_hours'),
        productivity_avg=Avg('productivity_score'),
    )

    # Retrieve all available months/years (for dropdown selection)
    all_dates = WellbeingRecord.objects.filter(user=request.user).dates('date', 'month', order='DESC')
    
    return render(request, 'frontoffice/pages/wellbeing/wellbeing_list.html', {
        'records': records,
        'stats': stats,
        'selected_month': month,
        'selected_year': year,
        'all_dates': all_dates,
    })



@login_required
def wellbeing_create(request):
    """Create a new wellbeing record with AI-generated summary and recommendations."""
    today = date.today()

    # Prevent duplicate record for today
    existing_record = WellbeingRecord.objects.filter(user=request.user, date=today).first()
    if existing_record:
        messages.warning(request, "You've already created a record for today!")
        return redirect('wellbeing:wellbeing_detail', pk=existing_record.pk)

    if request.method == 'POST':
        form = WellbeingRecordForm(request.POST)
        if form.is_valid():
            # 1️⃣ Save the basic record
            record = form.save(commit=False)
            record.user = request.user
            record.save()

            # 2️⃣ Generate AI summary and recommendations
            try:
                ai_results = generate_summary_and_recommendations(record, model="llama-3.1-8b-instant")
                
                # Save AI summary
                if ai_results.get("summary") and not ai_results["summary"].startswith("Error:"):
                    record.ai_summary = ai_results["summary"]
                    record.save()
                else:
                    messages.warning(request, f"AI summary: {ai_results.get('summary')}")

                # Save AI recommendations
                recommendations = ai_results.get("recommendations", {})
                for rec_type, description in recommendations.items():
                    if description and not description.startswith("Error:"):
                        RoutineRecommendation.objects.create(
                            wellbeing_record=record,
                            type=rec_type,
                            description=description,
                            ai_generated=True,
                            efficiency_score=0.5  # placeholder score
                        )
                    else:
                        messages.warning(request, f"AI recommendation ({rec_type}): {description}")

            except Exception as e:
                messages.warning(request, f"AI generation failed: {e}")

            messages.success(request, 'Record created successfully with AI-generated insights!')
            return redirect('wellbeing:wellbeing_detail', pk=record.pk)
    else:
        form = WellbeingRecordForm()

    return render(request, 'frontoffice/pages/wellbeing/wellbeing_form.html', {
        'form': form,
        'title': 'New Record'
    })


@login_required
def wellbeing_detail(request, pk):
    """Display the details of a wellbeing record along with its recommendations."""
    record = get_object_or_404(WellbeingRecord, pk=pk, user=request.user)
    recommendations = record.recommendations.all()
    
    return render(request, 'frontoffice/pages/wellbeing/wellbeing_detail.html', {
        'record': record,
        'recommendations': recommendations
    })


@login_required
def wellbeing_update(request, pk):
    """Edit an existing wellbeing record and regenerate AI insights."""
    record = get_object_or_404(WellbeingRecord, pk=pk, user=request.user)

    if request.method == 'POST':
        form = WellbeingRecordForm(request.POST, instance=record)
        if form.is_valid():
            # 1️⃣ Save the updated record
            record = form.save()

            # 2️⃣ Delete old AI-generated recommendations to avoid duplicates
            RoutineRecommendation.objects.filter(
                wellbeing_record=record,
                ai_generated=True
            ).delete()

            # 3️⃣ Regenerate AI summary and recommendations based on new values
            try:
                ai_results = generate_summary_and_recommendations(record, model="llama-3.1-8b-instant")
                
                # Save AI summary
                if ai_results.get("summary") and not ai_results["summary"].startswith("Error:"):
                    record.ai_summary = ai_results["summary"]
                    record.save()
                else:
                    messages.warning(request, f"AI summary: {ai_results.get('summary')}")

                # Save AI recommendations
                recommendations = ai_results.get("recommendations", {})
                for rec_type, description in recommendations.items():
                    if description and not description.startswith("Error:"):
                        RoutineRecommendation.objects.create(
                            wellbeing_record=record,
                            type=rec_type,
                            description=description,
                            ai_generated=True,
                            efficiency_score=0.5  # placeholder score
                        )
                    else:
                        messages.warning(request, f"AI recommendation ({rec_type}): {description}")

            except Exception as e:
                messages.warning(request, f"AI generation failed: {e}")

            messages.success(request, 'Record updated successfully with refreshed AI insights!')
            return redirect('wellbeing:wellbeing_detail', pk=record.pk)
    else:
        form = WellbeingRecordForm(instance=record)

    return render(request, 'frontoffice/pages/wellbeing/wellbeing_form.html', {
        'form': form,
        'title': 'Edit Record'
    })

@login_required
def wellbeing_delete(request, pk):
    """Delete a wellbeing record."""
    record = get_object_or_404(WellbeingRecord, pk=pk, user=request.user)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Record deleted successfully!')
        return redirect('wellbeing:wellbeing_list')
    
    return render(request, 'frontoffice/pages/wellbeing/wellbeing_confirm_delete.html', {
        'record': record
    })


@login_required
def recommendation_create(request, wellbeing_pk):
    """Create a routine recommendation for a given wellbeing record."""
    record = get_object_or_404(WellbeingRecord, pk=wellbeing_pk, user=request.user)
    
    if request.method == 'POST':
        form = RoutineRecommendationForm(request.POST)
        if form.is_valid():
            recommendation = form.save(commit=False)
            recommendation.wellbeing_record = record
            recommendation.ai_generated = False  # Created manually
            recommendation.save()
            messages.success(request, 'Recommendation added successfully!')
            return redirect('wellbeing:wellbeing_detail', pk=record.pk)
    else:
        form = RoutineRecommendationForm()
    
    return render(request, 'frontoffice/pages/wellbeing/recommendation_form.html', {
        'form': form,
        'record': record
    })



@staff_member_required
def wellbeing_analytics(request):
    """
    Privacy-focused analytics dashboard showing aggregated wellbeing statistics.
    No personal user data is displayed.
    """
    
    # Get date range filter from request
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    # Filter records by date range
    records = WellbeingRecord.objects.filter(date__gte=start_date)
    
    # Aggregate statistics (no personal data exposed)
    stats = {
        'total_records': records.count(),
        'total_users': records.values('user').distinct().count(),
        'avg_mood': round(records.aggregate(Avg('mood_score'))['mood_score__avg'] or 0, 2),
        'avg_energy': round(records.aggregate(Avg('energy_level'))['energy_level__avg'] or 0, 2),
        'avg_sleep': round(records.aggregate(Avg('sleep_hours'))['sleep_hours__avg'] or 0, 2),
        'avg_productivity': round(records.aggregate(Avg('productivity_score'))['productivity_score__avg'] or 0, 2),
        'mood_range': {
            'min': records.aggregate(Min('mood_score'))['mood_score__min'] or 0,
            'max': records.aggregate(Max('mood_score'))['mood_score__max'] or 0,
        },
        'energy_range': {
            'min': records.aggregate(Min('energy_level'))['energy_level__min'] or 0,
            'max': records.aggregate(Max('energy_level'))['energy_level__max'] or 0,
        },
        'sleep_range': {
            'min': round(records.aggregate(Min('sleep_hours'))['sleep_hours__min'] or 0, 1),
            'max': round(records.aggregate(Max('sleep_hours'))['sleep_hours__max'] or 0, 1),
        },
    }
    
    # Daily aggregates for trend chart
    daily_stats = []
    for i in range(days, 0, -1):
        current_date = timezone.now().date() - timedelta(days=i)
        day_records = records.filter(date=current_date)
        
        if day_records.exists():
            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'mood': round(day_records.aggregate(Avg('mood_score'))['mood_score__avg'] or 0, 1),
                'energy': round(day_records.aggregate(Avg('energy_level'))['energy_level__avg'] or 0, 1),
                'sleep': round(day_records.aggregate(Avg('sleep_hours'))['sleep_hours__avg'] or 0, 1),
                'productivity': round(day_records.aggregate(Avg('productivity_score'))['productivity_score__avg'] or 0, 1),
                'count': day_records.count(),
            })
    
    # Recommendation statistics
    recommendations = RoutineRecommendation.objects.filter(
        wellbeing_record__date__gte=start_date
    )
    
    recommendation_stats = {
        'total': recommendations.count(),
        'ai_generated': recommendations.filter(ai_generated=True).count(),
        'by_type': dict(
            recommendations.values('type').annotate(count=Count('id')).values_list('type', 'count')
        ),
        'avg_efficiency': round(recommendations.aggregate(Avg('efficiency_score'))['efficiency_score__avg'] or 0, 2),
    }
    
    # Score distribution (for histogram)
    mood_distribution = {
        'low': records.filter(mood_score__lte=3).count(),
        'medium': records.filter(mood_score__gt=3, mood_score__lte=7).count(),
        'high': records.filter(mood_score__gt=7).count(),
    }
    
    all_records = records.select_related('user').order_by('-date')
    
    # User Segmentation
    user_segments = UserSegmentation.get_all_user_segments(days)
    segment_summary = {
        segment: len(users) for segment, users in user_segments.items()
    }
    
    # Correlations
    records_list = list(records.order_by('date'))
    correlations = CorrelationAnalysis.calculate_correlations(records_list)
    correlation_insights = CorrelationAnalysis.get_correlation_insights(correlations)
    
    # Predictive Trends
    at_risk_users = PredictiveTrends.identify_at_risk_users(days)
    
    # Heatmap Data
    daily_heatmap = HeatmapData.generate_daily_heatmap(days)
    
    
    # Pagination
    paginator = Paginator(all_records, 4)  # 4 records per page
    page = request.GET.get('page', 1)
    
    try:
        all_records = paginator.page(page)
    except PageNotAnInteger:
        all_records = paginator.page(1)
    except EmptyPage:
        all_records = paginator.page(paginator.num_pages)
    
    context = {
        'stats': stats,
        'daily_stats': daily_stats,
        'recommendation_stats': recommendation_stats,
        'mood_distribution': mood_distribution,
        'days': days,
        'start_date': start_date,
        'all_records': all_records,
        'user_segments': user_segments,
        'segment_summary': segment_summary,
        'correlations': correlations,
        'correlation_insights': correlation_insights,
        'at_risk_users': at_risk_users,
        'daily_heatmap': daily_heatmap,
        'days': days,
    }
    
    return render(request, 'backoffice/pages/wellbeing_analytics.html', context)