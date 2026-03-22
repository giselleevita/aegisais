# Grafana (Docker)

Grafana is provisioned automatically with a **Prometheus** datasource (`http://prometheus:9090`) and the **AegisAIS API & Workers** dashboard under **Dashboards**.

## Open Grafana

With the stack running from this directory:

```bash
docker compose up -d grafana
```

In a browser, open **http://localhost:3000**.

## Login

- **Username:** `admin`
- **Password:** value of `GF_SECURITY_ADMIN_PASSWORD` (defaults to **`admin`** if unset)

Set a non-default password when starting Compose, for example:

```bash
GF_SECURITY_ADMIN_PASSWORD='your-secret' docker compose up -d grafana
```

## Files

| Path | Purpose |
|------|---------|
| `provisioning/datasources/datasource.yml` | Prometheus datasource (`uid: prometheus`) |
| `provisioning/dashboards/dashboard.yml` | Load JSON dashboards from `dashboards/` |
| `dashboards/aegisais-api-workers.json` | Minimal panels: scrape `up`, API request rate, worker stream lag |

After editing provisioned files, restart Grafana so it reloads configuration:

```bash
docker compose restart grafana
```
