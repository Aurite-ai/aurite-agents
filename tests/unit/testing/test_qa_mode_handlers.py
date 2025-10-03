"""
Unit tests for QA mode handlers.

Tests the three evaluation modes:
- Aurite: Execute components via AuriteEngine
- Manual: Use pre-recorded outputs
- Function: Execute custom run functions
"""

from unittest.mock import MagicMock

import pytest

from aurite.lib.models.config.components import EvaluationCase, EvaluationConfig
from aurite.testing.qa.qa_mode_handlers import (
    AuriteModeHandler,
    FunctionModeHandler,
    ManualModeHandler,
    get_mode_handler,
)


class TestGetModeHandler:
    """Test the mode handler factory function."""

    def test_get_aurite_handler(self):
        """Test getting Aurite mode handler."""
        handler = get_mode_handler("aurite")
        assert isinstance(handler, AuriteModeHandler)

    def test_get_manual_handler(self):
        """Test getting Manual mode handler."""
        handler = get_mode_handler("manual")
        assert isinstance(handler, ManualModeHandler)

    def test_get_function_handler(self):
        """Test getting Function mode handler."""
        handler = get_mode_handler("function")
        assert isinstance(handler, FunctionModeHandler)

    def test_invalid_mode(self):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Unknown evaluation mode"):
            get_mode_handler("invalid")


class TestManualModeHandler:
    """Test Manual mode handler."""

    @pytest.fixture
    def handler(self):
        """Create a ManualModeHandler instance."""
        return ManualModeHandler()

    @pytest.fixture
    def test_case(self):
        """Create a test case with pre-recorded output."""
        return EvaluationCase(
            input="test input",
            output="test output",
            expectations=["test expectation"],
        )

    @pytest.fixture
    def eval_request(self):
        """Create an evaluation request."""
        return EvaluationConfig(
            name="test_eval",
            component_type="agent",
            test_cases=[],
        )

    async def test_prepare_config_returns_none(self, handler, eval_request):
        """Test that prepare_config returns None for manual mode."""
        result = await handler.prepare_config(eval_request)
        assert result is None

    async def test_get_output_returns_prerecorded(self, handler, test_case, eval_request):
        """Test that get_output returns pre-recorded output."""
        output = await handler.get_output(test_case, eval_request)
        assert output == "test output"

    async def test_get_output_without_output_raises_error(self, handler, eval_request):
        """Test that missing output raises ValueError."""
        test_case = EvaluationCase(
            input="test input",
            output=None,  # No output provided
            expectations=["test expectation"],
        )

        with pytest.raises(ValueError, match="Manual mode requires output"):
            await handler.get_output(test_case, eval_request)


class TestFunctionModeHandler:
    """Test Function mode handler."""

    @pytest.fixture
    def handler(self):
        """Create a FunctionModeHandler instance."""
        return FunctionModeHandler()

    @pytest.fixture
    def test_case(self):
        """Create a test case."""
        return EvaluationCase(
            input="test input",
            expectations=["test expectation"],
        )

    async def test_prepare_config_returns_none(self, handler):
        """Test that prepare_config returns None for function mode."""
        eval_request = EvaluationConfig(
            name="test_eval",
            component_type="agent",
            test_cases=[],
        )
        result = await handler.prepare_config(eval_request)
        assert result is None

    async def test_get_output_with_async_function(self, handler, test_case):
        """Test execution with async function."""

        async def test_run_func(input_text, **kwargs):
            return f"processed: {input_text}"

        eval_request = EvaluationConfig(
            name="test_eval",
            component_type="agent",
            test_cases=[],
            run_agent=test_run_func,
        )

        output = await handler.get_output(test_case, eval_request)
        assert output == "processed: test input"

    async def test_get_output_with_sync_function(self, handler, test_case):
        """Test execution with sync function."""

        def test_run_func(input_text, **kwargs):
            return f"processed: {input_text}"

        eval_request = EvaluationConfig(
            name="test_eval",
            component_type="agent",
            test_cases=[],
            run_agent=test_run_func,
        )

        output = await handler.get_output(test_case, eval_request)
        assert output == "processed: test input"

    async def test_get_output_without_run_agent_raises_error(self, handler, test_case):
        """Test that missing run_agent raises ValueError."""
        eval_request = EvaluationConfig(
            name="test_eval",
            component_type="agent",
            test_cases=[],
            # No run_agent provided
        )

        with pytest.raises(ValueError, match="Function mode requires run_agent"):
            await handler.get_output(test_case, eval_request)


class TestAuriteModeHandler:
    """Test Aurite mode handler."""

    @pytest.fixture
    def config_manager(self):
        """Create a mock ConfigManager."""
        manager = MagicMock()
        manager.get_config.return_value = {
            "name": "test_agent",
            "type": "agent",
            "llm_config_id": "test_llm",
        }
        return manager

    @pytest.fixture
    def handler(self, config_manager):
        """Create an AuriteModeHandler instance."""
        return AuriteModeHandler(config_manager=config_manager)

    @pytest.fixture
    def eval_request(self):
        """Create an evaluation request."""
        return EvaluationConfig(
            name="test_eval",
            component_type="agent",
            component_refs=["test_agent"],
            test_cases=[],
        )

    async def test_prepare_config_loads_from_manager(self, handler, eval_request, config_manager):
        """Test that prepare_config loads config from ConfigManager."""
        component_name = await handler.prepare_config(eval_request)

        assert component_name == "test_agent"
        assert eval_request.component_config is not None
        assert eval_request.component_config["name"] == "test_agent"
        config_manager.get_config.assert_called_once_with(component_type="agent", component_id="test_agent")

    async def test_prepare_config_with_provided_config(self, handler):
        """Test that prepare_config uses provided config."""
        eval_request = EvaluationConfig(
            name="test_eval",
            component_type="agent",
            component_refs=["test_agent"],
            component_config={"name": "provided_agent", "type": "agent"},
            test_cases=[],
        )

        component_name = await handler.prepare_config(eval_request)
        assert component_name == "provided_agent"

    async def test_get_output_requires_executor(self, handler, eval_request):
        """Test that get_output requires an executor for Aurite mode."""
        test_case = EvaluationCase(
            input="test input",
            expectations=["test expectation"],
        )

        with pytest.raises(ValueError, match="AuriteEngine executor required"):
            await handler.get_output(test_case, eval_request, executor=None)
