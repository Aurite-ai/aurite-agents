import tempfile
import os

from openai import OpenAI
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from pydub import AudioSegment

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
    ten_minutes = 10 * 60 * 1000
    audio_segment = AudioSegment.from_file(filepath)

    transcriptions = []

    # split the audio file into 10 min chunks to not exceed transcription limit
    for i in range(0, audio_segment.__len__(), ten_minutes):
        chunk = audio_segment[i : i + ten_minutes]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_filename = temp_file.name
            chunk.export(temp_filename, format="wav")

        try:
            with open(temp_filename, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    model="gpt-4o-transcribe", file=file
                )

            transcriptions.append(transcription.text)

        finally:
            os.unlink(temp_filename)

    return "\n".join(transcriptions)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
