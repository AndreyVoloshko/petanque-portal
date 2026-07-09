#!/bin/bash
domains=(portal.petanque.org.ua feedback.petanque.org.ua)
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

