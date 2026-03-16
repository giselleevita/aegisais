from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import configure_logging
from app.core.database import Base, engine
from app.modules.alerts.models import AlertCooldown
from app.modules.vessels.models import VesselPosition
from app.api.v1.vessels import router as vessels_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.tracks import router as tracks_router
from app.infrastructure.ws.manager import router as ws_router
from app.api.v1.upload import router as upload_router
from app.api.v1.health import router as health_router

# ITDAE integration
from app.modules.itdae.api.routes_itdae import router as itdae_router

configure_logging()
# Note: Database migrations are handled by Alembic
# Run migrations with: alembic upgrade head
# For development, you can still use create_all, but migrations are preferred
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="AegisAIS")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vessels_router, prefix="/v1", tags=["vessels"])
app.include_router(alerts_router, prefix="/v1", tags=["alerts"])
app.include_router(tracks_router, prefix="/v1", tags=["replay"])
app.include_router(ws_router, prefix="/v1", tags=["stream"])
app.include_router(upload_router, prefix="/v1", tags=["upload"])
app.include_router(health_router, prefix="/v1", tags=["health"])
app.include_router(itdae_router, prefix="/api/v1/itdae", tags=["itdae"])

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AegisAIS",
        "version": "0.1.0",
        "description": "AIS Data Integrity and Anomaly Detection Tool",
        "docs": "/docs",
        "health": "/v1/health"
    }
