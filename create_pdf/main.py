import json
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import requests
from io import BytesIO
from PIL import Image as PILImage

def load_json_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def download_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = PILImage.open(BytesIO(response.content))
            return img
        else:
            print(f"Error al descargar imagen: {url} - Código {response.status_code}")
            return None
    except Exception as e:
        print(f"Error al descargar imagen {url}: {str(e)}")
        return None

def create_pdf(output_filename, json_files):
    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading1']
    body_style = styles['BodyText']
    
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=body_style,
        spaceAfter=12,
    )
    
    for json_file in json_files:
        data = load_json_data(json_file)
        category_name = json_file.replace('.json', '').capitalize()
        

        story.append(Paragraph(category_name, title_style))
        story.append(Spacer(1, 24))
        
        for item in data:

            # pon los condicionadores de acuerdo a los que vayas a transformar en pdf por orden

            story.append(Paragraph(item['name'], heading_style))
            story.append(Spacer(1, 12))

            if 'year' in item and item['year']:
                story.append(Paragraph(f"Year: {item['year']}", custom_style))
            
            # Imagen
            if 'photo' in item and item['photo']:
                img = download_image(item['photo'])
                if img:
                    try:
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                            
                        img_io = BytesIO()
                        img.save(img_io, format='JPEG', quality=90)
                        img_io.seek(0)
                        
                        # Añadir imagen al PDF
                        story.append(Image(img_io, width=2*inch, height=3*inch))
                        story.append(Spacer(1, 24))
                    except Exception as e:
                        print(f"Error al procesar imagen {item['photo']}: {str(e)}")
            
            story.append(Spacer(1, 24))
            
        print(f'se completo {json_file}')
        story.append(PageBreak())
    
    doc.build(story)

# Lista de archivos JSON a procesar
json_files = [
    
]

print('Iniciando...')
create_pdf('file.pdf', json_files)
print('Completo')