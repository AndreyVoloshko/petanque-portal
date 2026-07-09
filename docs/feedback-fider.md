# Feedback Board (Fider) — feedback.petanque.org.ua

Self-hosted [Fider](https://fider.io) instance where federation members post ideas/bugs and
vote for them. Runs from our fork **https://github.com/AndreyVoloshko/fider**, which adds a
full Ukrainian (`uk`) locale on top of upstream (upstream has no Ukrainian translation).
The UI language is set via `LOCALE=uk` in `docker-compose.yml`.

## How it is wired

- **Compose service:** `petanque_feedback_fider` in `docker-compose.yml`, built directly
  from the fork's git URL. It sits behind the compose profile `feedback`, so
  `./deploy/local_run.sh` (local dev) does **not** start it; `deploy/remote_run.sh` runs
  compose with `--profile feedback` and does.
- **Database:** a separate `fider` database inside the existing `petanque_portal_db`
  Postgres container. Fider runs its own migrations on container start.
  Attachments/logos are stored in Postgres too (`BLOB_STORAGE=sql` default), so the
  regular DB backup covers everything.
- **Nginx:** `components/web-api/conf/web-service-server.conf` has a
  `feedback.petanque.org.ua` vhost (HTTP → ACME challenge + redirect, HTTPS → proxy to
  `petanque_feedback_fider:3000`). The upstream is resolved at request time via Docker
  DNS, so nginx starts fine when the fider container is absent (local dev).
- **TLS:** one certificate shared with the portal — `deploy/init-letsencrypt.sh` issues
  it with both domains as SANs (`--expand`). Renewal is handled by the existing certbot
  service.
- **Secrets:** `deploy/remote_run.sh` reads them from `APP_CREDENTIALS` in `.env`:
  `fider_jwt_secret` (new, required), plus the existing `smtp_host`, `smtp_port`,
  `smtp_user`, `smtp_password`, `smtp_from_email`.

## One-time go-live steps (on the server)

1. **DNS:** add an `A` record `feedback.petanque.org.ua` pointing to the server IP.
2. **Secret:** add `"fider_jwt_secret": "<long random string>"` to the `APP_CREDENTIALS`
   JSON in `/root/app/portal/.env` (generate with `openssl rand -hex 32`).
3. **Database:** create the fider database once:
   ```bash
   docker compose -p petanque-portal exec petanque_portal_db \
       psql -U <db_user from APP_CREDENTIALS> -c "CREATE DATABASE fider;"
   ```
4. **Certificate:** re-issue the cert so it also covers the feedback domain
   (safe to run before the new nginx config is deployed — the existing nginx already
   serves ACME challenges for any host):
   ```bash
   ./deploy/init-letsencrypt.sh
   docker compose -p petanque-portal exec petanque_portal_nginx nginx -s reload
   ```
5. **Deploy:** merge to `master` (CI deploys automatically) or run
   `./deploy/remote_run.sh` manually.
6. **Create the site:** open `https://feedback.petanque.org.ua/signup` and register the
   first administrator account. Set site name/branding under Site Settings.

## Updating Fider

The image builds from the fork's `main` at deploy time. To pick up upstream updates:

```bash
cd fider   # local clone of AndreyVoloshko/fider
git fetch upstream && git rebase upstream/main && git push --force-with-lease
```

Then redeploy (the `uk` locale commit is small and additive — two JSON files plus four
one-line registrations — so rebases are usually conflict-free).
