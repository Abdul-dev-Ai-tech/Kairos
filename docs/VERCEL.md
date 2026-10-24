# Deploy the complete Kairos application on Vercel

The storefront, checkout, customer accounts, OTP-protected Django admin and webhooks
run as the same native Django Vercel Function. Static CSS/JavaScript/fonts are served
from the Vercel CDN. After deployment, your laptop does not need to stay on.

The PostgreSQL database must be a managed cloud database (for example a Neon
integration installed through Vercel Marketplace). Product media must use a permanent
S3-compatible bucket such as Cloudflare R2 or AWS S3. Vercel's local filesystem is not
an upload database. This package refuses the Vercel settings profile without cloud
media credentials. Sessions, orders, products and notification queues live in PostgreSQL.

## Accounts and plan

Use a Vercel plan that permits your commercial store. Vercel's Hobby plan is for
personal, non-commercial work. The included five-minute retry Cron requires Pro
or an eligible higher plan; Hobby only permits daily cron jobs. No paid service
or plan has been purchased by this project.

Required before launch:

- A Vercel account/project and a connected Git repository or authenticated CLI.
- Managed PostgreSQL connection URL, with TLS and an appropriately limited database user.
- S3/R2 bucket, API access key, secret and endpoint; product-photo files are public storefront assets.
- SMTP credentials and verified sending domain for order/password-reset email.
- Meta WhatsApp Cloud API credentials and approved templates for automated WhatsApp.
- Your actual products, logo, delivery charge and estimated delivery times.

Contact details are already configured: 03157292819 / international 923157292819,
and https://www.instagram.com/2.kairos.store/ . Delivery is restricted to Lahore.

## 1. Import the source

Extract the ZIP. Import the **kairos-store** directory into Git and Vercel. The
project root must contain `manage.py`, `pyproject.toml`, `requirements.txt` and
`vercel.json`. Do not deploy `preview-demo/` as the real shop; it is an isolated
static demonstration without the production backend.

Vercel's native Django framework detection reads `config.wsgi:application` from
`pyproject.toml`. Python 3.12 is pinned in `.python-version`. Leave the Output
Directory and Build Command overrides empty: native Django collection handles
`STATIC_ROOT` / `collectstatic`. No Docker process or `runserver` is used on Vercel.

## 2. Configure production environment variables

Set these under Vercel Project → Settings → Environment Variables, using your
actual deployment domain. Mark credentials sensitive. Do not paste them into chat,
commit them to Git or include them in an uploaded source ZIP.

| Variable | Value / source |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.vercel` |
| `DJANGO_SECRET_KEY` | Random secret of 50+ characters |
| `DJANGO_ALLOWED_HOSTS` | `your-store.vercel.app,your-domain.example` (real hosts only) |
| `SITE_URL` | The canonical `https://` storefront origin |
| `CSRF_TRUSTED_ORIGINS` | Same actual HTTPS origin(s), comma-separated |
| `DATABASE_URL` | Managed PostgreSQL URL with `sslmode=require` |
| `MEDIA_STORAGE` | `s3` |
| `AWS_STORAGE_BUCKET_NAME` | Your product-media bucket |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Bucket-scoped read/write/delete credentials |
| `AWS_S3_ENDPOINT_URL` | Provider HTTPS endpoint; omit for regular AWS S3 |
| `AWS_S3_REGION_NAME` | `auto` for R2, actual AWS region for S3 |
| `AWS_S3_CUSTOM_DOMAIN` | Optional public media/CDN hostname, without scheme |
| `AWS_QUERYSTRING_AUTH` | `false` only for a configured public media/CDN; otherwise `true` |
| `CRON_SECRET` | Separate random secret of 32+ characters |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| SMTP variables / `DEFAULT_FROM_EMAIL` | Your provider's actual values |
| WhatsApp variables | Follow `WHATSAPP.md`; keep disabled until configured |

