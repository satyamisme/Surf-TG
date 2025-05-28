#!/bin/bash
# Script to run the Telegram bot, with an optional update step.

# Check if the RUN_UPDATE environment variable is set to "true"
if [ "$RUN_UPDATE" = "true" ]; then
  echo "RUN_UPDATE is set to 'true'. Attempting to update from repository..."
  python3 update.py
  # Check if update.py succeeded before proceeding (optional but good practice)
  # if [ $? -ne 0 ]; then
  #   echo "Update script failed. Exiting."
  #   exit 1
  # fi
else
  echo "RUN_UPDATE is not set to 'true' or is unset. Skipping update from repository."
fi

echo "Starting bot..."
python3 -m bot