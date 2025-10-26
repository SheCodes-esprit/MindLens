#!/usr/bin/env bash
set -o errexit

# Upgrade pip, setuptools, wheel first
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply migrations
python manage.py migrate

# Create superuser if environment variables exist
python manage.py createsuperuser --noinput || true
