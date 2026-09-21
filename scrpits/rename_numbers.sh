#!/bin/bash
set -euo pipefail

# Script para renombrar archivos con prefijos numéricos
# Uso: rename_numbers.sh [numero_inicial] [directorio]

numero_inicial="${1:-1}"
directorio="${2:-.}"

if ! [[ "$numero_inicial" =~ ^[0-9]+$ ]]; then
    echo "Error: '$numero_inicial' no es un número válido." >&2
    exit 1
fi

if [ ! -d "$directorio" ]; then
    echo "Error: '$directorio' no es un directorio válido." >&2
    exit 1
fi

cd "$directorio" || exit 1

# Cuenta los archivos para calcular el padding de ceros (001, 002, ...)
archivos=(*)
total=0
for archivo in "${archivos[@]}"; do
    [ -f "$archivo" ] && total=$((total + 1))
done

if [ "$total" -eq 0 ]; then
    echo "No hay archivos para renombrar."
    exit 0
fi

pad=${#total}
contador=$numero_inicial
for archivo in "${archivos[@]}"; do
    if [ -f "$archivo" ]; then
        extension="${archivo##*.}"

        if [ "$archivo" = "$extension" ]; then
            nuevo_nombre=$(printf "%0${pad}d" "$contador")
        else
            nuevo_nombre=$(printf "%0${pad}d.%s" "$contador" "$extension")
        fi

        if [ "$nuevo_nombre" = "$archivo" ]; then
            continue
        fi

        if [ -e "$nuevo_nombre" ]; then
            echo "Omitido (ya existe): $archivo -> $nuevo_nombre"
            contador=$((contador + 1))
            continue
        fi

        mv "$archivo" "$nuevo_nombre"
        echo "$archivo -> $nuevo_nombre"
        contador=$((contador + 1))
    fi
done

echo "Total: $((contador - numero_inicial)) archivos renombrados."