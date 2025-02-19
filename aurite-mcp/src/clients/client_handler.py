import logging

from src.clients.client import MCPClient

model_to_server = {
    "weather": "src/servers/server.py"
}
model_to_client = {}

async def initialize_all_clients():
    """Initialize all clients defined in model_to_server"""
    for model, server in model_to_server.items():
        client = MCPClient()
        try:
            await client.connect_to_server(server)
            model_to_client[model] = client
        except Exception as e:
            logging.error(f"Error occured initializing clients: {str(e)}")
            
async def get_client(model: str) -> MCPClient | None:
    """Fetches a client by its corresponding model string, initializing it first if necessary"""
    if model in model_to_client:
        return model_to_client[model]
    elif model in model_to_server:
        client = MCPClient()
        try:
            await client.connect_to_server(model_to_server[model])
            model_to_client[model] = client
            return client
        except Exception as e:
            logging.error(f"Error occured initializing clients: {str(e)}")
    else:
        logging.error(f"Model not recognized: {model}")
    
    return None

async def clear_all_clients():
    """Clears the model_to_client dict, cleaning up the clients first"""
    for client in model_to_client.values():
        await client.cleanup()
        
    model_to_client.clear()