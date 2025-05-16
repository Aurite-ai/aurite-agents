import pathlib
import uuid

from .speech_server import speech_to_text  # Relative import
from ..memory.mem0_server import (
    add_memories,
    get_all_memories,
    delete_all_memories,
)  # Relative import

PARENT_PATH = pathlib.Path(__file__).parent.absolute()

if __name__ == "__main__":
    filepath = f"{PARENT_PATH}/test_audio/speech_commercial_mono.wav"

    transcript = speech_to_text(filepath)

    print(f"TRANSCRIPT:\n{transcript}")

    test_id = uuid.uuid4()
    user_id = f"test_user_{test_id}"

    add_memories(
        memory_str=transcript,
        user_id=user_id,
        prompt="The following is the transcript of a conversation. Store information about the customer",
    )

    memories = get_all_memories(user_id=user_id)

    memories_str = "\n".join(memories)
    print(f"MEMORIES:\n{memories_str}")

    delete_all_memories(user_id=user_id)
