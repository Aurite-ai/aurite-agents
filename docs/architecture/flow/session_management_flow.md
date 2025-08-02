# Session Management Flow

This document explains the session management flows used by the SessionManager and CacheManager to handle conversation history, execution results, and session lifecycle across the Aurite framework.

## Overview

The session management system provides persistent storage and retrieval of execution sessions through a two-tier architecture: the SessionManager provides high-level session operations while the CacheManager handles low-level file-based storage with in-memory caching. Sessions support both agent conversations and workflow executions with comprehensive metadata tracking.

## Core Session Operations

The session management system supports four primary operations with different flows based on the operation type and session characteristics.

=== "Session Creation Flow"

    **Objective**: Create new sessions with proper metadata initialization and storage backend setup.

    ```mermaid
    flowchart TD
        A[Session Creation Request] --> B[Session ID Generation]
        B --> C[Metadata Extraction]
        C --> D[Session Data Assembly]
        D --> E[CacheManager Storage]
        E --> F[In-Memory Cache Update]
        F --> G[File Persistence]
        G --> H[Session Created]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style H fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style E fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style G fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    ```

    **Phase 1: Session Data Assembly**
    ```python
    # SessionManager._save_result
    now = datetime.utcnow().isoformat()
    existing_data = self._cache.get_result(session_id) or {}

    metadata = self._extract_metadata(execution_result)
    session_data = {
        "session_id": session_id,
        "base_session_id": base_session_id,
        "execution_result": execution_result,
        "result_type": result_type,  # "agent" or "workflow"
        "created_at": existing_data.get("created_at", now),
        "last_updated": now,
        **metadata,  # name, message_count, agents_involved
    }
    ```

    **Phase 2: Metadata Extraction**
    ```python
    # Different extraction logic based on result type
    if is_workflow:
        name = execution_result.get("workflow_name")
        # Extract message count from all step results
        for step in execution_result.get("step_results", []):
            if "conversation_history" in step_result:
                message_count += len(step_result.get("conversation_history", []))

        # Track agents involved in workflow
        agent_session_id = step_result.get("session_id")
        agent_name_in_step = step_result.get("agent_name")
        if agent_session_id and agent_name_in_step:
            agents_involved[agent_session_id] = agent_name_in_step
    else:  # Agent result
        name = execution_result.get("agent_name")
        message_count = len(execution_result.get("conversation_history", []))
    ```

    **Phase 3: Storage Persistence**
    ```python
    # CacheManager.save_result
    # Update in-memory cache first
    self._result_cache[session_id] = session_data

    # Persist to disk with error handling
    session_file = self._get_session_file(session_id)
    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=2)
    ```

    **Session File Structure**:
    ```json
    {
      "session_id": "agent-a1b2c3d4",
      "base_session_id": "agent-a1b2c3d4",
      "execution_result": {
        "status": "success",
        "conversation_history": [...],
        "agent_name": "weather_agent"
      },
      "result_type": "agent",
      "created_at": "2025-01-09T19:08:48.959750",
      "last_updated": "2025-01-09T19:08:52.329089",
      "name": "weather_agent",
      "message_count": 4
    }
    ```

=== "Session Retrieval Flow"

    **Objective**: Retrieve session data with support for partial ID matching and metadata validation.

    ```mermaid
    flowchart TD
        A[Session Retrieval Request] --> B[Direct ID Lookup]
        B --> C{Session Found?}
        C -->|Yes| D[Return Session Data]
        C -->|No| E[Base Session ID Search]
        E --> F{Matches Found?}
        F -->|None| G[Return Not Found]
        F -->|One| H[Return Matched Session]
        F -->|Multiple| I[Primary Session Resolution]
        I --> J{Primary Found?}
        J -->|Yes| H
        J -->|No| K[Return Ambiguous Error]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style D fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style H fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style G fill:#F44336,stroke:#D32F2F,stroke-width:2px,color:#fff
        style K fill:#F44336,stroke:#D32F2F,stroke-width:2px,color:#fff
    ```

    **Phase 1: Direct Lookup**
    ```python
    # SessionManager.get_full_session_details
    execution_result = self.get_session_result(session_id)
    metadata_model = self.get_session_metadata(session_id)

    if execution_result is None:
        # Proceed to base session ID search
        all_sessions_result = self.get_sessions_list(limit=10000, offset=0)
        matching_sessions = [
            s for s in all_sessions_result["sessions"]
            if s.base_session_id and s.base_session_id == session_id
        ]
    ```

    **Phase 2: Cache Lookup with Disk Fallback**
    ```python
    # CacheManager.get_result
    # Check memory cache first
    if session_id in self._result_cache:
        return self._result_cache[session_id]

    # Try to load from disk if not in memory
    session_file = self._get_session_file(session_id)
    if session_file.exists():
        with open(session_file, "r") as f:
            data = json.load(f)
        self._result_cache[session_id] = data
        return data
    ```

    **Phase 3: Primary Session Resolution**
    ```python
    # Handle multiple matches by finding primary session
    if len(matching_sessions) > 1:
        # Primary session doesn't have suffix like -0, -1
        primary_match = [
            s for s in matching_sessions
            if not (s.session_id[-2] == "-" and s.session_id[-1].isdigit())
        ]
        if len(primary_match) == 1:
            matched_session_id = primary_match[0].session_id
        else:
            # Ambiguous case - return error
            session_ids = [s.session_id for s in matching_sessions]
            raise HTTPException(
                status_code=400,
                detail=f"Ambiguous partial ID '{session_id}'. Multiple sessions found: {session_ids[:5]}"
            )
    ```

