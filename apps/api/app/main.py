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
from app.api.v1.import_ais import router as import_ais_router
from app.modules.auth.api.routes_auth import router as auth_router
from prometheus_fastapi_instrumentator import Instrumentator

configure_logging()
_startup_log = logging.getLogger("aegisais.startup")

# --- Optional module imports (fail gracefully so core API stays up) ---
_optional_routers: list = []

def _try_import(label: str, import_fn):
    try:
        router = import_fn()
        _optional_routers.append((label, router))
        _startup_log.info("Module loaded: %s", label)
    except Exception as exc:
        _startup_log.warning("Module '%s' disabled at startup: %s", label, exc)

_try_import("interop",  lambda: __import__("app.modules.interop.router", fromlist=["router"]).router)
_try_import("sanctions", lambda: __import__("app.modules.sanctions.router", fromlist=["router"]).router)
_try_import("intel",    lambda: __import__("app.modules.intel.router", fromlist=["router"]).router)
_try_import("sharing",  lambda: __import__("app.modules.sharing.router", fromlist=["router"]).router)
_try_import("analyst",  lambda: __import__("app.modules.analyst.router", fromlist=["router"]).router)
_try_import("assets",   lambda: __import__("app.modules.assets.router", fromlist=["router"]).router)
_try_import("iot",      lambda: __import__("app.modules.iot.router", fromlist=["router"]).router)
_try_import("geodata",  lambda: __import__("app.services.geodata.router", fromlist=["router"]).router)

_OPTIONAL_PREFIXES = {
    "interop":   "/v1/interop",
    "sanctions": "/v1/sanctions",
    "intel":     "/v1/intel",
    "sharing":   "/v1/sharing",
    "analyst":   "/v1/analyst",
    "assets":    "/v1",
    "iot":       "/v1/iot",
    "geodata":   "/v1/geodata",
}


def _init_sentry_stub() -> None:
    if not settings.sentry_dsn:
        _startup_log.info("Sentry disabled (SENTRY_DSN not configured)")
        return
    try:
        import sentry_sdk  # type: ignore[import-not-found]
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.05)
        _startup_log.info("Sentry initialized")
    except Exception as exc:
        _startup_log.warning("Sentry initialization skipped: %s", exc)


_init_sentry_stub()


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

Instrumentator().instrument(app).expose(app)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

# Core routers — must always load
app.include_router(auth_router,       prefix="/v1/auth",      tags=["auth"])
app.include_router(vessels_router,    prefix="/v1",           tags=["vessels"])
app.include_router(alerts_router,     prefix="/v1",           tags=["alerts"])
app.include_router(tracks_router,     prefix="/v1",           tags=["replay"])
app.include_router(ws_router,         prefix="/v1",           tags=["stream"])
app.include_router(upload_router,     prefix="/v1",           tags=["upload"])
app.include_router(health_router,     prefix="/v1",           tags=["health"])
app.include_router(audit_router,      prefix="/v1",           tags=["audit"])
app.include_router(watchlist_router,  prefix="/v1",           tags=["watchlist"])
app.include_router(reports_router,    prefix="/v1",           tags=["reports"])
app.include_router(incidents_router,  prefix="/v1",           tags=["incidents"])
app.include_router(itdae_router,      prefix="/api/v1/itdae", tags=["itdae"])
app.include_router(sais_router,       prefix="/v1/sais",      tags=["sais"])
app.include_router(pilot_router,      prefix="/v1",           tags=["pilot"])
app.include_router(import_ais_router, prefix="/v1",           tags=["import"])

# Optional routers — loaded only if their module imported successfully
for label, router in _optional_routers:
    app.include_router(router, prefix=_OPTIONAL_PREFIXES[label], tags=[label])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AegisAIS",
        "version": "0.1.0",
        "description": "AIS Data Integrity and Anomaly Detection Tool",
        "docs": "/docs",
        "health": "/v1/health",
        "modules": [label for label, _ in _optional_routers],
    }
