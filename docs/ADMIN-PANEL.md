# KAIROS Store Manager — admin update

The Django admin now has a charcoal sidebar, a clear Add product action, real order statistics, a seven-day order chart, recent orders, stock alerts and product photography. Product lists show the SKU, effective variant price, inventory, publishing status and an Edit action. Native Django search, filters, pagination, validation, permissions, inline forms and CSRF remain in use.

The chart counts all orders received in the seven displayed calendar days, including cancelled orders. Delivered sales is the lifetime sum of orders whose current status is Delivered. The low-stock number counts active variants on published products at or below the threshold in Store settings. Statistics and navigation respect the signed-in staff member's existing permissions.

## Existing Windows installation — Roman Urdu

1. Chalta hua Django server Ctrl+C se band karo.
2. KAIROS-ADMIN-UPDATE.zip ko Downloads mein save karo.
3. VS Code terminal mein us project folder ko kholo jahan manage.py hai.
4. Neeche har command ko ek ek karke chalao:

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\KAIROS-ADMIN-UPDATE.zip" -DestinationPath "$env:TEMP\kairos-admin-update" -Force
.\.venv\Scripts\python.exe "$env:TEMP\kairos-admin-update\apply_admin_update.py" --project .
.\.venv\Scripts\python.exe manage.py runserver
```

5. Browser mein http://127.0.0.1:8000/admin/ kholo aur Ctrl+F5 dabao.

Installer sirf listed admin code, templates, assets, documentation aur tests replace karta hai. Existing files ki backup copy project ke saath kairos-store-admin-backups/<timestamp>/ mein banti hai. Is update ke liye database migration, dobara seed, ya naya administrator banane ki zaroorat nahi.

If your download is renamed with a suffix such as (1), use the actual downloaded ZIP filename in the first command.

## Managing products

- Products → Add product: enter a name, unique SKU, collection, category, description and price.
- Variants & stock: add at least one active variant with its own unique SKU and available quantity. A blank variant price inherits the product price.
- Images: choose a photograph, write useful alt text and set its position. Lower position numbers appear first. Add another Product image for more photos.
- Select Published when ready; Save. The product uses the existing storefront card automatically.
- Open a product to change its price, images, stock or collection.
- Product list bulk actions can publish, unpublish or archive selected products.
- Permanent product deletion remains owner-only and is blocked for products with purchased variants. Archive an ordered product to retain its purchase history.

## Other controls

Sidebar → Categories / Collections / Brands manages your catalog structure. Store settings contains branding, contact details, WhatsApp and Instagram information. Banners and Pages & policies manage storefront content. Orders contains customer/delivery snapshots and authorized status actions. Discounts, shipping and payment methods have their own sections. More tools keeps the existing notification and security records available to authorized staff.

## Production static files

For a conventional server release, run python manage.py collectstatic --noinput with your production settings. Vercel handles static collection during its configured deployment. Deploy the updated source for the production site to use this design.

## Verification

77 backend tests: 75 passed, two PostgreSQL concurrency tests skipped in the SQLite test environment. Added checks cover permission-limited dashboard navigation, absence of unauthorized order information, seven-day chart counts, delivered-sales calculation, and native admin form/inline rendering. Existing product create/edit/upload, inventory and OTP tests passed. Django checks, migration drift check and JavaScript syntax check passed.

Desktop dashboard, product list and editor were visually inspected using actual Django-rendered HTML snapshots with synthetic data. A 390px iframe was used to inspect the responsive layout and drawer. These browser snapshots are visual QA, not a live browser-to-database CRUD test. The isolated preview service cannot run the project's Python runtime, so live backend browser submission was not verified here. Native Windows/Python 3.14 and production deployment were not executed.
