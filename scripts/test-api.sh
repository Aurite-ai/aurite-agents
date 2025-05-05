#!/bin/bash

# This script is used to test the API of the application using the postman collection.
# It requires an environment variable file in tests/api/main_server.postman_environment.json
# and a postman collection file in tests/api/main_server.postman_collection.json
# It also requires the postman CLI to be installed and available in the PATH.

# Start the API in the background using the start-api script from pyproject.toml
start-api &
API_PID=$! # Capture the process ID of the API
# Wait for the API to start
while ! curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; do
    echo "Waiting for API to start..."
    sleep 1
done
echo "API started"

# Run the postman collection using the postman CLI
newman run tests/api/main_server.postman_collection.json \
    -e tests/api/main_server.postman_environment.json \
    --reporters cli

echo "API tests completed"

# Shut down the API server
kill $API_PID
echo "API server shut down"
