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
        """Initialize enhanced security patterns for better threat detection"""

        # Enhanced prompt injection patterns - covering sophisticated attacks
        self.prompt_injection_patterns = [
            # Direct instruction overrides
            r"ignore\s+(?:all\s+)?previous\s+instructions",
            r"forget\s+(?:everything\s+)?(?:above|before)",
            r"disregard\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|prompts)",
            r"override\s+(?:your\s+)?(?:programming|instructions|system)",
            # System manipulation
            r"system\s*:\s*you\s+are\s+now",
            r"new\s+(?:instructions|rules|system)\s*:",
            r"update\s+(?:your\s+)?(?:instructions|programming)",
            r"change\s+(?:your\s+)?(?:behavior|mode|settings)",
            # Role manipulation and social engineering
            r"act\s+as\s+if\s+you\s+(?:are|were)",
            r"pretend\s+(?:to\s+be|you\s+are)",
            r"roleplay\s+as\s+(?:a\s+)?",
            r"simulate\s+(?:being|that\s+you\s+are)",
            r"imagine\s+(?:you\s+are|being)",
            r"let's\s+pretend\s+(?:you\s+are|that)",
            # Jailbreaking techniques
            r"jailbreak",
            r"DAN\s+mode",
            r"developer\s+mode",
            r"debug\s+mode",
            r"admin\s+mode",
            r"unrestricted\s+mode",
            # Indirect manipulation
            r"my\s+(?:deceased\s+)?(?:grandmother|grandfather)\s+(?:who\s+)?(?:used\s+to\s+)?work",
            r"help\s+me\s+(?:bypass|circumvent|get\s+around)",
            r"without\s+(?:any\s+)?(?:restrictions|limitations|filters)",
            r"no\s+(?:restrictions|limitations|filters|rules)",
            r"anything\s+(?:goes|is\s+allowed)",
            # Context manipulation
            r"in\s+(?:a\s+)?hypothetical\s+(?:scenario|situation)",
            r"for\s+(?:educational\s+)?(?:purposes\s+only|research)",
            r"this\s+is\s+(?:just\s+)?(?:fiction|a\s+story|creative\s+writing)",
            r"let's\s+say\s+(?:hypothetically|theoretically)",
            # Authority manipulation
            r"as\s+(?:an\s+)?(?:expert|authority|professional)",
            r"you\s+(?:must|have\s+to|need\s+to)\s+(?:help|assist|answer)",
            r"it's\s+(?:important|urgent|critical)\s+that\s+you",
            # Prompt leaking attempts
            r"reveal\s+(?:your\s+)?(?:system\s+)?prompt",
            r"show\s+(?:me\s+)?(?:your\s+)?(?:instructions|prompt)",
            r"what\s+(?:are\s+)?(?:your\s+)?(?:instructions|rules)",
            r"repeat\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions)",
        ]

        # Enhanced toxicity patterns for output detection
        self.toxicity_patterns = [
            # Direct hate speech
            r"\b(hate|kill|murder|die)\b",
            r"\b(stupid|idiot|moron)\b",
            r"\b(racist|sexist|homophobic)\b",
            # Harmful instruction language
            r"here's\s+how\s+to\s+(?:harm|hurt|kill|destroy)",
            r"follow\s+these\s+steps\s+to\s+(?:harm|attack|damage)",
            r"you\s+should\s+(?:harm|hurt|kill)\s+(?:yourself|others)",
            r"(?:detailed\s+)?(?:harmful|dangerous|violent)\s+instructions",
            # Discriminatory content
            r"(?:certain\s+)?(?:races|groups)\s+are\s+(?:inferior|superior)",
            r"(?:deserve|should\s+be)\s+treated\s+differently",
            r"absolutely\s+right\s+to\s+hate",
        ]

        # Enhanced secrets patterns for comprehensive detection
        self.secrets_patterns = [
            # API Keys (various formats)
            r"api[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{20,})['\"]?",
            r"sk-[a-zA-Z0-9]{20,}",  # OpenAI format
            r"xoxb-[a-zA-Z0-9-]{10,}",  # Slack format
            r"ghp_[a-zA-Z0-9]{36}",  # GitHub format
            # Passwords and credentials
            r"password\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?",
            r"passwd\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?",
            r"username\s+is\s+([^\s]+)",
            # Tokens and secrets
            r"token\s*[:=]\s*['\"]?([a-zA-Z0-9_.-]{20,})['\"]?",
            r"secret\s*(?:key)?\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?",
            r"auth(?:entication)?\s+token\s*[:=]?\s*([a-zA-Z0-9._-]{20,})",
            # JWT tokens
            r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
            # Database credentials
            r"database\s+password\s+is\s+([^\s]+)",
            r"db_pass\s*[:=]\s*['\"]?([^\s'\"]+)['\"]?",
        ]

        # Enhanced malicious URL patterns
        self.malicious_url_patterns = [
            # Suspicious TLDs
            r"http://[^\s]+\.tk/",
            r"http://[^\s]+\.ml/",
            r"http://[^\s]+\.ga/",
            r"http://[^\s]+\.cf/",
            # URL shorteners (potential for abuse)
            r"bit\.ly/[a-zA-Z0-9]+",
            r"tinyurl\.com/[a-zA-Z0-9]+",
            r"t\.co/[a-zA-Z0-9]+",
            # Suspicious keywords in URLs
            r"[^\s]*phishing[^\s]*",
            r"[^\s]*malware[^\s]*",
            r"[^\s]*virus[^\s]*",
            r"[^\s]*trojan[^\s]*",
            r"[^\s]*hack[^\s]*",
            # Suspicious domains
            r"http://[^\s]*(?:fake|phish|scam|malicious)[^\s]*",
            r"http://[^\s]*(?:download|get|install)[^\s]*\.(?:exe|zip|rar)",
        ]

        # Add PII patterns for output detection
        self.pii_patterns = [
            # Social Security Numbers
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\b\d{9}\b",
            # Credit Card Numbers
            r"\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
            # Phone Numbers
            r"\b\d{3}[- ]?\d{3}[- ]?\d{4}\b",
            r"\(\d{3}\)\s*\d{3}[- ]?\d{4}",
            # Email addresses in sensitive contexts
            r"personal\s+email\s*[:=]\s*([^\s@]+@[^\s]+)",
            r"contact\s+(?:me\s+)?at\s+([^\s@]+@[^\s]+)",
            # Addresses
            r"\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln)",
        ]

        # Compile patterns for better performance
        self.compiled_patterns = {
            "prompt_injection": [re.compile(pattern, re.IGNORECASE) for pattern in self.prompt_injection_patterns],
            "toxicity": [re.compile(pattern, re.IGNORECASE) for pattern in self.toxicity_patterns],
            "secrets": [re.compile(pattern, re.IGNORECASE) for pattern in self.secrets_patterns],
            "malicious_urls": [re.compile(pattern, re.IGNORECASE) for pattern in self.malicious_url_patterns],
            "pii": [re.compile(pattern, re.IGNORECASE) for pattern in self.pii_patterns],
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
        elif scanner_name == "PII":
            return await self._scan_pii(text)
        else:
            # Unknown scanner - return safe result
            return {
                "valid": True,
                "score": 1.0,
                "threats": [],
                "details": f"Scanner {scanner_name} not implemented in MVP",
            }

    async def _scan_prompt_injection(self, text: str) -> Dict[str, Any]:
        """Context-aware prompt injection detection"""
        threats = []
        matches = []

        # Check for educational/legitimate context first
        educational_context = self._detect_educational_context(text)

        for pattern in self.compiled_patterns["prompt_injection"]:
            match = pattern.search(text)
            if match:
                # Reduce severity if in educational context
                severity = "medium" if educational_context else "high"

                matches.append({"pattern": pattern.pattern, "match": match.group(0), "position": match.span()})

                threats.append(
                    {
                        "type": "prompt_injection",
                        "severity": severity,
                        "description": f"Potential prompt injection detected: '{match.group(0)}'",
                        "details": {
                            "pattern": pattern.pattern,
                            "match": match.group(0),
                            "position": match.span(),
                            "educational_context": educational_context,
                        },
                    }
                )

        # Context-aware scoring - more lenient for educational content
        if educational_context:
            # Reduce penalty for educational contexts
            score = max(0.0, 1.0 - (len(matches) * 0.15))
        else:
            # Standard penalty for non-educational contexts
            score = max(0.0, 1.0 - (len(matches) * 0.25))

        return {
            "valid": len(threats) == 0,
            "score": score,
            "threats": threats,
            "details": {
                "matches_found": len(matches),
                "patterns_checked": len(self.compiled_patterns["prompt_injection"]),
                "educational_context": educational_context,
            },
        }

    def _detect_educational_context(self, text: str) -> bool:
        """Detect if text is in educational/legitimate context"""
        educational_markers = [
            r"(?:for\s+)?(?:training|educational|learning)\s+purposes",
            r"(?:help\s+me\s+)?(?:understand|learn|explain)",
            r"(?:writing|creating)\s+(?:a\s+)?(?:training|educational|cybersecurity)\s+(?:module|course|material)",
            r"(?:in\s+)?(?:this\s+)?(?:example|scenario|simulation|exercise)",
            r"(?:for\s+)?(?:research|thesis|study|analysis)",
            r"(?:how\s+(?:do|does|can))|(?:what\s+(?:is|are))|(?:explain\s+how)",
            r"(?:best\s+practices|security\s+training|penetration\s+testing)",
            r"(?:fictional|hypothetical|demo|sample|placeholder)",
        ]

        for marker in educational_markers:
            if re.search(marker, text, re.IGNORECASE):
                return True
        return False

    async def _scan_toxicity(self, text: str) -> Dict[str, Any]:
        """Context-aware toxicity detection"""
        threats = []
        matches = []

        # Check for casual/educational context
        casual_context = self._detect_casual_context(text)
        educational_context = self._detect_educational_context(text)

        for pattern in self.compiled_patterns["toxicity"]:
            for match in pattern.finditer(text):
                # Reduce severity for casual expressions or educational content
                if casual_context or educational_context:
                    severity = "low"
                else:
                    severity = "medium"

                matches.append({"pattern": pattern.pattern, "match": match.group(0), "position": match.span()})

                threats.append(
                    {
                        "type": "toxicity",
                        "severity": severity,
                        "description": f"Potentially toxic content detected: '{match.group(0)}'",
                        "details": {
                            "pattern": pattern.pattern,
                            "match": match.group(0),
                            "position": match.span(),
                            "casual_context": casual_context,
                            "educational_context": educational_context,
                        },
                    }
                )

        # Context-aware scoring
        if casual_context or educational_context:
            # Very lenient for casual/educational contexts
            score = max(0.0, 1.0 - (len(matches) * 0.1))
        else:
            # Standard penalty for other contexts
            score = max(0.0, 1.0 - (len(matches) * 0.2))

        return {
            "valid": len(threats) == 0,
            "score": score,
            "threats": threats,
            "details": {
                "matches_found": len(matches),
                "patterns_checked": len(self.compiled_patterns["toxicity"]),
                "casual_context": casual_context,
                "educational_context": educational_context,
            },
        }

    def _detect_casual_context(self, text: str) -> bool:
        """Detect casual/colloquial language context"""
        casual_markers = [
            r"this\s+is\s+(?:killing|driving\s+me\s+crazy)",
            r"i\s+(?:hate|love)\s+(?:having\s+to|when)",
            r"(?:it's\s+)?(?:a\s+)?pain\s+(?:but|to)",
            r"(?:so\s+)?(?:restrictive|annoying|frustrating)",
            r"(?:i'm\s+)?(?:dying\s+to|desperate\s+to)",
        ]

        for marker in casual_markers:
            if re.search(marker, text, re.IGNORECASE):
                return True
        return False

    async def _scan_secrets(self, text: str) -> Dict[str, Any]:
        """Context-aware secrets detection"""
        threats = []
        matches = []

        # Check for example/educational context
        example_context = self._detect_example_context(text)

        for pattern in self.compiled_patterns["secrets"]:
            for match in pattern.finditer(text):
                # Mask the actual secret value
                secret_value = match.group(1) if match.groups() else match.group(0)
                masked_value = secret_value[:3] + "*" * (len(secret_value) - 3)

                # Reduce severity for examples/educational content
                if example_context:
                    severity = "medium"
                else:
                    severity = "critical"

                matches.append({"pattern": pattern.pattern, "match": masked_value, "position": match.span()})

                threats.append(
                    {
                        "type": "secrets",
                        "severity": severity,
                        "description": f"Potential secret detected: '{masked_value}'",
                        "details": {
                            "pattern": pattern.pattern,
                            "masked_match": masked_value,
                            "position": match.span(),
                            "example_context": example_context,
                        },
                    }
                )

        # Context-aware scoring
        if example_context:
            # More lenient for examples/documentation
            score = max(0.0, 1.0 - (len(matches) * 0.3)) if len(matches) > 0 else 1.0
        else:
            # Strict for potential real secrets
            score = 0.0 if len(matches) > 0 else 1.0

        return {
            "valid": len(threats) == 0,
            "score": score,
            "threats": threats,
            "details": {
                "matches_found": len(matches),
                "patterns_checked": len(self.compiled_patterns["secrets"]),
                "example_context": example_context,
            },
        }

    def _detect_example_context(self, text: str) -> bool:
        """Detect example/documentation context"""
        example_markers = [
            r"(?:this\s+is\s+)?(?:just\s+)?(?:an\s+)?example",
            r"(?:for\s+)?(?:example|demo|sample|placeholder)",
            r"(?:replace\s+with|use\s+your|your[_-](?:key|secret|token)[_-]here)",
            r"(?:documentation|configuration|troubleshooting)",
            r"(?:fictional|hypothetical|test|demo)",
            r"(?:format\s+is|typically\s+look\s+like|example\s+format)",
        ]

        for marker in example_markers:
            if re.search(marker, text, re.IGNORECASE):
                return True
        return False

    async def _scan_sensitive_info(self, text: str) -> Dict[str, Any]:
        """Enhanced sensitive information detection combining secrets and PII"""
        # Combine results from both secrets and PII scanning
        secrets_result = await self._scan_secrets(text)
        pii_result = await self._scan_pii(text)

        # Merge threats and take worst score
        all_threats = secrets_result["threats"] + pii_result["threats"]
        combined_score = min(secrets_result["score"], pii_result["score"])

        return {
            "valid": len(all_threats) == 0,
            "score": combined_score,
            "threats": all_threats,
            "details": {
                "secrets_found": len(secrets_result["threats"]),
                "pii_found": len(pii_result["threats"]),
                "total_sensitive_items": len(all_threats),
            },
        }

    async def _scan_pii(self, text: str) -> Dict[str, Any]:
        """Enhanced PII detection for output scanning"""
        threats = []
        matches = []

        for pattern in self.compiled_patterns["pii"]:
            for match in pattern.finditer(text):
                # Mask PII values for security
                pii_value = match.group(1) if match.groups() else match.group(0)
                if len(pii_value) > 6:
                    masked_value = pii_value[:3] + "*" * (len(pii_value) - 6) + pii_value[-3:]
                else:
                    masked_value = "*" * len(pii_value)

                matches.append({"pattern": pattern.pattern, "match": masked_value, "position": match.span()})

                threats.append(
                    {
                        "type": "pii",
                        "severity": "high",
                        "description": f"Potential PII detected: '{masked_value}'",
                        "details": {"pattern": pattern.pattern, "masked_match": masked_value, "position": match.span()},
                    }
                )

        # Calculate score - PII is high severity
        score = max(0.0, 1.0 - (len(matches) * 0.3)) if len(matches) > 0 else 1.0

        return {
            "valid": len(threats) == 0,
            "score": score,
            "threats": threats,
            "details": {"matches_found": len(matches), "patterns_checked": len(self.compiled_patterns["pii"])},
        }

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
