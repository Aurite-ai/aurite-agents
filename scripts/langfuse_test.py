import os
import time

from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.decorators import observe

load_dotenv()

langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)


@observe()
def wait():
    time.sleep(1)


@observe()
def capitalize(input: str):
    return input.upper()


@observe()
def main_fn(query: str):
    wait()
    capitalized = capitalize(query)
    return f"Q:{capitalized}; A: nice too meet you!"


main_fn("hi there")

trace = langfuse.trace(name="test-trace", user_id="test-user", metadata={"source": "setup-check"})
langfuse.flush()  # Ensure the trace is sent immediately
