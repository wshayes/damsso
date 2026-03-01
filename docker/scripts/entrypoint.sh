#!/bin/bash
set -e

echo "========================================"
echo "  Multi-Tenant SSO Demo - Starting Up"
echo "========================================"

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('${DB_HOST:-postgres}', ${DB_PORT:-5432}))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
    echo "  PostgreSQL not ready, waiting..."
    sleep 2
done
echo "PostgreSQL is ready."

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Seed demo data
echo "Seeding demo data..."
SEED_ARGS=""
if [ -n "$KEYCLOAK_INTERNAL_URL" ]; then
    SEED_ARGS="--keycloak-url $KEYCLOAK_INTERNAL_URL"
fi
python manage.py seed_demo_data $SEED_ARGS || echo "Warning: Seed command had issues (may be partially seeded)"

echo ""
echo "========================================"
echo "  Demo Environment Ready!"
echo "========================================"
echo ""
echo "  Django App:     http://localhost:8000"
echo "  Django Admin:   http://localhost:8000/admin/"
echo "    Username:     admin@demo.com"
echo "    Password:     demo"
echo ""
echo "  Keycloak:       http://localhost:8443"
echo "    Username:     admin"
echo "    Password:     admin"
echo ""
echo "  Mailpit:        http://localhost:8025"
echo ""
echo "  Demo Tenants:"
echo "    Acme (OIDC):  http://localhost:8000/tenants/login/acme-oidc/"
echo "    Globex (SAML): http://localhost:8000/tenants/login/globex-saml/"
echo "    Initech:      http://localhost:8000/tenants/login/initech/"
echo ""
echo "  Test Users (password: password):"
echo "    alice@acme.com, bob@acme.com (OIDC)"
echo "    carol@globex.com, dave@globex.com (SAML)"
echo "    nouser@initech.com (no SSO)"
echo ""
echo "========================================"

# Execute the main command
exec "$@"
