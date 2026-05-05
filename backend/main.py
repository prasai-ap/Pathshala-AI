from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.app_name = "Pathshala AI"
    yield


app = FastAPI(
    title="Pathshala AI API",
    description="Backend API skeleton for a bilingual AI tutor for rural primary education in Nepal.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "pathshala-ai-backend"}
