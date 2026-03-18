"""Kyron Medical AI - FastAPI Application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import init_db, async_session
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize database and seed data."""
    await init_db()
    async with async_session() as db:
        await seed_database(db)
    print("🏥 Kyron Medical AI is ready!")
    yield
    print("👋 Kyron Medical AI shutting down.")


app = FastAPI(
    title="Kyron Medical AI",
    description="AI-powered medical assistant for patient scheduling and support",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routes
from app.routes import chat, voice, info

app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(info.router, prefix="/api", tags=["Info"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Kyron Medical AI"}


# Serve static frontend files in production
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

