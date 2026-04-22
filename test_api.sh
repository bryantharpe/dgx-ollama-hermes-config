#!/bin/bash
set -e

# Load HERMES_API_KEY from the repo's .env
source /home/admin/code/hermes-config/.env

# Extract transcript content
TRANSCRIPT=$(cat /home/admin/code/hermes-config/prototype-transcript/test-transcript.txt)

# Construct JSON payload using jq
JSON_PAYLOAD=$(jq -n \
  --arg msg "/meeting-transcript-to-specs Please convert this transcript to specs:\n\n$TRANSCRIPT" \
  '{
    "model": "qwen3.6-35b:128k",
    "messages": [
      {
        "role": "user",
        "content": $msg
      }
    ]
  }')

# Send request to Hermes Agent API
curl -s -X POST http://localhost:8642/v1/chat/completions \
  -H "Authorization: Bearer $HERMES_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD"
