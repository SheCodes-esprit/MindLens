from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import VisualEntryForm
from .models import VisualEntry, VisualInsight
from transformers import DetrImageProcessor, DetrForObjectDetection
from PIL import Image
import torch
import cv2
from colorthief import ColorThief
from django.conf import settings
import os
from fer import FER
import numpy as np
from moviepy.editor import VideoFileClip
from io import BytesIO


# ---------------------- LIST & DETAIL ----------------------

@login_required
def visual_list(request):
    entries = VisualEntry.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'frontoffice/pages/visual/visual_list.html', {'entries': entries})


@login_required
def visual_detail(request, pk):
    entry = get_object_or_404(VisualEntry, pk=pk, user=request.user)
    insights = entry.insights.all()
    return render(request, 'frontoffice/pages/visual/visual_detail.html', {'entry': entry, 'insights': insights})


# ---------------------- CREATE ----------------------

@login_required
def visual_create(request):
    if request.method == 'POST':
        form = VisualEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            analyze_visual(entry)
            return redirect('visual_list')
    else:
        form = VisualEntryForm()
    return render(request, 'frontoffice/pages/visual/visual_create.html', {'form': form})


# ---------------------- DELETE ----------------------

@login_required
def visual_delete(request, pk):
    entry = get_object_or_404(VisualEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        return redirect('visual_list')
    return render(request, 'frontoffice/pages/visual/visual_confirm_delete.html', {'entry': entry})


# ---------------------- ANALYSE PRINCIPALE ----------------------

def analyze_visual(entry):
    # 1️⃣ Device GPU/CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 2️⃣ Charger modèle DETR
    processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
    model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50").to(device)
    model.eval()

    # 3️⃣ Récupérer chemin fichier
    file_path = os.path.join(settings.MEDIA_ROOT, entry.media_url.name)
    file_ext = os.path.splitext(file_path)[1].lower()

    image_pil = None  # pour stocker l'image finale à analyser

    # 4️⃣ Gestion image / vidéo
    try:
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
            # --- Cas image ---
            image_pil = Image.open(file_path).convert("RGB")

        elif file_ext in ['.mp4', '.mov', '.avi', '.mkv']:
            # --- Cas vidéo : extraire une frame ---
            clip = VideoFileClip(file_path)
            frame = clip.get_frame(1)  # frame à 1s
            image_pil = Image.fromarray(frame)
            clip.close()

        else:
            entry.ai_description = "Unsupported file type for analysis."
            entry.save()
            return

        # Convertir pour FER (OpenCV utilise BGR)
        image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)

        # 5️⃣ Détection objets DETR
        inputs = processor(images=image_pil, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)

        target_sizes = torch.tensor([image_pil.size[::-1]], device=device)
        results = processor.post_process_object_detection(outputs, threshold=0.5, target_sizes=target_sizes)[0]
        detected_objects = [model.config.id2label[label.item()] for label in results["labels"]]

        # 6️⃣ Détection émotions FER
        detector = FER(mtcnn=True)
        emotion_scores = detector.detect_emotions(image_cv)
        if emotion_scores:
            top_emotion = max(emotion_scores[0]["emotions"], key=emotion_scores[0]["emotions"].get)
        else:
            top_emotion = "neutral"

        # 7️⃣ Couleurs dominantes (pour vidéos : sur frame extraite)
        buffer = BytesIO()
        image_pil.save(buffer, format="PNG")
        buffer.seek(0)
        color_thief = ColorThief(buffer)
        dominant_colors = color_thief.get_palette(color_count=3)

        # 8️⃣ Génération tags et score confiance
        tags_generated = detected_objects[:5]
        ai_confidence = (
            sum(results["scores"].tolist()) / len(results["scores"])
            if len(results["scores"]) > 0 else 0.0
        )

        # 9️⃣ Sauvegarde en base
        entry.ai_description = f"Détecté: {', '.join(detected_objects)}. Émotion: {top_emotion}."
        entry.save()

        VisualInsight.objects.create(
            visual_entry=entry,
            detected_objects=detected_objects,
            dominant_colors=dominant_colors,
            emotion_detected=top_emotion,
            tags_generated=tags_generated,
            ai_confidence=ai_confidence
        )

    except Exception as e:
        entry.ai_description = f"Erreur pendant l'analyse : {e}"
        entry.save()
