"""
Integration tests for QA Evaluation Configuration.

Tests the consolidated EvaluationConfig model and mode resolution logic
after Phase 1 refactoring.
"""

from uuid import UUID

import pytest

from aurite.lib.models.config.components import EvaluationCase, EvaluationConfig


class TestEvaluationCase:
    """Tests for EvaluationCase model validation."""

    def test_evaluation_case_basic(self):
        """Test basic EvaluationCase creation."""
        case = EvaluationCase(
            input="What is the weather?", expectations=["The output contains temperature information"]
        )

        assert isinstance(case.id, UUID)
        assert case.input == "What is the weather?"
        assert case.output is None
        assert case.name is None
        assert len(case.expectations) == 1

    def test_evaluation_case_with_output(self):
        """Test EvaluationCase with pre-provided output (manual mode)."""
        case = EvaluationCase(
            name="Weather test case",
            input="What is the weather?",
            output="The temperature is 72°F",
            expectations=["The output contains temperature in Fahrenheit"],
        )

        assert case.name == "Weather test case"
        assert case.output == "The temperature is 72°F"
        assert case.input == "What is the weather?"

    def test_evaluation_case_multiple_expectations(self):
        """Test EvaluationCase with multiple expectations."""
        case = EvaluationCase(
            input="Get weather for San Francisco",
            expectations=[
                "The get_weather tool was called",
                "The location is San Francisco",
                "Temperature is provided in Celsius",
            ],
        )

        assert len(case.expectations) == 3


class TestEvaluationConfigBasic:
    """Tests for basic EvaluationConfig model validation."""

    def test_minimal_evaluation_config(self):
        """Test minimal valid EvaluationConfig."""
        config = EvaluationConfig(
            name="test_eval", test_cases=[EvaluationCase(input="test input", expectations=["test expectation"])]
        )

        assert config.name == "test_eval"
        assert config.type == "evaluation"
        assert len(config.test_cases) == 1
        assert config.mode is None  # Not explicitly set
        assert config.use_cache is True  # Default value
        assert config.max_concurrent_tests == 3  # Default value

    def test_evaluation_config_with_all_fields(self):
        """Test EvaluationConfig with all fields populated."""
        config = EvaluationConfig(
            name="comprehensive_eval",
            description="A comprehensive evaluation test",
            mode="aurite",
            component_type="agent",
            component_refs=["weather_agent"],
            test_cases=[EvaluationCase(input="What's the weather?", expectations=["Contains temperature"])],
            review_llm="claude-sonnet",
            expected_schema={"type": "object"},
            use_cache=False,
            cache_ttl=7200,
            force_refresh=True,
            max_concurrent_tests=5,
            rate_limit_retry_count=5,
            rate_limit_base_delay=2.0,
            default_timeout=120.0,
            parallel_execution=False,
            max_retries=2,
        )

        assert config.mode == "aurite"
        assert config.component_type == "agent"
        assert config.component_refs == ["weather_agent"]
        assert config.use_cache is False
        assert config.cache_ttl == 7200
        assert config.force_refresh is True
        assert config.max_concurrent_tests == 5
        assert config.rate_limit_retry_count == 5
        assert config.default_timeout == 120.0
        assert config.parallel_execution is False
        assert config.max_retries == 2


