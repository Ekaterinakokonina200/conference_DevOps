from fastapi import FastAPI

app = FastAPI(
    title="Conference Management System",
    description="API для учёта участников конференции",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}