"""Route modules grouped by the operator capability they expose."""

from fastapi import APIRouter

from backend.http.routes import analysis, demo, incidents, realtime, system


router = APIRouter(prefix="/api")
router.include_router(system.router)
router.include_router(analysis.router)
router.include_router(incidents.router)
router.include_router(demo.router)
router.include_router(realtime.router)
