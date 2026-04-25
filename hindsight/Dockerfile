# Caddy sidecar in front of Hindsight to filter public access to diagnostic
# endpoints (/metrics, /docs, /openapi.json). Single Fly machine, two procs:
# Caddy on :8888 (Fly's internal_port) reverse-proxies to Hindsight on :8889.

FROM caddy:2.8-alpine AS caddy

FROM ghcr.io/vectorize-io/hindsight:latest

USER root
COPY --from=caddy /usr/bin/caddy /usr/local/bin/caddy
COPY Caddyfile /etc/caddy/Caddyfile
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
USER hindsight

EXPOSE 8888

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
