"""
Example implementation of a data analysis workflow using BaseWorkflow.

This example demonstrates:
1. Creating a workflow with steps that use the ToolManager
2. Using CompositeStep for nested step execution
3. Implementing hooks and error handlers
4. Adding validation with Pydantic models
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import logging
from pydantic import Field

from ...host.resources.tools import ToolManager
from ..base_workflow import BaseWorkflow, WorkflowStep, CompositeStep
from ..base_models import AgentContext, AgentData, StepStatus, StepResult

logger = logging.getLogger(__name__)


# Define a Pydantic model for our workflow data
class DataAnalysisContext(AgentData):
    """Data model for data analysis workflow context"""

    dataset_id: str = Field(..., description="ID of the dataset to analyze")
    analysis_type: str = Field(..., description="Type of analysis to perform")
    include_visualization: bool = Field(
        True, description="Whether to include visualizations"
    )
    max_rows: int = Field(1000, description="Maximum number of rows to analyze")
    column_filters: Optional[Dict[str, Any]] = Field(
        None, description="Filters to apply to the dataset"
    )

    # Fields that will be populated during workflow execution
    dataset_info: Optional[Dict[str, Any]] = None
    data_quality_report: Optional[Dict[str, Any]] = None
    statistical_metrics: Optional[Dict[str, Any]] = None
    visualization_urls: Optional[List[str]] = None
    analysis_results: Optional[Dict[str, Any]] = None
    final_report: Optional[str] = None


@dataclass
class DataLoadStep(WorkflowStep):
    """Step to load and validate dataset"""

    def __init__(self):
        super().__init__(
            name="load_dataset",
            description="Load dataset and validate its structure",
            required_inputs={"dataset_id", "max_rows"},
            provided_outputs={"dataset_info"},
            required_tools={"load_dataset"},
            tags={"data", "preprocessing"},
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the data loading step using ToolManager"""
        # Extract inputs from context
        dataset_id = context.get("dataset_id")
        max_rows = context.get("max_rows")

        # Use tool_manager from context to execute tool
        result = await context.tool_manager.execute_tool(
            "load_dataset",
            {"dataset_id": dataset_id, "max_rows": max_rows, "include_metadata": True},
        )

        # Process the result
        if result and isinstance(result, list):
            # Extract text content from the result
            result_text = context.tool_manager.format_tool_result(result)
            
            # In a real implementation, this would parse the JSON response
            # For test purposes, we'll continue with the placeholder data
            dataset_info = {
                "id": dataset_id,
                "num_rows": max_rows,  # This would come from the actual result
                "columns": ["column1", "column2", "column3"],  # Placeholder
                "data_types": {
                    "column1": "numeric",
                    "column2": "categorical",
                    "column3": "date",
                },  # Placeholder
                "last_updated": "2025-03-15",  # Placeholder
            }

            return {"dataset_info": dataset_info}

        # Return error information if tool call failed
        return {"dataset_info": {"error": "Failed to load dataset", "id": dataset_id}}


