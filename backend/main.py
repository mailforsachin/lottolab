"""LottoLab - Main Application Entry Point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.config.settings import settings
from backend.api.v1.endpoints import (
    auth,
    draws,
    portfolios,
    simulations,
    statistics,
    strategies,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    yield

app = FastAPI(
    title="LottoLab API",
    description="Statistical analysis, simulation, and optimization platform for lottery games",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(draws.router, prefix="/api/v1/draws", tags=["draws"])
app.include_router(portfolios.router, prefix="/api/v1/portfolios", tags=["portfolios"])
app.include_router(simulations.router, prefix="/api/v1/simulations", tags=["simulations"])
app.include_router(statistics.router, prefix="/api/v1/statistics", tags=["statistics"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])

# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/login")
    async def serve_login():
        login_path = os.path.join(frontend_path, "login.html")
        if os.path.exists(login_path):
            return FileResponse(login_path)
        return {"message": "Login page not found"}

    @app.get("/")
    async def serve_frontend():
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend not found"}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8044,
        reload=settings.DEBUG
    )
