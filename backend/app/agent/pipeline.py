"""
AutoMerge Agent Pipeline Orchestrator

Coordinates the full autonomous fix workflow:
  ingest → parse → extract → classify → analyze → patch → validate → summarize
"""

import asyncio
import structlog
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, PipelineStep, Patch, ValidationResult, Summary
from app.agent.log_parser import parse_logs
from app.agent.signal_extractor import extract_signals
from app.agent.failure_classifier import classify_failure
from app.agent.precision_triage import precision_triage
from app.agent.reproduction_engine import assess_reproduction
from app.agent.root_cause_analyzer import analyze_root_cause
from app.agent.patch_generator import generate_patch
from app.agent.patch_validator import validate_patch
from app.agent.commit_tracer import trace_causal_commit
from app.agent.evidence_aggregator import aggregate_evidence
from app.agent.summary_reporter import generate_summary
from app.agent.memory import record_pattern

logger = structlog.get_logger("automerge.pipeline")


# Pipeline step definitions (in order)
PIPELINE_STEPS = [
    "log_parsing",
    "signal_extraction",
    "failure_classification",
    "precision_triage",
    "reproduction_assessment",
    "root_cause_analysis",
    "patch_generation",
    "patch_validation",
    "commit_tracing",
    "evidence_aggregation",
    "summary_generation",
]


