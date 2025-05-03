# Define the default shell for commands
set shell := ["bash", "-c"]

# Run Postman API tests
test-api:
    newman run tests/api/main_server.postman_collection.json \
        -e tests/api/main_server.postman_environment.json \
        --reporters cli

# Run tests with a specific marker
test-marker marker:
    pytest -m "{{marker}}"

# Run tests for the host
test-host:
    pytest -m "host" --disable-warnings

# Examples for running tests with specific markers
test-integration:
    just test-marker integration

test-unit:
    just test-marker unit

test-e2e:
    just test-marker e2e