@dataclass
class DataQualityStep(WorkflowStep):
    """Step to assess data quality"""

    def __init__(self):
        super().__init__(
            name="assess_data_quality",
            description="Analyze data quality including missing values and outliers",
            required_inputs={"dataset_id", "dataset_info"},
            provided_outputs={"data_quality_report"},
            required_tools={"analyze_data_quality"},
            max_retries=2,
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the data quality assessment step"""
        dataset_id = context.get("dataset_id")
        dataset_info = context.get("dataset_info")

        # Use tool_manager from context
        result = await context.tool_manager.execute_tool(
            "analyze_data_quality",
            {"dataset_id": dataset_id, "columns": dataset_info.get("columns", [])},
        )

        # Extract text content from the result
        result_text = context.tool_manager.format_tool_result(result)
        
        # Process results - in a real implementation this would parse the actual JSON from result_text
        quality_report = {
            "missing_values": {
                "column1": 0.05,  # 5% missing
                "column2": 0.02,  # 2% missing
                "column3": 0.00,  # 0% missing
            },
            "outliers": {
                "column1": 0.03,  # 3% outliers
            },
            "overall_quality_score": 0.95,  # 95% quality score
        }

        return {"data_quality_report": quality_report}


@dataclass
class StatisticalAnalysisStep(WorkflowStep):
    """Step to perform statistical analysis"""

    def __init__(self):
        super().__init__(
            name="statistical_analysis",
            description="Calculate statistical metrics for the dataset",
            required_inputs={"dataset_id", "dataset_info", "analysis_type"},
            provided_outputs={"statistical_metrics"},
            required_tools={"calculate_statistics"},
            timeout=120.0,  # Longer timeout for complex calculations
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the statistical analysis step"""
        dataset_id = context.get("dataset_id")
        analysis_type = context.get("analysis_type")
        dataset_info = context.get("dataset_info")

        # Determine which metrics to calculate based on analysis type
        metrics_to_calculate = ["mean", "median", "std_dev"]
        if analysis_type.lower() == "comprehensive":
            metrics_to_calculate.extend(["quartiles", "skewness", "kurtosis"])

        # Use tool_manager to execute the statistics calculation
        result = await context.tool_manager.execute_tool(
            "calculate_statistics",
            {
                "dataset_id": dataset_id,
                "metrics": metrics_to_calculate,
                "numeric_columns": [
                    col
                    for col, type in dataset_info.get("data_types", {}).items()
                    if type == "numeric"
                ],
            },
        )

        # Extract text content from the result
        result_text = context.tool_manager.format_tool_result(result)
        
        # Process results (in a real implementation, this would parse the JSON from result_text)
        statistical_metrics = {
            "descriptive_stats": {
                "column1": {"mean": 42.5, "median": 41.2, "std_dev": 5.3}
            },
            "analysis_type": analysis_type,
        }

        if analysis_type.lower() == "comprehensive":
            statistical_metrics["descriptive_stats"]["column1"].update(
                {"quartiles": [36.2, 41.2, 47.8], "skewness": 0.12, "kurtosis": -0.34}
            )

        return {"statistical_metrics": statistical_metrics}


@dataclass
class VisualizationStep(WorkflowStep):
    """Step to generate data visualizations"""

    def __init__(self):
        super().__init__(
            name="generate_visualizations",
            description="Create visualizations of the dataset",
            required_inputs={"dataset_id", "analysis_type", "include_visualization"},
            provided_outputs={"visualization_urls"},
            required_tools={"create_visualization"},
            # Only execute this step if visualizations are requested
            condition=lambda context: context.get("include_visualization", False),
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the visualization step"""
        # Skip execution if visualizations are not requested
        if not context.get("include_visualization"):
            return {"visualization_urls": []}

        dataset_id = context.get("dataset_id")
        analysis_type = context.get("analysis_type")

        # Determine which visualizations to create based on analysis type
        viz_types = ["histogram", "scatter_plot"]
        if analysis_type.lower() == "comprehensive":
            viz_types.extend(["box_plot", "correlation_matrix"])

        # Use tool_manager to create visualizations
        visualization_urls = []
        for viz_type in viz_types:
            result = await context.tool_manager.execute_tool(
                "create_visualization",
                {"dataset_id": dataset_id, "type": viz_type, "format": "png"},
            )
            
            # Extract text content from the result
            result_text = context.tool_manager.format_tool_result(result)
            
            # In a real implementation, this would extract the URL from result_text
            visualization_urls.append(
                f"https://example.com/visualizations/{dataset_id}/{viz_type}.png"
            )

        return {"visualization_urls": visualization_urls}


@dataclass
class InsightGenerationStep(WorkflowStep):
    """Step to generate insights from analysis"""

    def __init__(self):
        super().__init__(
            name="generate_insights",
            description="Generate insights based on the analysis results",
            required_inputs={
                "dataset_info",
                "data_quality_report",
                "statistical_metrics",
                "analysis_type",
            },
            provided_outputs={"analysis_results"},
            required_tools={"generate_insights"},
        )

        # Set condition to check that all required data is available
        # Note: Using a regular function instead of lambda for better error handling
        def check_required_data(context_data):
            return all(
                key in context_data
                for key in [
                    "dataset_info",
                    "data_quality_report",
                    "statistical_metrics",
                ]
            )

        self.condition = check_required_data

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the insight generation step"""
        # Use a default empty dict if the value is None to prevent NoneType errors
        dataset_info = context.get("dataset_info") or {}
        data_quality = context.get("data_quality_report") or {}
        statistics = context.get("statistical_metrics") or {}
        analysis_type = context.get("analysis_type", "basic")

        # Call the insight generation tool
        result = await context.tool_manager.execute_tool(
            "generate_insights",
            {
                "dataset_metadata": dataset_info,
                "quality_metrics": data_quality,
                "statistical_metrics": statistics,
                "depth": "detailed"
                if analysis_type.lower() == "comprehensive"
                else "basic",
            },
        )
        
        # Extract text content from the result
        result_text = context.tool_manager.format_tool_result(result)

        # Process results - in a real implementation this would parse the JSON from result_text
        insights = {
            "key_findings": [
                "The data shows a strong correlation between X and Y",
                "There is a significant outlier group in column Z",
                "Time series analysis indicates a seasonal pattern",
            ],
            "recommendations": [
                "Further investigate the outlier group",
                "Consider normalizing the data before modeling",
            ],
        }

        return {"analysis_results": insights}


@dataclass
class ReportGenerationStep(WorkflowStep):
    """Step to generate final analysis report"""

    def __init__(self):
        super().__init__(
            name="generate_report",
            description="Generate a comprehensive final report",
            required_inputs={
                "dataset_info",
                "data_quality_report",
                "statistical_metrics",
                "analysis_results",
            },
            provided_outputs={"final_report"},
            required_tools={"generate_report"},
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the report generation step"""
        # Collect all inputs with fallbacks to prevent NoneType errors
        dataset_info = context.get("dataset_info") or {}
        data_quality = context.get("data_quality_report") or {}
        statistics = context.get("statistical_metrics") or {}
        analysis_results = context.get("analysis_results") or {}
        visualization_urls = context.get("visualization_urls") or []

        # Create input for report generation
        report_input = {
            "title": f"Analysis Report for Dataset {dataset_info.get('id', 'Unknown')}",
            "sections": [
                {"name": "Dataset Overview", "content": dataset_info},
                {"name": "Data Quality Assessment", "content": data_quality},
                {"name": "Statistical Analysis", "content": statistics},
                {"name": "Key Insights", "content": analysis_results},
            ],
        }

        if visualization_urls:
            report_input["visualizations"] = visualization_urls

        # Generate report
        result = await context.tool_manager.execute_tool(
            "generate_report", report_input
        )
        
        # Extract text content from the result
        result_text = context.tool_manager.format_tool_result(result)

        # Extract report text
        report_text = "# Data Analysis Report\n\n"
        report_text += f"## Dataset: {dataset_info.get('id', 'Unknown')}\n\n"
        report_text += "### Data Quality\n"
        report_text += f"Overall quality score: {data_quality.get('overall_quality_score', 'N/A')}\n\n"
        report_text += "### Statistical Summary\n"
        report_text += "Key metrics calculated based on dataset characteristics.\n\n"
        report_text += "### Key Findings\n"
        for finding in analysis_results.get("key_findings", []):
            report_text += f"- {finding}\n"
        if not analysis_results.get("key_findings"):
            report_text += "- No key findings available\n"

        report_text += "\n### Recommendations\n"
        for recommendation in analysis_results.get("recommendations", []):
            report_text += f"- {recommendation}\n"
        if not analysis_results.get("recommendations"):
            report_text += "- No recommendations available\n"

        if visualization_urls:
            report_text += "\n### Visualizations\n"
            for url in visualization_urls:
                report_text += f"- [View visualization]({url})\n"

        return {"final_report": report_text}


class DataAnalysisWorkflow(BaseWorkflow):
    """
    Workflow for analyzing datasets.

    This workflow demonstrates the complete life cycle of a data analysis task:
    1. Load and validate the dataset
    2. Assess data quality
    3. Perform statistical analysis
    4. Generate visualizations (optional)
    5. Generate insights
    6. Create final report

    It uses the AgentContext with a Pydantic model for type safety and
    leverages the ToolManager for tool execution.
    """

    def __init__(self, tool_manager: ToolManager, name: str = "data_analysis_workflow"):
        """Initialize the data analysis workflow"""
        super().__init__(tool_manager, name=name)
        
        # Set description for documentation
        self.description = "Comprehensive data analysis workflow for exploring datasets"

        # Add individual steps
        self.add_step(DataLoadStep())

        # Create a composite step for data preparation and analysis
        preparation_analysis = CompositeStep(
            name="preparation_and_analysis",
            description="Prepare and analyze the dataset",
            steps=[DataQualityStep(), StatisticalAnalysisStep()],
        )

        # Add the composite step
        self.add_step(preparation_analysis)

        # Add visualization step with condition
        self.add_step(VisualizationStep())

        # Create a composite step for results generation
        results_generation = CompositeStep(
            name="results_generation",
            description="Generate insights and final report",
            steps=[InsightGenerationStep(), ReportGenerationStep()],
        )

        # Add the results generation composite step
        self.add_step(results_generation)

        # Add error handlers
        self.add_error_handler("load_dataset", self._handle_data_load_error)
        self.set_global_error_handler(self._global_error_handler)

        # Add before/after hooks
        self.add_before_workflow_hook(self._before_workflow)
        self.add_after_workflow_hook(self._after_workflow)
        self.add_before_step_hook(self._before_step)
        self.add_after_step_hook(self._after_step)

    async def _before_workflow(self, context: AgentContext):
        """Hook that runs before workflow execution"""
        logger.info(
            f"Starting data analysis workflow for dataset {context.get('dataset_id')}"
        )

        # Additional setup could be done here
        context.metadata["workflow_start_message"] = (
            f"Analysis of {context.get('dataset_id')} starting"
        )

    async def _after_workflow(self, context: AgentContext):
        """Hook that runs after workflow execution"""
        execution_time = context.get_execution_time()
        logger.info(f"Data analysis workflow completed in {execution_time:.2f} seconds")

        # Could add metrics collection or notifications here
        context.metadata["execution_summary"] = {
            "total_execution_time": execution_time,
            "steps_completed": len(
                [
                    s
                    for s in context.step_results.values()
                    if s.status == StepStatus.COMPLETED
                ]
            ),
            "report_generated": "final_report" in context.get_data_dict(),
        }

    async def _before_step(self, step: WorkflowStep, context: AgentContext):
        """Hook that runs before each step execution"""
        logger.info(f"Executing step: {step.name}")

        # Could add detailed logging or tracing here
        step_inputs = {
            k: context.get(k) for k in step.required_inputs if hasattr(context.data, k)
        }
        logger.debug(f"Step {step.name} inputs: {step_inputs.keys()}")

    async def _after_step(
        self, step: WorkflowStep, context: AgentContext, result: StepResult
    ):
        """Hook that runs after each step execution"""
        if result.status == StepStatus.COMPLETED:
            logger.info(
                f"Step {step.name} completed in {result.execution_time:.2f} seconds"
            )
            # Record provided outputs for debugging/tracing
            output_keys = result.outputs.keys() if result.outputs else []
            logger.debug(f"Step {step.name} provided outputs: {output_keys}")
        elif result.status == StepStatus.FAILED:
            logger.error(f"Step {step.name} failed: {result.error}")
        elif result.status == StepStatus.SKIPPED:
            logger.info(f"Step {step.name} was skipped")

    def _handle_data_load_error(
        self, step: WorkflowStep, error: Exception, context: Dict[str, Any]
    ):
        """Special handler for data loading errors"""
        logger.error(f"Data loading error: {error}")

        # Add error information to context for reporting
        context["dataset_info"] = {
            "error": f"Failed to load dataset: {error}",
            "id": context.get("dataset_id", "unknown"),
            "status": "error",
        }

        # Could trigger fallback mechanisms or notifications

    def _global_error_handler(
        self, step: WorkflowStep, error: Exception, context: Dict[str, Any]
    ):
        """Global error handler for all steps"""
        logger.error(f"Error in step {step.name}: {error}")

        # Record error in context metadata for reporting
        if "errors" not in context:
            context["errors"] = []

        context["errors"].append(
            {"step": step.name, "error": str(error), "type": type(error).__name__}
        )

        # Could implement recovery logic based on step and error type

    async def analyze_dataset(
        self,
        dataset_id: str,
        analysis_type: str,
        include_visualization: bool = True,
        max_rows: int = 1000,
        column_filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method to execute the workflow with specific parameters.

        Args:
            dataset_id: ID of the dataset to analyze
            analysis_type: Type of analysis ("basic" or "comprehensive")
            include_visualization: Whether to include visualizations
            max_rows: Maximum number of rows to process
            column_filters: Optional filters to apply

        Returns:
            Dictionary with analysis results
        """
        # Create a typed context with our Pydantic model
        input_data = {
            "dataset_id": dataset_id,
            "analysis_type": analysis_type,
            "include_visualization": include_visualization,
            "max_rows": max_rows,
        }

        if column_filters:
            input_data["column_filters"] = column_filters

        # Execute the workflow
        result_context = await self.execute(input_data)

        # Return the summarized results
        return result_context.summarize_results()


# Example usage:
# async def main():
#     host = MCPHost(...)
#     await host.initialize()
#
#     workflow = DataAnalysisWorkflow(host)
#     await workflow.initialize()
#
#     results = await workflow.analyze_dataset(
#         dataset_id="sales_data_2025",
#         analysis_type="comprehensive",
#         include_visualization=True
#     )
#
#     print(f"Analysis complete. Report generated: {results['data'].get('final_report') is not None}")
