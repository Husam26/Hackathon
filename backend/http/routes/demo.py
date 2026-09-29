"""Deterministic guided-demo endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from backend.demo import DemoStatus, DemoStepResult
from backend.http.dependencies import services_from
from backend.memory_preferences import MemoryPreferences


router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/status", response_model=DemoStatus)
async def demo_status(request: Request) -> DemoStatus:
    return services_from(request).demo.status()


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_demo(request: Request) -> None:
    await services_from(request).demo.reset()


@router.post("/step", response_model=DemoStepResult)
async def step_demo(
    request: Request, preferences: MemoryPreferences | None = None
) -> DemoStepResult:
    try:
        return await services_from(request).demo.step(preferences)
    except IndexError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
