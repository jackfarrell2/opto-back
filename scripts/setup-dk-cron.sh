#!/bin/bash
# Installs the daily DraftKings slate fetch cron job on the production server.
# Run this once after deploying: ./scripts/setup-dk-cron.sh
set -e

if [[ -z "$SERVER" ]]; then
    export SERVER=optoback
fi

echo ">>> Setting up fetch-dk-slates cron on $SERVER"
ssh root@$SERVER /bin/bash << 'EOF'
set -e

# Make the script executable
chmod +x /app/scripts/fetch-dk-slates.sh

CRON_FILE=/etc/cron.d/fetch-dk-slates
CRON_LINE="0 9 * * * root /app/scripts/fetch-dk-slates.sh >> /app/logs/fetch-dk-slates.log 2>&1"

if grep -qF "fetch-dk-slates" "$CRON_FILE" 2>/dev/null; then
    echo ">>> Cron job already installed in $CRON_FILE"
else
    echo "$CRON_LINE" > "$CRON_FILE"
    chmod 644 "$CRON_FILE"
    echo ">>> Cron job installed: $CRON_FILE"
    echo "    Runs daily at 09:00 UTC (5 AM ET)"
fi
EOF

echo ">>> Done"
