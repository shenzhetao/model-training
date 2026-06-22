from fastapi import APIRouter

from app.api.v1 import users

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(users.router, prefix="/users", tags=["users"])
