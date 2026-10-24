# Verification record — updated 24 October 2026

This records checks actually executed for this source handover. It is not a production certification or independent security audit.

## Automated results

**74 tests discovered: 72 passed, 2 deliberately skipped.** Executed with Python 3.12.14, Django 5.2.18 and the pinned requirements. Fast tests used Django's isolated in-memory SQLite test database. No customer or real banking records were used.

Command:

```text
python manage.py test tests --settings=config.settings.test
```

| Flow / rule | Executed result |
| --- | --- |
| Admin adds a published product, uploads an image, creates a variant | Passed via the real Django admin HTTP form with OTP-verified session |
| Admin changes price, collection, image and stock; storefront reflects changes | Passed |
| Publishing without an active variant | Rejected as expected |
| Stale admin inventory form after stock was sold | Rejected; cannot silently restore sold stock |
| Guest and customer carts, guest merge at login, cross-session cart removal | Passed |
| Variant checkout and purchased-name/SKU/quantity/price snapshots | Passed |
| Browser-posted fake prices/totals | Ignored; server total used |
| Unavailable quantity, unpublished product, inactive payment method, wrong city | Rejected |
| Duplicate checkout POST / checkout-key reuse across carts | Same order returned / cross-cart reuse rejected |
| Valid, invalid, expired, exhausted and minimum-value coupons | Passed / rejected as appropriate; currency rounding checked |
| Bank pending state, verification permission and confirmation ordering | Passed |
| Invalid fulfilment transitions and premature COD paid status | Rejected |
| Supported cancellation restores stock only once | Passed |
| Owner-only customer order/receipt access; signed guest link scope | Passed |
| Real TOTP authentication wizard challenge and token verification | Passed with a test-only TOTP device |
| Password-only staff login, normal customer and anonymous admin attempts | Denied admin access |
| Staff role restrictions, order status admin update, CSV export | Passed |
| Customer registration, password hashing configuration, reset email and one-use reset token | Passed (test suite uses a fast test-only password hasher) |
| Order confirmation rendering, failed-email outbox and retry idempotency | Passed with local test email backend |
| Editable hero and PNG logo proportions/reuse in storefront and email | Passed |
| CSRF enforcement, login lockout after five failures, template/JSON escaping | Passed |
| Upload extension/content/size validation and CSV formula prefixes | Passed |
| Last unit purchased concurrently by two carts (PostgreSQL only) | **Skipped: PostgreSQL unavailable** |
| Concurrent use of a single-use coupon (PostgreSQL only) | **Skipped: PostgreSQL unavailable** |

Additional completed checks:

- `python manage.py check`: no issues.
- `python manage.py makemigrations --check --dry-run`: no changes detected; migrations included.
- Migrations applied and 12 demonstration watches seeded in a disposable local SQLite QA database; all six sample product photos are included for fresh seeding.
- The completed ZIP was extracted into a fresh folder. Migrations, seeding twice without duplicates, 12 watches / 24 variants / 24 images, stored image derivatives and nine representative HTTP routes passed there.
- Production-settings `check --deploy --fail-level WARNING`: no issues with synthetic production-shaped environment values. This checks configuration, not a real HTTPS host or a live database connection.
- `collectstatic --noinput` completed, including hashed/compressed assets. Generated output is reproducible and omitted from the ZIP.
- `node --check static/js/store.js`: passed.
- `npm run build:css`: passed. Tailwind's Browserslist age advisory does not stop the build.

## Browser/visual review

The managed browser supervisor could serve static assets but could not import the project's Django dependencies in its isolated Python runtime. Therefore browser review used **rendered snapshots of the actual Django templates and data**, with the same CSS/JavaScript/assets, through the supported preview server. Those snapshots were internal QA only and are not a substitute backend or included as the runnable application.

Inspected the desktop home/collection/product layouts and a 390px-wide embedded mobile viewport. Verified mobile menu expansion and keyboard Escape dismissal, product variant image/price/SKU/URL changes, gallery zoom dialog opening/closing, and readable desktop/mobile layout. Backend mutations were verified through Django's real HTTP test client, not end-to-end browser network checkout. A real touch-device test, tablet device test and formal screen-reader audit were not performed.

## Remaining verification limits

- PostgreSQL could not be started with the container's process/user restrictions; Docker was unavailable. The two PostgreSQL-specific row-lock races must run on the user's disposable PostgreSQL instance using README instructions. SQLite results must not be presented as proof of concurrency behaviour.
- Docker Compose startup, Windows installation, PostgreSQL dump/restore, real SMTP delivery and production deployment have not been executed here. Their configuration/instructions are provided.
- No real logo, products, stock, courier account, bank details, domain, SMTP credentials or payment-provider credentials were supplied. Demo data/policies/charges must be replaced. Bank transfer remains disabled until configured.
- Online card payments, signed provider webhooks, automatic refunds, tax-invoice generation and automatic expiry of unpaid orders are outside the implemented offline-payment scope.
- No live load test, independent penetration test or claim of vulnerability-free security is made. Review production settings, trusted-proxy IP handling, dependencies and business content before launch.


## 24 October: Lahore, WhatsApp, cloud storage and Vercel update

Added 22 passing tests for Pakistani mobile normalization, required address/area/
email, Lahore-only city validation even with an all-city zone, paired coordinates/
service bounds, safe Google Maps URLs, consent/ETA/location snapshots, unique order
alerts on duplicate checkout, owner email, fixed HTTPS Meta template requests,
disabled-provider behaviour, uncertain-outcome handling, transient backoff, signed
webhook verification and monotonic receipt state, protected Cron, geolocation policy,
Vercel client-IP extraction, post-commit inline notification dispatch, and preserving orders when the owner notification number is misconfigured.

All Meta calls in tests are mocked and email uses Django’s in-memory backend.
The Vercel production profile passed `check --deploy` with synthetic environment
values, PostgreSQL TLS/short-lived connections and S3 storage selected. No external
provider request was made in that configuration check. Dependencies passed `pip check`.
The original PostgreSQL-only races remain skipped; SQLite does not verify row-lock
behaviour under concurrent PostgreSQL traffic. New notification concurrency claims
are limited to the implemented database uniqueness/locking rules and sequential tests.

Actual Vercel deployment/build, cloud PostgreSQL, bucket writes, SMTP delivery and
Meta template approval/live delivery were not run: no accounts/credentials were
provided. The shareable static demo remains a browser-local preview. It now has the
supplied phone/Instagram and Lahore-only sample delivery wording; it collects no
real customer PII and sends no real notifications. The earlier automated photo-upload
browser test timed out; no successful end-to-end cloud photo upload is claimed.

## Windows installation correction — 24 October 2026

Removed the unused `pgserver==0.1.4` development-helper dependency from both requirements files after a Windows/Python 3.14.7 install could not resolve it. Application code does not import or use pgserver. The application continues to use a separately configured PostgreSQL server through psycopg. Both requirements files match and the updated ZIP integrity/manifest were checked. A native Windows/Python 3.14.7 installation has not been executed in this environment; the earlier runtime test results remain specific to Python 3.12.

## Store Manager admin redesign — 24 October 2026

77 tests discovered: 75 passed, 2 PostgreSQL-only concurrency checks skipped. New dashboard checks verify seven-day counts, delivered-only revenue, permission-aware navigation and restricted order visibility, and preserved native product form/inline controls. Existing admin product create/edit/image upload and OTP checks pass. The interface has an original charcoal sidebar, light readable content, local SVG icons/fonts, mobile navigation, inventory alerts and product photography. No schema migration or new dependency is required. See ADMIN-PANEL.md for update instructions and visual QA limitations.
