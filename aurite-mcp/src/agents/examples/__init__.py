"""
Example implementations of Aurite agents using the base classes.
"""

try:
    from .research_assistant import ResearchAssistantAgent
except ImportError:
    # Skip if file doesn't exist
    pass

try:
    from .data_analysis_workflow import DataAnalysisWorkflow
except ImportError:
    # Skip if file doesn't exist
    pass
