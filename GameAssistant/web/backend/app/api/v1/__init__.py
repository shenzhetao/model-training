from fastapi import APIRouter

from app.api.v1 import users, images, video, adb

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(video.router, prefix="/videos", tags=["videos"])
api_router.include_router(adb.router, prefix="/adb", tags=["adb"])
