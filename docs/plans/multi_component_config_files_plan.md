# Implementation Plan: Multi-Component Configuration Files

**Objective:** Modify the system to allow component configuration files (for clients, agents, LLMs, simple workflows, custom workflows) to contain a JSON array of individual component definitions. Each component in the array will be registered in the `ComponentManager`. Adapt the API for viewing configuration file content to return the raw file content. Implement functionality to save/update files containing arrays of components.

## Phase 1: Backend - `ComponentManager` Update (Loading)

**Target File:** `src/config/component_manager.py`

1.  **Modify `_parse_component_file(self, file_path: Path, component_type_key: str)` method:**
    *   Change the method to return a `List[BaseModel]` (list of parsed Pydantic models).
    *   Read the content of `file_path`.
    *   Attempt to decode the JSON.
    *   **If JSON decoding fails:** Log an error and return an empty list.
    *   **If JSON decoding succeeds:**
        *   Check if the root of the parsed JSON is a list or an object.
        *   **If root is an object:**
            *   Attempt to parse it into the `COMPONENT_META[component_type_key].model_class`.
            *   If parsing succeeds, return a list containing the single parsed model.
            *   If parsing fails, log an error (including Pydantic validation details) and return an empty list.
        *   **If root is a list:**
            *   Initialize `parsed_models: List[BaseModel] = []`.
            *   Iterate through each `item_data` in the JSON list:
                *   Attempt to parse `item_data` into the `COMPONENT_META[component_type_key].model_class`.
                *   If parsing succeeds, add the parsed model to `parsed_models`.
                *   If parsing fails, log an error for this specific item (including Pydantic validation details, item index, and filename) but continue to the next item.
            *   Return `parsed_models`.
    *   Ensure all path resolutions within component models (e.g., `server_path`) are handled correctly as they are now (e.g., by `resolve_path_fields` if called within `_parse_component_file` or before model instantiation).

2.  **Modify `_load_components_from_directory(self, component_type_key: str)` method:**
    *   This method iterates through files in a component directory.
    *   For each file, it calls `parsed_models = self._parse_component_file(file_path, component_type_key)`.
    *   It then iterates through `model` in `parsed_models`:
        *   Retrieve the `id_field_name` from `COMPONENT_META[component_type_key].id_field_name`.
        *   Get the `component_id = getattr(model, id_field_name)`.
        *   If `component_id` is already in `self.component_configs[component_type_key]`, log a warning about duplicate component ID (specifying both filenames if possible, or at least the new one causing conflict) and skip adding this duplicate. The first one loaded wins.
        *   Otherwise, store the model: `self.component_configs[component_type_key][component_id] = model`.
        *   Log the successful loading of this individual component.

## Phase 2: Backend - API Endpoint Update (Viewing)

**Target File:** `src/bin/api/routes/config_api.py`

1.  **Modify `get_config_file(component_type: str, filename: str, ...)` endpoint:**
    *   Change the `response_model` from `dict` to `Any`.
    *   The primary purpose of this endpoint will shift to returning the raw, parsed JSON content of the file, whether it's a single object or an array of objects.
    *   **Logic:**
        *   Construct the full path to the file using `COMPONENT_TYPES_DIRS` and the provided `filename`.
        *   Validate `component_type`.
        *   Check if `file_path` exists. If not, raise `HTTPException` (404).
        *   Read the file's text content.
        *   Attempt to `json.loads()` the content.
        *   If `json.JSONDecodeError` occurs, raise `HTTPException` (500 or 400).
        *   Return the successfully parsed Python object/list.
    *   Remove the part where it calls `cm.get_component_config()`.

## Phase 3: Backend - `ComponentManager` and API Update (Saving/Creating Multi-Component Files)

**Target File 1: `src/config/component_manager.py`**

1.  **New Method: `save_components_to_file(self, component_type_key: str, components_data: List[Union[Dict[str, Any], BaseModel]], filename: str, overwrite: bool = True) -> List[BaseModel]`**
    *   **Input:** `component_type_key`, a list of component data (`components_data`), the target `filename`, and an `overwrite` flag.
    *   **Validation & Path Resolution (per item):**
        *   Get `model_class` and `id_field_name` from `COMPONENT_META[component_type_key]`.
        *   Initialize `validated_models: List[BaseModel] = []`.
        *   Iterate through each `item_data` in `components_data`:
            *   If `item_data` is a dict, call `self._resolve_paths(item_data.copy(), model_class)`. Then validate into `model_instance = model_class(**resolved_item_data)`.
            *   If `item_data` is a `BaseModel` instance, dump it, resolve paths, then re-validate: `temp_dict = self._resolve_paths(item_data.model_dump(mode="json"), model_class); model_instance = model_class(**temp_dict)`.
            *   If validation fails for an item, log an error and skip that item (or decide on stricter error handling, e.g., fail the whole save). For now, skip and log.
            *   Add successfully validated `model_instance` to `validated_models`.
    *   **File Path Construction:**
        *   `component_dir = self.config_base_dir / COMPONENT_META[component_type_key].directory_name` (assuming `directory_name` is part of `COMPONENT_META` or use `COMPONENT_TYPES_DIRS`).
        *   `file_path = component_dir / filename`.
        *   Ensure `component_dir` exists (`mkdir(parents=True, exist_ok=True)`).
    *   **Overwrite Check:** If `not overwrite` and `file_path.exists()`, raise `FileExistsError`.
    *   **Data Preparation for Save:**
        *   `data_to_save_list = []`
        *   For each `model` in `validated_models`:
            *   Call `self._relativize_paths(model.model_dump(mode="json"), model_class)` to prepare it for saving.
            *   Add the result to `data_to_save_list`.
    *   **File Writing:**
        *   `with open(file_path, "w") as f: json.dump(data_to_save_list, f, indent=2)`
    *   **In-Memory Store Update:**
        *   For each `model` in `validated_models`:
            *   `component_id = getattr(model, id_field_name)`.
            *   `self.component_configs[component_type_key][component_id] = model`. (This updates or adds the component).
    *   Log success, including the number of components saved to the file.
    *   Return `validated_models`.

