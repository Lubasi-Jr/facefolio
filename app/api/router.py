from fastapi import APIRouter

from app.api.events import router as events_router
from app.api.invitations import router as invitations_router
from app.api.photos import router as photos_router

api_router = APIRouter()
api_router.include_router(events_router)
api_router.include_router(invitations_router)
api_router.include_router(photos_router)
