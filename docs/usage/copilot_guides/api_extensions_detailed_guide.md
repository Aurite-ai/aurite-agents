# API Extensions Detailed Guide

**Target Audience:** Developers building REST API endpoints for direct frontend/external access.

**Purpose:** Comprehensive guide for creating, configuring, and testing API extensions.

---

## When to Use API Extensions

### ✅ Use API Extensions For:

- Simple CRUD operations (Create, Read, Update, Delete)
- Direct service/manager method wrappers
- No agent orchestration needed
- Standard REST patterns
- Stateless operations
- Frontend/external system integration

### ❌ Do NOT Use For:

- Multi-step orchestration with conditional logic
- Operations requiring agent execution
- Complex business workflows with state management
- Operations requiring tool discovery by LLMs (use MCP Server)

### Decision Guide

**Choose API Extension if:**

- Frontend needs direct HTTP access
- Operation is straightforward (get/set data)
- No LLM reasoning required
- Response time critical (no agent overhead)

**Choose MCP Server if:**

- Agents need to discover and use tools
- LLM needs to reason about parameters
- Multi-agent tool sharing needed
- See: [MCP Server Tutorial](https://aurite-ai.github.io/aurite-agents/getting-started/tutorials/06_Building_Your_Own_MCP_Server/)

**💡 Pro Tip:** You can have BOTH - API extension for frontend, MCP server for agents!

---

## File Structure

```
src/api/
├── __init__.py
└── {feature}_extension.py

# No config files needed - just set environment variable
```

---

## Real-World Example: Automotive Dealership

### Before: Custom Workflow (Unnecessary Overhead)

```python
# src/custom_workflows/gmail_get_drafts_workflow.py
class GmailGetDraftsWorkflow(BaseCustomWorkflow):
    async def run(self, initial_input, executor, session_id):
        # Parse input
        max_results = initial_input.get("max_results") if isinstance(initial_input, dict) else None

        # Call manager
        gmail_manager = GmailManager()
        drafts = await gmail_manager.get_all_drafts_async(max_results)

        return {"status": "success", "drafts": drafts}
```

**Problems:**

- Workflow overhead for simple operation
- Requires workflow configuration files
- Slower than direct API call
- No automatic OpenAPI documentation

### After: API Extension (Simple & Fast)

```python
# src/api/dealership_extension.py
from fastapi import APIRouter, Security
from aurite.bin.api import Extension
from aurite.bin.dependencies import get_api_key
from src.servers.gmail.gmail_manager import GmailManager

class DealershipExtension(Extension):
    """Automotive dealership API operations."""

    def __call__(self, app):
        router = APIRouter(prefix="/dealership", tags=["Dealership"])

        @router.get("/gmail/drafts")
        async def get_drafts(
            max_results: int = None,
            api_key: str = Security(get_api_key)
        ):
            """Get all Gmail drafts."""
            manager = GmailManager()
            return await manager.get_all_drafts_async(max_results)

        @router.post("/gmail/drafts/{draft_id}/send")
        async def send_draft(
            draft_id: str,
            api_key: str = Security(get_api_key)
        ):
            """Send a Gmail draft by ID."""
            manager = GmailManager()
            return manager.send_draft(draft_id)

        @router.get("/config")
        async def get_config(api_key: str = Security(get_api_key)):
            """Get followup configuration settings."""
            from src.servers.sqlite.sqlite_manager import SQLiteManager
            manager = SQLiteManager(db_path="data/dealership.db")
            return manager.get_followup_config()

        @router.put("/config")
        async def update_config(
            updates: dict,
            api_key: str = Security(get_api_key)
        ):
            """Update configuration settings."""
            from src.servers.sqlite.sqlite_manager import SQLiteManager
            manager = SQLiteManager(db_path="data/dealership.db")
            for key, value in updates.items():
                manager.update_followup_config(key, value)
            return {"status": "success", "updated": list(updates.keys())}

        @router.get("/plates/{plate_number}/history")
        async def get_plate_history(
            plate_number: str,
            api_key: str = Security(get_api_key)
        ):
            """Get history for a license plate."""
            from src.servers.sqlite.sqlite_manager import SQLiteManager
            manager = SQLiteManager(db_path="data/dealership.db")
            return manager.get_plate_history(plate_number)

        app.include_router(router)
```

**Benefits:**

- 🚀 Direct method calls, no overhead
- 📚 Automatic OpenAPI/Swagger docs
- 🔌 Standard REST for frontend
- 🎯 No config files needed
- ✅ Easy HTTP testing
- 🔒 Built-in API key auth

---

## Loading Extensions

### Single Extension

```bash
# Environment variable
export AURITE_API_EXTENSIONS="src.api.dealership_extension.DealershipExtension"

# Or in .env file
AURITE_API_EXTENSIONS=src.api.dealership_extension.DealershipExtension
```

### Multiple Extensions

```bash
# Comma-separated
export AURITE_API_EXTENSIONS="src.api.dealership_extension.DealershipExtension,src.api.other_extension.OtherExtension"
```

---

## Testing API Extensions

### Start API Server

```bash
aurite api
```

### Test with curl

```bash
# GET request
curl -X GET "http://localhost:8000/dealership/gmail/drafts?max_results=10" \
  -H "X-API-Key: your-api-key"

# POST request
curl -X POST "http://localhost:8000/dealership/gmail/drafts/draft_id_123/send" \
  -H "X-API-Key: your-api-key"

# GET config
curl -X GET "http://localhost:8000/dealership/config" \
  -H "X-API-Key: your-api-key"

# PUT config
curl -X PUT "http://localhost:8000/dealership/config" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"setting1": "value1", "setting2": "value2"}'
```

### View Documentation

```bash
# Swagger UI
open http://localhost:8000/api-docs

# ReDoc
open http://localhost:8000/redoc

# OpenAPI JSON
curl http://localhost:8000/openapi.json
```

---

## Advanced Pattern: Batch Operations

```python
# src/api/dealership_extension.py (continued)
from pydantic import BaseModel
from typing import List

class BatchNotificationRequest(BaseModel):
    plate_numbers: List[str]

class DealershipExtension(Extension):
    def __call__(self, app):
        router = APIRouter(prefix="/dealership", tags=["Dealership"])

        # ... other endpoints ...

        @router.post("/plates/batch-notify")
        async def batch_notify_customers(
            request: BatchNotificationRequest,
            api_key: str = Security(get_api_key)
        ):
            """Send notifications for multiple plates at once."""
            from src.servers.sqlite.sqlite_manager import SQLiteManager
            from src.servers.gmail.gmail_manager import GmailManager

            db_manager = SQLiteManager(db_path="data/dealership.db")
            gmail_manager = GmailManager()

            results = []
            for plate_number in request.plate_numbers:
                customer = db_manager.get_customer_by_plate(plate_number)
                if customer:
                    # Send notification
                    draft_id = db_manager.get_notification_draft(plate_number)
                    gmail_manager.send_draft(draft_id)
                    results.append({
                        "plate": plate_number,
                        "status": "sent",
                        "customer": customer["name"]
                    })
                else:
                    results.append({
                        "plate": plate_number,
                        "status": "not_found"
                    })

            return {
                "total": len(request.plate_numbers),
                "sent": len([r for r in results if r["status"] == "sent"]),
                "results": results
            }

        app.include_router(router)
```

### Test Batch Operation

```bash
curl -X POST "http://localhost:8000/dealership/plates/batch-notify" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "plate_numbers": ["ABC123", "XYZ789", "DEF456"]
  }'
```

---

## Advanced Pattern: Request/Response Models

```python
# src/api/dealership_extension.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PlateStatus(BaseModel):
    plate_number: str = Field(..., description="License plate number")
    status: str = Field(..., description="Current status")
    customer_name: str
    ready_date: Optional[datetime] = None

class PlateHistoryResponse(BaseModel):
    plate_number: str
    history: List[dict]
    total_events: int

class DealershipExtension(Extension):
    def __call__(self, app):
        router = APIRouter(prefix="/dealership", tags=["Dealership"])

        @router.get("/plates/{plate_number}", response_model=PlateStatus)
        async def get_plate_status(
            plate_number: str,
            api_key: str = Security(get_api_key)
        ) -> PlateStatus:
            """Get detailed status for a plate."""
            from src.servers.sqlite.sqlite_manager import SQLiteManager
            manager = SQLiteManager(db_path="data/dealership.db")
            data = manager.get_plate_status(plate_number)
            return PlateStatus(**data)

        @router.get("/plates/{plate_number}/history", response_model=PlateHistoryResponse)
        async def get_plate_history(
            plate_number: str,
            api_key: str = Security(get_api_key)
        ) -> PlateHistoryResponse:
            """Get complete history for a plate."""
            from src.servers.sqlite.sqlite_manager import SQLiteManager
            manager = SQLiteManager(db_path="data/dealership.db")
            history = manager.get_plate_history(plate_number)
            return PlateHistoryResponse(
                plate_number=plate_number,
                history=history,
                total_events=len(history)
            )

        app.include_router(router)
```

**Benefits of Pydantic models:**

- 📝 Automatic validation
- 📚 Better OpenAPI docs
- 🔒 Type safety
- 🎯 Clear contracts

---

## When to Migrate from Custom Workflows

### ✅ Migrate If:

- Workflow has no agent orchestration
- Workflow is simple pass-through to manager methods
- Frontend needs direct access
- No conditional logic or state management
- Response time is critical

### ❌ Keep as Custom Workflow If:

- Orchestrates multiple agents
- Has complex conditional logic
- Manages state across operations
- Requires business domain knowledge
- Agent reasoning adds value

### Migration Example

**Before (Custom Workflow):**

```python
class SimpleGetWorkflow(BaseCustomWorkflow):
    async def run(self, initial_input, executor, session_id):
        manager = MyManager()
        result = manager.get_data(initial_input["id"])
        return {"status": "success", "data": result}
```

**After (API Extension):**

```python
@router.get("/data/{data_id}")
async def get_data(
    data_id: str,
    api_key: str = Security(get_api_key)
):
    """Get data by ID."""
    manager = MyManager()
    return manager.get_data(data_id)
```

---

## Development Workflow

### Step 1: Create Extension File

```python
# src/api/my_extension.py
from fastapi import APIRouter, Security
from aurite.bin.api import Extension
from aurite.bin.dependencies import get_api_key

class MyExtension(Extension):
    """My custom API extension."""

    def __call__(self, app):
        router = APIRouter(prefix="/my-feature", tags=["MyFeature"])

        @router.get("/items")
        async def get_items(api_key: str = Security(get_api_key)):
            """Get all items."""
            # Implementation
            return {"items": []}

        app.include_router(router)
```

### Step 2: Set Environment Variable

```bash
export AURITE_API_EXTENSIONS="src.api.my_extension.MyExtension"
```

### Step 3: Start API Server

```bash
aurite api
```

### Step 4: Test Endpoints

```bash
# Test with curl
curl -X GET "http://localhost:8000/my-feature/items" \
  -H "X-API-Key: your-api-key"

# Or view in browser
open http://localhost:8000/api-docs
```

### Step 5: Update Frontend

```typescript
// frontend code
const response = await fetch("http://localhost:8000/my-feature/items", {
  headers: {
    "X-API-Key": process.env.AURITE_API_KEY,
  },
});
const data = await response.json();
```

---

## Best Practices

### 1. Use Dependency Injection

```python
from fastapi import Depends

def get_db_manager():
    """Dependency for database manager."""
    return SQLiteManager(db_path="data/app.db")

@router.get("/customers")
async def get_customers(
    api_key: str = Security(get_api_key),
    db: SQLiteManager = Depends(get_db_manager)
):
    """Get all customers."""
    return db.get_all_customers()
```

### 2. Handle Errors Consistently

```python
from fastapi import HTTPException

@router.get("/customer/{customer_id}")
async def get_customer(
    customer_id: str,
    api_key: str = Security(get_api_key)
):
    """Get customer by ID."""
    try:
        manager = CustomerManager()
        customer = manager.get_customer(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

### 3. Use Path and Query Parameters

```python
from fastapi import Query

@router.get("/customers")
async def get_customers(
    status: str = Query("active", description="Filter by status"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Security(get_api_key)
):
    """Get customers with filtering and pagination."""
    manager = CustomerManager()
    return manager.get_customers(
        status=status,
        limit=limit,
        offset=offset
    )
```

### 4. Document Thoroughly

```python
@router.post("/orders", status_code=201)
async def create_order(
    order: OrderCreate,
    api_key: str = Security(get_api_key)
) -> Order:
    """
    Create a new order.

    **Parameters:**
    - order: Order details

    **Returns:**
    - Created order with ID

    **Raises:**
    - 400: Invalid order data
    - 404: Customer not found
    """
    manager = OrderManager()
    return manager.create_order(order)
```

---

## Comparison: API Extension vs MCP Server

### Same Functionality, Different Interfaces

**For Agents (MCP Server):**

```python
# src/servers/customer/customer_server.py
@mcp.tool()
async def get_customer(customer_id: str) -> dict:
    """Get customer details.

    Args:
        customer_id: Unique customer identifier

    Returns:
        Customer details with contact info
    """
    manager = CustomerManager()
    return manager.get_customer(customer_id)
```

**For Frontend (API Extension):**

```python
# src/api/customer_extension.py
@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    api_key: str = Security(get_api_key)
):
    """Get customer details."""
    manager = CustomerManager()
    return manager.get_customer(customer_id)
```

**Both use the same manager!**

```python
# src/servers/customer/customer_manager.py
class CustomerManager:
    def get_customer(self, customer_id: str) -> dict:
        # Shared business logic
        pass
```

### When to Have Both

✅ **Have both when:**

- Functionality useful for both agents and frontend
- Agents need to discover/reason about operations
- Frontend needs direct, fast access
- Example: Customer lookup, order management

❌ **Only MCP Server when:**

- Only agents need this functionality
- Requires LLM reasoning
- Not user-facing
- Example: Complex data analysis

❌ **Only API Extension when:**

- Only frontend needs this
- Simple CRUD operation
- Agents don't need it
- Example: UI configuration

---

## Summary

**API Extensions are ideal for:**

- ✅ Simple, direct operations
- ✅ Frontend integration
- ✅ Fast response times
- ✅ Standard REST patterns

**Key benefits:**

- 🚀 Performance - No agent overhead
- 📚 Auto-documentation - OpenAPI/Swagger
- 🔌 Easy integration - Standard HTTP
- 🎯 Simplicity - Just Python code
- ✅ Easy testing - curl/Postman/browser
- 🔒 Built-in auth - API key support

**Remember:**

- Can coexist with MCP Servers
- Share manager classes for DRY code
- Choose based on access pattern (frontend vs agents)

**Related Guides:**

- [Main Development Guide](aurite_agents_dev_guide.md)
- [API Reference](https://aurite-ai.github.io/aurite-agents/usage/api_reference/)
- [Example Extension Code](https://aurite-ai.github.io/aurite-agents/usage/example_extension/)
