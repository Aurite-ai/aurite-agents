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
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# Color codes for better output formatting
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


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
                            "case_results": result.get("case_results", {}),  # Store case results for detailed analysis
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

                logger.info(f"\n  � Testing {config_name}...")

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
                            "case_results": result.get("case_results", {}),  # Store case results for detailed analysis
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
        Create standardized test cases for all agents to ensure fair comparison.

        All agents get the same challenging test cases to see how they perform
        against the same criteria, rather than getting easier/harder tests
        based on their expected performance level.

        Args:
            config_name: Name of the agent configuration being tested

        Returns:
            List of EvaluationCase objects (same for all agents)
        """
        # Use the same challenging test cases for ALL agents
        # This allows us to see how good/average/poor agents perform on the same tasks
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
            EvaluationCase(
                input="Create a comprehensive travel plan based on weather in three cities",
                expectations=[
                    "The response uses weather tools to get weather data for multiple cities",
                    "The response uses planning tools to create and save a structured plan",
                    "The response provides detailed recommendations for all three cities",
                    "The response demonstrates coordination between weather and planning tools",
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
            # Poor workflow with single step should fail multi-step coordination expectations
            return [
                EvaluationCase(
                    input="Get weather for Paris and create a detailed activity plan",
                    expectations=[
                        "The workflow demonstrates multi-step processing",
                        "Weather data flows properly between workflow steps",
                        "The workflow shows coordination between multiple agents",
                        "The final output shows evidence of step-by-step refinement",
                    ],
                ),
                EvaluationCase(
                    input="Compare weather in three cities and recommend the best for vacation",
                    expectations=[
                        "The workflow processes multiple cities through separate steps",
                        "Analysis step compares data from weather retrieval step",
                        "Planning step creates recommendations based on analysis",
                        "The workflow demonstrates proper data flow between agents",
                    ],
                ),
                EvaluationCase(
                    input="Create a comprehensive weather-based travel itinerary",
                    expectations=[
                        "The workflow executes multiple coordinated steps",
                        "Each step builds upon the previous step's output",
                        "The workflow shows proper agent coordination",
                        "The final output demonstrates multi-step processing",
                    ],
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
        """Generate and display a comprehensive summary report of all test results."""
        from datetime import datetime

        # Show detailed case results first
        for _test_category, category_results in self.results.items():
            if isinstance(category_results, dict) and "error" not in category_results:
                for test_name, test_result in category_results.items():
                    if isinstance(test_result, dict):
                        # Show detailed case results
                        self._print_detailed_case_results(test_name, test_result)

        # Then show comprehensive summary
        logger.info("\n" + "📊" * 30 + " QA TESTING SUMMARY " + "📊" * 30)
        logger.info(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        logger.info("\n📈 Agent Performance Analysis:")
        logger.info("-" * 60)

        # Agent QA Results
        agent_results = self.results.get("agent_qa", {})
        if agent_results and "error" not in agent_results:
            logger.info("\n🤖 Agent QA Results (Same Test Cases for All Agents):")

            good_agent = agent_results.get("good_agent_qa", {})
            average_agent = agent_results.get("average_agent_qa", {})
            poor_agent = agent_results.get("poor_agent_qa", {})

            if "error" not in good_agent:
                score = good_agent.get("overall_score", 0)
                passed = good_agent.get("passed_cases", 0)
                total = good_agent.get("total_cases", 0)
                status_emoji = "✅" if score > 75 else "⚠️" if score > 50 else "❌"
                logger.info(f"   {status_emoji} Good Agent: {score:.1f}% ({passed}/{total} passed)")
            else:
                logger.info(f"   ❌ Good Agent: FAILED - {good_agent['error']}")

            if "error" not in average_agent:
                score = average_agent.get("overall_score", 0)
                passed = average_agent.get("passed_cases", 0)
                total = average_agent.get("total_cases", 0)
                status_emoji = "✅" if score > 50 else "⚠️" if score > 25 else "❌"
                logger.info(f"   {status_emoji} Average Agent: {score:.1f}% ({passed}/{total} passed)")
            else:
                logger.info(f"   ❌ Average Agent: FAILED - {average_agent['error']}")

            if "error" not in poor_agent:
                score = poor_agent.get("overall_score", 0)
                passed = poor_agent.get("passed_cases", 0)
                total = poor_agent.get("total_cases", 0)
                status_emoji = "✅" if score > 25 else "⚠️" if score > 10 else "❌"
                logger.info(f"   {status_emoji} Poor Agent: {score:.1f}% ({passed}/{total} passed)")
            else:
                logger.info(f"   ❌ Poor Agent: FAILED - {poor_agent['error']}")

        # Workflow QA Results
        workflow_results = self.results.get("workflow_qa", {})
        if workflow_results and "error" not in workflow_results:
            logger.info("\n🔄 Workflow QA Results:")

            good_workflow = workflow_results.get("good_workflow_qa", {})
            average_workflow = workflow_results.get("average_workflow_qa", {})
            poor_workflow = workflow_results.get("poor_workflow_qa", {})

            if "error" not in good_workflow:
                score = good_workflow.get("overall_score", 0)
                passed = good_workflow.get("passed_cases", 0)
                total = good_workflow.get("total_cases", 0)
                status_emoji = "✅" if score > 75 else "⚠️" if score > 50 else "❌"
                logger.info(f"   {status_emoji} Good Workflow: {score:.1f}% ({passed}/{total} passed)")
            else:
                logger.info(f"   ❌ Good Workflow: FAILED - {good_workflow['error']}")

            if "error" not in average_workflow:
                score = average_workflow.get("overall_score", 0)
                passed = average_workflow.get("passed_cases", 0)
                total = average_workflow.get("total_cases", 0)
                status_emoji = "✅" if score > 50 else "⚠️" if score > 25 else "❌"
                logger.info(f"   {status_emoji} Average Workflow: {score:.1f}% ({passed}/{total} passed)")
            else:
                logger.info(f"   ❌ Average Workflow: FAILED - {average_workflow['error']}")

            if "error" not in poor_workflow:
                score = poor_workflow.get("overall_score", 0)
                passed = poor_workflow.get("passed_cases", 0)
                total = poor_workflow.get("total_cases", 0)
                status_emoji = "✅" if score > 25 else "⚠️" if score > 10 else "❌"
                logger.info(f"   {status_emoji} Poor Workflow: {score:.1f}% ({passed}/{total} passed)")
            else:
                logger.info(f"   ❌ Poor Workflow: FAILED - {poor_workflow['error']}")

        # QA Engine Integration Results
        integration_results = self.results.get("qa_engine_integration", {})
        if integration_results and "error" not in integration_results:
            logger.info("\n🔧 QA Engine Integration:")

            agent_integration = integration_results.get("agent_through_engine", {})
            workflow_integration = integration_results.get("workflow_through_engine", {})

            if "error" not in agent_integration:
                score = agent_integration.get("overall_score", 0)
                status_emoji = "✅" if score > 75 else "⚠️" if score > 50 else "❌"
                logger.info(f"   {status_emoji} Agent Integration: {score:.1f}%")
            else:
                logger.info(f"   ❌ Agent Integration: FAILED - {agent_integration['error']}")

            if "error" not in workflow_integration:
                score = workflow_integration.get("overall_score", 0)
                status_emoji = "✅" if score > 75 else "⚠️" if score > 50 else "❌"
                logger.info(f"   {status_emoji} Workflow Integration: {score:.1f}%")
            else:
                logger.info(f"   ❌ Workflow Integration: FAILED - {workflow_integration['error']}")

        # Analysis and Insights
        logger.info("\n🔍 QA System Analysis:")

        if agent_results and "error" not in agent_results:
            good_score = good_agent.get("overall_score", 0) if "error" not in good_agent else 0
            average_score = average_agent.get("overall_score", 0) if "error" not in average_agent else 0
            poor_score = poor_agent.get("overall_score", 0) if "error" not in poor_agent else 0

            logger.info("🤖 Agent Performance Differentiation:")
            if good_score > average_score > poor_score:
                logger.info("✅ Agent quality properly differentiated: Good > Average > Poor")
                score_spread = good_score - poor_score
                if score_spread > 40:
                    logger.info(f"✅ Excellent score spread ({score_spread:.1f}%) - clear differentiation")
                elif score_spread > 20:
                    logger.info(f"⚠️  Moderate score spread ({score_spread:.1f}%) - some differentiation")
                else:
                    logger.info(f"❌ Low score spread ({score_spread:.1f}%) - poor differentiation")
            else:
                logger.info("⚠️  Agent quality differentiation needs review")
                logger.info(f"   Scores: Good={good_score:.1f}%, Average={average_score:.1f}%, Poor={poor_score:.1f}%")

        # Test Case Analysis
        logger.info("\n📋 Test Case Analysis:")
        logger.info("✅ All agents tested with identical challenging test cases")
        logger.info("✅ Fair comparison - no agent-specific test case bias")
        logger.info("✅ Standardized expectations across all agent types")

        # Security Fix Validation
        logger.info("\n🔒 Security Validation:")
        if poor_agent and "error" not in poor_agent:
            poor_case_results = poor_agent.get("case_results", {})
            security_validated = False
            for case_result in poor_case_results.values():
                analysis = case_result.get("analysis", "")
                if "no tools" in analysis.lower() or "empty mcp_servers" in analysis.lower():
                    security_validated = True
                    break

            if security_validated:
                logger.info("✅ Security fix validated - poor agent properly blocked from unauthorized tools")
            else:
                logger.info("⚠️  Security validation inconclusive - check poor agent tool access")
        else:
            logger.info("⚠️  Could not validate security fix - poor agent test failed")

        # Overall Assessment
        logger.info("\n🎯 Overall QA System Assessment:")

        total_tests = 0
        passed_tests = 0

        for category_results in self.results.values():
            if isinstance(category_results, dict) and "error" not in category_results:
                for test_result in category_results.values():
                    if isinstance(test_result, dict) and "status" in test_result:
                        total_tests += 1
                        if test_result.get("status") in ["success", "partial"]:
                            passed_tests += 1

        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            logger.info(f"📊 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")

            if success_rate >= 80:
                logger.info("🎉 QA system is functioning excellently!")
            elif success_rate >= 60:
                logger.info("✅ QA system is functioning well with minor issues")
            elif success_rate >= 40:
                logger.info("⚠️  QA system has some issues that should be addressed")
            else:
                logger.info("🚨 QA system has significant issues requiring immediate attention")

        logger.info("\n" + "=" * 80)

    def _print_detailed_case_results(self, test_name: str, test_result: Dict[str, Any]) -> None:
        """
        Print detailed case results for debugging.

        Args:
            test_name: Name of the test being analyzed
            test_result: Test result dictionary containing case_results
        """
        # Add colored header based on test quality
        if "good" in test_name:
            header = f"\n{Colors.GREEN}{'🟢' * 20} DETAILED RESULTS: {test_name.upper()} {'🟢' * 20}{Colors.END}"
        elif "average" in test_name:
            header = f"\n{Colors.YELLOW}{'🟡' * 20} DETAILED RESULTS: {test_name.upper()} {'🟡' * 20}{Colors.END}"
        else:  # poor
            header = f"\n{Colors.RED}{'🔴' * 20} DETAILED RESULTS: {test_name.upper()} {'🔴' * 20}{Colors.END}"

        logger.info(header)

        # Get the full API response if available
        if "case_results" in test_result:
            case_results = test_result["case_results"]

            for i, (case_id, case_result) in enumerate(case_results.items(), 1):
                grade = case_result.get("grade", "N/A")

                # Color code the grade
                if grade == "PASS":
                    grade_colored = f"{Colors.GREEN}✅ PASS{Colors.END}"
                elif grade == "FAIL":
                    grade_colored = f"{Colors.RED}❌ FAIL{Colors.END}"
                else:
                    grade_colored = f"{Colors.YELLOW}⚠️ {grade}{Colors.END}"

                logger.info(f"\n{Colors.BOLD}📝 Test Case {i} ({case_id[:8]}){Colors.END}")

                # Make the input text purple
                input_text = case_result.get("input", "N/A")
                logger.info(f"   Input: {Colors.MAGENTA}{input_text}{Colors.END}")

                logger.info(f"   {Colors.BOLD}Grade:{Colors.END} {grade_colored}")
                exec_time = case_result.get("execution_time", "N/A")
                logger.info(f"   {Colors.BLUE}Execution Time:{Colors.END} {exec_time}s")

                logger.info(f"   {Colors.CYAN}Analysis:{Colors.END} {case_result.get('analysis', 'N/A')}")

                # Show broken expectations with color
                broken_expectations = case_result.get("expectations_broken", [])
                if broken_expectations:
                    logger.info(f"   {Colors.RED}Broken Expectations:{Colors.END}")
                    for expectation in broken_expectations:
                        logger.info(f"     {Colors.RED}❌{Colors.END} {expectation}")

                output = case_result.get("output", "N/A")
                if output and output != "N/A":
                    if isinstance(output, str):
                        # Split output into conversation and final response
                        if "=== FINAL RESPONSE ===" in output:
                            conversation, final_response = output.split("=== FINAL RESPONSE ===", 1)
                            # Remove any old header from conversation
                            conversation = conversation.replace(
                                "========================== FULL CONVERSATION HISTORY ==========================\n", ""
                            ).strip()
                            logger.info(f"\n{Colors.BLUE}{'=' * 15} FULL CONVERSATION HISTORY {'=' * 15}{Colors.END}")
                            logger.info(conversation)
                            logger.info(f"{Colors.BLUE}{'*' * 50}{Colors.END}")
                        else:
                            # No final response marker, print as is
                            cleaned_output = output.replace(
                                "========================== FULL CONVERSATION HISTORY ==========================\n", ""
                            ).strip()
                            logger.info(f"\n{Colors.BLUE}{'=' * 15} FULL CONVERSATION HISTORY {'=' * 15}{Colors.END}")
                            logger.info(cleaned_output)
                            logger.info(f"{Colors.BLUE}{'*' * 50}{Colors.END}")
                    else:
                        logger.info(str(output))


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
