# PostgreSQL and media backup / restore

Back up the database, uploaded media and necessary secrets/configuration. Keep encrypted copies off the application host, restrict access, define retention, and regularly restore a copy into an isolated environment. Audit logs and orders live in PostgreSQL; product photos/logo/uploads live in media. Static assets are reproducible from source. PostgreSQL major versions matter: use compatible `pg_dump`/`pg_restore` tools and follow PostgreSQL's upgrade documentation for major upgrades.

## Docker Compose — portable binary-safe commands

These commands use the default `kairos` database/user from `.env.example`. Substitute your configured names. Run from the project directory. Stop accepting new orders or use an appropriate maintenance window when taking a coordinated database/media snapshot.

```powershell
New-Item -ItemType Directory -Force backups
docker compose exec -T db pg_dump -U kairos -d kairos --format=custom --file=/tmp/kairos.dump
docker compose cp db:/tmp/kairos.dump ./backups/kairos.dump
docker compose exec -T web tar -czf /tmp/kairos-media.tar.gz -C /app media
docker compose cp web:/tmp/kairos-media.tar.gz ./backups/kairos-media.tar.gz
```

Linux/macOS: replace the first command with `mkdir -p backups`. Copying the dump file avoids older PowerShell binary-redirection corruption. Do not store these backups in a public directory or commit them. Use timestamped filenames for real retention.

### Restore

Restore only after you have explicitly selected the intended destination and backed up its current contents. The `--clean` restore below replaces existing database objects. First test this procedure on a separate disposable environment.

```powershell
docker compose stop web
docker compose cp ./backups/kairos.dump db:/tmp/kairos.dump
docker compose exec -T db pg_restore -U kairos -d kairos --clean --if-exists --no-owner --no-privileges /tmp/kairos.dump
docker compose start web
docker compose cp ./backups/kairos-media.tar.gz web:/tmp/kairos-media.tar.gz
docker compose exec -T web tar -xzf /tmp/kairos-media.tar.gz -C /app
docker compose exec web python manage.py migrate
docker compose exec web python manage.py check
```

Keep application traffic blocked through your proxy/maintenance mechanism until the coordinated database/media restore is complete and checked. The application user must own the restored media files. Test a product image, admin OTP, customer order ownership and an order read after restoration. Verify an outbox from a restored backup before enabling email delivery; it may contain old pending messages.

## Native PostgreSQL

Use a PostgreSQL password prompt or a protected password file; avoid publishing credentials in shell history.

```bash
pg_dump -h 127.0.0.1 -U kairos -d kairos --format=custom --file=kairos.dump
pg_restore -h 127.0.0.1 -U kairos -d kairos_restore --no-owner --no-privileges kairos.dump
```

Create `kairos_restore` separately as a test target and configure a separate application instance for validation. Back up `MEDIA_ROOT` with your file/volume backup tool, and retain deployment environment values separately in secure storage. A database restore without the correct media backup loses photographs; without the original signing secret, existing signed links/reset/session data may no longer validate.

The commands are documented; a PostgreSQL backup/restore and Docker startup could not be executed in this environment. Run and verify them on your deployment platform.


## Cloud-hosted deployment

For Vercel, enable the managed PostgreSQL provider's automated backups/PITR and
perform a restore drill in a separate database. Use the provider's direct database
URL for maintenance when its transaction-pool endpoint does not support backup
operations. Include all new notification/consent/location tables in database backups.
Version and back up the permanent media bucket separately. No upload backup exists
on Vercel's temporary runtime filesystem. Keep cloud credentials out of backup ZIPs.
