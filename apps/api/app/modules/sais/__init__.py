"""
Satellite AIS (S-AIS) integration — Sprint 4 Task 4.2 stub.

**README (snippet)**

- Configure via environment: ``SAIS_PROVIDER`` (``spire`` | ``orbcomm`` | ``exactearth`` | ``none``),
  optional ``SAIS_API_KEY`` and ``SAIS_API_BASE_URL`` for the chosen provider.
- Until credentials are configured, the API uses ``StubSatelliteAISClient`` (no outbound HTTP).
- Authenticated endpoints: ``GET /v1/sais/health`` and ``GET /v1/sais/status`` (analyst or admin).

See ``app.modules.sais.client`` for the client abstraction and ``app.modules.sais.api.routes_sais`` for routes.
"""
