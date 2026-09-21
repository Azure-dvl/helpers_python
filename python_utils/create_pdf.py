import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer


def load_json_data(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def download_image(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return PILImage.open(BytesIO(response.content))
    except Exception as e:
        print(f"Error al descargar imagen {url}: {str(e)}")
        return None


def create_pdf(output_filename, json_files, img_width=2.0, img_height=3.0):
    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    story = []

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading1"]
    body_style = styles["BodyText"]

    custom_style = ParagraphStyle(
        "CustomStyle",
        parent=body_style,
        spaceAfter=12,
    )

    for json_file in json_files:
        data = load_json_data(json_file)
        category_name = Path(json_file).stem.capitalize()

        story.append(Paragraph(category_name, title_style))
        story.append(Spacer(1, 24))

        for item in data:
            # Agrega aqui los condicionadores de los campos que quieras incluir, en orden
            name = item.get("name")
            if name:
                story.append(Paragraph(str(name), heading_style))
                story.append(Spacer(1, 12))

            year = item.get("year")
            if year:
                story.append(Paragraph(f"Year: {year}", custom_style))

            photo = item.get("photo")
            if photo:
                img = download_image(photo)
                if img:
                    try:
                        if img.mode == "RGBA":
                            img = img.convert("RGB")

                        img_io = BytesIO()
                        img.save(img_io, format="JPEG", quality=90)
                        img_io.seek(0)

                        # Imagen redimensionada al PDF
                        story.append(Image(img_io, width=img_width * inch, height=img_height * inch))
                        story.append(Spacer(1, 24))
                    except Exception as e:
                        print(f"Error al procesar imagen {photo}: {str(e)}")

            story.append(Spacer(1, 24))

        print(f"Completado: {json_file}")
        story.append(PageBreak())

    doc.build(story)


def main():
    parser = argparse.ArgumentParser(description="Genera un PDF a partir de archivos JSON")
    parser.add_argument("json_files", nargs="+", help="Archivos JSON a procesar")
    parser.add_argument(
        "-o", "--output", default="output.pdf", help="Archivo PDF de salida (default: output.pdf)"
    )
    parser.add_argument(
        "--img-w", type=float, default=2.0, help="Ancho de las imagenes en pulgadas (default: 2)"
    )
    parser.add_argument(
        "--img-h", type=float, default=3.0, help="Alto de las imagenes en pulgadas (default: 3)"
    )
    args = parser.parse_args()

    print("Iniciando...")
    create_pdf(args.output, args.json_files, args.img_w, args.img_h)
    print("Completo")


if __name__ == "__main__":
    sys.exit(main())