=== "Session Update Flow"

    **Objective**: Update existing sessions with new conversation messages or execution results while preserving metadata.

    ```mermaid
    flowchart TD
        A[Session Update Request] --> B[Load Existing Session]
        B --> C[Update Session Data]
        C --> D[Refresh Metadata]
        D --> E[Update Timestamps]
        E --> F[Cache Update]
        F --> G[File Persistence]
        G --> H[Session Updated]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style H fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style C fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style D fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    ```

    **Phase 1: Message Addition (Streaming)**
    ```python
    # SessionManager.add_message_to_history
    existing_history = self.get_session_history(session_id) or []
    updated_history = existing_history + [message]
    self.save_conversation_history(session_id, updated_history, agent_name)
    ```

    **Phase 2: Complete Result Update**
    ```python
    # SessionManager.save_agent_result / save_workflow_result
    def _save_result(self, session_id: str, execution_result: Dict[str, Any],
                     result_type: str, base_session_id: Optional[str] = None):
        now = datetime.utcnow().isoformat()
        existing_data = self._cache.get_result(session_id) or {}

        # Preserve creation timestamp, update last_updated
        session_data = {
            "session_id": session_id,
            "base_session_id": base_session_id,
            "execution_result": execution_result,
            "result_type": result_type,
            "created_at": existing_data.get("created_at", now),  # Preserve original
            "last_updated": now,  # Always update
            **self._extract_metadata(execution_result),
        }
        self._cache.save_result(session_id, session_data)
    ```

    **Phase 3: Metadata Refresh**
    ```python
    # Automatic metadata extraction on update
    def _extract_metadata(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        message_count = 0
        name = None
        agents_involved: Dict[str, str] = {}
        is_workflow = "step_results" in execution_result

        # Extract current metadata from execution result
        if is_workflow:
            name = execution_result.get("workflow_name")
            # Recalculate message count from all steps
            for step in execution_result.get("step_results", []):
                if "conversation_history" in step_result:
                    message_count += len(step_result.get("conversation_history", []))
        else:
            name = execution_result.get("agent_name")
            message_count = len(execution_result.get("conversation_history", []))

        return {"name": name, "message_count": message_count, "agents_involved": agents_involved}
    ```

