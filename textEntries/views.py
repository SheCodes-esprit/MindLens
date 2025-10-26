from django.shortcuts import render, get_object_or_404, redirect
from .models import Entry, TextEntryInsight, Tag
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from datetime import datetime
from django.core.exceptions import ValidationError
from django.utils.timezone import localtime
from collections import Counter, defaultdict
import datetime
import re
from django.utils.safestring import mark_safe
import json
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import logging

logger = logging.getLogger(__name__)

# <CHANGE> Lazy loading for all heavy models
_classifier = None
_tokenizer = None
_model = None
_goal_extractor = None
_suggestion_generator = None

def get_classifier():
    """Lazy load the emotion classifier"""
    global _classifier
    if _classifier is None:
        try:
            logger.info("[Text] Loading emotion classifier...")
            from transformers import pipeline
            _classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", framework="pt")
            logger.info("[Text] Emotion classifier loaded successfully")
        except Exception as e:
            logger.error(f"[Text] Failed to load emotion classifier: {e}")
            raise
    return _classifier

def get_bart_model():
    """Lazy load BART model for summarization"""
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        try:
            logger.info("[Text] Loading BART model...")
            from transformers import BartTokenizer, BartForConditionalGeneration
            _tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
            _model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
            logger.info("[Text] BART model loaded successfully")
        except Exception as e:
            logger.error(f"[Text] Failed to load BART model: {e}")
            raise
    return _tokenizer, _model

def get_goal_extractor():
    """Lazy load the goal extractor model"""
    global _goal_extractor
    if _goal_extractor is None:
        try:
            logger.info("[Text] Loading goal extractor...")
            from transformers import pipeline
            _goal_extractor = pipeline("text2text-generation", model="google/flan-t5-base")
            logger.info("[Text] Goal extractor loaded successfully")
        except Exception as e:
            logger.error(f"[Text] Failed to load goal extractor: {e}")
            raise
    return _goal_extractor

def get_suggestion_generator():
    """Lazy load the suggestion generator model"""
    global _suggestion_generator
    if _suggestion_generator is None:
        try:
            logger.info("[Text] Loading suggestion generator...")
            from transformers import pipeline
            import torch
            _suggestion_generator = pipeline(
                "text2text-generation",
                model="google/flan-t5-base",
                device=0 if torch.cuda.is_available() else -1
            )
            logger.info("[Text] Suggestion generator loaded successfully")
        except Exception as e:
            logger.error(f"[Text] Failed to load suggestion generator: {e}")
            raise
    return _suggestion_generator

def ensure_nltk_data():
    """Ensure NLTK data is available (called only when needed)"""
    try:
        nltk.data.find('corpora/stopwords')
        nltk.data.find('corpora/wordnet')
        nltk.data.find('corpora/omw-1.4')
    except LookupError:
        logger.info("[Text] Downloading NLTK data...")
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)

def analyze_feeling(text):
    """Analyze text emotion with lazy loading"""
    if not text.strip():
        return ""
    
    try:
        classifier = get_classifier()
        result = classifier(text)
        if result:
            return result[0]['label']
        return ""
    except Exception as e:
        logger.error(f"[Text] Emotion analysis failed: {e}")
        return "neutral"

def summarize_text(text, max_summary_length=150):
    """Summarize text with lazy loading"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, "html.parser")
        plain_text = soup.get_text(separator=" ", strip=True)
        plain_text = " ".join(plain_text.split())

        tokenizer, model = get_bart_model()
        
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
    except Exception as e:
        logger.error(f"[Text] Summarization failed: {e}")
        return text[:200] + "..." if len(text) > 200 else text

def extract_goals(text):
    """Extract goals with lazy loading"""
    try:
        extractor = get_goal_extractor()
        text = text[:1000]  
        prompt = (
            "Extract only actionable goals or tasks from this journal entry. "
            "Return as a JSON array of short sentences. Do not include feelings or reflections.\n\n"
            f"{text}\n\nOutput:"
        )
        result = extractor(prompt, max_new_tokens=128)[0]["generated_text"].strip()

        result = re.sub(r"goals_or_tasks.*?;", "", result)
        result = result.replace("[];", "").replace("=[]", "").replace("= []", "").strip()

        match = re.search(r"\[.*\]", result, re.DOTALL)
        if match:
            result = match.group(0)
        else:
            result = f'["{result}"]'

        try:
            goals = json.loads(result)
            cleaned = [g.strip() for g in goals if isinstance(g, str) and g.strip() and g.lower() != "null"]
            return cleaned
        except:
            return []
    except Exception as e:
        logger.error(f"[Text] Goal extraction failed: {e}")
        return []

def generate_action_suggestion(summary):
    """Generate action suggestion with lazy loading"""
    try:
        generator = get_suggestion_generator()

        few_shot_prompt = f"""
