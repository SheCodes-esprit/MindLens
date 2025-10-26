#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
#Convertir les fichiers statiques
python manage.py collectstatic --no-input
#Appliquer toutes les migrations de bases de données en suspens
python manage.py migrate
python manage.py createsuperuser --noinput || true