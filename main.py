from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import tasks, slots, habits, settings, profile, feedback, library, plan, reset

Base.metadata.create_all(bind=engine)

app = FastAPI(title="StudyFlow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router, prefix="/api/v1")
app.include_router(slots.router, prefix="/api/v1")
app.include_router(habits.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(library.router, prefix="/api/v1")
app.include_router(plan.router, prefix="/api/v1")
app.include_router(reset.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "StudyFlow API is running"}
