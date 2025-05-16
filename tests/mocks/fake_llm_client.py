from typing import List, AsyncGenerator, Any, Dict, Optional  # Added Optional
from unittest.mock import AsyncMock


class FakeLLMClient:
    """
    A fake LLM client for testing purposes, particularly for streaming.
    It yields a predefined sequence of events.
    Tests can set `FakeLLMClient.test_event_sequence` before this client is instantiated
    by the application's LLM loading mechanism to control the event stream for an E2E test.
    """

    test_event_sequence: Optional[List[Dict[str, Any]]] = (
        None  # Class variable for test-specific sequence
    )

    def __init__(
        self,
        event_sequence: Optional[List[Dict[str, Any]]] = None,
        llm_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        # If an event_sequence is provided directly, use it.
        # Otherwise, if the class variable test_event_sequence is set, use that.
        # Otherwise, default to an empty list.
        if event_sequence is not None:
            self.event_sequence = event_sequence
        elif FakeLLMClient.test_event_sequence is not None:
            self.event_sequence = FakeLLMClient.test_event_sequence
        else:
            self.event_sequence = []

        self.llm_id = llm_id  # Store llm_id if passed, for potential debugging
        # Mock create_message for completeness if BaseLLM expects it
        self.create_message = AsyncMock(
            return_value={}
        )  # Returns a dummy dict for non-streaming calls

        # Attributes to track calls to stream_message
        self.stream_message_call_args: tuple = None
        self.stream_message_call_kwargs: dict = None
        self.stream_message_call_count: int = 0

    async def stream_message(
        self, *args, **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simulates the LLM streaming messages.
        Yields events from the pre-configured event_sequence.
        """
        self.stream_message_call_args = args
        self.stream_message_call_kwargs = kwargs
        self.stream_message_call_count += 1
        for event in self.event_sequence:
            yield event

    def assert_stream_message_called_once_with(self, **kwargs_to_check):
        assert self.stream_message_call_count == 1
        # Ensure stream_message_call_kwargs is not None before trying to access it
        # This can happen if the method was called but with no keyword arguments,
        # or if it was never called and stream_message_call_kwargs remains at its initial None value.
        # However, if call_count is 1, call_kwargs should be a dict (even if empty).
        # The primary check is call_count. Detailed arg checking is secondary.
        if self.stream_message_call_kwargs is not None:
            for key, value in kwargs_to_check.items():
                assert key in self.stream_message_call_kwargs, (
                    f"Key '{key}' not in call_kwargs"
                )
                assert self.stream_message_call_kwargs[key] == value, (
                    f"Value for key '{key}' does not match"
                )
        elif kwargs_to_check:
            # If we expected kwargs but none were recorded (and method was called)
            raise AssertionError(
                f"stream_message called with no kwargs (recorded: {self.stream_message_call_kwargs}), but expected {kwargs_to_check}."
            )

    @classmethod
    def clear_test_event_sequence(cls):
        """Clears the class-level test_event_sequence."""
        cls.test_event_sequence = None