**Target File 2: `src/bin/api/routes/config_api.py`**

1.  **Modify `create_config_file` (POST `/configs/{component_type}/{filename:path}`) endpoint:**
    *   The `ConfigContent` model's `content: Any` field already allows lists or dicts.
    *   **If `isinstance(config_body.content, dict)`:**
        *   (Current logic) Call `cm.create_component_file(cm_component_type, config_payload, overwrite=False)`. This uses `save_component_config` which saves a single component to a file named after its *internal ID*.
        *   **Consideration:** If `filename` from path differs from `internal_id.json`, this might be confusing. The current `cm.create_component_file` (and `save_component_config`) saves based on internal ID. If the intent of `POST .../{filename}` is to strictly use `filename`, then `cm.create_component_file` might need adjustment or a different method call. For now, assume it saves as `internal_id.json`.
    *   **If `isinstance(config_body.content, list)`:**
        *   Call `saved_models = cm.save_components_to_file(cm_component_type, config_body.content, filename, overwrite=False)`.
        *   Return a success response, perhaps `[model.model_dump(mode="json") for model in saved_models]`.
    *   Remove the previous `HTTPException` for non-dict content if implementing list saving.

2.  **Modify `update_config_file` (PUT `/configs/{component_type}/{filename:path}`) endpoint:**
    *   **If `isinstance(config_body.content, dict)`:**
        *   (Current logic) Call `cm.save_component_config(cm_component_type, config_payload)`. The `config_payload` should have its ID field aligned with `_extract_component_id(filename)` for `save_component_config` to update the correct file.
    *   **If `isinstance(config_body.content, list)`:**
        *   Call `saved_models = cm.save_components_to_file(cm_component_type, config_body.content, filename, overwrite=True)`.
        *   Return a success response, perhaps `[model.model_dump(mode="json") for model in saved_models]`.
    *   Remove the previous `HTTPException` for non-dict content if implementing list saving.

## Phase 4: Documentation & Testing (Extended)

1.  **Update `docs/design/configuration_system.md`:**
    *   In Section 2.3 (`ComponentManager`):
        *   Detail the new `save_components_to_file` method.
        *   Update the "CRUD Operations" note to explain how `save_component_config`/`create_component_file` handle single components versus how `save_components_to_file` (and the API endpoints using it) handle arrays being saved to a *specified filename*.
2.  **Testing (Extended):**
    *   **`ComponentManager` Tests (`tests/config/test_component_manager.py`):**
        *   Add tests for `save_components_to_file`:
            *   Saving a list of valid components to a new file. Verify file content and in-memory store.
            *   Saving a list with some invalid components (ensure valid ones are saved, errors logged for invalid).
            *   Overwriting an existing file.
            *   Attempting to save to an existing file with `overwrite=False`.
            *   Ensure paths are correctly relativized in the saved file and resolved in memory.
    *   **API Tests (`tests/api/routes/test_config_routes.py`):**
        *   For `POST /configs/{component_type}/{filename}`:
            *   Test creating a file with a single component (dict payload).
            *   Test creating a file with multiple components (list payload). Verify file content and that components are loaded.
        *   For `PUT /configs/{component_type}/{filename}`:
            *   Test updating a file with a single component (dict payload).
            *   Test updating a file with multiple components (list payload), overwriting previous content. Verify.

## Phase 5: Frontend Considerations (Informational - Not part of this backend plan)
*   The frontend "Save" functionality in `ConfigEditorView.tsx` will now be able to send either a single object or an array to the `PUT` endpoint. The backend will handle it appropriately.
*   Consider UI implications if a user edits a file that was an array, makes it a single object, and saves. Or vice-versa. The backend logic will save what's given to the specified filename.

This plan prioritizes the backend changes for loading, viewing, and saving/creating multi-component files.
