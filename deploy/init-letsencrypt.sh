#!/bin/bash

domains=(portal.petanque.org.ua)
email="andreyvoloshko@gmail.com"
webroot="/var/www/certbot"

docker compose -p "petanque-portal" \
    run --rm certbot sh -c "
        certbot certonly --webroot \
            --webroot-path=$webroot \
            --email $email \
            --agree-tos \
            --no-eff-email \
            $(for d in "${domains[@]}"; do echo -n "-d $d "; done);
        echo 'Waiting for certificate to be generated...';
        sleep 5
    "
