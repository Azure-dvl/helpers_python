"""Manejo de actualizaciones masivas automaticas en Appwrite"""

import os

from appwrite.client import Client
from appwrite.query import Query
from appwrite.services.databases import Databases

ENV_MAP = {
    "endpoint": "APPWRITE_ENDPOINT",
    "project_id": "APPWRITE_PROJECT_ID",
    "api_key": "APPWRITE_API_KEY",
    "database_id": "APPWRITE_DATABASE_ID",
    "collection_id": "APPWRITE_COLLECTION_ID",
}


def load_config():
    config = {key: os.environ.get(env, "").strip() for key, env in ENV_MAP.items()}
    missing = [env for key, env in ENV_MAP.items() if not config[key]]
    if missing:
        raise SystemExit("Faltan variables de entorno: " + ", ".join(missing))
    return config


def get_databases(config):
    client = Client()
    client.set_endpoint(config["endpoint"]).set_project(
        config["project_id"]
    ).set_key(config["api_key"])
    return Databases(client)


def update_prices(config):
    databases = get_databases(config)
    documents = []
    cursor = None
    limit = 100

    # Paginacion por cursor (recomendada por Appwrite) en vez de offset
    while True:
        queries = [Query.limit(limit)]
        if cursor:
            queries.append(Query.cursorAfter(cursor))
        response = databases.list_documents(
            config["database_id"],
            config["collection_id"],
            queries=queries,
        )

        batch = response["documents"]
        if not batch:
            break

        documents.extend(batch)
        cursor = batch[-1]["$id"]
        print(f"Obtenidos {len(documents)} documentos...")

    updated_count = 0
    for document in documents:
        try:
            # Verificamos que exista el campo "price" para copiarlo a originalPrice
            if "price" in document and document["price"] is not None:
                databases.update_document(
                    config["database_id"],
                    config["collection_id"],
                    document["$id"],
                    {"originalPrice": document["price"]},
                )
                updated_count += 1
                print(
                    f"✅ Documento {document['$id']} actualizado: originalPrice = {document['price']}"
                )
            else:
                print(f"⚠️ Documento {document['$id']} sin campo 'price'")

        except Exception as e:
            print(f"❌ Error actualizando documento {document['$id']}: {str(e)}")

    print(
        f"\n✅ Proceso completado! {updated_count} documentos actualizados de {len(documents)} totales"
    )


def main():
    config = load_config()
    update_prices(config)


if __name__ == "__main__":
    main()