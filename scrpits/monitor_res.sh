#!/bin/bash
set -euo pipefail

MODE="1920x1080_60.00"
MODELINE="173.00 1920 2048 2248 2576 1080 1083 1088 1120 -hsync +vsync"
OUTPUT="${1:-DP-1}"

if ! command -v xrandr >/dev/null 2>&1; then
    echo "Error: xrandr no esta instalado." >&2
    exit 1
fi

if ! xrandr | grep -q "^$OUTPUT "; then
    echo "Error: la salida '$OUTPUT' no esta disponible. Salidas detectadas:" >&2
    xrandr | grep -E "^[A-Za-z]+ " >&2
    exit 1
fi

if ! xrandr --newmode "$MODE" $MODELINE 2>/dev/null; then
    echo "El modo $MODE ya existe, continuando..."
fi

xrandr --addmode "$OUTPUT" "$MODE" 2>/dev/null || \
    echo "El modo $MODE ya estaba asignado a $OUTPUT"

xrandr --output "$OUTPUT" --mode "$MODE"

echo "Resolucion aplicada: $OUTPUT -> $MODE"