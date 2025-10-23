from django.shortcuts import render, get_object_or_404, redirect
from .models import Entry,TextEntryInsight,Tag
from django.contrib.auth.decorators import login_required
from transformers import pipeline
from django.db.models import Q
from datetime import datetime
from transformers import BartForConditionalGeneration, BartTokenizer
import torch
from bs4 import BeautifulSoup



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

tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")


def summarize_text(text, max_summary_length=150):
    soup = BeautifulSoup(text, "html.parser")
    plain_text = soup.get_text(separator=" ", strip=True)

    plain_text = " ".join(plain_text.split())

    max_input_length = model.config.max_position_embeddings
    inputs = tokenizer(
        plain_text,
        max_length=max_input_length,
        truncation=True,
        return_tensors="pt"
    )

    with torch.no_grad():
        summary_ids = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=max_summary_length,
            min_length=30,
            length_penalty=2.0,
            num_beams=4,
            early_stopping=True
        )

    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary



@login_required
def add_entry(request):
    if request.method == 'POST':
        title = request.POST.get('title', "").strip()
        content = request.POST.get('content', "").strip()
        tag_name = request.POST.get('tag', "").strip().lower()

        feeling = analyze_feeling(content)

        if title and content:
            tag = None
            if tag_name:
                tag, created = Tag.objects.get_or_create(user=request.user, name=tag_name)

            entry = Entry.objects.create(
                user=request.user,
                title=title or "Untitled",
                content=content,
                feeling=feeling,
                tag=tag
            )

            summary_text = summarize_text(content)
            TextEntryInsight.objects.create(
                entry=entry,
                user=request.user,
                summary=summary_text
            )

            return redirect('entry_list')

    return render(request, 'frontoffice/pages/text/entry_form.html', {'entry': None})



@login_required
@login_required
def update_entry(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id, user=request.user)
    insight = TextEntryInsight.objects.filter(entry=entry, user=request.user).first()

    if request.method == 'POST':
        entry.title = request.POST.get('title')
        entry.content = request.POST.get('content')
        entry.feeling = analyze_feeling(entry.content)
        entry.save()

        summary_text = request.POST.get('summary', '')
        if insight:
            insight.summary = summary_text
            insight.save()
        else:
            if summary_text:
                TextEntryInsight.objects.create(entry=entry, user=request.user, summary=summary_text)

        return redirect('entry_list')

    return render(request, 'frontoffice/pages/text/entry_form.html', {'entry': entry, 'insight': insight})


@login_required
def delete_entry(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id, user=request.user)
    if request.method == 'POST':
        entry.delete()
        return redirect('entry_list')

@login_required
def entry_detail(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id, user=request.user)
    insight =TextEntryInsight.objects.filter(entry=entry, user=request.user).first()
    return render(request, 'frontoffice/pages/text/entry_detail.html', {'entry': entry,'insight':insight})