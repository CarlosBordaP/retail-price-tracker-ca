#!/bin/bash

# Absolute path to the project directory
PROJECT_DIR="/Users/carlosborda/Documents/Python/Learning/scraping"
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"

# Navigate to the project directory
cd "$PROJECT_DIR"

# Run the scraper
# We use --ui-mode to ensure it updates the JSON state for the web dashboard if it's running
"$PYTHON_BIN" main.py --ui-mode >> logs/automation.log 2>&1

echo "Scraper execution finished at $(date)" >> logs/automation.log
