#!/usr/bin/env bash

# TODO: Make work with port other than 443

API_KEY=`cat /var/lib/mailinabox/api.key`
HOSTNAME=`hostname`

curl -s -X PUT -d "$CERTBOT_VALIDATION" --user "$API_KEY:" https://$HOSTNAME/admin/dns/custom/_acme-challenge.$CERTBOT_DOMAIN/TXT

sleep 15
