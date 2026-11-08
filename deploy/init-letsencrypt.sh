#!/bin/bash
# petanque.org.ua validates only once its DNS points at this host, so expand
# the certificate after the DNS switch, not before.
domains=(portal.petanque.org.ua feedback.petanque.org.ua petanque.org.ua www.petanque.org.ua)
email="andreyvoloshko@gmail.com"
webroot="/var/www/certbot"

# --entrypoint "" is required: the certbot service defines a renewal-loop
# entrypoint, and "docker compose run" keeps it, ignoring the certonly command.
docker compose -p "petanque-portal" \
    run --rm --entrypoint "" certbot certbot certonly --webroot \
    --webroot-path=$webroot \
    --email $email \
    --agree-tos \
    --no-eff-email \
    --expand \
    $(for d in "${domains[@]}"; do echo -n "-d $d "; done)

