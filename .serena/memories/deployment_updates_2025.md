# Deployment updates (2025)
- Web server: Gunicorn + uvicorn worker (`gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4 --timeout 120 --access-logfile -`).
- Static files: WhiteNoise enabled (`whitenoise.middleware.WhiteNoiseMiddleware`, `CompressedManifestStaticFilesStorage`).
- Networking: base `docker-compose.yml` publishes no ports; `web`/`flower` join shared `app-network` (for NPM) and internal network; `db`/`redis` are internal-only.
- Local dev: use `docker-compose.override.yml` to publish ports (web `18001:8000`, db `15433:5432`, redis `16380:6379`, flower `15555:5555`) and set `DEBUG=True`.
- Shared network: `app-network` is external; create if missing with `docker network create app-network` (reused by gateway/NPM and sibling apps).
- Domain: production host `blog-automation.ai-beauty.tokyo`; set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` accordingly.
