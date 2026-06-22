from fastapi import APIRouter

from app.api.v1 import users, images, video, adb, annotations, templates, datasets, models, training

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(video.router, prefix="/videos", tags=["videos"])
api_router.include_router(adb.router, prefix="/adb", tags=["adb"])
api_router.include_router(annotations.router, prefix="/annotations", tags=["annotations"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(training.router, prefix="/training", tags=["training"])
