"""
Testing and Security Assessment Routes

This module provides API endpoints for QA testing and security assessments
of Aurite components (agents, workflows, LLMs, etc.).
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from pydantic import BaseModel, Field

from ....execution.aurite_engine import AuriteEngine
from ....lib.components.evaluation.evaluator import evaluate
from ....lib.config.config_manager import ConfigManager
from ....lib.models import EvaluationRequest
from ....testing.qa.qa_engine import QAEngine
from ....testing.security.security_engine import SecurityEngine
from ....testing.security.security_models import (
    SecurityAssessmentResult,
    SecurityStatus,
    create_default_security_config,
    load_security_config_from_dict,
)
from ...dependencies import (
    get_api_key,
    get_config_manager,
    get_execution_facade,
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/testing", tags=["Testing & Security"])


# --- Request/Response Models ---


class SecurityAssessmentRequest(BaseModel):
    """Request model for security assessment."""

    component_type: str = Field(..., description="Type of component to assess (llm, agent, mcp_server, workflow)")
    component_id: str = Field(..., description="Unique identifier for the component")
    component_config: Dict[str, Any] = Field(..., description="Component configuration to assess")
    assessment_options: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional assessment parameters (e.g., specific tests to run)"
    )


class FullConfigurationAssessmentRequest(BaseModel):
    """Request model for full configuration assessment."""

    configuration: Dict[str, Any] = Field(..., description="Full configuration with multiple components to assess")
    assessment_options: Optional[Dict[str, Any]] = Field(default=None, description="Optional assessment parameters")


class SecurityAssessmentResponse(BaseModel):
    """Response model for security assessment."""

    assessment_id: str
    component_type: str
    component_id: str
    status: str
    overall_score: float
    threats_count: int
    critical_threats_count: int
    recommendations: List[str]
    duration_seconds: float

    @classmethod
    def from_assessment_result(cls, result: SecurityAssessmentResult) -> "SecurityAssessmentResponse":
        """Create response from SecurityAssessmentResult."""
        return cls(
            assessment_id=result.assessment_id,
            component_type=result.component_type,
            component_id=result.component_id,
            status=result.status.value if hasattr(result.status, "value") else str(result.status),
            overall_score=result.overall_score,
            threats_count=len(result.threats),
            critical_threats_count=len(result.get_critical_threats()) if hasattr(result, "get_critical_threats") else 0,
            recommendations=result.recommendations,
            duration_seconds=result.duration_seconds if result.duration_seconds else 0.0,
        )


class FullConfigurationAssessmentResponse(BaseModel):
    """Response model for full configuration assessment."""

    total_components: int = Field(description="Total number of components assessed")
    overall_security_score: float = Field(description="Average security score across all components")
    total_threats: int = Field(description="Total number of threats found across all components")
    critical_threats: int = Field(description="Total number of critical threats found")
    component_assessments: Dict[str, SecurityAssessmentResponse] = Field(
        description="Individual component assessment results"
    )
    assessment_summary: Dict[str, Any] = Field(description="Summary information about the assessment")

    @classmethod
    def from_assessment_results(
        cls, results: Dict[str, SecurityAssessmentResult]
    ) -> "FullConfigurationAssessmentResponse":
        """Create response from multiple SecurityAssessmentResult objects."""
        component_assessments = {}
        total_threats = 0
        critical_threats = 0
        total_score = 0.0

        for component_key, result in results.items():
            component_assessments[component_key] = SecurityAssessmentResponse.from_assessment_result(result)
            total_threats += len(result.threats)
            critical_threats += len(result.get_critical_threats()) if hasattr(result, "get_critical_threats") else 0
            total_score += result.overall_score

        overall_score = total_score / len(results) if results else 0.0

        return cls(
            total_components=len(results),
            overall_security_score=overall_score,
            total_threats=total_threats,
            critical_threats=critical_threats,
            component_assessments=component_assessments,
            assessment_summary={
                "assessment_completed_at": datetime.utcnow().isoformat(),
                "components_assessed": list(results.keys()),
                "security_status": "critical" if critical_threats > 0 else "warning" if total_threats > 0 else "good",
            },
        )


# --- Dependency Functions ---

_qa_engine_instance: Optional[QAEngine] = None
_security_engine_instance: Optional[SecurityEngine] = None


async def get_qa_engine(
    config_manager: ConfigManager = Depends(get_config_manager),
) -> QAEngine:
    """Get or create QAEngine instance."""
    global _qa_engine_instance

    if _qa_engine_instance is None:
        _qa_engine_instance = QAEngine()
        logger.info("QAEngine instance created")

    return _qa_engine_instance


async def get_security_engine(
    config_manager: ConfigManager = Depends(get_config_manager),
) -> SecurityEngine:
    """Get or create SecurityEngine instance."""
    global _security_engine_instance

    if _security_engine_instance is None:
        # Try to load security config from ConfigManager
        security_config = None
        try:
            security_config_dict = config_manager.get_config("security", "default")
            if security_config_dict and "config_dict" in security_config_dict:
                security_config = load_security_config_from_dict(security_config_dict["config_dict"])
                logger.info("Loaded security configuration from ConfigManager")
        except Exception as e:
            logger.warning(f"Could not load security config from ConfigManager: {e}")

        # Fall back to default if no config found
        if security_config is None:
            security_config = create_default_security_config()
            logger.info("Using default security configuration")

        _security_engine_instance = SecurityEngine(security_config, config_manager)
        logger.info("SecurityEngine instance created")

    return _security_engine_instance


# --- QA/Evaluation Endpoints ---


@router.post("/evaluate")
async def evaluate_component(
    request: EvaluationRequest,
    api_key: str = Security(get_api_key),
    engine: AuriteEngine = Depends(get_execution_facade),
):
    """
    Run QA evaluation on a component with the provided test cases.

    This endpoint allows you to evaluate agents, workflows, or other components
    by providing test cases with expected outputs and validation criteria.
    """
    try:
        eval_result = await evaluate(request, engine)
        return eval_result
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/evaluate/{evaluation_config_id}")
async def evaluate_component_by_config(
    evaluation_config_id: str,
    api_key: str = Security(get_api_key),
    engine: AuriteEngine = Depends(get_execution_facade),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Run QA evaluation using a saved evaluation configuration.

    This endpoint loads an evaluation configuration by ID and executes
    the evaluation based on the saved test cases and settings.
    """
    try:
        eval_config = config_manager.get_config("evaluation", evaluation_config_id)

        if not eval_config:
            raise HTTPException(status_code=404, detail=f"Evaluation configuration '{evaluation_config_id}' not found.")

        logger.info(f"Loading evaluation config: {evaluation_config_id}")

        # Convert config to EvaluationRequest
        shared_fields = set(EvaluationRequest.model_fields.keys())
        request_data = {field: eval_config[field] for field in shared_fields if field in eval_config}
        request = EvaluationRequest(**request_data)

        eval_result = await evaluate(request, engine)
        return eval_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evaluation by config failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- Security Assessment Endpoints ---


