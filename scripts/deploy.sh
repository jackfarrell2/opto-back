#!/bin/bash
set -e
# Deploy Django project
export SERVER=optoback
# ./scripts/backup-database.sh
# backups take too much space on cheap server, only use manually
./scripts/upload-code.sh
./scripts/install-code.sh