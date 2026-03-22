"""SAIS configuration sourced from :class:`app.core.config.Settings`."""

from app.core.config import settings


def get_sais_provider() -> str:
    return settings.SAIS_PROVIDER


def get_sais_api_key() -> str:
    return settings.SAIS_API_KEY


def get_sais_api_base_url() -> str:
    return settings.SAIS_API_BASE_URL
