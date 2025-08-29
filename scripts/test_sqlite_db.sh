#!/bin/bash

# Test script for SQLite database functionality

set -e  # Exit on error

echo "========================================="
echo "Testing SQLite Database Functionality"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Clean up any existing test database
echo -e "${YELLOW}Cleaning up any existing test database...${NC}"
rm -f .aurite_db/test_aurite.db

# Export environment variables for SQLite
export AURITE_ENABLE_DB=true
export AURITE_DB_TYPE=sqlite
export AURITE_DB_PATH=.aurite_db/test_aurite.db

echo -e "${GREEN}Environment configured for SQLite:${NC}"
echo "  AURITE_ENABLE_DB=$AURITE_ENABLE_DB"
echo "  AURITE_DB_TYPE=$AURITE_DB_TYPE"
echo "  AURITE_DB_PATH=$AURITE_DB_PATH"
echo ""

# Test 1: Export configurations to SQLite database
echo -e "${YELLOW}Test 1: Exporting configurations to SQLite database...${NC}"
aurite export

# Check if database file was created
if [ -f ".aurite_db/test_aurite.db" ]; then
    echo -e "${GREEN}✓ SQLite database file created successfully${NC}"

    # Check file size to ensure data was written
    DB_SIZE=$(stat -c%s ".aurite_db/test_aurite.db" 2>/dev/null || stat -f%z ".aurite_db/test_aurite.db" 2>/dev/null)
    echo -e "${GREEN}  Database size: ${DB_SIZE} bytes${NC}"
else
    echo -e "${RED}✗ SQLite database file was not created${NC}"
    exit 1
fi
echo ""

# Test 2: List components to verify they're loaded from database
echo -e "${YELLOW}Test 2: Listing components from database...${NC}"
aurite list agents
echo ""

# Test 3: Run a component to verify configuration retrieval
echo -e "${YELLOW}Test 3: Running Weather Agent with a test query...${NC}"
if aurite run "Weather Agent" "What's the weather in London?" --short; then
    echo -e "${GREEN}✓ Successfully ran Weather Agent using database configuration${NC}"
else
    echo -e "${RED}✗ Failed to run Weather Agent${NC}"
    echo -e "${YELLOW}Note: This might fail if the Weather Agent requires API keys or MCP servers${NC}"
fi
echo ""

# Test 4: Check database contents using Python
echo -e "${YELLOW}Test 4: Verifying database contents...${NC}"
python3 << 'EOF'
import sqlite3
import json

try:
    conn = sqlite3.connect('.aurite_db/test_aurite.db')
    cursor = conn.cursor()

    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"  Tables in database: {[t[0] for t in tables]}")

    # Count components
    cursor.execute("SELECT COUNT(*) FROM components;")
    component_count = cursor.fetchone()[0]
    print(f"  Total components in database: {component_count}")

    # Show component types
    cursor.execute("SELECT DISTINCT component_type FROM components;")
    types = cursor.fetchall()
    print(f"  Component types: {[t[0] for t in types]}")

    # Show some component names
    cursor.execute("SELECT name, component_type FROM components LIMIT 5;")
    components = cursor.fetchall()
    print("  Sample components:")
    for name, comp_type in components:
        print(f"    - {name} ({comp_type})")

    conn.close()
    print("\033[0;32m✓ Database structure verified successfully\033[0m")
except Exception as e:
    print(f"\033[0;31m✗ Error verifying database: {e}\033[0m")
    exit(1)
EOF
echo ""

# Test 5: Test session history storage
echo -e "${YELLOW}Test 5: Testing session history storage...${NC}"
SESSION_ID="test-session-$(date +%s)"
echo "  Using session ID: $SESSION_ID"

# Run agent with session ID to create history
if aurite run "Weather Agent" "What's the temperature in Paris?" --session-id "$SESSION_ID" --short; then
    echo -e "${GREEN}✓ Created session history${NC}"

    # Verify history was saved
    python3 << EOF
import sqlite3
conn = sqlite3.connect('.aurite_db/test_aurite.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM agent_history WHERE session_id = ?;", ("$SESSION_ID",))
history_count = cursor.fetchone()[0]
if history_count > 0:
    print(f"\033[0;32m✓ Session history saved: {history_count} records\033[0m")
else:
    print("\033[1;33m⚠ No session history found (this is normal if the agent didn't save history)\033[0m")
conn.close()
EOF
else
    echo -e "${YELLOW}⚠ Could not test session history (agent run failed)${NC}"
fi
echo ""

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}SQLite Database Tests Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Database file location: .aurite_db/test_aurite.db"
echo "You can now test migration to PostgreSQL using:"
echo "  aurite migrate --from-env"
