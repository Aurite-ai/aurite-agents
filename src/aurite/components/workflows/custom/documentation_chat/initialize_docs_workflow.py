# tests/fixtures/custom_workflows/example_workflow.py
import logging
import re

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from aurite.servers.storage.file_server import FILES, read_file
from aurite.servers.storage.vector.pgvector_server import batch_store, clear_database
from typing import TYPE_CHECKING, Optional, Any

# Type hint for ExecutionFacade to avoid circular import
if TYPE_CHECKING:
    from aurite.execution.facade import ExecutionFacade

logger = logging.getLogger(__name__)


class InitializeDocsWorkflow:
    """
    Custom workflow for initializing the documentation database
    """

    def separate_paragraphs(self, input: str) -> list[str]:
        """Split a string into a list of paragraphs"""

        paragraphs = list(filter(lambda x: x != "", input.strip().split("\n\n")))

        return [p.strip() for p in paragraphs]

    def separate_markdown(self, markdown_content: str) -> list[str]:
        """Split a string into markdown sections (which will each begin with one or more # symbols at the start of a line)"""
        lines = markdown_content.split("\n")

        sections = []
        current_section = []

        for line in lines:
            if re.match(r"^#+\s", line):
                if current_section:
                    sections.append("\n".join(current_section))
                    current_section = []

            current_section.append(line)

        if current_section:
            sections.append("\n".join(current_section))

        return sections

    async def execute_workflow(
        self,
        initial_input: Any,
        executor: "ExecutionFacade",
        session_id: Optional[str] = None,
    ) -> Any:
        """
        Executes the initialize docs workflow.

        Args:
            initial_input: Unused object
            executor: The ExecutionFacade
            session_id: Optional, id of the session for logging

        Returns:
            A dictionary containing the result or an error.
        """
        logger.info("InitializeDocsWorkflow started")

        try:
            clear_database()

            count = 0

            for path in FILES:
                file = read_file(path)

                paragraphs = [paragraph for paragraph in self.separate_markdown(file)]

                batch_store(paragraphs, {"filepath": path})

                count += len(paragraphs)

            return_value = {
                "status": "success",
                "entries": count,
            }

            return return_value
        except Exception as e:
            logger.error(
                f"Error within InitializeDocsWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