Generate independent secrets locally:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(64))"
```

Use separate preview and production databases/buckets. Do not attach production
customer records to public preview deployments. Avoid running migrations in every
preview build: release them deliberately once using the management wrapper below.

## 3. Prepare the cloud database once

Install project requirements in a local venv as described in README. Install a
current Vercel CLI with native Django support (50.38.0 or newer; verified docs
reference CLI 59.19.1). From the project root:

```powershell
npx vercel@59.19.1 link
npx vercel@59.19.1 env pull .env.vercel --environment=production
.\.venv\Scripts\python.exe scripts/vercel_manage.py migrate
.\.venv\Scripts\python.exe scripts/vercel_manage.py bootstrap_store
.\.venv\Scripts\python.exe scripts/vercel_manage.py setup_roles
.\.venv\Scripts\python.exe scripts/vercel_manage.py create_admin --email YOUR_EMAIL
```

The wrapper explicitly loads `.env.vercel` and requires `config.settings.vercel`.
It uses your cloud PostgreSQL directly. Administrator password entry is hidden;
no default administrator/password is shipped. Enrol authenticator OTP on first
admin visit and retain recovery codes privately.

Optional demonstration inventory, before any real catalogue is entered:

```powershell
.\.venv\Scripts\python.exe scripts/vercel_manage.py seed_demo
```

This uploads seed images to the configured durable bucket. Keep demonstration
mode enabled for sample products; do not offer conceptual watches as actual stock.
Review **Orders → Shipping zones**: only Lahore is accepted by the backend, even
if a staff-created zone has an empty/all-city list. Set actual charges, free-shipping
threshold and `Delivery estimate`. Existing purchases keep an ETA snapshot.

## 4. Deploy

```powershell
npx vercel@59.19.1 --prod
```

Alternatively deploy the connected repository in the Vercel dashboard. Add your
custom domain there, then update host/CSRF/canonical settings to match and redeploy.
Enable automated cloud database backups and media versioning/lifecycle retention.
Use provider restore tools in addition to the logical backups in BACKUP-RESTORE.md.

## Notifications without an always-running laptop

Vercel uses bounded, synchronous post-commit dispatch for each newly placed order.
The order is already saved before SMTP/Meta calls begin. Failures remain in the
database outbox. The authenticated `/internal/notifications/run/` route is called
by Vercel Cron every five minutes to retry eligible transient failures. Meta
webhooks report sent/delivered/read/failed status. A worker process is not needed
on Vercel. Do not run the endless `run_notification_worker` as a Vercel Function.
Container/Docker users can use that separate worker instead.

A transport timeout has an ambiguous outcome: it is marked `uncertain` and is not
blindly resent. The owner must review Meta delivery logs before manually requeuing,
to reduce duplicate messages. Provider acceptance does not prove delivery.

## Upload limits

Vercel Functions limit request bodies to 4.5 MB. The Vercel Django profile accepts
images of at most 1 MB each, and the admin performs a total-size preflight at
3.8 MB. Upload a few compressed photos, save, then add more. Local/Docker image
limits remain 5 MB. Images are validated again on the server, metadata removed,
renamed and stored as optimized WebP (PNG for logos/favicon). Files never depend
on the local runtime disk for persistence.

## Verification and remaining activation work

The source has been tested locally with isolated synthetic data and mocked Meta
responses. No Vercel account, cloud PostgreSQL/media credentials, SMTP credentials
or Meta tokens were supplied in this conversation. A real Vercel deployment,
cloud upload, live OTP enrollment and live WhatsApp delivery are not claimed.
Complete a real Lahore test order after account connection and verify each outbox
status, both WhatsApp recipients, email, stock and the delivery pin before launch.

Official references consulted on 24 October 2026:

- https://vercel.com/docs/frameworks/full-stack/django
- https://vercel.com/docs/functions/limitations
- https://vercel.com/docs/cron-jobs/usage-and-pricing
- https://vercel.com/docs/plans/hobby
- https://vercel.com/docs/postgres
- https://vercel.com/docs/headers/request-headers
- https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
