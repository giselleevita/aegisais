# Nginx TLS reverse proxy

Place TLS material in `certs/` next to this directory (see `certs/.gitkeep`):

- `cert.pem` — certificate (PEM)
- `key.pem` — private key (PEM)

Docker Compose mounts `infra/docker/nginx/certs` read-only at `/etc/nginx/certs` inside the container.

For local development, `scripts/start_full_stack.sh` will generate these files automatically if they are missing.

## Self-signed certificate (development)

```bash
cd infra/docker/nginx/certs
openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout key.pem \
  -out cert.pem \
  -days 365 \
  -subj "/CN=localhost"
```

Browsers will warn about the untrusted issuer; that is expected for local dev.

## Let's Encrypt (staging / production)

Use a real hostname with DNS pointing at your server. Typical options:

1. **Certbot on the host**, then copy or symlink `fullchain.pem` → `cert.pem` and `privkey.pem` → `key.pem` into `certs/`, or mount the live directory from `/etc/letsencrypt/live/<domain>/`.
2. **Certbot with the nginx container** — run Certbot in a one-off container or sidecar with the webroot or DNS challenge plugin, then reload nginx after renewal (`docker compose exec nginx nginx -s reload`).

Keep private keys out of version control; only `certs/.gitkeep` is tracked.
