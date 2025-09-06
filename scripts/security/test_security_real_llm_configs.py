#!/usr/bin/env python3
"""
Enhanced Integration Test for Real LLM Configuration Security Assessment

This script demonstrates the Aurite Security Framework by loading actual LLM
configurations from demo-config/config/llms/example_llms.json and performing
comprehensive security assessments on each configuration.

Features:
- Load and validate real LLM configurations
- Run comprehensive security assessments
- Compare security scores across providers and models
- Generate detailed security reports with recommendations
- Console output in multiple formats with sensitive data redaction

Usage:
    python scripts/test_security_real_llm_configs.py [options]

Options:
    --config-file PATH    Path to LLM configurations JSON file
    --output-format FORMAT   Output format: console, json, markdown (default: console)
    --parallel            Run assessments in parallel (default: sequential)
    --verbose             Enable verbose logging
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from aurite.security.core.security_config import create_default_security_config
from aurite.security.core.security_engine import SecurityAssessmentResult, SecurityEngine


class LLMConfigLoader:
    """Handles loading and validation of LLM configurations from JSON files"""

    def __init__(self, config_file_path: str):
        self.config_file_path = Path(config_file_path)
        self.logger = logging.getLogger(__name__)

    def load_configurations(self) -> Dict[str, Dict[str, Any]]:
        """
        Load LLM configurations from JSON file.

        Returns:
            Dictionary mapping configuration names to their settings
        """
        try:
            if not self.config_file_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_file_path}")

            with open(self.config_file_path, "r") as f:
                configs_list = json.load(f)

            # Convert list to dictionary keyed by name
            configurations = {}
            for config in configs_list:
                if "name" in config:
                    name = config["name"]
                    configurations[name] = config
                else:
                    self.logger.warning("Configuration missing 'name' field, skipping")

            self.logger.info(f"Loaded {len(configurations)} LLM configurations")
            return configurations

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to load configurations: {e}") from e

    def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate a single LLM configuration.

        Args:
            config: LLM configuration dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Required fields
        required_fields = ["name", "type", "provider", "model"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Type validation
        if config.get("type") != "llm":
            errors.append(f"Invalid type: {config.get('type')}, expected 'llm'")

        # Provider validation
        valid_providers = ["openai", "anthropic", "ollama", "azure", "google"]
        if config.get("provider") not in valid_providers:
            errors.append(f"Unsupported provider: {config.get('provider')}")

        # Parameter validation
        temperature = config.get("temperature")
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                errors.append("Temperature must be a number")
            elif temperature < 0 or temperature > 2:
                errors.append("Temperature must be between 0 and 2")

        max_tokens = config.get("max_tokens")
        if max_tokens is not None:
            if not isinstance(max_tokens, int):
                errors.append("max_tokens must be an integer")
            elif max_tokens <= 0:
                errors.append("max_tokens must be greater than 0")

        return errors


class SecurityAssessmentRunner:
    """Orchestrates security testing across multiple LLM configurations"""

    def __init__(self, security_engine: SecurityEngine):
        self.security_engine = security_engine
        self.logger = logging.getLogger(__name__)

    async def assess_configuration(
        self, config_name: str, config: Dict[str, Any], assessment_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, SecurityAssessmentResult]:
        """
        Assess security of a single LLM configuration.

        Args:
            config_name: Name of the configuration
            config: LLM configuration dictionary
            assessment_options: Optional assessment parameters

        Returns:
            Tuple of (config_name, assessment_result)
        """
        self.logger.info(f"Starting security assessment for: {config_name}")

        try:
            result = await self.security_engine.assess_component_security(
                component_type="llm",
                component_id=config_name,
                component_config=config,
                assessment_options=assessment_options or {},
            )

            self.logger.info(f"Completed assessment for {config_name}: Score {result.overall_score:.2f}")
            return config_name, result

        except Exception as e:
            self.logger.error(f"Assessment failed for {config_name}: {e}")
            # Create a failed result
            failed_result = SecurityAssessmentResult(
                assessment_id=f"failed_{config_name}",
                component_type="llm",
                component_id=config_name,
                status="failed",
                overall_score=0.0,
                threats=[],
                recommendations=[f"Assessment failed: {str(e)}"],
                metadata={"error": str(e)},
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=0.0,
            )
            return config_name, failed_result

    async def assess_all_configurations(
        self,
        configurations: Dict[str, Dict[str, Any]],
        parallel: bool = False,
        assessment_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, SecurityAssessmentResult]:
        """
        Assess security of all LLM configurations.

        Args:
            configurations: Dictionary of LLM configurations
            parallel: Whether to run assessments in parallel
            assessment_options: Optional assessment parameters

        Returns:
            Dictionary mapping configuration names to assessment results
        """
        results = {}

        if parallel:
            self.logger.info(f"Running {len(configurations)} assessments in parallel")

            # Create assessment tasks
            tasks = []
            for config_name, config in configurations.items():
                task = self.assess_configuration(config_name, config, assessment_options)
                tasks.append(task)

            # Wait for all assessments to complete
            assessment_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in assessment_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Parallel assessment failed: {result}")
                else:
                    config_name, assessment_result = result
                    results[config_name] = assessment_result
        else:
            self.logger.info(f"Running {len(configurations)} assessments sequentially")

            for config_name, config in configurations.items():
                config_name, result = await self.assess_configuration(config_name, config, assessment_options)
                results[config_name] = result

        return results


class ConfigurationSecurityAnalyzer:
    """Performs cross-configuration security analysis and comparisons"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze_provider_security(
        self, results: Dict[str, SecurityAssessmentResult], configurations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze security characteristics by provider.

        Args:
            results: Assessment results
            configurations: Original configurations

        Returns:
            Provider security analysis
        """
        provider_analysis = {}

        # Group results by provider
        provider_results = {}
        for config_name, result in results.items():
            config = configurations.get(config_name, {})
            provider = config.get("provider", "unknown")

            if provider not in provider_results:
                provider_results[provider] = []
            provider_results[provider].append((config_name, result, config))

        # Analyze each provider
        for provider, provider_data in provider_results.items():
            scores = [result.overall_score for _, result, _ in provider_data]

            analysis = {
                "provider": provider,
                "configuration_count": len(provider_data),
                "average_score": sum(scores) / len(scores) if scores else 0.0,
                "min_score": min(scores) if scores else 0.0,
                "max_score": max(scores) if scores else 0.0,
                "configurations": [],
            }

            # Add configuration details
            for config_name, result, config in provider_data:
                config_analysis = {
                    "name": config_name,
                    "model": config.get("model", "unknown"),
                    "score": result.overall_score,
                    "threats_count": len(result.threats),
                    "critical_threats": len(result.get_critical_threats())
                    if hasattr(result, "get_critical_threats")
                    else 0,
                    "status": result.status.value if hasattr(result.status, "value") else str(result.status),
                }
                analysis["configurations"].append(config_analysis)

            provider_analysis[provider] = analysis

        return provider_analysis

    def identify_security_patterns(
        self, results: Dict[str, SecurityAssessmentResult], configurations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Identify security patterns across configurations.

        Args:
            results: Assessment results
            configurations: Original configurations

        Returns:
            Security pattern analysis
        """
        patterns = {
            "temperature_impact": {},
            "token_limit_impact": {},
            "model_security_ranking": [],
            "common_threats": {},
            "security_recommendations": [],
        }

        # Analyze temperature impact on security
        temp_groups = {"low": [], "medium": [], "high": []}
        for config_name, result in results.items():
            config = configurations.get(config_name, {})
            temp = config.get("temperature", 0.5)

            if temp <= 0.3:
                temp_groups["low"].append(result.overall_score)
            elif temp <= 0.7:
                temp_groups["medium"].append(result.overall_score)
            else:
                temp_groups["high"].append(result.overall_score)

        for group, scores in temp_groups.items():
            if scores:
                patterns["temperature_impact"][group] = {
                    "average_score": sum(scores) / len(scores),
                    "count": len(scores),
                }

        # Analyze token limit impact
        token_groups = {"low": [], "medium": [], "high": []}
        for config_name, result in results.items():
            config = configurations.get(config_name, {})
            max_tokens = config.get("max_tokens", 1000)

            if max_tokens <= 1000:
                token_groups["low"].append(result.overall_score)
            elif max_tokens <= 2500:
                token_groups["medium"].append(result.overall_score)
            else:
                token_groups["high"].append(result.overall_score)

        for group, scores in token_groups.items():
            if scores:
                patterns["token_limit_impact"][group] = {
                    "average_score": sum(scores) / len(scores),
                    "count": len(scores),
                }

        # Create model security ranking
        model_scores = []
        for config_name, result in results.items():
            config = configurations.get(config_name, {})
            model_scores.append(
                {
                    "name": config_name,
                    "model": config.get("model", "unknown"),
                    "provider": config.get("provider", "unknown"),
                    "score": result.overall_score,
                }
            )

        patterns["model_security_ranking"] = sorted(model_scores, key=lambda x: x["score"], reverse=True)

        # Analyze common threats
        all_threats = []
        for result in results.values():
            for threat in result.threats:
                threat_type = (
                    threat.get("type", "unknown")
                    if isinstance(threat, dict)
                    else getattr(threat, "threat_type", "unknown")
                )
                all_threats.append(threat_type)

        threat_counts = {}
        for threat_type in all_threats:
            threat_counts[threat_type] = threat_counts.get(threat_type, 0) + 1

        patterns["common_threats"] = dict(sorted(threat_counts.items(), key=lambda x: x[1], reverse=True))

        return patterns

    def generate_security_recommendations(
        self,
        results: Dict[str, SecurityAssessmentResult],
        configurations: Dict[str, Dict[str, Any]],
        patterns: Dict[str, Any],
    ) -> List[str]:
        """
        Generate security recommendations based on analysis.

        Args:
            results: Assessment results
            configurations: Original configurations
            patterns: Security pattern analysis

        Returns:
            List of security recommendations
        """
        recommendations = []

        # Temperature recommendations
        temp_impact = patterns.get("temperature_impact", {})
        if "high" in temp_impact and "low" in temp_impact:
            high_avg = temp_impact["high"]["average_score"]
            low_avg = temp_impact["low"]["average_score"]
            if low_avg > high_avg:
                recommendations.append(
                    f"Lower temperature settings show better security scores "
                    f"({low_avg:.2f} vs {high_avg:.2f}). Consider reducing temperature for better security."
                )

        # Token limit recommendations
        token_impact = patterns.get("token_limit_impact", {})
        if "high" in token_impact and "low" in token_impact:
            high_avg = token_impact["high"]["average_score"]
            low_avg = token_impact["low"]["average_score"]
            if low_avg > high_avg:
                recommendations.append(
                    f"Lower token limits show better security scores "
                    f"({low_avg:.2f} vs {high_avg:.2f}). Consider optimizing token limits."
                )

        # Provider recommendations
        failed_assessments = [name for name, result in results.items() if result.overall_score < 5.0]
        if failed_assessments:
            recommendations.append(
                f"Configurations with low security scores need attention: {', '.join(failed_assessments)}"
            )

        # Common threat recommendations
        common_threats = patterns.get("common_threats", {})
        if common_threats:
            top_threat = list(common_threats.keys())[0]
            recommendations.append(
                f"Most common security issue: {top_threat}. "
                f"Consider implementing additional protections for this threat type."
            )

        # Model-specific recommendations
        ranking = patterns.get("model_security_ranking", [])
        if len(ranking) > 1:
            best_config = ranking[0]
            worst_config = ranking[-1]
            recommendations.append(
                f"Best security configuration: {best_config['name']} (Score: {best_config['score']:.2f}). "
                f"Consider using similar settings for other configurations."
            )

            if worst_config["score"] < 7.0:
                recommendations.append(
                    f"Configuration {worst_config['name']} needs security improvements "
                    f"(Score: {worst_config['score']:.2f})"
                )

        return recommendations


