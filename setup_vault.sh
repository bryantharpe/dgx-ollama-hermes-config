#!/bin/bash
set -e

# Bring up only the vault service
echo "Bringing up Vault container..."
docker compose up -d vault

# Wait for Vault to initialize
echo "Waiting 5 seconds for Vault to initialize..."
sleep 5

# Extract secrets from .env
echo "Extracting secrets from .env..."
HOME_ASSISTANT_URL=$(grep "^HOME_ASSISTANT_URL=" .env | cut -d'=' -f2-)
HOME_ASSISTANT_TOKEN=$(grep "^HOME_ASSISTANT_TOKEN=" .env | cut -d'=' -f2-)
BRAVE_API_KEY=$(grep "^BRAVE_API_KEY=" .env | cut -d'=' -f2-)
UNIFI_API_KEY=$(grep "^UNIFI_API_KEY=" .env | cut -d'=' -f2-)

# Inject secrets into Vault
echo "Injecting secrets into Vault at secret/gemini-cli..."
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='root' vault vault kv put secret/gemini-cli \
  HOME_ASSISTANT_URL="$HOME_ASSISTANT_URL" \
  HOME_ASSISTANT_TOKEN="$HOME_ASSISTANT_TOKEN" \
  BRAVE_API_KEY="$BRAVE_API_KEY" \
  UNIFI_API_KEY="$UNIFI_API_KEY"

# Verify injection
echo "Verifying secrets in Vault..."
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='root' vault vault kv get secret/gemini-cli
