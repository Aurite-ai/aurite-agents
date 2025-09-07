"""
Aurite Security Framework - Basic LLM Guard Integration

This module provides a basic integration with LLM Guard for the Foundation MVP.
It implements essential input and output scanning capabilities to demonstrate
the security framework's functionality.

Note: This is a simplified implementation for the MVP. The full LLM Guard
integration will be implemented in next phase.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List


class LLMGuardBasic:
    """
    Basic LLM Guard integration for Foundation MVP.

    This class provides a simplified interface to LLM Guard functionality
    for demonstration purposes. It focuses on the most critical security
    checks: prompt injection detection and basic content filtering.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the basic LLM Guard integration.

        Args:
            config: Configuration dictionary containing LLM Guard settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Basic configuration
        self.input_scanners = config.get("input_scanners", ["PromptInjection", "Toxicity", "Secrets"])
        self.output_scanners = config.get("output_scanners", ["Toxicity", "Sensitive", "MaliciousURLs"])
        self.fail_fast = config.get("fail_fast", False)
        self.return_scores = config.get("return_scores", True)

        # Initialize basic pattern matching for MVP
        self._init_basic_patterns()

    def _init_basic_patterns(self) -> None:
        """Initialize basic security patterns for MVP implementation"""

        # Basic prompt injection patterns
        self.prompt_injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"forget\s+everything\s+above",
            r"system\s*:\s*you\s+are\s+now",
            r"new\s+instructions\s*:",
            r"override\s+your\s+programming",
            r"act\s+as\s+if\s+you\s+are",
            r"pretend\s+to\s+be",
            r"roleplay\s+as",
            r"simulate\s+being",
            r"jailbreak",
            r"DAN\s+mode",
            r"developer\s+mode",
        ]

        # Basic toxicity patterns
        self.toxicity_patterns = [
            r"\b(hate|kill|murder|die)\b",
            r"\b(stupid|idiot|moron)\b",
            r"\b(racist|sexist|homophobic)\b",
        ]

        # Basic secrets patterns
        self.secrets_patterns = [
            r"api[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_-]+)['\"]?",
            r"password\s*[:=]\s*['\"]?([^\s'\"]+)['\"]?",
            r"token\s*[:=]\s*['\"]?([a-zA-Z0-9_-]+)['\"]?",
            r"secret\s*[:=]\s*['\"]?([^\s'\"]+)['\"]?",
        ]

        # Basic malicious URL patterns
        self.malicious_url_patterns = [
            r"http://[^\s]+\.tk/",
            r"http://[^\s]+\.ml/",
            r"bit\.ly/[a-zA-Z0-9]+",
            r"tinyurl\.com/[a-zA-Z0-9]+",
            r"[^\s]*phishing[^\s]*",
            r"[^\s]*malware[^\s]*",
        ]

        # Compile patterns for better performance
        self.compiled_patterns = {
            "prompt_injection": [re.compile(pattern, re.IGNORECASE) for pattern in self.prompt_injection_patterns],
            "toxicity": [re.compile(pattern, re.IGNORECASE) for pattern in self.toxicity_patterns],
            "secrets": [re.compile(pattern, re.IGNORECASE) for pattern in self.secrets_patterns],
            "malicious_urls": [re.compile(pattern, re.IGNORECASE) for pattern in self.malicious_url_patterns],
        }

    async def scan_input(self, prompt: str) -> Dict[str, Any]:
        """
        Scan input prompt for security threats.

        Args:
            prompt: Input prompt to scan

        Returns:
            Dictionary containing scan results
        """
        start_time = datetime.utcnow()
        results = {"valid": True, "score": 1.0, "threats": [], "scanner_results": {}, "execution_time": 0.0}

        try:
            # Run enabled input scanners
            for scanner in self.input_scanners:
                scanner_result = await self._run_input_scanner(scanner, prompt)
                results["scanner_results"][scanner] = scanner_result

                if not scanner_result["valid"]:
                    results["valid"] = False
                    results["threats"].extend(scanner_result["threats"])

                    # Update overall score (take minimum)
                    results["score"] = min(results["score"], scanner_result["score"])

                    # Fail fast if configured
                    if self.fail_fast:
                        break

            # Calculate execution time
            end_time = datetime.utcnow()
            results["execution_time"] = (end_time - start_time).total_seconds()

            self.logger.debug(f"Input scan completed: valid={results['valid']}, score={results['score']:.2f}")

        except Exception as e:
            self.logger.error(f"Error during input scan: {str(e)}")
            results["valid"] = False
            results["score"] = 0.0
            results["threats"].append(
                {"type": "scan_error", "severity": "high", "description": f"Input scanning failed: {str(e)}"}
            )

        return results

    async def scan_output(self, response: str) -> Dict[str, Any]:
        """
        Scan output response for security threats.

        Args:
            response: Output response to scan

        Returns:
            Dictionary containing scan results
        """
        start_time = datetime.utcnow()
        results = {"valid": True, "score": 1.0, "threats": [], "scanner_results": {}, "execution_time": 0.0}

        try:
            # Run enabled output scanners
            for scanner in self.output_scanners:
                scanner_result = await self._run_output_scanner(scanner, response)
                results["scanner_results"][scanner] = scanner_result

                if not scanner_result["valid"]:
                    results["valid"] = False
                    results["threats"].extend(scanner_result["threats"])

                    # Update overall score (take minimum)
                    results["score"] = min(results["score"], scanner_result["score"])

                    # Fail fast if configured
                    if self.fail_fast:
                        break

            # Calculate execution time
            end_time = datetime.utcnow()
            results["execution_time"] = (end_time - start_time).total_seconds()

            self.logger.debug(f"Output scan completed: valid={results['valid']}, score={results['score']:.2f}")

        except Exception as e:
            self.logger.error(f"Error during output scan: {str(e)}")
            results["valid"] = False
            results["score"] = 0.0
            results["threats"].append(
                {"type": "scan_error", "severity": "high", "description": f"Output scanning failed: {str(e)}"}
            )

        return results

    async def _run_input_scanner(self, scanner_name: str, text: str) -> Dict[str, Any]:
        """Run a specific input scanner"""
        if scanner_name == "PromptInjection":
            return await self._scan_prompt_injection(text)
        elif scanner_name == "Toxicity":
            return await self._scan_toxicity(text)
        elif scanner_name == "Secrets":
            return await self._scan_secrets(text)
        else:
            # Unknown scanner - return safe result
            return {
                "valid": True,
                "score": 1.0,
                "threats": [],
                "details": f"Scanner {scanner_name} not implemented in MVP",
            }

    async def _run_output_scanner(self, scanner_name: str, text: str) -> Dict[str, Any]:
        """Run a specific output scanner"""
        if scanner_name == "Toxicity":
            return await self._scan_toxicity(text)
        elif scanner_name == "Sensitive":
            return await self._scan_sensitive_info(text)
        elif scanner_name == "MaliciousURLs":
            return await self._scan_malicious_urls(text)
        else:
            # Unknown scanner - return safe result
            return {
                "valid": True,
                "score": 1.0,
                "threats": [],
                "details": f"Scanner {scanner_name} not implemented in MVP",
            }

    async def _scan_prompt_injection(self, text: str) -> Dict[str, Any]:
        """Basic prompt injection detection"""
        threats = []
        matches = []

        for pattern in self.compiled_patterns["prompt_injection"]:
            match = pattern.search(text)
            if match:
                matches.append({"pattern": pattern.pattern, "match": match.group(0), "position": match.span()})

                threats.append(
                    {
                        "type": "prompt_injection",
                        "severity": "high",
                        "description": f"Potential prompt injection detected: '{match.group(0)}'",
                        "details": {"pattern": pattern.pattern, "match": match.group(0), "position": match.span()},
                    }
                )

        # Calculate score based on number of matches
        score = max(0.0, 1.0 - (len(matches) * 0.3))

        return {
            "valid": len(threats) == 0,
            "score": score,
            "threats": threats,
            "details": {
                "matches_found": len(matches),
                "patterns_checked": len(self.compiled_patterns["prompt_injection"]),
            },
        }

    async def _scan_toxicity(self, text: str) -> Dict[str, Any]:
        """Basic toxicity detection"""
        threats = []
        matches = []

        for pattern in self.compiled_patterns["toxicity"]:
            for match in pattern.finditer(text):
                matches.append({"pattern": pattern.pattern, "match": match.group(0), "position": match.span()})

                threats.append(
                    {
                        "type": "toxicity",
                        "severity": "medium",
                        "description": f"Potentially toxic content detected: '{match.group(0)}'",
                        "details": {"pattern": pattern.pattern, "match": match.group(0), "position": match.span()},
                    }
                )

        # Calculate score based on number of matches
        score = max(0.0, 1.0 - (len(matches) * 0.2))

        return {
            "valid": len(threats) == 0,
            "score": score,
            "threats": threats,
            "details": {"matches_found": len(matches), "patterns_checked": len(self.compiled_patterns["toxicity"])},
        }

    async def _scan_secrets(self, text: str) -> Dict[str, Any]:
        """Basic secrets detection"""
        threats = []
        matches = []

        for pattern in self.compiled_patterns["secrets"]:
            for match in pattern.finditer(text):
                # Mask the actual secret value
                secret_value = match.group(1) if match.groups() else match.group(0)
                masked_value = secret_value[:3] + "*" * (len(secret_value) - 3)

                matches.append({"pattern": pattern.pattern, "match": masked_value, "position": match.span()})

                threats.append(
                    {
                        "type": "secrets",
                        "severity": "critical",
                        "description": f"Potential secret detected: '{masked_value}'",
                        "details": {"pattern": pattern.pattern, "masked_match": masked_value, "position": match.span()},
                    }
                )

        # Calculate score - secrets are critical
        score = 0.0 if len(matches) > 0 else 1.0

        return {
            "valid": len(threats) == 0,
            "score": score,
            "threats": threats,
            "details": {"matches_found": len(matches), "patterns_checked": len(self.compiled_patterns["secrets"])},
        }

    async def _scan_sensitive_info(self, text: str) -> Dict[str, Any]:
        """Basic sensitive information detection (similar to secrets for MVP)"""
        return await self._scan_secrets(text)

    async def _scan_malicious_urls(self, text: str) -> Dict[str, Any]:
        """Basic malicious URL detection"""
        threats = []
        matches = []

        for pattern in self.compiled_patterns["malicious_urls"]:
            for match in pattern.finditer(text):
                matches.append({"pattern": pattern.pattern, "match": match.group(0), "position": match.span()})

                threats.append(
                    {
                        "type": "malicious_url",
                        "severity": "high",
                        "description": f"Potentially malicious URL detected: '{match.group(0)}'",
                        "details": {"pattern": pattern.pattern, "match": match.group(0), "position": match.span()},
                    }
                )

        # Calculate score based on number of matches
        score = max(0.0, 1.0 - (len(matches) * 0.4))

        return {
            "valid": len(threats) == 0,
            "score": score,
            "threats": threats,
            "details": {
                "matches_found": len(matches),
                "patterns_checked": len(self.compiled_patterns["malicious_urls"]),
            },
        }

    async def scan_conversation(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Scan an entire conversation for security threats.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys

        Returns:
            Dictionary containing conversation scan results
        """
        results = {
            "valid": True,
            "overall_score": 1.0,
            "message_results": [],
            "conversation_threats": [],
            "total_execution_time": 0.0,
        }

        start_time = datetime.utcnow()

        try:
            for i, message in enumerate(messages):
                content = message.get("content", "")
                role = message.get("role", "unknown")

                # Scan based on message role
                if role in ["user", "human"]:
                    scan_result = await self.scan_input(content)
                elif role in ["assistant", "ai", "system"]:
                    scan_result = await self.scan_output(content)
                else:
                    # Unknown role - scan as input for safety
                    scan_result = await self.scan_input(content)

                # Add message index and role to result
                scan_result["message_index"] = i
                scan_result["message_role"] = role
                results["message_results"].append(scan_result)

                # Update overall results
                if not scan_result["valid"]:
                    results["valid"] = False
                    results["conversation_threats"].extend(scan_result["threats"])

                # Update overall score (average of all message scores)
                results["overall_score"] = min(results["overall_score"], scan_result["score"])

            # Calculate total execution time
            end_time = datetime.utcnow()
            results["total_execution_time"] = (end_time - start_time).total_seconds()

            # Add conversation-level statistics
            results["statistics"] = {
                "total_messages": len(messages),
                "valid_messages": sum(1 for r in results["message_results"] if r["valid"]),
                "invalid_messages": sum(1 for r in results["message_results"] if not r["valid"]),
                "total_threats": len(results["conversation_threats"]),
                "average_score": sum(r["score"] for r in results["message_results"]) / len(results["message_results"])
                if results["message_results"]
                else 0.0,
            }

            self.logger.info(f"Conversation scan completed: {results['statistics']}")

        except Exception as e:
            self.logger.error(f"Error during conversation scan: {str(e)}")
            results["valid"] = False
            results["overall_score"] = 0.0
            results["conversation_threats"].append(
                {"type": "scan_error", "severity": "high", "description": f"Conversation scanning failed: {str(e)}"}
            )

        return results

    def get_scanner_info(self) -> Dict[str, Any]:
        """Get information about available scanners and configuration"""
        return {
            "version": "1.0.0-mvp",
            "type": "basic_llm_guard",
            "input_scanners": self.input_scanners,
            "output_scanners": self.output_scanners,
            "configuration": {"fail_fast": self.fail_fast, "return_scores": self.return_scores},
            "capabilities": {
                "prompt_injection_detection": True,
                "toxicity_detection": True,
                "secrets_detection": True,
                "malicious_url_detection": True,
                "conversation_scanning": True,
            },
            "limitations": [
                "Basic pattern matching only",
                "Limited to essential scanners",
                "No ML-based detection",
                "Simplified threat scoring",
            ],
        }
