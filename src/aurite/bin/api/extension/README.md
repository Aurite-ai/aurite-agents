# Aurite API Extension System

This directory contains the extension system for the Aurite API, allowing users to add custom endpoints to the built-in API server.

## Architecture

```
extension/
├── __init__.py          # Public API exports
├── extension.py         # Base Extension class (ABC)
├── factory.py          # ExtensionFactory for dynamic loading
├── application.py      # Global Aurite instance access
└── README.md           # This file
```

## Components

### Extension (extension.py)

Abstract base class that all extensions must inherit from. Defines the contract for extension registration.

### ExtensionFactory (factory.py)

Provides dynamic loading of extension classes from module paths. Handles:

- Module import
- Class resolution
- Type validation

### Application State (application.py)

Manages global access to the Aurite instance for extensions. Provides:

- `set(aurite)` - Set the instance (called during lifespan)
- `get()` - Get the instance (called by extensions)

## Usage Flow

1. **Environment Variable Set:**

   ```bash
   export AURITE_API_EXTENSIONS="my_ext.MyExtension"
   ```

2. **API Startup:**

   - FastAPI lifespan initializes Aurite
   - `application.set(aurite)` called
   - Extensions parsed from env var
   - Each extension loaded via ExtensionFactory
   - Extension instance created and called with app

3. **Extension Execution:**
   - Extension's `__call__` method invoked
   - Creates APIRouter and defines endpoints
   - Registers router with FastAPI app
   - Endpoints can access Aurite via `application.get()`

## Design Decisions

1. **Separate Directory:** Keeps extension system organized and maintainable
2. **Global State:** Simplifies access to Aurite for extension developers
3. **Factory Pattern:** Enables dynamic loading with proper error handling
4. **Environment Variable:** Non-invasive, easy to configure
5. **txtai-inspired:** Familiar pattern for users of similar frameworks

## Security

- Extensions run with full API privileges
- No sandboxing - extensions are trusted code
- Use `get_api_key` dependency for authentication
- CORS settings inherited from main API

## Error Handling

- Invalid extensions logged but don't crash API
- Other extensions continue loading if one fails
- Detailed error messages in logs
- Type checking prevents common mistakes

## Testing

See `tests/unit/bin/api/test_extension.py` for unit tests covering:

- Extension registration
- Factory loading
- Error cases
- Multiple extensions

## Documentation

For user-facing documentation, see:

- `docs/usage/api_extensions.md` - Complete guide
- `docs/usage/example_extension.py` - Working example
