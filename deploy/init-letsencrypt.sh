#!/bin/bash
domains=(portal.petanque.org.ua feedback.petanque.org.ua)
email="andreyvoloshko@gmail.com"
webroot="/var/www/certbot"

docker compose -p "petanque-portal" \
    run --rm certbot certonly --webroot \
    --webroot-path=$webroot \
    --email $email \
    --agree-tos \
    --no-eff-email \
    --expand \
    $(for d in "${domains[@]}"; do echo -n "-d $d "; done)

