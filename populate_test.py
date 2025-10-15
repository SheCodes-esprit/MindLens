# populate_test.py
import os
import django
import random
from datetime import datetime, timedelta

# --- CONFIG DJANGO ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MindLens.settings")
django.setup()  # ← très important pour accéder aux modèles

# --- IMPORT MODELES ---
from users.models import User
from visual.models import VisualEntry, VisualInsight

# --- CONFIG DE TEST ---
user = User.objects.get(username='mouna')
emotions = ['happy', 'sad', 'neutral', 'angry', 'surprised']
objects_samples = [['cat','chair'], ['dog'], ['phone','book'], ['flower'], ['cup']]

# --- CRÉATION DES POSTS ET INSIGHTS ---
for i in range(8):
    # Lundi exact de la semaine i
    week_start = datetime.now() - timedelta(weeks=i)
    week_start = week_start - timedelta(days=week_start.weekday())

    # Créer 1 à 3 posts par semaine pour tester le graphique
    for j in range(random.randint(1, 3)):
        entry = VisualEntry.objects.create(
            user=user,
            type='image',
            media_url='visual_entries/test.jpg',  # assure-toi que ce fichier existe
            caption=f"Post test semaine {i+1}, post {j+1}",
            created_at=week_start + timedelta(days=random.randint(0, 6))
        )

        VisualInsight.objects.create(
            visual_entry=entry,
            detected_objects=random.choice(objects_samples),
            dominant_colors=[[255,0,0],[0,255,0],[0,0,255]],
            emotion_detected=random.choice(emotions),
            tags_generated=['test','demo'],
            ai_confidence=random.uniform(0.5, 1.0)
        )

print("✅ Données de test ajoutées avec succès !")
