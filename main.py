import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from database import init_db
from routes.api import router as api_router
from routes.admin import router as admin_router

app = FastAPI(
    title="MediaAPI",
    description="Universal Media Download API — 1000+ platforms supported",
    version="2.0.0",
    docs_url="/swagger",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/health", tags=["System"])
async def health_check():
    from database import get_stats
    stats = get_stats()
    return {
        "status": "ok",
        "version": "2.0.0",
        "total_keys": stats["total_keys"],
        "total_requests": stats["total_requests"],
        "today_requests": stats["today_requests"],
    }

app.include_router(api_router, prefix="/api", tags=["Media API"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])

# Serve frontend (must be last)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
