#!/bin/bash
# Cron job script for cleaning up old rejected verifications
# This script should be run monthly

# Navigate to project directory
cd /home/el-banna/Desktop/GGamer/backend

# Run cleanup command
docker exec ggamer-backend python manage.py cleanup_old_verifications

# Log the execution
echo "Cleanup executed at $(date)" >> /var/log/ggamer_cleanup.log
