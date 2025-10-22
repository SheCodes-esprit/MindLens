from django.shortcuts import render, get_object_or_404, redirect
from .models import Entry
from django.contrib.auth.decorators import login_required
from transformers import pipeline
from django.db.models import Q
from datetime import datetime


@login_required
def entry_list(request):
    entries = Entry.objects.filter(user=request.user).order_by('-created_at')
    
    q = request.GET.get('q', '').strip()
    if q:
        entries = entries.filter(title__icontains=q)
    
    feeling = request.GET.get('feeling', '').strip()
    if feeling:
        entries = entries.filter(feeling=feeling)
    
    month = request.GET.get('month', '').strip()
    if month:
        try:
            dt = datetime.strptime(month, '%Y-%m')
            entries = entries.filter(
                created_at__year=dt.year,
                created_at__month=dt.month
            )
        except ValueError:
            pass  

    feelings_list = Entry.objects.filter(user=request.user).values_list('feeling', flat=True).distinct()

    context = {
        'entries': entries,
        'feelings_list': feelings_list,
        'request': request,  
    }
    return render(request, 'frontoffice/pages/text/entries.html', context)


classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base",framework="pt" )

def analyze_feeling(text):
    if not text.strip():
        return ""
    result = classifier(text)
    if result:
        return result[0]['label']
    return ""

@login_required
def add_entry(request):
    if request.method == 'POST':
        title = request.POST.get('title',"").strip()
        content = request.POST.get('content',"").strip()
        feeling = analyze_feeling(content)
        if title and content:
            Entry.objects.create(user=request.user, title=title or "untitled", content=content,feeling=feeling)
    return redirect('entry_list')


@login_required
def update_entry (request,entry_id) : 
    entry =  get_object_or_404(Entry, id=entry_id, user=request.user)
    if(request.method == 'POST') : 
        entry.title = request.POST.get('title')
        entry.content = request.POST.get('content')
        entry.feeling = analyze_feeling('content')
        entry.save()
        return redirect('entry_list')
    return render(request, 'templates/frontoffice/pages/text/update_entry.html', {'entry': entry})

@login_required
def delete_entry(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id, user=request.user)
    entry.delete()
    return redirect('entry_list')

@login_required
def entry_detail(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id, user=request.user)
    return render(request, 'frontoffice/pages/text/entry_detail.html', {'entry': entry})