async def execute_pipeline(job_id: str, db: AsyncSession) -> None:
    """Execute the full agent pipeline for a job."""
    logger.info("pipeline.start", job_id=job_id)

    # Fetch job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        logger.error("pipeline.job_not_found", job_id=job_id)
        return

    # Update status to running
    job.status = "analyzing"
    await db.commit()

    # Create pipeline step records
    steps = {}
    for i, step_name in enumerate(PIPELINE_STEPS):
        step = PipelineStep(
            job_id=job_id,
            step_name=step_name,
            status="pending",
            order_index=i,
        )
        db.add(step)
        steps[step_name] = step
    await db.commit()

    # State accumulator passed between steps
    state = {
        "raw_logs": job.raw_logs,
        "failure_title": job.failure_title,
        "failure_type": job.failure_type,
    }

    try:
        # Step 1: Parse logs
        state = await _run_step(steps["log_parsing"], db, parse_logs, state)

        # Step 2: Extract signals
        state = await _run_step(steps["signal_extraction"], db, extract_signals, state)

        # Step 3: Classify failure type
        state = await _run_step(steps["failure_classification"], db, classify_failure, state)

        # Step 4: Precision triage — evidence quality gate
        state = await _run_step(steps["precision_triage"], db, precision_triage, state)

        # Step 5: Reproduction assessment — flake & stability check
        state = await _run_step(steps["reproduction_assessment"], db, assess_reproduction, state)

        # Step 6: Root cause analysis
        job.status = "diagnosing"
        await db.commit()
        state = await _run_step(steps["root_cause_analysis"], db, analyze_root_cause, state)

        # Update job with analysis results
        job.root_cause = state.get("root_cause", "")
        job.confidence_score = state.get("confidence", 0.0)
        job.failure_type = state.get("failure_type", job.failure_type)
        await db.commit()

        # Step 5: Generate patch
        job.status = "patching"
        await db.commit()
        state = await _run_step(steps["patch_generation"], db, generate_patch, state)

        # Save patch to database
        patch_data = state.get("patch", {})
        if patch_data:
            patch = Patch(
                job_id=job_id,
                file_path=patch_data.get("file_path", "unknown"),
                original_code=patch_data.get("original_code", ""),
                fixed_code=patch_data.get("fixed_code", ""),
                diff_text=patch_data.get("diff_text", ""),
                explanation=patch_data.get("explanation", ""),
                language=patch_data.get("language", "python"),
            )
            db.add(patch)
            await db.commit()

        # Step 8: Validate patch
        job.status = "validating"
        await db.commit()
        state = await _run_step(steps["patch_validation"], db, validate_patch, state)

        # Save validation result
        validation_data = state.get("validation", {})
        validation = ValidationResult(
            job_id=job_id,
            status=validation_data.get("status", "passed"),
            stdout=validation_data.get("stdout", ""),
            stderr=validation_data.get("stderr", ""),
            tests_passed=validation_data.get("tests_passed", 0),
            tests_failed=validation_data.get("tests_failed", 0),
            tests_total=validation_data.get("tests_total", 0),
            duration_seconds=validation_data.get("duration_seconds", 0.0),
            validated_at=datetime.now(timezone.utc),
        )
        db.add(validation)
        await db.commit()

        # Handle validation failure → retry
        if validation_data.get("status") == "failed" and job.retry_count < job.max_retries:
            job.retry_count += 1
            job.status = "retrying"
            await db.commit()
            logger.info("pipeline.retrying", job_id=job_id, retry=job.retry_count)

            # Re-run patch generation and validation with retry context
            state["retry_attempt"] = job.retry_count
            state = await _run_step(steps["patch_generation"], db, generate_patch, state)
            state = await _run_step(steps["patch_validation"], db, validate_patch, state)

        # Step 9: Commit tracing — causal commit identification
        state = await _run_step(steps["commit_tracing"], db, trace_causal_commit, state)

        # Step 10: Evidence aggregation — final scoring & merging
        state = await _run_step(steps["evidence_aggregation"], db, aggregate_evidence, state)

        # Step 11: Generate summary
        job.status = "summarizing"
        await db.commit()
        state = await _run_step(steps["summary_generation"], db, generate_summary, state)

        # Save summary
        summary_data = state.get("summary", {})
        summary = Summary(
            job_id=job_id,
            title=summary_data.get("title", ""),
            root_cause=summary_data.get("root_cause", ""),
            fix_description=summary_data.get("fix_description", ""),
            pr_title=summary_data.get("pr_title", ""),
            pr_body=summary_data.get("pr_body", ""),
            reasoning_trace=summary_data.get("reasoning_trace", ""),
            impact_assessment=summary_data.get("impact_assessment", ""),
            # Precision fields
            evidence_report_json=summary_data.get("evidence_report_json", "{}"),
            triage_verdict=summary_data.get("triage_verdict", ""),
            confidence_calibrated=summary_data.get("confidence_calibrated", 0.0),
            reproducibility=summary_data.get("reproducibility", ""),
            flake_score=summary_data.get("flake_score", 0.0),
            severity=summary_data.get("severity", ""),
            commit_trace_json=summary_data.get("commit_trace_json", "{}"),
            why_real=summary_data.get("why_real", "[]"),
            why_noise=summary_data.get("why_noise", "[]"),
            next_action=summary_data.get("next_action", ""),
        )
        db.add(summary)

        # Record bug pattern in memory
        await record_pattern(db, state)

        # Final status
        job.status = "completed"
        job.reasoning_trace = summary_data.get("reasoning_trace", "")
        await db.commit()

        logger.info("pipeline.completed", job_id=job_id, confidence=job.confidence_score)

    except Exception as e:
        logger.error("pipeline.error", job_id=job_id, error=str(e))
        job.status = "failed"
        job.reasoning_trace = f"Pipeline failed: {str(e)}"
        await db.commit()


async def _run_step(
    step: PipelineStep,
    db: AsyncSession,
    handler,
    state: dict,
) -> dict:
    """Execute a single pipeline step with timing and error handling."""
    import json

    step.status = "running"
    step.started_at = datetime.now(timezone.utc)
    await db.commit()

    # Simulate realistic processing time for demo feel
    await asyncio.sleep(0.8)

    try:
        result = await handler(state)
        step.status = "completed"
        step.output_data = json.dumps(
            {k: v for k, v in result.items() if isinstance(v, (str, int, float, bool, list))},
            default=str,
        )[:4000]  # Truncate to prevent massive storage
    except Exception as e:
        step.status = "failed"
        step.error_message = str(e)
        result = state  # Pass through on failure
        logger.error("step.failed", step=step.step_name, error=str(e))

    step.completed_at = datetime.now(timezone.utc)
    if step.started_at:
        step.duration_ms = int((step.completed_at - step.started_at).total_seconds() * 1000)
    await db.commit()

    return result
