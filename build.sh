#!/bin/bash
set -o errexit

echo "🚀 INSTALLATION OPTIMISÉE POUR RENDER..."

# Nettoyage avant installation
pip cache purge

# Installation avec optimisation mémoire
pip install --no-cache-dir --progress-bar off -r requirements.txt

# Nettoyage agressif après installation
find /opt/render/project/src/.venv -name "*.pyc" -delete
find /opt/render/project/src/.venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "📦 COLLECTSTATIC..."
python manage.py collectstatic --noinput --clear

echo "🗄️ MIGRATIONS..."
python manage.py migrate --noinput

echo "🧹 NETTOYAGE MÉMOIRE..."
python -c "
import gc
gc.collect()
import os
os.system('sync')
"

echo "✅ BUILD TERMINÉ!"