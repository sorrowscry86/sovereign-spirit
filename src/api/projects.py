"""
VoidCat RDC: Sovereign Spirit — Projects API
=============================================
Endpoints for creating and managing long-running agent projects.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.core.database import get_database
from src.core.graph import get_graph
from src.middleware.security import verify_api_key

logger = logging.getLogger("sovereign.api.projects")
router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    title: str
    description: str
    lead_agent_id: Optional[str] = None


class ProjectStatusUpdate(BaseModel):
    status: str  # active | paused | complete


@router.post("/", status_code=201)
async def create_project(
    body: ProjectCreate,
    _: str = Depends(verify_api_key),
):
    """Create a new project and assign a lead agent."""
    db = get_database()
    project_id = await db.create_project(
        title=body.title,
        description=body.description,
        lead_agent_id=body.lead_agent_id,
    )
    project = await db.get_project(project_id)
    return project


@router.get("/")
async def list_projects(
    status: Optional[str] = None,
    _: str = Depends(verify_api_key),
):
    """List all projects, optionally filtered by status."""
    db = get_database()
    projects = await db.list_projects(status=status)
    return {"projects": projects, "count": len(projects)}


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    _: str = Depends(verify_api_key),
):
    """Get full project detail including progress notes."""
    db = get_database()
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}")
async def update_project_status(
    project_id: str,
    body: ProjectStatusUpdate,
    _: str = Depends(verify_api_key),
):
    """Update project status (active | paused | complete)."""
    if body.status not in ("active", "paused", "complete"):
        raise HTTPException(
            status_code=400, detail="Invalid status. Use: active, paused, complete"
        )
    db = get_database()
    updated = await db.update_project_status(project_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return await db.get_project(project_id)


@router.get("/{project_id}/tasks")
async def get_project_tasks(
    project_id: str,
    _: str = Depends(verify_api_key),
):
    """Get all Neo4j tasks linked to a project."""
    graph = get_graph()
    tasks = await graph.get_tasks_for_project(project_id)
    return {"tasks": tasks, "count": len(tasks)}
