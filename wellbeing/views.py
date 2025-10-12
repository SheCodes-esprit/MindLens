from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import WellbeingRecord, RoutineRecommendation
from .forms import WellbeingRecordForm, RoutineRecommendationForm

@login_required
def wellbeing_list(request):
    """Liste des enregistrements de bien-être de l'utilisateur"""
    records = WellbeingRecord.objects.filter(user=request.user)
    return render(request, 'frontoffice/pages/wellbeing/wellbeing_list.html', {
        'records': records
    })

@login_required
def wellbeing_create(request):
    """Créer un nouvel enregistrement de bien-être"""
    if request.method == 'POST':
        form = WellbeingRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.user = request.user
            record.save()
            messages.success(request, 'Enregistrement créé avec succès !')
            return redirect('wellbeing:wellbeing_detail', pk=record.pk)
    else:
        form = WellbeingRecordForm()
    
    return render(request, 'frontoffice/pages/wellbeing/wellbeing_form.html', {
        'form': form,
        'title': 'Nouvel enregistrement'
    })

@login_required
def wellbeing_detail(request, pk):
    """Détail d'un enregistrement avec ses recommandations"""
    record = get_object_or_404(WellbeingRecord, pk=pk, user=request.user)
    recommendations = record.recommendations.all()
    
    return render(request, 'frontoffice/pages/wellbeing/wellbeing_detail.html', {
        'record': record,
        'recommendations': recommendations
    })

@login_required
def wellbeing_update(request, pk):
    """Modifier un enregistrement"""
    record = get_object_or_404(WellbeingRecord, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = WellbeingRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Enregistrement modifié avec succès !')
            return redirect('wellbeing:wellbeing_detail', pk=record.pk)
    else:
        form = WellbeingRecordForm(instance=record)
    
    return render(request, 'frontoffice/pages/wellbeing/wellbeing_form.html', {
        'form': form,
        'title': 'Modifier l\'enregistrement'
    })

@login_required
def wellbeing_delete(request, pk):
    """Supprimer un enregistrement"""
    record = get_object_or_404(WellbeingRecord, pk=pk, user=request.user)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Enregistrement supprimé avec succès !')
        return redirect('wellbeing:wellbeing_list')
    
    return render(request, 'frontoffice/pages/wellbeing/wellbeing_confirm_delete.html', {
        'record': record
    })

@login_required
def recommendation_create(request, wellbeing_pk):
    """Créer une recommandation pour un enregistrement"""
    record = get_object_or_404(WellbeingRecord, pk=wellbeing_pk, user=request.user)
    
    if request.method == 'POST':
        form = RoutineRecommendationForm(request.POST)
        if form.is_valid():
            recommendation = form.save(commit=False)
            recommendation.wellbeing_record = record
            recommendation.ai_generated = False  # Créé manuellement
            recommendation.save()
            messages.success(request, 'Recommandation ajoutée avec succès !')
            return redirect('wellbeing:wellbeing_detail', pk=record.pk)
    else:
        form = RoutineRecommendationForm()
    
    return render(request, 'frontoffice/pages/wellbeing/recommendation_form.html', {
        'form': form,
        'record': record
    })