class TestModeResolution:
    """Tests for evaluation mode resolution logic."""

    def test_explicit_aurite_mode(self):
        """Test when mode is explicitly set to 'aurite'."""
        config = EvaluationConfig(
            name="test_eval",
            mode="aurite",
            component_refs=["my_agent"],
            test_cases=[EvaluationCase(input="test", expectations=["pass"])],
        )

        assert config.resolve_mode() == "aurite"

    def test_explicit_manual_mode(self):
        """Test when mode is explicitly set to 'manual'."""
        config = EvaluationConfig(
            name="test_eval",
            mode="manual",
            test_cases=[EvaluationCase(input="test", output="pre-recorded output", expectations=["pass"])],
        )

        assert config.resolve_mode() == "manual"

    def test_explicit_function_mode(self):
        """Test when mode is explicitly set to 'function'."""
        config = EvaluationConfig(
            name="test_eval",
            mode="function",
            run_agent="path/to/run_function.py",
            test_cases=[EvaluationCase(input="test", expectations=["pass"])],
        )

        assert config.resolve_mode() == "function"

    def test_auto_detect_manual_mode(self):
        """Test automatic detection of manual mode (all outputs provided, no component_refs)."""
        config = EvaluationConfig(
            name="test_eval",
            test_cases=[
                EvaluationCase(input="test1", output="output1", expectations=["pass"]),
                EvaluationCase(input="test2", output="output2", expectations=["pass"]),
            ],
        )

        assert config.resolve_mode() == "manual"

    def test_auto_detect_function_mode(self):
        """Test automatic detection of function mode (run_agent provided, no component_refs)."""
        config = EvaluationConfig(
            name="test_eval",
            run_agent="custom_run_function",
            test_cases=[EvaluationCase(input="test", expectations=["pass"])],
        )

        assert config.resolve_mode() == "function"

    def test_auto_detect_aurite_mode_with_component_refs(self):
        """Test automatic detection of aurite mode (component_refs provided)."""
        config = EvaluationConfig(
            name="test_eval",
            component_refs=["my_agent"],
            test_cases=[EvaluationCase(input="test", expectations=["pass"])],
        )

        assert config.resolve_mode() == "aurite"

    def test_auto_detect_aurite_mode_default(self):
        """Test aurite mode as default when no special conditions met."""
        config = EvaluationConfig(
            name="test_eval", component_type="agent", test_cases=[EvaluationCase(input="test", expectations=["pass"])]
        )

        assert config.resolve_mode() == "aurite"

    def test_manual_mode_with_partial_outputs(self):
        """Test that partial outputs don't trigger manual mode."""
        config = EvaluationConfig(
            name="test_eval",
            test_cases=[
                EvaluationCase(
                    input="test1",
                    output="output1",  # Has output
                    expectations=["pass"],
                ),
                EvaluationCase(
                    input="test2",  # No output
                    expectations=["pass"],
                ),
            ],
        )

        # Should default to aurite since not ALL cases have outputs
        assert config.resolve_mode() == "aurite"

    def test_mode_override_takes_precedence(self):
        """Test that explicit mode overrides auto-detection."""
        config = EvaluationConfig(
            name="test_eval",
            mode="aurite",  # Explicitly set to aurite
            test_cases=[
                EvaluationCase(
                    input="test",
                    output="output",  # Would normally trigger manual mode
                    expectations=["pass"],
                )
            ],
        )

        # Explicit mode should take precedence
        assert config.resolve_mode() == "aurite"


class TestEvaluationConfigDefaults:
    """Tests for EvaluationConfig default values."""

    def test_caching_defaults(self):
        """Test default caching configuration."""
        config = EvaluationConfig(name="test_eval", test_cases=[EvaluationCase(input="test", expectations=["pass"])])

        assert config.use_cache is True
        assert config.cache_ttl == 3600
        assert config.force_refresh is False

    def test_rate_limiting_defaults(self):
        """Test default rate limiting configuration."""
        config = EvaluationConfig(name="test_eval", test_cases=[EvaluationCase(input="test", expectations=["pass"])])

        assert config.max_concurrent_tests == 3
        assert config.rate_limit_retry_count == 3
        assert config.rate_limit_base_delay == 1.0

    def test_testing_behavior_defaults(self):
        """Test default testing behavior configuration."""
        config = EvaluationConfig(name="test_eval", test_cases=[EvaluationCase(input="test", expectations=["pass"])])

        assert config.default_timeout == 90.0
        assert config.parallel_execution is True
        assert config.max_retries == 1


class TestMultiComponentEvaluation:
    """Tests for multi-component evaluation configuration."""

    def test_multiple_component_refs(self):
        """Test EvaluationConfig with multiple component references."""
        config = EvaluationConfig(
            name="multi_agent_eval",
            component_type="agent",
            component_refs=["agent1", "agent2", "agent3"],
            test_cases=[EvaluationCase(input="test", expectations=["pass"])],
        )

        assert config.component_refs is not None
        assert len(config.component_refs) == 3
        assert config.resolve_mode() == "aurite"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
