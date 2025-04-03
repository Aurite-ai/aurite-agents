from openai import OpenAI
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("speech")

client = OpenAI()

@mcp.tool()
def speech_to_text(filepath: str) -> str:
    """Convert an audio file into a text transcript
    
    Args:
        filepath: The local path to the file
        
    Returns:
        str: The text transcript
    """
    audio_file = open(filepath, "rb")

    transcription = client.audio.transcriptions.create(
        model="gpt-4o-transcribe", 
        file=audio_file
    )

    return transcription.text

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')