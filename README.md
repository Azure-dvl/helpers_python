# Helpers

[![tests](https://github.com/Azure-dvl/helpers_python/actions/workflows/tests.yml/badge.svg)](https://github.com/Azure-dvl/helpers_python/actions/workflows/tests.yml)

Colección de scripts personales de utilidad. Cada script es independiente y no comparte dependencias entre carpetas.

## Estructura

```
download/         # Descargador unificado sobre yt-dlp (genérico, facebook.com y donghua: seriesdonghua.com, donghualife.com, mundodonghua.com)
python_utils/     # Utilidades Python (Appwrite, generación de PDFs)
scrpits/          # Scripts de shell (certificados, resolución de pantalla, renombrado) — nombre del directorio así ya está escrito
tests/            # Tests con unittest de la stdlib (sin dependencias extra)
```

---

## 1. `download/downloader.py` — Descargador con yt-dlp

Wraper de `yt-dlp` que combina tres flujos:

- **Genérico**: descarga videos/playlists/audio de cualquier plataforma soportada por yt-dlp.
- **Facebook**: flujo optimizado para URLs de `facebook.com` / `fb.watch` / `fb.me`.
- **Donghua**: extrae la fuente de video real de `seriesdonghua.com`, `donghualife.com` y `mundodonghua.com` y la descarga.

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
| `--cookies-from-browser <nav>` | Extrae cookies del navegador para vídeos restringidos (ej. `chrome:Default`, `firefox:default-release`). Vale para **todos** los modos: genérico, `--facebook` y `--donghua` |
| `--dry-run` | Muestra el comando yt-dlp sin ejecutarlo |

Ejemplos:

```bash
# Video en 1080p
python download/downloader.py -u "https://www.youtube.com/watch?v=xxx" -r 1080

# Playlist completa sin máx. resolución
python download/downloader.py -u "https://www.youtube.com/playlist?list=xxx" -r best -p

# Solo audio
python download/downloader.py -u "https://example.com/cancion" -m

# Con cookies del navegador (vídeos restringidos)
python download/downloader.py -u "https://example.com/v" --cookies-from-browser chrome:Default

# Vista previa del comando
python download/downloader.py -u "https://example.com/v" -r 720 --dry-run
```

> Nota: `-m` y `-p` son mutuamente excluyentes.

### Uso facebook (`--facebook`)

```bash
python download/downloader.py -u <URL-facebook> --facebook [opciones]
```

Flujo optimizado para videos de Facebook (`facebook.com`, `www.facebook.com`, subdominios de locale como `es-la.facebook.com`, `fb.watch` y `fb.me`):

- **Valida que la URL sea de Facebook**: si no lo es, sale con error claro (exit 1).
- **User-Agent de navegador + `Referer: https://www.facebook.com/`**: Facebook bloquea peticiones que no parecen de un navegador.
- **Formato con respaldo `/best`**: Facebook suele servir un único archivo progresivo; si no existe un formato con la altura pedida (`-r`), cae a `best` en lugar de fallar.
- **Salida siempre `.mp4`** (`--merge-output-format mp4`).

Combina con `-r`, `-m`, `-s`, `-p`, `-o` y `--dry-run` igual que el modo genérico. `--facebook` y `--donghua` son mutuamente excluyentes.

```bash
# Descargar un video de Facebook en 720p
python download/downloader.py -u "https://www.facebook.com/watch/?v=10153231379946729" --facebook -r 720

# Enlace corto fb.watch, solo audio
python download/downloader.py -u "https://fb.watch/abcXYZ/" --facebook -m

# Usando cookies del navegador (para videos restringidos)
python download/downloader.py -u "https://www.facebook.com/usuario/videos/123/" --facebook --cookies-from-browser chrome:Default
python download/downloader.py -u "https://www.facebook.com/usuario/videos/123/" --facebook --cookies-from-browser firefox:i1nba72r.default-release

# Vista previa del comando
python download/downloader.py -u "https://www.facebook.com/usuario/videos/123/" --facebook --dry-run
```

> Limitación: vídeos privados o que piden inicio de sesión necesitan cookies de sesión; usa `--cookies-from-browser` para que yt-dlp las lea de tu navegador (Firefox puede pedir la contraseña del keyring; Chrome puede requerir `--no-sandbox` en algunas distros).

### Uso donghua (seriesdonghua.com, donghualife.com, mundodonghua.com)

```bash
python download/downloader.py -u <URL-episodio> --donghua [opciones]
```

El flujo `--donghua` detecta el dominio automáticamente y extrae la fuente de video real de cada página:

| Sitio | Mecanismo de extracción |
|---|---|
| `seriesdonghua.com` | API interna `/api/player/get-server` (cookie de sesión + token CSRF) |
| `donghualife.com` | tokens cifrados embebidos en la página, resueltos con `/api/player/source` |
| `mundodonghua.com` | scripts ofuscados (JavaScript Packer): m3u8 directo (`asura`), Dailymotion (`tamamo`) e iframes (`fmoon`, `amagi`, `vhide`, `swish`) |

| Opción | Descripción |
|---|---|
| `--source <clave>` | Fuerza una fuente concreta (claves por sitio abajo). Si se omite, muestra un menú numerado y, si la elegida falla, reintenta automáticamente con las demás |
| `-o, --output <dir>` | Directorio base (el episodio se guarda en `<output>/<título>/`) |
| `--dry-run` | Muestra los comandos yt-dlp sin ejecutarlos (con `--source`, solo el de esa fuente) |

Claves de fuente por sitio (las que yt-dlp resuelve de forma fiable van primero):

| Sitio | Claves de `--source` |
|---|---|
| `seriesdonghua.com` | `dailymotion`, `okru`, `rumble`, `voe` |
| `donghualife.com` | `directo` (m3u8 del propio sitio), `dailymotion`, `rumble` |
| `mundodonghua.com` | `asura` (m3u8 directo), `tamamo` (Dailymotion), `fmoon`, `amagi`, `vhide`, `swish` |

El título del episodio se toma del `<title>` de la página y se sanea antes de crear la carpeta/archivo. El resultado queda en `~/Downloads/<título>/<título>.mp4`.

```bash
# Menú interactivo (default: primera fuente; si falla, prueba las demás)
python download/downloader.py -u "https://seriesdonghua.com/against-the-sky-supreme-episodio-553/" --donghua

# Fijar una fuente concreta
python download/downloader.py -u "https://seriesdonghua.com/against-the-sky-supreme-episodio-553/" --donghua --source dailymotion

# donghualife.com (acepta slugs y UUIDs de /watch/<id>)
python download/downloader.py -u "https://donghualife.com/watch/against-sky-supreme-1-551" --donghua

# mundodonghua.com — m3u8 directo
python download/downloader.py -u "https://www.mundodonghua.com/ver/against-the-sky-supreme/510" --donghua --source asura
```

> Notas:
> - `directo` (donghualife) y `asura` (mundodonghua) son m3u8 directos: la opción más fiable de cada sitio.
> - Sin entrada interactiva (pipeline, cron o terminal cerrada) el menú no puede mostrarse: el script usa la primera fuente en lugar de fallar. `Ctrl+C` en el menú cancela con exit 1.
> - `okru`, `rumble`, `voe` y los iframes de terceros (`fmoon`, `amagi`, `vhide`, `swish`) pueden fallar según el soporte de yt-dlp (HTTP 403 en el extractor de Rumble, bug del extractor de OK.ru, "Unsupported URL" para Voe/Bysekoze/VidHidePro/EmbedWish); por eso el menú reintenta automáticamente con la siguiente fuente.
> - `tamamo` (Dailymotion) puede estar dado de baja para algunos episodios (el sitio elimina el video); en ese caso usa `asura`.
> - El script valida que `yt-dlp` esté instalado, comprueba el código de salida y termina con error (exit 1) si todas las fuentes fallan.

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
- El JSON debe ser una **lista de objetos** (`[{...}, {...}]`); si no lo es, el script sale con un error claro y exit 1 en lugar de un traceback.
- El script incluye los campos `name`, `year` y `photo`; para añadir otros campos edita el bloque comentado dentro de `create_pdf()`.
- Las fotos se descargan con timeout de 10 s: si una URL falla, el elemento se documenta sin foto y el PDF se genera igual.

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

## 7. `tests/` — Tests

Tests de las partes sin red de `download/downloader.py` y `python_utils/create_pdf.py`, con `unittest` de la stdlib (no requieren `yt-dlp` ni red):

```bash
python -m unittest discover -s tests -v
```

Se ejecutan también en CI (GitHub Actions) en cada push y pull request.

---

## Requisitos por carpeta

| Carpeta | Dependencias |
|---|---|
| `download/` | `yt-dlp` (binario, se valida en runtime) |
| `python_utils/` | `appwrite`, `reportlab`, `pillow`, `requests` |
| `scrpits/` | `mkcert`, `xrandr` (sistema) |

> Se recomienda un virtualenv por carpeta: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.