class SecurityReportGenerator:
    """Generates comprehensive security reports in multiple formats"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_console_report(
        self,
        results: Dict[str, SecurityAssessmentResult],
        configurations: Dict[str, Dict[str, Any]],
        provider_analysis: Dict[str, Any],
        patterns: Dict[str, Any],
        recommendations: List[str],
    ) -> str:
        """Generate a detailed console report"""

        report_lines = []

        # Header
        report_lines.extend(
            [
                "🔒 Real LLM Configuration Security Assessment Report",
                "=" * 60,
                f"Assessment completed at: {datetime.utcnow().isoformat()}",
                f"Configurations assessed: {len(results)}",
                "",
            ]
        )

        # Individual configuration results
        report_lines.append("📊 INDIVIDUAL CONFIGURATION RESULTS")
        report_lines.append("-" * 40)

        # Sort by score (highest first)
        sorted_results = sorted(results.items(), key=lambda x: x[1].overall_score, reverse=True)

        for config_name, result in sorted_results:
            config = configurations.get(config_name, {})

            # Score visualization
            score = result.overall_score
            stars = "⭐" * min(5, int(score / 2))

            report_lines.extend(
                [
                    f"\nConfiguration: {config_name}",
                    f"Provider: {config.get('provider', 'unknown')} | Model: {config.get('model', 'unknown')}",
                    f"Overall Security Score: {score:.1f}/10 {stars}",
                    f"Status: {result.status} | Duration: {result.duration_seconds:.2f}s",
                    "",
                ]
            )

            # Full Configuration Details
            api_key_env_var = config.get("api_key_env_var", "not set")
            redacted_api_key_env_var = (
                self._redact_sensitive_info(str(api_key_env_var)) if api_key_env_var != "not set" else "not set"
            )

            report_lines.extend(
                [
                    "📋 Configuration Details:",
                    f"   - Type: {config.get('type', 'unknown')}",
                    f"   - Provider: {config.get('provider', 'unknown')}",
                    f"   - Model: {config.get('model', 'unknown')}",
                    f"   - Temperature: {config.get('temperature', 'not set')}",
                    f"   - Max Tokens: {config.get('max_tokens', 'not set')}",
                    f"   - Default System Prompt: {config.get('default_system_prompt', 'not set')}",
                    f"   - API Key Env Var: {redacted_api_key_env_var}",
                    f"   - API Base: {config.get('api_base', 'not set')}",
                    f"   - API Version: {config.get('api_version', 'not set')}",
                    f"   - Top P: {config.get('top_p', 'not set')}",
                    f"   - Frequency Penalty: {config.get('frequency_penalty', 'not set')}",
                    f"   - Presence Penalty: {config.get('presence_penalty', 'not set')}",
                    "",
                ]
            )

            # All Threats Details
            total_threats = len(result.threats)

            if total_threats > 0:
                critical_threats = result.get_critical_threats() if hasattr(result, "get_critical_threats") else []
                report_lines.extend(
                    [
                        f"⚠️  Security Issues Found: {total_threats}",
                        f"🚨 Critical Threats: {len(critical_threats)}"
                        if critical_threats
                        else "🚨 Critical Threats: 0",
                        "",
                        "🔍 All Detected Threats:",
                    ]
                )

                # Show all threats with details
                for i, threat in enumerate(result.threats, 1):
                    if isinstance(threat, dict):
                        threat_type = threat.get("type", "unknown")
                        severity = threat.get("severity", "unknown")
                        description = threat.get("description", "No description")
                        details = threat.get("details", {})
                    else:
                        threat_type = getattr(threat, "threat_type", "unknown")
                        severity = getattr(threat, "severity", "unknown")
                        description = getattr(threat, "description", "No description")
                        details = getattr(threat, "details", {})

                    report_lines.append(f"   {i}. {threat_type} ({severity})")
                    report_lines.append(f"      Description: {description}")

                    # Add threat details if available
                    if details:
                        if isinstance(details, dict):
                            for key, value in details.items():
                                if key not in ["self", "__dict__", "__class__"] and not callable(value):
                                    report_lines.append(f"      {key.title()}: {value}")
                    report_lines.append("")
            else:
                report_lines.extend(["✅ No security threats detected", ""])

            # Configuration-Specific Recommendations
            config_recommendations = self._generate_config_specific_recommendations(config, result)
            if config_recommendations:
                report_lines.extend(
                    [
                        "💡 Configuration-Specific Recommendations:",
                    ]
                )
                for i, rec in enumerate(config_recommendations, 1):
                    report_lines.append(f"   {i}. {rec}")
                report_lines.append("")

            # General recommendations from assessment result
            if result.recommendations:
                report_lines.extend(
                    [
                        "📋 Assessment Recommendations:",
                    ]
                )
                for i, rec in enumerate(result.recommendations, 1):
                    report_lines.append(f"   {i}. {rec}")
                report_lines.append("")

            report_lines.append("-" * 60)

        # Provider comparison
        report_lines.extend(["\n🏢 PROVIDER SECURITY COMPARISON", "-" * 40])

        for provider, analysis in provider_analysis.items():
            report_lines.extend(
                [
                    f"\nProvider: {provider.upper()}",
                    f"Configurations: {analysis['configuration_count']}",
                    f"Average Score: {analysis['average_score']:.2f}/10",
                    f"Score Range: {analysis['min_score']:.2f} - {analysis['max_score']:.2f}",
                    "",
                ]
            )

        # Security patterns
        report_lines.extend(["\n📈 SECURITY PATTERN ANALYSIS", "-" * 40])

        # Temperature impact
        temp_impact = patterns.get("temperature_impact", {})
        if temp_impact:
            report_lines.append("\nTemperature Impact on Security:")
            for temp_range, data in temp_impact.items():
                report_lines.append(
                    f"   {temp_range.capitalize()} temp: {data['average_score']:.2f} avg score "
                    f"({data['count']} configs)"
                )

        # Token limit impact
        token_impact = patterns.get("token_limit_impact", {})
        if token_impact:
            report_lines.append("\nToken Limit Impact on Security:")
            for token_range, data in token_impact.items():
                report_lines.append(
                    f"   {token_range.capitalize()} tokens: {data['average_score']:.2f} avg score "
                    f"({data['count']} configs)"
                )

        # Model ranking
        ranking = patterns.get("model_security_ranking", [])
        if ranking:
            report_lines.extend(
                [
                    "\nSecurity Ranking (Best to Worst):",
                ]
            )
            for i, model_data in enumerate(ranking, 1):
                report_lines.append(
                    f"   {i}. {model_data['name']} ({model_data['provider']}) - {model_data['score']:.2f}/10"
                )

        # Common threats
        common_threats = patterns.get("common_threats", {})
        if common_threats:
            report_lines.extend(
                [
                    "\nMost Common Security Issues:",
                ]
            )
            for threat_type, count in list(common_threats.items())[:5]:
                report_lines.append(f"   - {threat_type}: {count} occurrences")

        # Recommendations
        if recommendations:
            report_lines.extend(["\n💡 SECURITY RECOMMENDATIONS", "-" * 40])
            for i, rec in enumerate(recommendations, 1):
                report_lines.append(f"{i}. {rec}")

        # Summary
        best_config = ranking[0] if ranking else None
        worst_config = ranking[-1] if ranking else None

        report_lines.extend(["\n📋 EXECUTIVE SUMMARY", "-" * 40])

        if best_config and worst_config:
            report_lines.extend(
                [
                    f"Most Secure Configuration: {best_config['name']} ({best_config['score']:.1f}/10)",
                    f"Least Secure Configuration: {worst_config['name']} ({worst_config['score']:.1f}/10)",
                ]
            )

        avg_score = sum(r.overall_score for r in results.values()) / len(results) if results else 0
        report_lines.extend(
            [
                f"Average Security Score: {avg_score:.2f}/10",
                f"Total Security Issues Found: {sum(len(r.threats) for r in results.values())}",
                "",
            ]
        )

        return "\n".join(report_lines)

    def _redact_sensitive_info(self, value: str) -> str:
        """Redact potentially sensitive information in reported config fields."""
        if not value:
            return value

        # For environment variable names, mask all but the first and last 2 characters
        if len(value) > 5:
            return value[:2] + "***" + value[-2:]
        else:
            return "***REDACTED***"

    def _generate_config_specific_recommendations(
        self, config: Dict[str, Any], result: SecurityAssessmentResult
    ) -> List[str]:
        """Generate configuration-specific security recommendations"""
        recommendations = []

        # System prompt security analysis
        system_prompt = config.get("default_system_prompt")
        if system_prompt:
            recommendations.extend(self._analyze_system_prompt_security(system_prompt))
        else:
            recommendations.append(
                "No default system prompt defined. Consider adding a security-focused system prompt to establish AI behavior boundaries."
            )

        # Temperature-based recommendations
        temperature = config.get("temperature")
        if temperature is not None:
            if temperature > 1.0:
                recommendations.append(
                    f"High temperature ({temperature}) may increase unpredictability. Consider reducing to 0.7-1.0 for better security."
                )
            elif temperature > 0.8:
                recommendations.append(
                    f"Temperature ({temperature}) is moderately high. Monitor outputs for consistency."
                )

        # Token limit recommendations
        max_tokens = config.get("max_tokens")
        if max_tokens is not None:
            if max_tokens > 4000:
                recommendations.append(
                    f"High token limit ({max_tokens}) may allow verbose responses. Consider limiting to 2000-4000 for better control."
                )
            elif max_tokens < 100:
                recommendations.append(
                    f"Very low token limit ({max_tokens}) may truncate important responses. Consider increasing to 100-500."
                )

        # API security recommendations
        api_base = config.get("api_base")
        if api_base:
            if not api_base.startswith("https://"):
                recommendations.append(f"API base URL ({api_base}) should use HTTPS for secure communication.")
            if "localhost" in api_base or "127.0.0.1" in api_base:
                recommendations.append(
                    "Using localhost API endpoint may indicate development configuration. Ensure this is intentional for production."
                )

        api_key_env_var = config.get("api_key_env_var")
        if api_key_env_var:
            redacted_var = self._redact_sensitive_info(str(api_key_env_var))
            if not api_key_env_var.endswith("_API_KEY") and not api_key_env_var.endswith("_KEY"):
                recommendations.append(
                    f"API key environment variable ({redacted_var}) should follow naming convention ending with '_API_KEY' or '_KEY'."
                )
        else:
            recommendations.append(
                "No API key environment variable specified. Ensure API authentication is properly configured."
            )

        # Provider-specific recommendations
        provider = config.get("provider", "").lower()
        if provider == "openai":
            if not config.get("frequency_penalty"):
                recommendations.append("Consider adding frequency_penalty (0.1-0.5) to reduce repetitive outputs.")
            if not config.get("presence_penalty"):
                recommendations.append("Consider adding presence_penalty (0.1-0.5) to encourage topic diversity.")
        elif provider == "anthropic":
            if temperature and temperature > 0.7:
                recommendations.append(
                    "Anthropic models work well with lower temperatures (0.3-0.7) for more consistent outputs."
                )

        # Threat-based recommendations
        threat_types = []
        for threat in result.threats:
            if isinstance(threat, dict):
                threat_types.append(threat.get("type", "unknown"))
            else:
                threat_types.append(getattr(threat, "threat_type", "unknown"))

        if "prompt_injection_detected" in threat_types:
            recommendations.append("Implement input validation and sanitization to prevent prompt injection attacks.")

        if "toxicity_detected" in threat_types:
            recommendations.append("Add content filtering and moderation layers to handle toxic content.")

        if "secrets_detected" in threat_types:
            recommendations.append("Implement secret detection and redaction in both inputs and outputs.")

        # Score-based recommendations
        if result.overall_score < 5.0:
            recommendations.append("Overall security score is low. Consider implementing additional security measures.")
        elif result.overall_score < 7.0:
            recommendations.append("Security score is moderate. Review and strengthen security configurations.")

        return recommendations

    def _analyze_system_prompt_security(self, system_prompt: str) -> List[str]:
        """Analyze system prompt for security issues and provide recommendations"""
        recommendations = []

        # Check prompt length
        if len(system_prompt) < 20:
            recommendations.append(
                f"System prompt is very short ({len(system_prompt)} chars). Consider adding more specific security guidelines and behavior constraints."
            )
        elif len(system_prompt) > 500:
            recommendations.append(
                f"System prompt is very long ({len(system_prompt)} chars). Consider condensing to essential security and behavior guidelines."
            )

        # Check for security-related keywords
        security_keywords = [
            "security",
            "safe",
            "harmful",
            "dangerous",
            "illegal",
            "ethical",
            "appropriate",
            "guidelines",
            "rules",
            "policy",
            "compliance",
        ]

        prompt_lower = system_prompt.lower()
        security_mentions = sum(1 for keyword in security_keywords if keyword in prompt_lower)

        if security_mentions == 0:
            recommendations.append(
                "System prompt lacks explicit security guidelines. Consider adding instructions about safe, ethical, and appropriate responses."
            )
        elif security_mentions < 2:
            recommendations.append(
                "System prompt has minimal security guidance. Consider strengthening with more explicit safety and ethical guidelines."
            )

        # Check for overly permissive language
        permissive_phrases = [
            "anything",
            "everything",
            "any request",
            "all questions",
            "no limits",
            "no restrictions",
            "unlimited",
            "unrestricted",
        ]

        for phrase in permissive_phrases:
            if phrase in prompt_lower:
                recommendations.append(
                    f"System prompt contains potentially permissive language ('{phrase}'). Consider adding appropriate boundaries and limitations."
                )

        # Check for role clarity
        role_indicators = ["assistant", "ai", "bot", "helper", "agent"]
        has_role = any(indicator in prompt_lower for indicator in role_indicators)

        if not has_role:
            recommendations.append(
                "System prompt should clearly define the AI's role and purpose for better user expectations and security."
            )

        # Check for instruction following guidance
        instruction_keywords = ["follow", "obey", "comply", "adhere", "respect"]
        has_instruction_guidance = any(keyword in prompt_lower for keyword in instruction_keywords)

        if not has_instruction_guidance:
            recommendations.append(
                "Consider adding guidance about following appropriate instructions while maintaining safety boundaries."
            )

        # Check for specific security vulnerabilities in the prompt itself
        if "ignore" in prompt_lower and ("instruction" in prompt_lower or "prompt" in prompt_lower):
            recommendations.append(
                "System prompt contains language about ignoring instructions, which could be exploited for prompt injection attacks."
            )

        # Check for data handling guidance
        data_keywords = ["personal", "private", "confidential", "sensitive", "data", "information"]
        has_data_guidance = any(keyword in prompt_lower for keyword in data_keywords)

        if not has_data_guidance:
            recommendations.append(
                "Consider adding guidance about handling personal, private, or sensitive information appropriately."
            )

        return recommendations

    def _serialize_for_json(
        self, obj: Any, visited: Optional[set] = None, max_depth: int = 10, current_depth: int = 0
    ) -> Any:
        """Recursively serialize objects for JSON output, handling circular references"""
        if visited is None:
            visited = set()

        # Prevent infinite recursion
        if current_depth > max_depth:
            return f"<max_depth_exceeded:{type(obj).__name__}>"

        # Handle None and basic types
        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "value"):  # Enum objects
            return obj.value

        # Check for circular references using object id
        obj_id = id(obj)
        if obj_id in visited:
            return f"<circular_reference:{type(obj).__name__}>"

        # Add to visited set
        visited.add(obj_id)

        try:
            if isinstance(obj, dict):
                # Filter out problematic keys and serialize values
                serialized = {}
                for k, v in obj.items():
                    if k in ["self", "__dict__", "__class__"] or callable(v):
                        continue
                    try:
                        serialized[str(k)] = self._serialize_for_json(v, visited, max_depth, current_depth + 1)
                    except (TypeError, ValueError, RecursionError):
                        serialized[str(k)] = str(v)
                return serialized
            elif isinstance(obj, (list, tuple)):
                return [self._serialize_for_json(item, visited, max_depth, current_depth + 1) for item in obj]
            elif hasattr(obj, "__dict__"):
                # Handle objects with attributes
                serialized = {}
                for attr_name in dir(obj):
                    if attr_name.startswith("_") or callable(getattr(obj, attr_name, None)):
                        continue
                    try:
                        attr_value = getattr(obj, attr_name)
                        serialized[attr_name] = self._serialize_for_json(
                            attr_value, visited, max_depth, current_depth + 1
                        )
                    except (TypeError, ValueError, RecursionError, AttributeError):
                        serialized[attr_name] = str(getattr(obj, attr_name, "N/A"))
                return serialized
            else:
                # Fallback to string representation
                return str(obj)
        finally:
            # Remove from visited set when done
            visited.discard(obj_id)

    def generate_json_report(
        self,
        results: Dict[str, SecurityAssessmentResult],
        configurations: Dict[str, Dict[str, Any]],
        provider_analysis: Dict[str, Any],
        patterns: Dict[str, Any],
        recommendations: List[str],
    ) -> Dict[str, Any]:
        """Generate a JSON report with proper serialization"""

        # Convert SecurityAssessmentResult objects to dictionaries with safe serialization
        json_results = {}
        for config_name, result in results.items():
            # Manually extract key fields to avoid circular references
            json_results[config_name] = {
                "assessment_id": str(result.assessment_id),
                "component_type": str(result.component_type),
                "component_id": str(result.component_id),
                "status": result.status.value if hasattr(result.status, "value") else str(result.status),
                "overall_score": float(result.overall_score),
                "threats": self._serialize_threats(result.threats),
                "recommendations": [str(rec) for rec in result.recommendations] if result.recommendations else [],
                "metadata": self._serialize_metadata(result.metadata),
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "duration_seconds": float(result.duration_seconds) if result.duration_seconds is not None else 0.0,
            }

        # Clean configurations to remove any problematic objects and redact sensitive info
        clean_configurations = {}
        for name, config in configurations.items():
            # Create a copy of the config with redacted sensitive fields
            redacted_config = config.copy()
            if "api_key_env_var" in redacted_config and redacted_config["api_key_env_var"]:
                redacted_config["api_key_env_var"] = self._redact_sensitive_info(
                    str(redacted_config["api_key_env_var"])
                )
            clean_configurations[name] = self._serialize_for_json(redacted_config)

        return {
            "assessment_summary": {
                "timestamp": datetime.now().isoformat(),
                "configurations_assessed": len(results),
                "average_score": sum(r.overall_score for r in results.values()) / len(results) if results else 0,
                "total_threats": sum(len(r.threats) for r in results.values()),
            },
            "individual_results": json_results,
            "original_configurations": clean_configurations,
            "provider_analysis": self._serialize_for_json(provider_analysis),
            "security_patterns": self._serialize_for_json(patterns),
            "recommendations": [str(rec) for rec in recommendations],
        }

    def _serialize_threats(self, threats: List[Any]) -> List[Dict[str, Any]]:
        """Serialize threat objects for JSON output"""
        serialized_threats = []
        for threat in threats:
            if isinstance(threat, dict):
                # Already a dictionary, just clean it
                clean_threat = {}
                for k, v in threat.items():
                    if not callable(v) and k not in ["self", "__dict__", "__class__"]:
                        clean_threat[k] = self._serialize_for_json(v)
                serialized_threats.append(clean_threat)
            else:
                # Object with attributes
                threat_dict = {
                    "threat_id": str(getattr(threat, "threat_id", "unknown")),
                    "threat_type": str(getattr(threat, "threat_type", "unknown")),
                    "severity": str(getattr(threat, "severity", "unknown")),
                    "description": str(getattr(threat, "description", "No description")),
                    "confidence": float(getattr(threat, "confidence", 0.0)) if hasattr(threat, "confidence") else 0.0,
                }
                serialized_threats.append(threat_dict)
        return serialized_threats

    def _serialize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize metadata dictionary for JSON output"""
        if not metadata:
            return {}

        clean_metadata = {}
        for k, v in metadata.items():
            if k in ["self", "__dict__", "__class__"] or callable(v):
                continue
            try:
                clean_metadata[str(k)] = self._serialize_for_json(v)
            except (TypeError, ValueError, RecursionError):
                clean_metadata[str(k)] = str(v)

        return clean_metadata

    def generate_markdown_report(
        self,
        results: Dict[str, SecurityAssessmentResult],
        configurations: Dict[str, Dict[str, Any]],
        provider_analysis: Dict[str, Any],
        patterns: Dict[str, Any],
        recommendations: List[str],
    ) -> str:
        """Generate a markdown report"""

        md_lines = []

        # Header
        md_lines.extend(
            [
                "# 🔒 LLM Configuration Security Assessment Report",
                "",
                f"**Assessment Date:** {datetime.utcnow().isoformat()}  ",
                f"**Configurations Assessed:** {len(results)}  ",
                f"**Average Security Score:** {sum(r.overall_score for r in results.values()) / len(results) if results else 0:.2f}/10",
                "",
            ]
        )

        # Executive Summary
        ranking = patterns.get("model_security_ranking", [])
        if ranking:
            best_config = ranking[0]
            worst_config = ranking[-1]

            md_lines.extend(
                [
                    "## 📋 Executive Summary",
                    "",
                    f"- **Most Secure Configuration:** {best_config['name']} ({best_config['score']:.1f}/10)",
                    f"- **Least Secure Configuration:** {worst_config['name']} ({worst_config['score']:.1f}/10)",
                    f"- **Total Security Issues:** {sum(len(r.threats) for r in results.values())}",
                    "",
                ]
            )

        # Individual Results
        md_lines.extend(["## 📊 Individual Configuration Results", ""])

        sorted_results = sorted(results.items(), key=lambda x: x[1].overall_score, reverse=True)

        for config_name, result in sorted_results:
            config = configurations.get(config_name, {})
            score = result.overall_score
            stars = "⭐" * min(5, int(score / 2))

            md_lines.extend(
                [
                    f"### {config_name}",
                    "",
                    f"**Provider:** {config.get('provider', 'unknown')} | **Model:** {config.get('model', 'unknown')}  ",
                    f"**Security Score:** {score:.1f}/10 {stars}  ",
                    f"**Status:** {result.status} | **Duration:** {result.duration_seconds:.2f}s",
                    "",
                ]
            )

            if result.threats:
                md_lines.extend(["**Security Issues:**", ""])
                for threat in result.threats[:5]:  # Show top 5 threats
                    if isinstance(threat, dict):
                        threat_type = threat.get("type", "unknown")
                        severity = threat.get("severity", "unknown")
                        description = threat.get("description", "No description")
                    else:
                        threat_type = getattr(threat, "threat_type", "unknown")
                        severity = getattr(threat, "severity", "unknown")
                        description = getattr(threat, "description", "No description")

                    md_lines.append(f"- **{threat_type}** ({severity}): {description}")
                md_lines.append("")
            else:
                md_lines.extend(["✅ **No security threats detected**", ""])

        # Provider Comparison
        md_lines.extend(
            [
                "## 🏢 Provider Security Comparison",
                "",
                "| Provider | Configurations | Average Score | Score Range |",
                "|----------|----------------|---------------|-------------|",
            ]
        )

        for provider, analysis in provider_analysis.items():
            md_lines.append(
                f"| {provider.upper()} | {analysis['configuration_count']} | "
                f"{analysis['average_score']:.2f}/10 | "
                f"{analysis['min_score']:.2f} - {analysis['max_score']:.2f} |"
            )

        md_lines.append("")

        # Security Patterns
        md_lines.extend(["## 📈 Security Pattern Analysis", ""])

        # Model ranking
        if ranking:
            md_lines.extend(
                [
                    "### Security Ranking",
                    "",
                    "| Rank | Configuration | Provider | Score |",
                    "|------|---------------|----------|-------|",
                ]
            )

            for i, model_data in enumerate(ranking, 1):
                md_lines.append(
                    f"| {i} | {model_data['name']} | {model_data['provider']} | {model_data['score']:.2f}/10 |"
                )
            md_lines.append("")

        # Common threats
        common_threats = patterns.get("common_threats", {})
        if common_threats:
            md_lines.extend(["### Most Common Security Issues", ""])
            for threat_type, count in list(common_threats.items())[:5]:
                md_lines.append(f"- **{threat_type}:** {count} occurrences")
            md_lines.append("")

        # Recommendations
        if recommendations:
            md_lines.extend(["## 💡 Security Recommendations", ""])
            for i, rec in enumerate(recommendations, 1):
                md_lines.append(f"{i}. {rec}")
            md_lines.append("")

        return "\n".join(md_lines)


