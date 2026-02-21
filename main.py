from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import tasks, habits, slots, plan, feedback, settings as settings_router, profile, library, reset, metrics
from app.routers import import_draft


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_db()
    yield


app = FastAPI(
    title="StudyFlow API",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(habits.router, prefix="/api/v1")
app.include_router(slots.router, prefix="/api/v1")
app.include_router(plan.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(library.router, prefix="/api/v1")
app.include_router(reset.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(import_draft.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "StudyFlow API is running", "version": settings.app_version}


@app.get("/health")
async def health():
    return {"status": "ok"}
