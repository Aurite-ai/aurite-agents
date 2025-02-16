from sqlalchemy import Result
from mcp.types import (
    BaseSession,
    RequestT,
    NotificationT,
    ResultT,
    RequestResponder,
    ReceiveRequestT,
    ReceiveNotificationT,
)


class Session(BaseSession[RequestT, NotificationT, ResultT]):
    async def send_request(
        self, request: RequestT, result_type: type[Result]
    ) -> Result:
        """
        Send request and wait for response. Raises McpError if response contains error.
        """
        # Request handling implementation

    async def send_notification(self, notification: NotificationT) -> None:
        """Send one-way notification that doesn't expect response."""
        # Notification handling implementation

    async def _received_request(
        self, responder: RequestResponder[ReceiveRequestT, ResultT]
    ) -> None:
        """Handle incoming request from other side."""
        # Request handling implementation

    async def _received_notification(self, notification: ReceiveNotificationT) -> None:
        """Handle incoming notification from other side."""
        # Notification handling implementation
