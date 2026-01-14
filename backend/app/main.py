from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .logging_config import configure_logging
from .db import Base, engine
from .models import AlertCooldown  # Ensure AlertCooldown table is created
from .api.routes_vessels import router as vessels_router
from .api.routes_alerts import router as alerts_router
from .api.routes_tracks import router as tracks_router
from .api.ws import router as ws_router
from .api.routes_upload import router as upload_router

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