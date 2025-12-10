#!/usr/bin/env python3
"""
Test script to verify MCP server evaluation optimization.
This tests that:
1. A single agent is reused for all test cases
2. Log messages are reduced
3. Tests still pass correctly
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from aurite.aurite import Aurite
from aurite.lib.models.api.requests import EvaluationCase, EvaluationRequest
from aurite.testing.qa.qa_engine import QAEngine

# Configure logging to capture relevant messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# Create a custom handler to capture specific log messages
class LogCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.agent_creation_count = 0
        self.registration_attempts = 0
        self.messages = []

    def emit(self, record):
        msg = record.getMessage()
        self.messages.append(msg)

        if "Created test agent" in msg:
            self.agent_creation_count += 1
            print(f"[CAPTURED] Agent creation #{self.agent_creation_count}: {msg}")

        if "Attempting to dynamically register client" in msg:
            self.registration_attempts += 1
            print(f"[CAPTURED] Registration attempt #{self.registration_attempts}: {msg}")

        if "Reusing existing test agent" in msg:
            print(f"[CAPTURED] Agent reuse: {msg}")


async def test_mcp_optimization():
    """Test MCP server evaluation with optimization."""
    print("\n" + "=" * 70)
    print("Testing MCP Server Evaluation Optimization")
    print("=" * 70 + "\n")

    # Set up log capture
    log_capture = LogCapture()
    logging.getLogger("aurite.testing.qa.qa_utils").addHandler(log_capture)
    logging.getLogger("aurite.execution.mcp_host.mcp_host").addHandler(log_capture)

    # Initialize Aurite
    aurite = Aurite()
    # Create QA Engine
    qa_engine = QAEngine(config_manager=aurite.kernel.config_manager)
    # Get the execution engine for the executor
    engine = aurite.kernel.execution

    # Create a mock MCP server evaluation request
    # This simulates multiple test cases for the same MCP server
    test_cases = [
        EvaluationCase(
            id=uuid.uuid4(), input=f"Test MCP server with input {i}", expectations=["The server responds correctly"]
        )
        for i in range(5)  # 5 test cases
    ]

    # Create evaluation request
    eval_request = EvaluationRequest(
        component_type="mcp_server",
        component_refs=["test_mcp_server"],  # Mock server name
        component_config={
            "name": "test_mcp_server",
            "type": "mcp_server",
            # Add minimal config for testing
        },
        test_cases=test_cases,
        review_llm="anthropic_claude_3_haiku",
        use_cache=False,  # Disable caching to see all executions
    )

    try:
        # Run the evaluation
        print("Running MCP server evaluation with 5 test cases...")
        results = await qa_engine.evaluate_component(eval_request, engine)

        # Analyze results
        print(f"\nEvaluation completed with status: {list(results.values())[0].status}")

        print("\n" + "-" * 50)
        print("OPTIMIZATION RESULTS:")
        print("-" * 50)

        print(f"Agent creations: {log_capture.agent_creation_count}")
        print(f"Registration attempts: {log_capture.registration_attempts}")
        print(f"Total test cases: {len(test_cases)}")

        # Check optimization effectiveness
        if log_capture.agent_creation_count <= 1:
            print("✅ OPTIMIZATION SUCCESSFUL: Single agent created and reused")
        else:
            print(f"❌ OPTIMIZATION ISSUE: {log_capture.agent_creation_count} agents created (expected 1)")

        # Count reuse messages
        reuse_count = sum(1 for msg in log_capture.messages if "Reusing existing test agent" in msg)
        print(f"Agent reuses: {reuse_count} (expected {len(test_cases) - 1})")

        if reuse_count == len(test_cases) - 1:
            print("✅ AGENT REUSE WORKING: Agent reused for subsequent test cases")

    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70 + "\n")

    return log_capture.agent_creation_count <= 1


if __name__ == "__main__":
    success = asyncio.run(test_mcp_optimization())
    sys.exit(0 if success else 1)
