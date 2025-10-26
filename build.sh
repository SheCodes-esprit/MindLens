#!/usr/bin/env bash
set -o errexit

# Install ffmpeg for MoviePy & FER video processing
apt-get update && apt-get install -y ffmpeg

# Upgrade pip tools first
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply migrations
python manage.py migrate

# Create superuser if environment variables exist
python manage.py createsuperuser --noinput || true
