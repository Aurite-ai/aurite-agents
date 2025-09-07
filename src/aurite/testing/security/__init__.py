"""
Aurite Security Framework

A comprehensive security framework for AI agent systems, providing:
- Component-based security testing (LLM, MCP, Agent, Workflow)
- Integration with open-source security tools
- Real-time monitoring and threat detection

Key Components:
- SecurityEngine: Main orchestration engine
- Component Testers: Specialized security testing for each component type
- Security Configuration: Centralized configuration management
- API Layer: REST API for external integration
"""

# Component testers
from .base_security_tester import *
from .components import *
from .security_engine import *
from .security_models import *