=== "Session Deletion Flow"

    **Objective**: Delete sessions with cascading cleanup for workflow hierarchies and parent-child relationships.

    ```mermaid
    flowchart TD
        A[Session Deletion Request] --> B[Load Session Metadata]
        B --> C{Session Type?}
        C -->|Workflow| D[Find Child Agent Sessions]
        C -->|Child Agent| E[Update Parent Workflow]
        C -->|Standalone Agent| F[Direct Deletion]
        D --> G[Delete Child Sessions]
        G --> F
        E --> H[Remove from Parent Agents List]
        H --> F
        F --> I[Delete from Cache]
        I --> J[Delete File]
        J --> K[Session Deleted]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style K fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style D fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style E fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style G fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    ```

    **Phase 1: Workflow Cascade Deletion**
    ```python
    # SessionManager.delete_session
    session_to_delete = self.get_session_metadata(session_id)

    # Case 1: Deleting a workflow - cascade to child agents
    if session_to_delete.is_workflow:
        all_sessions = self.get_sessions_list(limit=10000)["sessions"]
        child_agent_sessions = [
            s for s in all_sessions
            if not s.is_workflow
            and s.base_session_id == session_to_delete.base_session_id
            and s.session_id != session_to_delete.session_id
        ]
        for child in child_agent_sessions:
            self._cache.delete_session(child.session_id)
            logger.info(f"Cascading delete: removed child agent session '{child.session_id}'")
    ```

    **Phase 2: Parent Workflow Update**
    ```python
    # Case 2: Deleting a child agent - update parent workflow
    elif session_to_delete.base_session_id and session_to_delete.base_session_id != session_id:
        all_sessions = self.get_sessions_list(limit=10000)["sessions"]
        parent_workflows = [
            s for s in all_sessions
            if s.is_workflow and s.base_session_id == session_to_delete.base_session_id
        ]
        for parent in parent_workflows:
            parent_data = self._cache.get_result(parent.session_id)
            if parent_data and parent_data.get("agents_involved") and session_id in parent_data["agents_involved"]:
                del parent_data["agents_involved"][session_id]
                self._cache.save_result(parent.session_id, parent_data)
    ```

    **Phase 3: Physical Deletion**
    ```python
    # CacheManager.delete_session
    # Remove from memory cache
    session_exists_in_mem = self._result_cache.pop(session_id, None) is not None

    # Remove from disk
    session_file = self._get_session_file(session_id)
    session_exists_on_disk = session_file.exists()
    if session_exists_on_disk:
        session_file.unlink()

    return session_exists_in_mem or session_exists_on_disk
    ```

## Session Lifecycle Management

### Session ID Generation Patterns

The session management system supports different ID generation patterns based on execution context:

**Agent Sessions**:

- **Standalone**: `agent-{uuid4().hex[:8]}` (e.g., `agent-a1b2c3d4`)
- **User Provided**: Prefixed with `agent-` if not already prefixed
- **Workflow Context**: Uses workflow's base session ID without additional prefixing

**Workflow Sessions**:

- **Standalone**: `workflow-{uuid4().hex[:8]}` (e.g., `workflow-x9y8z7w6`)
- **User Provided**: Prefixed with `workflow-` if not already prefixed
- **Base Session Tracking**: Original session ID preserved for step coordination

### Session Metadata Validation

**Pydantic Model Validation**:

```python
# SessionManager._validate_and_transform_metadata
def _validate_and_transform_metadata(self, session_data: Dict[str, Any]) -> SessionMetadata:
    session_id = session_data.get("session_id", "N/A")
    result_type = session_data.get("result_type")
    is_workflow = result_type == "workflow"

    # Extract name with fallback handling
    name = session_data.get("name")
    if not name:
        type_str = "Workflow" if is_workflow else "Agent"
        logger.warning(f"{type_str} session '{session_id}' is missing a name. Using placeholder.")
        name = f"Untitled {type_str} ({session_id[:8]})"

    return SessionMetadata(
        session_id=session_id,
        name=name,
        created_at=session_data.get("created_at"),
        last_updated=session_data.get("last_updated"),
        message_count=session_data.get("message_count"),
        is_workflow=is_workflow,
        agents_involved=session_data.get("agents_involved"),
        base_session_id=session_data.get("base_session_id"),
    )
```

**Backwards Compatibility**:

```python
# Handle legacy sessions without message_count
if "message_count" not in session_data:
    metadata = self._extract_metadata(session_data.get("execution_result", {}))
    session_data.update(metadata)
```

### Session Filtering and Pagination

**Query Processing**:

```python
# SessionManager.get_sessions_list
def get_sessions_list(self, agent_name: Optional[str] = None,
                     workflow_name: Optional[str] = None,
                     limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    # Load and validate all sessions
    all_validated_sessions: List[SessionMetadata] = []
    cache_dir = self._cache.get_cache_dir()

    for session_file in cache_dir.glob("*.json"):
        try:
            with open(session_file, "r") as f:
                session_data = json.load(f)

            # Ensure backwards compatibility
            if "message_count" not in session_data:
                metadata = self._extract_metadata(session_data.get("execution_result", {}))
                session_data.update(metadata)

            model = self._validate_and_transform_metadata(session_data)
            all_validated_sessions.append(model)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Skipping invalid session file: {session_file}")
```

**Filtering Logic**:

