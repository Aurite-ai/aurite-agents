import subprocess
import sys
import threading


def consume_stream(stream):
    """Reads from a stream and discards the output."""
    while True:
        line = stream.readline()
        if not line:
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_mcp_server.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1:]

    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout_thread = threading.Thread(target=consume_stream, args=(proc.stdout,))
        stderr_thread = threading.Thread(target=consume_stream, args=(proc.stderr,))

        stdout_thread.start()
        stderr_thread.start()

        proc.wait()

        stdout_thread.join()
        stderr_thread.join()

    except FileNotFoundError:
        sys.exit(1)
