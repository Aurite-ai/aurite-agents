// Get API key from user
function getApiKey() {
    const apiKey = prompt('Please enter your API key:');
    if (!apiKey) {
        alert('API key is required');
        return null;
    }
    return apiKey;
}

// Show/hide system prompt field based on component type
document.getElementById('execComponentType').addEventListener('change', function() {
    const componentType = this.value;
    const systemPromptGroup = document.getElementById('systemPromptGroup');
    
    // Only show system prompt for agents
    if (componentType === 'agents') {
        systemPromptGroup.style.display = 'block';
    } else {
        systemPromptGroup.style.display = 'none';
    }
});

// Initialize system prompt field visibility on page load
document.addEventListener('DOMContentLoaded', function() {
    const componentType = document.getElementById('execComponentType').value;
    const systemPromptGroup = document.getElementById('systemPromptGroup');
    
    // Only show system prompt for agents
    if (componentType === 'agents') {
        systemPromptGroup.style.display = 'block';
    } else {
        systemPromptGroup.style.display = 'none';
    }
});

async function registerComponent() {
    const apiKey = getApiKey();
    if (!apiKey) return;

    const type = document.getElementById('componentType').value;
    const name = document.getElementById('name').value;
    let configJson;
    
    try {
        configJson = JSON.parse(document.getElementById('config').value);
    } catch (e) {
        alert('Invalid JSON in configuration');
        return;
    }

    // For clients, the payload is the entire config
    // For agents and workflows, we need to set the name in the config
    let payload;
    if (type === 'clients') {
        // Client config should include client_id
        if (!configJson.client_id) {
            configJson.client_id = name;
        }
        payload = configJson;
    } else {
        // For agents and workflows, name is a top-level property
        payload = {
            ...configJson,
            name: name
        };
    }

    try {
        const response = await fetch(`/${type}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`${response.status}: ${errorData.detail || 'Unknown error'}`);
        }
        
        const result = await response.json();
        document.getElementById('result').innerText = JSON.stringify(result, null, 2);
    } catch (error) {
        document.getElementById('result').innerText = `Error: ${error.message}`;
    }
}

async function executeComponent() {
    const apiKey = getApiKey();
    if (!apiKey) return;

    const type = document.getElementById('execComponentType').value;
    const name = document.getElementById('execName').value;
    let inputJson;
    
    try {
        inputJson = JSON.parse(document.getElementById('input').value);
    } catch (e) {
        alert('Invalid JSON in input');
        return;
    }

    // Prepare the request based on component type
    let url, payload;
    
    if (type === 'agents') {
        url = `/agents/${name}/execute`;
        // Get system prompt from dedicated field if available, otherwise from JSON input
        const systemPrompt = document.getElementById('systemPrompt').value.trim() || inputJson.system_prompt || null;
        payload = { 
            user_message: inputJson.user_message || '',
            system_prompt: systemPrompt
        };
    } else if (type === 'workflows') {
        url = `/workflows/${name}/execute`;
        payload = { initial_user_message: inputJson.initial_user_message || '' };
    } else if (type === 'custom_workflows') {
        url = `/custom_workflows/${name}/execute`;
        payload = { initial_input: inputJson.initial_input || {} };
    }

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`${response.status}: ${errorData.detail || 'Unknown error'}`);
        }
        
        const result = await response.json();
        document.getElementById('result').innerText = JSON.stringify(result, null, 2);
    } catch (error) {
        document.getElementById('result').innerText = `Error: ${error.message}`;
    }
}
