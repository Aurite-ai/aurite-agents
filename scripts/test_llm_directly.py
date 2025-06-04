import asyncio
import os
import sys
from llm.providers.openai_client import OpenAIClient

# filepath: /home/wilcoxr/workspace/aurite/aurite-agents/scripts/test_llm_directly.py


# Ensure src/aurite is on the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "aurite")))


async def main():
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY environment variable not set.")
        return

    # Minimal test message
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "Hello, who are you?"}]}
    ]

    # Instantiate the client (use a model you have access to)
    client = OpenAIClient(model_name="gpt-3.5-turbo")

    try:
        response = await client.create_message(messages, tools=None)
        print("Response from OpenAIClient:")
        for block in response.content:
            if block.type == "text":
                print(block.text)
            else:
                print(f"[{block.type}] {block}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())