# Order alerts and customer WhatsApp confirmations

The contact button is already linked to **923157292819** and Instagram is set to
https://www.instagram.com/2.kairos.store/ . A `wa.me` link opens WhatsApp for the
visitor; it cannot send unattended messages. Automated messages use the server-side
Meta WhatsApp Cloud API integration in `orders/notifications.py`.

## What happens when a customer orders

1. Server validates Lahore city, area, full address, Pakistani mobile and email;
   it checks the optional map link/coordinate pair, stock, prices, coupon and totals.
2. A transaction commits one order with customer/contact, line-item, delivery ETA
   and price snapshots. A duplicate checkout token does not create duplicate rows.
3. Customer email is sent; owner email is queued if a private notification inbox
   is configured. The owner WhatsApp alert is queued for the configured recipient.
4. Customer WhatsApp is queued only if the unticked order-update opt-in is selected.
   Its consent wording version and timestamp are retained with the order. No
   marketing consent or marketing send is implied.
5. Vercel dispatches after commit; containers use their notification worker. Meta's
   signed webhooks update sent/delivered/read/failed state in admin. Delivery cannot
   be guaranteed from an API acceptance response alone.

Owner alerts include the order number, customer name/phone/email, product/variant
summary, delivery address/area, total, optional map pin, ETA and an OTP-protected
staff order link. A long summary is shortened; the full order stays available in
the staff view. Customers receive their order receipt, selection, total, address
and the delivery estimate saved when they purchased. This does not mark a bank
transfer paid or promise dispatch before staff confirmation.

## Required Meta setup

Create/configure your own Meta business app, WhatsApp Business Account and API
sender. Obtain a server-side access token with the appropriate messaging permissions,
the sender's `PHONE_NUMBER_ID`, app secret and an unpredictable webhook verify token.
Use a production-capable token with the correct assets/permissions; monitor expiry.
No credentials are embedded in source or sent to browsers.

**The API sender cannot be the same as its recipient.** The default owner alert
recipient is 923157292819. Use a separate API sender to notify this number, or,
if you register 923157292819 as your API sender, enter a different owner receiving
number in **Core → Store settings → Order notification WhatsApp**. A private owner
email can serve as a second notification channel. Do not delete an existing
WhatsApp account or change its setup without following Meta's applicable onboarding
or supported coexistence flow for your account.

Set these in Vercel environment variables (or private local `.env` for Docker):

```text
WHATSAPP_ENABLED=true
WHATSAPP_ACCESS_TOKEN=<your server token>
WHATSAPP_PHONE_NUMBER_ID=<sender phone-number ID>
WHATSAPP_SENDER_NUMBER=<actual international sender digits>
WHATSAPP_GRAPH_VERSION=v26.0
WHATSAPP_CUSTOMER_TEMPLATE=kairos_order_received
WHATSAPP_OWNER_TEMPLATE=kairos_new_order_alert
WHATSAPP_TEMPLATE_LANGUAGE=en
WHATSAPP_WEBHOOK_VERIFY_TOKEN=<separate random secret>
WHATSAPP_APP_SECRET=<Meta app secret>
```

The default Graph version was checked against Meta's v26 changelog. Keep it updated
within Meta's support period. Add your real owner email under **Store settings →
Order notification email**. SMTP must be configured for delivery; the development
console email backend prints mail to the terminal.

## Templates to submit for approval

Create utility/order templates in WhatsApp Manager. **Meta must approve your exact
wording, category and language.** The texts below are proposed drafts; approval is
not guaranteed. Use positional body parameters and match the exact counts/order.
Do not add header/button parameters without updating the payload builder.

Customer template `kairos_order_received` — 6 parameters:

```text
Assalam-o-Alaikum {{1}}, KAIROS STORE ko aapka order {{2}} mil gaya hai.
Aapki selection: {{3}}.
Total PKR {{4}}, delivery charge included.
Lahore delivery address: {{5}}.
Andazati delivery: {{6}}.
Yeh order receive hone ki receipt hai; payment aur dispatch ki tasdeeq alag hogi.
Shukriya — Every Second, Your Style.
```

Parameters: customer name; order number; items/finishes/quantities; total in PKR;
address/area/city; delivery estimate.

Owner template `kairos_new_order_alert` — 10 parameters:

```text
KAIROS STORE: naya website order {{1}} receive hua hai.
Customer: {{2}}. Phone: {{3}}. Email: {{4}}.
Selection: {{5}}.
Lahore delivery address: {{6}}.
Total PKR {{7}}. Delivery pin: {{8}}. Andazati delivery: {{9}}.
Staff order details: {{10}}.
Payment status aur address verify karke fulfilment karein.
```

Parameters: order number; customer name; mobile; email; items summary; full delivery
address/area/landmark; total; map URL or no-pin text; ETA; staff-only admin URL.
Use approved sample values when submitting your templates. If you choose a language
other than `en`, change the environment value to match the approved template locale.

## Webhook and retries

Callback URL: `https://YOUR_REAL_DOMAIN/webhooks/whatsapp/`.
Configure the same verify token and subscribe to message status events. POSTs must
have a correct `X-Hub-Signature-256` HMAC using your app secret. Unknown phone-number
IDs and mismatched recipients are ignored. Incoming conversation text is not stored.

The built-in queue retries definitive transient provider errors, up to five attempts
with backoff. Permanent errors stop as failed. A network timeout or interrupted
worker is `uncertain`, because a message may already have reached Meta. Review Meta
logs first; only the OTP-verified owner can requeue reviewed failed/uncertain rows.
This is designed to reduce duplicate notifications; exactly-once external delivery
is not promised. A crashed function still leaves durable database rows for review.

For local/Docker use:

```text
python manage.py run_notification_worker --poll-seconds 5
python manage.py process_order_notifications --limit 25
```

Docker Compose includes the worker. On Vercel, the authenticated five-minute Cron
runs retries without a laptop or permanent worker. Keep `CRON_SECRET` private.
Never expose a public "send message" or notification-retry endpoint.

## Delivery location and ETA

Set actual delivery days and charges in **Orders → Shipping zones**. No number of
days was supplied, so the initial text says the team will confirm the delivery time.
The exact text is saved into each order before it appears in customer messages.
The GPS button requires a customer action and browser permission; full street/area
entry is still required. Google Maps share links are optional and host-validated.
The configured GPS bounds are an approximate Lahore service rectangle, not an
address-verification/geocoding service. Staff must review the actual address/pin
before confirming dispatch. Never claim that a manually entered city proves the
physical address is within a municipal boundary.

Official references consulted:

- https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview
- https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/whatsapp-business-phone-number/message-api
- https://developers.facebook.com/documentation/business-messaging/whatsapp/getting-opt-in
- https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview
- https://developers.facebook.com/docs/graph-api/webhooks/getting-started/
- https://developers.facebook.com/docs/graph-api/changelog/version26.0/
