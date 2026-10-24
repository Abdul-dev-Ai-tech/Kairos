# KAIROS STORE

A connected Django watch store with an ivory/charcoal storefront, a branded OTP-protected admin, PostgreSQL configuration, guest/customer bags, offline payments, order snapshots and editable merchandising. Default currency: PKR. Tagline: “Every Second, Your Style.”

The supplied source is editable. The supplied contact phone is 03157292819 and Instagram is https://www.instagram.com/2.kairos.store/. Delivery is Lahore-only. No real logo, verified product catalogue, bank account, courier contract, domain or SMTP/Meta credentials were supplied. The included photographs are generated conceptual assets, the 12 seeded watches are clearly marked demonstrations, and the policies/shipping rates need business review before sales. There is no pre-created administrator or shared default password.

## Quick start — Docker (Windows, macOS or Linux)

Install Docker Desktop / Docker Engine with Compose. Run all commands from the extracted `kairos-store` directory. On Windows, use PowerShell.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py bootstrap_store
docker compose exec web python manage.py setup_roles
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py create_admin --email your-email@example.com
```

On Linux/macOS use `cp .env.example .env` for the first command. Website: http://127.0.0.1:8000/ · Admin: http://127.0.0.1:8000/admin/.

The owner command prompts for a password of at least 12 characters; typing is hidden. First admin access requires authenticator enrollment. Scan the QR code using an authenticator app, enter its current code, and save the one-time recovery codes from **Two-factor settings → Backup tokens** somewhere private. Subsequent staff logins require the password and a valid OTP. Device clocks must be correct.

`seed_demo` is optional and never overwrites existing products. Without it, `bootstrap_store` supplies empty collections, editable pages, COD and a demonstration delivery zone. Bank transfer starts disabled. Demo coupon: `KAIROS10`, 10% off orders from PKR 5,000, up to 100 redemptions, expires 30 days after seeding. Cancelled orders do not recycle coupon usage.

Database and uploaded media use persistent Docker volumes. Use `docker compose stop` / `docker compose start` to pause/resume. Do not remove volumes if you want to retain the store. The Docker image already includes compiled CSS, local fonts and JavaScript; Node is unnecessary for normal startup. This Compose file is for local development, not an Internet-facing deployment.

## Alternative Windows PowerShell setup

Requirements: Python 3.12, PostgreSQL 17 (or a compatible supported PostgreSQL version), and optionally Node 20+ for editing Tailwind. The application pins Django 5.2.18 LTS and all Python dependencies in `requirements.lock`; `requirements.txt` contains the same pins. JavaScript asset build dependencies are pinned in `package-lock.json`.

1. Create a PostgreSQL login and database. Open SQL Shell (`psql`) as your PostgreSQL administrator. Enter your PostgreSQL admin password at the prompt:

```sql
CREATE USER kairos WITH PASSWORD 'replace-with-your-own-local-password';
CREATE DATABASE kairos OWNER kairos;
```

2. Open the extracted project in VS Code. In its PowerShell terminal:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
Copy-Item .env.example .env
notepad .env
```

