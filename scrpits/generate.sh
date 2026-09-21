#!/bin/bash
set -euo pipefail

# Uso: ./generate.sh [host] [cert-file] [key-file]
# host por defecto: localhost (remplaza con la IP/dominio que necesites)
HOST="${1:-localhost}"
CRT="${2:-server.crt}"
KEY="${3:-server.key}"

if ! command -v mkcert >/dev/null 2>&1; then
    echo "Error: mkcert no esta instalado (https://github.com/FiloSottile/mkcert)." >&2
    exit 1
fi

# Confia primero la CA local y luego genera el certificado
mkcert -install
mkcert -cert-file "$CRT" -key-file "$KEY" "$HOST"

echo "Certificados generados: $CRT y $KEY para $HOST"