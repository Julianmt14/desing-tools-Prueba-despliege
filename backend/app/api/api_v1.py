from fastapi import APIRouter

from app.api.routes import auth, users, designs, drawing_exports
from app.api.routes.tools import despiece, hooks, rebar

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(designs.router)
api_router.include_router(drawing_exports.router)
api_router.include_router(despiece.router)
api_router.include_router(hooks.router)
api_router.include_router(rebar.router)