Set `DATABASE_URL=postgresql://kairos:YOUR_PASSWORD@127.0.0.1:5432/kairos`. URL-encode special characters in the password (for example `@` as `%40`). Use a simple local password during setup if URL encoding is unfamiliar. Do not share `.env`.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py bootstrap_store
.\.venv\Scripts\python.exe manage.py setup_roles
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py create_admin --email your-email@example.com
.\.venv\Scripts\python.exe manage.py runserver
```

Open http://127.0.0.1:8000/. These explicit Python commands do not require activating a venv or changing PowerShell's execution policy. Port 8000 occupied? Use `manage.py runserver 8001` and update `SITE_URL` and `CSRF_TRUSTED_ORIGINS` in `.env` accordingly.

For Linux/macOS: `python3 -m venv .venv`, then substitute `.venv/bin/python` for the Windows interpreter above. Start PostgreSQL separately, or use `docker compose up -d db` with your host Python environment.

## Daily store management

Read `START-HERE-ROMAN-URDU.md` for a simple walkthrough.

- **Product:** Admin → Catalog → Products → Add. Enter the identity, collection, description and price. In **Variants**, enter at least one active finish with its unique SKU and stock. A product's stock shown in the listing is the sum of its active variants. Base prices are inherited unless a variant overrides them. A variant's own regular price does not inherit a product sale price. Set a lower variant sale price explicitly when needed.
- **Photos:** Add multiple rows in **Product images**. Each row has an upload, descriptive alt text, optional variant association and a numeric display position. Lower positions appear first. Save once before linking an image to a newly created variant; existing variants appear in that product's image dropdown. Unassigned photos appear for all variants. Replace image files or change positions in the form to rearrange. Allowed JPG/PNG/WebP, at most 5 MB, 6000 px / 20 MP. Product uploads become sanitized WebP with 480/960/1600 px versions; logos/favicons become PNG for email/browser compatibility. Camera metadata is removed. If stock changed while an admin form was open, the form asks you to reload rather than overwriting sold inventory.
- **Publish:** Select Published and save. The shared card automatically appears in its collection, search and Shop All. Check Featured/New Arrival for homepage sections. Sale badges follow a real configured sale price. Draft/Archived products disappear immediately; checkout rechecks publication and stock. Use archive/inactive states for purchased products and variants rather than deleting them.
- **Specifications:** Add label/value rows with verified product facts. The storefront does not hard-code any brand, authenticity, warranty or material promises. Demonstration fields deliberately contain the word demo.
- **Logo:** Core → Store settings → Logo. Upload your real transparent PNG or WebP. Its proportions are preserved on storefront, welcome screen, admin, emails and order document. Upload an optional favicon; otherwise the same logo is used. The original editable fallback mark is in `templates/core/logo.html` and `static/images/favicon.svg`.
- **Home:** Core → Banners controls secondary campaigns, image/text/link and order. The primary cinematic hero, its heading/copy/image and both CTAs are editable in Store settings. Collection photos/descriptions are in Collections. The supplied source also lets a designer extend the layout.
- **Contact, WhatsApp and policies:** Core → Store settings and Core → Pages. WhatsApp is international digits only (e.g. `923001234567`); it stays hidden until configured. Bank details are never invented.
- **Shipping:** Orders → Shipping zones. Empty city list covers Pakistan; otherwise one city per line. Set charge, free-shipping threshold and honest delivery estimate. The free-shipping threshold applies after coupon discount. The selected zone must cover the entered city. Country is fixed to Pakistan for this release.
- **Payments:** Orders → Payment methods. COD can be toggled. Enter real bank account instructions before enabling bank transfer. Instructions are snapshotted on orders. Only a user with **verify payment** permission and verified OTP may mark a payment received. Bank orders cannot be confirmed before verification. COD may be marked received after delivery.
- **Orders:** Pending → Confirmed → Processing → Shipped → Delivered. Pending/Confirmed/Processing can instead become Cancelled. A cancellation restocks the reserved variant quantities exactly once. Shipped/delivered orders cannot be cancelled through this workflow; contact the owner for a separate refund/return process. Paid cancellations require a separate manual refund through the actual banking channel. This application does not initiate refunds. Set tracking reference and internal notes in admin.
- **Documents & CSV:** An order's admin page links to its printable order document. Customers can also print their own order document / save it as PDF. It is explicitly an order summary, not a tax invoice or proof of payment. Select orders and use the CSV export action. Spreadsheet formula prefixes are escaped.
- **Team:** `setup_roles` creates Store Staff (catalogue/order operations) and Payment Verifier (view/verify payments). The owner manages users and group assignment. Set **Staff status** for team members and enroll each in OTP. No staff role can edit store identity or grant itself permissions. Owner is a Django superuser. Give a verifier both groups if they also fulfil orders.

## How the application is organised

| Directory | Responsibility |
| --- | --- |
| `config/settings/` | Common, development, production and test settings |
| `catalog/` | Products, variants, galleries, specifications, collections, filters, wishlist |
| `orders/` | Persistent bags, coupons, shipping, transactional checkout, payment adapters, order snapshots, email outbox |
| `accounts/` | Email-based customer registration/login, profile, password reset |
| `core/` | Store branding/content, uploads, OTP admin dashboard, audit trail |
| `templates/` | Server-rendered storefront, account, admin, email and order pages |
| `static/`, `assets/` | Compiled/local assets and Tailwind input |
| `tests/` | Business rules, admin HTTP flows, permission tests and PostgreSQL races |
| `deploy/`, `docs/` | Deployment example, verification, security, licences, backups |

No frontend API token is needed. Django sessions, CSRF forms and server-side validation remain authoritative. JavaScript progressively enhances search, gallery/zoom, wishlist, cart drawer, real operation loading and delivery quotes. Core purchase forms also work without JavaScript. The welcome dial runs once per browser session, has a skip button, auto-finishes quickly and is disabled by reduced-motion preferences. Native animation APIs avoid a GSAP dependency for the few effects used here.

For CSS editing only:

```powershell
npm ci
npm run build:css
```

`static/css/store.css` contains the bespoke luxury layout; `assets/tailwind.css` is the Tailwind entrypoint. Self-hosted fonts need no external network request. The hero concept image is `static/images/hero.webp`; seeds consume replaceable demo photos in `static/demo/`.

## Tests and checks

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test tests --settings=config.settings.test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

The portable test default is an in-memory SQLite database only for fast HTTP/business-rule checks. To run real locking/concurrency tests, use a disposable PostgreSQL database and a test-only role with CREATEDB permission:

```sql
CREATE USER kairos_test WITH PASSWORD 'replace-test-password' CREATEDB;
CREATE DATABASE kairos_test OWNER kairos_test;
```

```powershell
$env:TEST_DATABASE_URL = 'postgresql://kairos_test:replace-test-password@127.0.0.1:5432/kairos_test'
.\.venv\Scripts\python.exe manage.py test tests --settings=config.settings.test
Remove-Item Env:TEST_DATABASE_URL
```

Django creates/destroys `test_kairos_test`. Never point test configuration at a live database or give the production role CREATEDB. `docs/VERIFICATION.md` records the exact completed checks and limits. No claim of penetration testing, online payment processing or production deployment is made.

## Going live

See `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, `docs/BACKUP-RESTORE.md` and `docs/THIRD-PARTY-NOTICES.md`.

