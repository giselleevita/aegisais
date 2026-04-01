import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.infrastructure.ws import manager as ws_manager
from app.api.v1.vessels import router as vessels_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.tracks import router as tracks_router
from app.infrastructure.ws.manager import router as ws_router
from app.api.v1.upload import router as upload_router
from app.api.v1.health import router as health_router
from app.api.v1.audit import router as audit_router
from app.api.v1.watchlist import router as watchlist_router
from app.api.v1.reports import router as reports_router
from app.api.v1.incidents import router as incidents_router
from app.modules.itdae.api.routes_itdae import router as itdae_router
from app.modules.sais.api.routes_sais import router as sais_router
from app.api.v1.pilot import router as pilot_router

# ITDAE integration
from app.modules.auth.api.routes_auth import router as auth_router

# NATO interoperability (GAP-04)
from app.modules.interop.router import router as interop_router
# Sanctions screening (GAP-09)
from app.modules.sanctions.router import router as sanctions_router
# Intelligence products (GAP-11)
from app.modules.intel.router import router as intel_router
# Multi-national sharing (GAP-12)
from app.modules.sharing.router import router as sharing_router
# AI Analyst assistant (Featherless AI)
from app.modules.analyst.router import router as analyst_router
# Geodata: EEZ, weather, bathymetry
from app.services.geodata.router import router as geodata_router
from prometheus_fastapi_instrumentator import Instrumentator

configure_logging()

_startup_log = logging.getLogger("aegisais.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ws_manager.set_main_event_loop(asyncio.get_running_loop())
    try:
        try:
            from app.core.database import SessionLocal
            from app.modules.itdae.geofences.seed import seed_baltic_geofence_zones

            db = SessionLocal()
            try:
                seed_baltic_geofence_zones(db)
            except Exception as e:
                _startup_log.warning("ITDAE Baltic geofence seed failed: %s", e)
            finally:
                db.close()
        except Exception as e:
            _startup_log.warning("ITDAE startup initialization failed: %s", e)
        yield
    finally:
        ws_manager.set_main_event_loop(None)


app = FastAPI(title="AegisAIS", lifespan=lifespan)

# Instrument App
Instrumentator().instrument(app).expose(app)

# Middleware: CORS outermost (added last), security headers inner (IMPLEMENTATION_PLAN Sprint 1)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/v1/auth", tags=["auth"])
app.include_router(vessels_router, prefix="/v1", tags=["vessels"])
app.include_router(alerts_router, prefix="/v1", tags=["alerts"])
app.include_router(tracks_router, prefix="/v1", tags=["replay"])
app.include_router(ws_router, prefix="/v1", tags=["stream"])
app.include_router(upload_router, prefix="/v1", tags=["upload"])
app.include_router(health_router, prefix="/v1", tags=["health"])
app.include_router(audit_router, prefix="/v1", tags=["audit"])
app.include_router(watchlist_router, prefix="/v1", tags=["watchlist"])
app.include_router(reports_router, prefix="/v1", tags=["reports"])
app.include_router(incidents_router, prefix="/v1", tags=["incidents"])
app.include_router(itdae_router, prefix="/api/v1/itdae", tags=["itdae"])
app.include_router(sais_router, prefix="/v1/sais", tags=["sais"])
app.include_router(pilot_router, prefix="/v1", tags=["pilot"])
app.include_router(interop_router, prefix="/v1/interop", tags=["interop"])
app.include_router(sanctions_router, prefix="/v1/sanctions", tags=["sanctions"])
app.include_router(intel_router, prefix="/v1/intel", tags=["intel"])
app.include_router(sharing_router, prefix="/v1/sharing", tags=["sharing"])
app.include_router(analyst_router, prefix="/v1/analyst", tags=["analyst"])
app.include_router(geodata_router, prefix="/v1/geodata", tags=["geodata"])

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