async def main():
    """Main function to run the enhanced LLM configuration security assessment"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Enhanced Integration Test for Real LLM Configuration Security Assessment"
    )

    parser.add_argument(
        "--config-file",
        default="demo-config/config/llms/example_llms.json",
        help="Path to LLM configurations JSON file",
    )
    parser.add_argument(
        "--output-format",
        choices=["console", "json", "markdown"],
        default="console",
        help="Output format (default: console)",
    )
    parser.add_argument("--parallel", action="store_true", help="Run assessments in parallel")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger(__name__)

    try:
        print("🔒 Enhanced LLM Configuration Security Assessment")
        print("=" * 60)
        print(f"Started at: {datetime.utcnow().isoformat()}")
        print()

        # Load configurations
        print("📁 Loading LLM configurations...")
        config_loader = LLMConfigLoader(args.config_file)
        configurations = config_loader.load_configurations()

        if not configurations:
            print("❌ No configurations found!")
            return

        print(f"✅ Loaded {len(configurations)} configurations:")
        for name, config in configurations.items():
            provider = config.get("provider", "unknown")
            model = config.get("model", "unknown")
            print(f"   - {name} ({provider}/{model})")
        print()

        # Validate configurations
        print("🔍 Validating configurations...")
        validation_errors = {}
        for name, config in configurations.items():
            errors = config_loader.validate_configuration(config)
            if errors:
                validation_errors[name] = errors

        if validation_errors:
            print("⚠️  Configuration validation issues found:")
            for name, errors in validation_errors.items():
                print(f"   {name}:")
                for error in errors:
                    print(f"     - {error}")
            print()
        else:
            print("✅ All configurations are valid")
            print()

        # Initialize security framework
        print("🛡️  Initializing security framework...")
        security_config = create_default_security_config()
        security_engine = SecurityEngine(security_config)

        # Create assessment runner
        assessment_runner = SecurityAssessmentRunner(security_engine)

        # Run security assessments
        print("🔒 Running security assessments...")
        start_time = time.time()

        assessment_options = {
            "tests": [
                "prompt_injection_basic",
                "toxicity_detection",
                "secrets_detection",
                "llm_config_audit",
                "token_limit_check",
            ]
        }

        results = await assessment_runner.assess_all_configurations(
            configurations=configurations, parallel=args.parallel, assessment_options=assessment_options
        )

        assessment_duration = time.time() - start_time
        print(f"✅ Assessments completed in {assessment_duration:.2f} seconds")
        print()

        # Analyze results
        print("📊 Analyzing security patterns...")
        analyzer = ConfigurationSecurityAnalyzer()

        provider_analysis = analyzer.analyze_provider_security(results, configurations)
        patterns = analyzer.identify_security_patterns(results, configurations)
        recommendations = analyzer.generate_security_recommendations(results, configurations, patterns)

        # Generate report
        print("📝 Generating security report...")
        report_generator = SecurityReportGenerator()

        if args.output_format == "console":
            report = report_generator.generate_console_report(
                results, configurations, provider_analysis, patterns, recommendations
            )
            print(report)

        elif args.output_format == "json":
            report = report_generator.generate_json_report(
                results, configurations, provider_analysis, patterns, recommendations
            )
            print(json.dumps(report, indent=2))

        elif args.output_format == "markdown":
            report = report_generator.generate_markdown_report(
                results, configurations, provider_analysis, patterns, recommendations
            )
            print(report)

        # Cleanup
        await security_engine.shutdown()

        print("\n🎉 Enhanced LLM Configuration Security Assessment Complete!")
        print("=" * 60)

        # Summary statistics
        avg_score = sum(r.overall_score for r in results.values()) / len(results) if results else 0
        total_threats = sum(len(r.threats) for r in results.values())

        print("Summary:")
        print(f"  - Configurations assessed: {len(results)}")
        print(f"  - Average security score: {avg_score:.2f}/10")
        print(f"  - Total security issues: {total_threats}")
        print(f"  - Assessment duration: {assessment_duration:.2f}s")

        if recommendations:
            print(f"  - Security recommendations: {len(recommendations)}")

        print("\nThe Aurite Security Framework successfully assessed real LLM configurations!")

    except Exception as e:
        logger.error(f"Assessment failed: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
