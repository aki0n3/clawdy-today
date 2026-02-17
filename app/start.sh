#!/bin/bash
set -e

# Check if SSL certificates are available
if [ -n "$SSL_CERTFILE" ] && [ -n "$SSL_KEYFILE" ] && [ -f "$SSL_CERTFILE" ] && [ -f "$SSL_KEYFILE" ]; then
    echo "SSL certificates found. Launching with HTTPS..."
    uvicorn main:app --host 0.0.0.0 --port 8000 \
        --ssl-certfile "$SSL_CERTFILE" \
        --ssl-keyfile "$SSL_KEYFILE"
else
    echo "SSL certificates not found. Launching with HTTP..."
    uvicorn main:app --host 0.0.0.0 --port 8000
fi
