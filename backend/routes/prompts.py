"""
backend/routes/prompts.py
-------------------------
Prompt versioning and A/B comparison endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from engines.prompt_manager import (
    create_prompt_version, get_active_prompt, list_versions,
    activate_version, record_ab_result, list_ab_results,
)

router = APIRouter(tags=["prompts"])


class PromptVersionRequest(BaseModel):
    name: str = "session_analysis"
    system_prompt: str
    model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    temperature: float = 1.0
    max_tokens: int = 1024
    activate: bool = False


class AbResultRequest(BaseModel):
    session_id: int
    prompt_a_id: int
    prompt_b_id: int
    winner: Optional[str] = None
    metrics: Optional[dict] = None


@router.get("")
def list_prompt_versions(name: str = Query("session_analysis")):
    """List all versions of a prompt template."""
    return list_versions(name)


@router.get("/active")
def get_active(name: str = Query("session_analysis")):
    """Get the currently active prompt version."""
    prompt = get_active_prompt(name)
    if not prompt:
        raise HTTPException(status_code=404, detail="No active prompt found.")
    return prompt


@router.post("")
def create_version(body: PromptVersionRequest):
    """Create a new prompt version."""
    return create_prompt_version(
        name=body.name,
        system_prompt=body.system_prompt,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        activate=body.activate,
    )


@router.post("/{prompt_id}/activate")
def activate(prompt_id: int):
    """Activate a specific prompt version."""
    success = activate_version(prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt version not found.")
    return {"id": prompt_id, "activated": True}


@router.post("/ab")
def create_ab_result(body: AbResultRequest):
    """Record an A/B comparison result."""
    return record_ab_result(
        session_id=body.session_id,
        prompt_a_id=body.prompt_a_id,
        prompt_b_id=body.prompt_b_id,
        winner=body.winner,
        metrics=body.metrics,
    )


@router.get("/ab")
def get_ab_results(session_id: Optional[int] = Query(None), limit: int = Query(50, le=200)):
    """List A/B comparison results."""
    return list_ab_results(session_id=session_id, limit=limit)
