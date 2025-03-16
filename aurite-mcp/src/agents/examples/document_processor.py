"""
Example implementation of a document processing workflow using BaseWorkflow.
"""

from dataclasses import dataclass
from typing import Dict, Any
import logging

from ...host.host import MCPHost
from ..base_workflow import BaseWorkflow, WorkflowStep

logger = logging.getLogger(__name__)


@dataclass
class ClassificationStep(WorkflowStep):
    """Step to classify document type"""

    def __init__(self):
        super().__init__(
            name="classify_document",
            description="Classify the document type based on content",
            required_inputs={"document_text"},
            provided_outputs={"document_type", "document_category"},
            required_tools={"classify_text"},
        )

    async def execute(self, context: Dict[str, Any], host: MCPHost) -> Dict[str, Any]:
        """Execute the classification step"""
        document_text = context["document_text"]

        # Call classification tool
        result = await host.call_tool(
            "classify_text",
            {
                "text": document_text,
                "categories": ["invoice", "report", "letter", "contract"],
            },
        )

        # Extract text result
        if result and isinstance(result, list):
            result_text = (
                result[0].text if hasattr(result[0], "text") else str(result[0])
            )
            classification = result_text.strip()

            # Use simple logic to determine category
            category_map = {
                "invoice": "financial",
                "report": "business",
                "letter": "correspondence",
                "contract": "legal",
            }

            return {
                "document_type": classification,
                "document_category": category_map.get(classification.lower(), "other"),
            }

        # Fallback result
        return {"document_type": "unknown", "document_category": "unclassified"}


@dataclass
class ExtractionStep(WorkflowStep):
    """Step to extract key information from document"""

    def __init__(self):
        super().__init__(
            name="extract_information",
            description="Extract key information from document based on type",
            required_inputs={"document_text", "document_type"},
            provided_outputs={"extracted_data"},
            required_tools={"extract_entities"},
        )

    async def execute(self, context: Dict[str, Any], host: MCPHost) -> Dict[str, Any]:
        """Execute the extraction step"""
        document_text = context["document_text"]
        document_type = context["document_type"]

        # Define entities to extract based on document type
        entities_to_extract = ["date", "title", "author"]

        # Add document-type specific entities
        if document_type.lower() == "invoice":
            entities_to_extract.extend(["amount", "invoice_number", "due_date"])
        elif document_type.lower() == "report":
            entities_to_extract.extend(["summary", "recommendations", "findings"])
        elif document_type.lower() == "letter":
            entities_to_extract.extend(["recipient", "sender", "greeting"])
        elif document_type.lower() == "contract":
            entities_to_extract.extend(["parties", "effective_date", "terms"])

        # Call extraction tool
        result = await host.call_tool(
            "extract_entities", {"text": document_text, "entities": entities_to_extract}
        )

        # Parse the results
        extracted_data = {}
        if result and isinstance(result, list):
            result_text = (
                result[0].text if hasattr(result[0], "text") else str(result[0])
            )

            # In a real implementation, this would parse structured data
            # For this example, we'll just use a placeholder
            extracted_data = {
                "document_type": document_type,
                "extracted_entities": result_text,
            }

        return {"extracted_data": extracted_data}


@dataclass
class SentimentAnalysisStep(WorkflowStep):
    """Step to analyze sentiment of document"""

    def __init__(self):
        super().__init__(
            name="analyze_sentiment",
            description="Analyze the sentiment of the document",
            required_inputs={"document_text"},
            provided_outputs={"sentiment", "sentiment_score"},
            required_tools={"analyze_sentiment"},
        )

    async def execute(self, context: Dict[str, Any], host: MCPHost) -> Dict[str, Any]:
        """Execute the sentiment analysis step"""
        document_text = context["document_text"]

        # Call sentiment analysis tool
        result = await host.call_tool("analyze_sentiment", {"text": document_text})

        # Process results
        if result and isinstance(result, list):
            result_text = (
                result[0].text if hasattr(result[0], "text") else str(result[0])
            )

            # In a real implementation, this would parse JSON or structured data
            # For this example, we'll just use placeholder values
            return {"sentiment": "positive", "sentiment_score": 0.8}

        # Fallback
        return {"sentiment": "neutral", "sentiment_score": 0.5}


@dataclass
class ReportGenerationStep(WorkflowStep):
    """Step to generate final report"""

    def __init__(self):
        super().__init__(
            name="generate_report",
            description="Generate a final report from analyzed document data",
            required_inputs={
                "document_type",
                "document_category",
                "extracted_data",
                "sentiment",
                "sentiment_score",
            },
            provided_outputs={"final_report"},
            required_tools={"generate_text"},
        )

    async def execute(self, context: Dict[str, Any], host: MCPHost) -> Dict[str, Any]:
        """Execute the report generation step"""
        # Collect all the data
        document_type = context["document_type"]
        document_category = context["document_category"]
        extracted_data = context["extracted_data"]
        sentiment = context["sentiment"]
        sentiment_score = context["sentiment_score"]

        # Create prompt for report generation
        prompt = f"""
        Generate a document analysis report with the following information:
        
        Document Type: {document_type}
        Document Category: {document_category}
        Sentiment: {sentiment} (Score: {sentiment_score})
        
        Extracted Information:
        {extracted_data}
        
        Please provide a concise summary and any relevant observations.
        """

        # Call text generation tool
        result = await host.call_tool(
            "generate_text", {"prompt": prompt, "max_length": 1000}
        )

        # Process result
        if result and isinstance(result, list):
            report_text = (
                result[0].text if hasattr(result[0], "text") else str(result[0])
            )

            return {"final_report": report_text}

        # Fallback
        return {"final_report": "Error generating report."}


class DocumentProcessorWorkflow(BaseWorkflow):
    """Workflow for processing and analyzing documents"""

    def __init__(self, host: MCPHost):
        super().__init__(host, name="document_processor")

        # Add the steps in sequence
        self.add_step(ClassificationStep())
        self.add_step(ExtractionStep())
        self.add_step(SentimentAnalysisStep())
        self.add_step(ReportGenerationStep())

        # Add custom error handler for classification step
        self.add_error_handler("classify_document", self._handle_classification_error)

        # Add context validator
        self.add_context_validator(self._validate_document_input)

    def _validate_document_input(self, context: Dict[str, Any]) -> bool:
        """Validate that document input is present and valid"""
        if "document_text" not in context:
            logger.error("Missing required input: document_text")
            return False

        # Check document is not empty
        if not context["document_text"] or len(context["document_text"]) < 10:
            logger.error("Document text is too short or empty")
            return False

        return True

    def _handle_classification_error(
        self, step: WorkflowStep, error: Exception, context: Dict[str, Any]
    ):
        """Handle errors in the classification step"""
        logger.error(f"Classification error: {error}")

        # Provide default values to allow workflow to continue
        context["document_type"] = "unknown"
        context["document_category"] = "unclassified"

        logger.info("Set default classification values to allow workflow to continue")
