from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import ADMIN_DIR, ASSETS_DIR, STATIC_DIR, UPLOADS_DIR, get_settings
from app.errors import install_error_handlers
from app.routers import admin, auth, events, me, shop, submissions

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="龄花里 API", version="0.1.0")

    origins = settings.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    for r in (auth.router, me.router, events.router, submissions.router, shop.router, admin.router):
        app.include_router(r, prefix=API_PREFIX)

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    # follow_symlink: on the server static/uploads links to a directory outside the release tree
    app.mount("/static", StaticFiles(directory=STATIC_DIR, follow_symlink=True), name="static")
    # Operator console (static SPA; talks to /api/v1/admin with X-Admin-Token).
    app.mount("/admin", StaticFiles(directory=ADMIN_DIR, html=True), name="admin")
    return app


app = create_app()
