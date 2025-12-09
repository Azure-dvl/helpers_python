"""Manejo de actualizaciones masivas automaticas"""

from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.query import Query

# Configuración inicial del cliente
client = Client()

(client
  .set_endpoint('https://nyc.cloud.appwrite.io/v1')  # Tu endpoint
  .set_project('68d98212000f1200f4ea')                 # Tu Project ID
  .set_key('standard_950cffd809c79ff89affb980ef367b4da8cff05b40940ecaca55e94e504c9dfd6e9ade61f1a0e6bfff3493b3de783ed83af7262b1e29434e5c5906937442dc3c93f2380e302613a71a67649cb1303bb8dfb1a1e841185699612569e8ff940ea9bdf40cafded58e84fe143e924ba4e413405453893e5597b1c20864ff5055988b')                         # Tu API Key
)

databases = Databases(client)

# Configura estos valores
DATABASE_ID = '68dce67e00101f0ecf0f' # Tu Database ID
COLLECTION_ID = 'products'  # Tu collection ID

def update_prices():
    """Actualiza los precios de todos los productos"""
    try:
        # Primero obtenemos todos los documentos (productos)
        documents = []
        offset = 0
        limit = 100

        while True:
            response = databases.list_documents(
                DATABASE_ID,
                COLLECTION_ID,
                queries=[
                    Query.limit(limit),
                    Query.offset(offset)
                ]
            )
            
            batch = response['documents']
            if not batch:
                break
                
            documents.extend(batch)
            offset += limit
            print(f"Obtenidos {len(documents)} documentos...")

        # Actualizamos cada documento
        updated_count = 0
        for document in documents:
            try:
                # Verificamos que exista originalPrice
                if 'price' in document and document['price'] is not None:
                    databases.update_document(
                        DATABASE_ID,
                        COLLECTION_ID,
                        document['$id'],
                        {
                            'originalPrice': document['price']
                        }
                    )
                    updated_count += 1
                    print(f"✅ Documento {document['$id']} actualizado: originalPrice = {document['price']}")
                else:
                    print(f"⚠️ Documento {document['$id']} no tiene originalPrice válido")
                    
            except Exception as e:
                print(f"❌ Error actualizando documento {document['$id']}: {str(e)}")

        print(f"\n✅ Proceso completado! {updated_count} documentos actualizados de {len(documents)} totales")

    except Exception as e:
        print(f"❌ Error general: {str(e)}")

# Ejecución principal
if __name__ == "__main__":
    update_prices()