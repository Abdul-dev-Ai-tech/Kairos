# KAIROS STORE — interactive storefront and manager demo

A shareable, static demonstration of the luxury Kairos watch store, with an editable
browser-local manager. This is separate from the runnable Django/PostgreSQL source
ZIP supplied earlier. No real customer accounts, payments or orders are connected.

## Try the manager

Open `/preview-admin/` (or `/admin/`). No login is required because every visitor
has an isolated, local demo catalogue. Nothing edits a shared production database.

- Add, edit, publish, archive and delete watches.
- Set regular/sale prices; edit variant SKUs, prices, finishes and inventory.
- Upload JPG/PNG/WebP photographs, choose variant photographs and reorder images.
- Create, rename and delete categories, with reassignment for existing products.
- Edit logo, tagline, announcement, hero text, WhatsApp and Instagram settings.
- Complete a sample checkout, inspect its order, update status, export sample CSV.
- Restore the original demonstration through Settings → Reset demo.

Changes and compressed uploaded pictures are stored in this browser's localStorage.
Clearing browser data resets them. Other visitors see their own version. Do not
use this public demo as a production admin or enter sensitive customer information.
Business contacts are configured as supplied: WhatsApp 923157292819 and Instagram
https://www.instagram.com/2.kairos.store/. Delivery wording is Lahore-only. The demo
still sends no real order, payment, email or WhatsApp notification.

## Source

`dist/` is the published application. No installation/build is needed. Serve this
folder with any static HTTP server. Same-origin navigation renders preloaded page
shells instantly and preserves keyboard navigation, back/forward and shareable filters.

- `static/js/demo-store.js`: validated demo persistence and compressed image handling.
- `static/js/admin-ui.js`: traditional product/category/settings/order manager.
- `static/js/demo-ui.js`: routing, storefront, filters, variants, wishlist, bag, checkout.
- `static/js/demo-pages.js`: cached informational page shells.
- `static/js/demo-catalog.js`: replaceable demonstration seed inventory.
- `static/css/luxury.css`, `static/css/admin.css`: editable visual design.

The original `scripts/export_demo.py` captures server-rendered Django demo templates.
The prepared application assets above include subsequent custom development; keep
them when re-exporting. `scripts/upgrade_demo.py` records the initial conversion.

## Verification

Run `node scripts/test_demo_store.cjs` for product/category CRUD, stock and price
validation, publishing, category reassignment, social validation, sample orders and
reset. Run `node --check` on the edited JavaScript files for syntax checks.

Browser QA verified the admin dashboard and editor, saving a price/category/stock/
cover-order change into the storefront, variant availability, cart drawer, sample
checkout confirmation, homepage, navigation, and the category-creation form.
The first browser file-upload automation timed out and the preview environment
restarted. Image-upload code is present, but that upload was not verified end to end.
No cross-device synchronisation, real payment, authentication or production backend
is claimed for this static demo. The Django application implements those server rules.

## Assets and licences

Original Kairos demonstration SVG marks and generated concept-watch imagery from
the source project. Manrope and Cormorant Garamond fonts are OFL licensed; their
notices are included under `static/fonts/`. Product facts, stock and prices are
illustrative and must be replaced with verified business data before real sales.
