#!/usr/bin/env python3
"""
Advanced Test Runner for Aurite Framework

This script provides optimized test execution strategies with comprehensive
reporting and performance monitoring.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any


class TestRunner:
    """Advanced test runner with optimization strategies."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.test_results = {}
        
    def run_fast_tests(self) -> Dict[str, Any]:
        """Run fast unit tests first for quick feedback."""
        print("🚀 Running Fast Tests (Unit Tests)")
        print("=" * 50)
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit/",
            "-v", "--tb=short",
            "-m", "not slow",
            "--timeout=10"
        ]
        
        return self._execute_test_command(cmd, "fast_tests")
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests with proper isolation."""
        print("🔧 Running Integration Tests")
        print("=" * 50)
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/integration/",
            "-v", "--tb=short",
            "--timeout=30",
            "--maxfail=5"
        ]
        
        return self._execute_test_command(cmd, "integration_tests")
    
    def run_mcp_server_tests(self) -> Dict[str, Any]:
        """Run MCP server tests with connection management."""
        print("🌐 Running MCP Server Tests")
        print("=" * 50)
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/integration/mcp_servers/",
            "-v", "--tb=short",
            "-m", "mcp_server",
            "--timeout=30"
        ]
        
        return self._execute_test_command(cmd, "mcp_server_tests")
    
    def run_orchestration_tests(self) -> Dict[str, Any]:
        """Run orchestration tests with enhanced isolation."""
        print("🎼 Running Orchestration Tests")
        print("=" * 50)
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/integration/orchestration/",
            "-v", "--tb=short",
            "-m", "orchestration",
            "--timeout=45",
            "--maxfail=3"
        ]
        
        return self._execute_test_command(cmd, "orchestration_tests")
    
    def run_smoke_tests(self) -> Dict[str, Any]:
        """Run smoke tests for basic functionality verification."""
        print("💨 Running Smoke Tests")
        print("=" * 50)
        
        # Select a few critical tests from each category
        smoke_tests = [
            "tests/unit/config/test_config_manager.py::test_config_manager_initialization",
            "tests/integration/mcp_servers/test_stdio.py::test_stdio_server_working",
            "tests/integration/agent/test_agent_integration.py::test_agent_basic_functionality"
        ]
        
        cmd = [
            sys.executable, "-m", "pytest",
            *smoke_tests,
            "-v", "--tb=short",
            "--timeout=15"
        ]
        
        return self._execute_test_command(cmd, "smoke_tests")
    
    def run_parallel_tests(self) -> Dict[str, Any]:
        """Run tests in parallel using pytest-xdist."""
        print("⚡ Running Tests in Parallel")
        print("=" * 50)
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit/", "tests/integration/",
            "-v", "--tb=short",
            "-n", "auto",
            "--dist=worksteal",
            "--timeout=30",
            "--maxfail=10"
        ]
        
        return self._execute_test_command(cmd, "parallel_tests")
    
    def run_comprehensive_suite(self) -> Dict[str, Any]:
        """Run the complete test suite with all optimizations."""
        print("🎯 Running Comprehensive Test Suite")
        print("=" * 50)
        
        results = {}
        
        # Phase 1: Fast feedback
        results["smoke"] = self.run_smoke_tests()
        if results["smoke"]["success"]:
            print("✅ Smoke tests passed - continuing with full suite")
        else:
            print("❌ Smoke tests failed - stopping execution")
            return results
        
        # Phase 2: Unit tests
        results["unit"] = self.run_fast_tests()
        
        # Phase 3: Integration tests (grouped)
        results["mcp_servers"] = self.run_mcp_server_tests()
        results["orchestration"] = self.run_orchestration_tests()
        
        return results
    
    def run_performance_analysis(self) -> Dict[str, Any]:
        """Run tests with performance monitoring."""
        print("📊 Running Performance Analysis")
        print("=" * 50)
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit/config/",
            "-v", "--tb=short",
            "--timeout=30",
            "--benchmark-only" if self._has_pytest_benchmark() else "--durations=10"
        ]
        
        return self._execute_test_command(cmd, "performance_analysis")
    
    def _execute_test_command(self, cmd: List[str], test_type: str) -> Dict[str, Any]:
        """Execute a test command and capture results."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for any test suite
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            # Parse test results from output
            output_lines = result.stdout.split('\n')
            test_summary = self._parse_test_summary(output_lines)
            
            test_result = {
                "success": success,
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "summary": test_summary
            }
            
            # Print summary
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status} - {test_type} completed in {duration:.2f}s")
            if test_summary:
                print(f"   Tests: {test_summary}")
            print()
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ TIMEOUT - {test_type} timed out after {duration:.2f}s")
            return {
                "success": False,
                "duration": duration,
                "return_code": -1,
                "stdout": "",
                "stderr": "Test execution timed out",
                "summary": "TIMEOUT"
            }
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 ERROR - {test_type} failed with error: {e}")
            return {
                "success": False,
                "duration": duration,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "summary": "ERROR"
            }
    
    def _parse_test_summary(self, output_lines: List[str]) -> str:
        """Parse test summary from pytest output."""
        for line in output_lines:
            if "passed" in line and ("failed" in line or "error" in line or "skipped" in line):
                return line.strip()
            elif line.startswith("=") and ("passed" in line or "failed" in line):
                return line.strip("= ")
        return ""
    
    def _has_pytest_benchmark(self) -> bool:
        """Check if pytest-benchmark is available."""
        try:
            import pytest_benchmark
            return True
        except ImportError:
            return False
    
    def generate_report(self, results: Dict[str, Any]) -> None:
        """Generate a comprehensive test report."""
        print("\n" + "=" * 60)
        print("📋 TEST EXECUTION REPORT")
        print("=" * 60)
        
        total_duration = 0
        total_success = 0
        total_tests = len(results)
        
        for test_type, result in results.items():
            duration = result.get("duration", 0)
            success = result.get("success", False)
            summary = result.get("summary", "No summary")
            
            total_duration += duration
            if success:
                total_success += 1
            
            status_icon = "✅" if success else "❌"
            print(f"{status_icon} {test_type.upper():<20} {duration:>8.2f}s  {summary}")
        
        print("-" * 60)
        success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
        print(f"📊 OVERALL RESULTS:")
        print(f"   Success Rate: {success_rate:.1f}% ({total_success}/{total_tests})")
        print(f"   Total Duration: {total_duration:.2f}s")
        print(f"   Average per Suite: {total_duration/total_tests:.2f}s")
        
        if success_rate >= 95:
            print("🎉 EXCELLENT - Test suite is highly reliable!")
        elif success_rate >= 85:
            print("👍 GOOD - Test suite is mostly reliable")
        elif success_rate >= 75:
            print("⚠️  NEEDS IMPROVEMENT - Some test reliability issues")
        else:
            print("🚨 CRITICAL - Significant test reliability problems")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Advanced Test Runner for Aurite Framework")
    parser.add_argument(
        "strategy",
        choices=["fast", "integration", "mcp", "orchestration", "smoke", "parallel", "comprehensive", "performance"],
        help="Test execution strategy"
    )
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Execute the selected strategy
    if args.strategy == "fast":
        results = {"fast": runner.run_fast_tests()}
    elif args.strategy == "integration":
        results = {"integration": runner.run_integration_tests()}
    elif args.strategy == "mcp":
        results = {"mcp": runner.run_mcp_server_tests()}
    elif args.strategy == "orchestration":
        results = {"orchestration": runner.run_orchestration_tests()}
    elif args.strategy == "smoke":
        results = {"smoke": runner.run_smoke_tests()}
    elif args.strategy == "parallel":
        results = {"parallel": runner.run_parallel_tests()}
    elif args.strategy == "comprehensive":
        results = runner.run_comprehensive_suite()
    elif args.strategy == "performance":
        results = {"performance": runner.run_performance_analysis()}
    
    # Generate report if requested
    if args.report:
        runner.generate_report(results)
    
    # Exit with appropriate code
    all_success = all(result.get("success", False) for result in results.values())
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
