#!/bin/bash

# Script para renombrar archivos con prefijos numéricos
# Uso: renombrar_numeros.sh [numero_inicial] [directorio]

numero_inicial="${1:-1}"
directorio="${2:-.}"

if [ ! -d "$directorio" ]; then
    echo "Error: '$directorio' no es un directorio válido."
    exit 1
fi

cd "$directorio" || exit 1

contador=$numero_inicial
for archivo in *; do
    if [ -f "$archivo" ]; then
        extension="${archivo##*.}"
        
        if [ "$archivo" = "$extension" ]; then
            nuevo_nombre=$(printf "%03d" "$contador")
        else
            nuevo_nombre=$(printf "%03d.%s" "$contador" "$extension")
        fi
        
        mv -i "$archivo" "$nuevo_nombre"
        echo "$archivo -> $nuevo_nombre"
        ((contador++))
    fi
done

echo "Total: $((contador - numero_inicial)) archivos renombrados."
