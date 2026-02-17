#!/bin/bash
# Background health check runner for crontab
# This script calls the health check once per run
# Crontab will call it at intervals, and the script itself uses random sleep

cd "$(dirname "$0")"

# Run health check once
python3 health_check.py --once

# Log crontab execution
echo "Cron job executed at $(date)" >> ../logs/crontab.log
