# Vercel deployment option

For the requested Vercel hosting, use **VERCEL.md**. It includes native Django runtime, cloud PostgreSQL, durable media, notification dispatch and protected Cron. The container instructions below remain an alternative.

# Deployment

Target: a Python 3.12 host with PostgreSQL 17+, HTTPS, writable persistent media, and a scheduler for the email outbox. Build assets are already included. `compose.yaml` is local development configuration; it deliberately binds ports to localhost and uses development settings.

## Required configuration

Set secrets in your hosting provider's secret manager or a permission-restricted `.env`, never source control. Generate a secret locally with `python -c "import secrets; print(secrets.token_urlsafe(64))"` and place the output in the environment.

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<a unique random value, at least 50 characters>
DJANGO_ALLOWED_HOSTS=your-store-domain.example
CSRF_TRUSTED_ORIGINS=https://your-store-domain.example
SITE_URL=https://your-store-domain.example
DATABASE_URL=postgresql://<user>:<url-encoded-password>@<db-host>:5432/<database>?sslmode=require
MEDIA_ROOT=/srv/kairos/media
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=KAIROS STORE <orders@your-store-domain.example>
EMAIL_HOST=<smtp-host>
EMAIL_PORT=587
EMAIL_HOST_USER=<smtp-user>
EMAIL_HOST_PASSWORD=<smtp-secret>
EMAIL_USE_TLS=true
TRUST_PROXY_HEADERS=true
```

`TRUST_PROXY_HEADERS=true` is appropriate only when the backend is reachable solely through your trusted proxy and that proxy overwrites incoming forwarded headers. Otherwise leave it false. With the supplied single-proxy Nginx configuration, forwarded client IPs can be trusted for Axes only after configuring the callable described in SECURITY.md. Do not blindly enable arbitrary forwarded-header trust.

Install the locked requirements, then run with the production environment selected:

```bash
python manage.py migrate
python manage.py bootstrap_store
python manage.py setup_roles
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level WARNING
python manage.py create_admin --email owner@your-store-domain.example
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 45 --access-logfile - --error-logfile -
```

`bootstrap_store` creates draft policies and a demo shipping zone. Replace them in admin before accepting sales. Do not run `seed_demo` on a real catalogue. The production settings refuse a placeholder secret, HTTP SITE_URL, absent trusted CSRF origins, or a non-PostgreSQL database. HSTS with subdomains/preload is enabled; use it only on a domain whose relevant subdomains support HTTPS.

Run migrations as a release step, once per deployment; do not have every Gunicorn worker run them. Use a non-root application user and a PostgreSQL role with only application database privileges. The production role does not need CREATEDB or superuser privileges. Keep database access private. Restrict the backend port to the reverse proxy.

## Static and media

WhiteNoise serves versioned compressed static assets after `collectstatic`. Alternatively use `deploy/nginx.conf.example` to serve `STATIC_ROOT` and `MEDIA_ROOT`. Replace paths/domain and configure your real TLS certificate. The example does not issue certificates for you.

Media is mutable data: use a persistent filesystem volume with backups. Django's development media serving is intentionally disabled in production; Nginx or your media service must serve `/media/`. Uploads contain only validated/re-encoded JPG/PNG/WebP inputs saved as WebP (branding as PNG). Never execute files from media. A separately hosted media domain is a further hardening option; configure a Django storage backend and adjust CSP/media URLs as appropriate. S3/object-storage credentials and a storage integration have not been provisioned.

Use CDN/static caches for immutable hashed static assets. Avoid caching account/order/checkout/cart HTML or CSRF-bearing pages in a public shared cache. Product queries prefetch images and variants, and browse pages are paginated.

## Email and operations

Verify your sending domain and configure SPF/DKIM/DMARC with your email provider. Test password reset and a complete order to a mailbox you control. Development uses console email; delivery to a real inbox has not been verified here.

Schedule `python manage.py retry_order_emails` externally every few minutes. The outbox stores pending/sent state and errors; each normal retry avoids sending an already-marked-sent order. SMTP does not provide an atomic transaction with the database: a crash after provider acceptance but before marking sent may cause a duplicate email. Consider a provider idempotency key if you add an email API. A failed email never rolls back a committed purchase.

Monitor application errors, database health/disk, email failures, Axes lockouts and stale pending orders. Check banking records before marking transfers paid. Inventory is reserved on order creation and released only on supported cancellation. Review unpaid/abandoned orders regularly; automatic payment expiry/cancellation is not included. Paid cancellations/refunds and return logistics remain manual business operations. Do not delete historical orders.

## Payments extension

`orders/payments.py` defines a small provider boundary. COD and manual bank transfer are implemented. Online payment accounts, gateways, card collection, signed webhook handlers and automatic refunds are not implemented or advertised to shoppers. Add a provider only with verified webhook signatures, unique event IDs, amount/currency/order matching, durable webhook storage and tests. A success redirect alone must never mark an order paid.

## Release acceptance

Run the full tests against disposable PostgreSQL, including the two concurrency races. Exercise real admin uploads, OTP enrollment/recovery, mobile/touch and keyboard purchase flows, courier zones, email delivery, HTTPS cookies, backups and a restore. Review final business/policy content and replace all demo listings. This project has not undergone an independent penetration test or live load test. See VERIFICATION.md for what was actually executed.