```python
# Apply filtering based on request parameters
filtered_sessions: List[SessionMetadata] = []
if workflow_name:
    # Only return parent workflow sessions
    filtered_sessions = [s for s in all_validated_sessions
                        if s.is_workflow and s.name == workflow_name]
elif agent_name:
    # Only return direct agent runs (not workflow steps)
    filtered_sessions = [s for s in all_validated_sessions
                        if not s.is_workflow and s.name == agent_name]
else:
    filtered_sessions = all_validated_sessions

# Sort by last_updated descending and apply pagination
filtered_sessions.sort(key=lambda x: x.last_updated or "", reverse=True)
total = len(filtered_sessions)
paginated_sessions = filtered_sessions[offset:offset + limit]
```

## Storage Architecture

### Two-Tier Storage Design

**SessionManager (High-Level)**:

- Provides business logic for session operations
- Handles metadata extraction and validation
- Manages session relationships and cascading operations
- Implements filtering, pagination, and search functionality

**CacheManager (Low-Level)**:

- Handles file I/O operations with error handling
- Maintains in-memory cache for performance
- Manages session file naming and sanitization
- Provides atomic read/write operations

### File System Organization

**Cache Directory Structure**:

```
.aurite_cache/
├── agent-a1b2c3d4.json          # Agent session
├── workflow-x9y8z7w6.json       # Workflow session
├── workflow-x9y8z7w6-0.json     # Workflow step 0
├── workflow-x9y8z7w6-1.json     # Workflow step 1
└── ...
```

**Session ID Sanitization**:

```python
# CacheManager._get_session_file
def _get_session_file(self, session_id: str) -> Path:
    # Sanitize session_id to prevent directory traversal
    safe_session_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return self._cache_dir / f"{safe_session_id}.json"
```

### Performance Optimizations

**In-Memory Caching**:

- All sessions loaded into memory on startup
- Memory cache updated immediately on write operations
- Disk operations performed asynchronously when possible

**Lazy Loading**:

- Sessions loaded from disk only when not in memory cache
- Failed disk reads don't prevent memory cache operations
- Graceful degradation on file system errors

## Cleanup and Retention

### Retention Policy Implementation

**Age-Based Cleanup**:

```python
# SessionManager.cleanup_old_sessions
cutoff_date = datetime.utcnow() - timedelta(days=days)

for session in all_sessions:
    last_updated_str = session.last_updated
    if last_updated_str:
        last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00")).replace(tzinfo=None)
        if last_updated < cutoff_date:
            sessions_to_delete.add(session.session_id)
```

**Count-Based Cleanup**:

```python
# Keep only the most recent max_sessions
excess_count = len(sessions_kept) - max_sessions
if excess_count > 0:
    # Sessions already sorted oldest to newest
    for i in range(excess_count):
        sessions_to_delete.add(sessions_kept[i].session_id)
```

**Cascading Cleanup**:

- Workflow deletion automatically removes child agent sessions
- Parent workflow metadata updated when child agents are deleted
- Orphaned sessions cleaned up during retention policy execution

## Integration with AuriteEngine

### Session Creation Integration

**Agent Execution**:

```python
# AuriteEngine integration points
if agent_instance.config.include_history and final_session_id and self._session_manager:
    self._session_manager.save_agent_result(
        session_id=final_session_id,
        agent_result=run_result,
        base_session_id=final_base_session_id
    )
```

**Workflow Execution**:

```python
# Workflow result persistence
if result.session_id and self._session_manager:
    self._session_manager.save_workflow_result(
        session_id=result.session_id,
        workflow_result=result,
        base_session_id=base_session_id
    )
```

### History Loading Integration

**Pre-Execution History Loading**:

```python
# AuriteEngine._prepare_agent_for_run
if effective_include_history and session_id and self._session_manager:
    history = self._session_manager.get_session_history(session_id)
    if history:
        initial_messages.extend(history)

# Immediate message addition for streaming
self._session_manager.add_message_to_history(
    session_id=session_id,
    message=current_user_message,
    agent_name=agent_name,
)
```

## References

- **Implementation**: `src/aurite/lib/storage/sessions/session_manager.py` - Main SessionManager implementation
- **Storage Backend**: `src/aurite/lib/storage/sessions/cache_manager.py` - CacheManager file operations
- **Data Models**: `src/aurite/lib/models/api/responses.py` - Session metadata and response models
- **API Integration**: `src/aurite/bin/api/routes/execution_routes.py` - Session management endpoints
- **Engine Integration**: [AuriteEngine Execution Flow](aurite_engine_execution_flow.md) - Session integration patterns
