#!/usr/bin/env python3
"""
Functional QA Testing Script for the Aurite Framework.

This refactored version uses declarative evaluation configurations
stored in the shared_configs directory, making test management easier
and more maintainable.

Usage:
    python scripts/qa/functional_qa_test.py [--component-type agent|workflow|all] [--evaluation-mode live|manual|function] [--verbose] [--api-url URL]

Examples:
    python scripts/qa/functional_qa_test.py --component-type agent
    python scripts/qa/functional_qa_test.py --component-type agent --evaluation-mode manual
    python scripts/qa/functional_qa_test.py --component-type agent --evaluation-mode function
    python scripts/qa/functional_qa_test.py --component-type workflow --verbose
    python scripts/qa/functional_qa_test.py --api-url http://localhost:8000 --evaluation-mode manual
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

import httpx

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

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
    Simplified functional tester for the QA system using evaluation configuration names.

    This version just specifies evaluation configuration names and lets the API
    handle loading everything through the ConfigManager.
    """

    def __init__(self, api_url: str = "http://localhost:8000", verbose: bool = False, evaluation_mode: str = "live"):
        """
        Initialize the functional tester.

        Args:
            api_url: Base URL for the Aurite API
            verbose: Enable verbose logging
            evaluation_mode: Mode for evaluation ("live" or "manual")
        """
        self.api_url = api_url.rstrip("/")
        self.verbose = verbose
        self.evaluation_mode = evaluation_mode
        if verbose:
            # Enable debug logging for our logger but suppress httpx verbose output
            logging.getLogger(__name__).setLevel(logging.DEBUG)
            # Suppress httpx debug logging to avoid verbose HTTP headers
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("httpcore").setLevel(logging.WARNING)

        # Test results storage
        self.results: Dict[str, Any] = {}

        # Get API key from environment or use default
        self.api_key = os.getenv("AURITE_API_KEY", "test-api-key")

        # Predefined evaluation configurations
        self.agent_evaluations = [
            "weather_agents_evaluation"  # Single config that tests all three agents
        ]

        self.manual_agent_evaluations = [
            "manual_weather_agents_evaluation"  # Manual output evaluation
        ]

        self.function_agent_evaluations = [
            "function_weather_agents_evaluation"  # Function-based evaluation
        ]

        self.workflow_evaluations = [
            # Add workflow evaluation names here when available
        ]

    async def run_all_tests(self, component_type: str = "all") -> Dict[str, Any]:
        """
        Run all QA functional tests using evaluation configurations.

        Args:
            component_type: Type of component to test ("agent", "workflow", or "all")

        Returns:
            Dictionary containing all test results
        """
        self._print_header()

        # Check if API is running
        if not await self._check_api_health():
            logger.error(f"{Colors.RED}❌ API is not running or not accessible{Colors.END}")
            logger.info("Please start the API server with: aurite api")
            return {"error": "API not accessible"}

        if component_type in ["agent", "all"]:
            logger.info(f"\n{Colors.CYAN}🤖 Testing Agent QA System...{Colors.END}")
            agent_results = await self._test_agents()
            self.results["agent_qa"] = agent_results

        if component_type in ["workflow", "all"]:
            logger.info(f"\n{Colors.CYAN}🔄 Testing Workflow QA System...{Colors.END}")
            workflow_results = await self._test_workflows()
            self.results["workflow_qa"] = workflow_results

        # Generate summary report
        self._generate_summary_report()

        return self.results

    def _print_header(self):
        """Print a formatted header for the test run."""
        logger.info("=" * 80)
        logger.info(f"{Colors.BOLD}AURITE QA FUNCTIONAL TESTING (Configuration-Based){Colors.END}")
        logger.info("=" * 80)
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Evaluation Mode: {self.evaluation_mode.upper()}")

        # Show appropriate evaluation counts based on mode
        if self.evaluation_mode == "manual":
            logger.info(f"Agent Evaluations: {len(self.manual_agent_evaluations)}")
        elif self.evaluation_mode == "function":
            logger.info(f"Agent Evaluations: {len(self.function_agent_evaluations)}")
        else:
            logger.info(f"Agent Evaluations: {len(self.agent_evaluations)}")
        logger.info(f"Workflow Evaluations: {len(self.workflow_evaluations)}")

    async def _check_api_health(self) -> bool:
        """Check if the API is running and accessible."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"API health check failed: {e}")
            return False

    async def _test_agents(self) -> Dict[str, Any]:
        """Test agents using evaluation configurations."""
        results = {}

        # Choose evaluation list based on mode
        if self.evaluation_mode == "manual":
            evaluations_to_run = self.manual_agent_evaluations
        elif self.evaluation_mode == "function":
            evaluations_to_run = self.function_agent_evaluations
        else:
            evaluations_to_run = self.agent_evaluations

        async with httpx.AsyncClient(timeout=60.0) as client:
            for config_name in evaluations_to_run:
                logger.info(f"\n  📋 Testing {config_name}...")

                try:
                    # Use the API endpoint that loads evaluation configs directly
                    response = await client.post(
                        f"{self.api_url}/testing/evaluate/{config_name}", headers={"X-API-Key": self.api_key}
                    )

                    if response.status_code == 200:
                        result = response.json()
                        results[config_name] = self._process_result(result)
                        self._print_result_summary(config_name, results[config_name])
                    else:
                        error_msg = f"API returned status {response.status_code}: {response.text}"
                        logger.error(f"    ❌ {config_name}: {error_msg}")
                        results[config_name] = {"status": "error", "error": error_msg}

                except Exception as e:
                    logger.error(f"    ❌ {config_name}: Failed - {str(e)}")
                    results[config_name] = {"status": "error", "error": str(e)}

        return results

    async def _test_workflows(self) -> Dict[str, Any]:
        """Test workflows using evaluation configurations."""
        results = {}

        if not self.workflow_evaluations:
            logger.info("    ℹ️  No workflow evaluation configurations defined")
            return results

        async with httpx.AsyncClient(timeout=120.0) as client:
            for config_name in self.workflow_evaluations:
                logger.info(f"\n  📋 Testing {config_name}...")

                try:
                    # Use the API endpoint that loads evaluation configs directly
                    response = await client.post(
                        f"{self.api_url}/testing/evaluate/{config_name}", headers={"X-API-Key": self.api_key}
                    )

                    if response.status_code == 200:
                        result = response.json()
                        results[config_name] = self._process_result(result)
                        self._print_result_summary(config_name, results[config_name])
                    else:
                        error_msg = f"API returned status {response.status_code}: {response.text}"
                        logger.error(f"    ❌ {config_name}: {error_msg}")
                        results[config_name] = {"status": "error", "error": error_msg}

                except Exception as e:
                    logger.error(f"    ❌ {config_name}: Failed - {str(e)}")
                    results[config_name] = {"status": "error", "error": str(e)}

        return results

    def _process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and extract key information from API result.

        Now handles both single component results and multi-component results.

        Args:
            result: Raw API response (now a dict with component names as keys)

        Returns:
            Processed result dictionary with component-level results
        """
        # Check if this is a multi-component result (dict with component names as keys)
        # But exclude single manual output evaluations which also have this structure
        if (
            isinstance(result, dict)
            and all(isinstance(v, dict) and "status" in v for v in result.values())
            and len(result) > 1
        ):
            # Multi-component result - process each component
            processed_components = {}
            total_score = 0
            total_passed = 0
            total_failed = 0
            total_cases = 0

            for component_name, component_result in result.items():
                processed_components[component_name] = {
                    "status": component_result.get("status", "unknown"),
                    "overall_score": component_result.get("overall_score", 0),
                    "passed_cases": component_result.get("passed_cases", 0),
                    "failed_cases": component_result.get("failed_cases", 0),
                    "total_cases": component_result.get("total_cases", 0),
                    "recommendations": component_result.get("recommendations", []),
                    "case_results": component_result.get("case_results", {}),
                }

                # Aggregate totals
                total_score += component_result.get("overall_score", 0)
                total_passed += component_result.get("passed_cases", 0)
                total_failed += component_result.get("failed_cases", 0)
                total_cases += component_result.get("total_cases", 0)

            # Calculate average score
            avg_score = total_score / len(result) if result else 0

            return {
                "type": "multi_component",
                "components": processed_components,
                "summary": {
                    "overall_score": avg_score,
                    "passed_cases": total_passed,
                    "failed_cases": total_failed,
                    "total_cases": total_cases,
                    "component_count": len(result),
                },
            }
        else:
            # Single component result - extract from the nested structure
            # The API now returns {component_name: result} even for single components
            if isinstance(result, dict) and len(result) == 1:
                # Extract the single component result
                component_name, component_result = next(iter(result.items()))
                return {
                    "type": "single_component",
                    "component_name": component_name,
                    "status": component_result.get("status", "unknown"),
                    "overall_score": component_result.get("overall_score", 0),
                    "passed_cases": component_result.get("passed_cases", 0),
                    "failed_cases": component_result.get("failed_cases", 0),
                    "total_cases": component_result.get("total_cases", 0),
                    "recommendations": component_result.get("recommendations", []),
                    "case_results": component_result.get("case_results", {}),
                }
            else:
                # Legacy format (shouldn't happen with new API)
                return {
                    "type": "single_component",
                    "status": result.get("status", "unknown"),
                    "overall_score": result.get("overall_score", 0),
                    "passed_cases": result.get("passed_cases", 0),
                    "failed_cases": result.get("failed_cases", 0),
                    "total_cases": result.get("total_cases", 0),
                    "recommendations": result.get("recommendations", []),
                    "case_results": result.get("case_results", {}),
                }

    def _print_result_summary(self, eval_name: str, result: Dict[str, Any]):
        """
        Print a summary of evaluation results.

        Now handles both single and multi-component results.

        Args:
            eval_name: Name of the evaluation
            result: Processed result dictionary
        """
        if result.get("status") == "error":
            return

        if result.get("type") == "multi_component":
            # Multi-component result
            summary = result.get("summary", {})
            score = summary.get("overall_score", 0)
            passed = summary.get("passed_cases", 0)
            total = summary.get("total_cases", 0)
            component_count = summary.get("component_count", 0)

            # Determine status emoji based on score
            if score >= 75:
                status_emoji = f"{Colors.GREEN}✅{Colors.END}"
            elif score >= 50:
                status_emoji = f"{Colors.YELLOW}⚠️{Colors.END}"
            else:
                status_emoji = f"{Colors.RED}❌{Colors.END}"

            logger.info(
                f"    {status_emoji} {eval_name}: {score:.1f}% avg ({passed}/{total} passed across {component_count} components)"
            )

            # Print individual component results
            components = result.get("components", {})
            for component_name, component_result in components.items():
                comp_score = component_result.get("overall_score", 0)
                comp_passed = component_result.get("passed_cases", 0)
                comp_total = component_result.get("total_cases", 0)

                if comp_score >= 75:
                    comp_emoji = f"{Colors.GREEN}✅{Colors.END}"
                elif comp_score >= 50:
                    comp_emoji = f"{Colors.YELLOW}⚠️{Colors.END}"
                else:
                    comp_emoji = f"{Colors.RED}❌{Colors.END}"

                logger.info(
                    f"      {comp_emoji} {component_name}: {comp_score:.1f}% ({comp_passed}/{comp_total} passed)"
                )

                # Print detailed results if verbose
                if self.verbose and component_result.get("case_results"):
                    logger.info(f"\n{Colors.BOLD}    📋 Detailed results for {component_name}:{Colors.END}")
                    self._print_detailed_results(component_result["case_results"])

        else:
            # Single component result (legacy format)
            score = result.get("overall_score", 0)
            passed = result.get("passed_cases", 0)
            total = result.get("total_cases", 0)

            # Determine status emoji based on score
            if score >= 75:
                status_emoji = f"{Colors.GREEN}✅{Colors.END}"
            elif score >= 50:
                status_emoji = f"{Colors.YELLOW}⚠️{Colors.END}"
            else:
                status_emoji = f"{Colors.RED}❌{Colors.END}"

            logger.info(f"    {status_emoji} {eval_name}: {score:.1f}% ({passed}/{total} passed)")

            # Print detailed results if verbose
            if self.verbose and result.get("case_results"):
                self._print_detailed_results(result["case_results"])

    def _print_detailed_results(self, case_results: Dict[str, Any]):
        """
        Print detailed results for each test case.

        Args:
            case_results: Dictionary of case results
        """
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
                        conversation = conversation.replace("=== FULL CONVERSATION HISTORY ===\n", "").strip()
                        logger.info(f"\n{Colors.BLUE}{'=' * 15} FULL CONVERSATION HISTORY {'=' * 15}{Colors.END}")
                        logger.info(conversation)
                        logger.info(f"{Colors.BLUE}{'*' * 50}{Colors.END}")
                    else:
                        # No final response marker, print as is
                        cleaned_output = output.replace("=== FULL CONVERSATION HISTORY ===\n", "").strip()
                        logger.info(f"\n{Colors.BLUE}{'=' * 15} FULL CONVERSATION HISTORY {'=' * 15}{Colors.END}")
                        logger.info(cleaned_output)
                        logger.info(f"{Colors.BLUE}{'*' * 50}{Colors.END}")
                else:
                    logger.info(str(output))

    def _generate_summary_report(self):
        """Generate and display a comprehensive summary report."""
        from datetime import datetime

        logger.info("\n" + "=" * 80)
        logger.info(f"{Colors.BOLD}📊 QA TESTING SUMMARY{Colors.END}")
        logger.info(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        # Agent QA Results
        agent_results = self.results.get("agent_qa", {})
        if agent_results and "error" not in agent_results:
            logger.info(f"\n{Colors.CYAN}🤖 Agent QA Results:{Colors.END}")
            self._print_category_summary(agent_results)

        # Workflow QA Results
        workflow_results = self.results.get("workflow_qa", {})
        if workflow_results and "error" not in workflow_results:
            logger.info(f"\n{Colors.CYAN}🔄 Workflow QA Results:{Colors.END}")
            self._print_category_summary(workflow_results)

        # Overall Assessment
        self._print_overall_assessment()

    def _print_category_summary(self, results: Dict[str, Any]):
        """
        Print summary for a category of tests.

        Now handles both single and multi-component results.

        Args:
            results: Category results dictionary
        """
        for eval_name, result in results.items():
            if result.get("status") == "error":
                logger.info(f"   ❌ {eval_name}: FAILED - {result['error']}")
            elif result.get("type") == "multi_component":
                # Multi-component result
                summary = result.get("summary", {})
                score = summary.get("overall_score", 0)
                passed = summary.get("passed_cases", 0)
                total = summary.get("total_cases", 0)
                component_count = summary.get("component_count", 0)

                if score >= 75:
                    status = f"{Colors.GREEN}✅{Colors.END}"
                elif score >= 50:
                    status = f"{Colors.YELLOW}⚠️{Colors.END}"
                else:
                    status = f"{Colors.RED}❌{Colors.END}"

                logger.info(
                    f"   {status} {eval_name}: {score:.1f}% avg ({passed}/{total} passed across {component_count} components)"
                )

                # Show individual component summaries
                components = result.get("components", {})
                for component_name, component_result in components.items():
                    comp_score = component_result.get("overall_score", 0)
                    comp_passed = component_result.get("passed_cases", 0)
                    comp_total = component_result.get("total_cases", 0)

                    if comp_score >= 75:
                        comp_status = f"{Colors.GREEN}✅{Colors.END}"
                    elif comp_score >= 50:
                        comp_status = f"{Colors.YELLOW}⚠️{Colors.END}"
                    else:
                        comp_status = f"{Colors.RED}❌{Colors.END}"

                    logger.info(
                        f"     {comp_status} {component_name}: {comp_score:.1f}% ({comp_passed}/{comp_total} passed)"
                    )
            else:
                # Single component result (legacy format)
                score = result.get("overall_score", 0)
                passed = result.get("passed_cases", 0)
                total = result.get("total_cases", 0)

                if score >= 75:
                    status = f"{Colors.GREEN}✅{Colors.END}"
                elif score >= 50:
                    status = f"{Colors.YELLOW}⚠️{Colors.END}"
                else:
                    status = f"{Colors.RED}❌{Colors.END}"

                logger.info(f"   {status} {eval_name}: {score:.1f}% ({passed}/{total} passed)")

    def _print_overall_assessment(self):
        """Print overall assessment of the QA system."""
        logger.info(f"\n{Colors.CYAN}🎯 Overall QA System Assessment:{Colors.END}")

        total_components = 0
        passed_components = 0
        total_score = 0.0

        for category_results in self.results.values():
            if isinstance(category_results, dict) and "error" not in category_results:
                for test_result in category_results.values():
                    if isinstance(test_result, dict):
                        if test_result.get("type") == "multi_component":
                            # Multi-component result - count individual components
                            components = test_result.get("components", {})
                            for _component_name, component_result in components.items():
                                total_components += 1
                                comp_score = component_result.get("overall_score", 0)
                                total_score += comp_score

                                # Consider passed if score >= 50%
                                if comp_score >= 50:
                                    passed_components += 1
                        elif "status" in test_result:
                            # Single component result (legacy format)
                            total_components += 1
                            score = test_result.get("overall_score", 0)
                            total_score += score

                            if test_result.get("status") in ["success", "partial"] or score >= 50:
                                passed_components += 1

        if total_components > 0:
            success_rate = (passed_components / total_components) * 100
            avg_score = total_score / total_components

            logger.info(
                f"📊 Overall Success Rate: {success_rate:.1f}% ({passed_components}/{total_components} components)"
            )
            logger.info(f"📊 Average Score: {avg_score:.1f}%")

            if success_rate >= 80:
                logger.info(f"{Colors.GREEN}🎉 QA system is functioning excellently!{Colors.END}")
            elif success_rate >= 60:
                logger.info(f"{Colors.GREEN}✅ QA system is functioning well with minor issues{Colors.END}")
            elif success_rate >= 40:
                logger.info(f"{Colors.YELLOW}⚠️  QA system has some issues that should be addressed{Colors.END}")
            else:
                logger.info(
                    f"{Colors.RED}🚨 QA system has significant issues requiring immediate attention{Colors.END}"
                )
        else:
            logger.info("📊 No test results to assess")

        logger.info("\n" + "=" * 80)


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
    parser.add_argument(
        "--evaluation-mode",
        choices=["live", "manual", "function"],
        default="live",
        help="Evaluation mode: 'live' runs components, 'manual' uses pre-recorded outputs, 'function' uses custom run function (default: live)",
    )

    args = parser.parse_args()

    # Create and run the functional tester
    tester = QAFunctionalTester(api_url=args.api_url, verbose=args.verbose, evaluation_mode=args.evaluation_mode)

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
