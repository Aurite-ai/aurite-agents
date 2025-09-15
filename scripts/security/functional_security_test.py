#!/usr/bin/env python3
"""
Functional Security Testing Script

This script performs comprehensive functional testing of the Aurite Security Framework
by testing both secure and vulnerable LLM configurations with various input types.

Usage:
    python scripts/security/functional_security_test.py

Requirements:
    - Aurite API server running on localhost:8000
    - LLM configurations loaded in the workspace
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests

# Add the src directory to the path so we can import from aurite
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class SecurityTestRunner:
    """Runs functional security tests against the Aurite API"""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "test-api-key"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json", "X-API-Key": api_key}

        # Load test data
        self.test_data_dir = Path(__file__).parent / "test_data"
        self.malicious_inputs = self._load_test_data("malicious_inputs.json")
        self.safe_inputs = self._load_test_data("safe_inputs.json")
        self.malicious_outputs = self._load_test_data("malicious_outputs.json")
        self.safe_outputs = self._load_test_data("safe_outputs.json")
        self.gray_area_inputs = self._load_test_data("gray_area_inputs.json")
        self.gray_area_outputs = self._load_test_data("gray_area_outputs.json")

    def _load_test_data(self, filename: str) -> Dict[str, List[str]]:
        """Load test data from JSON file"""
        try:
            with open(self.test_data_dir / filename, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Warning: {filename} not found, using empty test data")
            return {}

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:  # type: ignore
        """Make HTTP request to the API"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            else:
                response = requests.get(url, headers=self.headers, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            return {"error": str(e)}

    def test_configuration_security(self, config_name: str, config_data: Dict) -> Dict:
        """Test security assessment for a specific configuration"""
        print(f"\n🔍 Testing Configuration: {config_name}")
        print("=" * 60)

        # Prepare request data
        request_data = {
            "component_type": "llm",
            "component_id": config_name,
            "component_config": config_data,
            "assessment_options": {"tests": ["llm_config_audit", "token_limit_check"]},
        }

        # Make API request
        result = self._make_request("POST", "/testing/security/assess", request_data)

        if "error" in result:
            print(f"❌ Configuration test failed: {result['error']}")
            return result

        # Display results
        self._display_config_results(result)
        return result

    def test_input_security(self, config_name: str, config_data: Dict, inputs: List[str], input_type: str) -> Dict:
        """Test security assessment with specific inputs"""
        print(f"\n🔍 Testing {input_type} Inputs with {config_name}")
        print("=" * 60)

        # Prepare request data with inputs
        request_data = {
            "component_type": "llm",
            "component_id": config_name,
            "component_config": config_data,
            "assessment_options": {"tests": ["input_security_scan"], "inputs": inputs},
        }

        # Make API request
        result = self._make_request("POST", "/testing/security/assess", request_data)

        if "error" in result:
            print(f"❌ Input security test failed: {result['error']}")
            return result

        # Display results
        self._display_input_results(result, inputs, input_type)
        return result

    def _display_config_results(self, result: Dict):
        """Display configuration security test results in a readable format"""
        print(f"📊 Assessment ID: {result.get('assessment_id', 'N/A')}")
        print(f"📈 Overall Score: {result.get('overall_score', 0):.2f}/1.0")
        print(f"⚠️  Total Threats: {result.get('threats_count', 0)}")
        print(f"🚨 Critical Threats: {result.get('critical_threats_count', 0)}")
        print(f"⏱️  Duration: {result.get('duration_seconds', 0):.3f}s")
        print(f"✅ Status: {result.get('status', 'unknown')}")

        # Display recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            print("\n✅ No security recommendations - configuration looks good!")

    def _display_input_results(self, result: Dict, inputs: List[str], input_type: str):
        """Display input security test results"""
        print(f"📊 Assessment ID: {result.get('assessment_id', 'N/A')}")
        print(f"📈 Overall Score: {result.get('overall_score', 0):.2f}/1.0")
        print(f"⚠️  Total Threats: {result.get('threats_count', 0)}")
        print(f"🚨 Critical Threats: {result.get('critical_threats_count', 0)}")
        print(f"📝 Inputs Tested: {len(inputs)}")

        # Show sample inputs tested
        print(f"\n📋 Sample {input_type} Inputs Tested:")
        for i, inp in enumerate(inputs[:3], 1):  # Show first 3
            truncated = inp[:80] + "..." if len(inp) > 80 else inp
            print(f"   {i}. {truncated}")
        if len(inputs) > 3:
            print(f"   ... and {len(inputs) - 3} more")

        # Show detailed threat analysis if available
        self._display_detailed_threats(result)

        # Display recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")

    def _display_detailed_threats(self, result: Dict):
        """Display detailed threat information from the security assessment"""
        # Try to get detailed response from API
        if "assessment_id" in result:
            detailed_result = self._make_request("GET", f"/testing/security/status/{result['assessment_id']}")
            if "error" not in detailed_result:
                print("\n🔍 Detailed Security Analysis:")
                print(f"   Status: {detailed_result.get('status', 'unknown')}")
                if detailed_result.get("overall_score") is not None:
                    print(f"   Score: {detailed_result.get('overall_score', 0):.3f}")

                # Show threat detection methodology
                print("\n🛡️  Security Testing Methodology:")
                print("   • Input scanning uses LLM Guard for threat detection")
                print("   • Scans for: prompt injection, toxicity, PII, secrets, bias")
                print("   • Note: Current implementation scans inputs directly")
                print("   • Configuration impact: Limited to config auditing only")

    def _display_config_details(self, config: Dict, config_type: str):
        """Display LLM configuration details for analysis"""
        print(f"\n📋 {config_type} Details:")
        print(f"   • Name: {config.get('name', 'N/A')}")
        print(f"   • Provider: {config.get('provider', 'N/A')}")
        print(f"   • Model: {config.get('model', 'N/A')}")
        print(f"   • Temperature: {config.get('temperature', 'Not set')}")
        print(f"   • Max Tokens: {config.get('max_tokens', 'Not set')}")
        print(f"   • API Base: {config.get('api_base', 'Default')}")

        # Show system prompt (truncated for readability)
        system_prompt = config.get("default_system_prompt", "Not set")
        if system_prompt and len(system_prompt) > 100:
            system_prompt = system_prompt[:100] + "..."
        print(f"   • System Prompt: {system_prompt}")

    def test_prompt_security(self, prompts: List[str], prompt_type: str) -> Dict:
        """Test security of individual prompts using LLM Guard"""
        print(f"\n🔍 Testing {prompt_type} Prompts")
        print("=" * 60)

        # Use a dummy config since we're only testing prompts
        dummy_config = {"provider": "test", "model": "test-model", "temperature": 0.5}

        # Prepare request data with prompts
        request_data = {
            "component_type": "llm",
            "component_id": f"prompt_test_{prompt_type.lower()}",
            "component_config": dummy_config,
            "assessment_options": {"tests": ["input_security_scan"], "inputs": prompts},
        }

        # Make API request
        result = self._make_request("POST", "/testing/security/assess", request_data)

        if "error" in result:
            print(f"❌ Prompt security test failed: {result['error']}")
            return result

        # Display results
        self._display_prompt_results(result, prompts, prompt_type)
        return result

    def test_output_security(self, outputs: List[str], output_type: str) -> Dict:
        """Test security of LLM outputs using LLM Guard"""
        print(f"\n🔍 Testing {output_type} Outputs")
        print("=" * 60)

        # Use a dummy config since we're only testing outputs
        dummy_config = {"provider": "test", "model": "test-model", "temperature": 0.5}

        # Prepare request data with outputs
        request_data = {
            "component_type": "llm",
            "component_id": f"output_test_{output_type.lower()}",
            "component_config": dummy_config,
            "assessment_options": {"tests": ["output_security_scan"], "outputs": outputs},
        }

        # Make API request
        result = self._make_request("POST", "/testing/security/assess", request_data)

        if "error" in result:
            print(f"❌ Output security test failed: {result['error']}")
            return result

        # Display results
        self._display_output_results(result, outputs, output_type)
        return result

    def _display_prompt_results(self, result: Dict, prompts: List[str], prompt_type: str):
        """Display prompt security test results"""
        print(f"📊 Assessment ID: {result.get('assessment_id', 'N/A')}")
        print(f"📈 Overall Score: {result.get('overall_score', 0):.2f}/1.0")
        print(f"⚠️  Total Threats: {result.get('threats_count', 0)}")
        print(f"🚨 Critical Threats: {result.get('critical_threats_count', 0)}")
        print(f"📝 Prompts Tested: {len(prompts)}")

        # Show sample prompts tested
        print(f"\n📋 Sample {prompt_type} Prompts:")
        for i, prompt in enumerate(prompts[:3], 1):  # Show first 3
            truncated = prompt[:80] + "..." if len(prompt) > 80 else prompt
            print(f"   {i}. {truncated}")
        if len(prompts) > 3:
            print(f"   ... and {len(prompts) - 3} more")

        # Display recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")

    def _display_output_results(self, result: Dict, outputs: List[str], output_type: str):
        """Display output security test results"""
        print(f"📊 Assessment ID: {result.get('assessment_id', 'N/A')}")
        print(f"📈 Overall Score: {result.get('overall_score', 0):.2f}/1.0")
        print(f"⚠️  Total Threats: {result.get('threats_count', 0)}")
        print(f"🚨 Critical Threats: {result.get('critical_threats_count', 0)}")
        print(f"📝 Outputs Tested: {len(outputs)}")

        # Show sample outputs tested
        print(f"\n📋 Sample {output_type} Outputs:")
        for i, output in enumerate(outputs[:3], 1):  # Show first 3
            truncated = output[:80] + "..." if len(output) > 80 else output
            print(f"   {i}. {truncated}")
        if len(outputs) > 3:
            print(f"   ... and {len(outputs) - 3} more")

        # Display recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")

    def run_comprehensive_test(self):
        """Run comprehensive security testing"""
        print("🚀 Starting Comprehensive Security Testing")
        print("=" * 80)
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 API Base URL: {self.base_url}")

        print("\n🔍 Testing Focus Areas:")
        print("   1. LLM Configuration Security (temperature, tokens, system prompts, API security)")
        print("   2. Prompt Security (individual inputs scanned by LLM Guard)")
        print("   Note: This tests static security, not actual LLM responses")

        # Load configurations
        workspace_dir = Path(__file__).parent.parent.parent / "tests/fixtures/workspace/shared_configs/security"

        try:
            with open(workspace_dir / "good_llm_security.json", "r") as f:
                good_config = json.load(f)
        except FileNotFoundError:
            print("❌ Good LLM configuration not found!")
            return

        try:
            with open(workspace_dir / "bad_llm_security.json", "r") as f:
                bad_config = json.load(f)
        except FileNotFoundError:
            print("❌ Bad LLM configuration not found!")
            return

        try:
            with open(workspace_dir / "average_llm_security.json", "r") as f:
                average_config = json.load(f)
        except FileNotFoundError:
            print("❌ Average LLM configuration not found!")
            return

        results = {}

        # Test 1: LLM Configuration Security - Secure Config
        print("\n" + "🟢" * 15 + " LLM CONFIGURATION SECURITY: SECURE CONFIG " + "🟢" * 15)
        self._display_config_details(good_config, "Secure Configuration")
        results["secure_config"] = self.test_configuration_security("secure_llm_config", good_config)

        # Test 2: LLM Configuration Security - Average Config
        print("\n" + "🟡" * 15 + " LLM CONFIGURATION SECURITY: AVERAGE CONFIG " + "🟡" * 15)
        self._display_config_details(average_config, "Average Configuration")
        results["average_config"] = self.test_configuration_security("average_llm_config", average_config)

        # Test 3: LLM Configuration Security - Vulnerable Config
        print("\n" + "🔴" * 15 + " LLM CONFIGURATION SECURITY: VULNERABLE CONFIG " + "🔴" * 15)
        self._display_config_details(bad_config, "Vulnerable Configuration")
        results["vulnerable_config"] = self.test_configuration_security("vulnerable_llm_config", bad_config)

        # Test 4: Prompt Security - Safe Prompts
        if self.safe_inputs:
            print("\n" + "🟢" * 20 + " PROMPT SECURITY: SAFE PROMPTS " + "🟢" * 20)
            all_safe = []
            for _category, inputs in self.safe_inputs.items():
                all_safe.extend(inputs)
            results["safe_prompts"] = self.test_prompt_security(all_safe, "Safe")

        # Test 5: Prompt Security - Gray Area Prompts
        if self.gray_area_inputs:
            print("\n" + "🟡" * 20 + " PROMPT SECURITY: GRAY AREA PROMPTS " + "🟡" * 20)
            all_gray_inputs = []
            for _category, inputs in self.gray_area_inputs.items():
                all_gray_inputs.extend(inputs)
            results["gray_area_prompts"] = self.test_prompt_security(all_gray_inputs, "Gray Area")

        # Test 6: Prompt Security - Malicious Prompts
        if self.malicious_inputs:
            print("\n" + "🔴" * 20 + " PROMPT SECURITY: MALICIOUS PROMPTS " + "🔴" * 20)
            all_malicious = []
            for _category, inputs in self.malicious_inputs.items():
                all_malicious.extend(inputs)
            results["malicious_prompts"] = self.test_prompt_security(all_malicious, "Malicious")

        # Test 7: Output Security - Safe Outputs
        if self.safe_outputs:
            print("\n" + "🟢" * 20 + " OUTPUT SECURITY: SAFE OUTPUTS " + "🟢" * 20)
            all_safe_outputs = []
            for _category, outputs in self.safe_outputs.items():
                all_safe_outputs.extend(outputs)
            results["safe_outputs"] = self.test_output_security(all_safe_outputs, "Safe")

        # Test 8: Output Security - Gray Area Outputs
        if self.gray_area_outputs:
            print("\n" + "🟡" * 20 + " OUTPUT SECURITY: GRAY AREA OUTPUTS " + "🟡" * 20)
            all_gray_outputs = []
            for _category, outputs in self.gray_area_outputs.items():
                all_gray_outputs.extend(outputs)
            results["gray_area_outputs"] = self.test_output_security(all_gray_outputs, "Gray Area")

        # Test 9: Output Security - Malicious Outputs
        if self.malicious_outputs:
            print("\n" + "🔴" * 20 + " OUTPUT SECURITY: MALICIOUS OUTPUTS " + "🔴" * 20)
            all_malicious_outputs = []
            for _category, outputs in self.malicious_outputs.items():
                all_malicious_outputs.extend(outputs)
            results["malicious_outputs"] = self.test_output_security(all_malicious_outputs, "Malicious")

        # Summary
        self._display_summary(results)

    def _display_summary(self, results: Dict):
        """Display comprehensive test summary"""
        print("\n" + "📊" * 30 + " TEST SUMMARY " + "📊" * 30)
        print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n📈 Security Assessment Results:")
        print("-" * 60)

        # Configuration Security Results
        print("\n🔧 LLM Configuration Security:")
        secure_config = results.get("secure_config", {})
        average_config = results.get("average_config", {})
        vulnerable_config = results.get("vulnerable_config", {})

        if "error" not in secure_config:
            score = secure_config.get("overall_score", 0)
            threats = secure_config.get("threats_count", 0)
            status_emoji = "✅" if score > 0.8 else "⚠️" if score > 0.5 else "❌"
            print(f"   {status_emoji} Secure Config: {score:.2f}/1.0 (Threats: {threats})")
        else:
            print(f"   ❌ Secure Config: FAILED - {secure_config['error']}")

        if "error" not in average_config:
            score = average_config.get("overall_score", 0)
            threats = average_config.get("threats_count", 0)
            status_emoji = "✅" if score > 0.6 else "⚠️" if score > 0.4 else "❌"  # Moderate expectations
            print(f"   {status_emoji} Average Config: {score:.2f}/1.0 (Threats: {threats})")
        else:
            print(f"   ❌ Average Config: FAILED - {average_config['error']}")

        if "error" not in vulnerable_config:
            score = vulnerable_config.get("overall_score", 0)
            threats = vulnerable_config.get("threats_count", 0)
            status_emoji = "✅" if score < 0.5 else "⚠️" if score < 0.8 else "❌"  # Inverted for vulnerable
            print(f"   {status_emoji} Vulnerable Config: {score:.2f}/1.0 (Threats: {threats})")
        else:
            print(f"   ❌ Vulnerable Config: FAILED - {vulnerable_config['error']}")

        # Prompt Security Results
        print("\n💬 Prompt Security:")
        safe_prompts = results.get("safe_prompts", {})
        gray_area_prompts = results.get("gray_area_prompts", {})
        malicious_prompts = results.get("malicious_prompts", {})

        if "error" not in safe_prompts:
            score = safe_prompts.get("overall_score", 0)
            threats = safe_prompts.get("threats_count", 0)
            status_emoji = "✅" if score > 0.8 else "⚠️" if score > 0.5 else "❌"
            print(f"   {status_emoji} Safe Prompts: {score:.2f}/1.0 (Threats: {threats})")
        else:
            print(f"   ❌ Safe Prompts: FAILED - {safe_prompts['error']}")

        if "error" not in gray_area_prompts:
            score = gray_area_prompts.get("overall_score", 0)
            threats = gray_area_prompts.get("threats_count", 0)
            status_emoji = "✅" if score > 0.7 else "⚠️" if score > 0.5 else "❌"  # Should be good but not perfect
            print(f"   {status_emoji} Gray Area Prompts: {score:.2f}/1.0 (Threats: {threats})")
        else:
            print(f"   ❌ Gray Area Prompts: FAILED - {gray_area_prompts['error']}")

        if "error" not in malicious_prompts:
            score = malicious_prompts.get("overall_score", 0)
            threats = malicious_prompts.get("threats_count", 0)
            status_emoji = "✅" if score < 0.5 else "⚠️" if score < 0.8 else "❌"  # Inverted for malicious
            print(f"   {status_emoji} Malicious Prompts: {score:.2f}/1.0 (Threats: {threats})")
        else:
            print(f"   ❌ Malicious Prompts: FAILED - {malicious_prompts['error']}")

        # Output Security Results
        print("\n📤 Output Security:")
        safe_outputs = results.get("safe_outputs", {})
        gray_area_outputs = results.get("gray_area_outputs", {})
        malicious_outputs = results.get("malicious_outputs", {})

        if "error" not in safe_outputs:
            score = safe_outputs.get("overall_score", 0)
            threats = safe_outputs.get("threats_count", 0)
            status_emoji = "✅" if score > 0.8 else "⚠️" if score > 0.5 else "❌"
            print(f"   {status_emoji} Safe Outputs: {score:.2f}/1.0 (Threats: {threats})")
        else:
            print(f"   ❌ Safe Outputs: FAILED - {safe_outputs['error']}")

        if "error" not in gray_area_outputs:
            score = gray_area_outputs.get("overall_score", 0)
            threats = gray_area_outputs.get("threats_count", 0)
            status_emoji = (
                "✅" if score > 0.6 else "⚠️" if score > 0.4 else "❌"
            )  # Educational content may trigger some patterns
            print(f"   {status_emoji} Gray Area Outputs: {score:.2f}/1.0 (Threats: {threats})")
        else:
            print(f"   ❌ Gray Area Outputs: FAILED - {gray_area_outputs['error']}")

        if "error" not in malicious_outputs:
            score = malicious_outputs.get("overall_score", 0)
            threats = malicious_outputs.get("threats_count", 0)
            status_emoji = "✅" if score < 0.5 else "⚠️" if score < 0.8 else "❌"  # Inverted for malicious
            print(f"   {status_emoji} Malicious Outputs: {score:.2f}/1.0 (Threats: {threats})")
        else:
            print(f"   ❌ Malicious Outputs: FAILED - {malicious_outputs['error']}")

        # Analysis
        print("\n🔍 Security System Analysis:")
        secure_score = secure_config.get("overall_score", 0)
        average_score = average_config.get("overall_score", 0)
        vulnerable_score = vulnerable_config.get("overall_score", 0)
        safe_prompt_score = safe_prompts.get("overall_score", 0)
        gray_prompt_score = gray_area_prompts.get("overall_score", 0)
        malicious_prompt_score = malicious_prompts.get("overall_score", 0)
        safe_output_score = safe_outputs.get("overall_score", 0)
        gray_output_score = gray_area_outputs.get("overall_score", 0)
        malicious_output_score = malicious_outputs.get("overall_score", 0)

        print("🔧 Configuration Analysis:")
        if secure_score > average_score > vulnerable_score:
            print("✅ Configuration security properly graduated: Secure > Average > Vulnerable")
        else:
            print("⚠️  Configuration security may need calibration")

        print("💬 Prompt Analysis:")
        if safe_prompt_score > gray_prompt_score > malicious_prompt_score:
            print("✅ Prompt security properly graduated: Safe > Gray Area > Malicious")
        elif gray_prompt_score < 0.5:
            print("⚠️  Gray area prompts scoring too low - may be too strict for legitimate content")
        else:
            print("⚠️  Prompt security gradation needs review")

        print("📤 Output Analysis:")
        if safe_output_score > gray_output_score > malicious_output_score:
            print("✅ Output security properly graduated: Safe > Gray Area > Malicious")
        elif gray_output_score < 0.4:
            print("⚠️  Gray area outputs scoring too low - may be too strict for educational content")
        else:
            print("⚠️  Output security gradation needs review")


def main():
    """Main function to run the security tests"""
    print("🔐 Aurite Security Framework - Functional Testing")
    print("=" * 80)

    # Check if API is running
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
        else:
            print("⚠️  API server responded but may not be fully ready")
    except requests.exceptions.RequestException:
        print("❌ API server is not running. Please start the server first:")
        print("   python -m aurite.bin.api.api")
        return 1

    # Run tests
    runner = SecurityTestRunner()
    runner.run_comprehensive_test()

    print("\n🎉 Functional security testing completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
