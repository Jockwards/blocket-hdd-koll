#!/bin/bash

# Configuration
# Get the directory where the script is located
REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$REPO_DIR/cron_run.log"
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Navigate to repository
cd "$REPO_DIR" || exit 1

echo "=== Starting run at $(date) ===" >> "$LOG_FILE"

# 1. Pull latest changes (in case you pushed from elsewhere)
echo "Pulling latest changes..." >> "$LOG_FILE"
git pull >> "$LOG_FILE" 2>&1

# 2. Run the scraper
echo "Running scraper..." >> "$LOG_FILE"
# Ensure we use the python from the virtual environment if you have one, 
# otherwise assume system python has dependencies installed.
# Better to use absolute path to python or activate venv.
# Assuming system python for now based on your environment context.
python3 scraper.py >> "$LOG_FILE" 2>&1

# 3. Run the availability checker
echo "Running availability checker..." >> "$LOG_FILE"
python3 check_availability.py >> "$LOG_FILE" 2>&1

# 4. Deploy to Surge
echo "Deploying to Surge..." >> "$LOG_FILE"
# You need to have surge installed globally or locally
# npm install -g surge
surge . jockeblocket.surge.sh >> "$LOG_FILE" 2>&1

# 5. Commit and push changes
echo "Committing changes..." >> "$LOG_FILE"
git add data/listings.json data/deals.json data/stats.json >> "$LOG_FILE" 2>&1
git commit -m "Update data from local cron [skip ci]" >> "$LOG_FILE" 2>&1
git push >> "$LOG_FILE" 2>&1

echo "=== Finished run at $(date) ===" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"
