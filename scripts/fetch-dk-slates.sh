#!/bin/bash
# Fetch DraftKings Classic slates for NFL, NBA, and MLB.
# Intended to be run daily via cron on the production server.
# Logs are appended to /app/logs/fetch-dk-slates.log

set -e
cd /app
. env/bin/activate
cd opto

echo "$(date '+%Y-%m-%d %H:%M:%S') — Starting fetch_dk_slates"
DJANGO_SETTINGS_MODULE=opto.settings.prod python manage.py fetch_dk_slates
echo "$(date '+%Y-%m-%d %H:%M:%S') — Done"
