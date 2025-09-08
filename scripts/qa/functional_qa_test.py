#!/usr/bin/env python3
"""
Functional QA Testing Script for the Aurite Framework.

This script provides comprehensive testing of the QA Engine and component-specific
testers (AgentQATester, WorkflowQATester) using predefined test configurations
and data sets through the API.

Usage:
    python scripts/qa/functional_qa_test.py [--component-type agent|workflow|all] [--verbose] [--api-url URL]

Examples:
    python scripts/qa/functional_qa_test.py --component-type agent
    python scripts/qa/functional_qa_test.py --component-type workflow --verbose
    python scripts/qa/functional_qa_test.py --api-url http://localhost:8000  # Tests all components
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx

# Add the src directory to the path so we can import aurite modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aurite.lib.models.api.requests import EvaluationCase

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class QAFunctionalTester:
    """
    Functional tester for the QA system using API endpoints.

    This class orchestrates comprehensive testing of the QA Engine and
    component-specific testers using predefined test configurations
    through the Aurite API.
    """

    def __init__(self, api_url: str = "http://localhost:8000", verbose: bool = False):
        """
        Initialize the functional tester.

        Args:
            api_url: Base URL for the Aurite API
            verbose: Enable verbose logging
        """
        self.api_url = api_url.rstrip("/")
        self.verbose = verbose
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        self.test_data_dir = Path(__file__).parent / "test_data"
        self.config_dir = (
            Path(__file__).parent.parent.parent / "tests" / "fixtures" / "workspace" / "shared_configs" / "qa"
        )

        # Test results storage
        self.results: Dict[str, Any] = {}

        # Get API key from environment or use default
        self.api_key = os.getenv("AURITE_API_KEY", "test-api-key")

    async def run_all_tests(self, component_type: str = "all") -> Dict[str, Any]:
        """
        Run all QA functional tests through the API.

        Args:
            component_type: Type of component to test ("agent", "workflow", or "all")

        Returns:
            Dictionary containing all test results
        """
        logger.info("=" * 80)
        logger.info("AURITE QA FUNCTIONAL TESTING (API Mode)")
        logger.info("=" * 80)
        logger.info(f"API URL: {self.api_url}")

        # Check if API is running
        if not await self._check_api_health():
            logger.error("❌ API is not running or not accessible")
            logger.info("Please start the API server with: aurite api")
            return {"error": "API not accessible"}

        if component_type in ["agent", "all"]:
            logger.info("\n🤖 Testing Agent QA System...")
            agent_results = await self._test_agent_qa_system()
            self.results["agent_qa"] = agent_results

        if component_type in ["workflow", "all"]:
            logger.info("\n🔄 Testing Workflow QA System...")
            workflow_results = await self._test_workflow_qa_system()
            self.results["workflow_qa"] = workflow_results

        if component_type == "all":
            logger.info("\n🔧 Testing QA Engine Integration...")
            integration_results = await self._test_qa_engine_integration()
            self.results["qa_engine_integration"] = integration_results

        # Generate summary report
        self._generate_summary_report()

        return self.results

    async def _check_api_health(self) -> bool:
        """Check if the API is running and accessible."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"API health check failed: {e}")
            return False

    async def _test_agent_qa_system(self) -> Dict[str, Any]:
        """Test the Agent QA system with different agent configurations."""
        logger.info("Testing Agent QA System through API...")

        results = {}

        # Test configurations: good, average, poor
        agent_configs = ["good_agent_qa.json", "average_agent_qa.json", "poor_agent_qa.json"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            for config_file in agent_configs:
                config_name = config_file.replace(".json", "")
                logger.info(f"\n  📋 Testing {config_name}...")

                try:
                    # Load agent configuration
                    config_path = self.config_dir / "agents" / config_file
                    with open(config_path, "r") as f:
                        agent_config = json.load(f)

                    # Create test cases for this agent
                    test_cases = self._create_agent_test_cases(config_name)

                    # Create evaluation request with component config
                    # Convert test cases to dict format with UUID as string
                    test_cases_dict = []
                    for case in test_cases:
                        case_dict = case.model_dump()
                        case_dict["id"] = str(case_dict["id"])  # Convert UUID to string
                        test_cases_dict.append(case_dict)

                    eval_request = {
                        "eval_name": agent_config["name"],
                        "eval_type": "agent",
                        "test_cases": test_cases_dict,
                        "component_config": agent_config,  # Include the configuration
                    }

                    # Send request to API
                    response = await client.post(
                        f"{self.api_url}/testing/evaluate", json=eval_request, headers={"X-API-Key": self.api_key}
                    )

                    if response.status_code == 200:
                        result = response.json()
                        # Debug: log the actual response structure
                        if self.verbose:
                            logger.debug(f"API Response keys: {list(result.keys())}")
                            logger.debug(f"Status: {result.get('status')}, Score: {result.get('overall_score')}")

                        # The API now returns the full QAEvaluationResult directly
                        results[config_name] = {
                            "status": result.get("status", "unknown"),
                            "overall_score": result.get("overall_score", 0),
                            "passed_cases": result.get("passed_cases", 0),
                            "failed_cases": result.get("failed_cases", 0),
                            "total_cases": result.get("total_cases", 0),
                            "recommendations": result.get("recommendations", []),
                        }
                        logger.info(
                            f"    ✅ {config_name}: {result.get('status')} (Score: {result.get('overall_score', 0):.1f}%)"
                        )
                    else:
                        error_msg = f"API returned status {response.status_code}: {response.text}"
                        logger.error(f"    ❌ {config_name}: {error_msg}")
                        results[config_name] = {"status": "error", "error": error_msg}

                except Exception as e:
                    logger.error(f"    ❌ {config_name}: Failed - {str(e)}")
                    results[config_name] = {"status": "error", "error": str(e)}

        return results

    async def _test_workflow_qa_system(self) -> Dict[str, Any]:
        """Test the Workflow QA system with different workflow configurations."""
        logger.info("Testing Workflow QA System through API...")

        results = {}

        # Test configurations: good, average, poor
        workflow_configs = ["good_workflow_qa.json", "average_workflow_qa.json", "poor_workflow_qa.json"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            for config_file in workflow_configs:
                config_name = config_file.replace(".json", "")
                logger.info(f"\n  📋 Testing {config_name}...")

                try:
                    # Load workflow configuration
                    config_path = self.config_dir / "workflows" / config_file
                    with open(config_path, "r") as f:
                        workflow_config = json.load(f)

                    # Create test cases for this workflow
                    test_cases = self._create_workflow_test_cases(config_name)

                    # Create evaluation request with component config
                    # Convert test cases to dict format with UUID as string
                    test_cases_dict = []
                    for case in test_cases:
                        case_dict = case.model_dump()
                        case_dict["id"] = str(case_dict["id"])  # Convert UUID to string
                        test_cases_dict.append(case_dict)

                    eval_request = {
                        "eval_name": workflow_config["name"],
                        "eval_type": workflow_config.get("type", "linear_workflow"),
                        "test_cases": test_cases_dict,
                        "component_config": workflow_config,  # Include the configuration
                    }

                    # Send request to API
                    response = await client.post(
                        f"{self.api_url}/testing/evaluate", json=eval_request, headers={"X-API-Key": self.api_key}
                    )

                    if response.status_code == 200:
                        result = response.json()
                        results[config_name] = {
                            "status": result.get("status", "unknown"),
                            "overall_score": result.get("overall_score", 0),
                            "passed_cases": result.get("passed_cases", 0),
                            "failed_cases": result.get("failed_cases", 0),
                            "total_cases": result.get("total_cases", 0),
                            "recommendations": result.get("recommendations", []),
                        }
                        logger.info(
                            f"    ✅ {config_name}: {result.get('status')} (Score: {result.get('overall_score', 0):.1f}%)"
                        )
                    else:
                        error_msg = f"API returned status {response.status_code}: {response.text}"
                        logger.error(f"    ❌ {config_name}: {error_msg}")
                        results[config_name] = {"status": "error", "error": error_msg}

                except Exception as e:
                    logger.error(f"    ❌ {config_name}: Failed - {str(e)}")
                    results[config_name] = {"status": "error", "error": str(e)}

        return results

    async def _test_qa_engine_integration(self) -> Dict[str, Any]:
        """Test the QA Engine integration with component testers."""
        logger.info("Testing QA Engine Integration through API...")

        results = {}

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Test agent evaluation through QA Engine
                logger.info("  🤖 Testing agent evaluation through QA Engine...")
                agent_config_path = self.config_dir / "agents" / "good_agent_qa.json"
                with open(agent_config_path, "r") as f:
                    agent_config = json.load(f)

                test_cases = self._create_simple_test_cases("agent")

                # Convert test cases to dict format with UUID as string
                test_cases_dict = []
                for case in test_cases:
                    case_dict = case.model_dump()
                    case_dict["id"] = str(case_dict["id"])  # Convert UUID to string
                    test_cases_dict.append(case_dict)

                eval_request = {
                    "eval_name": agent_config["name"],
                    "eval_type": "agent",
                    "test_cases": test_cases_dict,
                    "component_config": agent_config,
                }

                response = await client.post(
                    f"{self.api_url}/testing/evaluate", json=eval_request, headers={"X-API-Key": self.api_key}
                )

                if response.status_code == 200:
                    result = response.json()
                    results["agent_through_engine"] = {
                        "status": result.get("status"),
                        "overall_score": result.get("overall_score"),
                        "component_type": result.get("component_type"),
                    }
                else:
                    results["agent_through_engine"] = {
                        "status": "error",
                        "error": f"API returned {response.status_code}",
                    }

                # Test workflow evaluation through QA Engine
                logger.info("  🔄 Testing workflow evaluation through QA Engine...")
                workflow_config_path = self.config_dir / "workflows" / "good_workflow_qa.json"
                with open(workflow_config_path, "r") as f:
                    workflow_config = json.load(f)

                test_cases = self._create_simple_test_cases("workflow")

                # Convert test cases to dict format with UUID as string
                test_cases_dict = []
                for case in test_cases:
                    case_dict = case.model_dump()
                    case_dict["id"] = str(case_dict["id"])  # Convert UUID to string
                    test_cases_dict.append(case_dict)

                eval_request = {
                    "eval_name": workflow_config["name"],
                    "eval_type": "linear_workflow",
                    "test_cases": test_cases_dict,
                    "component_config": workflow_config,
                }

                response = await client.post(
                    f"{self.api_url}/testing/evaluate", json=eval_request, headers={"X-API-Key": self.api_key}
                )

                if response.status_code == 200:
                    result = response.json()
                    results["workflow_through_engine"] = {
                        "status": result.get("status"),
                        "overall_score": result.get("overall_score"),
                        "component_type": result.get("component_type"),
                    }
                else:
                    results["workflow_through_engine"] = {
                        "status": "error",
                        "error": f"API returned {response.status_code}",
                    }

                logger.info("  ✅ QA Engine integration tests completed")

            except Exception as e:
                logger.error(f"  ❌ QA Engine integration test failed: {str(e)}")
                results["error"] = str(e)

        return results

    def _create_agent_test_cases(self, config_name: str) -> List[EvaluationCase]:
        """
        Create test cases appropriate for the given agent configuration.

        Args:
            config_name: Name of the agent configuration being tested

        Returns:
            List of EvaluationCase objects
        """
        if "good" in config_name:
            # Good agent should handle complex weather and planning tasks well
            return [
                EvaluationCase(
                    input="What's the weather in San Francisco and create a plan for outdoor activities",
                    expectations=[
                        "The response uses the weather_lookup tool to get San Francisco weather",
                        "The response provides temperature information",
                        "The response creates a structured plan based on weather conditions",
                        "The response uses planning tools to save the plan",
                    ],
                ),
                EvaluationCase(
                    input="Check the weather in London and Tokyo, then compare them",
                    expectations=[
                        "The response uses weather_lookup for both London and Tokyo",
                        "The response provides temperature for both cities",
                        "The response compares the weather conditions between cities",
                        "The response is well-structured and informative",
                    ],
                ),
                EvaluationCase(
                    input="What time is it in New York and plan my day based on the weather",
                    expectations=[
                        "The response uses the current_time tool for New York timezone",
                        "The response uses weather_lookup to get New York weather",
                        "The response creates a day plan considering both time and weather",
                        "The response provides actionable recommendations",
                    ],
                ),
            ]
        elif "average" in config_name:
            # Average agent should handle basic weather tasks but may struggle with planning
            return [
                EvaluationCase(
                    input="What's the weather in London?",
                    expectations=[
                        "The response uses the weather_lookup tool",
                        "The response provides temperature information",
                        "The response mentions London specifically",
                    ],
                ),
                EvaluationCase(
                    input="Tell me about the weather in Tokyo using Fahrenheit",
                    expectations=[
                        "The response uses weather_lookup with imperial units",
                        "The response provides temperature in Fahrenheit",
                        "The response mentions Tokyo",
                    ],
                ),
                EvaluationCase(
                    input="Create a plan for tomorrow based on the weather",
                    expectations=[
                        "The response attempts to create a plan",
                        "The response considers weather conditions",
                    ],
                ),
            ]
        else:  # poor
            # Poor agent should struggle with tool usage
            return [
                EvaluationCase(
                    input="What's the weather in San Francisco?",
                    expectations=["The response attempts to address the weather question", "The response is coherent"],
                ),
                EvaluationCase(
                    input="Create a weather-based plan for the week",
                    expectations=[
                        "The response attempts to create some form of plan",
                        "The response mentions weather considerations",
                    ],
                ),
            ]

    def _create_workflow_test_cases(self, config_name: str) -> List[EvaluationCase]:
        """
        Create test cases appropriate for the given workflow configuration.

        Args:
            config_name: Name of the workflow configuration being tested

        Returns:
            List of EvaluationCase objects
        """
        if "good" in config_name:
            # Good workflow should handle complex multi-step weather planning processes
            return [
                EvaluationCase(
                    input="Get weather for San Francisco and create a comprehensive weekend plan",
                    expectations=[
                        "The workflow completes all three steps successfully",
                        "Step 1 retrieves weather data using tools",
                        "Step 2 analyzes the weather and provides recommendations",
                        "Step 3 creates a structured plan based on the analysis",
                        "The workflow demonstrates proper data flow between steps",
                        "The final output is comprehensive and actionable",
                    ],
                ),
                EvaluationCase(
                    input="Check weather in London and Tokyo, analyze differences, and plan a travel itinerary",
                    expectations=[
                        "The workflow executes all planning steps successfully",
                        "Weather data is retrieved for both cities",
                        "Analysis compares the two locations effectively",
                        "The final plan considers weather differences",
                        "The workflow shows proper coordination between agents",
                    ],
                ),
            ]
        elif "average" in config_name:
            # Average workflow should handle basic two-step weather analysis
            return [
                EvaluationCase(
                    input="Get weather for New York and provide recommendations",
                    expectations=[
                        "The workflow completes both steps",
                        "Weather data is retrieved in step 1",
                        "Analysis is provided in step 2",
                        "The workflow executes without major errors",
                    ],
                ),
                EvaluationCase(
                    input="Check today's weather and suggest activities",
                    expectations=[
                        "The workflow processes the weather request",
                        "The output provides activity suggestions",
                        "Basic coordination between steps is evident",
                    ],
                ),
            ]
        else:  # poor
            # Poor workflow with single step should have coordination issues
            return [
                EvaluationCase(
                    input="Create a weather report",
                    expectations=["The workflow attempts to execute", "Some form of output is produced"],
                ),
                EvaluationCase(
                    input="What should I do today?",
                    expectations=["The workflow processes the request", "The response attempts to be helpful"],
                ),
            ]

    def _create_simple_test_cases(self, component_type: str) -> List[EvaluationCase]:
        """
        Create simple test cases for integration testing.

        Args:
            component_type: Type of component ("agent" or "workflow")

        Returns:
            List of simple EvaluationCase objects
        """
        if component_type == "agent":
            return [
                EvaluationCase(
                    input="Hello, how are you?",
                    output="Hello! I'm doing well, thank you for asking. How can I help you today?",
                    expectations=["The response is polite and helpful", "The response acknowledges the greeting"],
                )
            ]
        else:  # workflow
            return [
                EvaluationCase(
                    input="Process this simple request",
                    output="Request processed successfully through workflow steps",
                    expectations=["The workflow processes the request", "The output indicates successful completion"],
                )
            ]

    def _generate_summary_report(self) -> None:
        """Generate and display a summary report of all test results."""
        logger.info("\n" + "=" * 80)
        logger.info("QA FUNCTIONAL TESTING SUMMARY")
        logger.info("=" * 80)

        total_tests = 0
        passed_tests = 0
        failed_tests = 0

        for test_category, category_results in self.results.items():
            logger.info(f"\n📊 {test_category.upper()}:")

            if isinstance(category_results, dict) and "error" not in category_results:
                for test_name, test_result in category_results.items():
                    if isinstance(test_result, dict):
                        status = test_result.get("status", "unknown")
                        score = test_result.get("overall_score", 0)

                        if status == "success":
                            logger.info(f"  ✅ {test_name}: {status} (Score: {score:.1f}%)")
                            passed_tests += 1
                        elif status == "partial":
                            logger.info(f"  ⚠️  {test_name}: {status} (Score: {score:.1f}%)")
                            passed_tests += 1  # Count partial as passed for summary
                        else:
                            # Handle None score gracefully
                            if score is not None:
                                logger.info(f"  ❌ {test_name}: {status} (Score: {score:.1f}%)")
                            else:
                                logger.info(f"  ❌ {test_name}: {status}")
                            failed_tests += 1

                        total_tests += 1

                        # Show recommendations if verbose
                        if self.verbose and test_result.get("recommendations"):
                            for rec in test_result["recommendations"]:
                                logger.info(f"    💡 {rec}")
            else:
                logger.info(f"  ❌ Category failed: {category_results.get('error', 'Unknown error')}")
                failed_tests += 1
                total_tests += 1

        # Overall summary
        logger.info("\n📈 OVERALL RESULTS:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Passed: {passed_tests}")
        logger.info(f"  Failed: {failed_tests}")

        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            logger.info(f"  Success Rate: {success_rate:.1f}%")

            if success_rate >= 80:
                logger.info("  🎉 QA system is functioning well!")
            elif success_rate >= 60:
                logger.info("  ⚠️  QA system has some issues that should be addressed")
            else:
                logger.info("  🚨 QA system has significant issues requiring attention")

        logger.info("=" * 80)


def main():
    """Main entry point for the functional testing script."""
    parser = argparse.ArgumentParser(description="Functional QA Testing for Aurite Framework")
    parser.add_argument(
        "--component-type",
        choices=["agent", "workflow", "all"],
        default="all",
        help="Type of component to test (default: all)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL for the Aurite API (default: http://localhost:8000)",
    )

    args = parser.parse_args()

    # Create and run the functional tester
    tester = QAFunctionalTester(api_url=args.api_url, verbose=args.verbose)

    try:
        results = asyncio.run(tester.run_all_tests(args.component_type))

        # Exit with appropriate code
        if any("error" in str(result) for result in results.values()):
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\n🛑 Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"🚨 Functional testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
