from fastapi import APIRouter
from api.routes.webhooks import router as webhooks_router
from api.routes.checkout import router as checkout_router

router = APIRouter()

router.include_router(webhooks_router)
router.include_router(checkout_router)

__all__ = ["router"]