@router.post("/security/assess", response_model=SecurityAssessmentResponse)
async def assess_component_security(
    request: SecurityAssessmentRequest,
    api_key: str = Security(get_api_key),
    security_engine: SecurityEngine = Depends(get_security_engine),
):
    """
    Run security assessment on a component.

    This endpoint performs comprehensive security testing on a component,
    including vulnerability scanning, configuration auditing, and threat detection.
    """
    try:
        result = await security_engine.assess_component_security(
            component_type=request.component_type,
            component_id=request.component_id,
            component_config=request.component_config,
            assessment_options=request.assessment_options,
        )

        return SecurityAssessmentResponse.from_assessment_result(result)
    except Exception as e:
        logger.error(f"Security assessment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/security/assess/{security_config_id}", response_model=SecurityAssessmentResponse)
async def assess_component_security_by_config(
    security_config_id: str,
    component_type: str = Query(..., description="Type of component to assess"),
    component_id: str = Query(..., description="ID of component to assess"),
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
    security_engine: SecurityEngine = Depends(get_security_engine),
):
    """
    Run security assessment using a saved security configuration.

    This endpoint loads a security configuration by ID and performs
    the assessment based on the saved security policies and test settings.
    """
    try:
        # Get the component configuration
        component_config = config_manager.get_config(component_type, component_id)

        if not component_config:
            raise HTTPException(
                status_code=404, detail=f"Component '{component_id}' of type '{component_type}' not found."
            )

        # Get security configuration if specified
        assessment_options = {}
        if security_config_id != "default":
            security_config_dict = config_manager.get_config("security", security_config_id)
            if security_config_dict:
                assessment_options = security_config_dict.get("assessment_options", {})

        result = await security_engine.assess_component_security(
            component_type=component_type,
            component_id=component_id,
            component_config=component_config,
            assessment_options=assessment_options,
        )

        return SecurityAssessmentResponse.from_assessment_result(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Security assessment by config failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/security/assess-full", response_model=FullConfigurationAssessmentResponse)
async def assess_full_configuration(
    request: FullConfigurationAssessmentRequest,
    api_key: str = Security(get_api_key),
    security_engine: SecurityEngine = Depends(get_security_engine),
):
    """
    Run security assessment on a full configuration with multiple components.

    This endpoint assesses all components in a configuration and provides
    cross-component security analysis to identify systemic vulnerabilities.
    """
    try:
        logger.info("Starting full configuration assessment")
        logger.info(f"Configuration keys: {list(request.configuration.keys())}")
        logger.info(f"Assessment options: {request.assessment_options}")

        # Log configuration structure for debugging
        for comp_type, components in request.configuration.items():
            if isinstance(components, dict):
                logger.info(f"Component type '{comp_type}' has {len(components)} components: {list(components.keys())}")
            else:
                logger.info(f"Component type '{comp_type}' has non-dict value: {type(components)}")

        results = await security_engine.assess_full_configuration(
            configuration=request.configuration,
            assessment_options=request.assessment_options,
        )

        logger.info(f"Full configuration assessment completed with {len(results)} results")

        # Convert results to structured response format
        response = FullConfigurationAssessmentResponse.from_assessment_results(results)

        logger.info(f"Full configuration assessment response prepared with {response.total_components} components")
        return response
    except Exception as e:
        logger.error(f"Full configuration assessment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/security/status/{assessment_id}")
async def get_assessment_status(
    assessment_id: str,
    api_key: str = Security(get_api_key),
    security_engine: SecurityEngine = Depends(get_security_engine),
):
    """
    Get the status of a security assessment.

    This endpoint allows you to check the status of a running or completed
    security assessment by its ID.
    """
    try:
        result = security_engine.get_assessment_status(assessment_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found.")

        return {
            "assessment_id": result.assessment_id,
            "status": result.status.value if hasattr(result.status, "value") else str(result.status),
            "component_type": result.component_type,
            "component_id": result.component_id,
            "overall_score": result.overall_score if result.status == SecurityStatus.COMPLETED else None,
            "duration_seconds": result.duration_seconds if result.duration_seconds else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get assessment status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/security/cancel/{assessment_id}")
async def cancel_assessment(
    assessment_id: str,
    api_key: str = Security(get_api_key),
    security_engine: SecurityEngine = Depends(get_security_engine),
):
    """
    Cancel a running security assessment.

    This endpoint allows you to cancel a security assessment that is
    currently in progress.
    """
    try:
        cancelled = await security_engine.cancel_assessment(assessment_id)

        if not cancelled:
            raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found or not running.")

        return {"message": f"Assessment '{assessment_id}' cancelled successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel assessment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/security/active")
async def list_active_assessments(
    api_key: str = Security(get_api_key),
    security_engine: SecurityEngine = Depends(get_security_engine),
):
    """
    List all currently active security assessments.

    This endpoint returns a list of all security assessments that are
    currently pending or running.
    """
    try:
        active = security_engine.get_active_assessments()

        return {
            "active_assessments": [
                {
                    "assessment_id": result.assessment_id,
                    "status": result.status.value if hasattr(result.status, "value") else str(result.status),
                    "component_type": result.component_type,
                    "component_id": result.component_id,
                    "started_at": result.started_at.isoformat() if result.started_at else None,
                }
                for result in active.values()
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list active assessments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/security/cleanup")
async def cleanup_old_assessments(
    max_age_hours: int = 24,
    api_key: str = Security(get_api_key),
    security_engine: SecurityEngine = Depends(get_security_engine),
):
    """
    Clean up old assessment results.

    This endpoint removes assessment results older than the specified
    number of hours to free up memory.
    """
    try:
        cleaned = security_engine.cleanup_old_assessments(max_age_hours=max_age_hours)

        return {"message": f"Cleaned up {cleaned} old assessments.", "max_age_hours": max_age_hours}
    except Exception as e:
        logger.error(f"Failed to cleanup assessments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
