#!/bin/bash
set -o errexit

# Installe les dépendances
pip install -r requirements.txt --no-cache-dir

# Applique les migrations
python manage.py migrate --noinput

# Collecte les fichiers statiques
python manage.py collectstatic --noinput

# Crée un superuser si les variables d'environnement sont définies (ignore les erreurs)
python manage.py createsuperuser --noinput --username "$DJANGO_SUPERUSER_USERNAME" --email "$DJANGO_SUPERUSER_EMAIL" --password "$DJANGO_SUPERUSER_PASSWORD" || true