from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import WellbeingRecord, RoutineRecommendation
from .forms import WellbeingRecordForm, RoutineRecommendationForm
from datetime import date
from django.db.models import Avg
# Import your AI utilities
from .ai_prompts import generate_summary_and_recommendations
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
