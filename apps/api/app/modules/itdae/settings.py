from app.core.config import settings

# Export configurations that this module needs, leveraging the global app settings
ITDAE_AIS_API_KEY = getattr(settings, "ITDAE_AIS_API_KEY", "")
ITDAE_BALTIC_BBOX = getattr(settings, "ITDAE_BALTIC_BBOX", "")