You are a friendly productivity coach. Based on the user's journal summary,
suggest one small, realistic action they can do TODAY.
The action should be practical, kind, and easy to start — not a reflection or long-term goal.

Examples of good suggestions:
- Write down tomorrow's top 3 priorities.
- Go for a 20-minute walk after lunch.
- Prepare one healthy meal for dinner.
- Send a kind message to a friend you miss.

Avoid repeating the summary or saying "I will…". 
Respond with a single actionable sentence only.

Summary: {summary}

Suggested Action:
""".strip()

        result = generator(
            few_shot_prompt,
            max_new_tokens=50,
            num_return_sequences=1,
            temperature=0.8,
            top_p=0.9,
            repetition_penalty=1.2,
        )

        suggestion = result[0]["generated_text"].strip()

        if len(suggestion.split()) > 25 or suggestion.lower().startswith("summary"):
            suggestion = "Take one small step today that moves you closer to your goal."

        return suggestion
    except Exception as e:
        logger.error(f"[Text] Suggestion generation failed: {e}")
        return "Take one small step today that moves you closer to your goal."

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
            dt = datetime.datetime.strptime(month, '%Y-%m')
            entries = entries.filter(
                created_at__year=dt.year,
                created_at__month=dt.month
            )
        except ValueError:
            pass  

    tag_id = request.GET.get('tag', '').strip()
    if tag_id.isdigit():
        entries = entries.filter(tag_id=int(tag_id))

    feelings_list = Entry.objects.filter(user=request.user).values_list('feeling', flat=True).distinct()
    
    tags_list = Tag.objects.filter(user=request.user).order_by('name')

    context = {
        'entries': entries,
        'feelings_list': feelings_list,
        'tags_list': tags_list,
        'request': request,  
    }
    return render(request, 'frontoffice/pages/text/entries.html', context)

@login_required
def add_entry(request):
    errors = {}

    if request.method == 'POST':
        title = request.POST.get('title', "").strip()
        content = request.POST.get('content', "").strip()
        tag_name = request.POST.get('tag', "").strip().lower()
        
        # <CHANGE> Analyze feeling with lazy loading
        feeling = analyze_feeling(content)

        tag = None
        if tag_name:
            tag, _ = Tag.objects.get_or_create(user=request.user, name=tag_name)

        entry = Entry(
            user=request.user,
            title=title,
            content=content,
            feeling=feeling,
            tag=tag,
        )

        try:
            entry.save()

            # <CHANGE> Generate insights with lazy loading
            summary_text = summarize_text(content)
            goals = extract_goals(content)  
            suggestion_text = generate_action_suggestion(summary_text)
            
            TextEntryInsight.objects.create(
                entry=entry, 
                user=request.user, 
                summary=summary_text,
                goals=goals,
                suggestion=suggestion_text
            )

            return redirect('entry_list')

        except ValidationError as e:
            errors = e.message_dict

    return render(request, 'frontoffice/pages/text/entry_form.html', {'entry': None, 'errors': errors})

@login_required
def update_entry(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id, user=request.user)
    insight = TextEntryInsight.objects.filter(entry=entry, user=request.user).first()
    errors = {}

    if request.method == 'POST':
        entry.title = request.POST.get('title', '').strip()
        entry.content = request.POST.get('content', '').strip()
        tag_name = request.POST.get('tag', '').strip().lower()

        if tag_name:
            tag, _ = Tag.objects.get_or_create(user=request.user, name=tag_name)
            entry.tag = tag

        # <CHANGE> Analyze feeling with lazy loading
        entry.feeling = analyze_feeling(entry.content)

        try:
            entry.save()

            summary_text = request.POST.get('summary', '')
            if insight:
                insight.summary = summary_text
                insight.save()
            elif summary_text:
                TextEntryInsight.objects.create(entry=entry, user=request.user, summary=summary_text)

            return redirect('entry_list')

        except ValidationError as e:
            errors = e.message_dict

    return render(request, 'frontoffice/pages/text/entry_form.html', {
        'entry': entry,
        'insight': insight,
        'errors': errors
    })

@login_required
def delete_entry(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id, user=request.user)
    if request.method == 'POST':
        entry.delete()
        return redirect('entry_list')

@login_required
def entry_detail(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id, user=request.user)
    insight = TextEntryInsight.objects.filter(entry=entry, user=request.user).first()
    return render(request, 'frontoffice/pages/text/entry_detail.html', {'entry': entry, 'insight': insight})

@login_required
def entry_stats(request):
    # <CHANGE> Ensure NLTK data is available only when needed
    ensure_nltk_data()
    
    STOPWORDS = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()

    entries = Entry.objects.filter(user=request.user).order_by('created_at')

    if not entries.exists():
        return render(request, "frontoffice/pages/text/entry_stats.html", {
            "labels": "[]",
            "line_datasets": "[]",
            "pie_labels": "[]",
            "pie_counts": "[]",
            "pie_colors": "[]",
            "tag_labels": "[]",
            "tag_counts": "[]",
            "tag_colors": "[]",
            "most_common_mood": "Neutral",
            "total_entries": 0
        })

    # ---------------- Mood statistics ----------------
    all_sentiments = set()
    sentiment_counts = Counter()
    sentiment_over_time = defaultdict(lambda: defaultdict(int))

    for entry in entries:
        date_str = localtime(entry.created_at).strftime("%Y-%m") 
        sentiment = entry.feeling or "Neutral"
        all_sentiments.add(sentiment)
        sentiment_counts[sentiment] += 1
        sentiment_over_time[date_str][sentiment] += 1

    sorted_dates = sorted(sentiment_over_time.keys())

    colors = ["#4caf50", "#2196f3", "#f44336", "#9e9e9e", "#ff9800", "#9c27b0", "#795548", "#00bcd4"]
    line_datasets = []
    for i, sentiment in enumerate(sorted(all_sentiments)):
        data = [sentiment_over_time[date].get(sentiment, 0) for date in sorted_dates]
        line_datasets.append({
            "label": sentiment,
            "data": data,
            "borderColor": colors[i % len(colors)],
            "backgroundColor": colors[i % len(colors)] + "33",
            "fill": True,
            "tension": 0.3
        })

    pie_labels = list(sentiment_counts.keys())
    pie_counts = list(sentiment_counts.values())
    pie_colors = colors[:len(pie_labels)]

    sorted_sentiments = [s for s, _ in sentiment_counts.most_common()]
    sentiment_to_score = {s: i + 1 for i, s in enumerate(sorted_sentiments)}

    total_entries = len(entries)
    most_common_mood = sorted_sentiments[0] if sorted_sentiments else "Neutral"

    # ---------------- Tag statistics ----------------
    tag_counts_qs = entries.values('tag__name').annotate(count=Count('id')).order_by('-count')
    tag_labels = [t['tag__name'] or 'Untagged' for t in tag_counts_qs]
    tag_counts = [t['count'] for t in tag_counts_qs]
    tag_colors = colors[:len(tag_labels)]

    context = {
        "labels": mark_safe(json.dumps(sorted_dates)),
        "line_datasets": mark_safe(json.dumps(line_datasets)),
        "pie_labels": mark_safe(json.dumps(pie_labels)),
        "pie_counts": mark_safe(json.dumps(pie_counts)),
        "pie_colors": mark_safe(json.dumps(pie_colors)),
        "tag_labels": mark_safe(json.dumps(tag_labels)),
        "tag_counts": mark_safe(json.dumps(tag_counts)),
        "tag_colors": mark_safe(json.dumps(tag_colors)),
        "most_common_mood": most_common_mood,
        "total_entries": total_entries,
    }

    return render(request, "frontoffice/pages/text/entry_stats.html", context)