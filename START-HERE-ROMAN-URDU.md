# KAIROS STORE — asaan setup aur admin guide

Abdul, is folder mein poora editable Django project hai. Products, login, cart, checkout aur orders backend se connected hain. Default database PostgreSQL hai. Apna asli logo aur products abhi replace karne hain.

## 1. Sab se asaan tareeqa: Docker

Apne laptop par Docker Desktop install aur open karo. ZIP extract karo. `kairos-store` folder VS Code mein kholo, phir terminal mein PowerShell select karo.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py bootstrap_store
docker compose exec web python manage.py setup_roles
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py create_admin --email apna-email@example.com
```

`apna-email@example.com` ki jagah apni email likhna. Password jab type karo ge to screen par kuch nazar nahi aaye ga; yeh normal hai. Password kam az kam 12 characters ka rakho. Dobara bhi wohi password likhna.

Website: **http://127.0.0.1:8000/**

Admin: **http://127.0.0.1:8000/admin/**

`seed_demo` se 12 example watches aur pictures aa jati hain. Yeh real stock nahi hai. Example coupon `KAIROS10` hai: 5,000 se upar order par 10%, seeding ke baad 30 din tak.

## 2. PostgreSQL kahan connect hai?

Docker wala tareeqa use karo ge to PostgreSQL khud separate container mein chale ga. Application us se connect ho jati hai; tumhein MySQL install karne ki zarurat nahi.

Agar Docker use nahi karna to PostgreSQL install karo, phir pgAdmin ya SQL Shell mein database banao:

```sql
CREATE USER kairos WITH PASSWORD 'apna-local-password';
CREATE DATABASE kairos OWNER kairos;
```

`.env.example` ki copy `.env` bana kar is line ko apne password ke mutabiq change karo:

```text
DATABASE_URL=postgresql://kairos:apna-local-password@127.0.0.1:5432/kairos
```

Windows ke Python wale exact commands `README.md` mein **Alternative Windows PowerShell setup** ke neeche hain. `.venv\Scripts\python.exe` commands use karne se activation ka issue bhi nahi aata. `.env` kisi ko mat bhejna.

## 3. Admin mein pehli dafa login

1. `/admin/` kholo aur owner email/password likho.
2. Pehli dafa authenticator setup karna hoga. Phone ke Google Authenticator, Microsoft Authenticator ya kisi compatible app mein QR scan karo.
3. App ka current six-digit code enter karo.
4. Setup ke baad dashboard open ho ga. Backup tokens generate karke private jagah save karo.
5. Agli dafa password ke saath authenticator code bhi chahiye hoga.

Customer account banana aur staff permission milna alag cheezen hain. Normal customer admin access nahi kar sakta.

## 4. Nayi watch add karna

**Catalog → Products → Add product** kholo.

- Name: watch ka naam.
- Slug: URL ka naam; name likhne se admin suggest kare ga.
- SKU: product ka unique code, misal `KAI-M001`.
- Collection: Men’s, Women’s ya Unisex.
- Category: Watches ya accessories.
- Regular price: PKR mein normal price.
- Sale price: optional; normal price se kam honi chahiye.
- Description aur specifications: sirf actual verified details likhna.

Neeche **Variants** mein kam az kam ek active row banao:

- Name: misal `Black dial / Silver strap`.
- Unique variant SKU: misal `KAI-M001-BLK`.
- Dial/strap colour aur stock: jitni available watches hain.
- Price khaali rakho to upar product wali price use ho gi; different price ho to yahan likh do.
- `Is active` tick hona chahiye.

**Product images** mein picture upload karo aur alt text likho. Multiple pictures ke liye multiple rows use karo. `Position` 0, 1, 2 se order set hota hai. Kisi specific variant ki picture attach karni ho to pehle product/variant save karo, phir dobara khol kar image ke Variant dropdown se select karo. Variant khaali ho to picture har finish mein nazar aati hai.

`Status = Published` select karo aur Save dabao. Watch apni collection aur Shop All mein khud aa jaye gi. `Featured` ya `New arrival` tick karne se relevant homepage section mein bhi aa jaye gi.

Picture JPG, PNG ya WebP ho: local/Docker par 5 MB tak, Vercel par har picture 1 MB se kam aur ek save mein total 3.8 MB se kam. SVG uploads allowed nahi. System filename khud banata, metadata remove karta aur smaller versions banata hai.

## 5. Logo, banners, price, stock aur contact change karna

| Kya change karna hai | Admin mein kahan |
| --- | --- |
| Logo / favicon / tagline | Core → Store settings |
| Main hero image, text aur buttons | Core → Store settings → Homepage hero |
| Neeche promotional banners | Core → Banners |
| Collection ki image | Catalog → Collections |
| Product ki price / sale | Catalog → Products → woh product |
| Product ka stock | Product ke neeche Variants → Stock |
| Phone, email, WhatsApp, social links | Core → Store settings |
| About, shipping, returns, privacy, FAQs | Core → Pages |
| Delivery charges / city list | Orders → Shipping zones |
| Bank details aur payment options | Orders → Payment methods |
| Discount code | Orders → Coupons |

Asli logo upload karte hi header, welcome screen, admin, emails aur order document mein wohi use ho ga. Proportions stretch nahi hongi. Transparent PNG/WebP best rahe ga. WhatsApp number `923001234567` jaisi digits mein likhna; plus aur spaces nahi.

## 6. Order aane ke baad

Admin → Orders mein order kholo. Customer ki delivery details, items aur totals wahin honge.

Normal order flow: **Pending → Confirmed → Processing → Shipped → Delivered**.

Bank transfer mein pehle apne actual bank mein payment check karo. Authorized owner/verifier phir **Verify received payments** action use kare. Is ke baghair bank-transfer order confirm nahi ho ga. Bank details pehle sahi likh kar payment method enable karna; demo bank account diya hi nahi gaya.

COD payment ko Delivered hone ke baad received mark karo. Pending/Confirmed/Processing order cancel karne se reserved stock ek dafa wapas aa jata hai. Paid order cancel ho to refund tumhein bank se alag manually handle karna ho ga. Website khud paise transfer/refund nahi karti.

Orders select karke CSV export kar sakte ho. Order page se document print ya PDF ke taur par save ho sakta hai. Yeh order summary hai, tax invoice ya payment proof nahi.

## 7. Emails kahan nazar aayengi?

Development mein email actually send nahi hoti; terminal mein print hoti hai. Docker use kar rahe ho to:

```powershell
docker compose logs web
```

Real customers ko emails bhejne ke liye SMTP credentials `.env` mein configure karne honge. Failed order emails dobara process karne ke liye:

```powershell
docker compose exec web python manage.py retry_order_emails
```

## 8. Live karne se pehle kya chahiye?

Apna logo, real product pictures/specifications, actual prices/stock, store contact details, bank account instructions, courier charges/areas, final policies, domain, Django hosting, PostgreSQL aur SMTP account configure karo. Demo items archive karo aur Store settings ka Demo mode tab off karo jab sab real data ho.

Production HTTPS/settings aur backups ke exact steps `docs/` mein hain. Website abhi kisi live domain par deploy nahi hui. Is environment mein 2 PostgreSQL concurrency tests run nahi ho sake; apne PostgreSQL setup par README wala full test command zaroor run karna.


## 8. Vercel par poori website (PC band hone par bhi)

Frontend aur backend dono isi Django project mein hain. `docs/VERCEL.md` mein exact
Vercel setup diya hai. Project Vercel par chalne ke baad laptop on rakhna zaroori
nahi. Database cloud PostgreSQL aur product pictures permanent S3/R2 bucket mein
honge. Local SQLite ya laptop ka media folder production ke liye use nahi karna.

Vercel account/project mein environment variables set karo. `DJANGO_SETTINGS_MODULE`
ko `config.settings.vercel` rakho. Database URL, bucket keys, HTTPS domain, random
Django secret, `CRON_SECRET`, SMTP aur WhatsApp keys wahan secure settings mein
likho; code ya chat mein paste nahi karna. Commercial store aur five-minute retry
Cron ke liye suitable Vercel plan chahiye; Hobby personal/non-commercial use ke liye hai.

Owner account banane aur migrations ke Windows commands `docs/VERCEL.md` mein hain.
Password screen par type hota hua nazar nahi aayega. Admin ka QR authenticator app
mein scan karo. `/admin/` mein products, stock, categories, pictures, policies aur
orders forms se manage ho sakte hain.

## 9. Tumhara number, Lahore checkout aur WhatsApp messages

Contact **03157292819**, WhatsApp **923157292819**, aur Instagram
**https://www.instagram.com/2.kairos.store/** set hain. Delivery sirf Lahore hai.
Customer ka name, mobile, email, area aur complete address required hain. Customer
chahe to location permission de kar pin add kare ya Google Maps share link paste kare.

Order aate hi owner alert aur customer receipt ke liye backend mein system bana
hai. Customer WhatsApp checkbox select kare ga to uska WhatsApp receipt queue hoga.
Email receipt bhi hai. Automatic WhatsApp ke liye apne Meta Business API sender,
access token aur approved templates configure karne hain—sirf WhatsApp number se
automatic message send nahi hota. Exact setup **docs/WHATSAPP.md** mein hai.

API sender apne hi number ko alert nahi bhej sakta. Agar 03157292819 ko sender banao
to owner alert ke liye doosra receiving number ya private email set karo; ya alag
API sender use karke 03157292819 par owner alerts lo. Owner notification fields
**Core → Store settings** mein hain.

**Orders → Shipping zones → Delivery estimate** mein apni asal delivery timing likho,
misal ke taur par business confirm kare to working days. Abhi koi days promise nahi
kiye gaye; default mein team se timing confirm karne ka text hai. Customer ke message
mein us waqt ki price, selection, address aur delivery estimate save hote hain.

Vercel par notifications ke liye laptop wala worker nahi chalana. Order ke baad
server send karta hai; Cron pending eligible retries sambhalta hai. Messages ka
status **Orders → WhatsApp notifications** mein dekho. `Submitted` ka matlab Meta
ne request accept ki; `Delivered` webhook ke baad hi delivery confirm hoti hai.
