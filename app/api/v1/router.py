# app/api/v1/router.py
"""
API v1 Router - Aggregates all v1 endpoints.
Future v2 endpoints will live in app/api/v2/router.py
"""
from fastapi import APIRouter

router = APIRouter()

# Import and include sub-routers as they are created
# from app.api.v1.chat import router as chat_router
# from app.api.v1.memory import router as memory_router
# router.include_router(chat_router)
# router.include_router(memory_router)