For your requested Vercel deployment, follow **docs/VERCEL.md**. The native Django/Python runtime serves both frontend templates and backend; a managed cloud PostgreSQL and permanent S3/R2-compatible media bucket retain data while your laptop is off. `vercel.json`, `pyproject.toml` and `config/settings/vercel.py` are included. The five-minute notification retry Cron is intended for a commercial-capable Vercel plan. No real Vercel account or service credentials have been connected from this environment. The separate shareable static demo does not submit real orders.


## Lahore delivery and automatic notifications (24 October update)

The live backend requires name, email, Pakistani mobile, full delivery address,
Lahore city and area. Landmark, Google Maps share link and a permission-based GPS
pin are available. Non-Lahore submissions are rejected even if a shipping zone is
configured for all cities. Location is private order data, visible to the customer
with order access and authorized staff. Set real delivery charges/ETA in Shipping zones.

A committed order creates durable owner/customer notification rows. On Vercel,
bounded sends happen after commit and authenticated Cron retries eligible failures.
Customer WhatsApp requires explicit order-update opt-in. Owner alerts use the
private notification contact fields in Store settings. Configure Meta-approved
templates, sender/token/webhook and SMTP using **docs/WHATSAPP.md**; automatic
messages cannot work from a contact link alone. No fake confirmation is reported
when a provider is disabled or its credentials are absent.

`preview-demo/` contains the current editable browser-local design demonstration
and its source assets. Its manager changes only that visitor's browser. The real
OTP-protected, database-backed admin is `/admin/` in the Django application.
