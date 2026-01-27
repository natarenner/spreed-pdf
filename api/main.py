from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from api.settings import api_settings
from api.routes import router
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app() -> FastAPI:
    """Create a FastAPI App"""

    # Create FastAPI App
    app: FastAPI = FastAPI(
        title=api_settings.title,
        version=api_settings.version,
        docs_url="/docs" if api_settings.docs_enabled else None,
        redoc_url="/redoc" if api_settings.docs_enabled else None,
        openapi_url="/openapi.json" if api_settings.docs_enabled else None,
    )

    # Add api router
    app.include_router(router, prefix="/api")

    # Add Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount templates (at the end so it doesn't intercept API calls)
    app.mount("/", StaticFiles(directory=str(BASE_DIR / "templates"), html=True), name="static")
    
    return app


# Create a FastAPI app
app = create_app()
