import os
import socket

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
    applications,
    auth,
    hotel_requests,
    invitations,
    participants,
    payments,
    reports,
    theses,
)

# Версия и коммит передаются при сборке образа (ARG APP_VERSION и APP_REVISION
# в Dockerfile; в CI APP_REVISION = commit SHA), идентификатор экземпляра —
# имя контейнера (hostname) или INSTANCE_ID. По /version проверка релиза (ЛР №6)
# убеждается, что в целевой среде работает именно развёрнутый образ.
APP_VERSION = os.getenv("APP_VERSION", "dev")
APP_REVISION = os.getenv("APP_REVISION", "unknown")
INSTANCE_ID = os.getenv("INSTANCE_ID") or socket.gethostname()

app = FastAPI(
    title="Conference Management System",
    description="API для учёта участников конференции",
    version=APP_VERSION,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    """Версия приложения, коммит сборки и экземпляр, который обработал запрос."""
    return {"version": APP_VERSION, "revision": APP_REVISION, "instance": INSTANCE_ID}


app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

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

app.include_router(
    invitations.router,
    prefix="/invitations",
    tags=["Invitations"],
)

app.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"],
)

app.include_router(
    theses.router,
    prefix="/theses",
    tags=["Theses"],
)

app.include_router(
    hotel_requests.router,
    prefix="/hotel-requests",
    tags=["Hotel Requests"],
)

app.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"],
)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


@app.get("/", include_in_schema=False)
def web_interface():
    return FileResponse("app/static/index.html")
