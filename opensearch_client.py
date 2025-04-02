from opensearchpy import OpenSearch
import datetime

class OpenSearchClient:
    def __init__(self, host='localhost', port=9200, index_name='stealer_data', verbose=False):
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_compress=True  # Enables gzip compression for requests
        )
        self.index_name = index_name
        self.verbose = verbose

        # Ensure the index exists
        self._create_index_if_not_exists()

    def _create_index_if_not_exists(self):
        if not self.client.indices.exists(index=self.index_name):
            if self.verbose:
                print(f"Creating index: {self.index_name}")
            self.client.indices.create(
                index=self.index_name,
                body={
                    "mappings": {
                        "properties": {
                            "email": {"type": "keyword"},
                            "password": {"type": "text"},
                            "source_file": {"type": "keyword"},
                            "timestamp": {"type": "date"},
                            "type": {"type": "keyword"}
                        }
                    }
                }
            )

    def index_document(self, document):
        try:
            response = self.client.index(index=self.index_name, body=document)
            if self.verbose:
                print(f"Indexed document: {response['_id']}")
        except Exception as e:
            if self.verbose:
                print(f"Error indexing document: {e}")

    def bulk_index_documents(self, documents):
        try:
            actions = [
                {"_index": self.index_name, "_source": doc} for doc in documents
            ]
            response = self.client.bulk(body=actions)
            if self.verbose:
                print(f"Bulk indexed {len(documents)} documents.")
        except Exception as e:
            if self.verbose:
                print(f"Error in bulk indexing: {e}")
