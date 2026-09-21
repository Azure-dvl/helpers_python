# Helpers

Colección de scripts personales de utilidad. Cada script es independiente y no comparte dependencias entre carpetas.

## Estructura

```
scripts/
├── download/        # Descargador unificado sobre yt-dlp (genérico + seriesdonghua.com)
├── python_utils/    # Utilidades Python (Appwrite, generación de PDFs)
└── scrpits/         # Scripts de shell (certificados, resolución de pantalla, renombrado)
```

---

## 1. `download/downloader.py` — Descargador con yt-dlp

Wraper de `yt-dlp` que combina dos flujos:

- **Genérico**: descarga videos/playlists/audio de cualquier plataforma soportada por yt-dlp.
- **Donghua**: extrae la fuente de video de páginas de `seriesdonghua.com` (script ofuscado) y la descarga.

Dependencia: `pip install yt-dlp` (ver `download/requirements.txt`).

### Uso genérico

```bash
python download/downloader.py -u <URL> [opciones]
```

| Opción | Descripción |
|---|---|
| `-u, --url <URL>` | URL a descargar (obligatorio) |
| `-o, --output <dir>` | Directorio de salida (default: `~/Downloads`) |
| `-r, --resolution {480,720,1080,best}` | Resolución máxima (default: `480`) |
| `-s, --subs` | Descarga subtítulos en inglés |
| `-m, --music` | Solo audio (extrae `bestaudio`; no descarga el video) |
| `-p, --playlist` | Descarga con estructura de playlist (`~/Downloads/<playlist>/...`) |
| `--dry-run` | Muestra el comando yt-dlp sin ejecutarlo |

Ejemplos:

```bash
# Video en 1080p
python download/downloader.py -u "https://www.youtube.com/watch?v=xxx" -r 1080

# Playlist completa sin máx. resolución
python download/downloader.py -u "https://www.youtube.com/playlist?list=xxx" -r best -p

# Solo audio
python download/downloader.py -u "https://example.com/cancion" -m

# Vista previa del comando
python download/downloader.py -u "https://example.com/v" -r 720 --dry-run
```

> Nota: `-m` y `-p` son mutuamente excluyentes.

### Uso donghua (seriesdonghua.com)

```bash
python download/downloader.py -u <URL-episodio> --donghua [opciones]
```

| Opción | Descripción |
|---|---|
| `--source {asura,skadi,fembed,tape,amagi}` | Fuerza una fuente (si se omite, muestra un menú numerado) |
| `-o, --output <dir>` | Directorio base (el episodio se guarda en `<output>/<título>/`) |
| `--dry-run` | Muestra el comando sin ejecutarlo |

El título del episodio se toma del `<title>` de la página y se sanea antes de crear la carpeta/archivo. El resultado queda en `~/Downloads/<título>/<título>.mp4`.

```bash
# Con menú interactivo de fuentes
python download/downloader.py -u "https://seriesdonghua.com/episodio-5" --donghua

# Forzando la fuente DailyMotion
python download/downloader.py -u "https://seriesdonghua.com/episodio-5" --donghua --source asura
```

> Errores de yt-dlp: el script valida que `yt-dlp` esté instalado, comprueba el código de salida y termina con error (exit 1) en caso de fallo.

---

## 2. `python_utils/appwrite_helper.py` — Actualización masiva en Appwrite

Copias el valor del campo `price` de cada documento de una colección a `originalPrice`.

**Dependencia:** `pip install appwrite` (ver `python_utils/requirements.txt`).

### Configuración

La configuración se lee de variables de entorno (el script falla si falta alguna):

| Variable | Descripción |
|---|---|
| `APPWRITE_ENDPOINT` | Endpoint de Appwrite (ej. `https://hostname/v1`) |
| `APPWRITE_PROJECT_ID` | ID del proyecto |
| `APPWRITE_API_KEY` | API Key con permisos de lectura/escritura en la base |
| `APPWRITE_DATABASE_ID` | ID de la base de datos |
| `APPWRITE_COLLECTION_ID` | ID de la colección |

### Ejecución

