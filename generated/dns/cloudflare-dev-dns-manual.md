# Cloudflare DNS Manual Step

This script does NOT call Cloudflare API.

Protected production domain:

- ordinoxai.com

Dev domain:

- dev.ordinoxai.com

Do NOT delete or edit existing production records.

Add only this record manually after ingress IP is confirmed:

Type: A
Name: dev
Value: <INGRESS_PUBLIC_IP>
Proxy: DNS only first
TTL: Auto

After HTTPS works, you may enable Cloudflare proxy.

Validation:

dig +short dev.ordinoxai.com
curl -I https://dev.ordinoxai.com

Rollback:

Only remove the dev record if needed.
Do not touch:
- root ordinoxai.com
- www
- api
- mail
- MX
- TXT
- SPF
- DKIM
- DMARC
