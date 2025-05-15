#!/bin/bash

# Script to test the Weather Agent on GKE via port-forwarded curl
# and then fetch the pod logs.

# Check if pod name is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <pod-name>"
  echo "Example: $0 aurite-agents-backend-xxxxxxxxxx-yyyyy"
  exit 1
fi

POD_NAME="$1"
NAMESPACE="persona"
LOCAL_PORT="8080" # Matches your kubectl port-forward local port
API_KEY="RwkWJFhApciiUSyH3B/Ad6T46kIxbu9gtAU" # Your plain text API key

AGENT_NAME_URL_ENCODED="Weather%20Agent"
REQUEST_URL="http://localhost:${LOCAL_PORT}/agents/${AGENT_NAME_URL_ENCODED}/execute"

echo "Executing Weather Agent via curl to $REQUEST_URL..."
curl -s -X POST "$REQUEST_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "user_message": "What is the weather in San Francisco today?"
  }' \
  -o /tmp/agent_execute_response.json # Save response to a temp file

echo "" # Newline for better formatting
echo "Agent execution request sent. Response saved to /tmp/agent_execute_response.json"
echo "Waiting a few seconds for logs to populate..."
sleep 5 # Adjust if necessary

echo ""
echo "Fetching last 150 lines of logs from pod ${POD_NAME} in namespace ${NAMESPACE}..."
kubectl logs "${POD_NAME}" -n "${NAMESPACE}" --tail=150

echo ""
echo "--- Agent Execution Response (from /tmp/agent_execute_response.json) ---"
cat /tmp/agent_execute_response.json
echo ""
echo "----------------------------------------------------------------------"

echo "Script finished."