```bash
export APPWRITE_ENDPOINT="https://appwrite.example.com/v1"
export APPWRITE_PROJECT_ID="mi-proyecto"
export APPWRITE_API_KEY="..."
export APPWRITE_DATABASE_ID="db1"
export APPWRITE_COLLECTION_ID="productos"

python python_utils/appwrite_helper.py
```

Detalles de implementación: paginación con `Query.cursorAfter` (recomendada por Appwrite en vez de offset) y resumen de documentos actualizados al final.

---

## 3. `python_utils/create_pdf.py` — Generador de PDF desde JSON

Convierte archivos JSON en un PDF con categorías, títulos, campos y fotos (descargadas desde URL).

**Instalación:** `pip install reportlab pillow requests` (ver `python_utils/requirements.txt`).

### Uso

```bash
python python_utils/create_pdf.py <archivo1.json> [archivo2.json ...] [opciones]
```

| Opción | Descripción |
|---|---|
| `json_files` | Archivos JSON a procesar (posicional, requerido) |
| `-o, --output <archivo>` | PDF de salida (default: `output.pdf`) |
| `--img-w <pulgadas>` | Ancho de las imágenes (default: `2`) |
| `--img-h <pulgadas>` | Alto de las imágenes (default: `3`) |

### Formato del JSON

```json
[
  { "name": "Pelicula A", "year": "2020", "photo": "https://ejemplo.com/a.jpg" }
]
```

- Cada archivo JSON genera una sección nueva (el nombre de la sección = nombre del archivo sin extensión).
- El script incluye los campos `name`, `year` y `photo`; para añadir otros campos edita el bloque comentado dentro de `create_pdf()`.

Ejemplo:

```bash
python python_utils/create_pdf.py peliculas.json series.json -o catalogo.pdf --img-w 3 --img-h 4
```

---

## 4. `scrpits/generate.sh` — Certificados locales con mkcert

Genera un certificado de desarrollo firmado por la CA local de `mkcert`.

**Requisito:** tener `mkcert` instalado. Uso:

```bash
./scrpits/generate.sh [host] [archivo-cert] [archivo-key]
```

- `host` (default: `localhost`): IP o dominio para el certificado.
- `archivo-cert` / `archivo-key` (default: `server.crt` / `server.key`): nombres de salida.

```bash
./scrpits/generate.sh localhost
./scrpits/generate.sh 192.168.1.50 server.crt server.key
```

El script instala la CA local (`mkcert -install`) antes de generar y falla con un mensaje claro si `mkcert` no existe.

---

## 5. `scrpits/monitor_res.sh` — Forzar resolución de un monitor

Crea y aplica el modo `1920x1080@60Hz` en una salida X11 con `xrandr`.

**Requisito:** sesión gráfica con `xrandr`. Uso:

```bash
./scrpits/monitor_res.sh [salida]
```

- `salida` (default: `DP-1`): nombre de la salida del monitor (usa `xrandr` para listarlas).

El script es idempotente (no falla si el modo ya existe), verifica que la salida exista y detiene la ejecución si algo falla. Para cambiar la frecuencia/huella del modelo, edita `MODELINE` en el script.

---

## 6. `scrpits/rename_numbers.sh` — Renombrar archivos con prefijo numérico

Renombra todos los archivos de un directorio usando prefijos `001, 002, ...` manteniendo sus extensiones.

```bash
./scrpits/rename_numbers.sh [numero_inicial] [directorio]
```

- `numero_inicial` (default: `1`): con qué número empezar.
- `directorio` (default: `.`): carpeta a procesar.

Ejemplos:

```bash
./scrpits/rename_numbers.sh              # en el directorio actual, desde 001
./scrpits/rename_numbers.sh 10 /fotos    # desde 010 en /fotos
```

Comportamiento seguro: valida que el número inicial sea un número, calcula el padding según la cantidad de archivos (para >999 no rompe el orden), omite nombres que ya existen sin pisarlos y es idempotente (re-ejecutarlo no duplica ni borra).

---

## Requisitos por carpeta

| Carpeta | Dependencias |
|---|---|
| `download/` | `yt-dlp` (binario, se valida en runtime) |
| `python_utils/` | `appwrite`, `reportlab`, `pillow`, `requests` |
| `scrpits/` | `mkcert`, `xrandr` (sistema) |

> Se recomienda un virtualenv por carpeta: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.