# app/api/v1/router.py
"""
API v1 Router - Aggregates all v1 endpoints.
Future v2 endpoints will live in app/api/v2/router.py
"""
from fastapi import APIRouter

router = APIRouter()

# Sub-routers
from app.api.v1.roles import router as roles_router

router.include_router(roles_router)
