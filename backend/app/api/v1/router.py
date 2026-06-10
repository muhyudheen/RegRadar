# backend/app/api/v1/router.py
# ─────────────────────────────────────────────────
#  V1 API Router
#  Registers all v1 endpoint routers in one place.
#  Add new routers here  build them.
# ─────────────────────────────────────────────────

from fastapi import APIRouter

from app.api.v1 import auth, subscriptions, changes

api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# place your future routes here

api_router.include_router(
    subscriptions.router,
    prefix="/subscriptions",
    tags=["Subscriptions"],
)

api_router.include_router(
    changes.router,
    prefix="/changes",
    tags=["Changes"],
)
