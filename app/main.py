from fastapi import FastAPI

from app.routers import applications, participants

app = FastAPI(
    title="Conference Management System",
    description="API для учёта участников конференции",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(
    participants.router,
    prefix="/participants",
    tags=["Participants"],
)

app.include_router(
    applications.router,
    prefix="/applications",
    tags=["Applications"],
)